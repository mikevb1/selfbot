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
    return f'```py\n{e.text}{"^":>{e.offset}}\n{type(e).__name__}: {e}```'


def exception_signature():
    return traceback.format_exc().split('\n')[-2]


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
        embed = self.repls[channel.id].embeds[0]
        await self.repls.pop(channel.id).delete()
        self.repls[channel.id] = await channel.send(embed=embed)

    @commands.command()
    async def repl(self, ctx):
        """Based on R.Danny's REPL and taciturasa's modification to use embed."""
        msg = ctx.message
        await msg.delete()

        if msg.channel.id in self.repls:
            await self.repl_summon(msg.channel)
            return

        variables = {
            'discord': discord,
            'ctx': ctx,
            'bot': self.bot,
            'msg': msg,
            'guild': msg.guild,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': None
        }

        embed = discord.Embed(description='Enter code to exec/eval. `exit`/`quit` to exit.')
        embed.set_author(name='Interactive Python Shell', icon_url='http://i.imgur.com/5BFecvA.png')
        self.repls[msg.channel.id] = await ctx.send(embed=embed)

        while True:
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=lambda m: m.content.startswith('`'))
            await response.delete()

            cleaned = cleanup_code(response.content)
            semi_split = '; '.join(l.strip() for l in cleaned.split('\n'))

            if self.repls[msg.channel.id] is None:
                self.repls[msg.channel.id] = await ctx.send(embed=embed)

            if cleaned in ('quit', 'exit'):
                embed.colour = discord.Colour.default()
                await self.repls[msg.channel.id].edit(embed=embed)
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
                    self.repls[msg.channel.id] = await self.repls[msg.channel.id].edit(embed=embed)
                    continue

            variables['msg'] = response

            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                embed.colour = discord.Colour.red()
                output = '```py\n{}{}\n```'.format(value, exception_signature())
            else:
                value = stdout.getvalue()
                variables['__'] = result
                embed.colour = discord.Colour.green()
                if result is not None:
                    output = f'```py\n{value}{result}\n```'
                elif value:
                    output = f'```py\n{value}\n```'
                else:
                    output = '```py\nNo response, assumed successful.\n```'

            embed.add_field(name='>>> ' + semi_split, value=output, inline=False)
            embed._fields = embed._fields[-7:]
            self.repls[msg.channel.id] = await self.repls[msg.channel.id].edit(embed=embed)

    @commands.command(aliases=['spy'])
    async def py(self, ctx, *, code: str):
        msg = ctx.message
        if ctx.invoked_with == 'spy':
            await msg.delete()
        code = code.strip('` ')
        cleaned = code.replace('{', '{{').replace('}', '}}')
        out = f'```ocaml\nInput  ⮞ {cleaned}\nOutput ⮞ {{}}\n```'
        result = None
        env = {
            'discord': discord,
            'bot': self.bot,
            'ctx': ctx,
            'msg': msg,
            'guild': msg.guild,
            'channel': msg.channel,
            'me': msg.author,
            '__': self.last_eval
        }
        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            edit = out.format(exception_signature())
        else:
            edit = out.format(result)
            self.last_eval = result
        if ctx.invoked_with == 'spy':
            return
        await ctx.message.edit(content=edit)

    @commands.command()
    async def code(self, ctx, *, text: str):
        await ctx.message.edit(content=f'```\n{text}\n```')


def setup(bot):
    bot.add_cog(REPL(bot))
