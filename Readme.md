# MitchBot: a robotic mitch presence for your server

MitchBot provides various fun text responses to messages as well as being able to play songs into your voice channels and, on Windows, speak with the default text-to-speech engine. It creates a user interface at http://localhost:9876/swordfish/ in order to accomplish those things.

## Setup:
### Normal Python Package Dependencies:
MitchBot has some fun python package dependencies that are listed in `requirements.in` and listed in pip-tools format in `requirements.txt`. As long as `requirements.txt` is up to date, the easiest way to obtain this project's python dependencies is by instlaling pip-tools and running the command `pip-sync`. (If `requirements.txt` is out of date but `requirements.in` isn't, you can create `requirements.txt` by running `pip-compile`. If both of those suckers are out of date, you can create `requirements.in` by running `pip freeze > requirements.in`. In case you're new to this, you can install new Python packages by running `pip install [package-name]`.)
### Weird dependencies:
ffmpeg: MitchBot currently uses the free ffmpeg utilities to convert audio to the Opus format that Discord likes. To use the audio functionality, ffmpeg.exe and ffprobe.exe should be available from the command line. This can be accomplished by downloading them, they're free, into a directory listed in the PATH environment variable.
SAPI5: MitchBot currently uses the default Windows text-to-speech engine SAPI5. So, that functionality only works on Windows at the moment, sorry.