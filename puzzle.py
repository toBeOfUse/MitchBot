import asyncio
from io import BytesIO
import json
import re
import sqlite3
from typing import Optional
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import random

from tornado.httpclient import AsyncHTTPClient
from cairosvg import svg2png
import discord
from PIL import Image

words_db = sqlite3.connect("db/words.db")


def get_word_frequency(word: str) -> int:
    cur = words_db.cursor()
    frequency = cur.execute(
        "select frequency from words where word=?",
        (word,)
    ).fetchone()
    return 0 if frequency is None else frequency[0]


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
            gotten_words: set = set()):
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

    def render(
        self,
        output_width: int = 1200,
        template=random.choice(list(Path("images").glob("puzzle_template_*.svg")))
    ) -> bytes:
        with open(template) as base_file:
            base_svg = base_file.read()
        base_svg = base_svg.replace("$C", self.center)
        for letter in self.outside:
            base_svg = base_svg.replace("$L", letter, 1)
        # with open('images/rendertest.svg', "w+") as render_test:
        #     render_test.write(base_svg)
        return svg2png(base_svg, output_width=output_width)

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

    def save(self, db_path="db/puzzles.db"):
        """Serializes the puzzle and saves it in a SQLite database."""
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


async def test():
    print("frequency of 'puzzle'", get_word_frequency("puzzle"))
    saved_puzzle = Puzzle.retrieve_last_saved("db/testpuzzles.db")
    if saved_puzzle is None:
        print("fetching puzzle from nyt")
        puzzle = await Puzzle.fetch_from_nyt()
    else:
        print("retrieving puzzle from db")
        puzzle = saved_puzzle
        if (datetime.now()
            - datetime.fromtimestamp(puzzle.timestamp)
                > timedelta(days=1)):
            print("puzzle from db was old, replacing it with current NYT one")
            puzzle = await Puzzle.fetch_from_nyt()
        else:
            print("puzzle from db is",
                  datetime.now() - datetime.fromtimestamp(puzzle.timestamp), "old")
    print("today's words from least to most common:")
    print(puzzle.get_unguessed_words())
    answers = iter(puzzle.answers)
    puzzle.guess(next(answers))
    puzzle.guess(next(answers))
    puzzle.db = "db/testpuzzles.db"
    puzzle.save()
    rendered = puzzle.render(template="images/puzzle_template_2.svg")
    Image.open(BytesIO(rendered)).show()


if __name__ == "__main__":
    asyncio.run(test())
