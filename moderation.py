import discord

from utils.constants import PROTECTED_USER_IDS
from utils.permissions import get_staff_level


async def can_moderate(ctx, member: discord.Member) -> bool:
    # Protected users
    if member.id in PROTECTED_USER_IDS:
        await ctx.send("❌ That user is protected.")
        return False

    # Can't punish yourself
    if member.id == ctx.author.id:
        await ctx.send("❌ You can't moderate yourself.")
        return False

    # Can't punish the bot
    if member.id == ctx.bot.user.id:
        await ctx.send("❌ You can't moderate me.")
        return False

    # Staff hierarchy
    if get_staff_level(member) >= get_staff_level(ctx.author):
        await ctx.send("❌ You can't moderate someone with an equal or higher staff level.")
        return False

    # Bot hierarchy
    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ My role is below that member.")
        return False

    return True