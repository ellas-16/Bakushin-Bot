import discord


async def get_member(guild: discord.Guild, user: str):
    try:
        user_id = int(user.strip("<@!>"))
    except ValueError:
        user_id = None

    if user_id:
        member = guild.get_member(user_id)

        if member is None:
            member = await guild.fetch_member(user_id)

        return member

    member = discord.utils.get(
        guild.members,
        mention=user,
        name=user,
        display_name=user
    )

    return member