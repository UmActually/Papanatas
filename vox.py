from __future__ import annotations

import asyncio
from enum import IntEnum
from functools import lru_cache
from random import choice, shuffle
from typing import Optional, List

import discord
from discord.ext import commands

import utils
from Media import ytdl
from utils import Emojis, AnyContext


@lru_cache(maxsize=None)
def _base_youtube_embed():
    desc = '`/play [link/search]` para poner música.\n' \
           '`/ly` y `/ost` pueden depurar la búsqueda.\nㅤ'
    embed = discord.Embed(description=desc)
    embed.set_author(name='YouTube', icon_url=utils.image_url(891565725326667796))
    return embed


class QueueElement:
    """Representa a una canción en la fila (now playing y queue). En modo soundboard,
    solo se inicializa con un título."""

    @classmethod
    def empty(cls) -> QueueElement:
        return cls(None, '', None, 0)

    @classmethod
    def just_title(cls, title: str) -> QueueElement:
        return cls(None, title, None, 0)

    @classmethod
    async def from_ytdl(cls, query: str, added_by: int) -> Optional[QueueElement]:
        """Principalmente wrappea la función de get_title_url() en ytdl.py. No lo pongo allá para que pueda
        funcionar el @lru_cache y recordar queries anteriores. Además, están los errores de ffmpeg."""

        title, url = ytdl.get_title_url(query)

        # Heroku a veces es cruel
        if title is None:
            return

        with open('Resources/ffmpeg_logs.txt', 'w') as f:
            kwargs = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn', 'stderr': f}
            source = discord.FFmpegOpusAudio(url, **kwargs)
        await asyncio.sleep(0.3)

        # Revisar que no haya petado ffmpeg / opus
        # A veces salen 403's cuando se inicializa el audio source
        with open('Resources/ffmpeg_logs.txt', 'r') as f:
            errors = f.read()
        if errors:
            print('FFMPEG', query, errors.split('\n')[0].split('] ')[-1])
            return

        return cls(query, title, source, added_by)

    def __init__(self, query: Optional[str], title: str, source: Optional[discord.FFmpegOpusAudio], added_by: int):
        if query is None:
            self.query = None
        else:
            self.query = None if query.startswith('https://www.youtube.com/watch?v=') else query
        self.title = title
        self.source = source
        self.added_by = added_by

    def reset(self):
        self.query = None
        self.title = ''
        self.source = None
        self.added_by = 0


class VS(IntEnum):
    """Vox Status. Los dos modos del player de música, y un status inactivo."""
    idle = 0
    soundboard = 1
    youtube = 2


class VCS(IntEnum):
    """Vox Client Status. A diferencia de VS, este no depende de mí. Para saber si el
    VoiceClient está pausado, desconectado, etc., se debe llamar a los métodos correspondientes en
    la librería de discord."""
    disconnected = 0
    idle = 1
    playing = 2
    paused = 3

    @property
    def active(self):
        return self > 1


class Vox:
    """Vox es la clase que maneja la música en los voice chats. A cada server le corresponde una instancia de Vox.
    Se guardan en el diccionario de utils.vox. La mayoria de los métodos aquí son para el modo youtube. El modo
    soundboard (poner sonidos y fx's de Resources/Sounds) se procesa principalmente en Cogs/events.py."""

    @classmethod
    def get(cls, guild_id: int) -> Vox:
        try:
            _ = utils.vox[guild_id]
        except KeyError:
            utils.vox[guild_id] = cls()
        return utils.vox[guild_id]

    def __init__(self):
        self.client = None
        self.embed_msg = None
        self._status = VS.idle
        self.previous_status = VS.idle
        self.embed_msg_gap = 0
        self.now_playing = QueueElement.empty()
        self.queue: List[QueueElement] = []
        self.lock_queue = False
        self.queuing_list = False

    @property
    def status(self) -> VS:
        return self._status

    @status.setter
    def status(self, new_value: VS):
        self.previous_status = self._status
        self._status = new_value

    @property
    def client_status(self) -> VCS:
        if self.client is None or not self.client.is_connected():
            return VCS.disconnected
        if self.client.is_playing():
            return VCS.playing
        if self.client.is_paused():
            return VCS.paused
        return VCS.idle

    @property
    def youtube_embed(self) -> discord.Embed:
        client_status = self.client_status
        if client_status == VCS.playing:
            name = f'{Emojis.random_animated()} **Now Playing**'
        elif client_status == VCS.paused:
            name = '**Paused**'
        else:
            name = '**Recently Played**'
        embed = _base_youtube_embed().copy()
        embed.add_field(name=name, value=self.now_playing.title)
        if (self.queue and client_status.active) or self.queuing_list:
            queue_list = [('**>>** ' + q.title) for q in self.queue]
            too_long = len(queue_list) > 6
            if too_long:
                queue_list = queue_list[:6]
            if too_long or self.queuing_list:
                queue_list.append('**...**')
            embed.add_field(
                name=f'ㅤ\n**Queue{" - Agregando Más Rolas" * self.queuing_list}**',
                value='\n'.join(queue_list), inline=False)
        return embed

    @property
    def soundboard_embed(self) -> discord.Embed:
        embed = discord.Embed(description='*Escribe en el chat la keyword de la rola.*')
        embed.set_author(name='Soundboard', icon_url=utils.image_url(885187433459773470, 'spoti'))
        is_playing = self.client_status == VCS.playing
        for key, value in utils.SOUND_JSON.items():
            emoji = Emojis.random_animated() if (key == self.now_playing.title and is_playing) else ''
            embed.add_field(name=f'{emoji} **{key}**', value=value)

        # Llenar de fields vacíos para que se vean siempre 3 columnas, luego se ve bn feo
        # En cel siempre se ve feo tho, no hay cómo mejorar eso
        filler = len(utils.SOUND_NAMES) % 3
        if filler != 0:
            for _ in range(3 - filler):
                embed.add_field(name='ㅤ', value='ㅤ')
        embed.set_footer(text='Provided by Papanatas.')
        return embed

    async def join_voice(self, member: discord.Member, greet=False):
        if self.client_status.active or member.voice is None:
            return
        self.client = await member.voice.channel.connect()
        if greet:
            with open('Resources/ffmpeg_logs.txt', 'w') as f:
                audio = discord.FFmpegOpusAudio(f'Resources/Sounds/{choice(utils.FX_NAMES)}.mp3', stderr=f)
            self.client.play(audio)

    async def update_embed(self, ctx: AnyContext):
        embed = self.soundboard_embed if self.status == VS.soundboard else self.youtube_embed
        is_playing = self.client_status == VCS.playing
        too_far_away = self.embed_msg_gap > 7
        send_new_message = (self.embed_msg is None) or (is_playing and too_far_away) or \
                           (ctx.channel.id != self.embed_msg.channel.id)

        if send_new_message:
            self.embed_msg_gap = 0
            try:
                self.embed_msg = await ctx.send(embed=embed, view=VoxButtons())
            except AttributeError:
                self.embed_msg = await ctx.channel.send(embed=embed, view=VoxButtons())
        else:
            try:
                await self.embed_msg.edit(embed=embed, view=VoxButtons())
            except discord.NotFound:
                pass

    async def add_to_queue(
            self, ctx: AnyContext, query: str, add_keyword='', replace_now_playing=False, will_queue_list=False):
        """Agregar una canción a la fila. La variable ctx, que se necesita para enviar y editar mensajes
        se pasea por varios métodos de la clase, y se origina aquí, o donde sea que se tenga contacto con un mensaje
        o comando. Add_keyword y replace_now_playing son usados por el método undo().

        Self.queuing_list es importante para evitar que todo pete completamente cuando haya un error al
        agregar una lista. También es para hacer una excepción en el lock (entre comillas) que hay aquí abajo, para
        ara que sí se agregue de forma concurrente. También uso self.queuing_list para no actualizar el embed de oquis.
        Will_queue_list lo único que hace es activar self.queuing_list."""

        while self.lock_queue:
            await asyncio.sleep(0.5)
            if self.queuing_list:
                break

        self.status = VS.youtube
        self.lock_queue = True
        if will_queue_list:
            self.queuing_list = True

        if isinstance(ctx, commands.Context):
            await ctx.message.edit(suppress=True)

        if add_keyword:
            query = query.replace(' lyrics', '').replace(' ost', '') + ' ' + add_keyword

        rola = await QueueElement.from_ytdl(query, ctx.author.id)
        if rola is None:
            # Solo queremos que se detenga cuando no haya más rolas en camino (queuing_list)
            if not self.queuing_list and not self.client_status.active:
                self.status = VS.idle
            self.lock_queue = False
            await ctx.send(embed=ytdl.error_embed(query), delete_after=10)
            return

        if replace_now_playing:
            self.queue.insert(0, rola)
        else:
            self.queue.append(rola)

        client_status = self.client_status
        self.lock_queue = False

        # Si no está conectado, unirse al voice
        if client_status == VCS.disconnected:
            await self.join_voice(ctx.author)

        # Si es la primera vez en modo youtube, poner la canción con next_song()
        if self.previous_status < 2:
            if client_status.active:
                self.client.stop()
            await self.next_song(ctx)
            return

        # Si vamos a corregir la query de now_playing, forzar next_song()
        if replace_now_playing:
            await self.next_song(ctx, True)
            return

        # Evitarnos la fatiga
        if (len(self.queue) < 8 and not self.queuing_list) or will_queue_list:
            await self.update_embed(ctx)

    async def next_song(self, ctx: AnyContext, force_skip=False):
        if force_skip:
            # Realmente no se hace nada en caso de force_skip
            # Al parar el client, como quiera se llama next_song()
            # por arte de magia, gracias al hook de after_playback
            self.client.stop()
            return

        try:
            next_song = self.queue.pop(0)
            self.now_playing = next_song
            self.client.play(next_song.source, after=self.after_playback(ctx))
        except discord.ClientException:
            await self.reset_queue(ctx)

        await self.update_embed(ctx)

    def after_playback(self, ctx: AnyContext):
        if self.status == VS.youtube:
            # Esta func para modo youtube / queue list
            # Pasar a la siguiente canción, salvo que la música se haya detenido
            def func(error):
                if error is not None:
                    print(error)
                if self.client_status == VCS.disconnected or not self.queue:
                    utils.pseudo_await(self.reset_queue(ctx))
                    return

                utils.pseudo_await(self.next_song(ctx))

            return func

        # Esta func para modo soundboard / idle
        # Nomás es actualizar el embed, salvo que sea redundante
        def func(error):
            if error is not None:
                print(error)
            if not (self.status == VS.youtube and self.previous_status == VS.soundboard):
                utils.pseudo_await(self.update_embed(ctx))
            if not self.client_status.active:
                self.status = VS.idle

        return func

    async def undo(self, ctx: AnyContext, add_keyword='') -> Optional[str]:
        """Esta función malavarea varias cosas. Cuando se quiere quitar o reemplazar una canción de la
        fila con los comandos /undo, /ly, /ost. En el caso de los últimos dos comandos, se prioriza buscar en el
        now playing."""

        # Reemplazar algo en now playing
        if add_keyword and self.now_playing.added_by == ctx.author.id and self.now_playing.query is not None:
            await self.add_to_queue(ctx, self.now_playing.query, add_keyword, True)
            return

        # Retirar o reemplazar en la fila. Se busca en reversa.
        for element in self.queue[::-1]:
            if element.added_by == ctx.author.id:
                self.queue.remove(element)
                if add_keyword:
                    if element.query is not None:
                        await self.add_to_queue(ctx, element.query, add_keyword)
                else:
                    await self.update_embed(ctx)
                    return element.title if element.query is None else element.query
                break

    async def pause_resume(self, ctx: AnyContext):
        if self.client_status == VCS.playing:
            self.client.pause()
        else:
            self.client.resume()
        await self.update_embed(ctx)

    async def clear_queue(self, ctx: AnyContext):
        self.queue.clear()
        await self.update_embed(ctx)

    async def shuffle_queue(self, ctx: AnyContext):
        shuffle(self.queue)
        await self.update_embed(ctx)

    async def reset_queue(self, ctx: AnyContext):
        self.queue.clear()
        await self.update_embed(ctx)
        if self.status == VS.youtube:
            self.status = VS.idle
        self.now_playing.reset()


class VoxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Pause', style=discord.ButtonStyle.secondary, emoji=Emojis.track_pause)
    async def pause_button(self, _button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        _button.label = 'Play'
        try:
            voice = interaction.user.voice
        except AttributeError:
            return
        vox = Vox.get(interaction.guild_id)
        if vox.status != 2 or voice is None:
            return
        utils.event_loop.create_task(vox.pause_resume(vox.embed_msg))

    @discord.ui.button(
        label='Next', style=discord.ButtonStyle.primary, emoji=Emojis.track_skip)
    async def skip_button(self, _button, interaction):
        await interaction.response.defer()
        try:
            voice = interaction.user.voice
        except AttributeError:
            return
        vox = Vox.get(interaction.guild_id)
        if voice is None or vox.status != 2 or not vox.client_status.active or vox.lock_queue or vox.queuing_list:
            return
        utils.event_loop.create_task(vox.next_song(vox.embed_msg, True))

    @discord.ui.button(
        label='Shuffle', style=discord.ButtonStyle.secondary, emoji=Emojis.wild)
    async def shuffle_button(self, _button, interaction):
        await interaction.response.defer()
        try:
            voice = interaction.user.voice
        except AttributeError:
            return
        vox = Vox.get(interaction.guild_id)
        if vox.status != 2 or voice is None:
            return
        utils.event_loop.create_task(vox.shuffle_queue(vox.embed_msg))
