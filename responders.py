import asyncio
import datetime
from io import BytesIO
import random

import discord
from PIL import Image

from MitchBot import MitchClient, MessageResponder
import textresources


def add_responses(bot: MitchClient):
    bot.register_responder(
        MessageResponder(
            [r"\bbot\b", "mitchbot", "robot"],
            lambda m: m.add_reaction('🤖')))
    bot.register_responder(
        MessageResponder(
            r"magic (8|eight) ball",
            lambda m: m.reply("magic 8 ball sez: \""+random.choice([
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
                "\U0001FA99 " + random.choice(["heads", "tails"]))  # coin emoji
        )
    )

    async def fuck_response(message):
        fuck = await message.channel.send("fuck you 🤬")
        await asyncio.sleep(3)
        await fuck.edit(content='love you guys')
    bot.register_responder(
        MessageResponder(
            "fuck (you|u)",
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
        elif len(message.mentions) == 1:
            await message.channel.send('it takes two to tango')
        else:
            await message.channel.send('too many people...')
    bot.register_responder(MessageResponder("make.*fight", fight))

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
        message = await message.channel.send("um " + wrong_days[0])
        await asyncio.sleep(0.5)
        for d in wrong_days[1:] + ["um", "oh god uh", "\*sweats*"]:
            await message.edit(content=d)
            await asyncio.sleep(0.5)
        await message.edit(content=days[now.weekday()])
    bot.register_responder(MessageResponder("what.*day", day_of_week))

    async def nickname(message: discord.Message):
        mess = "hello, ✨" + random.choice(textresources.nicknames)+"✨"
        await message.reply(mess)
    bot.register_responder(MessageResponder("nickname", nickname, require_mention=True))
