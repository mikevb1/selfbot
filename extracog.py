from math import ceil
import unicodedata
import random

from discord.ext import commands
import discord
import zenhan
import dice


UNIURL = "http://www.fileformat.info/info/unicode/char/{}/index.htm"


class Extra:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        await self.bot.edit_message(ctx.message, 'Pong!')

    @commands.command(pass_context=True, name='roll')
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
        await self.bot.edit_message(ctx.message, roll)

    @commands.command(pass_context=True)
    async def flip(self, ctx):
        """Flip any number of coins."""
        side = None
        rand = random.randint(0, 6000)
        if rand:
            if rand % 2:
                side = 'Yes.'
            else:
                side = 'No.'
        else:  # 1/6001 chance of being edge
            side = 'Maybe.'
        await self.bot.edit_message(ctx.message, side)

    @commands.command(pass_context=True)
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
            if len(uc) <= 4:
                code = '`\\u%s`' % uc.lower().zfill(4)
            else:
                code = '`\\U%s`' % uc.upper().zfill(8)
            embed.add_field(name=name,
                            value='{char} [{code}]({url})'.format(
                                char=char, code=code, url=UNIURL.format(uc)))
        await self.bot.delete_message(ctx.message)
        await self.bot.say(embed=embed)

    @commands.command(pass_context=True)
    async def fw(self, ctx, *, chars):
        """Make full-width meme text."""
        await self.bot.edit_message(ctx.message, zenhan.h2z(chars))

    @commands.command(pass_context=True)
    async def team(self, ctx, members=0, teams=2, *exclude):
        """Randomise teams of discord members.

        All members must be in the same voice channel.
        [members] = number of members per team, 0 to split evenly
        [teams] = number of teams
        [exclude] = space-separated list of member ids to exclude
        """
        await self.bot.delete_message(ctx.message)
        names = [m.mention for m in ctx.message.author.voice_channel.voice_members
                 if m.id not in exclude]
        random.shuffle(names)
        members = members or ceil(len(names)/teams)
        embed = discord.Embed()
        for team in range(teams):
            embed.add_field(name='Team {}'.format(team + 1),
                            value='\n'.join(names[team::teams]) or 'None')
        await self.bot.say(embed=embed)


def setup(bot):
    bot.add_cog(Extra(bot))
