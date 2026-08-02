import discord
from discord.ext import commands
from datetime import datetime, timedelta

from utils.permissions import ensure_jmod, ensure_mod, get_staff_level
from utils.moderation import can_moderate
from utils.member import get_member
from utils.cases import create_case, get_user_cases, delete_case
from utils.duration import parse_duration


class WarningDeleteView(discord.ui.View):
    def __init__(self, guild_id: int, case_id: int, author_id: int):
        super().__init__(timeout=60)

        self.guild_id = guild_id
        self.case_id = case_id
        self.author_id = author_id

    @discord.ui.button(
        label="Delete Warning",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def delete_warning(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the staff member who opened this warning can delete it.",
                ephemeral=True
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This can only be used inside the server.",
                ephemeral=True
            )
            return

        if get_staff_level(interaction.user) < 2:
            await interaction.response.send_message(
                "❌ You need to be Mod or higher to delete warnings.",
                ephemeral=True
            )
            return
        deleted = delete_case(
            guild_id=self.guild_id,
            case_id=self.case_id
        )

        if not deleted:
            await interaction.response.send_message(
                "❌ That warning no longer exists.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🗑️ Warning Deleted",
            description=(
                f"Warning **#{self.case_id:03}** has been permanently deleted."
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(text="Sakura • Lucent Moderation")

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        self.stop()


class WarningSelect(discord.ui.Select):
    def __init__(self, cases, guild_id: int, author_id: int):
        self.cases = cases
        self.guild_id = guild_id
        self.author_id = author_id

        options = []

        for case in cases[:25]:
            reason = case["reason"]

            if len(reason) > 75:
                reason = reason[:72] + "..."

            options.append(
                discord.SelectOption(
                    label=f"Case #{case['id']:03}",
                    description=reason,
                    value=str(case["id"]),
                    emoji="⚠️"
                )
            )

        super().__init__(
            placeholder="Select a warning to manage...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ You cannot manage this warning panel.",
                ephemeral=True
            )
            return

        case_id = int(self.values[0])

        case = next(
            (case for case in self.cases if case["id"] == case_id),
            None
        )

        if case is None:
            await interaction.response.send_message(
                "❌ That warning could not be found.",
                ephemeral=True
            )
            return

        moderator = interaction.guild.get_member(case["moderator_id"])

        moderator_text = (
            moderator.mention
            if moderator
            else f"`{case['moderator_id']}`"
        )

        timestamp = int(
            datetime.fromisoformat(case["timestamp"]).timestamp()
        )

        embed = discord.Embed(
            title=f"⚠️ Warning #{case['id']:03}",
            description="Review this warning before deleting it.",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📝 Reason",
            value=case["reason"],
            inline=False
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=moderator_text,
            inline=True
        )

        embed.add_field(
            name="📅 Date",
            value=f"<t:{timestamp}:F>",
            inline=True
        )

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        view = WarningDeleteView(
            guild_id=self.guild_id,
            case_id=case_id,
            author_id=self.author_id
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


class WarningSelectView(discord.ui.View):
    def __init__(self, cases, guild_id: int, author_id: int):
        super().__init__(timeout=60)

        self.add_item(
            WarningSelect(
                cases=cases,
                guild_id=guild_id,
                author_id=author_id
            )
        )


class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def warn(self, ctx, user: str, *, reason: str):
        member = await get_member(ctx.guild, user)

        if member is None:
            await ctx.send("❌ I couldn't find that user.")
            return

        if not await ensure_jmod(ctx):
            return

        if not await can_moderate(ctx, member):
            return

        case = create_case(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action="Warn",
            reason=reason,
        )

        embed = discord.Embed(
            title="⚠️ Warning Issued",
            description=(
                f"{member.mention} has received a warning.\n"
                "Please review the reason below."
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=f"{ctx.author.mention}\n`{ctx.author.id}`",
            inline=True
        )

        embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="📁 Case",
            value=f"`#{case['id']:03}`",
            inline=True
        )

        dm_sent = True

        try:
            dm_embed = discord.Embed(
                title="⚠️ You Received a Warning",
                description=(
                    f"You have received a warning in **{ctx.guild.name}**.\n\n"
                    "Please make sure you follow the server rules to avoid "
                    "further moderation action."
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )

            dm_embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )

            dm_embed.add_field(
                name="🛡️ Moderator",
                value=ctx.author.mention,
                inline=True
            )

            dm_embed.add_field(
                name="📁 Case",
                value=f"`#{case['id']:03}`",
                inline=True
            )

            if ctx.guild.icon:
                dm_embed.set_thumbnail(url=ctx.guild.icon.url)

            dm_embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await member.send(embed=dm_embed)

        except discord.Forbidden:
            dm_sent = False

        embed.add_field(
            name="📬 DM Sent",
            value="✅ Yes" if dm_sent else "❌ No (DMs closed)",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def warnings(self, ctx, user: str):
        member = await get_member(ctx.guild, user)

        if member is None:
            await ctx.send("❌ I couldn't find that user.")
            return

        if not await ensure_jmod(ctx):
            return

        cases = [
            case
            for case in get_user_cases(ctx.guild.id, member.id)
            if case["action"].lower() == "warn"
        ]

        if not cases:
            embed = discord.Embed(
                title="📋 Warning History",
                description=f"{member.mention} has no warnings.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Sakura • Lucent Moderation")

            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📋 Warning History",
            description=(
                f"Warning history for {member.mention}\n"
                f"Total warnings: **{len(cases)}**"
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        for case in cases[:10]:
            moderator = ctx.guild.get_member(case["moderator_id"])

            moderator_text = (
                moderator.mention
                if moderator
                else f"`{case['moderator_id']}`"
            )

            timestamp = int(
                datetime.fromisoformat(case["timestamp"]).timestamp()
            )

            embed.add_field(
                name=f"⚠️ Case #{case['id']:03}",
                value=(
                    f"**Reason:** {case['reason']}\n"
                    f"**Moderator:** {moderator_text}\n"
                    f"**Date:** <t:{timestamp}:F>"
                ),
                inline=False
            )

        embed.set_footer(
            text=(
                "Sakura • Lucent Moderation • "
                "Select a warning below to manage it"
            )
        )

        view = WarningSelectView(
            cases=cases,
            guild_id=ctx.guild.id,
            author_id=ctx.author.id
        )

        await ctx.send(
            embed=embed,
            view=view
        )

    @commands.command()
    async def hush(
        self,
        ctx,
        user: str,
        duration: str,
        *,
        reason: str = "No reason provided."
    ):
        member = await get_member(ctx.guild, user)

        if member is None:
            await ctx.send("❌ I couldn't find that user.")
            return

        if not await ensure_jmod(ctx):
            return

        if not await can_moderate(ctx, member):
            return

        duration_seconds = parse_duration(duration)

        if duration_seconds is None:
            embed = discord.Embed(
                title="❌ Invalid Duration",
                description=(
                    "Please provide a valid duration.\n\n"
                    "**Examples:**\n"
                    "`10m` • `1h` • `2d` • `1h30m`"
                ),
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )

            embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await ctx.send(embed=embed)
            return

        if duration_seconds > 28 * 24 * 60 * 60:
            embed = discord.Embed(
                title="❌ Duration Too Long",
                description="A Discord timeout cannot exceed **28 days**.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )

            embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await ctx.send(embed=embed)
            return

        case = create_case(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action="Hush",
            reason=reason,
            duration=duration,
        )

        until = discord.utils.utcnow() + timedelta(
             seconds=duration_seconds
        )

        try:
            await member.timeout(
                until,
                reason=f"Hush by {ctx.author} ({ctx.author.id}): {reason}"
            )
        except discord.Forbidden:
            await ctx.send(
                "❌ I don't have permission to hush that member."
            )
            return
        except discord.HTTPException:
            await ctx.send(
                "❌ Discord rejected the timeout. Try again."
            )
            return

        embed = discord.Embed(
            title="🤫 Member Hushed",
            description=(
                f"{member.mention} has been hushed.\n"
                "They will not be able to communicate until the timeout ends."
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=f"{ctx.author.mention}\n`{ctx.author.id}`",
            inline=True
        )

        embed.add_field(
            name="⏱️ Duration",
            value=f"`{duration}`",
            inline=True
        )

        embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="📁 Case",
            value=f"`#{case['id']:03}`",
            inline=True
        )

        embed.add_field(
            name="⏰ Ends",
            value=f"<t:{int(until.timestamp())}:R>",
            inline=True
        )

        dm_sent = True

        try:
            dm_embed = discord.Embed(
                title="🤫 You Have Been Hushed",
                description=(
                    f"You have been hushed in **{ctx.guild.name}**.\n\n"
                    "You cannot communicate in the server until the "
                    "timeout expires."
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )

            dm_embed.add_field(
                name="⏱️ Duration",
                value=f"`{duration}`",
                inline=True
            )

            dm_embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )

            dm_embed.add_field(
                name="🛡️ Moderator",
                value=ctx.author.mention,
                inline=True
            )

            dm_embed.add_field(
                name="📁 Case",
                value=f"`#{case['id']:03}`",
                inline=True
            )

            if ctx.guild.icon:
                dm_embed.set_thumbnail(url=ctx.guild.icon.url)

            dm_embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await member.send(embed=dm_embed)

        except discord.Forbidden:
            dm_sent = False

        embed.add_field(
            name="📬 DM Sent",
            value="✅ Yes" if dm_sent else "❌ No (DMs closed)",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def unhush(self, ctx, user: str):
        member = await get_member(ctx.guild, user)

        if member is None:
            await ctx.send("❌ I couldn't find that user.")
            return

        if not await ensure_jmod(ctx):
            return

        if not await can_moderate(ctx, member):
            return

        if member.timed_out_until is None:
            embed = discord.Embed(
                title="ℹ️ Member Not Hushed",
                description=f"{member.mention} is not currently hushed.",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )

            embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await ctx.send(embed=embed)
            return

        case = create_case(
            guild_id=ctx.guild.id,
            user_id=member.id,
            moderator_id=ctx.author.id,
            action="Unhush",
            reason="Hush removed manually.",
        )

        try:
            await member.timeout(
                None,
                reason=f"Unhush by {ctx.author} ({ctx.author.id})"
            )
        except discord.Forbidden:
            await ctx.send(
                "❌ I don't have permission to remove that timeout."
            )
            return
        except discord.HTTPException:
            await ctx.send(
                "❌ Discord rejected the timeout removal. Try again."
            )
            return

        embed = discord.Embed(
            title="🔊 Member Unhushed",
            description=(
                f"{member.mention} has been unhushed.\n"
                "Their server communication has been restored."
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(
            text="Sakura • Lucent Moderation"
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=f"{ctx.author.mention}\n`{ctx.author.id}`",
            inline=True
        )

        embed.add_field(
            name="📁 Case",
            value=f"`#{case['id']:03}`",
            inline=True
        )

        dm_sent = True

        try:
            dm_embed = discord.Embed(
                title="🔊 Your Hush Has Been Removed",
                description=(
                    f"Your hush in **{ctx.guild.name}** has been removed.\n\n"
                    "You can communicate in the server again."
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            dm_embed.add_field(
                name="🛡️ Moderator",
                value=ctx.author.mention,
                inline=True
            )

            dm_embed.add_field(
                name="📁 Case",
                value=f"`#{case['id']:03}`",
                inline=True
            )

            if ctx.guild.icon:
                dm_embed.set_thumbnail(url=ctx.guild.icon.url)

            dm_embed.set_footer(
                text="Sakura • Lucent Moderation"
            )

            await member.send(embed=dm_embed)

        except discord.Forbidden:
            dm_sent = False

        embed.add_field(
            name="📬 DM Sent",
            value="✅ Yes" if dm_sent else "❌ No (DMs closed)",
            inline=True
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Staff(bot))