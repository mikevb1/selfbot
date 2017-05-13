from discord.ext import commands
import discord


class Management:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['kill', 'restart'])
    async def exit(self, ctx, code: int = None):
        """Restart/kill bot."""
        codes = {'restart': 2, 'kill': 1}
        code = codes.get(ctx.invoked_with, code)
        if code is None:
            await ctx.message.edit(content='Not exiting.')
            await asyncio.sleep(3)
            await ctx.message.delete()
            return
        await ctx.message.delete()
        self.bot.exit_status = code
        await self.bot.logout()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await ctx.message.guild.kick(member, reason=reason)
        except:
            await ctx.message.edit(content=f'{ctx.message.content} \N{THUMBS DOWN SIGN}')
        else:
            await ctx.message.edit(content=f'{ctx.message.content} \N{THUMBS UP SIGN}')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await ctx.message.guild.ban(member, reason=reason)
        except:
            await ctx.message.edit(content=f'{ctx.message.content} \N{THUMBS DOWN SIGN}')
        else:
            await ctx.message.edit(content=f'{ctx.message.content} \N{THUMBS UP SIGN}')


def setup(bot):
    bot.add_cog(Management(bot))
