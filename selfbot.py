#!/usr/bin/env python3.6
import traceback
import asyncio
import logging
import signal
import json
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
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    async def on_ready(self):
        await self.change_presence(status=discord.Status.invisible)
        if config.get('error_channel'):
            guild_id, channel_id = map(int, config['error_channel'].split('/'))
            guild = self.get_guild(guild_id)
            self.error_channel = guild.get_channel(channel_id)
        else:
            self.error_channel = None

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
        if self.error_channel:
            await self.error_channel.send('\n'.join((msg, tb)))
        logging.error('\n'.join((msg, tb)))

    def logout_(self):
        self.loop.create_task(self.logout())


if __name__ == '__main__':
    config = json.load(open('config.json'))
    bot = SelfBot(config=config, command_prefix='$', self_bot=True)

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


    bot.loop.add_signal_handler(signal.SIGTERM, bot.logout_)
    bot.run(config.pop('token'), bot=False)
    sys.exit(getattr(bot, 'exit_status', 0))
