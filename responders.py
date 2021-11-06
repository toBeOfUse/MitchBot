from __future__ import annotations
import asyncio
import datetime
import inspect
from io import BytesIO
import random
import re

import discord
from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from MitchBot import MitchClient
from db.queries import get_random_nickname


class MessageResponder():
    '''
    Stores a condition and a function to call if asked to react to a message that
    meets that condition.
    '''

    def __init__(self, condition, responder, require_mention=False):
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

    def react_to(self, message: discord.Message):
        '''
        Reacts to messages by executing a function if the certain condition is
        fulfilled. Returns True if it called the function.
        '''
        if message.author.bot:
            return False
        match = False
        if self.require_mention:
            if (not message.guild.me.mentioned_in(message)) or message.mention_everyone:
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


def add_responses(bot: MitchClient):
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

    async def fight(message: discord.Message):
        if len(
                message.mentions) == 2 or (
                len(message.mentions) == 3 and bot.user.mentioned_in(message)):
            async with message.channel.typing():
                if len(message.mentions) == 2:
                    fighters = message.mentions
                else:
                    fighters = [user for user in message.mentions if bot.user != user]
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
                await message.channel.send(file=discord.File(fp=image_bytes, filename='fight.png'))
    bot.register_responder(MessageResponder(r"\bmake\b.*\bfight\b", fight))

    async def kiss(message: discord.Message):
        async with message.channel.typing():
            recipient = message.author
            avatar = await bot.get_avatar_small(recipient, 200)
            blank = Image.new('RGBA', (200, 200), 0)
            mask = Image.open("images/mask_rect.png")
            blank.paste(avatar, (0, 0), mask)
            smooch = Image.open("images/kiss.png")
            final = Image.alpha_composite(blank, smooch)
            image_bytes = BytesIO()
            final.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            await message.reply(file=discord.File(fp=image_bytes, filename='kiss.png'))
    bot.register_responder(MessageResponder("kiss", kiss, require_mention=True))

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

    async def nickname(message: discord.Message):
        if "nicknames" in message.content.lower():
            nicknames = [
                get_random_nickname() for _ in range(
                    0, 5 * message.content.lower().count("nicknames"))
            ]
            mess = "Hello, " + ", ".join(nicknames[:-1])+", and/or "+nicknames[-1]
            await message.reply(mess)
        else:
            mess = "Hello, ✨" + get_random_nickname()+"✨"
            await message.reply(mess)
    bot.register_responder(MessageResponder(r"nicknames?", nickname, require_mention=True))

    async def add_emoji(message: discord.Message):
        emoji_name_match = re.search("make (.*) emoji", message.content)
        if (emoji_name_match and
            len(emoji_name_match.group(1).strip()) and
                len(message.attachments) > 0):
            emoji_name = emoji_name_match.group(1).strip()
            emoji_file = BytesIO()
            await message.attachments[0].save(emoji_file, seek_begin=True)
            emoji_file = emoji_file.read()
            try:
                created_emoji = await message.guild.create_custom_emoji(name=emoji_name, image=emoji_file)
                await message.channel.send("Done "+str(created_emoji))
            except:
                await message.channel.send("I couldn't :( the file was possibly too big or Discord is just fucking up")
        else:
            await message.channel.send("To make emoji, send something like \"make great_auk emoji\" and attach an image file with it")
    bot.register_responder(MessageResponder("make .* emoji", add_emoji, require_mention=True))
