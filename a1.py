from __future__ import print_function

import numpy as np
import alsaaudio

RATE= 44100
CHUNK_SIZE = 1024

def dito():
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE)
    inp.setchannels(1)
    inp.setrate(RATE)
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(CHUNK_SIZE)

    while True:
        l, data = inp.read()
        a = np.fromstring(data, dtype='int16')
        print(np.abs(a).mean())
dito()
