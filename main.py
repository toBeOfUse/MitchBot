# python libraries
import asyncio

# project files
import MitchBot


async def main():
    discord_client = MitchBot.MitchClient()
    with open('login_token.txt') as token_file:
        await discord_client.login(token_file.read())
    await discord_client.connect()

if __name__ == "__main__":
    asyncio.run(main())
