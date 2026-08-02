# Sakura external ban appeal page

This is the simplest version of the external appeal system.

## What it does

1. A banned user opens the webpage.
2. They enter their Discord User ID and appeal.
3. The server sends the appeal to a Discord webhook in the staff appeal channel.

## Configure

Set the environment variable:

`APPEAL_WEBHOOK_URL`

Do not put the webhook URL in frontend HTML/JavaScript.

## Run locally

```bash
pip install -r requirements.txt
python appeal_web/app.py
```

Then open `http://127.0.0.1:5000`.
