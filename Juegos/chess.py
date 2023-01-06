from __future__ import annotations

import os
from typing import Callable, Optional, Union, Tuple, List
from enum import IntEnum
from random import shuffle

import discord
from PIL import Image

import utils
from utils import Emojis
from Juegos.juegos import \
    GS, UnnecessaryAbstractPlayer, UnnecessaryAbstractGame


# def king_rule():
#     pass
#
#
# def queen_rule():
#     pass
#
#
# def bishop_rule():
#     pass
#
#
# def knight_rule():
#     pass
#
#
# def rook_rule():
#     pass
#
#
# def pawn_rule():
#     pass


king_rule = [1, 7, 8, 9]
queen_rule = [1, 7, 8, 9]
bishop_rule = [7, 9]
knight_rule = [6, 10, 15, 17]
rook_rule = [1, 8]
pawn_rule = [8, 16]


class PZ(IntEnum):
    """Chess piece."""
    aire = 0
    bking = 1
    bqueen = 2
    bbishop = 3
    bknight = 4
    brook = 5
    bpawn = 6
    nking = 7
    nqueen = 8
    nbishop = 9
    nknight = 10
    nrook = 11
    npawn = 12
    king = 13
    queen = 14
    bishop = 15
    knight = 16
    rook = 17
    pawn = 18
    out_of_bounds = 19

    @property
    def color(self) -> Optional[bool]:
        if not self:
            return
        return self > 6

    @property
    def kind(self) -> PZ:
        return eval('PZ.' + self.name[1:])

    @property
    def rule(self) -> List[int]:
        return eval(self.name[1:] + '_rule')


class ChessPlayer(UnnecessaryAbstractPlayer):
    def __init__(self, member: discord.Member):
        super().__init__(member.display_name, member.id, 0)
        self.board_msg: Optional[discord.Message] = None
        self.embed_msg: Optional[discord.Message] = None
        self.color = False
        self.n_pieces = 16
        self.board_path = ''
        self.member = member

    async def set_color(self, guild: discord.Guild, color: Union[bool, int]):
        self.color = bool(color)
        self.channel_id = Chess.channels[str(guild.id)][color]
        self.board_path = f'Resources/Juegos/{guild.id}/{"negras" if color else "blancas"}.png'
        rol = discord.utils.get(guild.roles, name='Negras' if color else 'Blancas')
        await self.member.add_roles(rol)


class Chess(UnnecessaryAbstractGame):
    channels = utils.file('Resources/Juegos/chess_channels.json')
    board: Optional[Image.Image] = None
    pieces_img: Optional[Image.Image] = None
    coords: Optional[Image.Image] = None
    pieces: List[Image.Image] = []
    rules: List[Callable] = []
    b_img = 'Resources/Juegos/blancas.png'
    n_img = 'Resources/Juegos/negras.png'

    @classmethod
    def class_init(cls):
        cls.board = Image.open('Resources/Juegos/tablero.png')
        cls.pieces_img = Image.open('Resources/Juegos/piezas.png')
        cls.coords = Image.open('Resources/Juegos/coords.png')

        cls.pieces = [Image.new('RGBA', (100, 100), (0, 0, 0, 0))]
        for i in range(12):
            left = (i % 6) * 100
            top = (i // 6) * 100
            cls.pieces.append(cls.pieces_img.crop((left, top, left + 100, top + 100)))

    def __init__(self):
        super().__init__()
        if Chess.board is None:
            Chess.class_init()
        self.game: List[PZ] = []
        self.players: List[ChessPlayer] = []
        self.msg: Optional[discord.Message] = None
        self.turn = False
        self.move = 0
        self.creator_id = 0
        self.n_players = 0
        self.dir = ''

    @property
    def embed(self) -> discord.Embed:
        starting = self.status == GS.starting
        embed = discord.Embed(title='Nueva Partida' if starting else 'Partida En Curso').set_author(
            name='AJEDREZ', icon_url=utils.image_url(885640705563820093, kind='jpg'))
        players_str = '\n'.join([f'>> {f"<#{p.channel_id}> " * (not starting)}**{p.name}**' for p in self.players])
        embed.add_field(name='**| Players**', value=players_str + '\nㅤ')
        embed.set_footer(text=f'Solo el creador de la partida puede {"iniciarla" if starting else "terminarla"}.')
        return embed

    @property
    def game_embed(self) -> discord.Embed:
        desc = ''
        for player in self.players:
            if player.color == self.turn:
                desc += '**>> ' + player.name + ': ' + str(player.n_pieces) + '**\n'
            else:
                desc += 'ㅤㅤ         ' + player.name + ': ' + str(player.n_pieces) + '\n'
        embed = discord.Embed(title=f'Turno de **{self.current_player.name}**')
        embed.add_field(name='Jugadores', value=desc, inline=True)
        return embed

    @property
    def current_player(self) -> ChessPlayer:
        return self.players[self.turn]

    @property
    def other_player(self) -> ChessPlayer:
        return self.players[(not self.turn)]

    async def new_game(self, ctx: discord.ApplicationContext):
        self.game = [
            PZ.nrook, PZ.nknight, PZ.nbishop, PZ.nqueen, PZ.nking, PZ.nbishop, PZ.nknight, PZ.nrook
            ] + [PZ.npawn] * 8 + [
            ] + [PZ.aire] * 32 + [
            ] + [PZ.bpawn] * 8 + [
            PZ.brook, PZ.bknight, PZ.bbishop, PZ.bqueen, PZ.bking, PZ.bbishop, PZ.bknight, PZ.brook
        ]
        self.dir = f'Resources/Juegos/{ctx.guild.id}'
        os.mkdir(self.dir)
        self.status = GS.starting
        self.creator_id = ctx.author.id
        await self.add_player(ctx, True)

    async def add_player(self, ctx: Union[discord.ApplicationContext, discord.Interaction], initial=False):
        if self.status == GS.playing or self.n_players > 1:
            return

        if ctx is None:
            # Debug mode
            player = utils.NATAS
        else:
            # Esta consistencia de nombres
            player = ctx.author if initial else ctx.user

        if player.id in [p.id for p in self.players]:
            return

        self.players.append(ChessPlayer(player))
        self.n_players += 1

        if initial:
            self.msg = await ctx.respond(embed=self.embed, view=ChessStartingButtons())
            self.msg = await self.msg.original_message()
        else:
            await self.msg.edit(embed=self.embed)
            await self.start_game()

    async def start_game(self):
        self.status = GS.playing
        shuffle(self.players)
        guild = self.msg.guild
        for color, player in enumerate(self.players):
            await player.set_color(guild, color)
        self.turn = False

        await self.msg.edit(embed=self.embed, view=ChessPlayingButtons())

        embed = utils.emb('El juego está empezando...')

        # Mensajes dummy, en send_boards() se van a editar.
        for player in self.players:
            # noinspection PyTypeChecker
            channel = guild.get_channel(player.channel_id)
            await channel.purge(limit=10)
            player.embed_msg = await channel.send(embed=embed)
            player.board_msg = await channel.send(file=discord.File('Resources/Juegos/tablero.png'))

        await self.send_boards(True)

    async def send_boards(self, initial=False):
        embed = self.game_embed
        if initial:
            embed.set_footer(text=f'Empieza {self.current_player.name}')

        for player in self.players:
            board = Chess.board.copy()
            for i in range(64):
                pz = self.game[i]
                if pz == PZ.aire:
                    continue
                pz_image = Chess.pieces[pz]
                left = (i % 8) * 100
                top = (i // 8) * 100
                board.paste(pz_image, (left, top), pz_image)
            self.game.reverse()
            board.paste(Chess.coords, (0, 0), Chess.coords)
            board.save(player.board_path)

        for player in self.players:
            channel: discord.TextChannel = player.board_msg.channel
            await player.embed_msg.edit(embed=embed)
            await player.board_msg.delete()
            player.board_msg = await channel.send(file=discord.File(player.board_path))

    async def submit_move(self, coords: str):
        try:
            old_index = self.coords_to_index(*coords[:2])
            new_index = self.coords_to_index(*coords[3:])
        except ValueError:
            return

        if not self.is_legal_move(old_index, new_index):
            player = self.current_player
            await player.embed_msg.channel.send('JUEGA BIEN.', delete_after=1)
            return
        if self.game[new_index] != PZ.aire:
            self.other_player.n_pieces -= 1

        # Mover la pieza
        self.game[new_index] = self.game[old_index]
        self.game[old_index] = PZ.aire

        self.turn = not self.turn
        await self.send_boards()

    async def end_game(self):
        for player in self.players:
            rol = discord.utils.get(
                self.msg.guild.roles, name='Negras' if player.color else 'Blancas')
            await player.member.remove_roles(rol)

        for file in os.listdir(self.dir):
            os.remove(f'{self.dir}/{file}')
        os.rmdir(self.dir)

        await self.msg.edit(view=None)
        self.status = GS.idle

    def is_legal_move(self, old_index: int, new_index: int) -> bool:
        old = self.game[old_index]
        new = self.game[new_index]

        # Checar que mueve una suya a un espacio del oponente o aire
        if old == PZ.aire or old.color != self.turn or new.color == self.turn:
            return False
        # Para blancas, subir el index es ir abajo/derecha.
        # Para negras, subir el index es ir arriba/izquierda.
        kind = old.kind
        rival_color = not self.turn
        if self.turn:
            new_index = 63 - new_index
            old_index = 63 - old_index
        diff = new_index - old_index

        def adjacent(pz=True, vertical=0, horizontal=0) -> Union[PZ, int]:
            if pz:
                return self.game[old_index + -1 * horizontal + -8 * vertical]
            return -1 * horizontal + -8 * vertical

        def collision_check(vertical=0, horizontal=0) -> bool:
            if diff > 0:
                vertical = vertical * -1
                horizontal = horizontal * -1
            index = old_index
            while index != new_index:
                index += adjacent(False, vertical, horizontal)
                if self.game[index] != PZ.aire:
                    return False
            return True

        def diagonal_check() -> bool:
            # En diagonal así /
            if diff % 7 == 0:
                return collision_check(1, 1)
            # En diagonal así \
            if diff % 9 == 0:
                return collision_check(1, -1)

        def linear_check() -> bool:
            if diff % 8 == 0:
                return collision_check(1, 0)

        # PEÓN
        if kind == PZ.pawn:
            if diff == adjacent(False, vertical=1):
                return True
            legal = []
            # Al empezar puede brincar dos espacios
            if 48 < old_index < 55 and adjacent(vertical=1) == PZ.aire:
                legal.append(-16)
            # Comer en diagonal
            if adjacent(vertical=1, horizontal=-1).color is rival_color:
                legal.append(-9)
            if adjacent(vertical=1, horizontal=1).color is rival_color:
                legal.append(-7)
            return diff in legal

        # ALFIL
        if kind == PZ.bishop:
            return diagonal_check()

        # CABALLO
        if kind == PZ.knight:
            legal = [6, -6, 10, -10, 15, -15, 17, -17]
            return diff in legal

        # TORRE
        # if kind == PZ.rook:
        return True

    def coords_to_index(self, x: str, y: str) -> int:
        if self.turn:
            # Tablero de negras
            return int(y) * 8 - ord(x) + 96
        # Tablero de blancas
        return int(y) * -8 + ord(x) - 33

    @staticmethod
    def index_to_coords(index: int) -> Tuple[int, int]:
        return index % 8 + 1, 8 - index // 8


class ChessStartingButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Unirse', style=discord.ButtonStyle.green, emoji=Emojis.raised_hand)
    async def join_game(self, _button, interaction: discord.Interaction):
        if Chess.get_status(interaction.guild_id) != 1:
            return
        chess = Chess.get(interaction.guild_id)
        await chess.add_player(interaction)
        if interaction.user.id == 715394802752946199:
            # noinspection PyTypeChecker
            utils.event_loop.create_task(chess.add_player(None))


class ChessPlayingButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Terminar', style=discord.ButtonStyle.danger, emoji=Emojis.x)
    async def end_game(self, _button, interaction: discord.Interaction):
        if Chess.get_status(interaction.guild_id) != 2:
            return
        chess = Chess.get(interaction.guild_id)
        if interaction.user.id not in [chess.creator_id, 715394802752946199]:
            return
        utils.event_loop.create_task(chess.end_game())
        await chess.msg.channel.send('Partida terminada <a:obama:885262941543333888>')
