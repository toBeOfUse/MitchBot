import asyncio
from io import BytesIO
import json
from os import PathLike
import re
import sqlite3
from typing import Optional
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import random
from timeit import default_timer as timer
import base64
import statistics
import subprocess

from tornado.httpclient import AsyncHTTPClient
from cairosvg import svg2png
import discord
from PIL import Image, ImageFont, ImageDraw

from db.queries import get_word_frequency, get_wiktionary_trie
from textresources import RandomNoRepeats
from images.svg_hexagon_generator import make_hexagon


class PuzzleRenderer:
    """Base class for subclasses to override; they should implement __init__, render,
    and __repr__, on principle and so they work with instances of RandomNoRepeats.
    available_renderers should be populated with instances of subclasses to make them
    chooseable by Puzzle.render()."""
    available_renderers = []

    def __init__(self):
        raise NotImplementedError()

    def render(self) -> bytes:
        raise NotImplementedError()

    def __repr__(self) -> str:
        raise NotImplementedError()


class Puzzle():
    """
    Instance of an NYT Spelling Bee puzzle. The puzzle consists of 6 outer letters
    and one central letter; players must use the central letter and any of the outer
    letters to create words that are at least 4 letters long. At least one "pangram,"
    a word that uses every letter, can be formed. This class stores the necessary
    data to represent the puzzle and judge answers, has serialization mechanisms to
    save the puzzle and the answers that have come in so far in a simple SQLite
    database, can render itself to a PNG, and includes a functions to allow it to
    interact with discord Message objects.
    """

    # constants returned by `guess(word)`:
    wrong_word = 1
    good_word = 2
    pangram = 3

    def __init__(
            self,
            originally_loaded: int,
            center: str,
            outside: list[str],
            pangrams: list[str],
            answers: list[str],
            gotten_words: set = set(),
            db_path: PathLike = "db/puzzles.db"):
        self.timestamp = originally_loaded
        self.center = center.upper()
        self.outside = [l.upper() for l in outside]
        self.pangrams = set(p.lower() for p in pangrams)
        self.answers = set(a.lower() for a in answers)
        for word in self.pangrams:
            self.answers.add(word)  # shouldn't be necessary but just in case
        self.gotten_words = set(w.lower() for w in gotten_words)
        self.message_id: int = -1
        self.message: Optional[discord.Message] = None
        self.db_path = db_path

    def __eq__(self, other):
        return self.center+self.outside == other.center+other.outside

    @property
    def percentageComplete(self):
        return round(len(self.gotten_words) / len(self.answers) * 100, 1)

    def does_word_count(self, word: str) -> bool:
        return word.lower() in self.answers

    def is_pangram(self, word: str) -> bool:
        return word.lower() in self.pangrams

    def guess(self, word: str) -> int:
        """
        determines whether a word counts for a point and/or is a pangram. uses
        arbitrary constants defined on the class.
        """
        w = word.lower()
        if self.is_pangram(w):
            self.gotten_words.add(w)
            self.save()
            return self.pangram
        elif self.does_word_count(w):
            self.gotten_words.add(w)
            self.save()
            return self.good_word
        else:
            return self.wrong_word

    def get_unguessed_words(self) -> list[str]:
        """returns the heretofore unguessed words in a list sorted from the least to
        the most common words."""
        unguessed = list(self.answers - self.gotten_words)
        unguessed.sort(key=lambda w: get_word_frequency(w))
        return unguessed

    def get_wiktionary_alternative_answers(self) -> list[str]:
        """
        Returns the words that use the required letters and are english words
        according to Wiktionary (according to data obtained by
        https://github.com/tatuylonen/wiktextract) but aren't in the official answers
        list
        """
        start = timer()
        wiktionary_words = get_wiktionary_trie()
        all_letters = [x.lower() for x in self.outside+[self.center]]
        candidates = wiktionary_words.search_words_by_letters(all_letters)
        end = timer()
        print("obtaining wiktionary words took", round((end-start)*1000, 2), "ms")

        result = []
        for word in candidates:
            # i probably filtered the dataset for some of these characteristics at
            # some point but i forget which ones so whatever better safe than sorry
            if self.center not in word.upper():
                continue
            if len(word) < 4:
                continue
            if word.lower() in self.answers:
                continue
            if word.lower() != word:
                continue
            characters_count = True
            for character in word:
                if character.upper() not in (self.outside + [self.center]):
                    characters_count = False
                    break
            if not characters_count:
                continue
            result.append(word)
        return result

    def render(self, renderer: PuzzleRenderer = None):
        """If you do not pass in an instance of a subclass of PuzzleRenderer, one
        will be provided for you from the PuzzleRenderer.available_renderers
        variable."""
        if renderer is None:
            source = RandomNoRepeats(PuzzleRenderer.available_renderers, "puzzle_renderers")
            renderer = source.get_item()
        return renderer.render(self)

    def associate_with_message(self, message: discord.Message):
        """The message that was most recently passed to this function will be edited
        to append percentage completeness updates to it as guesses come in. WARNING:
        parenthesized content in the message text will not survive such an update.
        The message's id will be serialized by the `save()` function and can be used
        to retrieve the message itself for Puzzles loaded through
        `retrieve_last_saved`."""
        self.message = message
        self.message_id = message.id

    @classmethod
    async def fetch_from_nyt(cls) -> "Puzzle":
        client = AsyncHTTPClient()
        response = await client.fetch("https://www.nytimes.com/puzzles/spelling-bee")
        html = response.body.decode("utf-8")
        game_data = re.search("window.gameData = (.*?)</script>", html)
        if game_data:
            game = json.loads(game_data.group(1))["today"]
            return cls(
                int(datetime.now().timestamp()),
                game["centerLetter"],
                game["outerLetters"],
                game["pangrams"],
                game["answers"])

    async def respond_to_guesses(self, message: discord.Message):
        """
        Discord bot-specific function for awarding points in the form of reactions
        """
        num_emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        words = re.sub("\W", " ", message.content).split()
        points = 0
        pangram = False
        for word in words:
            guess_result = self.guess(word)
            if guess_result == Puzzle.good_word:
                points += 1
            if guess_result == Puzzle.pangram:
                points += 1
                pangram = True
        if points > 0:
            await message.add_reaction("👍")
            if points > 1:
                for num_char in str(points):
                    await message.add_reaction(num_emojis[int(num_char)])
        if pangram:
            await message.add_reaction("🍳")
        if self.percentageComplete > 0 and self.message is not None:
            base_content = re.sub("\(.*\)", "", self.message.content).strip()
            await self.message.edit(
                content=(base_content
                         + f" ({self.percentageComplete}% complete)"
                         )
            )

    def save(self, db_path=None):
        """Serializes the puzzle and saves it in a SQLite database."""
        if db_path is None:
            db_path = self.db_path
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        cur.execute("""create table if not exists puzzles
            (timestamp integer primary key, message_id integer, center text, outside text,
            pangrams text, answers text, gotten_words text);""")
        cur.execute("""create index if not exists chrono on puzzles (timestamp desc);""")
        cur.execute(
            """insert or replace into puzzles
            (timestamp, message_id, center, outside, pangrams, answers, gotten_words)
            values (?, ?, ?, ?, ?, ?, ?)""",
            (self.timestamp, self.message_id, self.center, json.dumps(list(self.outside)),
             json.dumps(list(self.pangrams)),
             json.dumps(list(self.answers)),
             json.dumps(list(self.gotten_words))))
        db.commit()
        db.close()

    @classmethod
    def retrieve_last_saved(cls, db_path: str = "db/puzzles.db") -> Optional["Puzzle"]:
        """Retrieves the most recently saved puzzle from the SQLite database. The
        only thing lost through serialization is the self.message instance variable,
        which stores an object of type discord.Message, which needs to be retrieved
        by a discord client and passed to associate_with_message in order for said
        message to be updated with completion information upon future guesses."""
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        try:
            latest = cur.execute("""select 
                timestamp, message_id, center, outside, pangrams, answers, gotten_words
                from puzzles order by timestamp desc limit 1""").fetchone()
            if latest is None:
                db.close()
                return None
            else:
                db.close()
                loaded_puzzle = cls(latest[0], latest[2], *[json.loads(x) for x in latest[3:]])
                loaded_puzzle.message_id = latest[1]
                return loaded_puzzle
        except:
            print("couldn't load latest puzzle from database")
            traceback.print_exc()
            db.close()
            return None


class SVGTemplateRenderer(PuzzleRenderer):
    def __init__(self, template_path: PathLike):
        self.template_path = template_path
        with open(template_path) as base_file:
            self.base_svg = base_file.read()

    def __repr__(self):
        return f"{self.__class__.__name__} for {self.template_path}"

    def __eq__(self, other):
        return self.base_svg == other.base_svg


class SVGTextTemplateRenderer(SVGTemplateRenderer):
    def render(self, puzzle: Puzzle, output_width: int = 1200) -> bytes:
        base_svg = self.base_svg.replace("$C", puzzle.center)
        for letter in puzzle.outside:
            base_svg = base_svg.replace("$L", letter, 1)
        return svg2png(base_svg, output_width=output_width)


for path in Path("images/").glob("puzzle_template_*.svg"):
    PuzzleRenderer.available_renderers.append(SVGTextTemplateRenderer(path))


class SVGImageTemplateRenderer(SVGTemplateRenderer):
    def __init__(self, template_path: PathLike, alphabet_path: PathLike):
        super().__init__(template_path)
        self.alphabet_path = alphabet_path

    def render(self, puzzle: Puzzle, output_width: int = 1200) -> bytes:
        center_placeholder_pixel = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ" +
            "AAAADUlEQVR42mP8/5fhPwAH/AL9Ow9X5gAAAABJRU5ErkJggg=="
        )
        outside_placeholder_pixel = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1" +
            "HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with open(Path(
            self.alphabet_path,
            puzzle.center.lower()+".png"
        ), "rb") as center_letter_file:
            center_letter = base64.b64encode(center_letter_file.read()).decode('ascii')
            base_svg = self.base_svg.replace(center_placeholder_pixel, center_letter)
        for letter in puzzle.outside:
            with open(Path(
                self.alphabet_path,
                letter.lower()+".png"
            ), "rb") as letter_file:
                letter_image = base64.b64encode(letter_file.read()).decode('ascii')
                base_svg = base_svg.replace(outside_placeholder_pixel, letter_image, 1)
        return svg2png(base_svg, output_width=output_width)


PuzzleRenderer.available_renderers.append(SVGImageTemplateRenderer(
    "images/image_puzzle_template_1.svg", "fonts/pencil/"))


class GIFTemplateRenderer(PuzzleRenderer):
    def __init__(
            self, first_frame_file: str, gif_file: str,
            center_coords: tuple[int, int],
            text_radius: float,
            font_size: int = 50):
        self.gif_file = gif_file
        self.first_frame_file = first_frame_file
        self.text_radius = text_radius
        self.center_coords = center_coords
        self.font_size = font_size

    def __repr__(self):
        return f"GIFTemplateRenderer for {self.gif_file}"

    def render(self, puzzle: Puzzle) -> bytes:
        base = Image.open(self.first_frame_file)
        palette = base.palette
        darkest_available_color = (255, 255, 255)
        darkest_index = -1
        for i, color in enumerate(palette.colors):
            if statistics.mean(color) < statistics.mean(darkest_available_color):
                darkest_available_color = color
                darkest_index = i
        font = ImageFont.truetype("./fonts/LiberationSans-Bold.ttf", self.font_size)
        surface = ImageDraw.Draw(base)
        base.seek(0)
        surface.text(self.center_coords, puzzle.center,
                     fill=darkest_index, font=font, anchor="mm")
        for letter, coords in zip(
            puzzle.outside,
            make_hexagon(self.center_coords, self.text_radius, True)
        ):
            surface.text(coords, letter, fill=darkest_index, font=font, anchor="mm")
        image_bytes = BytesIO()
        base.seek(0)
        base.save(image_bytes, format="GIF")
        image_bytes.seek(0)
        gifsicle = subprocess.Popen(
            ["gifsicle", self.gif_file, "--replace", "#0", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gifsicle_output = gifsicle.communicate(input=image_bytes.read())
        if len(gifsicle_output[1]) > 0:
            print("gifsicle errors:")
            print(gifsicle_output[1].decode("ascii"))
        return gifsicle_output[0]


PuzzleRenderer.available_renderers.append(
    GIFTemplateRenderer(
        "images/spinf1.gif", "images/spin.gif",
        (300, 300), 90
    ))


async def test():
    print("frequency of 'puzzle'", get_word_frequency("puzzle"))
    saved_puzzle = Puzzle.retrieve_last_saved("db/testpuzzles.db")
    if saved_puzzle is None:
        print("fetching puzzle from nyt")
        puzzle = await Puzzle.fetch_from_nyt()
        puzzle.db_path = "db/testpuzzles.db"
    else:
        print("retrieved puzzle from db")
        puzzle = saved_puzzle
        puzzle.db_path = "db/testpuzzles.db"
        if (datetime.now()
            - datetime.fromtimestamp(puzzle.timestamp)
                > timedelta(days=1)):
            print("puzzle from db was old, replacing it with current NYT one")
            puzzle = await Puzzle.fetch_from_nyt()
            puzzle.db_path = "db/testpuzzles.db"
        else:
            print("puzzle from db is",
                  datetime.now() - datetime.fromtimestamp(puzzle.timestamp), "old")
    print("today's words from least to most common:")
    print(puzzle.get_unguessed_words())
    answers = iter(puzzle.answers)
    puzzle.guess(next(answers))
    print("words that the nyt doesn't want us to know about:")
    print(random.sample(puzzle.get_wiktionary_alternative_answers(), 5))
    puzzle.save()
    rendered = puzzle.render(PuzzleRenderer.available_renderers[-1])
    # Image.open(BytesIO(rendered)).show()
    with open("images/puzzlestest.gif", "wb+") as test_output:
        test_output.write(rendered)


if __name__ == "__main__":
    asyncio.run(test())
