from utils.constants import ALLOWED_IDS, STAFF_KEY_ROLE_ID


def is_owner(user) -> bool:
    return user.id in ALLOWED_IDS


def has_staff_key(member) -> bool:
    return any(role.id == STAFF_KEY_ROLE_ID for role in member.roles)


async def ensure_guild(ctx) -> bool:
    if ctx.guild is None:
        await ctx.send("❌ This command only works in a server.")
        return False
    return True


async def ensure_owner(ctx) -> bool:
    if not is_owner(ctx.author):
        await ctx.send("❌ You don't have permission to use this command.")
        return False
    return True


async def ensure_staff(ctx) -> bool:
    if not is_owner(ctx.author) and not has_staff_key(ctx.author):
        await ctx.send("❌ You don't have permission to use this command.")
        return False
    return True