#!/bin/env python3

from __future__ import print_function

import threading
import time
import random
import alsaaudio
import wave
import configparser
import queue
import socket
import select


class Vmse(object):
    DEFAULT_CONFIG_PATH = "vmse2000.default.ini"
    CONFIG_PATH = "vmse2000.ini"
    #
    GPIO = None
    running = False
    fining = False
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
    # socket config
    udp_host = None
    udp_port = None
    socket_list = []
    # morale config
    morale_swear_path = None
    morale_swear_set = None
    # threads:
    audio_thread = None
    printer_thread = None
    socket_thread = None
    button_thread = None
    # queues
    audio_start_queue = queue.Queue()
    audio_finish_queue = queue.Queue()
    printer_start_queue = queue.Queue()
    printer_finish_queue = queue.Queue()
    socket_word_queue = queue.Queue()

    def __init__(self):
        self.read_config()
        self._init_audio()
        self._init_gpio()
        self._init_printer()
        self._init_socket()
        self._load_morale()

    def _load_morale(self):
        print("loading morale from %s" % self.morale_swear_path)
        self.morale_swear_set = set([line.rstrip('\n') for line in open(self.morale_swear_path)])
        print("%d words on blacklist" % len(self.morale_swear_set))

    def read_config(self):
        config = configparser.SafeConfigParser()
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
        # socket
        self.udp_port = config.getint("socket", "udp_port")
        self.udp_host = config.get("socket", "udp_host")
        # morale
        self.morale_swear_path = config.get("morale", "swear_file")

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
        if self.socket_list:
            print("starting socket listener thread")
            self.socket_thread = threading.Thread(target=self.socket_thread_foo)
            self.socket_thread.start()
        if self.pin_button:
            print("starting button monitoring thread")
            self.button_thread = threading.Thread(target=self.button_thread_foo)
            self.button_thread.start()

    def stop_threads(self):
        if self.audio_thread:
            print("joining audio thread")
            self.audio_start_queue.put(False)
            self.audio_thread.join()
        if self.printer_thread:
            print("printer thread")
            self.printer_start_queue.put(False)
            self.printer_thread.join()
        if self.socket_thread:
            print("joining socket thread")
            self.socket_thread.join()
        if self.button_thread:
            print("joining button thread")
            self.button_thread.join()

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
        xx = "%f" % (random.random() / 1000.0)
        if self.printer_flipped:
            self.printer.set(align='center', flip=True)
            for line in reversed(self.printer_text):
                if "$FINE$" in line:
                    line = line.replace("$FINE$", xx)
                line = line + "\n"
                line = line.encode()
                self.printer.text(line)
            self.printer.image(self.printer_logo_path)
        else:
            self.printer.set(align='center')
            self.printer.image(self.printer_logo_path)
            for line in self.printer_text:
                if "$FINE$" in line:
                    line = line.replace("$FINE$", xx)
                    line = line.encode()
                self.printer.text(line)
        self.printer.cut()

    #def print_cut(self):
    #    self.printer._raw(b"\n\n\n\n\n\n")
    #    self.printer._raw(b'\x1d\x56\x00')

    def socket_thread_foo(self):
        print("S: socket thread started")
        while self.running:
            (r, w, e) = select.select(self.socket_list, [], [], 0.1)
            for s in r:
                data, addr = s.recvfrom(1024)
                data = "fuck"
                # TODO: fix this, this needs buffering
                print("%s sent: '%s'" % (addr, data))
                for word in data.split(" "):
                    if word:
                        self.socket_word_queue.put(word)
        print("S: socket thread exiting")

    def button_thread_foo(self):
        print("B: button thread started")
        while self.running:
            if self.fining:
                time.sleep(0.1)
                continue
            pressed = not self.GPIO.input(self.pin_button)
            if pressed:
                self.socket_word_queue.put(True)
                # unprelling:
                time.sleep(0.3)
            else:
                time.sleep(0.01)

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

    def _init_socket(self):
        if self.udp_port:
            print("listening on UDP %s:%d" % (self.udp_host, self.udp_port))
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.udp_host, self.udp_port))
            self.socket_list.append(self.udp_socket)
        else:
            print("No UDP socket")

    def do_fine(self):
        # led on:
        self.fining = True
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
        self.fining = False

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

            while self.running:
                try:
                    item = self.socket_word_queue.get(True, 0.1)
                except queue.Empty:
                    # that's okay, dude! we'll just try again...
                    continue
                if item is True:
                    # this one came from button:
                    print("Tautologic, my dear Watson!")
                    self.do_fine()
                else:
                    print("got word: '%s'" % item)
                    if item.lower() in self.morale_swear_set:
                        print("VIOLATION DETECTED!")
                        self.do_fine()
                    else:
                        print("seems fine...")
            else:
                print("Wait - no trigger!")
                time.sleep(10)

            self.power_off()
        finally:
            self.running = False
            self.stop_threads()
            self.clean_up()


def vmse():
    v = Vmse()
    v.run()

if __name__ == "__main__":
    vmse()
