from math import ceil
import unicodedata
import logging
import random
import json

from discord.ext import commands
import discord
import zenhan
import dice


UNIURL = "http://www.fileformat.info/info/unicode/char/{}/index.htm"


def hex_or_rgb(arg):
    s = arg.split(' ')
    if len(s) == 1:
        color = s[0]
        if len(color) == 6:
            color = f'0x{color}'
        elif len(color) == 7:
            color = color.replace('#', '0x')
        try:
            return discord.Color(int(color, 0))
        except ValueError:
            raise commands.BadArgument('A single argument must be passed as hex (`0x7289DA`, `#7289DA`, `7289DA`)')
    elif len(s) == 3:
        try:
            rgb = [*map(int, s)]
        except ValueError:
            raise commands.BadArgument('Three arguments must be passed as RGB (`114 137 218`, `153 170 181`)')
        if any(c < 0 or c > 255 for c in rgb):
            raise commands.BadArgument('RGB colors must be in the range `[0, 255]`')
        return discord.Color.from_rgb(*rgb)
    raise commands.BadArgument('You must pass 1 (hex) or 3 (RGB) arguments.')


class Extra:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.message.edit(content='Pong!')

    @commands.command(name='roll')
    async def roll_dice(self, ctx, roll: dice.roll = None):
        """In format CdS, rolls C dice each with S sides.

        If C is neglected, it will be assumed to mean 1 die.

        Advanced notation:
            * add "t" to get the total of the rolls : 2d6t   -> 9
            * add "s" to sort the rolls             : 2d6s   -> 2, 4
            * add "^X" to keep the highest X rolls  : 10d6^3 -> 4, 4, 5
            * add "vX" to keep the lowest X rolls   : 10d6v3 -> 1, 2, 2

        You can also specify a list of dice to roll. "1d6 2d20 d12"

        This command also handles basic arithmetic operations (/*+-)
        """
        if roll is None:
            roll = random.randint(1, 6)
        elif isinstance(roll, list):
            roll = ', '.join(map(str, roll))
        await ctx.message.edit(content=roll)

    @commands.command()
    async def flip(self, ctx):
        side = None
        rand = random.randint(0, 6000)
        if rand:
            if rand % 2:
                side = 'Yes.'
            else:
                side = 'No.'
        else:  # 1/6001 chance of being edge
            side = 'Maybe.'
        await ctx.message.edit(content=side)

    @commands.command()
    async def choose(self, ctx, *options):
        await ctx.message.edit(content=random.choice(options))

    @commands.command()
    async def charinfo(self, ctx, *, chars):
        """Get unicode character info."""
        if not chars:
            return
        chars = unicodedata.normalize('NFC', chars)
        if len(chars) > 25:
            return
        embed = discord.Embed()
        for char in chars:
            uc = hex(ord(char))[2:]
            name = unicodedata.name(char, 'unknown')
            if name in {'SPACE', 'EM QUAD', 'EN QUAD'} or ' SPACE' in name:
                char = '" "'
            short = len(uc) <= 4
            code = f"\\{'u' if short else 'U'}{uc.lower().zfill(4 if short else 8)}"
            embed.add_field(name=name, value=f'{char} [{code}]({UNIURL.format(uc)})')
        await ctx.message.edit(content='', embed=embed)

    @commands.command()
    async def fw(self, ctx, *, chars):
        """Make full-width meme text."""
        await ctx.message.edit(content=zenhan.h2z(chars))

    @commands.command()
    async def color(self, ctx, *, color: hex_or_rgb):
        """Show color from hex or RGB."""
        em = discord.Embed(color=color, description=f'Hex: {color}\nRGB: {color.to_rgb()}')
        await ctx.message.edit(content='', embed=em)

    @commands.command()
    async def team(self, ctx, members=0, teams=2, *exclude):
        """Randomise teams of discord members.

        All members must be in the same voice channel.
        [members] = number of members per team, 0 to split evenly
        [teams] = number of teams
        [exclude] = space-separated list of member ids to exclude
        """
        names = [m.mention for m in ctx.message.author.voice.channel.members
                 if m.id not in exclude]
        random.shuffle(names)
        members = members or ceil(len(names) / teams)
        embed = discord.Embed()
        for team in range(teams):
            embed.add_field(name=f'Team {team + 1}',
                            value='\n'.join(names[team::teams]) or 'None')
        await ctx.message.edit(content='', embed=embed)

    @commands.command()
    async def shared(self, ctx, member: discord.Member = None):
        if member is None:
            async for m in ctx.history():
                if m.author != ctx.author:
                    member = m.author
                    break
        mid = member.id
        guilds = [g.name for g in self.bot.guilds if g.get_member(mid)]
        await ctx.message.edit(content=', '.join(f'"{guild}"' for guild in guilds))


def setup(bot):
    bot.add_cog(Extra(bot))
