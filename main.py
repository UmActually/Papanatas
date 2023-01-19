import asyncio
import os
import sys
import traceback

import discord
from discord.ext import commands

import nlp
import utils
from Juegos.chess import Chess
from Juegos.juegos import GS
from Juegos.uno import Uno
from Media import ytdl
from utils import Guilds, Checks, Emojis, Schedule


bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())


# Misc


@bot.slash_command(guild_ids=Guilds.all)
@nlp.listens()
async def info(ctx: discord.ApplicationContext):
    """Información de Papanatas."""
    embed, view = utils.info_embed()
    await ctx.respond(embed=embed, view=view)


@bot.slash_command(guild_ids=Guilds.all)
@nlp.listens()
@Checks.default
async def time(ctx):
    """Fecha y hora en México."""
    embed = discord.Embed()
    datetime = utils.time()
    day, month = datetime.day, utils.MONTHS[datetime.month - 1]
    weekday = datetime.weekday()
    embed.add_field(name='Tiempo', value=f'**{datetime.hour}**ₕ **{datetime.minute}**ₘ '
                                         f'**{datetime.second}**ₛ **{datetime.microsecond}**μs\n'
                                         f'**{utils.WEEKDAYS[weekday]} {day}** {month} {datetime.year} DC')
    await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=Guilds.all)
async def natas(ctx: discord.ApplicationContext):
    """Información y ejemplos de 'natas Natural Language."""
    desc = utils.file('Resources/embed_descriptions.txt').split('~')
    embed = discord.Embed(description=desc[0].strip('\n '), color=discord.Color.blue())
    embed.set_author(name='\'NATAS NATURAL LANGUAGE', icon_url=utils.NATAS.avatar.url)
    embed.set_thumbnail(url=utils.image_url(936145063556309022))
    embed.set_footer(text='Lqm, atte. Papanatas')
    embed2 = discord.Embed(description=desc[1].strip('\n '), color=discord.Color.blue())
    embed2.set_author(name='EJEMPLOS')
    for command in nlp.Command.index.values():
        if command.examples:
            value = ''
            for example in command.examples:
                value += f'>> natas {example}\n'
        else:
            value = 'No tiene ejemplos.'
        embed2.add_field(name=f'/**{command.name}**', value=value, inline=False)
    embed2.set_footer(text='Lqm, atte. Papanatas')
    await ctx.respond(embeds=[embed, embed2])


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def dl(ctx: discord.ApplicationContext, link_or_search: discord.Option(str)):
    """Descargar un video DE DURACIÓN RAZONABLE con YouTube DL."""
    msg = await ctx.respond(embed=discord.Embed(description=':arrow_down: **Descargando...**'))
    msg = await msg.original_message()
    path = await ytdl.download(link_or_search)
    if path is None:
        await msg.edit(embed=ytdl.error_embed(link_or_search))
        return
    try:
        await ctx.send(file=discord.File(path))
    except discord.HTTPException:
        await msg.edit(embed=utils.emb('Discord no me dejó subir el video. Te odio Discord.'))
    path.unlink()


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def act(ctx, _type: discord.Option(str, choices=['playing', 'listening', 'watching'], required=False),
              name: discord.Option(str, required=False),
              status: discord.Option(str, choices=['online', 'idle', 'dnd'], required=False)):
    """Cambiar el status de Papanatas."""
    if not (_type and name):
        # Random
        await bot.change_presence(status=status, activity=utils.random_activity())
    else:
        # Custom
        _type = eval(f'discord.ActivityType.{_type}') if _type else discord.ActivityType.playing
        status = eval(f'discord.Status.{status}') if status else discord.Status.online
        await bot.change_presence(status=status, activity=discord.Activity(type=_type, name=name))
    await ctx.respond(embed=utils.emb('Cambiado de status.', Emojis.wild), ephemeral=True)


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def nk(ctx: discord.ApplicationContext, member: discord.Option(discord.Member),
             nick: discord.Option(str, description='Escribe "reset" para quitar el nick.')):
    """Cambiar el nick de cualquier usuario."""
    if member.id == ctx.author.id and ctx.guild.id == Guilds.sociedad[0]:
        await ctx.respond(embed=utils.emb('No. Cámbiale el nombre a los demás, pero jamás el tuyo. No soy pendejo.'),
                          ephemeral=True)
        return
    utils.freeze_nick = False
    try:
        await member.edit(nick=(None if nick.lower() == 'reset' else nick))
        await ctx.respond(embed=utils.emb(f'{member.mention} ahora es **"{member.display_name}"**.'))
    except discord.Forbidden:
        await ctx.respond(embed=utils.emb(f'No tengo permiso de cambiarle el nick a {member.mention}.'))


@bot.slash_command(guild_ids=Guilds.maria)
@Checks.maria
async def hr(ctx):
    """ESTE COMANDO YA NO NOS SIRVE. SOLO ESTÁ AQUÍ POR NOSTALGIA."""

    curr_datetime = utils.time()
    curr_weekday = curr_datetime.weekday()
    curr_time = curr_datetime.time().replace(second=0, microsecond=0)

    try:
        clases = Schedule.schedule[curr_weekday]
    except IndexError:
        await ctx.send('Nmms es fin de semana')
        return

    _bounds = [Schedule.bounds[i] <= curr_time < Schedule.bounds[i + 1] for i in range(6)]

    try:
        index = _bounds.index(True)
    except ValueError:
        index = -1

    embed = discord.Embed(colour=Schedule.colors[clases[index]])
    minutes_left = Schedule.bounds[index + 1].minute - curr_time.minute + 60 * (
            Schedule.bounds[index + 1].hour != curr_time.hour)
    receso = 30 * (index == 2) + 5 * (index < 5 and index != 2)
    en_clase = minutes_left - receso > 0
    extra = ''
    if index != -1:
        extra = f'{"(Receso) " * (not en_clase)}**{minutes_left - receso * en_clase}** min'
    clases[index] = f'**{clases[index]} <<** {extra}'

    embed.add_field(name='**Horario**', value='\n'.join(clases))
    clases[index] = clases[index].split(' <<')[0][2:]
    tm: str = curr_time.strftime('%H:%M')
    embed.set_footer(text=f'{utils.WEEKDAYS[curr_weekday]} {curr_datetime.day}\n{tm}')
    await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
@nlp.listens()
async def coords(ctx, xyz: discord.Option(str, description='Separa las coords por espacio o por coma.')):
    """Traduce coordenadas de minecraft de Overworld a Nether."""
    for sep in [', ', ',', ' ']:
        split = xyz.split(sep)
        if len(split) > 1:
            break
    else:
        await ctx.respond(embed=utils.emb('Escribe bien, atte. Papanatas.'))
        return
    if len(split) == 3:
        del split[1]
    try:
        split = list(map(int, split))
    except ValueError:
        await ctx.respond(embed=utils.emb('Esas no son coordenadas, wtf'))
        return
    embed = discord.Embed()
    embed.add_field(name='Overworld', value='ㅤ      ' + ', '.join(map(str, split)), inline=False)
    embed.add_field(name='Nether', value='ㅤ      ' + ', '.join(map(lambda x: str(round(x / 8)), split)), inline=False)
    await ctx.respond(embed=embed)


# Juegos


@bot.slash_command(guild_ids=Guilds.uno, name='uno')
@Checks.default
@nlp.listens('uno')
async def uno_new_game(ctx):
    """Iniciar nuevo juego de UNO."""
    status = Uno.get_status(ctx.guild.id)
    if status.unavailable:
        desc = 'En este server aún no está activado el UNO. ' \
               'Por favor contacta a tu WellActually local.'
        await ctx.respond(embed=utils.emb(desc))
    if status.active:
        return
    uno = Uno.get(ctx.guild.id)
    await uno.new_game(ctx)


@bot.slash_command(guild_ids=Guilds.sociedad, name='chess')
@Checks.default
async def chess_new_game(ctx):
    """Iniciar nuevo juego de ajedrez."""
    status = Chess.get_status(ctx.guild.id)
    if status == GS.unavailable:
        desc = 'En este server aún no está activado el chess. ' \
               'Por favor contacta a tu WellActually local.'
        await ctx.respond(embed=utils.emb(desc))
    if status.active:
        return
    chess = Chess.get(ctx.guild.id)
    await chess.new_game(ctx)


# Mandar / Editar / Responder mensajes


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def echo(ctx, text: discord.Option(str)):
    """Enviar un mensaje en este canal."""
    await ctx.delete()
    await ctx.send(text)


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def tell(ctx, channel: discord.Option(discord.TextChannel), text: discord.Option(str)):
    """Enviar un mensaje a otro canal."""
    await ctx.delete()
    await channel.send(text)


@bot.command()
@Checks.admin
async def gsquad(_ctx, *, text):
    """Enviar un mensaje a G-chat en la G-squad."""
    await utils.gsquad.send(text)


@bot.slash_command(guild_ids=Guilds.maria)
@Checks.maria
async def telegram(ctx, text: discord.Option(str, description='De preferencia miéntales la madre.')):
    """Enviar un mensaje al otro server (entre Sociedad ☭ y G-squad)."""
    if ctx.guild.id == Guilds.sociedad[0]:
        channel = utils.gsquad
    else:
        channel = utils.general
    embed = discord.Embed().add_field(name=f'**| {ctx.author.name}**', value=text)
    embed.set_author(name=f'Mensaje de parte de la {ctx.guild.name}', icon_url=ctx.guild.icon.url)
    await channel.send(embed=embed)
    embed.set_author(name=f'Mensaje enviado a la {channel.guild.name}', icon_url=channel.guild.icon.url)
    await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=Guilds.all)
@Checks.default
async def reply(ctx,
                message_id: discord.Option(str), text: discord.Option(str),
                channel: discord.Option(discord.TextChannel, description='Por default es este canal.', required=False)):
    """Responder a un mensaje."""
    channel = channel or ctx.channel
    msg: discord.Message = await channel.fetch_message(int(message_id))
    await ctx.delete()
    await msg.reply(text)


@bot.slash_command(guild_ids=Guilds.all)
@Checks.admin
async def edit(ctx, message_id: discord.Option(str), text: discord.Option(str),
               channel: discord.Option(discord.TextChannel, description='Por default es este canal.', required=False)):
    """Editar un mensaje de Papanatas."""
    channel = channel or ctx.channel
    msg: discord.Message = await channel.fetch_message(message_id)
    await ctx.delete()
    await msg.edit(content=text)


@bot.slash_command(guild_ids=Guilds.maria)
@Checks.default
@nlp.listens()
async def salt(ctx, seconds: discord.Option(int, description='De 5 a 900 segundos.'),
               text: discord.Option(str, description='Algo cancelable.')):
    """Enviar un mensaje que se autodestruirá en la cantidad de segundos que le digas."""
    seconds = max(5, min(900, seconds))
    embed = discord.Embed(description=text.strip(' .:'))
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    embed.set_footer(text=f'Este mensaje se autodestruirá en {seconds} segundos.')
    ctx: discord.Interaction = await ctx.respond(embed=embed)
    await asyncio.sleep(1)
    for second in range(seconds - 1, 0, -1):
        embed.set_footer(text=f'Este mensaje se autodestruirá en {utils.plural(second, "segundo")}.')
        await ctx.edit_original_message(embed=embed)
        await asyncio.sleep(1)
    await ctx.delete_original_message()


# Brasil / Argentina


@bot.user_command(guild_ids=Guilds.sociedad, name='MANDAR A BRASIL')
async def user_brazil(ctx, member: discord.Member):
    await utils.send_to_brazil(ctx, member)


@bot.message_command(guild_ids=Guilds.sociedad, name='MANDAR A BRASIL')
async def message_brazil(ctx, message: discord.Message):
    await utils.send_to_brazil(ctx, message.author, message)


@bot.slash_command(guild_ids=Guilds.sociedad, name='brazil')
@Checks.default
async def manual_brazil(ctx, member: discord.Option(discord.Member)):
    """Mandar manualmente a alguien a Brasil."""
    await utils.send_to_brazil(ctx, member)


@bot.slash_command(guild_ids=Guilds.sociedad)
@Checks.sociedad
async def argentina(ctx):
    """Suspender el sufrimiento de la tierra de Orden y Progreso."""
    await utils.send_to_argentina(ctx)


# Cosas de debug / admin


@bot.command()
@Checks.mac
async def unosetup(ctx):
    uno_category = await ctx.guild.create_category('uno')
    await ctx.guild.create_role(name='Espectador')
    spectator_channel = await uno_category.create_text_channel('espectador')
    await spectator_channel.send(embed=discord.Embed(title='Embed Temporal'))
    spectator_channel = spectator_channel.id
    player_channels = []
    for i in range(10):
        await ctx.guild.create_role(name=f'P{i + 1}')
        player_channel = await uno_category.create_text_channel(f'p{i + 1}')
        player_channels.append(player_channel.id)
    uno_channels = utils.file('Resources/Juegos/uno_channels.json')
    uno_channels[str(ctx.guild.id)] = [player_channels, spectator_channel]
    utils.file('Resources/Juegos/uno_channels.json', uno_channels)


@bot.command()
@Checks.admin
async def purge(ctx, n: int):
    """Borrar muchos mensajes a la vez."""
    await ctx.channel.purge(limit=n + 1)


@bot.command()
@Checks.admin
@Checks.sociedad
async def endseason(ctx):
    """Reiniciar todos los nicks y el nombre de la S. de P."""
    sociedad: discord.Guild = ctx.guild
    await sociedad.edit(name='Sociedad de Patanes ☭')
    utils.freeze_nick = False
    for member in sociedad.members:
        try:
            new_nick = '~' + member.name if member.bot and member.id != utils.NATAS_ID else None
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            pass
    utils.freeze_nick = True
    await ctx.message.add_reaction('✅')


@bot.command()
@Checks.admin
async def leave(ctx, guild_id: int):
    """Sacar a Papanatas de un server."""
    guild: discord.Guild = discord.utils.get(bot.guilds, id=guild_id)
    if guild is None:
        await ctx.send('Not Found.')
        return
    await guild.leave()
    await ctx.send(f'Left {guild.name}.')


@bot.command()
@Checks.admin
async def opus(ctx):
    await ctx.send(f'Opus {"not" * (not discord.opus.is_loaded())} loaded')


@bot.command(name='print')
async def print_to_console(_ctx, *, text):
    print(text)


@bot.command()
async def signature(ctx, cmd_name):
    command = nlp.Command.index.get(cmd_name)
    await ctx.send('```' + '\n\n'.join([str(arg) for arg in command.signature]) + '```')


@bot.command(aliases=['stdout'])
@Checks.cloud
async def logs(ctx):
    global stdout
    stdout.close()
    with open('Resources/logs.txt', 'r') as f:
        _logs = f.read()
    stdout = open('Resources/logs.txt', 'w')
    sys.stdout = stdout
    sys.stderr = stdout
    embed = discord.Embed(title='**Standard Output**', description='```' + _logs + '```')
    await ctx.send(embed=embed)
    print('-')


@bot.command(name='exit')
@Checks.admin
async def mexicanada(ctx):
    await ctx.send('Usando exit() para desconectarme...')
    exit()


@bot.command()
@Checks.admin
async def close(ctx):
    await ctx.send('Desconectándome como debe ser...')
    await bot.close()


# Eventos (lo importante está en Cogs/events)


@bot.event
async def on_message(message: discord.Message):
    if message is None or message.type != discord.MessageType.default:
        return
    if utils.in_brazil(message.author):
        await message.delete()
        await message.channel.send(':x: Estás en brasil', delete_after=2)
        return
    if message.guild is not None:
        await bot.process_commands(message)
    else:
        # Es un DM
        try:
            await message.author.send(
                embed=utils.emb('No tengo manera de parsear mensajes directos '
                                'en este momento. La tuya por si acaso.'))
            await utils.debug_channel.send(f'DM de {message.author.mention}: {message.content}')
        except discord.HTTPException:
            pass


@bot.event
async def on_command_error(ctx, error):
    if not (isinstance(error, commands.errors.CheckFailure) or isinstance(error, commands.errors.CommandNotFound)):
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


# Tasks


async def periodically_change_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await bot.change_presence(activity=utils.random_activity())
        await asyncio.sleep(600)  # 10 minutos


bot.loop.create_task(periodically_change_status())


for file in os.listdir('Cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'Cogs.{file[:-3]}')


if utils.ON_CLOUD:
    stdout = open('Resources/logs.txt', 'w')
    sys.stdout = stdout
    sys.stderr = stdout


bot.run(utils.super_secret_token('papanatas'))


# The end.
