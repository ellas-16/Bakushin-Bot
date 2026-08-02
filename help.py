import discord
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            title="🌸 Sakura Bot",
            description="**Available Commands**",
            color=discord.Color.from_rgb(144, 238, 144)
        )

        embed.add_field(
            name="👑 Owner Commands",
            value=(
                "`+execute @user`\n"
                "Removes all removable roles.\n\n"

                "`+reverseexecution @user`\n"
                "Restores removed roles.\n\n"

                "`+assassinate @user`\n"
                "Kicks the mentioned user."
            ),
            inline=False
        )

        embed.add_field(
            name="🔑 Staff Key",
            value=(
                "`+say <message>`\n"
                "Makes the bot say your message."
            ),
            inline=False
        )

        embed.set_footer(text="Sakura Bot • Made by Ellas")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))