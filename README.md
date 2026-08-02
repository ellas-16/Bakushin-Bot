# Discord Role Bot

This bot lets one configured Discord account run `?execute @user`.
It removes every role below the bot's highest role from the mentioned server member.

## Setup

1. In `config.py`, set `TOKEN` to your bot token and `OWNER_ID` to your Discord user ID.
2. Run `pip install -r requirements.txt`.
3. In the Discord Developer Portal, enable **Server Members Intent** and **Message Content Intent**.
4. Invite the bot with **Manage Roles**, **View Channels**, **Send Messages**, and **Read Message History** permissions.
5. Move the bot's role above every role it should remove.
6. Run `python main.py`.

Only the account whose ID is in `OWNER_ID` can use the command.
