import asyncio
from io import BytesIO
import json
import re
import sqlite3
from PIL import Image

from tornado.httpclient import AsyncHTTPClient
from cairosvg import svg2png
import discord

words_db = sqlite3.connect("words.db")


def get_word_frequency(word: str) -> int:
    cur = words_db.cursor()
    frequency = cur.execute(
        "select frequency from words where word=?",
        (word,)
    ).fetchone()
    return 0 if frequency is None else frequency[0]


class Puzzle():
    # constants returned by `guess(word)`:
    wrong_word = 1
    good_word = 2
    pangram = 3

    def __init__(self, center: str, outside: list[str], pangrams: list[str], answers: list[str]):
        self.center = center.upper()
        self.outside = [l.upper() for l in outside]
        self.pangrams = set(p.lower() for p in pangrams)
        self.answers = set(a.lower() for a in answers)
        for word in self.pangrams:
            self.answers.add(word)
        self.gotten_words = set()

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
            return self.pangram
        elif self.does_word_count(w):
            self.gotten_words.add(w)
            return self.good_word
        else:
            return self.wrong_word

    def get_unguessed_words(self) -> list[str]:
        """returns the heretofore unguessed words in a list sorted from the least to
        the most common words."""
        unguessed = list(self.answers - self.gotten_words)
        unguessed.sort(key=lambda w: get_word_frequency(w))
        return unguessed

    def render(self, output_width: int = 600) -> bytes:
        with open("images/puzzle_bg_1.svg") as base_file:
            base_svg = base_file.read()
        base_svg = base_svg.replace("%center%", self.center)
        for letter in self.outside:
            base_svg = base_svg.replace("%letter%", letter, 1)
        return svg2png(base_svg, output_width=output_width)

    @classmethod
    async def fetch_from_nyt(cls) -> "Puzzle":
        client = AsyncHTTPClient()
        response = await client.fetch("https://www.nytimes.com/puzzles/spelling-bee")
        html = response.body.decode("utf-8")
        game_data = re.search("window.gameData = (.*?)</script>", html)
        if game_data:
            game = json.loads(game_data.group(1))["today"]
            return cls(
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


async def test():
    print("frequency of 'puzzle'", get_word_frequency("puzzle"))
    puzzle = await Puzzle.fetch_from_nyt()
    print("today's words from least to most common:")
    print(puzzle.get_unguessed_words())
    rendered = puzzle.render()
    Image.open(BytesIO(rendered)).show()


if __name__ == "__main__":
    asyncio.run(test())
