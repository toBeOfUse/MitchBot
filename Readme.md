# MitchBot: a fun robotic mitch presence for your server

MitchBot provides various fun responses to messages as well as being able to play songs into your voice channels and, on Windows, speak with the default text-to-speech engine. It creates a user interface at http://localhost:9876/swordfish/ in order to accomplish those things. Start MitchBot by running `ControlServer.py` after placing a login token by itself in a `login_token.txt` file on the root directory.

## Setup
### Normal Python Package Dependencies:
MitchBot has some fun python package dependencies that are listed in `requirements.in` and listed in pip-tools format in `requirements.txt`. As long as `requirements.txt` is up to date, the easiest way to obtain this project's python dependencies is by installing pip-tools and running the command `pip-sync`. (If `requirements.txt` is out of date but `requirements.in` isn't, you can create `requirements.txt` by running `pip-compile`. If both of those suckers are out of date, you can create `requirements.in` by running `pip freeze > requirements.in`. (In case you're new to this: you can install new Python packages by running `python -m pip install [package-name]`.))
### Weird dependencies
 - ffmpeg: MitchBot currently uses ffmpeg to convert audio to the Opus format that Discord likes. To use this audio functionality, the ffmpeg and ffprobe executable files should be available from your command line. They are free to download; to make them command-line accessible on Windows, place them in a directory that's listed in the PATH environment variable.
 - SAPI5: MitchBot currently uses the default Windows text-to-speech engine SAPI5. So, that functionality only works on Windows at the moment, sorry

## Use
MitchBot automatically responds to messages that include the following (case-insensitive):

 - bot/MitchBot/robot
 - horse
 - good night/goodnight
 - fuck you
 - hm(mmm....)
 - flip (a) coin

MitchBot responds to the following commands if you @-mention it:

- @MitchBot fake link "title" \*description\* \`image url\` (this is kind of buggy if there's punctuation in the title)
- @MitchBot roll \[number]d\[number] (it's like rolling dice)
- @MitchBot make @someone and @someone fight
- @MitchBot kiss (only works if no one else is mentioned; asking MitchBot to kiss other people will not work)
- @MitchBot *when* was i *born*/what is *my* *age* (checks for either pair of the italicized keywords)
- @MitchBot *what day* is it (again, keywords italicized)
- @MitchBot emoji "emoji_name" \`emoji_url\` (instead of providing a url, the user can upload an image)
- @MitchBot nickname

Only one command and one key word(s) can be responded to per incoming message.
