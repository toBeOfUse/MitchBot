import asyncio
import json
import re
from io import BytesIO
from timeit import default_timer
from db.queries import get_wiktionary_trie, get_word_rank
from cairosvg import svg2png
from tornado.httpclient import AsyncHTTPClient
from PIL import Image
from sortedcontainers import SortedList


class ValidLetterBoxedWord:
    def __init__(self, word: str, fake_unique_letters: bool = False):
        self.word = word.upper() + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ" if fake_unique_letters else "")

    @property
    def unique_letters(self):
        return len(set(self.word))

    @property
    def first_letter(self):
        return self.word[0]

    @property
    def last_letter(self):
        return self.word[-1]

    def __eq__(self, other):
        return self.word == other.word

    @property
    def cmp_key(self):
        return (self.first_letter, -self.unique_letters, self.word[1:])

    def __repr__(self):
        return self.word


class LetterBoxed:
    def __init__(
            self,
            sides: list[tuple[str, str, str]],
            valid_words: list[str],
            par: int):
        self.sides = sides
        self.valid_words: SortedList[ValidLetterBoxedWord] = SortedList(
            map(ValidLetterBoxedWord, valid_words), key=lambda x: x.cmp_key)
        self.restricted_valid_words: SortedList[ValidLetterBoxedWord] = (
            SortedList(
                map(ValidLetterBoxedWord,
                    (x for x in valid_words if get_word_rank(x) < 100_000)),
                key=lambda x: x.cmp_key))
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

    @property
    def needed_letter_count(self):
        return 12
        # or return sum(map(self.sides, len), 0) for added headaches

    def unique_letters_in_words(self, some_words: list[str]):
        letters = set()
        for word in some_words:
            letters.update(word.word)
        return len(letters)

    def are_words_solution(self, some_words: list[str]):
        return self.unique_letters_in_words(some_words) == self.needed_letter_count

    def _get_solutions_by_length(
            self,
            max_length: int,
            valid_words: SortedList[ValidLetterBoxedWord],
            words_so_far: list[ValidLetterBoxedWord] = []
    ) -> list[list[str]]:
        # note that the length of words_so_far corresponds to the level of recursion
        # we're at
        if max_length == 1:
            # special case: find any one-word solutions with a simple linear scan,
            # recursion unhelpful
            return [[x] for x in valid_words if self.are_words_solution([x])]
        if self.are_words_solution(words_so_far):
            # if we already have a solution, it's guaranteed not to be the right
            # length (and we don't want to just keep tacking words on to fix this),
            # so we've hit a dead end
            return []
        elif len(words_so_far) == max_length-1:
            # this is the final letter of recursion; we need to take any word that
            # turns words_so_far into a solution, tack it onto the end, and return
            # the list of all the solutions we've found
            next_start = words_so_far[-1].last_letter
            found_solutions = []
            unique_letters_so_far = self.unique_letters_in_words(words_so_far)
            letters_still_needed = self.needed_letter_count - unique_letters_so_far
            search_pos = valid_words.bisect_left(
                ValidLetterBoxedWord(next_start, True))
            while search_pos < len(valid_words):
                word: ValidLetterBoxedWord = valid_words[search_pos]
                if word == words_so_far[-1]:
                    pass
                elif word.unique_letters < letters_still_needed or word.first_letter != next_start:
                    break
                elif self.are_words_solution(words_so_far+[word]):
                    found_solutions.append(words_so_far+[word])
                search_pos += 1
            return found_solutions
        elif len(words_so_far) == 0:
            # this is the first level of recursion; we have no restrictions and need
            # to try starting with each individual word. this is also the most
            # centralized place to eliminate solutions that are "padded" with words
            # extraneous to their "core solution"; we can do that just by making sure
            # that we couldn't remove a word from either the beginning or end (how to prove?)
            found_solutions = []
            potential_solutions = []
            for word in valid_words:
                potential_solutions = self._get_solutions_by_length(max_length, valid_words, [word])
                # exclude solutions who have subsequences that are "already" solutions
                for sol in potential_solutions:
                    if not (self.are_words_solution(sol[1:]) or self.are_words_solution(sol[:-1])):
                        found_solutions.append(sol)
            return found_solutions
        else:
            # this is a level of recursion somewhere in between the first and last;
            # we just need to continue the chain of words_so_far in a valid way
            next_start = words_so_far[-1].last_letter
            potential_solutions = []
            # select all words starting with next_start, hopefully
            for word in valid_words.irange(
                    ValidLetterBoxedWord(next_start, True),
                    ValidLetterBoxedWord(chr(ord(next_start)+1), True)):
                if word == words_so_far[-1]:
                    pass
                potential_solutions += self._get_solutions_by_length(
                    max_length, valid_words, words_so_far + [word])
            return potential_solutions

    def get_solutions_by_length(
        self,
        max_length: int = 3,
        restrict_words=False
    ) -> dict[int, list[list[ValidLetterBoxedWord]]]:
        if restrict_words:
            valid_words = self.restricted_valid_words
        else:
            valid_words = self.valid_words
        result = {}
        for i in range(1, max_length+1):
            result[i] = self._get_solutions_by_length(i, valid_words)
        return result

    def get_solutions_quantity_statement(
            self,
            max_length: int = 3
    ):
        def verb(count: int):
            return "are" if count != 1 else "is"

        def sol(count: int):
            return "solutions" if count != 1 else "solution"

        def num(number: int):
            numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                       6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
            if number in numbers:
                return numbers[number]
            else:
                return number

        unrestricted = self.get_solutions_by_length(3)
        restricted = self.get_solutions_by_length(3, True)
        result = ""
        if len(unrestricted[1]):
            one = len(unrestricted[1])
            result += f"There {verb(one)} {num(one)} one-word {sol(one)} today. "

        two = len(unrestricted[2])
        two_r = len(restricted[2])
        three = len(unrestricted[3])
        three_r = len(restricted[3])
        result += (
            f"There {verb(two)} {num(two)} two-word {sol(two)} " +
            f"and {num(three)} three-word {sol(three)}. "
        )
        result += (
            "Limiting ourselves to the most common 100,000 words in the " +
            f"Google Books corpus, there {verb(two_r)} {num(two_r)} two-word " +
            f"{sol(two_r)} and {num(three_r)} three-word {sol(three_r)}."
        )

        return result

    def percentage_of_words_in_wiktionary(self):
        wikt = get_wiktionary_trie()
        return round(
            (
                sum(
                    (1 if wikt.is_string_there(x.word) else 0) for x in self.valid_words
                ) /
                len(self.valid_words))
            * 100, 2)

    def __repr__(self):
        return f"<LetterBoxed sides={self.sides} par={self.par} len(valid_words)={len(self.valid_words)}>"


async def test():
    puzzle = await LetterBoxed.fetch_from_nyt()
    print(puzzle)
    print(puzzle.get_solutions_by_length(2))
    print(puzzle.get_solutions_quantity_statement(1))
    print(puzzle.get_solutions_quantity_statement(2))
    print(puzzle.get_solutions_quantity_statement(3))
    print("percentage of today's words in wiktionary:", puzzle.percentage_of_words_in_wiktionary())
    print("restricted mode:")
    print(puzzle.get_solutions_quantity_statement(3, True))
    # print(puzzle.get_solutions_quantity_statement(4))  # slow!


if __name__ == "__main__":
    asyncio.run(test())
