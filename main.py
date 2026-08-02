import asyncio
import os
import requests
import threading
from flask import Flask

import discord
from discord.ext import commands

from config import OWNERS_IDS, TOKEN
from utils.usage import get_usage

from utils.constants import (
    ALLOWED_IDS,
    EXCLUDED_ROLE_IDS,
    PROTECTED_USER_IDS,
    STAFF_KEY_ROLE_ID,
)

from utils.permissions import get_staff_level, ensure_jmod
from utils.moderation import can_moderate
from utils.cases import create_case
from utils.helpers import load_backups, save_backups

from utils.checks import (
    ensure_guild,
    ensure_owner,
    ensure_staff,
)

app = Flask(__name__)

@app.route("/")
def home():
    return "Sakura Bot is online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()


APPEAL_CHANNEL_ID = 1532742444922179744
APPEAL_WEB_URL = "https://bakushin-bot.onrender.com"

# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="+",
    intents=intents,
    help_command=None,
)


# ============================================================
# BAN APPEAL MODAL
# ============================================================

class BanAppealModal(discord.ui.Modal, title="Ban Appeal"):
    appeal = discord.ui.TextInput(
        label="Your Appeal",
        placeholder=(
            "Explain why you believe your ban should be removed..."
        ),
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000,
    )

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ):
        channel = interaction.client.get_channel(
            APPEAL_CHANNEL_ID
        )

        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(
                    APPEAL_CHANNEL_ID
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
            ):
                await interaction.response.send_message(
                    "❌ The appeal system is currently unavailable.",
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title="📨 New Ban Appeal",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="👤 User",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=True,
        )

        embed.add_field(
            name="📝 Appeal",
            value=self.appeal.value,
            inline=False,
        )

        embed.set_footer(
            text="Sakura • Lucent Moderation • Ban Appeal"
        )

        try:
            await channel.send(embed=embed)

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            await interaction.response.send_message(
                "❌ I couldn't submit your appeal right now. "
                "Please try again later.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ Your appeal has been submitted to the staff team.",
            ephemeral=True,
        )


# ============================================================
# ORIGINAL APPEAL BUTTON
# ============================================================

class BanAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    discord.ui.Button(
        label="Submit Appeal",
        style=discord.ButtonStyle.link,
        url=APPEAL_WEB_URL
    )
    async def appeal_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(
            BanAppealModal()
        )


def update_appeal_status(user_id: int, status: str):
    try:
        response = requests.post(
            f"{APPEAL_WEB_URL}/api/appeal/{user_id}",
            json={"status": status},
            timeout=5,
        )

        print(
            f"[APPEAL] Website status update: "
            f"{user_id} -> {status} "
            f"({response.status_code})",
            flush=True,
        )

    except requests.RequestException as e:
        print(
            f"[APPEAL] ❌ Could not update website: {e}",
            flush=True,
        )

# ============================================================
# STAFF BAN APPEAL VIEW
# ============================================================

class BanAppealStaffView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    # ========================================================
    # ACCEPT APPEAL
    # ========================================================

    @discord.ui.button(
        label="Accept Appeal",
        style=discord.ButtonStyle.success,
        custom_id="sakura_accept_appeal",
        emoji="✅",
    )
    async def accept_appeal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This button can only be used in the server.",
                ephemeral=True,
            )
            return

        # Get the banned user
        try:
            user = await interaction.client.fetch_user(self.user_id)

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ I couldn't find that Discord user.",
                ephemeral=True,
            )
            return


        # ==================================================
        # NOW UNBAN THE USER
        # ==================================================

        try:
            await interaction.guild.unban(
                user,
                reason=(
                    f"Ban appeal accepted by "
                    f"{interaction.user} ({interaction.user.id})"
                ),
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ That user is not currently banned.",
                ephemeral=True,
            )
            return

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to unban that user.",
                ephemeral=True,
            )
            return

        except discord.HTTPException as e:
            print(
                f"[APPEAL] ❌ Unban failed: {e}",
                flush=True,
            )

            await interaction.response.send_message(
                "❌ Discord rejected the unban request.",
                ephemeral=True,
            )
            return

        # Send approval DM
        dm_sent = False

        try:
            dm_embed = discord.Embed(
                title="✅ Ban Appeal Approved",
                description=(
                    f"Your ban appeal for **{interaction.guild.name}** "
                    "has been approved.\n\n"
                    "You have been **unbanned** and may rejoin the server."
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )

            dm_embed.add_field(
                name="🔗 Rejoin the server",
                value="https://discord.gg/lucent",
                inline=False,
            )

            dm_embed.set_footer(
               text="Sakura • Lucent Moderation"
            )

              dm_embed.add_field(
              name="🔗 Submit an Appeal",
              value="https://bakushin-bot.onrender.com/appeal",
              inline=False
            )

            await user.send(embed=dm_embed)

            dm_sent = True

            print(
                f"[APPEAL] ✅ Approval DM sent to {self.user_id}",
                flush=True,
            )

        except discord.Forbidden:
            print(
                f"[APPEAL] ❌ Cannot DM {self.user_id} "
                "(DMs closed or blocked).",
                flush=True,
            )

        except discord.HTTPException as e:
            print(
                f"[APPEAL] ❌ DM failed for {self.user_id}: {e}",
                flush=True,
            )
        # Update website
        update_appeal_status(
            self.user_id,
           "approved",
        )

        # Update staff message
        embed = interaction.message.embeds[0]

        embed.color = discord.Color.green()

        embed.set_footer(
            text="Sakura • Lucent Moderation • Appeal Accepted"
        )

        embed.add_field(
            name="✅ Decision",
            value=(
                f"Accepted by {interaction.user.mention}\n"
                "User has been unbanned.\n"
                f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
            ),
            inline=False,
        )

        # Disable both buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

    # ========================================================
    # REJECT APPEAL
    # ========================================================

    @discord.ui.button(
        label="Reject Appeal",
        style=discord.ButtonStyle.danger,
        custom_id="sakura_reject_appeal",
        emoji="❌",
    )
    async def reject_appeal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This button can only be used in the server.",
                ephemeral=True,
            )
            return

        # Get the user
        try:
            user = await interaction.client.fetch_user(
                self.user_id
            )

        except discord.NotFound:
            user = None

        # Send rejection DM
        dm_sent = False

        if user is not None:
            try:
                dm_embed = discord.Embed(
                    title="❌ Ban Appeal Rejected",
                    description=(
                        f"Your ban appeal for **{interaction.guild.name}** "
                        "has been rejected.\n\n"
                        "You will remain banned from the server."
                    ),
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow(),
                )

                dm_embed.set_footer(
                    text="Sakura • Lucent Moderation"
                )

                await user.send(embed=dm_embed)

                dm_sent = True

                print(
                    f"[APPEAL] ✅ Rejection DM sent to {self.user_id}",
                    flush=True,
                )

            except discord.Forbidden:
                print(
                    f"[APPEAL] ❌ Cannot DM {self.user_id} "
                    "(DMs closed or blocked).",
                    flush=True,
                )

            except discord.HTTPException as e:
                print(
                    f"[APPEAL] ❌ DM failed for {self.user_id}: {e}",
                    flush=True,
                )

        # Update website
        update_appeal_status(
            self.user_id,
            "rejected",
        )

        # Update staff message
        embed = interaction.message.embeds[0]

        embed.color = discord.Color.red()

        embed.set_footer(
            text="Sakura • Lucent Moderation • Appeal Rejected"
        )

        embed.add_field(
            name="❌ Decision",
            value=(
                f"Rejected by {interaction.user.mention}\n"
                "User remains banned.\n"
                f"DM sent: {'✅ Yes' if dm_sent else '❌ No'}"
            ),
            inline=False,
        )

        # Disable both buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

# ============================================================
# DM FALLBACK APPEAL BUTTON
# ============================================================

class DMAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Open Appeal Form",
        style=discord.ButtonStyle.primary,
        custom_id="sakura_dm_appeal",
    )
    async def open_appeal_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(
            BanAppealModal()
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready() -> None:
    print(
        f"Logged in as {bot.user} "
        f"(ID: {bot.user.id})",
        flush=True,
    )


# ============================================================
# WEBSITE APPEAL -> STAFF APPEAL MESSAGE
# ============================================================

@bot.event
async def on_message(message: discord.Message):

    # Debug: prove the bot is receiving messages
    print(
        f"[APPEAL DEBUG] Message received | "
        f"channel={message.channel.id} | "
        f"webhook={message.webhook_id} | "
        f"embeds={len(message.embeds)}",
        flush=True
    )

    # Ignore the bot's own messages
    if message.author == bot.user:
        return

    # Only watch the appeal channel
    if message.channel.id == APPEAL_CHANNEL_ID:

        # Only process webhook messages
        if message.webhook_id is not None:

            print(
                "[APPEAL DEBUG] Webhook message detected!",
                flush=True
            )

            if message.embeds:

                embed = message.embeds[0]

                user_id = None

                # Find the User field
                for field in embed.fields:

                    if field.name == "👤 User":

                        print(
                            f"[APPEAL DEBUG] User field: {field.value}",
                            flush=True
                        )

                        try:
                            # The ID is between ` `
                            user_id = int(
                                field.value.split("`")[1]
                            )

                        except (IndexError, ValueError):
                            print(
                                "[APPEAL DEBUG] Could not read user ID!",
                                flush=True
                            )

                        break

                if user_id is not None:

                    print(
                        f"[APPEAL DEBUG] Appeal belongs to {user_id}",
                        flush=True
                    )

                    # Make a NEW staff embed
                    staff_embed = discord.Embed(
                        title="📨 New Ban Appeal",
                        color=discord.Color.blurple(),
                        timestamp=discord.utils.utcnow(),
                    )

                    for field in embed.fields:
                        staff_embed.add_field(
                            name=field.name,
                            value=field.value,
                            inline=field.inline,
                        )

                    staff_embed.set_footer(
                        text="Sakura • Lucent Moderation • Pending"
                    )

                    # SEND THE BUTTON VERSION FIRST
                    try:
                        print(
                            "[APPEAL DEBUG] Creating staff appeal view...",
                            flush=True
                        )

                        staff_view = BanAppealStaffView(user_id)

                        print(
                            "[APPEAL DEBUG] View created successfully!",
                            flush=True
                        )

                        await message.channel.send(
                            embed=staff_embed,
                            view=staff_view,
                        )

                        print(
                            "[APPEAL DEBUG] Staff appeal + buttons sent!",
                            flush=True
                        )

                    except Exception as e:
                        print(
                            f"[APPEAL DEBUG] ❌ FAILED: "
                            f"{type(e).__name__}: {e}",
                            flush=True
                        )

                    # Delete the original webhook message
                    try:
                        await message.delete()

                    except discord.HTTPException:
                        pass

    await bot.process_commands(message)


# ============================================================
# EXECUTE
# ============================================================

@bot.command()
async def execute(
    ctx: commands.Context,
    member: discord.Member,
) -> None:

    if not await ensure_guild(ctx):
        return

    if not await ensure_owner(ctx):
        return

    if member.id in PROTECTED_USER_IDS:
        await ctx.send(
            "❌ That user cannot be executed."
        )
        return

    bot_member = ctx.guild.me

    if bot_member is None:
        await ctx.send(
            "❌ I couldn't determine my server permissions."
        )
        return

    roles_to_remove = [
        role
        for role in member.roles
        if (
            role != ctx.guild.default_role
            and role.id not in EXCLUDED_ROLE_IDS
            and role < bot_member.top_role
        )
    ]

    if not roles_to_remove:
        await ctx.send(
            f"⚠️ {member.mention} has no roles I can remove."
        )
        return

    backups = load_backups()

    backups.setdefault(
        str(ctx.guild.id),
        {}
    )

    backups[str(ctx.guild.id)][str(member.id)] = [
        role.id
        for role in roles_to_remove
    ]

    save_backups(backups)

    try:
        await member.remove_roles(
            *roles_to_remove,
            reason=(
                f"?execute used by "
                f"{ctx.author} ({ctx.author.id})"
            ),
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to remove those roles."
        )
        return

    except discord.HTTPException:
        await ctx.send(
            "❌ Discord rejected the role update. Try again."
        )
        return

    embed = discord.Embed(
        title="✅ Execution Successful",
        description=(
            f"**{member.mention}** was executed successfully."
        ),
        color=discord.Color.red(),
    )

    embed.add_field(
        name="Roles removed",
        value=f"`{len(roles_to_remove)}` role(s)",
        inline=True,
    )

    embed.add_field(
        name="Executed by",
        value=ctx.author.mention,
        inline=True,
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


# ============================================================
# REVERSE EXECUTION
# ============================================================

@bot.command()
async def reverseexecution(
    ctx: commands.Context,
    member: discord.Member,
) -> None:

    if not await ensure_guild(ctx):
        return

    if not await ensure_owner(ctx):
        return

    bot_member = ctx.guild.me

    if bot_member is None:
        await ctx.send(
            "❌ I couldn't determine my server permissions."
        )
        return

    backups = load_backups()

    saved_role_ids = (
        backups
        .get(str(ctx.guild.id), {})
        .get(str(member.id))
    )

    if not saved_role_ids:
        await ctx.send(
            f"⚠️ No saved roles were found for {member.mention}."
        )
        return

    roles_to_restore = [
        role
        for role_id in saved_role_ids
        if (
            role := ctx.guild.get_role(role_id)
        ) is not None
        and role < bot_member.top_role
    ]

    if not roles_to_restore:
        await ctx.send(
            "⚠️ None of the saved roles can be restored."
        )
        return

    try:
        await member.add_roles(
            *roles_to_restore,
            reason=(
                f"?reverseexecution used by "
                f"{ctx.author} ({ctx.author.id})"
            ),
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to restore those roles."
        )
        return

    except discord.HTTPException:
        await ctx.send(
            "❌ Discord rejected the role update. Try again."
        )
        return

    del backups[str(ctx.guild.id)][str(member.id)]

    if not backups[str(ctx.guild.id)]:
        del backups[str(ctx.guild.id)]

    save_backups(backups)

    embed = discord.Embed(
        title="🔄 Execution Reversed",
        description=(
            f"Roles were restored for **{member.mention}**."
        ),
        color=discord.Color.green(),
    )

    embed.add_field(
        name="Roles restored",
        value=f"`{len(roles_to_restore)}` role(s)",
        inline=True,
    )

    embed.add_field(
        name="Reversed by",
        value=ctx.author.mention,
        inline=True,
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


# ============================================================
# ASSASSINATE
# ============================================================

@bot.command()
async def assassinate(
    ctx: commands.Context,
    member: discord.Member,
) -> None:

    if not await ensure_jmod(ctx):
        return

    if not await can_moderate(ctx, member):
        return

    case = create_case(
        guild_id=ctx.guild.id,
        user_id=member.id,
        moderator_id=ctx.author.id,
        action="Assassinate",
        reason="Member assassinated.",
    )

    dm_sent = True

    try:
        dm_embed = discord.Embed(
            title="💀 You Have Been Assassinated",
            description=(
                f"You have been removed from **{ctx.guild.name}** "
                "by a staff member."
            ),
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow(),
        )

        dm_embed.add_field(
            name="🛡️ Moderator",
            value=ctx.author.mention,
            inline=True,
        )

        dm_embed.add_field(
            name="📁 Case",
            value=f"`#{case['id']:03}`",
            inline=True,
        )

        if ctx.guild.icon:
            dm_embed.set_thumbnail(
                url=ctx.guild.icon.url
            )

        dm_embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        await member.send(
            embed=dm_embed
        )

    except discord.Forbidden:
        dm_sent = False

    try:
        await member.kick(
            reason=(
                f"Assassinate by "
                f"{ctx.author} ({ctx.author.id})"
            )
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to assassinate that member."
        )
        return

    except discord.HTTPException:
        await ctx.send(
            "❌ Discord rejected the kick request. Try again."
        )
        return

    embed = discord.Embed(
        title="💀 Assassination Completed",
        description=(
            f"{member.mention} has been assassinated "
            "and removed from the server."
        ),
        color=discord.Color.dark_red(),
        timestamp=discord.utils.utcnow(),
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.set_footer(
        text="Sakura • Lucent Moderation"
    )

    embed.add_field(
        name="👤 Member",
        value=f"`{member.id}`",
        inline=True,
    )

    embed.add_field(
        name="🛡️ Moderator",
        value=ctx.author.mention,
        inline=True,
    )

    embed.add_field(
        name="📁 Case",
        value=f"`#{case['id']:03}`",
        inline=True,
    )

    embed.add_field(
        name="📬 DM Sent",
        value=(
            "✅ Yes"
            if dm_sent
            else "❌ No (DMs closed)"
        ),
        inline=True,
    )

    await ctx.send(embed=embed)


# ============================================================
# DM-ONLY APPEAL COMMAND
# ============================================================

@bot.command()
async def appeal(
    ctx: commands.Context,
) -> None:

    # This command is only intended to be used
    # in Sakura's DMs.
    if ctx.guild is not None:
        await ctx.send(
            "❌ Please DM Sakura and use `+appeal` there."
        )
        return

    await ctx.send(
        "📨 **Ban Appeal**\n\n"
        "Click the button below to open the appeal form.",
        view=DMAppealView(),
    )


# ============================================================
# EXILE
# ============================================================

@bot.command()
async def exile(
    ctx: commands.Context,
    member: discord.Member,
    *,
    reason: str = "No reason provided.",
) -> None:

    if not await ensure_jmod(ctx):
        return

    if not await can_moderate(ctx, member):
        return

    case = create_case(
        guild_id=ctx.guild.id,
        user_id=member.id,
        moderator_id=ctx.author.id,
        action="Exile",
        reason=reason,
    )

    dm_sent = True

    # --------------------------------------------------------
    # SEND APPEAL DM BEFORE BAN
    # --------------------------------------------------------

    try:
        dm_embed = discord.Embed(
            title="🚪 You Have Been Exiled",
            description=(
                f"You have been exiled from **{ctx.guild.name}** "
                "and banned from the server."
            ),
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow(),
        )

        dm_embed.add_field(
            name="🛡️ Moderator",
            value=ctx.author.mention,
            inline=True,
        )

        dm_embed.add_field(
            name="📁 Case",
            value=f"`#{case['id']:03}`",
            inline=True,
        )

        dm_embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False,
        )

        if ctx.guild.icon:
            dm_embed.set_thumbnail(
                url=ctx.guild.icon.url
            )

       embed.set_footer(
           text="Sakura • Lucent Moderation"
            )

       dm_embed.add_field(
           name="🔗 Submit an Appeal",
           value="https://bakushin-bot.onrender.com/appeal",
           inline=False
           )

           await member.send(
           embed=dm_embed
           
           )
    except discord.Forbidden:
        dm_sent = False

    # --------------------------------------------------------
    # ACTUAL BAN
    # --------------------------------------------------------

    try:
        await member.ban(
            reason=(
                f"Exile by "
                f"{ctx.author} ({ctx.author.id}): {reason}"
            ),
            delete_message_days=0,
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to exile that member."
        )
        return

    except discord.HTTPException:
        await ctx.send(
            "❌ Discord rejected the exile request. Try again."
        )
        return

    # --------------------------------------------------------
    # EXILE COMPLETED MESSAGE
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🚪 Exile Completed",
        description=(
            f"{member.mention} has been exiled "
            "and banned from the server."
        ),
        color=discord.Color.dark_red(),
        timestamp=discord.utils.utcnow(),
    )

    embed.set_footer(
        text="Sakura • Lucent Moderation"
    )

    embed.add_field(
        name="👤 Member",
        value=f"`{member.id}`",
        inline=True,
    )

    embed.add_field(
        name="🛡️ Moderator",
        value=ctx.author.mention,
        inline=True,
    )

    embed.add_field(
        name="📁 Case",
        value=f"`#{case['id']:03}`",
        inline=True,
    )

    embed.add_field(
        name="📝 Reason",
        value=reason,
        inline=False,
    )

    embed.add_field(
        name="📬 DM Sent",
        value=(
            "✅ Yes"
            if dm_sent
            else "❌ No (DMs closed)"
        ),
        inline=True,
    )

    await ctx.send(embed=embed)


# ============================================================
# UNEXILE
# ============================================================

@bot.command()
async def unexile(
    ctx: commands.Context,
    user_id: int,
) -> None:

    if not await ensure_jmod(ctx):
        return

    try:
        user = await bot.fetch_user(user_id)

    except discord.NotFound:
        await ctx.send(
            "❌ I couldn't find a Discord user with that ID."
        )
        return

    try:
        await ctx.guild.unban(
            user,
            reason=(
                f"Unexile by "
                f"{ctx.author} ({ctx.author.id})"
            ),
        )

    except discord.NotFound:
        await ctx.send(
            "❌ That user isn't currently banned."
        )
        return

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to unban that user."
        )
        return

    except discord.HTTPException:
        await ctx.send(
            "❌ Discord rejected the unban request. Try again."
        )
        return

    embed = discord.Embed(
        title="🔓 Exile Reversed",
        description=(
            f"**{user}** has been unexiled and can now rejoin "
            f"**{ctx.guild.name}**."
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    embed.set_footer(
        text="Sakura • Lucent Moderation"
    )

    embed.add_field(
        name="👤 User",
        value=f"`{user.id}`",
        inline=True,
    )

    embed.add_field(
        name="🛡️ Moderator",
        value=ctx.author.mention,
        inline=True,
    )

    await ctx.send(embed=embed)


# ============================================================
# SAY
# ============================================================

@bot.command()
async def say(
    ctx: commands.Context,
    *,
    message: str,
) -> None:

    if not await ensure_guild(ctx):
        return

    if not await ensure_staff(ctx):
        return

    try:
        await ctx.message.delete()

    except discord.Forbidden:
        pass

    await ctx.send(message)


# ============================================================
# LEVEL
# ============================================================

@bot.command()
async def level(
    ctx: commands.Context,
):
    await ctx.send(
        f"Your staff level is "
        f"**{get_staff_level(ctx.author)}**."
    )


# ============================================================
# COMMAND ERRORS
# ============================================================

@bot.event
async def on_command_error(
    ctx: commands.Context,
    error: commands.CommandError,
) -> None:

    if isinstance(
        error,
        commands.MissingRequiredArgument,
    ):
        usage = get_usage(ctx.command.name)

        embed = discord.Embed(
            title="🌸 Incorrect Command Usage",
            description=(
                "❌ You used this command incorrectly.\n\n"
                f"📌 **Usage**\n"
                f"{usage}"
            ),
            color=discord.Color.from_rgb(
                255,
                170,
                190,
            ),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        await ctx.send(embed=embed)
        return

    if isinstance(
        error,
        commands.MemberNotFound,
    ):
        usage = get_usage(ctx.command.name)

        embed = discord.Embed(
            title="🌸 User Not Found",
            description=(
                "❌ I couldn't find that member.\n\n"
                f"📌 **Usage**\n"
                f"{usage}"
            ),
            color=discord.Color.from_rgb(
                255,
                170,
                190,
            ),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        await ctx.send(embed=embed)
        return

    if isinstance(
        error,
        commands.CommandNotFound,
    ):
        embed = discord.Embed(
            title="🌸 Unknown Command",
            description=(
                "❌ I don't recognize that command.\n\n"
                "Use `+help` to see the available commands."
            ),
            color=discord.Color.from_rgb(
                255,
                170,
                190,
            ),
            timestamp=discord.utils.utcnow(),
        )

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        await ctx.send(embed=embed)
        return

    print(
        f"COMMAND ERROR: "
        f"{type(error).__name__}: {error}",
        flush=True,
    )

    await ctx.send(
        f"❌ **Command Error**\n"
        f"`{type(error).__name__}: {error}`"
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    await bot.load_extension(
        "commands.staff"
    )

    # Register both persistent views BEFORE
    # starting the bot.
    bot.add_view(
        BanAppealView()
    )

    bot.add_view(
        DMAppealView()
    )

    print(
        "🔥 BAN APPEAL VIEWS REGISTERED",
        flush=True,
    )

    print(
        "🔥 BAN APPEAL BUTTON:",
        [
            (
                type(item).__name__,
                item.custom_id,
            )
            for item in BanAppealView().children
        ],
        flush=True,
    )

    print(
        "🔥 DM APPEAL BUTTON:",
        [
            (
                type(item).__name__,
                item.custom_id,
            )
            for item in DMAppealView().children
        ],
        flush=True,
    )

    await bot.start(TOKEN)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
