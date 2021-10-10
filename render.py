from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from puzzle import Puzzle

from os import PathLike
from pathlib import Path
import base64
import statistics
import asyncio
from io import BytesIO
import abc
from timeit import default_timer

from PIL import Image, ImageFont, ImageDraw
from images.svg_hexagon_generator import make_hexagon
from cairosvg import svg2png


class PuzzleRenderer(metaclass=abc.ABCMeta):
    """Base class for subclasses to override; they should implement __init__, render,
    and __repr__, on principle and so they work with instances of RandomNoRepeats.
    available_renderers should be populated with instances of subclasses to make them
    chooseable by Puzzle.render()."""
    available_renderers: list["PuzzleRenderer"] = []

    @abc.abstractmethod
    def __init__(self):
        pass

    @abc.abstractmethod
    async def render(self, puzzle: Puzzle) -> bytes:
        pass

    @abc.abstractmethod
    def __repr__(self) -> str:
        pass


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
    async def render(self, puzzle: Puzzle, output_width: int = 1200) -> bytes:
        base_svg = self.base_svg.replace("$C", puzzle.center)
        for letter in puzzle.outside:
            base_svg = base_svg.replace("$L", letter, 1)
        return svg2png(base_svg, output_width=output_width)


class SVGImageTemplateRenderer(SVGTemplateRenderer):
    def __init__(self, template_path: PathLike, alphabet_path: PathLike):
        super().__init__(template_path)
        self.alphabet_path = alphabet_path

    async def render(self, puzzle: Puzzle, output_width: int = 1200) -> bytes:
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

    async def render(self, puzzle: Puzzle) -> bytes:
        base = Image.open(self.first_frame_file)
        palette = base.palette
        darkest_available_color = (255, 255, 255)
        darkest_index = -1
        for i, color in enumerate(palette.colors):
            if (statistics.mean(color) < statistics.mean(darkest_available_color)
                    and i != base.info["transparency"]):
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
        gifsicle = await asyncio.create_subprocess_exec(
            "gifsicle", self.gif_file, "--replace", "#0", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        gifsicle_output = await gifsicle.communicate(input=image_bytes.read())
        if len(gifsicle_output[1]) > 0:
            print("gifsicle errors:")
            print(gifsicle_output[1].decode("ascii"))
        return gifsicle_output[0]


class BlenderRenderer(PuzzleRenderer):
    def __init__(self, blender_file_path: PathLike):
        self.blender_file_path = blender_file_path

    async def render(self, puzzle: Puzzle):
        letters = puzzle.center+("".join(puzzle.outside))
        output_path = Path.cwd()/("images/blenderrenders/"+letters)
        blender = await asyncio.create_subprocess_exec(
            "blender", "-b", self.blender_file_path,
            "-E", "CYCLES",
            "-o", str(output_path)+"#",
            "--python-text", "AddLetters",
            "-F", "PNG ",
            "-f", "1",
            "--", letters,
            stdout=asyncio.subprocess.PIPE
        )
        async for line in blender.stdout:
            line = line.decode("ascii").strip()
            print("\r"+line, end="\x1b[1K")
            if line.startswith("Saved:"):
                result_file_path = line[line.find("'")+1: -1]
        await blender.wait()
        print("\r", end="")

        with open(result_file_path, "rb") as result_file:
            result = result_file.read()
        return result

    def __repr__(self):
        return f"BlenderRenderer for {self.blender_file_path}"


for path in Path("images/").glob("puzzle_template_*.svg"):
    PuzzleRenderer.available_renderers.append(SVGTextTemplateRenderer(path))

PuzzleRenderer.available_renderers.append(SVGImageTemplateRenderer(
    Path("images", "image_puzzle_template_1.svg"), Path("fonts", "pencil")))

PuzzleRenderer.available_renderers.append(BlenderRenderer("images/blender_template_1.blend"))

PuzzleRenderer.available_renderers.append(
    GIFTemplateRenderer(
        Path("images", "spinf1.gif"), Path("images", "spin.gif"),
        (300, 300), 90
    ))


async def test():
    from puzzle import Puzzle
    rs = PuzzleRenderer.available_renderers
    print(f"{len(rs)} renderers available. testing...")
    for r in rs:
        start = default_timer()
        render = await r.render(Puzzle(-1, "A", ["B", "C", "D", "E", "F", "G"], [], []))
        type = ".png" if render[0:4] == b"\x89PNG" else ".gif"
        renderer_name_slug = str(r).replace(" ", "_").replace("\\", "-").replace("/", "-")
        with open(f'images/testrenders/{renderer_name_slug}{type}', "wb+") as output:
            output.write(render)
        print(r, "took", round((default_timer()-start)*1000), "ms")

if __name__ == "__main__":
    asyncio.run(test())
