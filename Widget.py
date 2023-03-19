from tkinter import Tk, Canvas, NW
import pyaudio
from PIL import Image, ImageTk, ImageEnhance
import numpy as np

# region config
listening_device_index = 8  # device output that widget should react to
# endregion


CHUNK = 1024
FORMAT = pyaudio.paInt16


def get_audio_level(device_index):
    global CHUNK, FORMAT
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK)

    data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
    audio_level = np.sqrt(np.mean(np.square(data)))

    stream.stop_stream()
    stream.close()
    p.terminate()

    return audio_level


# create the root window
root = Tk()

# hide the bar at the top of the window
root.overrideredirect(True)

# position the window at the bottom left of the screen
window_width = 450
window_height = 600
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x_position = -2
y_position = 657

root.geometry("+%d+%d" % (x_position, y_position))

# make the background transparent
root.attributes('-transparentcolor', '#f0f0f0')

# make the window appear over other windows
root.attributes('-topmost', True)

# create the canvas
canvas = Canvas(root, width=window_width, height=window_height)
canvas.pack()

# create the images
normal_img = Image.open("WidgetImages/1_Useable.png").convert("RGBA")
dim_img = ImageEnhance.Brightness(normal_img).enhance(0.8)

# add the normal image to the canvas
normal_img_tk = ImageTk.PhotoImage(normal_img)
img_id = canvas.create_image(0, 0, anchor=NW, image=normal_img_tk)

# add the dimmed image to the canvas
dim_img_tk = ImageTk.PhotoImage(dim_img)


def update_image(device_index):
    if get_audio_level(device_index) > 0.5:
        canvas.itemconfigure(img_id, image=normal_img_tk)
    else:
        canvas.itemconfigure(img_id, image=dim_img_tk)
    root.after(1000, lambda: update_image(device_index))


# start the GUI
# root.after(1000, lambda: update_image(listening_device_index))
root.mainloop()
