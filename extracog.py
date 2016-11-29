import unicodedata
import random

from discord.ext import commands
import zenhan
import dice


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
        msg = []
        chars = unicodedata.normalize('NFC', chars)
        for char in chars:
            uc = hex(ord(char))[2:]
            msg.append('{char} - `{char}` - {name}'.format(
                name=unicodedata.name(char, '`\\U%s`' % uc.upper()), char=char))
        await self.bot.edit_message(ctx.message, '\n'.join(msg))

    @commands.command(pass_context=True)
    async def fw(self, ctx, *, chars):
        """Make full-width meme text."""
        await self.bot.edit_message(ctx.message, zenhan.h2z(chars))


def setup(bot):
    bot.add_cog(Extra(bot))
