# python libraries
import asyncio
import inspect
import math
import re
import subprocess
import time
from io import BytesIO
import random

# external package dependencies
import discord
from PIL import Image


class ReactiveDict(dict):
    '''
    a dict that accepts listener functions/coroutines to call when the value
    corresponding to a specified key is updated
    '''

    def __init__(self):
        super().__init__()
        self.listeners = []

    def add_listener(self, f):
        self.listeners.append(f)

    def remove_listener(self, f):
        self.listeners.remove(f)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.listeners:
            [asyncio.create_task(x(key, value)) if inspect.iscoroutinefunction(x)
             else x(key, value) for x in self.listeners]


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
        Reacts to messages by executing a function if the certain condition is fulfilled.
        '''
        if message.author.bot:
            return
        match = False
        if self.require_mention:
            if (not message.guild.me.mentioned_in(message)) or message.mention_everyone:
                return
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


class MitchClient(discord.Client):
    def __init__(self):
        super().__init__()
        self.vc = None
        # self.voice = speaker.VoiceHaver()
        self.started_playing = -1
        self.public_state = ReactiveDict()
        self.public_state['text_channels'] = []
        self.public_state['voice_channels'] = []
        self.public_state['prompts'] = self.get_prompts()
        self.public_state['currently_playing'] = ""
        # self.public_state['current_voice'] = self.voice.current_voice()
        self.responses: list[MessageResponder] = []

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
        # for g in self.guilds:
        #     for vc in g.voice_channels:
        #         if self.user in vc.members:
        #             self.vc = await vc.connect()
        #             vc_connected = True
        #             break
        #     if vc_connected:
        #         break
        self.public_state['text_channels'] = self.get_text_channels()
        self.public_state['voice_channels'] = self.get_voice_channels()

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
                ["completely correct", "i'm afraid not", "i'm not too sure",
                 "ik spreek geen engels", "only on tuesdays", "seize the means of production"])
            await message.reply(response + ", "+message.author.display_name+".")

    async def on_disconnect(self):
        if self.vc:
            await self.vc.disconnect()
            self.vc = None
            self.public_state['voice_channels'] = self.get_voice_channels()

    # public interface for remote control voice and text chat control:

    def get_prompts(self):
        prompts = open('text/prompts.txt', 'r')
        text = prompts.read()
        groups = re.split(r"\n+", text)
        prompts.close()
        return [x.split('-') for x in groups]

    def set_prompts(self, prompts):
        prompts_string = '\n\n'.join([z.strip()
                                      for z in
                                      [' - '.join([y.strip() for y in x]) for x in prompts]])
        txt = open('text/prompts.txt', 'w')
        txt.write(prompts_string)
        txt.close()
        self.public_state['prompts'] = prompts

    async def start_playing(self, audio_file, name=None):
        if not name:
            name = audio_file
        if (not self.vc) or (not self.vc.is_connected()):
            print("audio request bounced; no vc connection available")
        else:
            args = ("ffprobe", "-show_entries", "format=duration", "-i", audio_file)
            popen = subprocess.Popen(args, stdout=subprocess.PIPE)
            popen.wait()
            output = str(popen.stdout.read(), 'utf-8')
            length = re.search(r"(.*?)\r\n", output.split('=')[1]).group(1)
            if self.vc.is_playing():
                self.interrupt_current_audio()
            source = await discord.FFmpegOpusAudio.from_probe(audio_file)
            self.vc.play(source)
            self.public_state['currently_playing'] = name
            start_time = time.time()
            self.started_playing = start_time
            await asyncio.sleep(float(length))
            if self.started_playing == start_time:
                self.public_state['currently_playing'] = ""

    async def say(self, text):
        pass
        # audio_name = self.voice.text_to_wav(text)
        # audio_file = os.path.join(os.getcwd(), "audio\\", audio_name)
        # await self.start_playing(audio_file, text)

    def change_voice(self):
        pass
        # self.voice.change_voice()
        # self.public_state['current_voice'] = self.voice.current_voice()

    def interrupt_current_audio(self):
        if self.vc and self.vc.is_playing():
            self.vc.stop()
            self.public_state['currently_playing'] = ""
            self.started_playing = -1

    async def connect_to_vc(self, channel_id):
        channel = self.get_channel(channel_id)
        if self.vc and self.vc.is_connected():
            if self.vc.channel is channel:
                await self.vc.disconnect()
                self.public_state['voice_channels'] = self.get_voice_channels()
                self.vc = None
                return
            else:
                await self.vc.disconnect()
        self.vc = await channel.connect()
        self.public_state['voice_channels'] = self.get_voice_channels()

    def get_voice_channels(self):
        vcs = []
        for guild in self.guilds:
            for channel in guild.voice_channels:
                # todo: check if we actually have permission to connect
                vcs.append([str(guild), str(channel), str(channel.id), bool(
                    self.vc and self.vc.is_connected() and self.vc.channel == channel)])
        return vcs

    def get_text_channels(self):
        tcs = []
        for guild in self.guilds:
            for channel in guild.text_channels:
                tcs.append([str(guild), str(channel), str(channel.id)])
        return tcs
