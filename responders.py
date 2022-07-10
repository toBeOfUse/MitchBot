from __future__ import annotations
import asyncio
import datetime
import inspect
from io import BytesIO
import random
import re
import traceback

import disnake as discord
from disnake.interactions import ApplicationCommandInteraction
from disnake.ext.commands import Param
from PIL import Image

from typing import TYPE_CHECKING, Union, Callable
if TYPE_CHECKING:
    from MitchBot import MitchBot
    from asyncio.futures import Future

from db.queries import get_random_nickname, get_random_strategy


class MessageResponder():
    '''
    Stores a condition and a function to call if asked to react to a message that
    meets that condition.
    '''

    def __init__(
        self,
        condition: Union[str, list[str],
                         Callable[[discord.Message], bool]],
        responder: Union[Callable[[discord.Message], None],
                         Callable[[discord.Message], Future]],
            require_mention: bool = False):
        '''
        Args:
            condition: either a string or list of strings that can be used as a
            regular expression to search the message contents case-insensitively
            or a function that returns true or false depending on whether the
            MessageResponder should respond.
            responder: a function that is called with the message that we are
            potentially going to respond to. this can be a normal function that
            potentially returns a future or an async function.
        '''
        self.condition = condition
        self.responder = responder
        self.require_mention = require_mention

    @staticmethod
    def mentions_bot(message: discord.Message):
        return not message.mention_everyone and (
            message.guild.me.mentioned_in(message)
            or len(set(message.guild.me.roles).intersection(message.role_mentions)) > 0)

    def react_to(self, message: discord.Message):
        '''
        Reacts to messages by executing a function if the certain condition is
        fulfilled. Returns True if it called the function.
        '''
        if message.author.bot:
            return False
        match = False
        if self.require_mention and not MessageResponder.mentions_bot(message):
            return False
        if isinstance(self.condition, str):
            if re.search(self.condition, message.content, re.IGNORECASE):
                match = True
        elif isinstance(self.condition, list):
            for regex in self.condition:
                if re.search(regex, message.content, re.IGNORECASE):
                    match = True
                    break
        elif inspect.isfunction(self.condition) and self.condition(message):
            match = True
        if match:
            if inspect.iscoroutinefunction(self.responder):
                asyncio.create_task(self.responder(message))
            else:
                potential_future = self.responder(message)
                if potential_future is not None:
                    asyncio.create_task(potential_future)
        return match


def add_responses(bot: MitchBot):
    bot.register_responder(
        MessageResponder(
            [r"\bbot\b", "mitchbot", "robot"],
            lambda m: m.add_reaction('🤖')))
    bot.register_responder(
        MessageResponder(
            r"magic (8|eight) ball",
            lambda m: m.reply("Magic 8-ball sez: \""+random.choice([
                "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.",
                "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.",
                "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
                "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
                "Don't count on it.", "My reply is no.", "My sources say no.",
                "Outlook not so good.", "Very doubtful."])+'"')
        )
    )
    bot.register_responder(
        MessageResponder(
            r"\bgood(\s|-)?night\b",
            lambda m: m.channel.send("🛏️💖")
        )
    )
    bot.register_responder(
        MessageResponder(
            r"\bflip\b.*\bcoin\b",
            lambda m: m.reply(
                "\U0001FA99 " + random.choice(["Heads", "Tails"]))  # coin emoji
        )
    )

    async def fuck_response(message):
        fuck = await message.channel.send("Fuck you 🤬")
        await asyncio.sleep(3)
        await fuck.edit(content='Love you guys')
    bot.register_responder(
        MessageResponder(
            r"fuck (you|u)",
            fuck_response
        )
    )

    async def _fight(fighters: list[discord.User]) -> BytesIO:
        i1 = await bot.get_avatar_small(fighters[0], 180)
        i2 = await bot.get_avatar_small(fighters[1], 180)
        bg = Image.open('images/fight.png')
        blank = Image.new("RGBA", (640, 200), 0)
        mask = Image.open('images/mask.png')
        blank.paste(i1, (10, 10))
        blank.paste(i2, (640-10-180, 10))
        bg.paste(blank, (0, 0), mask)
        image_bytes = BytesIO()
        bg.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        return image_bytes
    
    def _fight_alt_text(fighters: list[discord.User]) -> str:
        return f"{fighters[0].name} and {fighters[1].name} with crossed swords between them"

    async def message_fight(message: discord.Message):
        if len(
                message.mentions) == 2 or (
                len(message.mentions) == 3 and bot.user.mentioned_in(message)):
            async with message.channel.typing():
                if len(message.mentions) == 2:
                    fighters = message.mentions
                else:
                    fighters = [user for user in message.mentions if bot.user != user]
                await message.channel.send(
                    file=discord.File(
                        fp=await _fight(fighters),
                        filename="fight.png",
                        description=_fight_alt_text(fighters)
                    )
                )

    bot.register_responder(MessageResponder(r"\bmake\b.*\bfight\b", message_fight))

    @bot.slash_command(description="Self explanatory")
    async def start_fight(
            ctx: ApplicationCommandInteraction,
            fighter1: discord.Member,
            fighter2: discord.Member):
        await ctx.response.send_message(
            file=discord.File(
                fp=await _fight([fighter1, fighter2]),
                filename="fight.png",
                description=_fight_alt_text([fighter1, fighter2])
            )
        )

    async def _kiss(recipient: discord.User):
        avatar = await bot.get_avatar_small(recipient, 200)
        blank = Image.new('RGBA', (200, 200), 0)
        mask = Image.open("images/mask_rect.png")
        blank.paste(avatar, (0, 0), mask)
        smooch = Image.open("images/kiss.png")
        final = Image.alpha_composite(blank, smooch)
        image_bytes = BytesIO()
        final.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        return image_bytes
    
    def _kiss_alt_text(recipient: discord.User) -> str:
        return f"{recipient.name}'s avatar with lipstick marks on it"

    async def message_kiss(message: discord.Message):
        async with message.channel.typing():
            await message.reply(
                file=discord.File(
                    fp=await _kiss(message.author),
                    filename='kiss.png',
                    description=_kiss_alt_text(message.author)
                )
            )
    bot.register_responder(MessageResponder("kiss", message_kiss, require_mention=True))

    @bot.slash_command(description="kis 🥺")
    async def kiss(ctx: ApplicationCommandInteraction):
        await ctx.response.send_message(
            file=discord.File(
                fp=await _kiss(ctx.user),
                filename='kiss.png',
                description=_kiss_alt_text(ctx.user)
            )
        )

    async def day_of_week(message: discord.Message):
        now = datetime.date.today()
        days = ["Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"]
        wrong_days = days[0:now.weekday()] + days[now.weekday()+1:]
        random.shuffle(wrong_days)
        message = await message.reply("um " + wrong_days[0])
        await asyncio.sleep(0.5)
        for d in wrong_days[1:] + ["um", "oh god uh", "\*sweats*"]:
            await message.edit(content=d)
            await asyncio.sleep(0.5)
        await message.edit(content=days[now.weekday()])
    bot.register_responder(MessageResponder(r"\bwhat\b.*\bday\b|\bday of the week\b", day_of_week))

    def nicknames_by_count(count: int):
        nicknames = [get_random_nickname() for _ in range(0, count)]
        return (
            "Hello, " + (
                ", ".join(nicknames[:-1])+", and/or " if count > 1 else ""
            )+nicknames[-1]+".")

    async def nickname(message: discord.Message):
        if "nicknames" in message.content.lower():
            count = 5 * message.content.lower().count("nicknames")
            await message.reply(nicknames_by_count(count))
        else:
            mess = "Hello, ✨" + get_random_nickname()+"✨"
            await message.reply(mess)
    bot.register_responder(MessageResponder(r"nicknames?", nickname, require_mention=True))

    nickname_param = Param(default=5, ge=1, le=25, description="how many" )

    @bot.slash_command(description='https://www.findnicknames.com/cool-nicknames/')
    async def obtain_nicknames(
        ctx: ApplicationCommandInteraction,
        count: int = nickname_param):
        await ctx.response.send_message(nicknames_by_count(count))
    
    @bot.slash_command(description="the response will be private so feel free to spam")
    async def quietly_obtain_nicknames(
        ctx: ApplicationCommandInteraction,
        count: int=nickname_param
    ):
      await ctx.response.send_message(nicknames_by_count(count), ephemeral=True)

    async def _process_emoji(emoji_image: discord.Attachment):
        emoji_file = BytesIO()
        await emoji_image.save(emoji_file, seek_begin=True)
        # resize image so that the largest dimension is 128 pixels to help with
        # file size
        emoji_image = Image.open(emoji_file, formats=["jpeg", "png", "gif"])
        largest_dimension = max(emoji_image.width, emoji_image.height)
        scale_factor = 128/largest_dimension
        emoji_image = emoji_image.resize(
            (round(emoji_image.width * scale_factor), round(emoji_image.height * scale_factor)),
            resample=Image.LANCZOS)
        resized_file = BytesIO()
        emoji_image.save(resized_file, format="png")
        resized_file.seek(0)
        resized_file = resized_file.read()
        return resized_file
    
    async def add_emoji_message(message: discord.Message):
        emoji_name_match = re.search("make (.*) emoji", message.content)
        if (emoji_name_match and
            len(emoji_name_match.group(1).strip()) and
                len(message.attachments) > 0):
            emoji_name = emoji_name_match.group(1).strip().strip('"\'')
            emoji_file = await _process_emoji(message.attachments[0])
            try:
                created_emoji = await message.guild.create_custom_emoji(name=emoji_name, image=emoji_file)
                await message.channel.send("Done "+str(created_emoji))
            except Exception as e:
                print(e)
                traceback.print_exc()
                await message.channel.send(
                    "I couldn't :( the file was possibly too big or Discord is"
                    " just fucking up"
                )
        else:
            await message.channel.send(
                "To make emoji, send something like \"make great_auk emoji\" "
                "and attach an image file with it"
            )

    bot.register_responder(
        MessageResponder(
            "make .* emoji",
            add_emoji_message,
            require_mention=True
        )
    )

    @bot.slash_command(description="add a fun emoji")
    async def add_emoji(
        ctx: ApplicationCommandInteraction,
        file: discord.Attachment,
        name: str,
    ):
        emoji_file = await _process_emoji(file)
        if not (2 <= len(name) <= 32):
            await ctx.response.send_message(
                "emoji names must be between 2 and 32 characters long",
                ephemeral=True
            )
        else:
            try:
                created_emoji = await ctx.guild.create_custom_emoji(
                    name=name, image=emoji_file
                )
                await ctx.response.send_message(str(created_emoji))
            except Exception as e:
                print(e)
                traceback.print_exc()
                await ctx.response.send_message(
                    "I couldn't :( the file was possibly too big or Discord is "
                    "just fucking up"
                )


    with open("text/untamed.txt") as untamed_words_file:
        untamed_word_list = untamed_words_file.read()
        untamed_words = [
            r"\b"+x.strip('"')+r"\b"
            for x in re.findall(r"(?:\"[^\"]+?\")|(?:\b(?:\w|-)+?\b)", untamed_word_list)]

    async def react_negatively(message: discord.Message):
        await message.add_reaction(random.choice(["🚫", "❌", "🛑", "🙅", "👎"]))

    bot.register_responder(MessageResponder(untamed_words, react_negatively))

    @bot.slash_command(description="Puzzle hints or life advice, depending on the channel")
    async def obtain_hint(context: ApplicationCommandInteraction):
        if context.channel_id in bot.hint_functions:
            await bot.hint_functions[context.channel_id](context)
        else:
            await context.response.send_message(get_random_strategy())
    
    @bot.slash_command(description="am helpful")
    async def convert_100_miles_to_kilometers(context: ApplicationCommandInteraction
        ):
        await context.response.send_message("100 miles is 160.9344 kilometers.")
