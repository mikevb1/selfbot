import asyncio

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
    await bot.edit_message(ctx.message, ctx.message.content.replace('$mybot', 'https://github.com/mikevb1/discordbot', 1))


@bot.event
async def on_message(msg):
    if msg.author.id == bot.user.id:
        if any(h in msg.content for h in ('http://', 'https://')):
            words = []
            for ind, word in enumerate(msg.content.split()):
                if word.startswith(('http://', 'https://')):
                    words.append('<{}>'.format(word))
                else:
                    words.append(word)
            await asyncio.sleep(1)
            msg = await bot.edit_message(msg, ' '.join(words))
        await bot.process_commands(msg)


@bot.event
async def on_command_error(exc, ctx):
    print(exc)


if __name__ == '__main__':
    token = 'mfa.Kq1CHhyfs0J6TP-uSyOw_x6v_n5NGBdo1n0nnlssZwLwi517-EzYZvm1Le-qWT-WccA4csHj5n8efTwDTV5N'
    bot.run(token, bot=False)
