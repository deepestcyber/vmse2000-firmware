from __future__ import print_function

import tty
import termios
import sys
import string
import wave
import alsaaudio
import os
import select

class NParse(object):
    ALPHABET = string.ascii_lowercase
    SEPARATOR = " "
    MAX_WORD_LENGTH = 32
    WORD_LIST_FILE = "swear"
    FINE_WAV = "fine.wav"

    def __init__(self):
        self.running = False
        self.buffer = ""
        self.load_word_list()
        self.load_wave()
        self.init_audio()

    def load_wave(self):
        f = wave.open(self.FINE_WAV, "rb")
        self.periodsize = f.getframerate() / 8
        data = f.readframes(self.periodsize)
        chunks = []
        while data:
            chunks.append(data)
            data = f.readframes(self.periodsize)
        self.wave_chunks = chunks

    def init_audio(self):
        device = alsaaudio.PCM(device="default")
        device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        device.setchannels(1)
        device.setrate(44100)
        self.audio_device = device

    def play_fine(self):
        for chunk in self.wave_chunks:
            self.audio_device.write(chunk)

    def load_word_list(self):
        print("loading word lists")
        lines = [line.rstrip('\n') for line in open(self.WORD_LIST_FILE)]
        self.words = set(lines)
        print("%d words in list" % len(self.words))

    def fine(self):
        #self.play_fine()
        os.system("aplay %s" % self.FINE_WAV)

    def evaluate_word(self, word):
        if word in self.words:
            # uhoh, bad word
            print("VALUATION DETECTED '%s' --- FINE CHARGED!" % word)
            self.fine()
        else:
            # puh, that was close
            pass

    def clear_stdin(self):
        cleared = ""
        got = select.select([sys.stdin], [], [], 0)
        while got[0]:
            cleared += sys.stdin.read(1)
            got = select.select([sys.stdin], [], [], 0)
        #print("cleared '%s'" % cleared)

    def read_from_stdin(self):
        c = sys.stdin.read(1)
        if c in self.ALPHABET:
            self.buffer += c
            if len(self.buffer) > self.MAX_WORD_LENGTH:
                print("word too long (%d chars), dropping" % len(self.buffer))
                self.buffer = ""
        elif c in self.SEPARATOR:
            if self.buffer == "":
                print("[empty]")
            else:
                self.evaluate_word(self.buffer)
                self.clear_stdin()
                self.buffer = ""

    def run(self):
        self.running = True
        while self.running:
            self.read_from_stdin()


stdin = sys.stdin.fileno()
tattr = termios.tcgetattr(stdin)
try:
    tty.setcbreak(stdin, termios.TCSANOW)
    nparse = NParse()
    nparse.run()
finally:
    termios.tcsetattr(stdin, termios.TCSANOW, tattr)
