from __future__ import annotations
import asyncio
from datetime import date, time, datetime, timedelta, timezone
import inspect
import random
from typing import Callable, TYPE_CHECKING

import disnake as discord

if TYPE_CHECKING:
    from MitchBot import MitchBot

from zoneinfo import ZoneInfo

from db.queries import get_random_city_timezone, get_random_poem, get_next_mail

et = ZoneInfo("America/New_York")


async def do_thing_after(seconds: float, thing: Callable, name: str = ""):
    """Utility function to call a function or create a task for a coroutine in a
    certain number of seconds"""
    print(
        "scheduling next", (name or thing.__name__), "for", seconds, "seconds from now"
    )
    await asyncio.sleep(seconds)
    if inspect.iscoroutinefunction(thing):
        asyncio.create_task(thing())
    else:
        result = thing()
        if asyncio.isfuture(result) or asyncio.iscoroutine(result):
            await result


def get_seconds_before_next(time_of_day: time) -> float:
    """Utility function to get the number of seconds before the next time a time of
    day occurs."""
    now = datetime.now(tz=timezone.utc).astimezone(time_of_day.tzinfo)
    if now.time() >= time_of_day:
        next_puzzle_day = now.date() + timedelta(days=1)
    else:
        next_puzzle_day = now.date()
    next_puzzle_time = datetime.combine(next_puzzle_day, time_of_day).astimezone(
        time_of_day.tzinfo
    )
    result = (next_puzzle_time - now).total_seconds()
    return result


async def repeatedly_schedule_task_for(
    time_of_day: time, task: Callable, name: str = ""
) -> None:
    """
    Schedules a task (a function or coroutine) to be performed every day at
    time_of_day in UTC.
    """
    waiting_time = get_seconds_before_next(time_of_day)
    await do_thing_after(waiting_time, task, name)
    await asyncio.sleep(10)  # just to make completely sure it doesn't get double called
    asyncio.create_task(repeatedly_schedule_task_for(time_of_day, task, name))


def schedule_tasks(client: MitchBot):
    async def wordle_joke():
        start_date = date(2022, 1, 1)
        start_number = 196
        wordle_number = start_number + (date.today() - start_date).days
        wordle_thread_id = 928243083479490561
        guild = client.get_guild(678337806510063626)
        available_threads = await guild.active_threads()
        target_thread = next(x for x in available_threads if x.id == wordle_thread_id)
        await target_thread.join()
        await target_thread.send(f"Wordle {wordle_number} 1/6\n\n🟩🟩🟩🟩🟩")

    wordle_time = time(hour=0, minute=0, second=5, tzinfo=et)
    # asyncio.create_task(repeatedly_schedule_task_for(wordle_time, wordle_joke))

    # poetry scheduling:
    poem_time = time(hour=2, tzinfo=et)
    if client.test_mode:
        poem_time = (datetime.now(tz=et) + timedelta(seconds=5)).time()  # test

    async def send_poem():
        poetry_channel_id = (
            678337807764422691 if not client.test_mode else 888301952067325952
        )
        next_mail = get_next_mail()
        a_city, a_zone = get_random_city_timezone()
        a_time = datetime.now().astimezone(ZoneInfo(a_zone))
        a_body = random.choice(
            [
                "Mercury",
                "Venus",
                "Mars",
                "Earth",
                "Jupiter",
                "Saturn",
                "Neptune",
                "Pluto",
                "Cassiopeia",
                "Ceres",
                "Charon",
                "Ganymede",
                "The ISS",
                "Alpha Centauri",
                "The Sombrero Galaxy",
                "The Tadpole Galaxy",
                "Hoag's Object",
            ]
        )
        a_state = random.choice(
            [
                "retrograde",
                "intrograde",
                "astrograde",
                "interrograde",
                "terragrade",
                "fluxigrade",
                "axigrade",
                "centigrade",
                "tardigrade",
                "upgrade",
                "demigrade",
                "distastigrade",
                "deltagrade",
                "orthograde",
                "fermigrade",
                "esograde",
                "altigrade",
                "bizarrograde",
                "essentiagrade",
            ]
        )
        prelude = (
            "Good evening. "
            + f"It's {int(a_time.strftime('%I'))}:{a_time.strftime('%M %p')} "
            + f"in {a_city}. {a_body} is in {a_state}. "
        )

        prelude += "Tonight's top story is:"
        # original from 2022:
        animals = [
            "cat",
            "dog",
            "alligator",
            "ostrich",
            "llama",
            "bunny",
            "bird",
            "cow",
            "horsie",
            "penguin",
            # "frog",
            # "chinchilla",
            "meerkat",
            # "snake",
            # "duck",
            "catboy",
            "raccoon",
            "gila monster",
            # "komodo dragon",
            "unicorn",
            # new:
            "band on the run",
            "pteradon",
            "mere cat",
            "Sweet Caroline",
            "Santa Claus",
            "beast",
            "pop star",
            "venus flytrap",
            "boomerang",
            "higgs boson",
            "tropical depression",
            "narwhal",
            "seal",
            "nightmare",
            "ostrich",
            "Wicked Witch of the West",
            "disaster bi",
            "strange loop",
            "Toronto Maple Leafs fan",
            "Tim Curry",
            "Gene Simmons",
            "bot",
            "Saturn Devouring his Son",
            "gambler",
        ]

        sounds = [
            # original:
            "mew",
            # "[REDACTED]",
            # "oink",
            # "boing",
            # "pew pew pew",
            "brrring",
            "boom",
            '"hey guys what\'s up"',
            "hiss",
            # "snort",
            "grrr",
            # "bzzz",
            "squeak",
            "purr",
            # "cock-a-doodle-doo",
            # "chirp",
            # "clang",
            # "hee-haw",
            "FNRNRNRNRNRNNNRNRNR (elephant noise)",
            "honk",
            # "neigh",
            "hah-hah-hah",
            # "coo",
            # "waf",
            "yap",
            "awooo",
            "baa",
            "quack"
            # new:
            "E-I-E-I-O",
            "nyoom",
            "death is but a door; time is a but a window. i'll be back",
            "🥺",
            "And as for my gambling, it's true I lost it all a few times. But that's because I always took the long shot and it never came in. But I still have some time before I cross that river. And if you're at the table and you're rolling them bones, then there's no money in playing it safe. You have to take all your chips and put them on double six and watch as every eye goes to you and then to those red dice doing their wild dance and freezing time before finding the cruel green felt.\n\nI've been lucky.",
            "switch it up like nintendo",
            "mew! mew! mew! mew!",
            "I am 30 or 40 years old and I do not need this",
            '"It\'s 2am bitches"',
            "Don't talk to me before I've had my ~GAMING~",
        ]
        poem = (
            f"what if there was a little {random.choice(animals)} that "
            + f"went {random.choice(sounds)}"
        )
        body = "\n".join("> " + x for x in poem.split("\n"))
        embed = None
        if datetime.now().isoformat().startswith("2022-10-19"):
            body = "> what if there was a little..... what am i doing with my life. i can't do this anymore"
        elif datetime.now().isoformat().startswith("2025-05-14"):
            body = '> "It\'s 2 am bitches"'
        elif datetime.now().isoformat().startswith("2025-05-15"):
            body = "> And as for my gambling, it's true I lost it all a few times. But that's because I always took the long shot and it never came in. But I still have some time before I cross that river. And if you're at the table and you're rolling them bones, then there's no money in playing it safe. You have to take all your chips and put them on double six and watch as every eye goes to you and then to those red dice doing their wild dance and freezing time before finding the cruel green felt.\n\nI've been lucky."
        elif datetime.now().isoformat().startswith("2025-05-16"):
            body = "> what if there was a little gambler that went boing"
        await client.get_channel(poetry_channel_id).send(prelude, embed=embed)
        if body:
            await client.get_channel(poetry_channel_id).send(body)

    asyncio.create_task(repeatedly_schedule_task_for(poem_time, send_poem))


async def test():
    pass  # ???


if __name__ == "__main__":
    asyncio.run(test())
