import asyncio
import json
import re
from io import BytesIO

from cairosvg import svg2png
from tornado.httpclient import AsyncHTTPClient
from PIL import Image


class LetterBoxed:
    def __init__(self, sides: list[tuple[str, str, str]], valid_words: list[str], par: int):
        self.sides = sides
        self.valid_words = valid_words
        self.par = par

    @classmethod
    async def fetch_from_nyt(cls):
        client = AsyncHTTPClient()
        response = await client.fetch("https://www.nytimes.com/puzzles/letter-boxed")
        html = response.body.decode("utf-8")
        game_data = re.search("window.gameData = (.*?)</script>", html)
        if game_data:
            game = json.loads(game_data.group(1))
            return cls(game["sides"], game["dictionary"], game["par"])

    async def render(self) -> bytes:
        with open("images/letterboxed_template.svg") as svg_template_file:
            svg_template = svg_template_file.read()
            for i in range(4):
                for letter in self.sides[i]:
                    svg_template = svg_template.replace("$S"+str(i+1), letter, 1)
            return svg2png(svg_template, output_width=1000)

    def __repr__(self):
        return f"<LetterBoxed sides={self.sides} par={self.par} len(valid_words)={len(self.valid_words)}>"


async def test():
    puzzle = await LetterBoxed.fetch_from_nyt()
    print(puzzle)
    Image.open(BytesIO(await puzzle.render())).show()


if __name__ == "__main__":
    asyncio.run(test())
