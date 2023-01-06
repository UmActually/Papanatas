from random import sample
from typing import Optional, List

import discord
from discord.ext import commands
from spotifyatlas import Track

import nlp
import utils
from utils import Guilds, Checks, Emojis, Cog, AnyContext
from vox import Vox


ROAST_INNOCENT_USER = utils.emb('Tú no estás en ningún canal de voz y yo no estoy hecho para adivinar a cuál unirme.')
ROAST_EDGY_USER = utils.emb('No estás en ningún canal de voz. Me reservo el derecho de no hacer nada por ti.')


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


async def queue_list(ctx: AnyContext, tracks: List[Track], sample_size=10):
    length = len(tracks)
    tracks = list(map(lambda t: f'{t.name} {t.artist} lyrics',
                      sample(tracks, min(length, sample_size))))

    vox = Vox.get(ctx.guild.id)
    if length == 1:
        await vox.add_to_queue(ctx, tracks[0], 'lyrics')
        return

    task = None

    # La primera rola la agrega siempre
    await vox.add_to_queue(ctx, tracks[0], 'lyrics', will_queue_list=True)

    # Las otras rolas se las prometemos al usuario. Viva el async™
    # DE DOS EN DOS PORQUE HEROKU LLORA
    for i, track in enumerate(tracks[1:]):
        task = utils.event_loop.create_task(vox.add_to_queue(ctx, track, 'lyrics'))
        if i % 2:
            await task
            await vox.update_embed(ctx)
    if length % 2:
        await task

    vox.queuing_list = False
    await vox.update_embed(ctx)


def spotify_embed(result) -> discord.Embed:
    embed = discord.Embed(title=result.name, description=result.author_or_artist)
    embed.set_thumbnail(url=result.image_url)
    return embed


class VoxCommands(commands.Cog):
    def __init__(self, client):
        self.bot = client

    async def search_playlist(self, channel_id: int, name: str) -> Optional[List[str]]:
        channel: discord.TextChannel = self.bot.get_channel(channel_id)
        async for msg in channel.history():
            if msg.author.bot:
                continue
            tracks = msg.content.split('\n')
            curr_name = utils.acentoless(tracks.pop(0))
            if curr_name == name:
                return tracks

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
            await queue_list(ctx, result.tracks)
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

    @commands.slash_command(guild_ids=Guilds.all)
    async def playlist(self, ctx: discord.ApplicationContext, link_or_name: discord.Option(str)):
        """Agregar una playlist a la fila, del canal #playlists."""
        if ctx.author.voice is None:
            await ctx.respond(embed=ROAST_EDGY_USER, ephemeral=True)
            return

        query = link_or_name
        sample_size = 10

        # Por default toma 10 canciones al azar, salvo que haya un número al final de query
        if ' ' in query and query[-1].isdigit():
            split = query.split(' ')
            try:
                sample_size = int(split[-1])
                query = ' '.join(split[:-1])
            except ValueError:
                pass

        # Si pasa el link
        if query.startswith('https://open.spotify.com/'):
            resp: discord.Interaction = await ctx.respond(embed=utils.emb(f'Buscando en spoti...'))
            result = utils.spoti.get(query)
            if result is None:
                await resp.edit_original_message(embed=utils.emb(f'La URL no jala. Escribe bien, atte, Papanatas.'))
                return
            await resp.edit_original_message(embed=spotify_embed(result))
            tracks = result.tracks

        # Si pasa un nombre
        else:
            resp: discord.Interaction = await ctx.respond(embed=utils.emb(f'Buscando la playlist **"{query}"**.'))
            query = utils.acentoless(query)

            # Buscar la playlist, priorizando el canal del server
            playlist_channels: dict = utils.file('Resources/playlist_channels.json')
            try:
                channel_id = playlist_channels[str(ctx.guild.id)]
                tracks = await self.search_playlist(channel_id, query)
            except KeyError:
                tracks = None

            if tracks is None:
                for channel_id in playlist_channels.values():
                    tracks = await self.search_playlist(channel_id, query)
                    if tracks is not None:
                        break
                else:
                    await resp.edit_original_message(embed=utils.emb(f'No existe la playlist **"{query}"**.'))
                    return
            
            # Si el nombre es un alias para un link
            if tracks[0].startswith('https://open.spotify.com/'):
                result = utils.spoti.get(tracks[0])
                if result is None:
                    await resp.edit_original_message(embed=utils.emb(f'La URL no jala. Escribe bien, atte, Papanatas.'))
                    return
                await resp.edit_original_message(embed=spotify_embed(result))
                tracks = result.tracks

        # Agregar las rolas de una por una
        await queue_list(ctx, tracks, sample_size)

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
