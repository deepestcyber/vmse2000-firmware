#!/bin/env python2.7

from __future__ import print_function

import threading
import time
import alsaaudio
import wave
import ConfigParser

class Vmse(object):
    DEFAULT_CONFIG_PATH = "vmse2000.default.ini"
    CONFIG_PATH = "vmse2000.ini"
    #
    running = False
    # audio config
    audio_device_name = None
    audio_device = None
    fine_data = None
    # gpio config
    pin_running = None
    pin_fine = None
    pin_button = None
    # printer config
    printer = None
    printer_dev = None
    printer_rate = 38400

    def __init__(self):
        self.read_config()
        self._init_audio()
        self._init_gpio()
        self._init_printer()

    def read_config(self):
        config = ConfigParser.SafeConfigParser()
        print("reading config '%s'" % self.DEFAULT_CONFIG_PATH)
        config.read(self.DEFAULT_CONFIG_PATH)
        print("reading config '%s'" % self.CONFIG_PATH)
        config.read(self.CONFIG_PATH)
        # audio
        self.audio_device_name = config.get("audio", "device")
        # gpio
        self.pin_running = config.getint("gpio", "running")
        self.pin_fine = config.getint("gpio", "fine")
        self.pin_button = config.getint("gpio", "button")
        # printer
        self.printer_dev = config.get("printer", "device")
        self.printer_rate = config.getint("printer", "baudrate")

    def _init_audio(self):
        print("initialsing audio output")
        device = alsaaudio.PCM(device="default")
        device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        device.setchannels(1)
        device.setrate(44100)
        device.setperiodsize(320)
        self.audio_device = device
        # load fine sound data:
        self.fine_data = []
        FINE = "fine.wav"
        wav = wave.open(FINE, "rb")
        data = wav.readframes(320)
        while data:
            self.fine_data.append(data)
            data = wav.readframes(320)

    def _init_gpio(self):
        if self.pin_running or self.pin_fine or self.pin_button:
            print("initialising gpio")
            from RPi import GPIO
            GPIO.setmode(GPIO.BCM)
            if self.pin_running:
                print("running pin on %d" % self.pin_running)
                GPIO.setup(self.pin_running, GPIO.OUT)
            if self.pin_fine:
                print("fine pin on %d" % self.pin_fine)
                GPIO.setup(self.pin_fine, GPIO.OUT)
            if self.pin_button:
                print("button pin on %d (pulluped)" % self.pin_button)
                GPIO.setup(self.pin_button, GPIO.IN, pull_up_down=GPIO.PUD)
        else:
            print("skipping gpio initialisation")

    def _init_printer(self):
        if self.printer_dev:
            print("initialising serial printer on device '%s' at %d" % (self.printer_dev, self.printer_rate))
            import escpos.printer
            self.printer = escpos.printer.Serial(self.printer_dev, baudrate=self.printer_rate)
        else:
            print("no printer")

    def play_fine(self):
        for data in self.fine_data:
            self.audio_device.write(data)

    def finer(self):
        self.play_fine()

    def run(self):
        running = True
        return
        t = threading.Thread(target=self.finer)
        t.start()
        t.join()
        print("donned")


def vmse():
    print("VMSE 2000")
    v = Vmse()
    v.run()

if __name__ == "__main__":
    vmse()
