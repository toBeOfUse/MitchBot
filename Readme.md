# MitchBot: a fun robotic Mitch presence for Discord servers

MitchBot provides various fun responses to messages as well as posting predictions and puzzles at specified times. Start MitchBot by running `main.py` after placing a login token by itself in a `login_token.txt` file on the root directory.

## Setup

### Normal Python Package Dependencies:

MitchBot's Python dependencies are managed by pipenv. Install pipenv and run `pipenv install` to set them up and then `pipenv shell` to enter the resulting Python virtual environment.

### Non-Python dependencies

- **Cairo**: MitchBot uses the CairoSVG Python package to render some of the daily puzzles, and the CairoSVG Python package depends on the Cairo library. On Linux, Cairo is probably already installed, or you can get it from a package manager; on Windows, the easiest way to get Cairo is unfortunately to install the SVG editor Inkscape and then add C:/Program Files/Inkscape/ to your system PATH.
- **Blender**: MitchBot also uses Blender to render some puzzle templates. Blender is freely obtainable through blender.org.
- **Fonts**: MitchBot's puzzle templates use the fonts Liberation Sans, Mario 256, Kingthings Exeter, fs Tahoma 8px, and Arial. These fonts are available for free on the Internet. If they are not installed on your system, some random fallback font will probably be used.

### Dependencies for Features That Aren't Currently Maintained:

- **ffmpeg**: MitchBot currently uses ffmpeg to convert audio to the Opus format that Discord likes. To use this audio functionality, the ffmpeg and ffprobe executable files should be available from your command line. They are free to download; to make them command-line accessible on Windows, place them in a directory that's listed in the PATH environment variable.
- **SAPI5**: MitchBot currently uses the default Windows text-to-speech engine SAPI5. So, that functionality only works on Windows at the moment, sorry

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

## Other Credits

Source images for the puzzle backgrounds come from: The Codex Atlanticus, pages 272 and 459; a screenshot of Super Mario Galaxy 2, Honeyhop Galaxy; Ben Kirchner's illustration of Sam Ezersky for "Who Made My Crossword?"; and the "HEXAGONAL RULER 2.0 - Redefine Your Sketch Tool" Kickstarter page.
