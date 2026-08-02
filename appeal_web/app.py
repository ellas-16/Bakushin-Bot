import os
import json
import requests

from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("APPEAL_WEBHOOK_URL", "")
APPEALS_FILE = "appeals.json"


def load_appeals():
    if not os.path.exists(APPEALS_FILE):
        return {}

    try:
        with open(APPEALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_appeals(appeals):
    with open(APPEALS_FILE, "w", encoding="utf-8") as f:
        json.dump(appeals, f, indent=4)


@app.route("/", methods=["GET", "POST"])
def appeal():
    error = None
    success = False

    if request.method == "POST":
        discord_id = request.form.get("discord_id", "").strip()
        username = request.form.get("username", "").strip()
        appeal_text = request.form.get("appeal", "").strip()

        if not discord_id.isdigit():
            error = "Please enter a valid Discord User ID."

        elif not appeal_text:
            error = "Please write your appeal."

        elif len(appeal_text) > 2000:
            error = "Your appeal must be 2000 characters or less."

        elif not DISCORD_WEBHOOK_URL:
            error = "The appeal system is not configured yet."

        else:
            appeals = load_appeals()

            appeals[discord_id] = {
                "username": username,
                "appeal": appeal_text,
                "status": "pending",
            }

            save_appeals(appeals)

            payload = {
                "embeds": [
                    {
                        "title": "📨 New Ban Appeal",
                        "color": 0x5865F2,
                        "fields": [
                            {
                                "name": "👤 User",
                                "value": (
                                    f"{username or 'Not provided'}\n"
                                    f"`{discord_id}`"
                                ),
                                "inline": True,
                            },
                            {
                                "name": "📝 Appeal",
                                "value": appeal_text,
                                "inline": False,
                            },
                        ],
                        "footer": {
                            "text": (
                                "Sakura • Lucent Moderation • Ban Appeal"
                            )
                        },
                    }
                ]
            }

            try:
                response = requests.post(
                    DISCORD_WEBHOOK_URL,
                    json=payload,
                    timeout=10,
                )

                response.raise_for_status()
                success = True

            except requests.RequestException:
                error = (
                    "We couldn't submit your appeal right now. "
                    "Please try again later."
                )

    return render_template(
        "index.html",
        error=error,
        success=success,
    )

@app.route("/status")
def status():
    discord_id = request.args.get("discord_id", "").strip()

    if not discord_id.isdigit():
        return render_template(
            "index.html",
            error="Please enter a valid Discord User ID.",
        )

    appeals = load_appeals()
    appeal_data = appeals.get(discord_id)

    if appeal_data is None:
        return render_template(
            "index.html",
            error="No appeal was found for that Discord ID.",
        )

    status_value = appeal_data.get("status", "pending")

    return render_template(
        "index.html",
        status=status_value,
    )




@app.route("/api/appeal/<discord_id>", methods=["POST"])
def update_appeal(discord_id):
    if not discord_id.isdigit():
        return {"error": "Invalid Discord ID"}, 400

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("approved", "rejected"):
        return {"error": "Invalid status"}, 400

    appeals = load_appeals()

    if discord_id not in appeals:
        return {"error": "Appeal not found"}, 404

    appeals[discord_id]["status"] = new_status
    save_appeals(appeals)

    print(
        f"[WEBSITE] Appeal status updated: "
        f"{discord_id} -> {new_status}",
        flush=True,
    )

    return {
        "success": True,
        "status": new_status,
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )