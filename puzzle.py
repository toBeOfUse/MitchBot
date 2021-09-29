import asyncio
import json
import math
from io import BytesIO
import re
import sqlite3

from tornado.httpclient import AsyncHTTPClient
from PIL import Image, ImageDraw, ImageFont
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

    @staticmethod
    def make_hexagon(width: int, height: int, tilted: bool = False) -> list[tuple[int, int]]:
        # starting with the leftmost point, construct a hexagon with the given
        # dimensions centered on 0,0 so it can be trivially translated to center on
        # whatever we want and also scaled. for a regular hexagon, width should be
        # sqrt(3) times the height or vice versa. points go clockwise. if tilted is
        # True, the sides are parallel to the edges of the image instead of the top
        # and bottom, and the topmost point comes first
        base = [(-width / 2, 0),
                (-width/4, -height/2),
                (width/4, -height/2),
                (width/2, 0),
                (width/4, height/2),
                (-width/4, height/2)]
        return [(tuple(reversed(x)) if tilted else x) for x in base]

    def render(self, output_width: int = 600) -> BytesIO:
        base_hex_side = 10
        base_width = base_hex_side*2
        base_height = math.sqrt(3) * base_hex_side
        # used for base hexagon
        hexpoints = self.make_hexagon(base_width, base_height)
        # used for placement of the centers of the base hexagon
        rotated_hexpoints = self.make_hexagon(base_width, base_height, True)
        # to perfectly tile the hexagons, we would place their centers at the points
        # of a hexagon sqrt(3) times larger than the base one. we are scaling them up a
        # little more here for spacing.
        hexcenters = [(x*(math.sqrt(3)+0.2), y*(math.sqrt(3)+0.2)) for x, y in rotated_hexpoints]
        # this is the width (longest side) of the image, which we will use to make a
        # square resulting image. it needs to be at least. something.
        base_image_width = base_width*3.25
        anti_alias_level = 4
        temp_width = output_width * anti_alias_level
        actual_to_base = temp_width/base_image_width
        image = Image.new("RGBA", (temp_width, temp_width), 0)
        surface = ImageDraw.Draw(image)
        # experimental background
        for i in range(8):
            surface.regular_polygon(
                bounding_circle=(temp_width/2, temp_width/2, temp_width/1.8),
                n_sides=6,
                fill=(255, 255, 255, int(100 + 155/(8-i))),
                rotation=360/8*i)
        # bg dodecahedron, scaled to the canvas size and then translated to be centered
        surface.regular_polygon(
            bounding_circle=(temp_width/2, temp_width/2, temp_width/2),
            n_sides=12,
            fill=(255, 255, 255, 255))
        font = ImageFont.truetype("./fonts/LiberationSans-Bold.ttf",
                                  round(base_height*0.4*actual_to_base))
        # center points of the base hexagons, scaled to the canvas size and then
        # translated to be centered
        hexcenters = [(x*actual_to_base+temp_width/2, y*actual_to_base+temp_width/2)
                      for x, y in hexcenters]
        letter_iterator = iter(self.outside)
        for hexcenter in hexcenters:
            surface.polygon(
                [(x * actual_to_base + hexcenter[0],
                  y * actual_to_base + hexcenter[1])
                 for x, y in hexpoints],
                fill="#E6E6E6FF")
            surface.text((hexcenter[0], hexcenter[1]), next(
                letter_iterator), fill="#000000ff", font=font, anchor="mm")
        # draw center base polygon
        surface.polygon(
            [(x * actual_to_base + temp_width/2,
              y * actual_to_base + temp_width/2)
             for x, y in hexpoints],
            fill="#F7DA21FF")
        surface.text((temp_width/2, temp_width/2), self.center,
                     fill="#000000ff", font=font, anchor="mm")

        image = image.resize((output_width, output_width), resample=Image.LANCZOS)
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        return image_bytes

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
    print("today's words from least to most common:")
    print((await Puzzle.fetch_from_nyt()).get_unguessed_words())


if __name__ == "__main__":
    asyncio.run(test())
