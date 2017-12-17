#!/usr/bin/env python2.7 -u

from __future__ import print_function

import termios
import tty
import sys
import os
import string
import wave
import alsaaudio

ALPHABET = string.ascii_lowercase
TERM = " "
WORDFILE = "swear"
FINE = "fine.wav"


def load_words(filename):
    lines = [line.rstrip('\n') for line in open(filename)]
    return set(lines)

def do_fine():
    # os.system("aplay " + FINE)
    device.setperiodsize(320)

def work_word(words, word):
    if word in words:
        print("VIOLATION DETECTED: '%s'" % word)
        do_fine()

def load_wav(filename):
    return wave.open(filename, "rb")


words = load_words(WORDFILE)
wav = load_wav(FINE)
#wavdata = wav.read
device = alsaaudio.PCM(device="default")
device.setformat(alsaaudio.PCM_FORMAT_S16_LE)

stdin = sys.stdin.fileno()
tattr = termios.tcgetattr(stdin)


try:
    tty.setcbreak(stdin, termios.TCSANOW)

    buf = ""
    while True:
        c = sys.stdin.read(1)
        if c in ALPHABET:
            buf += c
        elif c in TERM:
            # word ends:
            if buf == "":
                print("[empty]")
            else:
                work_word(words, buf)
                buf = ""
finally:
    termios.tcsetattr(stdin, termios.TCSANOW, tattr)

