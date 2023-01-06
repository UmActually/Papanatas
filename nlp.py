from __future__ import annotations

from typing import Union, Optional, Callable, List, Dict

import discord
from discord.ext import commands as _commands
import spacy
from spacy.language import Language
from spacy.tokens import Token, Doc
from spacy.matcher import Matcher
from tabulate import tabulate

import utils
from utils import PseudoContext, Cog, Argument


if not Token.has_extension('less'):
    Token.set_extension('less', default='')


@Language.component('less')
def acentoless(doc: Doc) -> Doc:
    for token in doc:
        # noinspection PyProtectedMember
        token._.less = utils.acentoless(token.text)
    return doc


pattern_soup: dict = utils.file('Resources/patterns.json')
nlp: spacy.Language = spacy.load('es_core_news_sm')
nlp.add_pipe('less', last=True)


def listens(name: Optional[str] = None, inside=Cog.main) -> Callable:
    """Produce un decorator que podemos infiltrar en los comandos de discord. Toda aquella función en
    main.py o los cogs. Se necesita saber la cog en la que se está, porque eventualmente se debe pasar
    la instancia del cog a los Commands."""
    def decorator(func: Callable) -> Callable:
        """No hay ningún wrapper. El decorator simplemente agrega las cosas a los diccionarios y regresa
        la func tal cual."""
        _name = func.__name__ if name is None else name
        command = Command(_name, func, inside)
        command.implement(pattern_soup[_name])
        Command.index[_name] = command
        return func
    return decorator


def set_cog_instance(cog: Cog, instance: _commands.Cog):
    for command in Command.index.values():
        if command.cog == cog:
            command.cog_instance = instance


def closest_valid_token(adjacent: Callable, get_next: bool) -> Optional[dict]:
    resp = ''
    k = 0
    is_valid = False
    while not is_valid:
        k += (1 if get_next else -1)
        resp = adjacent(k)
        is_valid = isinstance(resp, Optional[dict])
    return resp


class Command:
    """Cada comando que lleve un @nlp.listens() se traduce a un Command, donde se guarda la func original,
    la firma (incluyendo los tipos que declara) y lo de los cogs."""

    # Function name -> Command
    index: Dict[str, Command] = {}

    matcher = Matcher(nlp.vocab)
    fallback_matcher = Matcher(nlp.vocab)

    @staticmethod
    async def search(message: discord.Message, content: str):
        """Usando principalmente el Matcher de spacy, busca el comando más acertado, busca sus argumentos, y
        ejecuta el comando. Primero busca usando el matcher normal. Si de plano no se encuentra nada, usa el
        matcher fallback, que es menos estricto. Para sacar los argumentos se usan los matchers particulares
        del comando encontrado."""

        doc = nlp(content)

        table = []
        for token in doc:
            table.append([token.text, token.lemma_, token.pos_, token.dep_])

        table = tabulate(table, headers=['Text', 'Lemma', 'PoS', 'Dep'])
        print('\nTokens:\n', table, '\n')
        # await message.channel.send(f'```{table}```')

        # Búsqueda normal
        command = None
        matches = Command.matcher(doc)
        for match_id, start, end in matches:
            name = nlp.vocab.strings[match_id]
            print(f'Comando detectado: /{name}\nMatch: {doc[start:end]}')
            command = Command.index.get(name, None)
            if command is not None:
                kwargs = command.find_arguments(doc)
                await command.run(message, **kwargs)
                break

        # Búsqueda fallback
        if command is None:
            matches = Command.fallback_matcher(doc)
            for match_id, start, end in matches:
                name = nlp.vocab.strings[match_id]
                print(f'Comando detectado: /{name}\nFallback match: {doc[start:end]}')
                command = Command.index.get(name, None)
                if command is not None:
                    kwargs = command.find_arguments(doc)
                    await command.run(message, **kwargs)
                    break

        if command is None:
            await message.channel.send('Alch no te entendí')

    def __init__(self, name: str, func: Callable, cog: Cog):
        self.name = name
        self.examples: List[str] = []
        self.function = func
        self.signature = utils.get_signature(func, True)
        self.cog = cog
        self.cog_instance = None
        self.arg_matcher = Matcher(nlp.vocab)

    async def run(self, message: discord.Message, **kwargs):
        if len(self.signature) != len(kwargs):
            print('invalid n arguments :(')
            return
        ctx = PseudoContext(message)
        if self.cog:
            # self.cog_instance es 'self' en los métodos de un cog
            # y la única forma de acceder a ese bastardo es en las funciones
            # setup() al final de cada script de cog
            await self.function(self.cog_instance, ctx, **kwargs)
            return
        await self.function(ctx, **kwargs)

    def get_argument(self, name_or_index: Union[int, str]) -> Optional[Argument]:
        if isinstance(name_or_index, int):
            return self.signature[name_or_index]
        for arg in self.signature:
            if arg.name == name_or_index:
                return arg

    def add_arg_pattern(self, name_or_index: Union[int, str], pattern: dict, position='real'):
        arg = self.get_argument(name_or_index)
        setattr(arg, position, pattern)

    def implement(self, patterns: List[List[Dict]]):
        self.examples = patterns.pop(0)

        fallback_patterns = []
        for pattern in patterns:
            fallback_pattern = []
            argument = ''
            # Usar [:] para copiar el array y que no sucedan incidentes.
            for token, adjacent in utils.adjacents(pattern[:]):
                is_impostor = isinstance(token, str)

                prev_token = closest_valid_token(adjacent, False)
                next_token = closest_valid_token(adjacent, True)

                if (argument or token == '!') and prev_token is not None:
                    if not (argument and is_impostor):
                        fallback_pattern.append(token if argument else prev_token)

                if is_impostor:
                    # noinspection PyTypeChecker
                    pattern.remove(token)

                    if '{' in token:
                        argument = token.split(' ')[0]
                        self.add_arg_pattern(argument, prev_token, 'prev')
                        if adjacent(2) == '}':
                            self.add_arg_pattern(argument, next_token, 'real')
                    elif '}' in token:
                        self.add_arg_pattern(argument, next_token, 'next')
                        argument = ''

            if len(fallback_pattern):
                fallback_patterns.append(fallback_pattern)

        for arg in self.signature:
            if arg.real is not None:
                self.arg_matcher.add(f'real_{arg.name}', [[arg.prev, arg.real, arg.next]])
            if arg.prev is not None:
                self.arg_matcher.add(f'prev_{arg.name}', [[arg.prev]])
            if arg.next is not None:
                self.arg_matcher.add(f'next_{arg.name}', [[arg.next]])

        Command.matcher.add(self.name, patterns)
        if len(fallback_patterns):
            Command.fallback_matcher.add(self.name, fallback_patterns)

    def find_arguments(self, doc: Doc) -> dict:
        if not len(self.signature):
            return {}

        args = {}
        matches = self.arg_matcher(doc)

        print(f'\nBuscando parámetros de /{self.name}...')

        for arg in self.signature:
            # Búsqueda normal (con el match real del arg)
            start, end = '', ''
            for match_id, _start, _end in matches:
                kind, name = (nlp.vocab.strings[match_id]).split('_', maxsplit=1)
                if name == arg.name and kind == 'real':
                    start = _start + 1
                    end = _end - 1
                    break

            # Búsqueda fallback (con el match antes y/o match después)
            # Cuando un arg no se cierra con '}', se matchea todo lo que esté después de prev.
            if start == '' and end == '':
                for match_id, _start, _end in matches:
                    kind, name = (nlp.vocab.strings[match_id]).split('_', maxsplit=1)
                    if name != arg.name:
                        continue
                    if kind == 'prev':
                        start = _end
                    else:
                        end = _start

            # Se necesita usar eval en caso de que no haya start o end. Por eso
            # se utilizan strings vacíos arriba.
            value = eval(f'doc[{start}:{end}]').text

            # Hay que castear si no es un string. Python es basado pero no tanto.
            try:
                value = arg.cls(value)
                args[arg.name] = value
            except ValueError:
                pass

        print(args)
        return args


# Comandos exclusivos de NLP


@listens()
async def say(ctx: PseudoContext, text: str):
    await ctx.send(text)
