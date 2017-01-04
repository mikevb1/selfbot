import traceback
import asyncio
import logging

from discord.ext import commands
import discord

bot = commands.Bot(command_prefix='$', self_bot=True)

for cog in ('test', 'repl', 'manage', 'extra'):
    try:
        bot.load_extension(cog + 'cog')
    except Exception as e:
        print("Couldn't load {}\n{}: {}".format(cog, type(e).__name__, e))


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.invisible)


@bot.command()
async def reload(cog):
    try:
        bot.unload_extension(cog + 'cog')
        bot.load_extension(cog + 'cog')
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e))
        await bot.say("{}: {}".format(type(e).__name__, e))


@bot.command(pass_context=True)
async def mybot(ctx, *, text):
    await bot.edit_message(ctx.message, ctx.message.content.replace('$mybot', 'https://github.com/mikevb1/discordbot'))


@bot.event
async def on_message(msg):
    if msg.author.id == bot.user.id:
        await bot.process_commands(msg)


@bot.event
async def on_command_error(exc, ctx):
    """Emulate default on_command_error and add server + channel info."""
    if hasattr(ctx.command, 'on_error') or isinstance(exc, commands.CommandNotFound):
        return
    logging.warning('Ignoring exception in command {}'.format(ctx.command))
    if isinstance(ctx.message.channel, discord.PrivateChannel):
        if str(ctx.message.channel.type) == 'group':
            msg = 'Message was "{0.content}" in {0.channel}.'
        else:
            msg = 'Message was "{0.content}" in {0.channel}.'
    else:
        msg = 'Message was "{0.content}" in "{0.channel}" on "{0.server}".'
    msg = msg.format(ctx.message)

    exc = getattr(exc, 'original', exc)
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.error('\n'.join((msg, tb)))


if __name__ == '__main__':
    token = 'mfa.Kq1CHhyfs0J6TP-uSyOw_x6v_n5NGBdo1n0nnlssZwLwi517-EzYZvm1Le-qWT-WccA4csHj5n8efTwDTV5N'
    bot.run(token, bot=False)
