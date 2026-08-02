from utils.constants import ALLOWED_IDS

# ==========================
# Access Roles
# ==========================

STAFF_KEY_ROLE = 1426339476874989750
MANAGEMENT_KEY_ROLE = 1426034359961387100

# ==========================
# Moderation Hierarchy
# Lowest -> Highest 
# ==========================

JUNIOR_MOD_ROLE = 1426023421082341491
MOD_ROLE = 1426023239888539740
SENIOR_MOD_ROLE = 1426023138172338286
HEAD_MOD_ROLE = 1426022983083888681
ADMIN_ROLE = 1426022833833906258
ASSISTANT_MANAGER_ROLE = 1458655844294987797
MANAGER_ROLE = 1458655767937683559
LEAD_MANAGER_ROLE = 1458655699310739625
CO_OWNER_ROLE = 1426338715923644516
OWNER_ROLE = 1425998931057184768


# Lowest -> Highest
MODERATION_HIERARCHY = [
    JUNIOR_MOD_ROLE,
    MOD_ROLE,
    SENIOR_MOD_ROLE,
    HEAD_MOD_ROLE,
    ADMIN_ROLE,
    ASSISTANT_MANAGER_ROLE,
    MANAGER_ROLE,
    LEAD_MANAGER_ROLE,
    CO_OWNER_ROLE,
    OWNER_ROLE,
]


def get_staff_level(member) -> int:
    # Bot owners always have the highest level
    if member.id in ALLOWED_IDS:
        return len(MODERATION_HIERARCHY) + 1

    highest = 0

    for index, role_id in enumerate(MODERATION_HIERARCHY, start=1):
        if any(role.id == role_id for role in member.roles):
            highest = index

    return highest


async def ensure_level(ctx, required_level: int) -> bool:
    if get_staff_level(ctx.author) < required_level:
        await ctx.send("❌ You don't have permission to use this command.")
        return False
    return True

async def ensure_jmod(ctx):
    return await ensure_level(ctx, 1)


async def ensure_mod(ctx):
    return await ensure_level(ctx, 2)


async def ensure_smod(ctx):
    return await ensure_level(ctx, 3)


async def ensure_hmod(ctx):
    return await ensure_level(ctx, 4)


async def ensure_admin(ctx):
    return await ensure_level(ctx, 5)


async def ensure_assistant_manager(ctx):
    return await ensure_level(ctx, 6)


async def ensure_manager(ctx):
    return await ensure_level(ctx, 7)


async def ensure_lead_manager(ctx):
    return await ensure_level(ctx, 8)


async def ensure_coowner(ctx):
    return await ensure_level(ctx, 9)


async def ensure_owner(ctx):
    return await ensure_level(ctx, 10)