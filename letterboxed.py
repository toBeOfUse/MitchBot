from __future__ import annotations
import asyncio
from collections import defaultdict
from difflib import SequenceMatcher
import json
from os import PathLike
import re
from io import BytesIO
import sqlite3
from timeit import default_timer
from typing import Optional, Union, TYPE_CHECKING
from datetime import time, datetime, timedelta
import traceback

import discord
from cairosvg import svg2png
from discord.commands.context import ApplicationContext
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop
from PIL import Image
from bs4 import BeautifulSoup as Soup

from responders import MessageResponder
from scheduler import repeatedly_schedule_task_for, et
from db.queries import get_word_rank
from grammar import andify, num, add_s, copula
if TYPE_CHECKING:
    from MitchBot import MitchBot

alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
assert len(alphabet) == 26

with open(
    "db/letterboxed-wiktionary-english-words.txt",
        encoding="utf-8") as wiktionary_file:
    wiktionary = set(map(lambda x: x.casefold(), wiktionary_file.read().splitlines()))


class LetterBoxedWord:
    def __init__(self, word: str):
        self.word = word.upper()

    @property
    def unique_letters(self):
        return len(set(self.word))

    @property
    def first_letter(self):
        return self.word[0]

    @property
    def last_letter(self):
        return self.word[-1]

    @property
    def is_common(self):
        return get_word_rank(self.word) < 100_000

    def __eq__(self, other):
        return self.word == other.word

    def __hash__(self) -> int:
        return hash(self.word)

    def __repr__(self):
        return self.word


class LetterBoxedSolution:
    def __init__(self, initial: list[LetterBoxedWord] = []):
        self.words = initial

    def add_word(self, word: LetterBoxedWord):
        self.words.append(word)

    def __len__(self) -> int:
        return len(self.words)

    def __add__(self, new_word: LetterBoxedWord):
        return LetterBoxedSolution(self.words+[new_word])

    def __hash__(self):
        return hash(tuple(self.words))

    def __str__(self):
        return "->".join(str(x) for x in self.words)

    @property
    def unique_letters(self):
        letters = set()
        for word in self.words:
            letters.update(word.word)
        return len(letters)

    def is_complete(
            self,
            check_basic_validity: bool = False,
            valid_words: Optional[set[LetterBoxedWord]] = None,
            needed_letter_count: int = 12):
        if check_basic_validity:
            # we don't need to check the basic validity if we're e. g. in the process
            # of building the solution in the LetterBoxed class from the internal
            # index
            for i in range(len(self.words)-1):
                if self.words[i].word[-1] != self.words[i+1].word[0]:
                    return False
            if valid_words is not None:
                if any(word not in valid_words for word in self.words):
                    return False
        return self.unique_letters >= needed_letter_count


class LetterBoxedSolutionSet:
    def __init__(self, solutions: list[LetterBoxedSolution] = []):
        self.solutions: set[LetterBoxedSolution] = set(solutions)
        self._words: set[LetterBoxedWord] = set()
        self._common_words: set[LetterBoxedWord] = set()
        self._common_word_solutions: set[LetterBoxedWord] = set()
        self.finalized = False

    def to_lists(self) -> list[list[str]]:
        solutions = []
        for solution in self.solutions:
            solutions.append([x.word for x in solution.words])
        return solutions

    @classmethod
    def from_lists(cls, lists: list[list[str]]) -> LetterBoxedSolutionSet:
        solutions = set()
        for list in lists:
            solutions.add(
                LetterBoxedSolution([LetterBoxedWord(x) for x in list])
            )
        return cls(solutions)

    def finalize(self):
        for solution in self.solutions:
            common = True
            for word in solution.words:
                self._words.add(word)
                if word.is_common:
                    self._common_words.add(word)
                else:
                    common = False
            if common:
                self._common_word_solutions.add(solution)
        self.finalized = True

    @property
    def words(self):
        if not self.finalized:
            self.finalize()
        return self._words

    @property
    def common_words(self):
        if not self.finalized:
            self.finalize()
        return self._common_words

    @property
    def common_word_solutions(self):
        if not self.finalized:
            self.finalize()
        return self._common_word_solutions

    def __add__(
        self,
        other: LetterBoxedSolutionSet | LetterBoxedSolution
    ) -> LetterBoxedSolutionSet:
        if isinstance(other, LetterBoxedSolutionSet):
            return LetterBoxedSolutionSet(self.solutions.union(other.solutions))
        else:
            return LetterBoxedSolutionSet(self.solutions.union(set([other])))

    def __len__(self):
        return len(self.solutions)

    def __str__(self):
        return "{"+", ".join(str(x) for x in self.solutions)+"}"


class LetterBoxed:
    def __init__(
            self,
            loaded_timestamp: int,
            sides: list[tuple[str, str, str]],
            valid_words: list[str],
            par: int):
        self.sides = sides
        self.par = par
        self.timestamp = loaded_timestamp

        self.valid_words: set[LetterBoxedWord] = set()
        self.min_word_score: int = 10000000  # good enough (max possible score is currently 12)
        self.max_word_score: int = 0
        self.restricted_valid_words: set[LetterBoxedWord] = set()
        self.index = {l: defaultdict(set) for l in alphabet}

        print("building letterboxed index...")
        for word in map(LetterBoxedWord, valid_words):
            self.valid_words.add(word)
            if word.is_common:
                self.restricted_valid_words.add(word)
            self.min_word_score = min(word.unique_letters, self.min_word_score)
            self.max_word_score = max(word.unique_letters, self.max_word_score)
            self.index[word.first_letter][word.unique_letters].add(word)
        print("index built")

        self.found_solution_sets: dict[int, LetterBoxedSolutionSet] = {}

        self.graphic = self.fill_letters_into_template()

        self.user_found_words: set[LetterBoxedWord] = set()
        self.hints_given: set[LetterBoxedWord] = set()

        self.db_path: str = ""

    def persist(self, db_path="db/puzzles.db"):
        self.db_path = db_path
        self.save()

    @classmethod
    def get_connection(self, db_path: PathLike) -> Optional[sqlite3.Connection]:
        """Connects to the database, ensures the letterboxed table exists with the
        correct schema, and returns the connection."""
        if db_path is None:
            return None
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        cur.execute("""create table if not exists letterboxed
        (timestamp integer primary key, par integer, side1 text, side2 text, side3 text,
        side4 text, valid_words text, found_solutions text,
        user_found_words text, hints_given text);""")
        cur.execute("""create index if not exists chrono on letterboxed(timestamp);""")
        db.commit()
        return db

    def save(self):
        db = self.get_connection(self.db_path)
        if db is None:
            return
        cur = db.cursor()
        cur.execute(
            """insert or replace into letterboxed
            (timestamp, par, side1, side2, side3, side4, valid_words,
            found_solutions, user_found_words, hints_given)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (self.timestamp, self.par, *["".join(x) for x in self.sides],
             json.dumps([x.word for x in self.valid_words]),
             json.dumps(
                 {key: value.to_lists() for key, value in self.found_solution_sets.items()}
            ), json.dumps([x.word for x in self.user_found_words]),
                json.dumps([x.word for x in self.hints_given]))
        )
        db.commit()
        db.close()

    @classmethod
    def retrieve_last_saved(cls, db_path: str = "db/puzzles.db") -> Optional[LetterBoxed]:
        db = cls.get_connection(db_path)
        cur = db.cursor()
        try:
            latest = cur.execute("""select
            timestamp, par, side1, side2, side3, side4, valid_words,
            found_solutions, user_found_words, hints_given
            from letterboxed order by timestamp desc limit 1;""").fetchone()
            db.close()
            if latest is None:
                return None
            else:
                loaded_puzzle = cls(
                    latest[0],
                    [tuple(x) for x in latest[2:6]],
                    json.loads(latest[6]),
                    latest[1])
                loaded_puzzle.found_solution_sets = {
                    int(k): LetterBoxedSolutionSet.from_lists(v)
                    for k, v in json.loads(latest[7]).items()}
                loaded_puzzle.user_found_words = (
                    set(map(LetterBoxedWord, json.loads(latest[8])))
                )
                loaded_puzzle.hints_given = (
                    set(map(LetterBoxedWord, json.loads(latest[9])))
                )
                return loaded_puzzle
        except:
            print("couldn't load latest letterboxed from database")
            traceback.print_exc()
            db.close()
            return None

    @classmethod
    async def fetch_from_nyt(cls):
        client = AsyncHTTPClient()
        response = await client.fetch("https://www.nytimes.com/puzzles/letter-boxed")
        html = response.body.decode("utf-8")
        game_data = re.search("window.gameData = (.*?)</script>", html)
        if game_data:
            game = json.loads(game_data.group(1))
            return cls(
                int(datetime.now().timestamp()),
                game["sides"],
                game["dictionary"],
                game["par"])

    def fill_letters_into_template(self) -> Soup:
        """Goes through letterboxed_template.svg; fills letters into the right spots;
        and gives each group containing a letter and a circle the id letter-[whatever
        letter it is], like #letter-A"""
        with open("images/letterboxed_template.svg") as svg_template_file:
            template = svg_template_file.read()
        soup = Soup(template, "xml")
        for i in range(1, 5):
            side = soup.find(id=f"side-{i}")
            side_letters = iter(self.sides[i-1])
            for letter_thing in side.find_all("g"):
                letter = next(side_letters)
                letter_thing.find("tspan").string = letter.upper()
                letter_thing["id"] = "letter-"+letter
        return soup

    def render(self) -> bytes:
        return svg2png(str(self.graphic), output_width=1000)

    def render_hint(self) -> Optional[bytes]:
        # try to find a word that hasn't been put out there by a user or given as a
        # hint already, prioritizing nice long ones
        hint_words = sorted(
            list(self.get_solutions_by_length(2).words),
            key=lambda x: len(x.word), reverse=True)
        hint_word = next((x for x in hint_words
                         if x not in self.hints_given and
                         x not in self.user_found_words), None)
        if not hint_word:
            return None
        else:
            self.hints_given.add(hint_word)
            self.save()
            hint_word = hint_word.word
        # copy the graphic into a new Soup for modification
        soup = Soup(str(self.graphic), "xml")
        soup.find(id="arrowsgroup").decompose()
        letter_pairs = []
        for i in range(0, len(hint_word)-1, 2):
            letter_pairs.append((hint_word[i], hint_word[i+1]))
        print(f"{hint_word} becomes {letter_pairs}")
        lettersgroup = soup.find(id="lettersgroup")
        for pair in letter_pairs:
            groups = [soup.find(id="letter-"+x) for x in pair]
            circles = [x.find("circle") for x in groups]
            for c in circles:
                c["style"] = c["style"].replace("stroke:#000000", "stroke:#f8aa9e")
            points = [{"x": float(x["cx"]), "y": float(x["cy"])} for x in circles]
            line = soup.new_tag(
                "line", x1=points[0]["x"],
                y1=points[0]["y"],
                x2=points[1]["x"],
                y2=points[1]["y"])
            line["stroke"] = "#f8aa9e"
            line["stroke-width"] = "1.5"
            line["stroke-dasharray"] = "5"
            lettersgroup.insert(0, line)
        return svg2png(str(soup), output_width=1000)

    @property
    def needed_letter_count(self):
        return 12
        # or return sum(map(self.sides, len)) for added headaches

    def get_valid_continuation(
            self,
            antecedent: Union[LetterBoxedWord, LetterBoxedSolution],
            min_points=-1,
            max_points=-1) -> set[LetterBoxedWord]:
        """
        Returns all valid follow-up words with scores in the range [min_points,
        max_points]. Duplicate words are not considered valid follow-ups.
        """
        if type(antecedent) is LetterBoxedSolution:
            last_word = antecedent.words[-1]
        else:
            last_word = antecedent
        if min_points == -1:
            min_points = self.min_word_score
        if max_points == -1:
            max_points = self.max_word_score
        result = set()
        for i in range(min_points, max_points+1):
            result = result.union(self.index[last_word.last_letter][i])
        result.discard(last_word)
        return result

    def _recursive_search(
        self,
        desired_length: int,
        words_so_far: LetterBoxedSolution = LetterBoxedSolution([])
    ) -> Optional[LetterBoxedSolutionSet]:
        """
        recursive method. takes a solution that's in the process of being built,
        finds each possible valid continuation word by searching self.index, and
        either continues the recursion or returns the resulting solution set.
        """
        if words_so_far.is_complete():
            # premature completion (this method would not have been called if
            # words_so_far was already the desired length)
            return None
        if desired_length == 1:
            # special case; no recursion required
            solutions = []
            for word in self.valid_words:
                solution = LetterBoxedSolution([word])
                if solution.is_complete():
                    solutions.append(solution)
            return LetterBoxedSolutionSet(solutions)
        if len(words_so_far) == 0:
            # we're just starting to build the solution; we can try any word because
            # we have nothing to follow. we just have to start the recursive calling
            # and gather and return the results.
            result = LetterBoxedSolutionSet()
            for word in self.valid_words:
                solutions = self._recursive_search(desired_length, words_so_far+word)
                if solutions is not None:
                    result += solutions
            result.finalize()
            return result
        elif len(words_so_far) == desired_length-1:
            # we only need to build and return the final solution set possible with
            # this "chain" so far
            result = []
            for followup in self.get_valid_continuation(
                    words_so_far, self.needed_letter_count - words_so_far.unique_letters):
                final = words_so_far + followup
                if final.is_complete():
                    result.append(final)
            return LetterBoxedSolutionSet(result)
        else:
            # this is a level of recursion between the beginning and the end; we just
            # have to continue the chain of words, call, and return the eventual
            # result. don't bother with words that will prematurely complete the
            # solution.
            results = LetterBoxedSolutionSet()
            for followup in self.get_valid_continuation(
                    words_so_far, 0, 12 - words_so_far.unique_letters):
                result = self._recursive_search(desired_length, words_so_far+followup)
                if result is not None:
                    results += result
            return results

    def get_solutions_by_length(self, length: int = 2) -> LetterBoxedSolutionSet:
        if length in self.found_solution_sets:
            return self.found_solution_sets[length]
        else:
            solutions = self._recursive_search(length)
            self.found_solution_sets[length] = solutions
            self.save()
            return solutions

    def get_solutions_quantity_statement(self):

        def sol(count: int) -> str:
            return add_s("solution", count)

        solutions = {n: self.get_solutions_by_length(n) for n in range(1, 3+1)}
        result = ""
        if len(solutions[1]):
            one = len(solutions[1])
            result += f"There {copula(one)} {num(one)} one-word {sol(one)} today. "

        two = len(solutions[2])
        two_r = len(solutions[2].common_word_solutions)
        three = len(solutions[3])
        three_r = len(solutions[3].common_word_solutions)
        result += (
            f"There {copula(two)} {num(two)} two-word {sol(two)} " +
            f"and {num(three)} three-word {sol(three)}. "
        )
        result += (
            "Limiting ourselves to the most common 100,000 words in the " +
            f"Google Books corpus, there {copula(two_r)} {num(two_r)} two-word " +
            f"{sol(two_r)} and {num(three_r)} three-word {sol(three_r)}."
        )

        return result

    def percentage_of_words_in_wiktionary(self):
        return round(
            (
                sum(int(x.word in wiktionary) for x in self.valid_words) /
                len(self.valid_words))
            * 100, 2)

    def react_to_words(self, words: list[str]) -> list[str]:
        reactions = []
        solutions = {n: self.get_solutions_by_length(n) for n in range(1, 3+1)}
        words = [LetterBoxedWord(x) for x in words]
        # scan single words
        user_found_words_count = len(self.user_found_words)
        for word in words:
            if word in self.valid_words:
                self.user_found_words.add(word)
            if word in solutions[2].words:
                if word in solutions[2].common_words:
                    reactions.append("🐫")
                else:
                    reactions.append("👀")
            if word in solutions[3].words:
                if word in solutions[3].common_words:
                    reactions.append("🌳")
                else:
                    reactions.append("🥶")
        if user_found_words_count != len(self.user_found_words):
            self.save()

        def has_solution(length: int) -> Optional[LetterBoxedSolution]:
            for i in range(len(words)-(length-1)):
                if length == 1:
                    subseq = [words[i]]
                else:
                    subseq = words[i:i+length]
                subseq = LetterBoxedSolution(subseq)
                if subseq.is_complete(True, self.valid_words):
                    return subseq
            return None

        # scan word sequences
        if has_solution(4):
            reactions.append("🥳")
        if has_solution(3):
            reactions.append("🥲")  # U+1F972; smiling-tear. no idea why it's invisible in vscode
        if has_solution(2):
            reactions.append("📦")
            reactions.append("👑")
        if has_solution(1):
            reactions.append("🤯")

        return list(dict.fromkeys(reactions))  # removes duplicates; maintains order

    def __repr__(self):
        return f"<LetterBoxed sides={self.sides} par={self.par} len(valid_words)={len(self.valid_words)}>"


# letterboxed scheduling:

current_letterboxed = LetterBoxed.retrieve_last_saved()
if current_letterboxed is not None:
    current_letterboxed.persist()


async def post_letterboxed(guild: discord.Guild, thread_id: int):
    global current_letterboxed
    new_boxed = await LetterBoxed.fetch_from_nyt()
    last_boxed = current_letterboxed

    # find long words not in wiktionary to show off
    unfound_words = list(
        map(
            lambda x: x.word,
            last_boxed.valid_words.difference(last_boxed.user_found_words))
    )
    unfound_words.sort(key=len, reverse=True)
    mystery_words = []

    def word_mysteriousness_test(x):
        return (
            x.casefold() not in wiktionary and
            all(SequenceMatcher(None, x, y).ratio() < 0.9 for y in mystery_words)
        )
    i = 0
    test_nullified = False
    word_source = iter(word for word in unfound_words if word_mysteriousness_test(word))
    while i < 5:
        mystery_word = next(word_source, None)
        if mystery_word is not None:
            mystery_words.append(mystery_word)
            i += 1
        else:
            # nullify the mysteriousness test if we've run out of words that meet it
            if not test_nullified:
                def word_mysteriousness_test(): return True
                test_nullified = True
            else:
                break
    mystery_words = list(map(lambda x: str(x).lower(), mystery_words))

    current_letterboxed = new_boxed
    current_letterboxed.persist()
    new_boxed_image = new_boxed.render()
    available_threads = await guild.active_threads()
    target_thread = next(x for x in available_threads if x.id == thread_id)
    await target_thread.join()
    message = ("Good noon ~ " +
               f"Today's puzzle is a par {new_boxed.par}. " +
               new_boxed.get_solutions_quantity_statement())
    if len(mystery_words) > 0:
        message += f" Some unfound words from yesterday were {andify(mystery_words)}."
    await target_thread.send(
        content=message,
        file=discord.File(BytesIO(new_boxed_image), "letterboxed.png")
    )


async def letterboxed_react(message: discord.Message):
    global current_letterboxed
    words = re.sub("\W", " ", message.content).split()
    if current_letterboxed is None:
        current_letterboxed = await LetterBoxed.fetch_from_nyt()
    for reaction in current_letterboxed.react_to_words(words):
        await message.add_reaction(reaction)


def add_letterboxed_functionality(client: MitchBot):
    post_new_letterboxed_at = time(hour=12, tzinfo=et)
    if not client.test_mode:
        letterboxed_thread_id = 897476378709065779  # production
        letterboxed_guild_id = 678337806510063626
    else:
        letterboxed_thread_id = 907998436853444658  # test
        letterboxed_guild_id = 708955889276551198
        if False:
            # in case we want to test puzzle posting directly
            post_new_letterboxed_at = (datetime.now(tz=et)+timedelta(seconds=5)).time()
    client.register_responder(MessageResponder(
        lambda m: m.channel.id == letterboxed_thread_id,
        letterboxed_react))
    asyncio.create_task(
        repeatedly_schedule_task_for(
            post_new_letterboxed_at,
            lambda: post_letterboxed(
                client.get_guild(letterboxed_guild_id),
                letterboxed_thread_id),
            "post_letterboxed"))

    async def obtain_hint(context: ApplicationContext):
        if current_letterboxed:
            hint = current_letterboxed.render_hint()
            if hint is not None:
                await context.respond(
                    content="Fill in the missing lines to make a Word.",
                    file=discord.File(
                        fp=BytesIO(hint),
                        filename="aletterboxedhint.png"
                    )
                )
            else:
                await context.respond("No hints left -  all out of hints.")
    client.register_hint(letterboxed_thread_id, obtain_hint)


async def test():
    puzzle = LetterBoxed.retrieve_last_saved()
    if puzzle is None:
        print("no puzzle in db, fetching from the times")
        puzzle = await LetterBoxed.fetch_from_nyt()
    print(puzzle)
    print(puzzle.get_solutions_by_length(2))
    print(puzzle.get_solutions_by_length(2).common_word_solutions)
    print(puzzle.get_solutions_quantity_statement())
    print(
        "percentage of today's words in wiktionary:",
        puzzle.percentage_of_words_in_wiktionary()
    )
    puzzle.react_to_words(["pulton", "neckwear"])
    puzzle.react_to_words(["CEPE", "ENWRAP", "PROLETKULT"])
    hint = puzzle.render_hint()
    if hint is not None:
        Image.open(BytesIO(hint)).show()
    else:
        print("no hints left; all out of hints")
    puzzle.persist()


if __name__ == "__main__":
    try:
        IOLoop.current().run_sync(test)
    except KeyboardInterrupt:
        print("Received SIGINT, exiting")
