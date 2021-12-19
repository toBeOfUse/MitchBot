# python libraries
import logging

# external libraries
from tornado.ioloop import IOLoop

# project files
from MitchBot import MitchBot

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s'))
logger.addHandler(handler)


async def main():
    discord_client = MitchBot()
    with open('login_token.txt') as token_file:
        await discord_client.login(token_file.read())
    await discord_client.connect()

if __name__ == "__main__":
    try:
        IOLoop.current().run_sync(main)
    except KeyboardInterrupt:
        print("Received SIGINT, exiting")
