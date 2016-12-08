from contextlib import redirect_stdout
import traceback
import inspect
import io

from discord.ext import commands
import discord


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def get_syntax_error(e):
    return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)


class REPL:
    def __init__(self, bot):
        self.bot = bot
        self.repls = {}
        self.last_eval = None

    async def on_message_delete(self, message):
        repl = self.repls.get(message.channel.id)
        if repl is None or repl.id != message.id:
            return
        self.repls[message.channel.id] = None

    async def repl_summon(self, channel):
        embed = discord.Embed.from_data(self.repls[channel.id].embeds[0])
        await self.bot.delete_message(self.repls.pop(channel.id))
        self.repls[channel.id] = await self.bot.send_message(channel, embed=embed)

    @commands.command(pass_context=True)
    async def repl(self, ctx):
        """Based on R.Danny's REPL and taciturasa's modification to use embed."""
        msg = ctx.message
        await self.bot.delete_message(msg)

        if msg.channel.id in self.repls:
            await self.repl_summon(msg.channel)
            return

        variables = {
            'discord': discord,
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': None
        }

        embed = discord.Embed(description='Enter code to exec/eval. `exit`/`quit` to exit.')
        embed.set_author(name='Interactive Python Shell', icon_url='http://i.imgur.com/5BFecvA.png')
        self.repls[msg.channel.id] = await self.bot.say(embed=embed)

        while True:
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=lambda m: m.content.startswith('`'))
            await self.bot.delete_message(response)

            cleaned = cleanup_code(response.content)
            semi_split = '; '.join(l.strip() for l in cleaned.split('\n'))

            if self.repls[msg.channel.id] is None:
                self.repls[msg.channel.id] = await self.bot.say(embed=embed)

            if cleaned in ('quit', 'exit'):
                embed.colour = discord.Colour.default()
                await self.bot.edit_message(self.repls[msg.channel.id], embed=embed)
                self.repls.pop(msg.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    embed.add_field(name='>>> ' + semi_split, value=get_syntax_error(e), inline=False)
                    embed.colour = discord.Colour.red()
                    embed._fields = embed._fields[-7:]
                    self.repls[msg.channel.id] = await self.bot.edit_message(
                        self.repls[msg.channel.id], embed=embed)
                    continue

            variables['message'] = response

            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                embed.colour = discord.Colour.red()
                output = '```py\n{}{}\n```'.format(value, traceback.format_exc().split('\n')[-2])
            else:
                value = stdout.getvalue()
                variables['__'] = result
                embed.colour = discord.Colour.green()
                if result is not None:
                    output = '```py\n{}{}\n```'.format(value, result)
                elif value:
                    output = '```py\n{}\n```'.format(value)
                else:
                    output = '```py\nNo response, assumed successful.\n```'

            embed.add_field(name='>>> ' + semi_split, value=output, inline=False)
            embed._fields = embed._fields[-7:]
            self.repls[msg.channel.id] = await self.bot.edit_message(
                self.repls[msg.channel.id], embed=embed)

    @commands.command(pass_context=True, aliases=['spy'])
    async def py(self, ctx, *, code: str):
        msg = ctx.message
        if ctx.invoked_with == 'spy':
            await self.bot.delete_message(msg)
        code = code.strip('` ')
        cleaned = code.replace('{', '{{').replace('}', '}}')
        out = '```ocaml\nInput  ⮞ {}\nOutput ⮞ {{}}\n```'.format(cleaned)
        result = None
        env = {
            'discord': discord,
            'bot': self.bot,
            'ctx': ctx,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'me': msg.author,
            '__': self.last_eval
        }
        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            edit = out.format(type(e).__name__ + ': ' + str(e))
        else:
            edit = out.format(result)
        self.last_eval = result
        if ctx.invoked_with == 'spy':
            return
        await self.bot.edit_message(ctx.message, edit)


def setup(bot):
    bot.add_cog(REPL(bot))
