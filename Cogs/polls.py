import discord
from discord.ext import commands

import nlp
import utils
from utils import AnyContext, Guilds, Checks, Emojis, Cog


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
        embed.set_author(name='Encuesta', icon_url=utils.image_url(884568260786389054, 'poll_icon'))
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
