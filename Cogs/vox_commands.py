import itertools
from random import sample
from typing import Optional, Callable

import discord
import spotifyatlas
from discord.ext import commands

import nlp
import utils
from utils import Guilds, Checks, Emojis, Cog, AnyContext
from vox import Vox


ROAST_INNOCENT_USER = utils.emb('Tú no estás en ningún canal de voz y yo no estoy hecho para adivinar a cuál unirme.')
ROAST_EDGY_USER = utils.emb('No estás en ningún canal de voz. Me reservo el derecho de no hacer nada por ti.')
PLAYLIST_CHANNELS = utils.file('Resources/playlist_channels.json')


async def special_search(ctx: AnyContext, query: str, keyword: str):
    """En los comandos /ly y /ost, el incluir una query agregará una nueva canción a la fila con el sufijo
    'lyrics' u 'ost' respectivamente. Si no se incluye query, se modifica con vox.undo() el now playing (o la fila),
    agregando los sufijos.

    Sé por experiencia que 9/10 de las veces que pones una canción de pop te va a salir un
    Official Video, donde la música se tarda en empezar.

    El caso de /ost es diferente. A veces, cuando vas a poner una canción de un videojuego o película, se
    necesita más contexto que solo el nombre de la canción. Si bien '/p otherside' pone la de Red Hot Chili Peppers,
    '/ost otherside' va a regresar la de Lena Raine."""

    if ctx.author.voice is None:
        return
    vox = Vox.get(ctx.guild.id)
    if query:
        # No tiene caso agregar un sufijo a un URL (creo)
        if 'youtu' not in query:
            await vox.add_to_queue(ctx, query, keyword)
    else:
        await vox.undo(ctx, keyword)


async def queue_spotify_result(ctx: AnyContext, result: spotifyatlas.Result):
    length = len(result.tracks)

    if isinstance(result.tracks[0], str):
        tracks = result.tracks
        first_track = tracks.pop(0)
    else:
        tracks = map(lambda t: f'{t.name} {t.artist} lyrics',
                     sample(result.tracks, min(length, 10)))
        first_track = next(tracks)

    vox = Vox.get(ctx.guild.id)
    if length == 1:
        await vox.add_to_queue(ctx, first_track, 'lyrics')
        return

    task = None

    # La primera rola la agrega siempre
    await vox.add_to_queue(ctx, first_track, 'lyrics', will_queue_list=True)

    # Las otras rolas se las prometemos al usuario. Viva el async™
    # DE DOS EN DOS PORQUE HEROKU LLORA
    for i, track in enumerate(tracks):
        # noinspection PyTypeChecker
        task = utils.event_loop.create_task(vox.add_to_queue(ctx, track, 'lyrics'))
        if i % 2:
            await task
            await vox.update_embed(ctx)
    if length % 2:
        await task

    vox.queuing_list = False
    await vox.update_embed(ctx)


def spotify_embed(result: spotifyatlas.Result) -> discord.Embed:
    desc = 'Top Tracks' if result.type == spotifyatlas.Type.ARTIST else result.author_or_artist
    embed = discord.Embed(title=result.name, description=desc)
    if result.image_url is not None:
        embed.set_thumbnail(url=result.image_url)
    return embed


class VoxCommands(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @staticmethod
    def spotify_command(name: str) -> Callable:
        """Factory de los comandos /playlist, /album y /artist"""
        is_playlist = name == 'playlist'

        @commands.command(name=name)
        async def command(self, ctx: commands.Context, *, query: str):
            """Para buscar contenido específico en spotify, y reproducir el top result.

            En el caso de /playlist, hay un chequeo especial para ver si una playlist
            está guardada como alias (o tiene ahí mismo las canciones) en los canales
            de playlists de los servers."""

            msg = await ctx.send(embed=utils.emb(
                f'Buscando en {"playlists guardadas" if is_playlist else "spoti"}...'))

            result = None
            if query.startswith('https://open.spotify.com/'):
                result = utils.spoti.get(query)
            elif is_playlist:
                result = await self.search_playlist_aliases(query, ctx.guild.id)

            if result is None:
                if is_playlist:
                    await msg.edit(embed=utils.emb('Buscando en spoti...'))
                result = utils.spoti.im_feeling_lucky(
                    query, eval(f'spotifyatlas.Type.{name.upper()}'))

            if result is not None:
                await msg.edit(embed=spotify_embed(result))
                await queue_spotify_result(ctx, result)
            else:
                await msg.edit(embed=utils.emb(
                    f'No encontré ningún resultado. Escribe bien, atte., Papanatas.'))

        return command

    async def search_playlist_aliases(self, target: str, guild_id: int) -> Optional[spotifyatlas.Result]:
        target = utils.acentoless(target)

        for channel_id in itertools.chain(
                (PLAYLIST_CHANNELS[str(guild_id)], ), PLAYLIST_CHANNELS.values()):
            channel: discord.TextChannel = self.bot.get_channel(channel_id)

            async for msg in channel.history():
                if msg.author.bot:
                    continue
                tracks = msg.content.split('\n')
                header = tracks.pop(0)
                less = utils.acentoless(header)

                if less == target:
                    if tracks[0].startswith('https://open.spotify.com/'):
                        return utils.spoti.get(tracks[0])

                    # noinspection PyTypeChecker
                    return spotifyatlas.Result(
                        None, spotifyatlas.Type.PLAYLIST, header,
                        msg.author.display_name, tracks)

    playlist = spotify_command('playlist')
    album = spotify_command('album')
    artist = spotify_command('artist')

    @commands.slash_command(guild_ids=Guilds.all, name='jn')
    @nlp.listens('jn', inside=Cog.vox_commands)
    async def join(self, ctx):
        """Unirse al voice."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_INNOCENT_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        await vox.join_voice(ctx.author, True)
        await ctx.respond(embed=utils.emb(f'Joined **{ctx.author.voice.channel.name}**.'))

    @commands.slash_command(guild_ids=Guilds.all, name='lv')
    @nlp.listens('lv', inside=Cog.vox_commands)
    async def leave(self, ctx):
        """Salirse del voice."""
        vox = Vox.get(ctx.guild.id)
        await vox.client.disconnect()
        await ctx.respond(embed=utils.emb(f'Left **{vox.client.channel.name}**.'))

    @commands.command(aliases=['p'])
    @nlp.listens(inside=Cog.vox_commands)
    async def play(self, ctx: commands.Context, *, query: str):
        """Agregar una canción a la fila"""
        if ctx.author.voice is None:
            return
        if query.startswith('https://open.spotify.com/'):
            result = utils.spoti.get(query)
            if result is None:
                await ctx.send(embed=utils.emb('La URL no jala. Escribe bien, atte, Papanatas.'))
                return
            await ctx.send(embed=spotify_embed(result))
            await queue_spotify_result(ctx, result)
            return
        vox = Vox.get(ctx.guild.id)
        await vox.add_to_queue(ctx, query)

    @commands.slash_command(guild_ids=Guilds.all)
    async def skip(self, ctx):
        """Siguiente canción en la fila."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        await vox.next_song(ctx, True)
        await ctx.respond(
            embed=utils.emb('Ya nadie usa este comando. Ahora hay **BOTONES**, bye.', Emojis.cagada),
            ephemeral=True)

    @commands.slash_command(guild_ids=Guilds.all)
    async def undo(self, ctx):
        """Quitar la última canción de la fila (que tú hayas agregado)"""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        search = await vox.undo(ctx)
        if search is None:
            resp = f'{Emojis.gilbert} No tienes ninguna rola en fila.'
        else:
            resp = f'{Emojis.skip} Quité a **"{search}"** de la fila.'
        await ctx.respond(embed=utils.emb(resp), ephemeral=True)

    @commands.slash_command(guild_ids=Guilds.all)
    async def clear(self, ctx):
        """Borrar todas las rolas de la fila."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        await vox.clear_queue(ctx)
        await ctx.respond(embed=utils.emb('Done.', Emojis.skip), delete_after=5)

    @commands.slash_command(guild_ids=Guilds.all)
    async def shuffle(self, ctx):
        """Shufflear la fila."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        await vox.shuffle_queue(ctx)
        await ctx.respond(embed=utils.emb('Shuffleado.', Emojis.wild), delete_after=5)

    @commands.command(aliases=['ly'])
    async def lyrics(self, ctx: commands.Context, *, query=''):
        if ctx.author.voice is None:
            return
        await special_search(ctx, query, 'lyrics')

    @commands.command()
    async def ost(self, ctx: commands.Context, *, query=''):
        if ctx.author.voice is None:
            return
        await special_search(ctx, query, 'ost')

    @commands.slash_command(guild_ids=Guilds.all)
    async def soundboard(self, ctx):
        """Mostrar el soundboard pa ver qué hay."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return
        vox = Vox.get(ctx.guild.id)
        vox.status = 1
        await vox.update_embed(ctx)
        vox.status = vox.previous_status
        await ctx.respond(embed=utils.emb('Para poner un fx, nomás envía el nombre, sin /.'), ephemeral=True)

    @commands.command()
    @Checks.admin
    async def st(self, ctx: commands.Context):
        vox = Vox.get(ctx.guild.id)
        await ctx.send(f'status: {vox.status.name}\n'
                       f'previous: {vox.previous_status.name}\n'
                       f'client status: {vox.client_status.name}')


def setup(client):
    cog = VoxCommands(client)
    nlp.set_cog_instance(Cog.vox_commands, cog)
    client.add_cog(cog)
