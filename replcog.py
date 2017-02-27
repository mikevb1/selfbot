from contextlib import redirect_stdout
import traceback
import textwrap
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

    async def eval_output(self, inp, out):
        lines = []
        for ind, line in enumerate(inp.splitlines()):
            if ind == 0:
                lines.append(f'>>> {line}')
            else:
                lines.append(f'... {line}')
        link = await self.maybe_upload(out, len('```py\n' + '\n'.join(lines) + '\n\n```'))
        if link != 'None':
            lines.append(link if link == '' else "''")
        return '```py\n' + '\n'.join(lines) + '\n```'

    async def on_message_delete(self, message):
        repl = self.repls.get(message.channel.id)
        if repl is None or repl.id != message.id:
            return
        self.repls[message.channel.id] = None

    async def repl_summon(self, channel):
        embed = self.repls[channel.id].embeds[0]
        await self.repls.pop(channel.id).delete()
        self.repls[channel.id] = await channel.send(embed=embed)

    async def maybe_upload(self, content, cur_len=0, max_len=2000,
                           title='Selfbot Eval', lang='python3'):
        """Checks length of content and returns either the content or link to paste.

        Recommended langs are: python3, py3tb (traceback), pycon (interactive session)
        """
        contents = str(content)
        if len(contents) <= max_len - cur_len:
            return contents
        data = {
            'content': contents,
            'syntax': lang,
            'title': title,
            'poster': str(self.bot.user),
            'expiry_days': 1
        }
        resp = await self.bot.request('http://dpaste.com/api/v2/',
                                      method='POST', data=data, type_='text')
        if resp.status == 201:
            return resp.data
        return 'Result too long and error occurred while posting to dpaste.'

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
            'client': self.bot,
            'msg': msg,
            'message': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': None
        }

        embed = discord.Embed(description='Enter code to exec/eval. `exit`/`quit` to exit.')
        embed.set_author(name='Interactive Python Shell', icon_url='http://i.imgur.com/5BFecvA.png')
        self.repls[msg.channel.id] = await ctx.send(embed=embed)

        def response_check(response):
            return (response.content.startswith('`') and
                    response.author == msg.author and
                    response.channel == msg.channel)

        async def update():
            if self.repls[msg.channel.id] is not None:
                await self.repls[msg.channel.id].edit(embed=embed)
            else:
                self.repls[msg.channel.id] = await ctx.send(embed=embed)

        while True:
            response = await self.bot.wait_for('message', check=response_check)
            await response.delete()

            cleaned = cleanup_code(response.content)
            semi_split = '; '.join(l.strip() for l in cleaned.split('\n'))

            if cleaned in ('quit', 'exit'):
                embed.colour = discord.Colour.default()
                await update()
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
                    await update()
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
            embed._fields = embed._fields[-3:]
            await update()

    @commands.command(name='eval', aliases=['seval'])  # seval for silent eval
    async def eval_(self, ctx, *, code: str):
        """Alternative to `py` that executes code inside a coroutine.

        Allows multiple lines and `await`ing.

        This is RoboDanny's latest `eval` command adapted for a selfbot.
        """
        msg = ctx.message
        silent = ctx.invoked_with == 'seval'
        if silent:
            await msg.delete()

        code = cleanup_code(code)
        env = {
            'discord': discord,
            'bot': self.bot,
            'client': self.bot,
            'ctx': ctx,
            'msg': msg,
            'message': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'me': msg.author,
        }
        stdout = io.StringIO()

        to_compile = 'async def _func():\n%s' % textwrap.indent(code, '  ')

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            if silent:
                await ctx.send(get_syntax_error(e))
            else:
                await msg.edit(content=await self.eval_output(code, get_syntax_error(e)))
            return

        func = env['_func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            if silent:
                await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
            else:
                await msg.edit(content=await self.eval_output(code, f'{value}{traceback.format_exc()}'))
        else:
            value = stdout.getvalue()
            if isinstance(ret, discord.Embed):
                if silent:
                    await ctx.send(embed=ret)
                else:
                    await msg.delete()
                    await ctx.send(await self.eval_output(code, ''), embed=ret)
                return
            if silent:
                await ctx.send(value if ret is None else f'{value}{ret}')
            else:
                await msg.edit(content=await self.eval_output(code, value if ret is None
                                                                    else f'{value}{ret}'))  # NOQA

    @commands.command(aliases=['spy'])  # spy for silent eval
    async def py(self, ctx, *, code: str):
        msg = ctx.message
        silent = ctx.invoked_with == 'spy'
        if silent:
            await msg.delete()

        code = cleanup_code(code)
        result = None
        env = {
            'discord': discord,
            'bot': self.bot,
            'client': self.bot,
            'ctx': ctx,
            'msg': msg,
            'message': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'me': msg.author,
            '__': self.last_eval
        }
        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, discord.Embed):
                if silent:
                    await ctx.send(embed=result)
                else:
                    await msg.delete()
                    await ctx.send(await self.eval_output(code), embed=result)
                return
        except Exception as e:
            edit = await self.eval_output(code, exception_signature())
            if silent:
                await ctx.send('```py\n{exception_signature()}\n```')
        else:
            edit = await self.eval_output(code, result)
            self.last_eval = result

        if silent:
            return
        await msg.edit(content=edit)


def setup(bot):
    bot.add_cog(REPL(bot))
