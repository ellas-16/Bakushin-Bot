import discord


def success_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )


def error_embed(description: str) -> discord.Embed:
    return discord.Embed(
        title="❌ Error",
        description=description,
        color=discord.Color.red()
    )


def info_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )