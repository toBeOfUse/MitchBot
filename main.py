# python libraries
import asyncio

# project files
import MitchBot

discord_client = None  # instantiated in main() so as to use the event loop created when main() is run


async def main():
    global discord_client
    discord_client = MitchBot.MitchClient()
    with open('login_token.txt') as token_file:
        await discord_client.login(token_file.read())
    await discord_client.connect()

if __name__ == "__main__":
    asyncio.run(main())
