from __future__ import unicode_literals

import os
from enum import IntEnum
from typing import Optional, Callable, AsyncIterator

import discord
from discord import Option
from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw

import utils
from utils import Guilds


DEFAULT_PATH = 'Resources/Memes/meem.jpg'


class Anchor(IntEnum):
    """Vertical Anchor."""
    top = 0
    center = 1
    bottom = 2

    def text_y(self, image_height: int) -> int:
        resp = [
            image_height / 20,  # Top
            image_height / 2,  # Center
            image_height - image_height / 20  # Bottom
        ]
        return int(resp[self])

    @property
    def offset(self) -> float:
        return self / 2


def meemify(input_path: str = DEFAULT_PATH, output_path: str = DEFAULT_PATH, caption: str = '',
            anchor: Anchor = Anchor.center, y: Optional[int] = None, y_correction: int = 0, x_offset: int = 0,
            font_size_cap: Optional[int] = None, white=False, stroke=False, impact_font=False,
            double_caption=False) -> None:
    if not input_path or not caption:
        raise ValueError
    filename = input_path.split('/')[-1].split('.')[0]
    color = (255, 255, 255) if white else (0, 0, 0)
    font = f'Resources/Memes/{"impact" if impact_font else "arial"}.ttf'
    image = Image.open(input_path)
    idraw = ImageDraw.Draw(image)
    line_length_limit = 245 if filename == 'jimmy' else int(image.width * 0.8)
    font_size_limits = (int(image.height / 11), font_size_cap)
    font_size = int(image.width / 5.28)
    has_space = ' ' in caption
    next_caption = ''
    if double_caption:
        anchor = Anchor.top
        caption, next_caption = caption.split(';', maxsplit=1)
    if y is None:
        y = anchor.text_y(image.height)

    # Hacer que el texto quepa en una sola línea
    fmt = ImageFont.truetype(font, font_size)
    text_width, text_height = idraw.textsize(caption, fmt)
    while text_width > line_length_limit:
        font_size -= 1
        if has_space and font_size < font_size_limits[0]:
            # Ya no tiene caso seguir haciendo el texto más pequeño,
            # hay que empezar a hacerlo multilínea
            break
        fmt = ImageFont.truetype(font, font_size)
        text_width, text_height = idraw.textsize(caption, fmt)

    if has_space and (font_size < font_size_limits[0] or filename == 'jimmy'):
        words = caption.split(' ')
        font_size = font_size_limits[0]
        # if font_size_limits[1] is not None:
        #     font_size = min(font_size, font_size_limits[1])
        fmt = ImageFont.truetype(font, font_size)
        caption = ''
        acum_width = 0
        for word in words:
            word_width = idraw.textsize(word, fmt)[0]
            acum_width += word_width
            if acum_width > line_length_limit:
                # New line
                acum_width = word_width
                y += y_correction
                caption += '\n' + word + ' '
            else:
                caption += word + ' '
        caption = caption[:-1]

    if font_size_limits[1] is not None and font_size > font_size_limits[1]:
        fmt = ImageFont.truetype(font, font_size_limits[1])

    text_width, text_height = idraw.textsize(caption, font=fmt)
    if filename == 'skipper' and text_width > 400:
        # Hay una imagen de Skipper editada para que le quepa más texto
        image = Image.open('Resources/Memes/skipper2.jpg')
        idraw = ImageDraw.Draw(image)

    # Colocar el texto en medio horizontalmente,
    # y desplazarlo por x_offset
    x = (image.width - text_width) / 2 + x_offset

    # Si el texto está anclado abajo o en medio verticalmente,
    # hay que subir la Y para acomodar todas las nuevas líneas
    y -= int(text_height * anchor.offset)
    y = max(y, 0)

    kwargs = {'xy': (x, y), 'text': caption, 'fill': color, 'font': fmt}
    if stroke:
        if filename == 'meem':
            stroke_width = int(font_size / 30) + 1 if impact_font else int(font_size / 32) + 1
        else:
            stroke_width = 4
        kwargs.update({
            'stroke_fill': (0, 0, 0) if white else (255, 255, 255),
            'stroke_width': stroke_width
        })
    idraw.text(**kwargs)
    image.save(output_path)

    if double_caption:
        meemify(output_path, output_path, next_caption.strip(' '), Anchor.bottom,
                white=white, stroke=stroke, impact_font=impact_font)


skipper = {
    'input_path': 'Resources/Memes/skipper.jpg',
    'y': 260,
    'y_correction': -5,
}

able = {
    'input_path': 'Resources/Memes/able.jpg',
    'anchor': Anchor.bottom,
    'y': 360,
    'y_correction': -1
}

yoda = {
    'input_path': 'Resources/Memes/yoda.jpg',
    'y': 200,
    'y_correction': 8,
    'font_size_cap': 55,
    'white': True,
    'stroke': True,
    'impact_font': True
}

jimmy = {
    'input_path': 'Resources/Memes/jimmy.jpg',
    'y': 140,
    'y_correction': -2,
    'x_offset': 100,
    'font_size_cap': 100
}

chtm = {
    'input_path': 'Resources/Memes/chtm.jpg',
    'y': 45,
    'font_size_cap': 90,
}


async def get_last_image(history: AsyncIterator[discord.Message]) -> bool:
    found = False
    async for message in history:
        if message.author.id == utils.NATAS_ID:
            continue
        for file in message.attachments:
            if file.filename.split('.')[-1].lower() in ['jpg', 'jpeg', 'webp', 'png']:
                # noinspection PyTypeChecker
                await file.save('Resources/Memes/meem.png')
                found = True
                break
        if found:
            break
    return found


class Memes(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @staticmethod
    def meme_command(name: str) -> Callable:
        @commands.command(name=name)
        async def command(_self, ctx: commands.Context, *, text: str):
            meemify(caption=text, **eval(name))
            await ctx.send(file=discord.File('Resources/Memes/meem.jpg'))
            os.remove('Resources/Memes/meem.jpg')

        return command

    skipper = meme_command('skipper')
    able = meme_command('able')
    yoda = meme_command('yoda')
    jimmy = meme_command('jimmy')
    chtm = meme_command('chtm')

    @commands.slash_command(guild_ids=Guilds.all)
    async def meme(self, ctx: discord.ApplicationContext, text: str,
                   position: Option(str, choices=['top', 'center', 'bottom', 'top & bottom'], default='center'),
                   color: Option(str, choices=['white', 'black'], default='white'),
                   font: Option(str, choices=['Arial', 'Impact'], default='white'),
                   stroke: Option(bool, default=False)):
        """Crear un meme con la imagen más reciente del canal."""

        found = await get_last_image(ctx.history(limit=20))
        if not found:
            await ctx.respond(embed=utils.emb('No encontré ninguna imagen reciente en el canal.'))
            return
        await ctx.respond('...')

        double_caption = False
        if position == 'top & bottom':
            position = 'top'
            double_caption = True

        meemify(
            input_path='Resources/Memes/meem.png',
            output_path='Resources/Memes/meem.png',
            caption=text,
            anchor={
                'top': Anchor.top,
                'center': Anchor.center,
                'bottom': Anchor.bottom
            }[position],
            white=(color == 'white'),
            stroke=stroke,
            impact_font=(font == 'Impact'),
            double_caption=double_caption
        )

        await ctx.channel.send(file=discord.File('Resources/Memes/meem.png'))
        os.remove('Resources/Memes/meem.png')

    @commands.Cog.listener('on_message')
    async def on_message_nlp(self, message: discord.Message):
        if not utils.is_worthy(message):
            return

        content = message.content.lower()
        if any(content.endswith(pattern) for pattern in
               [' le gana', ' le gano', ' les gano', ' les gana', ' le ganan', ' les ganan']):
            kwargs = skipper
        elif content.endswith('able') and len(content) < 70:
            kwargs = able
        elif any(content.startswith(pattern) for pattern in
                 ['mucho ', 'mucha ', 'muchos ', 'muchas ']):
            kwargs = yoda
        elif any(content.startswith(pattern) for pattern in
                 ['esta va pa ', 'esta va pal ']):
            kwargs = chtm
        else:
            return

        meemify(caption=message.content.replace('\n', ' '), **kwargs)
        await message.channel.send(file=discord.File('Resources/Memes/meem.jpg'))
        os.remove('Resources/Memes/meem.jpg')


def setup(client):
    client.add_cog(Memes(client))
