from random import randint

import discord
from discord.ext import commands
from spotifyatlas import SpotifyAPI

import nlp
import utils
from Juegos.chess import Chess
from Juegos.juegos import GS
from Juegos.uno import Uno
from vox import Vox, VS, VCS, QueueElement


MUSIC_CHANNELS = [754098185449898058, 765560541309304862, 872546033345900646, 874053137999229010, 618230954032496641,
                  694577714300059691]


class Events(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        utils.event_loop = self.bot.loop
        utils.spoti = SpotifyAPI('1654ce98e382492cab9091fcf28da0bc', utils.super_secret_token('spoti'))
        utils.debug_channel = self.bot.get_channel(765560541309304862)
        utils.general = self.bot.get_channel(754098185449898056)
        utils.gsquad = self.bot.get_channel(618189115179139100)
        utils.NATAS = await utils.general.guild.fetch_member(self.bot.user.id)
        utils.NATAS_ID = self.bot.user.id

        await self.bot.change_presence(status=discord.Status.online, activity=utils.random_activity())

        if utils.ON_CLOUD:
            await utils.debug_channel.send('Papanatas Enabled.')
        else:
            print('Papanatas Enabled.')

        # Espacio para poner cosillas

    @commands.Cog.listener('on_message')
    async def on_message_nlp(self, message: discord.Message):
        if not utils.is_worthy(message):
            return
        content = message.content.lower()
        if content.startswith('natas '):
            await nlp.Command.search(message, content[6:])

    @commands.Cog.listener('on_message')
    async def on_message_soundboard(self, message: discord.Message):
        if not utils.is_worthy(message):
            return

        content = message.content.lower()

        if message.channel.id in MUSIC_CHANNELS:
            vox = Vox.get(message.guild.id)

            # Soundboard
            if (content in utils.SOUND_NAMES or content == 'risa') and message.author.voice is not None:
                await message.delete()

                vox.status = VS.soundboard
                client_status = vox.client_status
                if client_status.active:
                    vox.client.stop()
                elif client_status == VCS.disconnected:
                    await vox.join_voice(message.author)
                if vox.previous_status == VS.youtube:
                    vox.queue.clear()

                fname = f'sitcom{randint(1, 4)}' if content == 'risa' else content
                with open('Resources/ffmpeg_logs.txt', 'w') as f:
                    audio = discord.FFmpegOpusAudio(f'Resources/Sounds/{fname}.mp3', stderr=f)

                vox.client.play(audio, after=vox.after_playback(message))
                vox.now_playing = QueueElement.just_title(content)
                await vox.update_embed(message)
            else:
                # Cada mensaje que pasa, el embed del player se va quedando en el olvido
                # Cuando supera cierto número, vuelve a enviar embed en vox.update_embed()
                vox.embed_msg_gap += 1

    @commands.Cog.listener('on_message')
    async def on_message_juegos(self, message: discord.Message):
        if not utils.is_worthy(message):
            return

        # UNO
        try:
            guild_uno_channels = Uno.channels[str(message.guild.id)][0]
        except KeyError:
            guild_uno_channels = {}

        if message.channel.id in guild_uno_channels and Uno.get_status(message.guild.id) == GS.playing:
            await message.delete()
            uno = Uno.get(message.guild.id)
            if message.channel.id != guild_uno_channels[uno.turn]:
                return
            # Después de CUATRO guards:
            card_input = message.content.lower().split(' ')
            color, index = None, card_input[0]
            if len(card_input) > 1:
                color = card_input[1]

            # Más guards, uno nunca sabe
            try:
                index = int(index)
                if index > 0:
                    index -= 1

                # Submit Uno Card
                await uno.submit_card(index, color)
            except ValueError:
                pass
            return

        try:
            guild_chess_channels = Chess.channels[str(message.guild.id)]
        except KeyError:
            guild_chess_channels = {}

        if message.channel.id in guild_chess_channels and Chess.get_status(message.guild.id) == GS.playing:
            await message.delete()

            chess = Chess.get(message.guild.id)
            if message.channel.id != guild_chess_channels[chess.turn]:
                return

            coords = message.content.lower()
            if len(coords) != 5:
                return
            letters = [coords[0], coords[3]]
            try:
                numbers = map(int, [coords[1], coords[4]])
            except ValueError:
                return
            if all([i in 'abcdefg' for i in letters] +
                   [0 < i < 9 for i in numbers]):
                await chess.submit_move(coords)

    @commands.Cog.listener()
    async def on_voice_state_update(
            self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.guild.id == 754098185449898054:
            try:
                general_channel = self.bot.get_channel(754098185449898056)
                brazil_channel = self.bot.get_channel(808355253141372990)
                in_brazil = utils.in_brazil(member)
                if in_brazil and (after.channel is not None) and after.channel.id != 808355253141372990:
                    await member.move_to(brazil_channel)
                    await general_channel.send(f':x: Ni lo intentes {member.mention}', delete_after=2)
            except KeyError:
                pass

        channel = before.channel
        if channel is None:
            return
        # Sacar a todos si ya no queda ningún humano en el chat de voz
        if not any(not member.bot for member in channel.members):
            for member in channel.members:
                # noinspection PyTypeChecker
                await member.move_to(None)


def setup(client):
    client.add_cog(Events(client))
