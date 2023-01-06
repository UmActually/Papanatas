import discord
from discord.ext import commands

import nlp
import utils
from utils import Guilds, Poll, Checks, Cog


class Polls(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @commands.slash_command(guild_ids=Guilds.all)
    @Checks.default
    async def poll(
            self, ctx, title: discord.Option(str),
            options: discord.Option(str, description='Separa las opciones con ;')):
        """Crear nueva encuesta."""
        await ctx.delete()
        new_poll = Poll(title, options)
        await new_poll.send_to(ctx)
        try:
            utils.polls[ctx.guild.id].append(new_poll)
        except KeyError:
            utils.polls[ctx.guild.id] = [new_poll]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == 765329083759329282:
            return
        try:
            server_polls = utils.polls[payload.guild_id]
        except KeyError:
            return
        for poll in server_polls:
            if payload.message_id == poll.msg.id:
                await poll.update(payload)
                return


def setup(client):
    cog = Polls(client)
    nlp.set_cog_instance(Cog.polls, cog)
    client.add_cog(cog)
