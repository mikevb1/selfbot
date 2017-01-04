from discord.ext import commands
import discord


class Management:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, *, member: discord.Member):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await ctx.message.guild.kick(member)
        except:
            await ctx.message.edit(ctx.message.content + ' \N{THUMBS DOWN SIGN}')
        else:
            await ctx.message.edit(ctx.message.content + ' \N{THUMBS UP SIGN}')

    @commands.command(no_pm=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, *, member: discord.Member):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await ctx.message.guild.ban(member)
        except:
            await ctx.message.edit(ctx.message.content + ' \N{THUMBS DOWN SIGN}')
        else:
            await ctx.message.edit(ctx.message.content + ' \N{THUMBS UP SIGN}')


def setup(bot):
    bot.add_cog(Management(bot))
