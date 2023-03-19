# Beowulf
Beowulf is an AI powered assistant that aims to help keep track of daily tasks, basic diet information and launguage learning. I made Beowulf to test the ChatGPT API that released last week. 
# Features
- Voice recognition along with manual input
- Access to ChatGPT for general questions
- Vocalized responses
- Automatic spreadsheeting of dietary information
- GUI for selecting common food items
- A time based reminder that selects a random task out of user defined daily goals
- Commands to create a dictionary of forien words to be quizzed on either manually or automatically over the day

# Setup
1. Install docker and get the latest voicevox image (voicevox is only needed for vocalized responses)
2. Download Beowulf
3. Obtain deepl and openai auth keys
4. In the CONFIG region add your keys. By default it attempts to read deepl_auth_key and openai_api_key in a keys.text file
5. Next if you plan to use the spreadhsheeting functionality create a google service account with the google sheets and google drive APIs
6. Download your service account's information in json format
7. Create a spreadsheet with headers for the diaty information you choose to track
![image](https://user-images.githubusercontent.com/98662866/226198396-37be614c-1cf9-48fc-bfb2-6e595dab0e9c.png)
(clicking view>freeze>freeze first row allows viewing the header row while scrolling down)

8. Click share on your spreadsheet and add the service account you created as a editor of the spreadsheet
9. Back in your python script find the following lines in the CONFIG region and change them accordingly
- sa = gspread.service_account(filename="your googleAPI_secret json file here")
- sheet = sa.open("Spreadsheet name here")
- work_sheet = sheet.worksheet("Worksheet name here") (default is Sheet1)

10. Install all required libraries
11. If you want the script's audio to be heard on applications such as discord you will need to use virutal audio cables, I used voicemeeter potato and will explain voicemeet setup later on

# Config Setup
I will shortly go into each config setting, most also have comments in the code

- beowulf_generates_audio - enabled vocalized responses 
- speaker_id - which voicevox speaker you would like
- use_widget, use_intro - wether or not you want to use these features [Widget WIP, only a solid image right now until I get around to finishing it]
- _trigger_word - word to trigger script
- _command_word - word to use a command
- _timeout - timeout for listing for trigger/command words. setting this too low will cause it to not hear you sometimes, too high and youll have to wait for the entire timeout before it processes the text.
- _ai_desc - a short prompt for what you want your ai to act like
- _ai_prompt1 - an extra prompt for giving a command "be succinct" seems to work well
- max_completion_tokens - the max tokens the ai can return, before telling the bot to be succinct it would cut it off in the middle of scenteces but now it seems to almost always keep it's replies under 100, this default could be higher most likely
- reminderTimeMin/Max - set the range of time that reminders should be (30 and 35 would give you a reminder every 30-35 mins)
- language_time - time in minutes between automatic language tests
- time_between_clears - the number of itterations between clearing the console, if you are using an IDE such as PyCharm you might need to go into your settings and configure the IDE terminal to emulate a windows terminal so that it clears correctly. this is only relevant if you plan to run the script non-stop for long periods of time
- output_device - index of device you want to handle audio output

# Extra Instructions
This section will be a few short notes that could be helpful.
- Saying the trigger word will start to record an input which will be responded to
- saying "command help list" will give you all possible commands
- adding to dictionary can be done manually by editing the dictionary file or by using the dict add command. However languages with logographic writing systems such as Korean or Chinese are easier to add with the command since their symbols are stored in unicode. If your IDE's terminal displayed forien characters as ? then you need to look into how to download that language for your IDE/windows
- Tasks can be configured in the TASKS region in the format "task": number_of_times_to_do. Example Draw: 2 will remind you to draw twice.
- The DIETARY region contains a daily values dictionary to decide which values to track and what the daily goal is for each, by default it will do dietary information for a 20 year old male
- The DIETARY region also contains a common foods dictionary, with this you can add commonly eaten foods to automatically add their dietary values to your daily
- The docker setup region has a command to run a container with the image you downloaded, you might want to change the launch options for this container
- The PROCESSING region has a function for processing commands if you would like to add any new commands.

