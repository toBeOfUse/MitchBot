from __future__ import annotations
import asyncio
from io import BytesIO
from typing import TYPE_CHECKING
import traceback
from datetime import datetime, time, timedelta
import random
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

import disnake as discord
from PIL import Image

from bee_engine import SpellingBee, SessionBee, BeeRenderer

from responders import MessageResponder
from grammar import andify
from scheduler import repeatedly_schedule_task_for
if TYPE_CHECKING:
    from MitchBot import MitchBot
    from disnake.interactions import ApplicationCommandInteraction
    
db_path = "./db/bee_engine.db"

async def fetch_new_puzzle(quick_render=False):
    print("fetching puzzle from NYT...")
    todays_puzzle = await SpellingBee.fetch_from_nyt()
    print("fetched. rendering graphic...")
    await todays_puzzle.render(
        "hexspin" if quick_render else ""
    )
    print("graphic rendered. saving today's puzzle in database")
    todays_puzzle.persist_to(db_path)


async def post_new_puzzle(channel: discord.TextChannel):
    todays_puzzle = SpellingBee.retrieve_saved("latest", "./db/bee_engine.db")
    message_text = random.choice(["Good morning",
                                  "Goedemorgen",
                                  "Bon matin",
                                  "Ohayō",
                                  "Back at it again at Krispy Kremes",
                                  "Hello",
                                  "Bleep Bloop",
                                  "Here is a puzzle",
                                  "Guten Morgen"])+" ✨"
    alt_words = todays_puzzle.get_wiktionary_alternative_answers()
    if len(alt_words) > 1:
        alt_words_sample = alt_words[:5]
        message_text += (
            " Words from Wiktionary that should count today that the NYT "
            f"fails to acknowledge include: {andify(alt_words_sample)}.")
    yesterdays_puzzle = SessionBee.retrieve_saved("primary", db_path)
    if yesterdays_puzzle is not None:
        previous_words = yesterdays_puzzle.get_unguessed_words()
        if len(previous_words) > 1:
            message_text += (
                " The least common word that no one got for yesterday's "
                f"puzzle was \"{previous_words[0]};\" "
                f"the most common word was \"{previous_words[-1]}.\""
            )
        elif len(previous_words) == 1:
            message_text += (
                " The only word no one got yesterday was \"" +
                previous_words[0] +
                ".\""
            )
    puzzle_filename = "puzzle."+todays_puzzle.image_file_type
    await channel.send(
        content=message_text,
        file=discord.File(
            BytesIO(todays_puzzle.image), 
            puzzle_filename, 
            description="A spelling bee puzzle with the center letter"
                f" {todays_puzzle.center} and surrounding letters"
                f" {andify(todays_puzzle.outside)}."
            )
        )
    status_message = await channel.send(content="Words found by you guys so far: None~")
    session = SessionBee(
        todays_puzzle, metadata={"status_message_id": status_message.id}
    )
    session.persist_to(db_path)
    session.make_primary_session()


async def respond_to_guesses(message: discord.Message):
    current_puzzle = SessionBee.retrieve_saved("primary", db_path)
    if current_puzzle is None:
        return
    current_puzzle.persist_to(db_path)
    already_found = len(current_puzzle.gotten_words)
    reactions = current_puzzle.respond_to_guesses(message.content)
    for reaction in reactions:
        await message.add_reaction(reaction)
    if len(current_puzzle.gotten_words) == already_found:
        return
    try:
        puzzle_channel = message.channel
        status_message: discord.Message = (
            await puzzle_channel.fetch_message(
                current_puzzle.metadata["status_message_id"]
            )
        )
        status_text = 'Words found by you guys so far: '
        status_text += current_puzzle.list_gotten_words(separate_pangrams=True, enclose_with=["||", "||"])
        status_text += f' ({round(current_puzzle.percentage_words_gotten(), 1)}% complete'
        if current_puzzle.percentage_words_gotten() == 100:
            status_text += " 🎉)"
        else:
            status_text += ")"
        await status_message.edit(content=status_text)

    except:
        print("could not retrieve Discord message and update puzzle status !!!")
        traceback.print_exc()


def add_bee_functionality(bot: MitchBot):
    try:
        current_puzzle = SessionBee.retrieve_saved("primary", db_path)
        assert current_puzzle is not None
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
        if False:
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
                        await reaction.remove(bot.user)
                # replace with new ones
                await respond_to_guesses(after)

    async def obtain_hint(ctx: ApplicationCommandInteraction):
        await ctx.response.send_message(
            SessionBee
                .retrieve_saved("primary", db_path)
                .get_unguessed_hints()
                .format_all_for_discord()
        )

    bot.register_hint(puzzle_channel_id, obtain_hint)

    async def monitor_website():
        while True:
            try:
                await SpellingBee.fetch_from_nyt()
                print("spelling bee website appears as expected")
            except HTTPError:
                print("nyt website appears to be down")
                puzzle_channel = bot.get_channel(puzzle_channel_id)
                await puzzle_channel.send(
                    "Warning⚠️: The NYT Spelling Bee site appears to have gone "
                    "down or to have been moved as of now, "
                    "which might waylay upcoming puzzle posts.")
            except AssertionError:
                print("nyt website appears to have changed")
                puzzle_channel = bot.get_channel(puzzle_channel_id)
                await puzzle_channel.send(
                    "Warning⚠️: The NYT Spelling Bee site's code appears to have changed "
                    "to-day, which might waylay upcoming puzzle posts.")
            await asyncio.sleep(60*60*6)
    asyncio.create_task(monitor_website())


async def test():
    saved_puzzle = SpellingBee.retrieve_saved()
    if saved_puzzle is None:
        print("fetching puzzle from nyt")
        puzzle = await SpellingBee.fetch_from_nyt()
    else:
        puzzle = saved_puzzle
    print("today's words from least to most common:")
    print(puzzle.get_unguessed_words(set()))
    # answers = iter(puzzle.answers)
    # puzzle.guess(next(answers))
    print("words that the nyt doesn't want us to know about:")
    print(random.sample(puzzle.get_wiktionary_alternative_answers(), 5))
    puzzle.persist_to(db_path)

    print("Hints table:")
    table = puzzle.get_unguessed_hints(set())
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
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("Received SIGINT, exiting")
