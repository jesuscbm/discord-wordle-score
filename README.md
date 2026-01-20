# Discord Wordle Score-tracker

Discord bot that makes Wordle a competition. It includes commands to see the
current scoreboard and to compare two users.

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

In case of self-botting (not encouraged), replace discord.py with
discord.py-self

## How to use

The script is configured in a .env file.

```bash
DISCORD_TOKEN="YourBotToken"    # For self-botting, you can get your user token from the cookies in the browser
WORDLE_BOT_ID="1211781489931452447" # I am not sure whether it changes or not, worth checking
```

It also accepts two arguments:

- `overwrite`: To overwrite `score.log`

## Explanation of the script

All users must `!login` in order to be registered by the script.

### Scoreboard

The command is `!scoreboard`. The bot goes through all messages in the channel,
filtering by author to only process those made by the Wordle bot. It determines
who wins with the comprobations:

- Message contains the keyword **results**. This indicates that it is the bot
  showing the scoreboard of the previous day
- One point is added to all users in first position.

### Compare

Similar to scoreboard, `!compare @User1 @User2` runs a Head To Head comparison.
The messages go through the comprobations:

- Message contains the keyword **results**. This indicates that it is the bot
  showing the scoreboard of the previous day
- Message contains both users. It must look for the users' IDs and names, since
  the bot sometimes mentions and sometimes just says the name.
- Both users' names are in different lines. If there is not a line break
  between the name of the users, it must be a tie.

```
**Your group is on a 14 day streak!** 🔥 Here are yesterday's results:
👑 4/6: User1 User2
5/6: <@ID_OF_USER_3>
X/6: Loser4
```

In the database, all users are stored, as well as all previous results. The bot
syncs at 00.30 every day, as well as when a command is used.

## Docker

A Dockerfile and docker-compose is included to build and run the bot as an image.

## Word of advice

Self-botting this script is possible by using discord.py-self instead of
discord.py and following the instruction in the script. This is against Discord
TOS and thus can get you banned.

This is a small, ultra-quick project meant to save you a few minutes, this is
not robust code.
