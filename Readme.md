# MitchBot: a fun robotic mitch presence for your server

MitchBot provides various fun responses to messages as well as being able to play songs into your voice channels and, on Windows, speak with the default text-to-speech engine. It creates a user interface at http://localhost:9876/swordfish/ in order to accomplish those things. Start MitchBot by running `main.py` after placing a login token by itself in a `login_token.txt` file on the root directory.

## Setup

### Normal Python Package Dependencies:

MitchBot's Python dependencies are managed by pipenv. Install pipenv and run `pipenv install` to set them up and then `pipenv shell` to enter the resulting Python virtual environment.

### Weird dependencies

- ffmpeg: MitchBot currently uses ffmpeg to convert audio to the Opus format that Discord likes. To use this audio functionality, the ffmpeg and ffprobe executable files should be available from your command line. They are free to download; to make them command-line accessible on Windows, place them in a directory that's listed in the PATH environment variable.
- SAPI5: MitchBot currently uses the default Windows text-to-speech engine SAPI5. So, that functionality only works on Windows at the moment, sorry

## Use

MitchBot automatically responds to messages that include the following (case-insensitive):

- bot/MitchBot/robot
- good night/goodnight
- fuck you
- flip (a) coin
- magic (8/eight) ball
- make (...) fight (with 2 @mentions in there somewhere)
- what (...) day / day of the week

MitchBot responds to the following commands if you @-mention it:

- kiss
- nickname

Only one command and one key word(s) can be responded to per incoming message.
