#!/usr/bin/env python3.6
from collections import namedtuple
import traceback
import asyncio
import logging
import signal
import sys

from discord.ext import commands
import aiohttp
import discord

from replcog import UPPER_PATH, exception_signature
import config

logging.basicConfig(level=logging.WARNING)

# stolen from R.Danny
try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


Response = namedtuple('Response', 'status data')


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, status=discord.Status.invisible, **kwargs)
        self.http_ = aiohttp.ClientSession(
            loop=self.loop,
            headers={'User-Agent': 'Discord Selfbot'})

    async def on_ready(self):
        if config.error_channel:
            guild_id, channel_id = map(int, config.error_channel.split('/'))
            guild = self.get_guild(guild_id)
            self.error_channel = guild.get_channel(channel_id)
        else:
            self.error_channel = None

    async def on_resumed(self):
        me = self.guilds[0].me
        await self.change_presence(game=me.game, status=discord.Status.invisible)

    async def on_message(self, msg):
        if msg.author.id == self.user.id:
            await self.process_commands(msg)

    async def on_command_error(self, ctx, exc):
        """Emulate default on_command_error and add server + channel info."""
        if hasattr(ctx.command, 'on_error') or isinstance(exc, commands.CommandNotFound):
            return
        logging.warning(f'Ignoring exception in command {ctx.command}')
        msg = ctx.message.content
        msg = msg.format(ctx.message)
        exc = getattr(exc, 'original', exc)
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)).replace(UPPER_PATH, '...')
        if self.error_channel:
            await self.error_channel.send('\n'.join((msg, tb)))
        logging.error('\n'.join((msg, tb)))

    def logout_(self):
        self.loop.create_task(self.logout())

    async def _request(self, url, type_='json', *, timeout=10, method='GET', **kwargs):
        if type_ not in {'json', 'read', 'text'}:
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        async with self.http_.request(method, url, timeout=timeout, **kwargs) as resp:
            data = None
            try:
                data = await getattr(resp, type_)()
            except:
                logging.exception(f'Failed getting type {type_} from "{url}".')
            return Response(resp.status, data)

    async def request(self, *args, ignore_timeout=True, **kwargs):
        """Utility request function.

        type_ is the method to get data from response
        """
        if ignore_timeout:
            try:
                return await self._request(*args, **kwargs)
            except asyncio.TimeoutError:
                return Response(None, None)
        else:
            return await self._request(*args, **kwargs)


if __name__ == '__main__':
    bot = Bot(command_prefix='$', self_bot=True)

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
            await ctx.message.edit(content=msg)
        else:
            await ctx.message.delete()

    bot.loop.add_signal_handler(signal.SIGTERM, bot.logout_)
    bot.run(config.token, bot=False)
    sys.exit(getattr(bot, 'exit_status', 0))
