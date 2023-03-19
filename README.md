# Beowulf
Beowulf is an AI-powered assistant that helps keep track of daily tasks, basic diet information, and language learning. I created Beowulf to test the ChatGPT API that was released last week.

# Features
- Voice recognition along with manual input.
- Access to ChatGPT for general questions.
- Vocalized responses.
- Automatic spreadsheeting of dietary information.
- GUI for selecting common food items.
- A time-based reminder that selects a random task out of user-defined daily goals.
- Commands to create a dictionary of foreign words to be quizzed on either manually or automatically throughout the day.
Setup
- Install Docker and get the latest Voicevox image (Voicevox is only needed for vocalized responses).
- Download Beowulf.

- Obtain Deepl and OpenAI auth keys.

- In the CONFIG region, add your keys. By default, it attempts to read deepl_auth_key and openai_api_key in a keys.txt file.

- If you plan to use the spreadsheeting functionality, create a Google service account with the Google Sheets and Google Drive APIs.

- Download your service account's information in JSON format.

- Create a spreadsheet with headers for the dietary information you choose to track.
![image](https://user-images.githubusercontent.com/98662866/226211362-c977f672-79ca-46d0-a450-d86fbf346baa.png)

(Clicking View > Freeze > Freeze first row allows viewing the header row while scrolling down.)

- Click Share on your spreadsheet and add the service account you created as an editor of the spreadsheet.

- Back in your Python script, find the following lines in the CONFIG region and change them accordingly:

sa = gspread.service_account(filename="your googleAPI_secret JSON file here")
sheet = sa.open("Spreadsheet name here")
work_sheet = sheet.worksheet("Worksheet name here") (default is Sheet1)

- Install all required libraries.
- If you want the script's audio to be heard on applications such as Discord, you will need to use virtual audio cables. I used Voicemeeter Potato and will explain Voicemeeter setup later on.

# Config Setup
I will shortly go into each config setting, most also have comments in the code.

- beowulf_generates_audio: enables vocalized responses.
- speaker_id: which Voicevox speaker you would like.
- use_widget, use_intro: whether or not you want to use these features [Widget WIP, only a solid image right now until I get around to finishing it].
- _trigger_word: word to trigger script.
- _command_word: word to use as a command.
- _timeout: timeout for listening for trigger/command words. Setting this too low will cause it to not hear you sometimes, too high and you'll have to wait for the entire timeout before it processes the text.
- _ai_desc: a short prompt for what you want your AI to act like.
- _ai_prompt1: an extra prompt for giving a command. "Be succinct" seems to work well.
- max_completion_tokens: the maximum tokens the AI can return. Before telling the bot to be succinct, it would cut it off in the middle of sentences, but now it seems to almost always keep its replies under 100. This default could be higher, most likely.
- reminderTimeMin/Max: set the range of time that reminders should be (30 and 35 would give you a reminder every 30-35 minutes).
- language_time: time in minutes between automatic language tests.
- time_between_clears: the number of iterations between clearing the console. If you are using an IDE such as PyCharm, you might need to go into your settings and configure the IDE terminal to emulate a Windows terminal so that it clears correctly. This is only relevant if you plan to run the script non-stop for long periods of time.

- output_device: index of the device you want to handle audio output.
# Extra Instructions
This section will be a few short notes that could be helpful.

- Saying the trigger word will start to record an input that will be responded to.
- Saying "command help list" will give you all possible commands.
- Adding to the dictionary can be done manually by editing the dictionary file or by using the dict add command. However, languages with logographic writing systems such as Korean or Chinese are easier to add with the command since their symbols are stored in Unicode. If your IDE's terminal displayed foreign characters as ?, then you need to look into how to download that language for your IDE/Windows.
- Tasks can be configured in the TASKS region in the format "task": number_of_times_to_do. Example: Draw: 2 will remind you to draw twice.
- The DIETARY region contains a daily values dictionary to decide which values to track and what the daily goal is for each. By default, it will do dietary information for a 20-year-old male.
- The DIETARY region also contains a common foods dictionary. With this, you can add commonly eaten foods to automatically add their dietary values to your daily.
- The Docker setup region has a command to run a container with the image you downloaded. You might want to change the launch options for this container.
- The PROCESSING region has a function for processing commands if you would like to add any new commands.

# Voicemeeter Setup
- Download Voicemeeter potato
- Perform standard setup for input and output
- Below is a reference picture of my setup, outputting my script's audio to VAIO 3. Using virtual AUX for discord, Skype, ect.
![image](https://user-images.githubusercontent.com/98662866/226211604-93ab6d99-2ecd-40fe-9f9f-a4ff33f2e48a.png)
