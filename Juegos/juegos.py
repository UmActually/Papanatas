from __future__ import annotations
from typing import Optional
from enum import IntEnum


class GS(IntEnum):
    """Juegos Status."""
    idle = 0
    starting = 1
    playing = 2
    unavailable = 3

    @property
    def active(self):
        return self > 0


class UnnecessaryAbstractPlayer:
    def __init__(self, name: str, user_id: int, channel_id: int):
        self.name: str = name
        self.id: int = user_id
        self.channel_id: int = channel_id


class UnnecessaryAbstractGame:
    _games = {}
    channels = {}

    @classmethod
    def guild_set_up(cls, guild_id: int) -> bool:
        return str(guild_id) in cls.channels

    @classmethod
    def get_status(cls, guild_id: int) -> GS:
        """Para saber desde afuera el status antes de crear alguna instancia o algo."""
        if not cls.guild_set_up(guild_id):
            return GS.unavailable
        try:
            game = cls._games[guild_id]
        except KeyError:
            return GS.idle
        return game.status

    @classmethod
    def get(cls, guild_id: int) -> Optional[UnnecessaryAbstractGame]:
        if not cls.guild_set_up(guild_id):
            return
        try:
            game = cls._games[guild_id]
            if game.status == GS.idle:
                cls._games[guild_id] = cls()
        except KeyError:
            cls._games[guild_id] = cls()
        return cls._games[guild_id]

    def __init__(self):
        self.status: int = GS.idle
