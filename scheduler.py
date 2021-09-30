import asyncio
from io import BytesIO
import re
from datetime import time, datetime, timedelta, timezone
import inspect
import random
from typing import Callable, Optional
import traceback

import discord

from MitchBot import MessageResponder, MitchClient
from textresources import poetry_generator
from puzzle import Puzzle


async def do_thing_after(seconds: float, thing: Callable):
    """Utility function to call a function or create a task for a coroutine in a
    certain number of seconds"""
    print("scheduling next", thing.__name__, "for", seconds, "seconds from now")
    await asyncio.sleep(seconds)
    if inspect.iscoroutinefunction(thing):
        asyncio.create_task(thing())
    else:
        thing()


def get_seconds_before_next(time_of_day: time) -> float:
    """Utility function to get the number of seconds before the next time a time of
    day occurs in UTC"""
    now = datetime.now(tz=timezone.utc)
    if now.time().replace(tzinfo=timezone.utc) >= time_of_day:
        next_puzzle_day = now.date()+timedelta(days=1)
    else:
        next_puzzle_day = now.date()
    next_puzzle_time = datetime.combine(next_puzzle_day, time_of_day)
    result = (next_puzzle_time - now).total_seconds()
    return result


async def repeatedly_schedule_task_for(time_of_day: time, task: Callable) -> None:
    """
    Schedules a task (a function or coroutine) to be performed every day at
    time_of_day in UTC.
    """
    waiting_time = get_seconds_before_next(time_of_day)
    await do_thing_after(waiting_time, task)
    await asyncio.sleep(10)  # just to make completely sure it doesn't get double called
    asyncio.create_task(repeatedly_schedule_task_for(time_of_day, task))


def schedule_tasks(client: MitchClient):
    # puzzle scheduling:
    puzzle_channel_id = 814334169299157001  # production
    # puzzle_channel_id = 888301952067325952  # test
    fetch_new_puzzle_at = time(hour=7+4, tzinfo=timezone.utc)  # 7am EDT
    # fetch_new_puzzle_at = (datetime.now(tz=timezone.utc)+timedelta(seconds=15)
    #                        ).time().replace(tzinfo=timezone.utc)  # test
    current_puzzle: Optional[Puzzle] = None
    last_puzzle_post: Optional[Puzzle] = None

    async def load_puzzle():
        await client.wait_until_ready()
        nonlocal current_puzzle, last_puzzle_post
        current_puzzle = Puzzle.retrieve_last_saved()
        if current_puzzle is not None:
            print("retrieved current puzzle from database")
            try:
                last_puzzle_post = await (client.get_channel(puzzle_channel_id)
                                          .fetch_message(current_puzzle.message_id))
                print("retrieved last puzzle post")
            except:
                print("could not retrieve last puzzle post")
                traceback.print_exc()
        else:
            print("could not retrieve current puzzle from database")

    asyncio.create_task(load_puzzle())

    async def send_new_puzzle():
        nonlocal current_puzzle, last_puzzle_post
        previous_puzzle = current_puzzle
        current_puzzle = await Puzzle.fetch_from_nyt()
        last_puzzle_post = await client.get_channel(puzzle_channel_id).send(
            content=random.choice(["Good morning",
                                   "Goedemorgen",
                                   "Bon matin",
                                   "Ohayō",
                                   "Back at it again at Krispy Kremes",
                                   "Hello",
                                   "Bleep Bloop",
                                   "Here is a puzzle",
                                   "Guten Morgen"])+" ✨",
            file=discord.File(BytesIO(current_puzzle.render()), 'puzzle.png'))
        current_puzzle.associate_with_message(last_puzzle_post)
        current_puzzle.save()
        if previous_puzzle:
            previous_words = previous_puzzle.get_unguessed_words()
            if len(previous_words) > 1:
                await client.get_channel(puzzle_channel_id).send(
                    "(The least common word that no one got for yesterday's "
                    + f"puzzle was \"{previous_words[0]}\"; "
                    + f"the most common word was \"{previous_words[-1]}\".)"
                )

    asyncio.create_task(repeatedly_schedule_task_for(fetch_new_puzzle_at, send_new_puzzle))

    async def respond_to_guesses(message: discord.Message):
        if current_puzzle is not None:
            await current_puzzle.respond_to_guesses(message)
            if current_puzzle.percentageComplete > 0 and last_puzzle_post is not None:
                base_content = re.sub("\(.*\)", "", last_puzzle_post.content).strip()
                await last_puzzle_post.edit(
                    content=(base_content
                             + f" ({current_puzzle.percentageComplete}% complete)"
                             )
                )

    client.register_responder(MessageResponder(
        lambda m: m.channel.id == puzzle_channel_id, respond_to_guesses))

    # poetry scheduling:

    async def send_poem():
        poetry_channel_id = 678337807764422691  # production
        # poetry_channel_id = 888301952067325952  # test
        await client.get_channel(poetry_channel_id).send(next(poetry_generator))
    poem_time = time(hour=2+4, tzinfo=timezone.utc)  # 2am EDT
    asyncio.create_task(repeatedly_schedule_task_for(poem_time, send_poem))


async def test():
    pass

if __name__ == "__main__":
    asyncio.run(test())
