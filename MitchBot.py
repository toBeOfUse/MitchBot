# python libraries
import asyncio
import datetime
import inspect
import math
import os
import random
import re
import subprocess
import time
import traceback
import urllib
from io import BytesIO

# package dependencies
import discord
import tornado.httpclient
from PIL import Image

# project files
import speaker
import textresources

http_client = tornado.httpclient.AsyncHTTPClient()


# class for a dict that accepts listener functions/coroutines and calls them when with a key and a value when it updates
class ReactiveDict(dict):
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
            [asyncio.create_task(x(key, value)) if inspect.iscoroutinefunction(x) else x(key, value) for x in
             self.listeners]


class MitchClient(discord.Client):
    def __init__(self):
        super().__init__()
        self.vc = None
        self.voice = speaker.VoiceHaver()
        self.started_playing = -1
        self.tombot_mocked = False
        self.public_state = ReactiveDict()
        self.public_state['text_channels'] = []
        self.public_state['voice_channels'] = []
        self.public_state['prompts'] = []
        self.public_state['currently_playing'] = ""
        self.public_state['current_voice'] = self.voice.current_voice()

    @classmethod
    async def get_avatar_small(cls, user, final_size):
        req_size = 2**(math.ceil(math.log(final_size, 2)))
        return Image\
            .open(BytesIO(await user.avatar_url_as(format="jpg", size=req_size).read())) \
            .resize((final_size, final_size), Image.LANCZOS)

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        vc_connected = False
        nym_g = discord.utils.find(lambda g: "tanya" in g.name, self.guilds)
        self_member = discord.utils.find(lambda m: m == self.user, nym_g.members)
        await self_member.edit(nick="#758: \"Heart’s Desire\"")
        for g in self.guilds:
            for vc in g.voice_channels:
                if self.user in vc.members:
                    self.vc = await vc.connect()
                    vc_connected = True
                    break
            if vc_connected:
                break
        self.public_state['text_channels'] = self.get_text_channels()
        self.public_state['voice_channels'] = self.get_voice_channels()
        prompts = open('prompts.txt', 'r')
        text = prompts.read()
        groups = text.split('\n')
        prompts.close()
        self.public_state['prompts'] = [x.split('-') for x in groups]

    # todo: make this less than 10 billion lines long
    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        if message.author == self.user:
            return
        text = message.content.lower()

        if False and message.author.id == 191291201805090817:  # nym, whose mic setup don't work
            await self.say(message.content)

        # casual responses
        if re.search(r"\bbot\b", text) or "mitchbot" in text or "robot" in text:
            await message.add_reaction('🤖')
        elif "magic" in text and ("8" in text or "eight" in text) and "ball" in text:
            responses = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.",
                         "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.",
                         "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
                         "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
                         "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.",
                         "Very doubtful."]
            response = random.choice(responses)
            await message.channel.send('magic 8 ball sez: "' + response+'"')
        elif "horse" in text:
            site_to_send = random.choice(["http://nice.horse", "http://endless.horse"])
            await message.channel.send(site_to_send, file=discord.File(fp="images/horse.jpg"))
        elif re.search(r"\bgood\s?night\b", text):
            await message.channel.send("🛏️💖")
        elif "fuck you" in text:
            fuck = await message.channel.send("fuck you 🤬")
            await asyncio.sleep(3)
            await fuck.edit(content='love you guys')
        elif hmm_match := re.search(r"\bhm(m*)\b", text):
            if not message.author.bot:
                await message.channel.send(next(textresources.poetry_generator))
            else:  # anti-tombot measures
                if not self.tombot_mocked:
                    hmm_length = len(hmm_match.group(0))
                    hmm_string = 'h' + ''.join(['‍m' for _ in range(hmm_length-1)]) + '~'  # zero-width space
                    await message.channel.send('[tombot voice] '+hmm_string)
                    self.tombot_mocked = True
                    await asyncio.sleep(10)
                    self.tombot_mocked = False
                else:
                    await message.delete()
        elif "flip" in text and "coin" in text:
            await message.channel.send(random.choice(['heads', 'tails']))

        # @ mention commands
        users_mentioned_by_role = []
        for role in message.role_mentions:
            for user in role.members:
                users_mentioned_by_role.append(user)
        if self.user in message.mentions or self.user in users_mentioned_by_role:
            other_mentions = [x for x in message.mentions if x != self.user]
            if "fake link" in text and len(other_mentions) == 0:
                async with message.channel.typing():
                    searchpart = text[re.search(r"fake link", text).end():]
                    title = re.search(r"['\"“”‘’„](.*?)['\"“”‘’„]", searchpart)
                    if not title or not title.group(1).strip():
                        await message.channel.send(
                            content="use it like this: @MitchBot fake link \"title\" \\*description\\* \\`image url\\`",
                        )
                    else:
                        title = title.group(1).strip()
                        description = re.search(r"\*(.*?)\*", searchpart)
                        if description:
                            description = description.group(1).strip()
                        else:
                            description = ""
                        image_url = re.search(r"`(.*?)`", searchpart)
                        if image_url:
                            image_url = image_url.group(1).strip()
                        else:
                            image_url = ""
                        webpage = '''
<html>
    <head>
        <title>''' + title + '''</title>
        <meta name="description" content="''' + description + '''">
        <meta name="og:image" content="''' + image_url + '''">
    </head>
    <body>
        <p>:P</p>
    </body>
</html>'''
                        filename = urllib.parse.quote(title.replace(' ', '-') + '.html')
                        html = open('static/html/' + filename, 'w+')
                        html.write(webpage)
                        html.close()
                        external_ip = str((await http_client.fetch('https://ident.me')).body, 'utf-8')
                        await message.channel.send('http://' + external_ip + ':9876/html/' + filename)
            elif "roll" in text and (nums := re.search(r"(\d+)d(\d+)", text)):
                if (quantity := nums.group(1)) and (maximum := nums.group(2)):
                    rolls = [random.randint(1, int(maximum)) for _ in range(int(quantity))]
                    if int(quantity) > 1:
                        rolls_string = " + ".join([str(r) for r in rolls]) + " = "
                    else:
                        rolls_string = "your result is: "
                    await message.channel.send(rolls_string + str(sum(rolls)))
            elif "make" in text and "fight" in text:
                if len(other_mentions) == 2:
                    async with message.channel.typing():
                        i1 = await self.get_avatar_small(other_mentions[0], 180)
                        i2 = await self.get_avatar_small(other_mentions[1], 180)
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
                # if we're being asked to make someone else and us fight
                elif len(other_mentions) == 1 and message.raw_mentions.count(self.user.id) == 2:
                    await message.channel.send('nope, too scared')
                elif len(other_mentions) == 1 and message.raw_mentions.count(other_mentions[0].id) > 1:
                    await message.channel.send('it takes two to tango')
            elif "kiss" in text and len(other_mentions) == 0:
                async with message.channel.typing():
                    recipient = message.author
                    avatar = await self.get_avatar_small(recipient, 200)
                    blank = Image.new('RGBA', (200, 200), 0)
                    mask = Image.open("images/mask_rect.png")
                    blank.paste(avatar, (0, 0), mask)
                    smooch = Image.open("images/kiss.png")
                    final = Image.alpha_composite(blank, smooch)
                    image_bytes = BytesIO()
                    final.save(image_bytes, format='PNG')
                    image_bytes.seek(0)
                    await message.channel.send(file=discord.File(fp=image_bytes, filename='kiss.png'))
            elif ("when" in text and "born" in text) or ("my" in text and "age" in text):
                async with message.channel.typing():
                    ages = ([x for x in range(1899, 1972)] + [y for y in range(2009, 2019)])
                    age = random.choice(ages)
                    await asyncio.sleep(3)
                    await message.channel.send('you were born in: '+str(age))
            elif "what" in text and "day" in text:
                now = datetime.date.today()
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                wrong_days = days[0:now.weekday()] + days[now.weekday()+1:]
                random.shuffle(wrong_days)
                message = await message.channel.send("um " + wrong_days[0])
                await asyncio.sleep(0.3)
                for d in wrong_days[1:] + ["um", "oh god uh", "\*sweats*"]:
                    await message.edit(content=d)
                    await asyncio.sleep(0.3)
                await message.edit(content=days[now.weekday()])
            elif "emoji" in text:
                usage_hint = "usage is as follows: @MitchBot emoji \"emoji_name\" \\`emoji_souce_image_url\\`. " + \
                    "you can copy and paste this into the message box, if that helps. you can also add your image to "+\
                    "your message instead of giving a url for it."
                emoji_name = re.search(r"(?:['\"“”‘’„])(.*?)(?:['\"“”‘’„])", text)
                emoji_url = re.search(r"`(.*?)`", text)
                if not emoji_name or (not emoji_url and not message.attachments):
                    await message.channel.send(usage_hint)
                else:
                    emoji_name = emoji_name.group(1)
                    try:
                        if emoji_url:
                            emoji_url = emoji_url.group(1)
                            emoji_file = (await http_client.fetch(emoji_url)).body
                        else:
                            emoji_url = "uploaded image"  # for error handling
                            emoji_file = BytesIO()
                            await message.attachments[0].save(emoji_file, seek_begin=True)
                            emoji_file = emoji_file.read()
                        created_emoji = await message.guild.create_custom_emoji(name=emoji_name, image=emoji_file)
                        await message.channel.send(str(created_emoji))
                    except Exception as e:
                        print('error obtaining image from '+emoji_url+':')
                        print(traceback.format_exc())
                        await message.channel.send("error loading image :( check the url and try again?")
                        await message.channel.send(usage_hint)
            elif "nickname" in text:
                num = random.randint(0, len(textresources.nicknames) - 1)
                list_num = 1
                if num > 583:
                    num -= 583
                    list_num = 2
                mess = "#" + str(num+1) + " from list " + str(list_num) + ": " + textresources.nicknames[num]
                await message.channel.send(mess)

            else:
                if random.randint(0, 10) < 7:
                    compliments = [
                        "you're great, ", "you're wonderful, ", "that's amazing, ", "i'm impressed, ",
                        "that's incredible, ", "beautiful, ", "exactly, ", "couldn't have put it better myself, ",
                        "bleep-bloop, ", "truly, ", "amAzing, ", "excellent, "
                    ]
                    compliment = random.choice(compliments)
                    message_string = compliment + message.author.mention
                    await message.channel.send(message_string)
                else:
                    poem = next(textresources.poetry_generator)
                    await message.channel.send(poem)

    async def on_disconnect(self):
        if self.vc:
            await self.vc.disconnect()
            self.vc = None
            self.public_state['voice_channels'] = self.get_voice_channels()

    # public interface:

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
                self.interrupt_voice()
            source = await discord.FFmpegOpusAudio.from_probe(audio_file)
            self.vc.play(source)
            self.public_state['currently_playing'] = name
            start_time = time.time()
            self.started_playing = start_time
            await asyncio.sleep(float(length))
            if self.started_playing == start_time:
                self.public_state['currently_playing'] = ""

    async def say(self, text):
        audio_name = self.voice.text_to_wav(text)
        audio_file = os.path.join(os.getcwd(), "audio\\", audio_name)
        await self.start_playing(audio_file, text)

    def change_voice(self):
        self.voice.change_voice()
        self.public_state['current_voice'] = self.voice.current_voice()

    def interrupt_voice(self):
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
                vcs.append([str(guild), str(channel), str(channel.id),
                            bool(self.vc and self.vc.is_connected() and self.vc.channel == channel)])
        return vcs

    def get_text_channels(self):
        tcs = []
        for guild in self.guilds:
            for channel in guild.text_channels:
                tcs.append([str(guild), str(channel), str(channel.id)])
        return tcs
