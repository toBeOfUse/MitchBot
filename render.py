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
from xml.dom import minidom
import sys
import random

from PIL import Image, ImageFont, ImageDraw
from images.svg_hexagon_generator import make_hexagon
from cairosvg import svg2png


class PuzzleRenderer(metaclass=abc.ABCMeta):
    """Base class for subclasses to override; they should implement __init__, render,
    and __repr__, on principle and so they work with instances of RandomNoRepeats.
    available_renderers should be populated with instances of subclasses to make them
    chooseable by Puzzle.render()."""
    available_renderers: list[PuzzleRenderer] = []

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
    @staticmethod
    def is_placeholder_text_element(text_element: minidom.Element):
        """Detects svg <text> elements that are formatted to hold placeholder text
        for Puzzle letters. Such elements are expected to have one text node child
        whose content starts with a $."""
        return (len(text_element.childNodes) == 1 and
                type(text_element.firstChild) is minidom.Text and
                text_element.firstChild.nodeValue.startswith("$"))

    @staticmethod
    def get_other_elements_in_group(text_element: minidom.Element):
        """For placeholder <text> elements, detects whether they are in an SVG group
        (<g> tag) with other placeholder <text> siblings and returns the other
        placeholder <text> siblings if so, returning an empty list otherwise."""
        parent: minidom.Element = text_element.parentNode
        if parent.tagName == "g":
            only_element_children = all((type(x) is minidom.Element or
                                         (type(x) is minidom.Text and x.data.strip() == ""))
                                        for x in parent.childNodes)
            only_text_element_children = (only_element_children and all(
                x.tagName == "text" for x in parent.childNodes if type(x) is minidom.Element))
            has_placeholder_children = (only_text_element_children and any(
                SVGTextTemplateRenderer.is_placeholder_text_element(x)
                for x in parent.childNodes if type(x) is minidom.Element))
            if has_placeholder_children:
                siblings = [x for x in parent.childNodes
                            if type(x) is minidom.Element and
                            SVGTextTemplateRenderer.is_placeholder_text_element(x)]
                return siblings
        return []

    async def render(self, puzzle: Puzzle, output_width: int = 1200) -> bytes:
        """Finds placeholder <text> nodes (those with "$L" or "$C" as their content)
        in the SVG file passed to the constructor and replaces that content with the
        letters from the puzzle. If multiple placeholder <text> nodes are by
        themselves in a <g> group (according to is_placeholder_text_element), they
        are all set to the same letter."""
        letters = iter(puzzle.outside)
        base: minidom.Document = minidom.parseString(self.base_svg)
        for text_element in base.getElementsByTagName("text"):
            if self.is_placeholder_text_element(text_element):
                if text_element.firstChild.nodeValue == "$C":
                    text_element.firstChild.nodeValue = puzzle.center
                    for sibling in self.get_other_elements_in_group(text_element):
                        sibling.firstChild.nodeValue = puzzle.center
                elif text_element.firstChild.nodeValue == "$L":
                    letter = next(letters)
                    text_element.firstChild.nodeValue = letter
                    for sibling in self.get_other_elements_in_group(text_element):
                        sibling.firstChild.nodeValue = letter
        return svg2png(base.toxml(encoding="utf-8"), output_width=output_width)


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
        output_path = Path.cwd()/("images/temp/"+letters)
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


class LetterSwapRenderer(PuzzleRenderer):
    def __init__(
            self,
            base_image_path: PathLike,
            image_palette: PathLike,
            letter_locations: list[tuple[int, int]],
            frames_path: PathLike,
            frames_size: tuple[int, int],
            frames_per_letter: int,
            pause_length: int):
        """Creates a renderer that creates a GIF animation in which letters switch back
        and forth and transition between each other. Created with split-flap displays
        in mind.

        Args:
            base_image_path (PathLike): Path to the image upon which the letters will
                be superimposed
            base_image_palette (PathLike): Path to the palette for the gif. This should
                have been generated with the ffmpeg palettegen filter.
            letter_locations (list[tuple[int, int]]): List of the upper left corners
                of the 7 boxes that letters should be placed in, starting with the box
                for the center letter
            frames_path (PathLike): Path to the folder that contains the frames that
                display the letters and transition between them.
            frames_size (tuple[int, int]): Size of the boxes that the letters should
                be placed in: (width, height)
            frames_per_letter (int): How many frames it takes to transition from one
                letter to the other using the frames in `frames_path`.
            pause_length (int): How long to pause, in seconds, between each letter 
                transition.
        """
        self.base_image_path = base_image_path
        self.image_palette = image_palette
        self.letter_locations = letter_locations
        self.frames_path = frames_path
        self.frames_size = frames_size
        self.frames_per_letter = frames_per_letter
        self.pause_length = pause_length

    @property
    def total_frames(self):
        return self.frames_per_letter*26

    def __repr__(self):
        return f"LetterSwapRenderer for {self.base_image_path}"

    def get_frame_for_letter(self, letter: str) -> list[int]:
        return (ord(letter)-ord("A"))*self.frames_per_letter

    def get_frames_between_letters(self, start_letter: str, end_letter: str):
        start = self.get_frame_for_letter(start_letter)
        end = self.get_frame_for_letter(end_letter)
        if end < start:
            end += self.total_frames
        return list(x % self.total_frames for x in range(start, end))

    def resize_frame(self, frame: Image.Image) -> Image.Image:
        if (frame.width, frame.height) != self.frames_size:
            return frame.resize(self.frames_size)
        else:
            return frame

    def open_frame(self, frame_path: PathLike) -> Image.Image:
        return self.resize_frame(Image.open(frame_path))

    async def render(self, puzzle: Puzzle):
        base_image = Image.open(self.base_image_path)
        frame_paths = sorted(
            list(Path(self.frames_path).glob("*")),
            key=lambda x: int(x.stem))
        center_frame = self.get_frame_for_letter(puzzle.center)
        center_frame_image = self.open_frame(frame_paths[center_frame])
        base_image.paste(center_frame_image, self.letter_locations[0])
        frame_count = 0
        freeze_frames = [0]
        for i in range(6):
            frame_image = self.open_frame(frame_paths[self.get_frame_for_letter(puzzle.outside[i])])
            base_image.paste(frame_image, self.letter_locations[i+1])
        base_image.save("images/temp/"+str(frame_count)+".bmp")
        frame_count += 1
        swappable_index_pairs = [(0, 1), (2, 3), (4, 5), (1, 0), (3, 2), (5, 4)]
        total_frames = 1
        for indexes in swappable_index_pairs:
            total_frames += max(
                [len(
                    self.get_frames_between_letters(
                        puzzle.outside[indexes[0]], puzzle.outside[indexes[1]])),
                 len(
                    self.get_frames_between_letters(
                        puzzle.outside[indexes[1]], puzzle.outside[indexes[0]]))
                 ]
            )
        swappable_locations = self.letter_locations[1:]
        for indexes in swappable_index_pairs:
            pos_1_frames = self.get_frames_between_letters(
                puzzle.outside[indexes[0]], puzzle.outside[indexes[1]])
            pos_2_frames = self.get_frames_between_letters(
                puzzle.outside[indexes[1]], puzzle.outside[indexes[0]])
            for i in range(max(len(pos_1_frames), len(pos_2_frames))):
                if i < len(pos_1_frames):
                    base_image.paste(
                        self.open_frame(frame_paths[pos_1_frames[i]]),
                        swappable_locations[min(indexes)]
                    )
                if i < len(pos_2_frames):
                    base_image.paste(
                        self.open_frame(frame_paths[pos_2_frames[i]]),
                        swappable_locations[max(indexes)]
                    )
                base_image.save("images/temp/"+str(frame_count)+".bmp")
                frame_count += 1
                if frame_count % 10 == 0:
                    print(f"\remitted {frame_count}/{total_frames} frames", end="")
            freeze_frames.append(frame_count-1)
        print(f"\remitted all {total_frames} frames")
        ffmpeg_pauses = "+".join([f"gt(N,{x})*{self.pause_length}/TB" for x in freeze_frames])
        ffmpeg_command = (
            f"ffmpeg -framerate 45 -i images/temp/%d.bmp -i {self.image_palette} " +
            f"-filter_complex \"setpts='PTS-STARTPTS+({ffmpeg_pauses})'," +
            "paletteuse\" -loop 0 -y images/temp/letter_swap_output.gif")
        print("ffmpeg command", ffmpeg_command)

        ffmpeg = await asyncio.create_subprocess_shell(ffmpeg_command)
        await ffmpeg.wait()
        for temp_frame in Path("images/temp/").glob("*.bmp"):
            temp_frame.unlink()
        with open("images/temp/letter_swap_output.gif", "rb") as result_file:
            result = result_file.read()
            return result


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

PuzzleRenderer.available_renderers.append(
    LetterSwapRenderer(
        "images/trainstationbase.png",
        "images/trainstationpalette.png",
        [(586, 277), (479, 277), (693, 277), (532, 138), (640, 415), (533, 415), (640, 138)],
        "fonts/split-flap/resized/",
        (40, 66), 5, 20
    )
)


async def test():
    from puzzle import Puzzle
    rs = PuzzleRenderer.available_renderers
    letters = random.sample(["B", "C", "D", "E", "F", "G"], 6)
    if len(sys.argv) > 1:
        print(f"looking for renderers with {sys.argv[1]} in name")
    else:
        print(f"{len(rs)} renderers available. testing...")
    for r in rs:
        if len(sys.argv) > 1:
            if sys.argv[1] not in str(r):
                continue
        start = default_timer()
        render = await r.render(Puzzle(-1, "A", letters, [], []))
        type = ".png" if render[0:4] == b"\x89PNG" else ".gif"
        renderer_name_slug = str(r).replace(" ", "_").replace("\\", "-").replace("/", "-")
        with open(f'images/testrenders/{renderer_name_slug}{type}', "wb+") as output:
            output.write(render)
        print(r, "took", round((default_timer()-start)*1000), "ms")

if __name__ == "__main__":
    asyncio.run(test())
