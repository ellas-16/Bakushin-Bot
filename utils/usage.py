USAGE_MESSAGES = {
    "warn": (
        "**Usage:** `+warn @user <reason>`\n"
        "**Example:** `+warn @user Spamming in general`"
    ),

    "warnings": (
        "**Usage:** `+warnings @user`\n"
        "**Example:** `+warnings @user`"
    ),

    "hush": (
        "**Usage:** `+hush @user <duration> [reason]`\n"
        "**Example:** `+hush @user 10m`\n"
        "**Example:** `+hush @user 1h Spamming`"
    ),

    "unhush": (
        "**Usage:** `+unhush @user`\n"
        "**Example:** `+unhush @user`"
    ),

    "execute": (
        "**Usage:** `+execute @user`\n"
        "**Example:** `+execute @user`"
    ),

    "reverseexecution": (
        "**Usage:** `+reverseexecution @user`\n"
        "**Example:** `+reverseexecution @user`"
    ),

    "assassinate": (
        "**Usage:** `+assassinate @user`\n"
        "**Example:** `+assassinate @user`"
    ),

    "say": (
        "**Usage:** `+say <message>`\n"
        "**Example:** `+say Hello everyone!`"
    ),
    "exile": (
        "**Usage:** `+exile @user`\n"
        "**Example:** `+exile @user`"
    ),

    "unexile": (
        "**Usage:** `+unexile <user ID>`\n"
        "**Example:** `+unexile 123456789012345678`"
    ),
}


def get_usage(command_name: str) -> str:
    return USAGE_MESSAGES.get(
        command_name,
        f"**Usage:** `+{command_name}`"
    )