# python libraries
from __future__ import annotations
import math
from io import BytesIO
import random
from typing import TYPE_CHECKING, Callable, Union, Coroutine

# external package dependencies
import disnake as discord
from PIL import Image
from disnake.interactions import ApplicationCommandInteraction
from disnake.ext import commands

# project files
from responders import add_responses, MessageResponder
from scheduler import schedule_tasks
from spellingbee import add_bee_functionality
# from letterboxed import add_letterboxed_functionality


class MitchBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents, prefix="")
        # set in on_ready:
        self.responses: list[MessageResponder] = []
        self.initialized = False
        self.test_mode: Union[bool, str] = "unknown"
        self.command_guild_ids: list[int] = []
        # maps channel ids to hint functions triggered by the obtain_hint slash
        # command
        self.hint_functions: dict[int, Coroutine[ApplicationCommandInteraction]] = {}

    def register_hint(self, channel_id: int, function: Coroutine[ApplicationCommandInteraction]):
        self.hint_functions[channel_id] = function

    @classmethod
    async def get_avatar_small(cls, user: discord.User, final_size: int):
        ceil_size = 2**(math.ceil(math.log(final_size, 2)))
        ceil_size_avatar = user.display_avatar.replace(size=ceil_size, format="png")
        return Image.open(
            BytesIO(await ceil_size_avatar.read())
        ).resize(
            (final_size, final_size), Image.LANCZOS
        )

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        for guild in self.guilds:
            await guild.me.edit(nick="Servers Georg")
        self.test_mode = self.user.name == "MitchBotTest"
        self.command_guild_ids = (
            [708955889276551198] if self.test_mode else [678337806510063626]
        )

        if not self.initialized:
            add_responses(self)
            schedule_tasks(self)
            add_bee_functionality(self)
            # add_letterboxed_functionality(self)
            self.initialized = True

    def slash_command(self, *args, **kwargs):
        return super().slash_command(*args, **kwargs, guild_ids=self.command_guild_ids)

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

        if not responded and MessageResponder.mentions_bot(message):
            response = random.choice(
                ["Completely correct", "I'm afraid not", "I'm not too sure",
                 "No-one has said that before", "Only on Tuesdays",
                 "Seize the means of production"])
            await message.reply(response + ", "+message.author.display_name+".")

    async def on_disconnect(self):
        print("disconnected :(")
