# Discord Wordle Score-tracker

Small dumb python script that uses Discord.py API to track scores in Discord's Wordle - for the most competitive users. Works by processing all messages in the designated chat to find those in which one of two users wins.

The script outputs the number of wins and ties of both users, allowing you to brag and annoy your fellow Wordlers. It also stores all the relevant messages in `score.log`. Just in case they don't believe you.

## Requirements

- Python >= 3.8 and Pip
- discord.py or discord.py-self
- dotenv

## Installation

With python >= 3.8 installed, run in the folder of your choice

```bash
python -m venv .venv                    # Create virtual environment in a new .venv folder
source .venv/bin/activate               # Activate the venv for the current shell session
pip install discord.py python-dotenv    # Install required dependencies
```

In case of self-botting (not encouraged), replace discord.py with discord.py-self

## How to use

The script is configured in a .env file.

```bash
DISCORD_TOKEN="YourBotToken"    # For self-botting, you can get your user token from the cookies in the browser
CHANNEL_ID="Channel where Wordle Bot announces results"
WORDLE_BOT_ID="1211781489931452447" # I am not sure if it changes or not, worth checking

U1_ID="ID of user 1"
U1_DISCORD_NAME="Server display name of user 1"
U1_NAME="Name for logging and showing results"

U1_ID="ID of user 2"
U1_DISCORD_NAME="Server display name of user 2"
U1_NAME="Name for logging and showing results"
```

It also accepts two arguments:
- `debug`: To store the discarded messages in another file `discarded.log`
- `overwrite`: To overwrite `score.log`

## Explanation of the script

The script goes through all messages in the channel, filtering by author to only process those made by the Wordle bot. It determines who wins with the comprobations:
- Message contains the keyword **results**. This indicates that it is the bot showing the scoreboard of the previous day
- Message contains both users. It must look for the users' IDs and names, since the bot sometimes mentions and sometimes just says the name.
- Both users' names are in different lines. If there is not a line break between the name of the users, it must be a tie.

```
**Your group is on a 14 day streak!** 🔥 Here are yesterday's results:  
👑 4/6: User1 User2  
5/6: <@ID_OF_USER_3>  
X/6: Loser4  
```

## Word of advice

Self-botting this script is possible by using discord.py-self instead of discord.py and following the instruction in the script. This is against Discord TOS and thus can get you banned. 

This is a small, ultra-quick project meant to save you a few minutes, this is not robust code. 
