"""
Provides functions to access the word frequency and wiktionary words databases (which
are in SQLite and bespoke trie database forms, respectively) as well as the nicknames
in db/nicknames.json and poetry from text/poetry.txt. The RandomNoRepeats class
defined here is also useful in general. Note: the paths within this file are
constructed with the expectation that the CWD will be the root directory of the
repository. Puzzles are persisted via code in the SpellingBee and Letterboxed classes
(not here.)
"""

import json
import sqlite3
from typing import Any, Optional
from timeit import default_timer as timer
import random
from typing import Sequence
from math import inf

from timezonefinder import TimezoneFinder


words_db = sqlite3.connect("db/words.db")


def get_word_rank(word: str) -> int:
    """
    Exposes the word frequency data stored in words.db to easy python access. The
    lower the rank, the more common the word.
    """
    cur = words_db.cursor()
    rank = cur.execute(
        "select rank from words where word=?",
        (word.lower(),)
    ).fetchone()
    return inf if rank is None else rank[0]


cities_db = sqlite3.connect("db/cities.db")


def get_random_city_timezone() -> tuple[str, str]:
    cur = cities_db.cursor()
    random_city = cur.execute(
        "select city, longitude, latitude from location " +
        "order by random() limit 1").fetchone()
    finder = TimezoneFinder()
    zone = finder.timezone_at(lng=random_city[1], lat=random_city[2])
    return (random_city[0], zone)


def get_random_nickname() -> str:
    with open("db/nicknames.json", encoding="utf-8") as nickname_file:
        return random.choice(json.load(nickname_file))


def get_random_strategy() -> str:
    with open("text/strategies.txt", encoding="utf-8") as strategy_file:
        return random.choice(strategy_file.read().split("\n"))


def get_next_mail(mark_retrieved=True) -> Optional[str]:
    with open("db/mail.json", encoding="utf-8", mode="r+") as mail_file:
        mailbag = json.load(mail_file)
        assert all("text" in x and "retrieved" in x for x in mailbag)
        next_mail = next((x for x in mailbag if not x["retrieved"]), None)
        if next_mail is not None:
            if mark_retrieved:
                next_mail["retrieved"] = True
                mail_file.seek(0)
                json.dump(mailbag, mail_file)
                mail_file.truncate()
            return next_mail["text"]
        return None


class RandomNoRepeats:
    """
    Class that wraps a sequence and returns a random item from it, repeating items
    only when every item in the sequence has already been used once and never
    returning the same item twice in a row. This class persists its state through the
    SQLite file db/random.db. Because the client may wish to change the contents of a
    specific sequence between program executions, sequences are uniquely identified
    by a string name rather than by their contents; items need to be convertable to
    strings (by implementing __str__ or __repr__) to be stored. Items that were not
    present during previous instantiations of a specific named sequence and have
    never been returned before will always be prioritized over every item that has
    been returned before; instantiating a new named sequence without an item that it
    previously contained is equivalent to removing it from the sequence forever.
    """
    random_db = sqlite3.connect("db/random.db")
    cursor = random_db.cursor()

    @classmethod
    def get_new_access_id(cls):
        """Returns the greatest integer currently saved in the random table as an
        access id plus one."""
        result = cls.cursor.execute(
            "select last_access_id from random order by last_access_id desc limit 1"
        ).fetchone()
        return result[0]+1

    def __init__(self, source: Sequence, name: str):
        if len(source) < 2:
            assert("RandomNoRepeats object needs > 1 source items")
        self.source = list(source)
        self.name = name

        cur = self.cursor
        # id is arbitrary; name is self.name; item is the string version of the item
        # passed to the constructor as source; and last_access_id stores a unique
        # integer that identifies the get_item call that most recently returned this
        # item (or is -1 if it hasn't been accessed.) last_access_id is used to make
        # sure that get_item never returns the same item twice in a row, even when
        # all the items associated with the collection name have been accessed an
        # equal number of times.
        cur.execute(
            "create table if not exists random " +
            "(id integer primary key, name text, item text, " +
            "uses integer, last_access_id int)")
        cur.execute("create index if not exists uses_by_name " +
                    "on random (name, uses, last_access_id)")

        existing_items: set[str] = set(x[0] for x in cur.execute(
            "select item from random where name=?",
            (name,)).fetchall())
        # this may very well end up being a mapping of strings to themselves...
        self.item_lookup: dict[str, Any] = {str(x): x for x in source}

        for string in self.item_lookup.keys():
            if string not in existing_items:
                cur.execute(
                    "insert into random (name, item, uses, last_access_id) values (?, ?, ?, ?)",
                    (name, string, 0, -1)
                )
        for string in existing_items:
            if string not in self.item_lookup:
                cur.execute("delete from random where name=? and item=?",
                            (name, string)
                            )

        self.random_db.commit()

    def get_item(self):
        """Returns a random item that has been returned fewer times than or, when
        necessary, the same number of times as every other item. Never returns the
        same item twice in a row."""
        # find the least and most number of times any element has been used and the
        # id of the last access that retrieved an item with name==self.name from the
        # table
        least_uses = self.cursor.execute(
            "select uses from random where name=? " +
            "order by uses limit 1",
            (self.name,)).fetchone()[0]
        most_uses = self.cursor.execute(
            "select uses from random where name=? " +
            "order by uses desc limit 1",
            (self.name,)).fetchone()[0]
        last_access = self.cursor.execute(
            "select last_access_id from random where name=? " +
            "order by last_access_id desc limit 1",
            (self.name,)).fetchone()[0]
        # select a random element that has been used the least number of times any
        # element has been used AND wasn't the last element to be accessed among
        # those with name==self.name (as determined by the greatest last_access_id).
        # if the greatest last_access_id is -1, it means that no items in this named
        # category have ever been accessed, so we can ignore this condition.
        item = self.cursor.execute(
            "select item from random where name=? and uses=? and " +
            "(last_access_id=-1 or last_access_id!=?) order by random() limit 1",
            (self.name, least_uses, last_access)).fetchone()[0]
        # set the uses count of the item that was just used to the greatest number of
        # uses of any item in that named group, unless all the numbers of uses are
        # equal, in which case we need to increment from the current greatest number
        # of uses. this number may be inaccurate for items that were just inserted
        # and are being used for the first time, but we do not want such items to be
        # used e. g. 5 times in a row to catch up in the case that all the other
        # items have been used at least 5 times, so this is the best way to handle
        # that.
        new_uses = most_uses
        if most_uses == least_uses:
            new_uses += 1
        self.cursor.execute(
            "update random set uses=?, last_access_id=? where item=?",
            (new_uses, self.get_new_access_id(), item)
        )
        self.random_db.commit()
        return self.item_lookup[item]


with open("text/poetry.txt", encoding="utf-8") as poetry_file:
    raw_poems = poetry_file.read().split("\n---\n")
poetry = [p.strip() for p in raw_poems if p.strip()]
poetry_source = RandomNoRepeats(poetry, "poetry")


def get_random_poem() -> str:
    return poetry_source.get_item()


if __name__ == "__main__":
    print("random city and timezone:", get_random_city_timezone())
    print()
    print("some words ordered by frequency:")
    print(
        sorted(
            ["especially", "when", "dogs", "should", "vote"],
            key=get_word_rank))
    print()
    print("random nickname:", get_random_nickname())
    print()
    RandomNoRepeats.random_db = sqlite3.connect(":memory:")
    RandomNoRepeats.cursor = RandomNoRepeats.random_db.cursor()
    print("10 outputs from RandomNoRepeats coin flips:")
    flipper = RandomNoRepeats(["heads", "tails"], "coins")
    test_flips = [flipper.get_item() for _ in range(10)]
    print(", ".join(test_flips))
    for i in range(7):
        subsequence = test_flips[i:i+2]
        assert subsequence[0] != subsequence[1], "no same result twice in a row"
    print("10 outputs from RandomNoRepeats coin flips with a replaced item:")
    new_flipper = RandomNoRepeats(["heads", "tails", "not heads"], "coins")
    test_flops = [new_flipper.get_item() for _ in range(10)]
    print(", ".join(test_flops))
    assert test_flops[0] == "not heads", "new elements chosen immediately"
    for j in range(1, 8, 3):
        subsequence = test_flops[j:j+3]
        assert subsequence[0] != subsequence[1], "no same result twice in a row"
        assert subsequence[1] != subsequence[2], "no same result twice in a row"
        for element in ("heads", "tails", "not heads"):
            assert element in subsequence, "subsequence draws from all available elements equally"
    print("next item in mailbag:")
    print(get_next_mail(False))
    print("tests passed")
