from __future__ import annotations

import asyncio
import datetime
import inspect
import json
import os
import subprocess
from enum import IntEnum
from pathlib import Path
from random import choice
from typing import \
    Any, Optional, Union, Callable, Coroutine, List, Dict, Tuple, TYPE_CHECKING

import discord
import pytz
from discord.ext import commands

if TYPE_CHECKING:
    from vox import Vox
    from Juegos.uno import Uno
    from spotifyatlas import SpotifyAPI


AnyContext = Union[discord.Message, discord.ApplicationContext, discord.ext.commands.Context]


lines_of_code = 0
for _file in Path.cwd().rglob('*'):
    if _file.suffix == '.py':
        lines_of_code += len(_file.read_text().split('\n'))
    elif _file.suffix == '.part':
        # quitar las descargas que no se completaron
        _file.unlink(missing_ok=True)


def file(path: str, obj=None) -> Optional[Union[str, list, dict]]:
    if obj is None:
        with open(path, 'r') as f:
            if path.endswith('.json'):
                _file_ = json.load(f)
            else:
                _file_ = f.read()
        return _file_
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


NATAS: Optional[discord.Member] = None
NATAS_ID: Optional[int] = None

vox: Dict[int, Vox] = {}
uno: Dict[int, Uno] = {}
polls: Dict[int, List[Poll]] = {}
brazil: Dict[int, List[int]] = {}
read_audiobook = {754098185449898054: False, 618189115179139095: False}

event_loop: Optional[asyncio.AbstractEventLoop] = None
spoti: Optional[SpotifyAPI] = None
debug_channel: Optional[discord.TextChannel] = None
general: Optional[discord.TextChannel] = None
gsquad: Optional[discord.TextChannel] = None

ON_CLOUD = 'on_cloud' in os.environ
ON_RPI = 'on_rpi' in os.environ
DEBUG_MODE = False

WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
SOUND_JSON = file('Resources/sounds.json')
SOUND_NAMES = list(SOUND_JSON.keys())
FX_NAMES = ['enmp3', 'hello']


def time() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone('Mexico/General'))


def run(executable: str, *args: str, get_stdout=True) -> Tuple[int, Optional[str]]:
    kwargs = {'capture_output': get_stdout, 'text': True}
    if not get_stdout:
        kwargs['stdout'] = subprocess.DEVNULL
        kwargs['stderr'] = subprocess.DEVNULL
    process = subprocess.run([executable, *args], **kwargs)
    # noinspection PyTypeChecker
    return process.returncode, process.stdout


def install_dependencies():
    """Esto es a lo que tengo que recurrir dada la falta de docs de Google App Engine."""
    if os.path.exists('./vendor'):
        # Heroku ya lo hizo por mí, tqm heroku
        return
    run('./Resources/dependencies.sh', get_stdout=False)


def get_signature(func: Callable, is_command=False) -> List[Argument]:
    types = []
    for param in inspect.signature(func).parameters.values():
        if is_command and param.name in ['self', 'ctx']:
            continue
        annotation = param.annotation
        if annotation == inspect.Parameter.empty and \
                param.default != inspect.Parameter.empty:
            # Se puede inferir
            types.append(Argument(param.name, type(param.default)))
            continue
        if annotation == inspect.Parameter.empty:
            # No tengo idea
            types.append(Argument(param.name, None))
            continue
        if isinstance(annotation, str):
            annotation = eval(annotation)
        if isinstance(annotation, discord.Option):
            # Es una Option en un slash command
            # Esto parece extremadamente redundante, pero no es mi culpa
            bruh_why = {
                'string': str,
                'number': int,
                'integer': int,
                'boolean': bool,
                'channel': discord.abc.GuildChannel,
                'user': discord.Member
            }
            types.append(Argument(param.name, bruh_why[annotation.input_type.name]))
        else:
            # Sí especifica el tipo
            types.append(Argument(param.name, annotation))
    return types


def get_method_class(func: Callable) -> Optional[type]:
    """Conseguir como objeto la clase a la que pertenece el método recibido. Este código está muy macabro,
    la verdad no he podido entenderlo bien."""
    if inspect.ismethod(func):
        # noinspection PyUnresolvedReferences
        for cls in inspect.getmro(func.__self__.__class__):
            if func.__name__ in cls.__dict__:
                return cls
    else:
        return getattr(
            inspect.getmodule(func), func.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0], None)


def adjacents(array: list) -> Tuple[Any, Callable]:
    """Hace un Iterable que en cada paso da el elemento actual, y una func para sacar elementos adyacentes."""
    for i, item in enumerate(array):
        def adjacent(num: int):
            index = i + num
            if index < 0:
                return
            try:
                return array[index]
            except IndexError:
                return
        yield item, adjacent


def pseudo_await(coro: Coroutine):
    """Ejecutar una coroutine, para cuando se está dentro de un def."""
    fut = asyncio.run_coroutine_threadsafe(coro, event_loop)
    fut.result()


def acentoless(text: str) -> str:
    return text.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')


def plural(amount: int, word: str, bold=False) -> str:
    if bold:
        return f'**{amount}** {word}{"s" * int(amount != 1)}'
    return f'{amount} {word}{"s" * int(amount != 1)}'


def random_activity() -> discord.Activity:
    """Actividad random. Véase Resources/Activities."""
    act_type = choice(['playing', 'listening', 'watching'])
    act_list = file(f'Resources/Activities/{act_type}.txt')
    act_name = choice(act_list.split('\n'))
    return discord.Activity(type=eval(f'discord.ActivityType.{act_type}'), name=act_name)


def image_url(msg_id: int, name='unknown', kind='png', channel_id=765560541309304862) -> str:
    return f'https://cdn.discordapp.com/attachments/{channel_id}/{msg_id}/{name}.{kind}'


async def go_the_fuck_to_sleep(voxes: List[Vox], channels: List[discord.VoiceChannel]):
    """En un mundo sin controles parentales, un Papanatas es todo lo que necesitas
    para mandar a dormir a los chamacos."""

    for _vox, channel in zip(voxes, channels):
        guild_id = channel.guild.id
        if not (1 < len(channel.members) < 4) or read_audiobook[guild_id]:
            continue

        read_audiobook[guild_id] = True

        def after_playback(error):
            if error is not None:
                print(error)
            pseudo_await(_vox.client.disconnect())

        if _vox.client_status.active:
            _vox.client.stop()
        if _vox.status == 2:
            await _vox.reset_queue(_vox.embed_msg)
        _vox.status = type(_vox.status).soundboard
        await _vox.join_voice(channel.members[0])
        _vox.now_playing.reset()
        with open('Resources/ffmpeg_logs.txt', 'w') as f:
            audio = discord.FFmpegOpusAudio(f'Resources/Sounds/sleep.mp3', stderr=f)
        _vox.client.play(audio, after=after_playback)
        await debug_channel.send(f'Reading Bedtime Story: {channel.name}')


def emb(text: str, emoji='') -> discord.Embed:
    """Embed simple para respuestas de comandos."""
    if emoji:
        emoji += ' '
    if len(text) > 15 or '@' in text:
        return discord.Embed(description=emoji + text)
    return discord.Embed(title=emoji + text)


def super_secret_token(key: str) -> str:
    """No touchy."""
    return os.environ.get(key) if ON_CLOUD or ON_RPI \
        else file(f'{os.environ.get("supersecrettokens")}/{key}.txt')


def papanatas_age() -> int:
    tm = NATAS.created_at.replace(tzinfo=pytz.timezone('UTC')).astimezone(pytz.timezone('Mexico/General'))
    curr_tm = datetime.datetime.now(pytz.timezone('Mexico/General'))
    dx = curr_tm - tm
    return dx.days


def info_embed(faq=False) -> Tuple[discord.Embed, discord.ui.View]:
    about: dict = file('about.json')
    embed = discord.Embed(description=f'Versión {about["version"]}\nUna verga pa todo')
    embed.set_author(name='PAPANATAS', icon_url=NATAS.avatar.url)
    if faq:
        embed.add_field(name='ㅤ\n**| FAQ**', value='ㅤ\n' + '\n\n'.join(about['faq']), inline=False)
    else:
        embed.add_field(
            name='**| Status**',
            value=f'{Emojis.heroku} En Heroku' if ON_CLOUD else f'{Emojis.mac} En Mac de Leo')
        embed.add_field(name='**| Edad**', value=f'{papanatas_age()} Días')
        embed.add_field(name='**| Líneas de Código**', value=str(lines_of_code))
        embed.add_field(name='**| About**', value=about['about'], inline=False)
    return embed, InfoEmbedButtons()


def is_worthy(message: discord.Message, ignore_myself=True) -> bool:
    """Determina si un mensaje es digno de ser procesado."""
    return not (
            message is None or
            message.type != discord.MessageType.default or
            ignore_myself and message.author.id == NATAS_ID or
            in_brazil(message.author)
    )


def in_brazil(member: discord.Member):
    try:
        return member.id in brazil[member.guild.id] \
               and member.id != 715394802752946199
    except KeyError:
        return False


async def send_to_brazil(ctx: AnyContext, member: discord.Member, message: discord.Message = None):
    if member.id == NATAS_ID:
        await ctx.respond(f'??????? PQ {Emojis.gilbert}')
        return

    brazil_channel = ctx.guild.get_channel(808355253141372990)
    try:
        await member.move_to(brazil_channel)
    except discord.HTTPException:
        pass
    try:
        rol = discord.utils.get(ctx.guild.roles, name='brazil')
        await member.add_roles(rol)
    except discord.NotFound:
        pass
    try:
        brazil[ctx.guild.id].append(member.id)
    except KeyError:
        brazil[ctx.guild.id] = [member.id]
    if message is not None:
        await message.add_reaction('🇧🇷')

    mention = member.mention
    resps = [
        f'{mention} se nos fue pa 🇧🇷.',
        f'{mention}, mi loco, dele pa 🇧🇷.',
        f'Pa brasil, {mention}.',
        f'successfully 🇧🇷\'d {mention}.'
    ]

    await ctx.respond(embed=emb(choice(resps)))


async def send_to_argentina(ctx: AnyContext):
    mentions = []
    try:
        brazil_ids = brazil[ctx.guild.id]
    except KeyError:
        return
    for member_id in brazil_ids:
        member = await ctx.guild.fetch_member(member_id)
        mentions.append(member.mention)
        vox_channel = ctx.guild.get_channel(754098185449898060)
        try:
            await member.move_to(vox_channel)
        except discord.HTTPException:
            pass
        try:
            rol = discord.utils.get(ctx.guild.roles, name='brazil')
            await member.remove_roles(rol)
        except discord.NotFound:
            pass
    brazil[ctx.guild.id].clear()

    if not mentions:
        await ctx.respond(embed=emb('No había gente en 🇧🇷. Todos se han estado portando bien.'))
        return

    mention = ', '.join(mentions)
    resps = [
        f'Regresando de 🇧🇷 a {mention}.',
        f'Levantando el castigo a {mention}.',
        f'Regresando los derechos y la dignidad a {mention}.',
        f'Terminando el sufrimiento para {mention}.',
        f'Liberando a {mention} del purgatorio.',
    ]

    await ctx.respond(embed=emb(choice(resps)))


class Guilds:
    sociedad = [754098185449898054]
    gsquad = [618189115179139095]
    itc = [871860282840997888]
    coro = [865988914723815454]
    ell = [790338348048187413]
    maria = sociedad + gsquad
    all = sociedad + gsquad + itc + coro + ell
    uno = list(map(int, file('Resources/Juegos/uno_channels.json').keys()))


class Checks:
    default = commands.check(lambda ctx: (not in_brazil(ctx.author)))
    admin = commands.check(lambda ctx: ctx.author.id == 715394802752946199)
    sociedad = commands.check(lambda ctx: (ctx.guild.id == Guilds.sociedad[0] and not in_brazil(ctx.author)))
    maria = commands.check(lambda ctx: (ctx.guild.id in Guilds.maria and not in_brazil(ctx.author)))
    mac = commands.check(lambda ctx: (ctx.author.id == 715394802752946199 and not ON_CLOUD))
    cloud = commands.check(lambda ctx: (ctx.author.id == 715394802752946199 and ON_CLOUD))


class Emojis:
    numbers = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
    letters = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶',
               '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']

    # Emoji
    que = '❔'
    raised_hand = '✋'
    check = '✅'
    eyes = '👀'
    x = '❌'

    # Discord animated
    obama = '<a:obama:885262941543333888>'
    wahoo = '<a:wahoo:895427086284628009>'

    # Discord
    gilbert = '<:gilbert:892979651524300820>'
    marie = '<:marie:763874595580805130>'
    cagada = '<:cagada:842610366059380757>'
    skip = '<:skip:800111602942607380>'
    wild = '<:wild:800111602530910209>'
    mas4 = '<:mas4:800111602724110348>'
    heroku = '<:heroku:839551444868136970>'
    mac = '<:mac:839551393564327956>'
    itesm = '<:itesm:884970698567721031>'
    track_pause = '<:track_pause_alt:908261410524495883>'
    track_skip = '<:track_skip_alt:908261430279684107>'

    @staticmethod
    def random_animated():
        return choice([Emojis.obama, Emojis.wahoo])


class Poll:
    """Clase para crear y llevar la cuenta en encuestas, hechas con el comando /poll."""

    def __init__(self, title: str, options: str):
        options = [o.strip(' ,;\n\t') for o in options.split(';')]
        self.n_options = len(options)
        self.title = title
        self.options = options
        self.msg = None
        self.already_voted = []
        self.votes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    @property
    def embed(self) -> discord.Embed:
        desc = ''
        for k, option in enumerate(self.options):
            votes = self.votes[k]
            winner = votes == max(self.votes)
            if votes == 0:
                desc += f'{Emojis.numbers[k]} | {option}\n'
            else:
                percent = int(100 * (votes / sum(self.votes)))
                desc += f'{Emojis.numbers[k]} {winner * "**"}| {option} ({percent}%){winner * "**"}\n'
        embed = discord.Embed(title=self.title.title(), description=desc)
        embed.set_author(name='Encuesta', icon_url=image_url(884568260786389054, 'poll_icon'))
        embed.set_footer(text='Provided by Papanatas.')
        return embed

    async def send_to(self, channel: AnyContext):
        msg = await channel.send(embed=self.embed)
        for i in range(self.n_options):
            await msg.add_reaction(Emojis.numbers[i])
        self.msg = msg
        return self.msg.id

    async def update(self, payload: discord.RawReactionActionEvent):
        member = await self.msg.guild.fetch_member(payload.user_id)
        if member.id in self.already_voted:
            await self.msg.remove_reaction(payload.emoji, member)
            return
        self.already_voted.append(member.id)
        self.votes[Emojis.numbers.index(str(payload.emoji))] += 1
        await self.msg.edit(embed=self.embed)


class Schedule:
    schedule = [
        ['Inglés', 'Empresa', 'Historia', 'Literatura', 'Biología', 'TOK'],
        ['Inglés', 'Libre', 'Biología', 'Historia', 'Empresa', 'Empresa'],
        ['Inglés', 'Historia', 'Biología', 'CAS', 'Literatura', 'Empresa'],
        ['Inglés', 'Francés', 'Mono', 'Mate', 'TOK', 'Biología'],
        ['Mate', 'Mate', 'Historia', 'Libre', 'Literatura', 'Literatura']
    ]

    colors = {
        'Inglés': discord.Colour.red(), 'Empresa': discord.Colour.gold(), 'Historia': discord.Colour.purple(),
        'Literatura': discord.Colour.dark_red(), 'Biología': discord.Colour.green(), 'TOK': discord.Colour.blue(),
        'Libre': discord.Colour.dark_grey(), 'CAS': discord.Colour.teal(), 'Mono': discord.Colour.light_grey(),
        'Francés': discord.Colour.magenta(), 'Mate': discord.Colour.dark_blue()
    }

    bounds = [
        datetime.time(8, 0, 0, 0), datetime.time(8, 50, 0, 0), datetime.time(9, 40, 0, 0),
        datetime.time(10, 55, 0, 0), datetime.time(11, 45, 0, 0), datetime.time(12, 35, 0, 0),
        datetime.time(13, 20, 0, 0)
    ]


class InfoEmbedButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='FAQ', style=discord.ButtonStyle.primary, emoji=Emojis.que)
    async def faq(self, _button, interaction: discord.Interaction):
        await interaction.message.edit(embed=info_embed(True)[0], view=None)


class PseudoContext:
    """Básicamente es nuestro boleto para poder meter un discord.Message en el parámetro 'ctx' de
    los comandos del bot. Los métodos de discord.ApplicationContext casi siempre van a tener un
    equivalente en Message. Esta sí es una mexicanada de las grandes. Favor de no ver este código."""

    def __init__(self, message: discord.Message):
        self.message = message
    
    def __getattr__(self, name: str):
        try:
            return getattr(self.message, name)
        except AttributeError:
            print('CTX ATTRIBUTE:', name)
            return None

    async def send(self, *args, **kwargs):
        msg = await self.message.channel.send(*args, **kwargs)
        return PseudoContext(msg)

    async def respond(self, *args, **kwargs):
        try:
            embed = kwargs['embed']
            embed.color = discord.Color.blue()
        except KeyError:
            pass
        try:
            msg = await self.message.reply(*args, **kwargs)
        except TypeError:
            del kwargs['ephemeral']
            msg = await self.message.reply(*args, **kwargs)
        return PseudoContext(msg)
    
    async def original_message(self):
        return self
    
    async def edit_original_message(self, *args, **kwargs):
        await self.message.edit(*args, **kwargs)
    
    async def delete_original_message(self):
        await self.message.delete()


class Cog(IntEnum):
    main = 0
    events = 1
    polls = 2
    roles = 3
    vox_commands = 4


class Argument:
    """Command argument."""
    def __init__(self, name: str, cls: Optional[type]):
        self.name = name
        self.cls = cls
        self.desc: Optional[str] = None
        self.prev: Optional[dict] = None
        self.real: Optional[dict] = None
        self.next: Optional[dict] = None

    def __str__(self):
        return f'{self.name}: {self.cls}'

    def __repr__(self):
        return f'{self.name}: {self.cls}\n"""{self.desc}"""\n' \
               f'{self.prev} <{self.name}> {self.next}'
