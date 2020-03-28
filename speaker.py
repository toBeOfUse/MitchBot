import comtypes.client  # Importing comtypes.client will make the gen subpackage
try:
    from comtypes.gen import SpeechLib  # comtypes
except ImportError:
    # Generate the SpeechLib lib and any associated files
    engine = comtypes.client.CreateObject("SAPI.SpVoice")
    stream = comtypes.client.CreateObject("SAPI.SpFileStream")
    from comtypes.gen import SpeechLib
import os
import re
import hashlib


# loosely based on pyttsx3 (GPL-3.0) which sadly had an installation bug on windows that kept me from using it
# directly. maybe someday
class VoiceHaver():
    def __init__(self):
        self._tts = comtypes.client.CreateObject('SAPI.SPVoice')
        self.voiceIndex = 1
        self.voices = [x for x in self._tts.GetVoices()]  # possibly redundant?
        self._set_voice()
        self.rate = 0
        self.change_speed(100.0)

    def _set_voice(self):
        self._tts.Voice = self.voices[self.voiceIndex]
        self._voiceID = self._tts.Voice.Id

    def current_voice(self):
        return re.search(r"\\([^\\]*)$", self._voiceID).group(1).replace('_', ' ')

    def change_voice(self):
        self.voiceIndex += 1
        self.voiceIndex %= len(self.voices)
        self._set_voice()

    def change_speed(self, percentage):
        self.rate *= percentage/100
        self._tts.Rate = int(self.rate)

    def text_to_wav(self, text):
        hash = hashlib.md5(bytes(text + self._voiceID, 'utf-8')).hexdigest()
        filename = os.path.join(os.getcwd(), "audio\\", hash + ".wav")
        if not os.path.exists(filename):
            cwd = os.getcwd()
            stream = comtypes.client.CreateObject('SAPI.SPFileStream')
            stream.Open(filename, SpeechLib.SSFMCreateForWrite)
            temp_stream = self._tts.AudioOutputStream
            self._tts.AudioOutputStream = stream
            self._tts.Speak(text)
            self._tts.AudioOutputStream = temp_stream
            stream.close()
            os.chdir(cwd)
        return filename
