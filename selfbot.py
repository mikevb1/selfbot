#!/usr/bin/env python3.6
import traceback
import asyncio
import logging
import signal
import sys

from discord.ext import commands
import discord

from replcog import exception_signature

logging.basicConfig(level=logging.WARNING)

# stolen from R.Danny
try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class SelfBot(commands.Bot):
    async def on_ready(self):
        await self.change_presence(status=discord.Status.invisible)

    async def on_message(self, msg):
        if msg.author.id == self.user.id:
            await self.process_commands(msg)

    async def on_command_error(self, exc, ctx):
        """Emulate default on_command_error and add server + channel info."""
        if hasattr(ctx.command, 'on_error') or isinstance(exc, commands.CommandNotFound):
            return
        logging.warning(f'Ignoring exception in command {ctx.command}')
        if isinstance(ctx.message.channel, (discord.GroupChannel, discord.DMChannel)):
            msg = 'Message was "{0.content}" in {0.channel}.'
        else:
            msg = 'Message was "{0.content}" by {0.author} in "{0.channel}" on "{0.guild}".'
        msg = msg.format(ctx.message)
        exc = getattr(exc, 'original', exc)
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logging.error('\n'.join((msg, tb)))

    def _logout(self):
        self.loop.create_task(self.logout())


bot = SelfBot(command_prefix='$', self_bot=True)

for cog in {'test', 'repl', 'manage', 'extra'}:
    try:
        bot.load_extension(f'{cog}cog')
    except Exception as e:
        logging.error(f"Couldn't load {cog}\n{type(e).__name__}: {e}")


@bot.command()
async def reload(ctx, cog):
    try:
        bot.unload_extension(cog + 'cog')
        bot.load_extension(cog + 'cog')
    except Exception as e:
        msg = exception_signature()
        logging.error(msg)
        await bot.say(msg)
    else:
        await ctx.message.delete()


@bot.command()
async def mybot(ctx, *, text):
    await ctx.message.edit(content=ctx.message.content.replace('$mybot', 'https://github.com/mikevb1/discordbot', 1))


if __name__ == '__main__':
    token = 'mfa.dEzp4UE4goS2cRIdPCYXTxo0jA4K0VcDFWeWbKH8MD3uNL-oVsgN9p8SCc-1039rwUOXAN9TKKBqzdBcuxTr'
    bot.loop.add_signal_handler(signal.SIGTERM, bot._logout)
    bot.run(token, bot=False)
    sys.exit(getattr(bot, 'exit_status', 0))
