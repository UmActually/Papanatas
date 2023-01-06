from __future__ import annotations

from random import randint, shuffle
from typing import Union, Optional, List

import discord

import utils
from utils import Emojis
from Juegos.juegos import \
    GS, UnnecessaryAbstractPlayer, UnnecessaryAbstractGame


class UnoCard:
    encode = {
        'r': 'r', 'y': 'y', 'g': 'g', 'b': 'b',
        'rojo': 'r', 'roja': 'r', 'amarillo': 'y', 'amarilla': 'y', 'verde': 'g', 'azul': 'b'
    }

    decode = {
        'r': ' (ROJO)', 'y': '  (AMARILLO)', 'g': '  (VERDE)', 'b': '  (AZUL)',
    }

    def __init__(self, raw: str):
        self.raw = raw
        self.pretty = raw.split(':')[1]
        self.is_special = len(self.pretty) != 2
        self.requires_color_input = self.pretty in ['mas4', 'wild']
        self.color = '' if self.is_special else self.pretty[0]
        self.number = '' if self.is_special else self.pretty[1]

    @property
    def as_discard(self):
        if self.is_special:
            return self.raw + UnoCard.decode[self.color]
        return self.raw

    def set_special_color(self, color: str):
        self.color = color


class UnoPlayer(UnnecessaryAbstractPlayer):
    def __init__(self, name: str, user_id: int, channel_id: int):
        super().__init__(name, user_id, channel_id)
        self.cards: List[UnoCard] = []
        self.n_cards = 0
        self.embed_msg = None
        self.discard_msg = None
        self.cards_msg = None

    @property
    def has_mas4(self):
        return 'mas4' in [c.pretty for c in self.cards]

    def get_initial_cards(self, deck: List[str]):
        self.n_cards = 7
        for _ in range(7):
            self.cards.append(UnoCard(deck.pop(0)))

    def draw_cards(self, amount: int, deck: List[str]):
        self.n_cards += amount
        for _ in range(amount):
            self.cards.append(UnoCard(deck.pop(0)))


class Uno(UnnecessaryAbstractGame):
    """Para jugar nada menos que UNO. A cada server le corresponde una instancia de Uno. Se guardan en el
    diccionario de utils.uno."""

    channels = utils.file('Resources/Juegos/uno_channels.json')

    def __init__(self):
        super().__init__()
        self.creator_id = 0
        self.msg = None
        self.players: List[UnoPlayer] = []
        self.n_players = 0
        self.deck = []
        self.turn = 0
        self.acum = 0
        self.clockwise = True
        self.discard: UnoCard = UnoCard(Emojis.mas4)
        self.available_channels = []
        self.spectators = []
        self.spectator = None

    @property
    def embed(self) -> discord.Embed:
        starting = self.status == GS.starting
        embed = discord.Embed(title='Nueva Partida' if starting else 'Partida En Curso').set_author(
            name='UNO', icon_url=utils.image_url(885640705563820093, kind='jpg'))
        players_str = '\n'.join([f'>> <#{p.channel_id}> **{p.name}**' for p in self.players])
        embed.add_field(name='**| Players**', value=players_str + '\nㅤ')
        embed.set_footer(text=f'Solo el creador de la partida puede {"iniciarla" if starting else "terminarla"}.')
        return embed

    @property
    def game_embed(self) -> discord.Embed:
        n_cards = ''
        arrow = ':arrow_down:' if self.clockwise else ':arrow_up:'
        for player in self.players:
            if player == self.current_player:
                n_cards += '**>> ' + player.name + ': ' + str(player.n_cards) + '**\n'
            else:
                n_cards += 'ㅤㅤ         ' + player.name + ': ' + str(player.n_cards) + '\n'
        embed = discord.Embed(title=f'Turno de **{self.current_player.name}**')
        embed.add_field(name='Jugadores', value=n_cards, inline=True)
        embed.add_field(name='Sentido', value=f'ㅤ    {arrow}', inline=True)
        return embed

    @property
    def current_player(self) -> UnoPlayer:
        return self.players[self.turn]

    @property
    def next_player(self) -> UnoPlayer:
        return self.players[self.next_turn('')]

    def next_turn(self, card: str, change_turn=False) -> int:
        """Solo cuando change_turn es True cambia el turno. De lo contrario,
        solo regresa el número."""
        increment = 1 if self.clockwise else -1
        if card == 'skip':
            increment *= 2
        elif card == 'reverse':
            increment *= -1
            if change_turn:
                self.clockwise = not self.clockwise
        turn = (self.turn + increment) % self.n_players
        if change_turn:
            self.turn = turn
        return turn

    async def new_game(self, ctx: discord.ApplicationContext):
        self.status = GS.starting
        self.creator_id = ctx.author.id
        self.available_channels = Uno.channels[str(ctx.guild.id)][0][:]
        self.spectator = Uno.channels[str(ctx.guild.id)][1]
        await self.add_player(ctx, True)

    async def add_player(self, ctx: Union[discord.ApplicationContext, discord.Interaction], initial=False):
        if len(self.available_channels) == 0:
            return

        if ctx is None:
            # Debug mode
            player = utils.NATAS
        else:
            # Esta consistencia de nombres
            player = ctx.author if initial else ctx.user

        if player.id in [p.id for p in self.players]:
            return

        self.players.append(UnoPlayer(player.display_name, player.id, self.available_channels.pop(0)))
        self.n_players += 1

        if initial:
            msg: discord.WebhookMessage = await ctx.respond(embed=self.embed, view=UnoStartingButtons())
            self.msg = await ctx.fetch_message(msg.id)
        else:
            await self.msg.edit(embed=self.embed)

        rol = discord.utils.get(self.msg.guild.roles, name='P' + str(self.n_players))
        await player.add_roles(rol)

    async def start_game(self):
        self.status = GS.playing
        await self.msg.edit(embed=self.embed, view=UnoPlayingButtons())
        # spectator_channel = self.msg.guild.get_channel(self.spectator)
        # history = await spectator_channel.history(limit=1).flatten()
        history = [self.msg]
        self.spectator = history[0]

        self.deck = utils.file('Resources/Juegos/deck.txt').split(' ')

        for k in range(32):
            # El deck (Resources/Juegos/deck.txt) tiene cada emoji de carta sin repetirse.
            # Originalmente tenía pensado una razón de 3:6:1.
            if ('re' in self.deck[k]) or ('sk' in self.deck[k]):
                # Reversa / Salto
                duplicates = 9
            elif ('ma' in self.deck[k]) or ('wi' in self.deck[k]):
                # +4 / Wild
                duplicates = 14
            else:
                # Cartas normales
                duplicates = 4
            for _ in range(duplicates):
                self.deck.append(self.deck[k])
        shuffle(self.deck)

        # Queremos que la discard siempre sea carta normal al inicio
        k = 0
        while ('re' in self.deck[k]) or ('wi' in self.deck[k]) or ('sk' in self.deck[k]) or ('ma' in self.deck[k]):
            k += 1
        self.discard = UnoCard(self.deck.pop(k))

        for player in self.players:
            player.get_initial_cards(self.deck)

        self.turn = randint(0, self.n_players - 1)

        guild = self.msg.guild
        embed = utils.emb('El juego está empezando...')

        # Mensajes dummy, en send_cards() se van a editar.
        for player in self.players:
            channel = guild.get_channel(player.channel_id)
            await channel.purge(limit=10)
            player.embed_msg = await channel.send(embed=embed)
            player.discard_msg = await channel.send('ㅤ')
            player.cards_msg = await channel.send('ㅤ')

        await self.send_cards(True)

    async def send_cards(self, initial=False):
        acum_posible = self.acum > 0 and self.current_player.has_mas4
        discard = self.discard.as_discard
        embed = self.game_embed
        remove_me = False
        if initial:
            embed.set_footer(text=f'Empieza {self.current_player.name}')

        for k, player in enumerate(self.players):
            players_turn = k == self.turn
            if remove_me:
                embed.remove_footer()
                remove_me = False

            if acum_posible and players_turn:
                embed.set_footer(text='Eh tienes un +4, puedes acumular.')
                remove_me = True

            cards = ''.join([c.raw for c in player.cards])
            await player.embed_msg.edit(embed=embed, view=UnoGameButtons() if players_turn else None)
            await player.discard_msg.edit(content=discard)
            await player.cards_msg.edit(content=cards)

        if self.spectators:
            embed.add_field(name='ㅤ', value='ㅤ')
            embed.add_field(name='Centro', value=discard, inline=False)
            self.show_all_cards(embed)
            await self.spectator.edit(embed=embed)

    async def submit_card(self, index: int, new_color: Optional[str] = None):
        player: UnoPlayer = self.current_player
        try:
            card: UnoCard = player.cards[index]
        except IndexError:
            return
        if card.requires_color_input:
            if new_color is None:
                return
            try:
                new_color = UnoCard.encode[new_color]
            except KeyError:
                return

        if card.pretty == 'mas4':
            # Los +4's, según las reglas oficiales, no se pueden acumular
            # Pero UNO no sabe jugar UNO
            # En este código apoyamos la acumulación de +4's
            self.acum += 4
            next_player: UnoPlayer = self.next_player
            if not next_player.has_mas4:
                next_player.draw_cards(self.acum, self.deck)
                self.acum = 0
        else:
            # Es salto o reversa
            if card.is_special and not card.requires_color_input:
                new_color = self.discard.color

            # No le supo
            if self.acum > 0 and player.has_mas4:
                player.draw_cards(self.acum, self.deck)

            # Es carta normal, checar color o número
            if not card.is_special and not (card.color == self.discard.color or card.number == self.discard.number):
                return

        player.n_cards -= 1
        card = player.cards.pop(index)

        self.discard = card
        if new_color is not None:
            self.discard.set_special_color(new_color)

        if player.n_cards == 0:
            await self.win_game(player)
            return

        self.next_turn(card.pretty, True)
        await self.send_cards()

    async def draw_card(self):
        player: UnoPlayer = self.current_player
        player.draw_cards(1, self.deck)
        self.next_turn('', True)
        await self.send_cards()

    async def win_game(self, winner: UnoPlayer):
        embed = discord.Embed(title='Stats')
        embed.add_field(name='Carta Final', value=self.discard.as_discard)
        self.show_all_cards(embed)

        await self.msg.channel.send(embed=embed)
        await self.msg.channel.send(f'Ganó **{winner.name}**, ya bye')
        await self.end_game()

    async def end_game(self):
        for i, player in enumerate(self.players):
            member = await self.msg.guild.fetch_member(player.id)
            rol = discord.utils.get(self.msg.guild.roles, name='P' + str(i + 1))
            await member.remove_roles(rol)

        for spectator in self.spectators:
            member = await self.msg.guild.fetch_member(spectator)
            rol = discord.utils.get(self.msg.guild.roles, name='Espectador')
            await member.remove_roles(rol)
            self.spectators.append(member.id)

        await self.msg.edit(view=None)
        self.status = GS.idle

    async def spectate(self, ctx: discord.Interaction):
        member = ctx.user
        if member.id in [p.id for p in self.players]:
            await self.msg.channel.send(
                f'{member.mention} por razones obvias, un jugador no puede espectar a los demás.')
            return
        rol = discord.utils.get(self.msg.guild.roles, name='Espectador')
        await member.add_roles(rol)
        self.spectators.append(member.id)

    def show_all_cards(self, embed: discord.Embed):
        """Extiende el embed que recibe. Se usa en win_game() y en el modo espectador."""
        for player in self.players:
            if len(player.cards) > 0:
                embed.add_field(name=player.name, value=''.join([c.raw for c in player.cards]), inline=False)
        deck_str = ''.join(self.deck)
        if len(deck_str) > 1000:
            deck_str = deck_str[:1000]
            while True:
                if deck_str[-1] == '>':
                    break
                else:
                    deck_str = deck_str[:-1]
            deck_str += '...'
        embed.add_field(name='Deck', value=deck_str, inline=False)


class UnoStartingButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Unirse', style=discord.ButtonStyle.secondary, emoji=Emojis.raised_hand)
    async def join_game(self, _button, interaction: discord.Interaction):
        if Uno.get_status(interaction.guild_id) != 1:
            return
        uno = Uno.get(interaction.guild_id)
        await uno.add_player(interaction)
        if interaction.user.id == 715394802752946199:
            # noinspection PyTypeChecker
            await uno.add_player(None)

    @discord.ui.button(
        label='Iniciar', style=discord.ButtonStyle.green, emoji=Emojis.check)
    async def start_game(self, _button, interaction: discord.Interaction):
        if Uno.get_status(interaction.guild_id) != 1:
            return
        uno = Uno.get(interaction.guild_id)
        if interaction.user.id != uno.creator_id:
            return
        # La ejecución de esta madre tarda demasiado. Si uso un await, va a aparecer
        # 'interaction failed' en el botón. Con create_task no se tiene que esperar.
        utils.event_loop.create_task(uno.start_game())


class UnoPlayingButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Espectar', style=discord.ButtonStyle.secondary, emoji=Emojis.eyes)
    async def spectate_game(self, _button, interaction: discord.Interaction):
        if Uno.get_status(interaction.guild_id) != 2:
            return
        uno = Uno.get(interaction.guild_id)
        await uno.spectate(interaction)

    @discord.ui.button(
        label='Terminar', style=discord.ButtonStyle.danger, emoji=Emojis.x)
    async def end_game(self, _button, interaction: discord.Interaction):
        if Uno.get_status(interaction.guild_id) != 2:
            return
        uno = Uno.get(interaction.guild_id)
        if interaction.user.id not in [uno.creator_id, 715394802752946199]:
            return
        utils.event_loop.create_task(uno.end_game())
        await uno.msg.channel.send('Partida terminada <a:obama:885262941543333888>')


class UnoGameButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Comer', style=discord.ButtonStyle.secondary, emoji=Emojis.que)
    async def draw_card(self, _button, interaction: discord.Interaction):
        if Uno.get_status(interaction.guild_id) != 2:
            return
        uno = Uno.get(interaction.guild_id)
        await uno.draw_card()
