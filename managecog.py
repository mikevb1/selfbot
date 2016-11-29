from discord.ext import commands
import discord

class Management:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, *, member: discord.Member):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await self.bot.kick(member)
        except:
            await self.bot.say('\N{THUMBS DOWN SIGN}')
        else:
            await self.bot.say('\N{THUMBS UP SIGN}')

    @commands.command(no_pm=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, *, member: discord.Member):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await self.bot.ban(member)
        except:
            await self.bot.say('\N{THUMBS DOWN SIGN}')
        else:
            await self.bot.say('\N{THUMBS UP SIGN}')


def setup(bot):
    bot.add_cog(Management(bot))
