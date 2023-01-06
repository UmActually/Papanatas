import json
from functools import lru_cache
from pathlib import Path
from typing import Union, Optional, Tuple, List
import discord
import utils


DEFAULT_OPTS = ['--default-search', 'auto', '--no-playlist']


def error_embed(query):
    embed = discord.Embed(description='Hubo un error en YouTubeDL.')
    desc = '>> No sabes escribir.\n>> El video es muy largo y Discord es un inepto débil pay-to-win.\n' \
           '>> El video tiene restricción demográfica o geográfica\n>> YouTube sabe que soy un robot y ' \
           'desconfía de mí.'
    embed.add_field(name='**| Búsqueda**', value=f'`{query}`', inline=False)
    embed.add_field(name='**| Causas comunes de errores**', value=desc, inline=False)
    embed.set_footer(text='Si se trata de lo último, se arregla reiniciándome. Contacta al WellActually de tu área '
                          'para ver la posibilidad de un PapanatasReboot.')
    return embed


def rename(path: Path, name: str) -> Path:
    return path.rename(path.with_stem(name))


def ld_0(num: Union[int, str]) -> str:
    """Leading zero."""
    return '0' * (int(num) < 10) + num


def get_timestamp(tm: str) -> str:
    """Formatear bonito un string de tiempo."""
    units = tm.split(':')
    if len(units) == 1:
        return f'00:00:{ld_0(units[0])}'
    if len(units) == 2:
        return f'00:{ld_0(units[0])}:{units[1]}'
    return f'{ld_0(units[0])}:{units[1]}:{units[2]}'


def this_is_way_too_much_for_discord(tm: str) -> bool:
    """Lo que el nombre dice."""
    units = tm.split(':')
    if len(units) == 1:
        return False
    if len(units) == 2:
        return (int(units[0]) * 60 + int(units[1])) > 360
    return True


def pretty_youtube_url(url: str) -> str:
    """En cel, compartir un video de yt te da la URL corta. Eso hace petar a mi compa youtube-dl."""
    if 'youtu.' in url:
        return f'https://www.youtube.com/watch?v={(url.split("youtu.be/")[1]).strip("/")}'
    return url


async def download(query: str, opts: Optional[List[str]] = None) -> Optional[Path]:
    if opts is None:
        opts = ['--format', 'worst']
    start_time, end_time = [None, None]
    if query[0].isnumeric():
        start_time = get_timestamp(query.split(' ')[0])
        end_time = get_timestamp(query.split(' ')[1])
        query = ' '.join(query.split(' ')[2:])

    query = pretty_youtube_url(query.strip())

    # Conseguir título y duración
    code, out = utils.run(
        'youtube-dl', '-o', '%(title)s.%(ext)s', '--restrict-filenames', '--get-filename', '--get-duration',
        *DEFAULT_OPTS, query, get_stdout=True)
    if code != 0:
        return

    filename, video_length = out.strip(' \n').split('\n')
    path = Path(filename).resolve()

    # No vaya discord a llorar
    if this_is_way_too_much_for_discord(video_length):
        return

    # Descargar
    code, out = utils.run(
        'youtube-dl', '-o', '%(title)s.%(ext)s', '--restrict-filenames',
        *DEFAULT_OPTS, *opts, query, get_stdout=False)
    if code != 0:
        return

    # Ponerle de nombre el título del video
    if not path.exists():
        for file in Path.cwd().rglob('*'):
            if file.suffix in ['.m4a', '.mp3', '.mp4', '.webm', '.mov']:
                path = file
                break
        else:
            return

    # Para trimear el video
    if start_time is not None:
        temp = rename(path, 'TEMP')
        code, out = utils.run(
            'ffmpeg', '-i', str(temp), '-ss', start_time, '-to', end_time, '-c:v', 'copy',
            '-c:a', 'copy', '-shortest', str(path), get_stdout=False)
        temp.unlink(missing_ok=True)
        if code != 0:
            return

    return path


@lru_cache(maxsize=None)
def get_title_url(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Consigue el título del video y el URL que lleva directamente a este en formato mp3."""
    query = pretty_youtube_url(query)

    # q: Quiet
    # j: JSON con la info del video
    # x: Extraer audio
    # 4: Forzar IPv4
    code, out = utils.run(
        'youtube-dl', '-qjx4', '--audio-format', 'mp3', *DEFAULT_OPTS, query, get_stdout=True)
    if code != 0:
        return None, None

    info = json.loads(out)
    try:
        title = info['title']
        url = info['formats'][0]['url']
    except KeyError:
        title = info['entries'][0]['title']
        url = info['entries'][0]['formats'][0]['url']

    return title, url
