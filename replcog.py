from contextlib import redirect_stdout
from timeit import timeit
from dis import dis
import traceback
import textwrap
import inspect
import io
import os

from discord.ext import commands
import discord


UPPER_PATH = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def get_syntax_error(e):
    return f'```py\n{e.text}{"^":>{e.offset}}\n{type(e).__name__}: {e}\n```'


def exception_signature():
    return traceback.format_exc().split('\n')[-2]


def rep(obj):
    return repr(obj) if isinstance(obj, str) else str(obj)


def print_(*args, **kwargs):
    new_args = [rep(arg) for arg in args]
    print(*new_args, **kwargs)


def get_env(ctx):
    return dict(
        print=print_,
        timeit=timeit,
        dis=dis,
        discord=discord,
        bot=ctx.bot,
        client=ctx.bot,
        ctx=ctx,
        msg=ctx.message,
        message=ctx.message,
        guild=ctx.guild,
        server=ctx.guild,
        channel=ctx.channel,
        me=ctx.me
    )


class REPL:
    def __init__(self, bot):
        self.bot = bot
        self.last_eval = None

    def eval_output(self, inp, out=None):
        lines = []
        for ind, line in enumerate(inp.splitlines()):
            if ind == 0:
                lines.append(f'>>> {line}')
            else:
                lines.append(f'... {line}')
        if sum(len(line) for line in lines) + len(out or '') + (out or '').count('\n') > 2000:
            out = 'Output too long.'
        if out is not None:
            if out.startswith('\n'):
                out = "''" + out
            if out != '':
                lines.append(out)
        return '```py\n' + '\n'.join(lines) + '\n```'

    @commands.command(name='eval', aliases=['seval'])  # seval for silent eval
    async def eval_(self, ctx, *, code: cleanup_code):
        """Alternative to `py` that executes code inside a coroutine.

        Allows multiple lines and `await`ing.

        This is RoboDanny's latest `eval` command adapted for a selfbot.
        """
        msg = ctx.message
        silent = ctx.invoked_with == 'seval'
        if silent:
            await msg.delete()

        env = get_env(ctx)
        stdout = io.StringIO()

        to_compile = 'async def _func():\n%s' % textwrap.indent(code, '  ')

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            if silent:
                await ctx.send(get_syntax_error(e))
            else:
                await msg.edit(content=self.eval_output(code, '\n'.join(get_syntax_error(e).splitlines()[1:-1])))
            return

        func = env['_func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            exc = traceback.format_exc().replace(UPPER_PATH, '...').splitlines()
            exc = '\n'.join([exc[0], *exc[3:]])
            if silent:
                await ctx.send(f'```py\n{value}{exc}\n```')
            else:
                await msg.edit(content=self.eval_output(code, f'{value}{exc}'))
        else:
            value = stdout.getvalue()
            if isinstance(ret, discord.Embed):
                if silent:
                    await ctx.send(value, embed=ret)
                else:
                    await msg.delete()
                    await ctx.send(self.eval_output(code, value), embed=ret)
                return
            if silent:
                await ctx.send(value if ret is None else f'{value}{rep(ret)}')
            else:
                await msg.edit(content=self.eval_output(code, value if ret is None
                                                                    else f'{value}{rep(ret)}'))  # NOQA

    @commands.command(aliases=['spy'])  # spy for silent eval
    async def py(self, ctx, *, code: cleanup_code):
        msg = ctx.message
        silent = ctx.invoked_with == 'spy'
        if silent:
            await msg.delete()

        result = None
        env = get_env(ctx)
        env['__'] = self.last_eval
        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, discord.Embed):
                if silent:
                    await ctx.send(embed=result)
                else:
                    await msg.delete()
                    await ctx.send(self.eval_output(code), embed=result)
                return
        except Exception as e:
            edit = self.eval_output(code, exception_signature())
            if silent:
                await ctx.send('```py\n{exception_signature()}\n```')
        else:
            edit = self.eval_output(code, rep(result))
            self.last_eval = result

        if silent:
            return
        await msg.edit(content=edit)


def setup(bot):
    bot.add_cog(REPL(bot))
