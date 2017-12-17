#!/usr/bin/env python2.7 -u

from __future__ import print_function

import termios
import tty
import sys
import os
import string
import wave
import alsaaudio

FINE = "fine.wav"



wav = wave.open(FINE, "rb")


device = alsaaudio.PCM(device="default")
device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
device.setchannels(1)
device.setrate(44100)

device.setperiodsize(320)

data = wav.readframes(320)
wavdat = []

print("loading")
while data:
    wavdat.append(data)
    data = wav.readframes(320)
print("outing")
for data in wavdat:
    device.write(data)
print("doning")
