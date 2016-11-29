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
        self.repls = set()
        self.last_eval = None

    @commands.command(pass_context=True)
    async def repl(self, ctx):
        msg = ctx.message

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

        if msg.channel.id in self.repls:
            await self.bot.edit_message(msg, 'Already running a REPL here.')
            return

        self.repls.add(msg.channel.id)
        await self.bot.edit_message(msg, 'Entering REPL.')
        while True:
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=lambda m: m.content.startswith('`'))

            cleaned = cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await self.bot.edit_message(response, 'Exiting REPL.')
                self.bot.repls.remove(msg.channel.id)
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
                    await self.bot.edit_message(response, response.content + '\n' + get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = '```py\n{}{}\n```'.format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                variables['__'] = result
                if result is not None:
                    fmt = '```py\n{}{}\n```'.format(value, result)
                    variables['last'] = result
                elif value:
                    fmt = '```py\n{}\n```'.format(value)

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await self.bot.edit_message(response, response.content + '\n' + 'Result too big to be printed.')
                    else:
                        await self.bot.edit_message(response, response.content + '\n' + fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await self.bot.edit_message(response, response.content + '\n' + 'Unexpected error: `{}`'.format(e))

    @commands.command(pass_context=True)
    async def py(self, ctx, *, code: str):
        msg = ctx.message
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
        await self.bot.edit_message(ctx.message, edit)


def setup(bot):
    bot.add_cog(REPL(bot))
