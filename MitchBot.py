# python libraries
from __future__ import annotations
import math
from io import BytesIO
import random
from typing import TYPE_CHECKING

# external package dependencies
import discord
from PIL import Image

# project files
from responders import add_responses
from scheduler import schedule_tasks
if TYPE_CHECKING:
    from responders import MessageResponder


class MitchClient(discord.Bot):
    def __init__(self):
        super().__init__()
        self.responses: list[MessageResponder] = []
        self.initialized = False

    @classmethod
    async def get_avatar_small(cls, user, final_size):
        req_size = 2**(math.ceil(math.log(final_size, 2)))
        return Image\
            .open(BytesIO(await user.avatar_url_as(format="jpg", size=req_size).read())) \
            .resize((final_size, final_size), Image.LANCZOS)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        for guild in self.guilds:
            await guild.me.edit(nick="MitchBot")
        if not self.initialized:
            add_responses(self)
            schedule_tasks(self)
            self.initialized = True

    def register_responder(self, responder: MessageResponder):
        self.responses.append(responder)

    async def on_message(self, message: discord.Message):
        print(f'Message from {message.author}: {message.content}')
        if message.author == self.user:
            return

        responded = False
        for response in self.responses:
            if response.react_to(message):
                responded = True

        if not responded and self.user.mentioned_in(message) and not message.mention_everyone:
            response = random.choice(
                ["Completely correct", "I'm afraid not", "I'm not too sure",
                 "No-one has said that before", "Only on Tuesdays",
                 "Seize the means of production"])
            await message.reply(response + ", "+message.author.display_name+".")

    async def on_disconnect(self):
        print("disconnected :(")
