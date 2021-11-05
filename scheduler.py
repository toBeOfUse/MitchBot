from __future__ import annotations
import asyncio
from io import BytesIO
from datetime import time, datetime, timedelta, timezone
import inspect
import random
import traceback
from typing import Callable, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from MitchBot import MitchClient

import discord
from zoneinfo import ZoneInfo

from responders import MessageResponder

from puzzle import Puzzle
from db.queries import get_random_city_timezone, get_random_poem
from render import PuzzleRenderer


def andify(things: list):
    """Helper function to put commas and spaces between the items in a list of things
    with appropriate placement of the word "and." 
    """
    if len(things) < 1:
        return ""
    return (f'{", ".join(things[:-1])}' +
            f'{", and " if len(things) > 2 else (" and " if len(things) > 1 else "")}' +
            f'{things[-1]}')


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
    day occurs."""
    now = datetime.now(tz=timezone.utc).astimezone(time_of_day.tzinfo)
    if now.time() >= time_of_day:
        next_puzzle_day = now.date()+timedelta(days=1)
    else:
        next_puzzle_day = now.date()
    next_puzzle_time = datetime.combine(next_puzzle_day, time_of_day).astimezone(time_of_day.tzinfo)
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
    et = ZoneInfo("America/New_York")
    fetch_new_puzzle_at = time(hour=6, minute=50, tzinfo=et)
    post_new_puzzle_at = time(hour=7, tzinfo=ZoneInfo("America/New_York"))
    if client.user.display_name != "MitchBotTest":
        puzzle_channel_id = 814334169299157001  # production
        quick_render = False
    else:
        puzzle_channel_id = 888301952067325952  # test
        if False:
            # in case we want to test puzzle posting directly
            fetch_new_puzzle_at = (datetime.now(tz=et)+timedelta(seconds=10)).time()
            post_new_puzzle_at = (datetime.now(tz=et)+timedelta(seconds=20)).time()
            quick_render = True

    current_puzzle: Optional[Puzzle] = None

    async def maintain_last_posted_puzzle():
        nonlocal current_puzzle
        current_puzzle = Puzzle.retrieve_last_saved()
        if current_puzzle is not None:
            print("retrieved current puzzle from database")
            current_puzzle.persist()
            try:
                if current_puzzle.message_id == -1:
                    raise ValueError("Puzzle from DB did not have message ID")
                puzzle_channel = client.get_channel(puzzle_channel_id)
                await puzzle_channel.fetch_message(current_puzzle.message_id)
                print("the previous puzzle status post is accessible")
            except:
                print("could not retrieve previous puzzle status post")
                traceback.print_exc()
        else:
            print("could not retrieve current puzzle from database")

    asyncio.create_task(maintain_last_posted_puzzle())

    async def send_new_puzzle():
        nonlocal current_puzzle
        channel = client.get_channel(puzzle_channel_id)
        previous_puzzle = current_puzzle
        current_puzzle = await Puzzle.fetch_from_nyt()
        current_puzzle.persist()
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
            alt_words_sample = random.sample(alt_words, min(len(alt_words), 5))
            alt_words_string = (", ".join(alt_words_sample[:-1]) +
                                ", and "+alt_words_sample[-1]+". ")
            message_text += (
                " Words from Wiktionary that should count today that " +
                "the NYT fails to acknowledge include: " + alt_words_string)
        if previous_puzzle is not None:
            previous_words = previous_puzzle.get_unguessed_words()
            if len(previous_words) > 1:
                message_text += (
                    "The least common word that no one got for yesterday's "
                    + f"puzzle was \"{previous_words[0]};\" "
                    + f"the most common word was \"{previous_words[-1]}.\""
                )
        # takes between 0 and 5 minutes, depending on the renderer
        puzzle_image = await current_puzzle.render(
            PuzzleRenderer.available_renderers[0] if quick_render else None
        )
        puzzle_filename = "puzzle" + (".png" if puzzle_image[0:4] == b"\x89PNG" else ".gif")
        seconds_to_wait = get_seconds_before_next(post_new_puzzle_at)
        # sanity check to try to make sure that, if rendering the image took so
        # long that it's already a little bit after post_new_puzzle_at, we don't
        # wait until the next day
        if seconds_to_wait < 60*60:
            print(f"rendered puzzle; waiting {seconds_to_wait} seconds to post")
            await asyncio.sleep(seconds_to_wait)
        await channel.send(
            content=message_text,
            file=discord.File(BytesIO(puzzle_image), puzzle_filename))
        status_message = await channel.send(content="Words found by you guys so far: None~")
        current_puzzle.associate_with_message(status_message)

    asyncio.create_task(repeatedly_schedule_task_for(fetch_new_puzzle_at, send_new_puzzle))

    # kind of a cheat to have these next two things in scheduler.py. but.
    async def respond_to_guesses(message: discord.Message):
        if current_puzzle is not None:
            already_found = len(current_puzzle.gotten_words)
            reactions = current_puzzle.respond_to_guesses(message)
            for reaction in reactions:
                await message.add_reaction(reaction)
            if len(current_puzzle.gotten_words) == already_found:
                return
            try:
                puzzle_channel = client.get_channel(puzzle_channel_id)
                assert puzzle_channel is not None, "could not retrieve channel that puzzles are sent in"
                status_message: discord.Message = (
                    await puzzle_channel.fetch_message(current_puzzle.message_id)
                )
                found_words = sorted(list(current_puzzle.gotten_words-current_puzzle.pangrams))
                status_text = 'Words found by you guys so far: '
                status_text += (
                    f'||{andify(found_words)}.|| '
                )
                found_pangrams = sorted(
                    list(
                        current_puzzle.gotten_words.intersection(
                            current_puzzle.pangrams)))
                if len(found_pangrams) > 0:
                    status_text += f"Pangrams: ||{andify(found_pangrams)}.|| "
                status_text += f' ({current_puzzle.percentage_complete}% complete'
                if current_puzzle.percentage_complete == 100:
                    status_text += " 🎉)"
                else:
                    status_text += ")"
                await status_message.edit(content=status_text)

            except:
                print("could not retrieve Discord message to update puzzle status !!!")
                traceback.print_exc()

    client.register_responder(MessageResponder(
        lambda m: m.channel.id == puzzle_channel_id, respond_to_guesses))

    @client.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        if before.author.id == client.user.id:
            return
        if after.channel.id == puzzle_channel_id:
            if before.content != after.content:
                # remove old reactions
                for reaction in after.reactions:
                    if reaction.me:
                        await reaction.remove(client)
                # replace with new ones
                await respond_to_guesses(after)

    # poetry scheduling:

    async def send_poem():
        poetry_channel_id = 678337807764422691  # production
        # poetry_channel_id = 888301952067325952  # test
        a_city, a_zone = get_random_city_timezone()
        a_time = datetime.now().astimezone(ZoneInfo(a_zone))
        a_body = random.choice(
            ["Mercury", "Venus", "Mars", "Earth", "Jupiter", "Saturn", "Neptune", "Pluto",
             "Cassiopeia", "Ceres", "Charon", "Ganymede", "The ISS", "Alpha Centauri",
             "The Sombrero Galaxy", "The Tadpole Galaxy", "Hoag's Object"])
        a_state = random.choice(
            ["retrograde", "intrograde", "prograde", "astrograde", "interrograde", "terragrade",
             "peltagrade", "fluxigrade", "axigrade", "centigrade", "tardigrade", "upgrade",
             "degrade", "orthograde", "fermigrade"])
        prelude = ("Good evening. " +
                   f"It's {int(a_time.strftime('%I'))}:{a_time.strftime('%M %p')} " +
                   f"in {a_city}. {a_body} is in {a_state}. Tonight's prediction is:")
        await client.get_channel(poetry_channel_id).send(prelude)
        poem = "\n".join("> "+x for x in get_random_poem().split("\n"))
        await client.get_channel(poetry_channel_id).send(poem)
    poem_time = time(hour=2, tzinfo=ZoneInfo("America/New_York"))
    # poem_time = (datetime.now(tz=timezone.utc)+timedelta(seconds=15)
    #              ).time().replace(tzinfo=timezone.utc)  # test
    asyncio.create_task(repeatedly_schedule_task_for(poem_time, send_poem))


async def test():
    pass

if __name__ == "__main__":
    asyncio.run(test())
