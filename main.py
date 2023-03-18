import os
import random
import subprocess
import sys
import time
import urllib
import urllib.parse
import urllib.request
import wave
import deepl
import openai
import pyaudio
import requests
import json
import threading
import sounddevice as sd
import datetime
import speech_recognition as sr
import gspread
import tkinter as tk

# region instructions

# make sure to start docker before running
# tasks can be configured in the "task" region

command_list = "'help list' - displays this \n" \
               "'task complete' - marks a task as complete\n" \
               "'english [text]' - says provided text in english\n" \
               "'dict add' - calls add_word_to_dictionary()\n" \
               "'dict test - forces a dictionary calibration\n" \
               "'diet add' - adds values to spreadsheet\n" \
               "'diet auto' - auto adds values of common food items"

# endregion

# region CONFIG
beowulf_generates_audio = True  # when enabled beowulf speaks back
speakerID = 24  # F: 3 6 14 24 25 29? M: 11 13     #ASMR WTF?? 19

_trigger_word = "beowulf"  # trigger word to start talking to the A.I.
_timeout = 2  # int for timeout while listening for keyword
_command_word = "command"  # if word is in recorded words, respawn with a preset (i.e. if asking for dietary info we wouldn't want to ask openAI for it)

_ai_desc = "You are a friendly friendly anime girl themed assistant"
_ai_prompt1 = "Be somewhat succinct"
max_completion_tokens = 100  # max number of completion tokens

reminderTimeMin = 20
reminderTimeMax = 35

language_time = 100  # how many minutes pass between being given a word

# keys and google API
with open('keys.txt', 'r') as f:
    lines = f.readlines()

for line in lines:
    label, key = line.strip().split(': ')
    if label == 'deepl_auth_key':
        deepl_auth_key = key
    elif label == 'openai_api_key':
        openai.api_key = key

sa = gspread.service_account(filename="googleAPI_secret.json")
sheet = sa.open("Beowulf dietary")
work_sheet = sheet.worksheet("Sheet1")

time_between_clears = 1  # number of cycles until the command line is cleared

# print(sd.query_devices())
output_device = 13

# endregion

# region utils

# global variables
currently_speaking = False
waiting = False


def clear():
    sys.stdout.flush()
    os.system('cls')
    os.system('cls')


# endregion

# region foreign language

def add_word_to_dictionary():
    japanese_word = input("Enter Japanese word: ")
    english_word = input("Enter translation: ")

    # Load the dictionary from the JSON file
    with open('dictionary.json', 'r') as f:
        dictionary = json.load(f)

    # Add the new word to the dictionary
    if japanese_word not in dictionary:
        dictionary[japanese_word] = {
            'english': english_word,
            'correct_guesses': 0,
            'incorrect_guesses': 0,
            'attempts': 0,
            'last_seen': "1970-01-01",
            'last_correct_guess': "1970-01-01"
        }

    # Save the updated dictionary to the JSON file
    with open('dictionary.json', 'w') as f:
        json.dump(dictionary, f, indent=1)


def select_word_to_review():
    # Load the dictionary from the JSON file
    with open('dictionary.json', 'r') as f:
        dictionary = json.load(f)

    # Calculate the weight for each word
    weights = []
    for japanese_word in dictionary:
        last_seen_date = datetime.date.fromisoformat(str(dictionary[japanese_word].get('last_seen', '1970-01-01')))
        last_correct_guess_date = datetime.date.fromisoformat(str(
            dictionary[japanese_word].get('last_correct_guess', '1970-01-01')))
        days_since_last_seen = (datetime.date.today() - last_seen_date).days
        days_since_last_correct = (datetime.date.today() - last_correct_guess_date).days if dictionary[japanese_word][
                                                                                                'correct_guesses'] > 0 else float(
            'inf')
        correct_guesses = dictionary[japanese_word]['correct_guesses']
        incorrect_guesses = dictionary[japanese_word]['incorrect_guesses']
        attempts = dictionary[japanese_word]['attempts']
        if correct_guesses + incorrect_guesses == 0:
            weight = 0
        else:
            weight = correct_guesses / (correct_guesses + incorrect_guesses + 1) * (0.9 ** days_since_last_seen) * (
                    0.8 ** days_since_last_correct) * (0.5 ** attempts)
        weights.append(weight)

    # Normalize the weights
    weights = [weight + 0.01 for weight in weights]  # add a small positive value to each weight
    total_weight = sum(weights)
    weights = [weight / total_weight for weight in weights]

    # Select a word based on its weight
    selected_word = random.choices(list(dictionary.keys()), weights=weights)[0]

    # Update the last_seen and last_correct_guess fields for the selected word
    current_date = datetime.date.today()
    dictionary[selected_word]['last_seen'] = current_date.isoformat()

    # Increment the attempts count for the selected word
    dictionary[selected_word]['attempts'] += 1

    # Save the updated dictionary to the JSON file
    with open('dictionary.json', 'w') as f:
        json.dump(dictionary, f, indent=4)

    # Return the selected word and its English translation
    return selected_word, dictionary[selected_word]['english']


def update_dictionary(selected_word, guessed_correctly):
    # Load the dictionary from the JSON file
    with open('dictionary.json', 'r') as f:
        dictionary = json.load(f)

    # Update the fields for the selected word based on whether the user guessed correctly or not
    if guessed_correctly:
        dictionary[selected_word]['correct_guesses'] += 1
        dictionary[selected_word]['last_correct_guess'] = datetime.date.today().isoformat()
    else:
        dictionary[selected_word]['incorrect_guesses'] += 1

    dictionary[selected_word]['attempts'] += 1

    # Save the updated dictionary to the JSON file
    with open('dictionary.json', 'w') as f:
        json.dump(dictionary, f, indent=4)


# endregion

# region tasks
tasks = {"draw": 2, "exercise": 5}
completed_tasks = {task: 0 for task in tasks}
global current_task


def get_random_incomplete_task():
    incomplete_tasks = [task for task, count in tasks.items() if count > completed_tasks[task]]
    if incomplete_tasks:
        return random.choice(incomplete_tasks)
    else:
        return None


def complete_task(task):
    if task in tasks and completed_tasks[task] < tasks[task]:
        completed_tasks[task] += 1


def show_incomplete_tasks():
    incomplete_tasks = [task for task, count in tasks.items() if count > completed_tasks[task]]
    if incomplete_tasks:
        print("Uncompleted tasks:")
        for task in incomplete_tasks:
            print(f"- {task}")
    else:
        print("All tasks have been completed!")


# endregion

# region dietary
# Recommended dietary values for a 20-year-old male
DAILY_VALUES = {
    "calories": 2500,
    "protein": 36,
    "carbs": 310,
    "fat": 53,  # limit not goal
    "fiber": 38,
    "water": 8  # 8 cups per day
}
COMMON_FOODS = {
    "None": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
    "Banana": {"calories": 110, "protein": 1, "carbs": 28, "fat": 0, "fiber": 3},
    "Apple": {"calories": 95, "protein": 1, "carbs": 25, "fat": 0, "fiber": 4},
    # Add more foods here
}


def get_current_intake():
    today = datetime.date.today().strftime("%m/%d/%Y")  # get today's date in "mm/dd/yyyy" format

    # find the index of the row for the current day
    dates = work_sheet.col_values(1)  # get all the dates in the worksheet
    try:
        row_index = dates.index(today)
    except ValueError:
        print("No data found for today.")
        current_intake.update({nutrient: 0 for nutrient in DAILY_VALUES})
        return

    # get the nutrient values from the corresponding row
    nutrient_values = work_sheet.row_values(
        row_index + 1)  # the row index in the worksheet starts at 1, so add 1 to the index
    nutrient_values.pop(0)  # remove the date from the list

    # update the current_intake dictionary with the nutrient values
    for nutrient, value in zip(DAILY_VALUES.keys(), nutrient_values):
        current_intake[nutrient] = int(value)


# Initialize current amounts of nutrients
current_intake = {nutrient: 0 for nutrient in DAILY_VALUES}
get_current_intake()


def diet_add():
    global waiting
    waiting = True
    nutrient = input(
        "Enter the name of the nutrient you want to add to (calories, protein, carbs, fat, fiber, water): ")
    while nutrient not in DAILY_VALUES:
        print("Invalid nutrient name. Please enter a valid nutrient name.")
        nutrient = input(
            "Enter the name of the nutrient you want to add to (e.g. calories, protein, carbs, fat, fiber, water): ")

    amount = input(f"Enter the amount of {nutrient} you want to add: ")
    while not amount.isnumeric():
        print("Invalid input. Please enter a numeric value.")
        amount = input(f"Enter the amount of {nutrient} you want to add: ")

    current_intake[nutrient] += int(amount)
    print(f"{amount} {nutrient} added to current intake.")
    log_intake()
    waiting = False


def diet_add_common_food(food):
    """Update the current_intake dictionary with the nutrient values of the selected food."""
    for nutrient, value in COMMON_FOODS[food].items():
        current_intake[nutrient] += value
    # Update the worksheet with the new values
    log_intake()


def create_common_food_gui():
    """Create the GUI with buttons for each food item."""
    root = tk.Tk()
    root.geometry("400x400")
    root.title("Select a food")

    # Create a scrollbar for the food list
    scrollbar = tk.Scrollbar(root)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Create a listbox for the food list
    food_listbox = tk.Listbox(root, yscrollcommand=scrollbar.set)
    for food in COMMON_FOODS.keys():
        food_listbox.insert(tk.END, food)
    food_listbox.pack(side=tk.LEFT, fill=tk.BOTH)

    # Attach the scrollbar to the listbox
    scrollbar.config(command=food_listbox.yview)

    # Create a button to select the chosen food
    select_button = tk.Button(root, text="Select",
                              command=lambda: (diet_add_common_food(food_listbox.get(tk.ACTIVE)), root.destroy()))
    select_button.pack()

    # Start the GUI loop
    root.mainloop()


def log_intake():
    """Update the worksheet with the new values."""
    today = datetime.date.today().strftime("%m/%d/%Y")  # get today's date in "mm/dd/yyyy" format

    # find the index of the row for the current day
    dates = work_sheet.col_values(1)  # get all the dates in the worksheet
    try:
        row_index = dates.index(today)
    except ValueError:
        # If there is no row for today, create a new one
        row_index = len(dates)
        work_sheet.update_cell(row_index + 1, 1, today)

    # Update the nutrient values in the row
    for i, nutrient in enumerate(DAILY_VALUES.keys()):
        work_sheet.update_cell(row_index + 1, i + 2, current_intake[nutrient])


# endregion

# region AI setup
messages = [
    {"role": "system", "content": _ai_desc},
    {"role": "user", "content": _ai_prompt1}
]

# endregion

# region Docker setup
cmd = ["docker", "run", "--rm", "--gpus", "all", "-p", "127.0.0.1:50021:50021",
       "voicevox/voicevox_engine:nvidia-ubuntu20.04-latest"]
process = subprocess.Popen(cmd, shell=True)

# Continue executing the rest of the code
print("Docker command running in background.")
# endregion

# region stage 1 audio and text

# used to listen for when to process audio

# define the trigger word
trigger_word = _trigger_word

# initialize the recognizer
r = sr.Recognizer()

# set the microphone as the audio source
mic = sr.Microphone()

timeout = _timeout


# endregion

# region stage 2 audio and text

# used for recording audio to process requests

def record_audio(is_command):
    clear()
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "input.wav"
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    frames = []
    print("Recording...")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
        while True:
            try:
                # text = r.recognize_google(audio)
                frames.append(audio.get_raw_data(convert_rate=RATE, convert_width=2))
                audio = r.listen(source, timeout=0.1)
            except sr.WaitTimeoutError:
                break
            except sr.UnknownValueError:
                pass
    print("Stopped recording.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    if is_command:
        transcribe_audio_command("input.wav")
    else:
        transcribe_audio("input.wav")


def transcribe_audio(file):
    global currently_speaking
    currently_speaking = True
    audio_file = open(file, "rb")
    transcript = openai.Audio.translate("whisper-1", audio_file)
    query_openAI(transcript.text)


def transcribe_audio_command(file):
    global currently_speaking
    currently_speaking = True
    audio_file = open(file, "rb")
    transcript = openai.Audio.translate("whisper-1", audio_file)
    process_command(transcript.text)


# endregion

# region processing

def is_phrase_in_string(phrase, input_string):
    phrase_words = phrase.split()
    input_words = input_string.split()

    for i in range(len(input_words) - len(phrase_words) + 1):
        if input_words[i:i + len(phrase_words)] == phrase_words:
            return True

    return False


def process_manual_input(input_text):
    if currently_speaking:
        return

    if _command_word in input_text:
        process_command(input_text)
    else:
        query_openAI(input_text)


def process_command(command_text):
    global last_task_done, current_task, currently_speaking, waiting
    waiting = True

    if is_phrase_in_string("task complete", command_text) and last_task_done is False:
        last_task_done = True
        complete_task(current_task)
        if beowulf_generates_audio:
            translate_text("Task marked as complete")
        else:
            print("Task marked as complete")
    elif is_phrase_in_string("help list", command_text):
        print(command_list)
    elif is_phrase_in_string("english", command_text):
        speech_text(command_text[15::])
    elif is_phrase_in_string("dict add", command_text):
        add_word_to_dictionary()
    elif is_phrase_in_string("dict test", command_text):
        process_language_test()
    elif is_phrase_in_string("diet add", command_text):
        diet_add()
    elif is_phrase_in_string("diet auto", command_text):
        create_common_food_gui()
    else:
        print("Unknown command")

    currently_speaking = False
    waiting = False
    time.sleep(2)


def query_openAI(text):
    if text:
        messages.append(
            {"role": "user", "content": text},
        )
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages, max_tokens=max_completion_tokens
        )
    reply = chat.choices[0].message.content  # later check how many choices are outputted and maybe get a random one
    if not beowulf_generates_audio: print(f"Beowulf: {reply}")
    messages.append({"role": "assistant", "content": reply})
    if beowulf_generates_audio:
        translate_text(reply)


def process_reminder():
    global last_task_done, current_task
    if last_task_done:
        last_task_done = False
        current_task = get_random_incomplete_task()

        if beowulf_generates_audio and current_task is not None:
            translate_text(f"time to complete task. {current_task}")
        elif not beowulf_generates_audio and current_task is not None:
            print(f"It's time to perform task: {current_task}")
    else:
        if beowulf_generates_audio:
            translate_text(f"It seems you didn't complete {current_task}. Don't forget to mark it as complete by "
                           f"telling me 'Command, complete task task name'")
        else:
            print(f"It seems you didn't complete {current_task}. Don't forget to mark it as complete by telling me "
                  f"'Command, complete task task name'")
        time.sleep(1)
        print(f"Tasks remaining: {show_incomplete_tasks()}")
        time.sleep(1)


def process_language_test():
    global waiting
    waiting = True
    word, english_translation = select_word_to_review()
    print(f"Dictionary: {word}. Press enter and then type your answer ")
    speech_text(f"Dictionary : {word}")
    guess = input("type guess now:\n")
    update_dictionary(word, guess.lower() == english_translation)
    if guess.lower() == english_translation:
        print("good job!")
        speech_text("good job!")
    else:
        print(f"nice try, but it was {word}")
        speech_text(f"nice try, but it was {word}")


# endregion

# region generate audio

def translate_text(text):
    translator = deepl.Translator(deepl_auth_key)
    result = translator.translate_text(text, target_lang="JA")
    print("EN: " + text)
    print("JP: " + result.text)
    speech_text(result.text)


def speech_text(sentence):
    params_encoded = urllib.parse.urlencode({'text': sentence, 'speaker': speakerID})
    r = requests.post(f'http://127.0.0.1:50021/audio_query?{params_encoded}')
    voicevox_query = r.json()
    params_encoded = urllib.parse.urlencode({'speaker': speakerID})
    r = requests.post(f'http://127.0.0.1:50021/synthesis?{params_encoded}', json=voicevox_query)
    with open("output.wav", "wb") as outfile:
        outfile.write(r.content)

    p = pyaudio.PyAudio()
    audio_file = wave.open("output.wav", "rb")
    # Open the audio stream
    stream = p.open(format=p.get_format_from_width(audio_file.getsampwidth()),
                    channels=audio_file.getnchannels(),
                    rate=audio_file.getframerate(),
                    output=True,
                    output_device_index=output_device)
    # Read data from the audio file and write it to the audio stream
    data = audio_file.readframes(1024)
    while data:
        stream.write(data)
        data = audio_file.readframes(1024)
    # Clean up
    stream.stop_stream()
    stream.close()
    audio_file.close()
    p.terminate()
    time.sleep(2)

    currently_speaking = False


def play_intro():
    p = pyaudio.PyAudio()
    audio_file = wave.open("intro.wav", "rb")
    # Open the audio stream
    stream = p.open(format=p.get_format_from_width(audio_file.getsampwidth()),
                    channels=audio_file.getnchannels(),
                    rate=audio_file.getframerate(),
                    output=True,
                    output_device_index=output_device)
    # Read data from the audio file and write it to the audio stream
    data = audio_file.readframes(1024)
    while data:
        stream.write(data)
        data = audio_file.readframes(1024)
    # Clean up
    stream.stop_stream()
    stream.close()
    audio_file.close()
    p.terminate()
    time.sleep(2)


# endregion

def run_time_based():
    global last_task_done
    global currently_speaking
    last_task_execution_time = time.time()
    last_language_execution_time = time.time()
    last_task_done = True

    while True:
        current_time = time.time()
        if current_time - last_task_execution_time >= random.uniform(reminderTimeMin * 60,
                                                                     reminderTimeMax * 60) and not currently_speaking:
            last_task_execution_time = time.time()
            if get_random_incomplete_task() is not None:
                process_reminder()
        if current_time - last_language_execution_time >= (language_time * 60) and not currently_speaking:
            last_language_execution_time = time.time()
            process_language_test()

        time.sleep(1)


def run_user_input():
    while True:
        user_input = input()
        if user_input != "":
            process_manual_input(user_input)
        time.sleep(1)


input_thread = threading.Thread(target=run_user_input)
input_thread.daemon = True
input_thread.start()

time_thread = threading.Thread(target=run_time_based)
time_thread.daemon = True
time_thread.start()

play_intro()

with mic as source:
    r.adjust_for_ambient_noise(source)
    i = 0
    print("Beowulf started")
    while True:
        if waiting:
            continue

        i += 1
        try:
            audio = r.listen(source, timeout=timeout)
            text = r.recognize_google(audio, show_all=False)
            # check if the trigger word is in the speech
            if trigger_word in text.lower():
                record_audio(False)
            if _command_word in text.lower():
                record_audio(True)

        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            pass
        except sr.WaitTimeoutError:
            pass

        if i >= time_between_clears:
            i = 0
            clear()

        time.sleep(0.1)
