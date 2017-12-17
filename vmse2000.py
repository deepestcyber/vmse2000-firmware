#!/bin/env python2.7

from __future__ import print_function

import threading
import time
import alsaaudio
import wave
import ConfigParser
import Queue

class Vmse(object):
    DEFAULT_CONFIG_PATH = "vmse2000.default.ini"
    CONFIG_PATH = "vmse2000.ini"
    #
    running = False
    # audio config
    audio_device_name = None
    audio_device = None
    fine_data = None
    audio_file_path = None
    # gpio config
    pin_running = None
    pin_fine = None
    pin_button = None
    # printer config
    printer = None
    printer_dev = None
    printer_rate = 38400
    printer_logo_path = None
    # threads:
    audio_thread = None
    printer_thread = None
    # queues
    audio_start_queue = Queue.Queue()
    audio_finish_queue = Queue.Queue()
    printer_start_queue = Queue.Queue()
    printer_finish_queue = Queue.Queue()

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
        self.audio_file_path = config.get("audio", "file")
        # gpio
        self.pin_running = config.getint("gpio", "running")
        self.pin_fine = config.getint("gpio", "fine")
        self.pin_button = config.getint("gpio", "button")
        # printer
        self.printer_dev = config.get("printer", "device")
        self.printer_rate = config.getint("printer", "baudrate")
        self.printer_logo_path = config.get("printer", "logo")
        self.printer_flipped = config.getboolean("printer", "flipped")
        self.printer_text = config.get("printer", "text").split("|")

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
        wav = wave.open(self.audio_file_path, "rb")
        data = wav.readframes(320)
        while data:
            self.fine_data.append(data)
            data = wav.readframes(320)

    def start_threads(self):
        if self.audio_device:
            print("starting audio thread")
            self.audio_thread = threading.Thread(target=self.audio_thread_foo)
            self.audio_thread.start()
        if self.printer:
            print("starting printer thread")
            self.printer_thread = threading.Thread(target=self.printer_thread_foo)
            self.printer_thread.start()

    def stop_threads(self):
        if self.audio_thread:
            self.audio_start_queue.put(False)
            self.audio_thread.join()
        if self.printer_thread:
            self.printer_start_queue.put(False)
            self.printer_thread.join()

    def audio_thread_foo(self):
        print("A: audio thread started")
        while self.running:
            entry = self.audio_start_queue.get()
            if entry:
                print("A: start playing")
                self.play_fine()
                print("A: done playing")
                self.audio_finish_queue.put(True)
            else:
                print("A: negative entry, leaving")
                break
        print("A: audio thread exiting")

    def play_fine(self):
        for data in self.fine_data:
            self.audio_device.write(data)

    def printer_thread_foo(self):
        print("P: printer thread started")
        while self.running:
            entry = self.printer_start_queue.get()
            if entry:
                print("P: start printing")
                self.print_ticket()
                print("P: done printing")
                self.printer_finish_queue.put(True)
            else:
                print("P: negative entry, leaving")
                break
        print("P: printing thread exiting")

    def print_ticket(self):
        if self.printer_flipped:
            self.printer.set(align='center', flip=True)
            for line in reversed(self.printer_text):
                self.printer.text(line + "\n")
            self.printer.image(self.printer_logo_path)
        else:
            self.printer.set(align='center')
            self.printer.image(self.printer_logo_path)
            for line in self.printer_text:
                self.printer.text(line)
        self.printer.cut()


    def _init_gpio(self):
        if self.pin_running or self.pin_fine or self.pin_button:
            print("initialising gpio")
            from RPi import GPIO
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            if self.pin_running:
                print("running pin on %d" % self.pin_running)
                GPIO.setup(self.pin_running, GPIO.OUT)
            if self.pin_fine:
                print("fine pin on %d" % self.pin_fine)
                GPIO.setup(self.pin_fine, GPIO.OUT)
            if self.pin_button:
                print("button pin on %d (pulluped)" % self.pin_button)
                GPIO.setup(self.pin_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        else:
            print("skipping gpio initialisation")

    def _init_printer(self):
        if self.printer_dev:
            print("initialising serial printer on device '%s' at %d" % (self.printer_dev, self.printer_rate))
            import escpos.printer
            self.printer = escpos.printer.Serial(self.printer_dev, baudrate=self.printer_rate)
        else:
            print("no printer")

    def do_fine(self):
        # led on:
        if self.pin_fine:
            print("Turning on fine pin %d" % self.pin_fine)
            self.GPIO.output(self.pin_fine, self.GPIO.HIGH)
        else:
            print("No fine pin set")

        # start blocking stuff in threads:
        if self.audio_thread:
            self.audio_start_queue.put(True)
        if self.printer_thread:
            self.printer_start_queue.put(True)
        # wait for threads to do there stuff:
        if self.audio_thread:
            self.audio_finish_queue.get()
        if self.printer_thread:
            self.printer_finish_queue.get()

        # led off:
        if self.pin_fine:
            print("Turning off fine pin %d" % self.pin_fine)
            self.GPIO.output(self.pin_fine, self.GPIO.LOW)

    def power_on(self):
        if self.pin_running:
            self.GPIO.output(self.pin_running, self.GPIO.HIGH)

    def power_off(self):
        if self.pin_running:
            self.GPIO.output(self.pin_running, self.GPIO.LOW)

    def clean_up(self):
        print("cleaning up")
        if self.pin_running:
            self.GPIO.output(self.pin_running, self.GPIO.LOW)
        if self.pin_fine:
            self.GPIO.output(self.pin_fine, self.GPIO.LOW)
        if self.GPIO:
            self.GPIO.cleanup()

    def run(self):
        print("\n === VMSE 2000 ===")
        print("Better watch that dirty mouths of yours...\n")
        self.running = True
        try:
            self.start_threads()
            self.power_on()

            if self.pin_button:
                while True:
                    if not self.GPIO.input(self.pin_button):
                        self.do_fine()
                    else:
                        time.sleep(0.01)
            else:
                print("Wait - no trigger!")
                time.sleep(10)

            self.power_off()
        finally:
            self.stop_threads()
            self.clean_up()


def vmse():
    v = Vmse()
    v.run()

if __name__ == "__main__":
    vmse()
