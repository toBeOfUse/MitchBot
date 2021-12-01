from __future__ import annotations
import asyncio
from io import BytesIO
import json
from os import PathLike
import re
import sqlite3
from typing import Optional, TYPE_CHECKING
import traceback
from datetime import datetime, time, timedelta
import random
from timeit import default_timer as timer
from enum import Enum
from collections import defaultdict
from zoneinfo import ZoneInfo

from tornado.httpclient import AsyncHTTPClient
import discord
from PIL import Image

from db.queries import get_wiktionary_trie, get_random_renderer, get_word_rank, get_random_strategy
from render import PuzzleRenderer
from responders import MessageResponder
from grammar import andify, copula, add_s, num
from scheduler import repeatedly_schedule_task_for
if TYPE_CHECKING:
    from MitchBot import MitchClient
    from discord.commands.context import ApplicationContext


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

    Attributes:
        todays (Puzzle): static, always stores the last constructed Puzzle
        yesterdays (Puzzle): static, always stores the second-to-last constructed Puzzle
    """

    todays: Puzzle = None
    yesterdays: Puzzle = None

    class GuessJudgement(Enum):
        wrong_word = 1
        good_word = 2
        pangram = 3
        already_gotten = 4

    class HintTable:
        def __init__(self, words: list[str]):
            words = [w.lower() for w in words]
            self.empty: bool = len(words) == 0
            self.one_letters: dict[dict[int, int]] = defaultdict(lambda: defaultdict(lambda: 0))
            self.two_letters: dict[int] = defaultdict(lambda: 0)
            self.word_lengths: set[int] = set()
            self.pangram_count = 0
            for word in words:
                self.word_lengths.add(len(word))
                self.one_letters[word[0]][len(word)] += 1
                self.two_letters[word[0:2]] += 1
                if len(set(word)) == 7:
                    self.pangram_count += 1

        def format_table(self) -> str:
            if self.empty:
                return "There are no remaining words."
            f = "   "+" ".join(f"{x:<2}" for x in sorted(list(self.word_lengths)))+" Σ \n"
            sorted_lengths = sorted(list(self.word_lengths))
            sums_by_length = {x: 0 for x in sorted_lengths}
            for letter, counts in sorted(
                    list(self.one_letters.items()), key=lambda i: i[0]):
                f += f"{letter.upper()}  " + " ".join(
                    (f"{counts[c]:<2}" if counts[c] != 0 else "- ") for c in sorted_lengths)
                f += f" {sum(counts.values()):<2}\n"
                for length, count in counts.items():
                    sums_by_length[length] += count
            f += "Σ  "+" ".join(f"{c:<2}" for c in sums_by_length.values())
            f += f" {sum(sums_by_length.values())}"
            return f

        def format_two_letters(self) -> str:
            sorted_2l = sorted(
                list(self.two_letters.items()), key=lambda x: x[0]
            )
            return ", ".join(
                f"{l[0].upper()}{l[1]}: {c}" for (l, c) in sorted_2l)

        def format_pangram_count(self) -> str:
            c = self.pangram_count
            return f"There {copula(c)} {num(c)} remaining {add_s('pangram', c)}."

        def format_all_for_discord(self) -> str:
            result = f"```\n{self.format_table()}\n```\n"
            result += self.format_two_letters()
            result += "\n"
            result += self.format_pangram_count()
            return result

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
        if (all(l in [self.center]+self.outside for l in "ACAB") and
                self.center in "ACAB"):
            self.answers.add("acab")
        for word in self.pangrams:
            self.answers.add(word)  # shouldn't be necessary but just in case
        self.gotten_words = set(w.lower() for w in gotten_words)
        self.image: Optional[bytes] = None
        self.message_id: int = -1
        self.db_path: Optional[str] = None
        Puzzle.yesterdays = Puzzle.todays
        Puzzle.todays = self

    def __eq__(self, other):
        return self.center+self.outside == other.center+other.outside

    @property
    def percentage_complete(self):
        return round(len(self.gotten_words) / len(self.answers) * 100, 1)

    def does_word_count(self, word: str) -> bool:
        return word.lower() in self.answers

    def is_pangram(self, word: str) -> bool:
        return word.lower() in self.pangrams

    def guess(self, word: str) -> set[GuessJudgement]:
        """
        determines whether a word counts for a point and/or is a pangram and/or has
        already been gotten. uses the GuessJudgement enum inner class.
        """
        result = set()
        w = word.lower()
        if self.does_word_count(w):
            result.add(self.GuessJudgement.good_word)
            if self.is_pangram(w):
                result.add(self.GuessJudgement.pangram)
            if w in self.gotten_words:
                result.add(self.GuessJudgement.already_gotten)
            self.gotten_words.add(w)
            self.save()
        else:
            result.add(self.GuessJudgement.wrong_word)
        return result

    def get_unguessed_words(self, sort=True) -> list[str]:
        """returns the heretofore unguessed words in a list sorted from the least to
        the most common words."""
        unguessed = list(self.answers - self.gotten_words)
        if sort:
            unguessed.sort(key=lambda w: get_word_rank(w), reverse=True)
        return unguessed

    def get_unguessed_hints(self) -> HintTable:
        return self.HintTable(self.get_unguessed_words(sort=False))

    def get_wiktionary_alternative_answers(self) -> list[str]:
        """
        Returns the words that use the required letters and are english words
        according to Wiktionary (according to data obtained by
        https://github.com/tatuylonen/wiktextract) but aren't in the official answers
        list, sorted from most to least common (they... may all be quite uncommon)
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
            for character in word:
                if character.upper() not in (self.outside + [self.center]):
                    break
            else:
                result.append(word)
        return sorted(result, key=lambda w: get_word_rank(w))

    async def render(self, renderer: PuzzleRenderer = None) -> bytes:
        """Renders the puzzle to an image; returns the image file as bytes and caches
        it in the image instance variable. If you do not pass in an instance of a
        subclass of PuzzleRenderer, one will be provided for you via
        get_random_renderer from queries.py."""
        if renderer is None:
            renderer = get_random_renderer()
        self.image = await renderer.render(self)
        return self.image

    @property
    def image_file_type(self) -> Optional[str]:
        if self.image is None:
            return None
        elif self.image[0:4] == b"\x89PNG":
            return "png"
        elif self.image[0:3] == b"GIF":
            return "gif"
        elif self.image[0:2] == b"\xff\xd8":
            return "jpg"

    def associate_with_message(self, message: discord.Message):
        """Used to give a puzzle a Discord message ID that can be saved in the
        database and retrieved with the puzzle so that Discord client code can
        retrieve that message and update it with puzzle status information whenever
        it wants. Technically violates separation of concerns, and the Discord
        API-oriented code should persist this data itself, but oh well it's just one
        integer"""
        self.message_id = message.id
        self.save()

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

    def respond_to_guesses(self, message: discord.Message) -> list[str]:
        """
        Discord bot-specific function for awarding points in the form of reactions;
        returns a list of emojis.
        """
        num_emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        reactions = []
        words = set(re.sub("\W", " ", message.content).split())
        points = 0
        pangram = False
        already_gotten = False
        for word in words:
            guess_result = self.guess(word)
            if Puzzle.GuessJudgement.good_word in guess_result:
                points += 1
            if Puzzle.GuessJudgement.pangram in guess_result:
                pangram = True
            if Puzzle.GuessJudgement.already_gotten in guess_result:
                already_gotten = True
        if points > 0:
            reactions.append("👍")
            if points > 1:
                for num_char in str(points):
                    reactions.append(num_emojis[int(num_char)])
        if pangram:
            reactions.append("🍳")
        if already_gotten:
            reactions.append("🤝")
        return reactions

    def persist(self, db_path: PathLike = "db/puzzles.db"):
        """Sets a puzzle object up to be saved in the given database. This method
        must be called on an object for it to persist and be returnable by
        retrieve_last_saved. After it is called, the puzzle object will automatically
        update its record in the database whenever its state changes."""
        self.db_path = db_path
        self.save()

    @classmethod
    def get_connection(self, db_path: PathLike) -> Optional[sqlite3.Connection]:
        """Connects to the database, ensures the table exists with the correct
        schema, and returns the connection."""
        latest_version = 1
        if db_path is None:
            return None
        db = sqlite3.connect(db_path)
        cur = db.cursor()
        cur.execute("""create table if not exists puzzles
            (timestamp integer primary key, message_id integer, center text, outside text,
            pangrams text, answers text, gotten_words text);""")
        cur.execute("""create index if not exists chrono on puzzles (timestamp desc);""")

        current_version = cur.execute("pragma user_version").fetchone()[0]
        if current_version == 0:
            cur.execute("alter table puzzles add column image bytes")
            cur.execute(f"pragma user_version={latest_version}")
            db.commit()
        return db

    def save(self):
        """Serializes the puzzle and saves it in a SQLite database."""
        db = self.get_connection(self.db_path)
        if db is None:
            return
        cur = db.cursor()
        cur.execute(
            """insert or replace into puzzles
            (timestamp, message_id, center, outside, pangrams, answers, gotten_words, image)
            values (?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.timestamp, self.message_id, self.center, json.dumps(list(self.outside)),
             json.dumps(list(self.pangrams)),
             json.dumps(list(self.answers)),
             json.dumps(list(self.gotten_words)),
             self.image))
        db.commit()
        db.close()

    @classmethod
    def retrieve_last_saved(cls, db_path: str = "db/puzzles.db") -> Optional["Puzzle"]:
        """Retrieves the most recently saved puzzle from the SQLite database. Note
        that the returned object is separate from the database record until/unless
        persist() is called to assign it to the same database again."""
        db = cls.get_connection(db_path)
        cur = db.cursor()
        try:
            latest = cur.execute("""select
                timestamp, message_id, image, center, outside, pangrams, answers, gotten_words
                from puzzles order by timestamp desc limit 1""").fetchone()
            if latest is None:
                db.close()
                return None
            else:
                db.close()
                loaded_puzzle = cls(
                    latest[0],
                    latest[3],
                    *[json.loads(x) for x in latest[4:]])
                loaded_puzzle.message_id = latest[1]
                loaded_puzzle.image = latest[2]
                return loaded_puzzle
        except:
            print("couldn't load latest puzzle from database")
            traceback.print_exc()
            db.close()
            return None


# functions used by the Discord bot

async def fetch_new_puzzle(quick_render=False):
    print("fetching puzzle from NYT...")
    await Puzzle.fetch_from_nyt()
    print("fetched. rendering graphic...")
    await Puzzle.todays.render(
        PuzzleRenderer.available_renderers[0] if quick_render else None
    )
    print("graphic rendered. saving today's puzzle in database")
    Puzzle.todays.persist()


async def post_new_puzzle(channel: discord.TextChannel):
    current_puzzle = Puzzle.todays
    message_text = random.choice(["Good morning",
                                  "Goedemorgen",
                                  "Bon matin",
                                  "Ohayō",
                                  "Back at it again at Krispy Kremes",
                                  "Hello",
                                  "Bleep Bloop",
                                  "Here is a puzzle",
                                  "Guten Morgen"])+" ✨"
    alt_words = current_puzzle.get_wiktionary_alternative_answers()
    if len(alt_words) > 1:
        alt_words_sample = alt_words[:5]
        message_text += (
            " Words from Wiktionary that should count today that the NYT "
            f"fails to acknowledge include: {andify(alt_words_sample)}.")
    if Puzzle.yesterdays is not None:
        previous_words = Puzzle.yesterdays.get_unguessed_words()
        if len(previous_words) > 1:
            message_text += (
                " The least common word that no one got for yesterday's "
                f"puzzle was \"{previous_words[0]};\" "
                f"the most common word was \"{previous_words[-1]}.\""
            )
        elif len(previous_words) == 1:
            message_text += (
                " The only word no one got yesterday was " +
                previous_words[0] +
                "."
            )
    puzzle_filename = "puzzle."+current_puzzle.image_file_type
    await channel.send(
        content=message_text,
        file=discord.File(BytesIO(current_puzzle.image), puzzle_filename))
    status_message = await channel.send(content="Words found by you guys so far: None~")
    current_puzzle.associate_with_message(status_message)


async def respond_to_guesses(message: discord.Message):
    if Puzzle.todays is None:
        return
    current_puzzle = Puzzle.todays
    already_found = len(current_puzzle.gotten_words)
    reactions = current_puzzle.respond_to_guesses(message)
    for reaction in reactions:
        await message.add_reaction(reaction)
    if len(current_puzzle.gotten_words) == already_found:
        return
    try:
        puzzle_channel = message.channel
        status_message: discord.Message = (
            await puzzle_channel.fetch_message(current_puzzle.message_id)
        )
        found_words = sorted(
            list(current_puzzle.gotten_words-current_puzzle.pangrams)
        )
        status_text = 'Words found by you guys so far: '
        status_text += f'||{andify(found_words)}.|| '
        found_pangrams = sorted(
            list(current_puzzle.gotten_words & current_puzzle.pangrams)
        )
        if len(found_pangrams) > 0:
            status_text += f"Pangrams: ||{andify(found_pangrams)}.|| "
        status_text += f'({current_puzzle.percentage_complete}% complete'
        if current_puzzle.percentage_complete == 100:
            status_text += " 🎉)"
        else:
            status_text += ")"
        await status_message.edit(content=status_text)

    except:
        print("could not retrieve Discord message and update puzzle status !!!")
        traceback.print_exc()


def add_bee_functionality(bot: MitchClient):
    try:
        Puzzle.retrieve_last_saved()
    except:
        print("could not retrieve last puzzle from database; " +
              "puzzle functionality will stop until the next one is loaded")

    et = ZoneInfo("America/New_York")
    fetch_new_puzzle_at = time(hour=6, minute=50, tzinfo=et)
    post_new_puzzle_at = time(hour=7, tzinfo=ZoneInfo("America/New_York"))
    if not bot.test_mode:
        puzzle_channel_id = 814334169299157001  # production
        quick_render = False
    else:
        puzzle_channel_id = 888301952067325952  # test
        if True:
            # in case we want to test puzzle posting directly
            fetch_new_puzzle_at = (datetime.now(tz=et)+timedelta(seconds=10)).time()
            post_new_puzzle_at = (datetime.now(tz=et)+timedelta(seconds=20)).time()
            quick_render = True

    puzzle_channel = bot.get_channel(puzzle_channel_id)
    asyncio.create_task(repeatedly_schedule_task_for(
        fetch_new_puzzle_at, lambda: fetch_new_puzzle(quick_render), "fetch_new_puzzle"))
    asyncio.create_task(repeatedly_schedule_task_for(
        post_new_puzzle_at, lambda: post_new_puzzle(puzzle_channel), "post_new_puzzle"))

    bot.register_responder(MessageResponder(
        lambda m: m.channel.id == puzzle_channel_id, respond_to_guesses))

    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        if before.author.id == bot.user.id:
            return
        if after.channel.id == puzzle_channel_id:
            if before.content != after.content:
                # remove old reactions
                for reaction in after.reactions:
                    if reaction.me:
                        await reaction.remove(bot)
                # replace with new ones
                await respond_to_guesses(after)

    @bot.slash_command(guild_ids=bot.command_guild_ids)
    async def obtain_hint(ctx: ApplicationContext):
        "Spelling Bee hints or life advice (depending on the channel)"
        if ctx.channel_id == puzzle_channel_id:
            await ctx.respond(
                Puzzle.todays.get_unguessed_hints().format_all_for_discord()
            )
        else:
            await ctx.respond(get_random_strategy())


async def test():
    print("rank of 'puzzle'", get_word_rank("puzzle"))
    saved_puzzle = Puzzle.retrieve_last_saved("db/testpuzzles.db")
    if saved_puzzle is None:
        print("fetching puzzle from nyt")
        puzzle = await Puzzle.fetch_from_nyt()
    else:
        print("retrieved puzzle from db")
        puzzle = saved_puzzle
        if (datetime.now()
            - datetime.fromtimestamp(puzzle.timestamp)
                > timedelta(days=1)):
            print("puzzle from db was old, replacing it with current NYT one")
            puzzle = await Puzzle.fetch_from_nyt()
        else:
            print("puzzle from db is",
                  datetime.now() - datetime.fromtimestamp(puzzle.timestamp), "old")
    puzzle.persist("db/testpuzzles.db")
    print("today's words from least to most common:")
    print(puzzle.get_unguessed_words())
    # answers = iter(puzzle.answers)
    # puzzle.guess(next(answers))
    print("words that the nyt doesn't want us to know about:")
    print(random.sample(puzzle.get_wiktionary_alternative_answers(), 5))
    puzzle.save()

    print("Hints table:")
    table = puzzle.get_unguessed_hints()
    print(table.format_table())
    print(table.format_two_letters())
    print(table.format_pangram_count())

    rendered = await puzzle.render()
    if puzzle.image_file_type == "png":
        print("displaying rendered png")
        if not Image.open(BytesIO(rendered)).show():
            print("also saving it")
            with open("images/testrenders/puzzletest.png", "wb+") as test_output:
                test_output.write(rendered)
    elif puzzle.image_file_type == "gif":
        with open("images/testrenders/puzzletest.gif", "wb+") as test_output:
            test_output.write(rendered)
            print("wrote puzzletest.gif to images folder")


if __name__ == "__main__":
    asyncio.run(test())
