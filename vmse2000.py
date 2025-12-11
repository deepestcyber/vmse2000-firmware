#!/usr/bin/env python
import threading
import time
import random
import alsaaudio
import wave
from configparser import ConfigParser
from queue import Queue, Empty
import socket
import select
import logging
import json

import gpiod
from gpiod.line import Direction, Value


class Vmse(object):
    DEFAULT_CONFIG_PATH = "vmse2000.default.ini"
    CONFIG_PATH = "vmse2000.ini"
    #
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
    gpio_running = None
    gpio_fine = None
    gpio_button = None
    # printer config
    printer = None
    printer_dev = None
    printer_rate = 38400
    printer_logo_path = None
    printer_text = "Violation"
    printer_flipped = False
    printer_vendor_id = None
    printer_device_id = None
    # evidence
    evidence_file = None
    # socket config
    udp_host = None
    udp_port = None
    socket_list = []
    # threads:
    audio_thread = None
    printer_thread = None
    socket_thread = None
    button_thread = None
    # queues
    audio_start_queue = Queue()
    audio_finish_queue = Queue()
    printer_start_queue = Queue()
    printer_finish_queue = Queue()
    socket_word_queue = Queue()

    def __init__(self):
        self.read_config()
        self._init_audio()
        self._init_gpio()
        self._init_printer()
        self._init_socket()

    def read_config(self):
        config = ConfigParser()
        print(f"reading config '{self.DEFAULT_CONFIG_PATH}'")
        config.read(self.DEFAULT_CONFIG_PATH)
        print(f"reading config '{self.CONFIG_PATH}'")
        config.read(self.CONFIG_PATH)
        # audio
        self.audio_device_name = config.get("audio", "device")
        self.audio_file_path = config.get("audio", "file")
        # gpio
        def get_gpio(name):
            val = config.get("gpio", name)
            if val is not None and val != "":
                return int(val)
            return None
        self.pin_running = get_gpio("running")
        self.pin_fine = get_gpio("fine")
        self.pin_button = get_gpio("button")
        # printer
        self.printer_vendor_id = int(
            config.get("printer", "vendor_id", fallback=0), 16)
        self.printer_device_id = int(
            config.get("printer", "device_id", fallback=0), 16)
        self.printer_dev = config.get("printer", "device", fallback=None)
        self.printer_rate = config.getint("printer", "baudrate", fallback=9600)
        self.printer_logo_path = config.get("printer", "logo")
        self.printer_flipped = config.getboolean("printer", "flipped")
        self.printer_text = config.get("printer", "text").split("|")
        # socket
        self.udp_port = config.getint("socket", "udp_port")
        self.udp_host = config.get("socket", "udp_host")
        # evidence vault
        self.evidence_file = config.get("prosecution", "evidence_file", fallback=None)
        if self.evidence_file == "":
            self.evidence_file = None
        if self.evidence_file:
            print(f"evidence will be stored in '{self.evidence_file}'")
        else:
            print("no evidence vault configured, prosecutions will be tricky...")
        #
        print("Text is:")
        for line in self.printer_text:
            print(f"  {line}")

    def _init_audio(self):
        print("initialising audio output")

        # load fine sound data:
        self.fine_data = []
        with wave.open(self.audio_file_path, "rb") as wav:
            period_size = wav.getframerate() // 8
            data = wav.readframes(period_size)
            while data:
                self.fine_data.append(data)
                data = wav.readframes(period_size)

        device = alsaaudio.PCM(
            device=self.audio_device_name,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            rate=44_100,
            channels=1,
            periodsize=period_size,
        )
        self.audio_device = device

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
        try:
            # drain any pending audio to prevent underruns errors:
            self.audio_device.drop()
            for data in self.fine_data:
                self.audio_device.write(data)
        except alsaaudio.ALSAAudioError as e:
            logging.exception("Writing to device failed")

    def printer_thread_foo(self):
        print("P: printer thread started")
        while self.running:
            entry = self.printer_start_queue.get()
            if entry:
                print("P: start printing")
                self.print_ticket(entry)
                print("P: done printing")
                self.printer_finish_queue.put(True)
            else:
                print("P: negative entry, leaving")
                break
        print("P: printing thread exiting")

    def print_ticket(self, item=True):
        xx = "{:f}".format(random.random() / 1000.0)
        print(f"item is {item} ({type(item)})")
        if self.printer_flipped:
            self.printer.set(align="center", flip=True)
            self.printer.image("assets/violation-flipped.png")
            for line in reversed(self.printer_text):
                if "$FINE$" in line:
                    line = line.replace("$FINE$", xx)
                if isinstance(item, str):
                    line = line.replace("$ITEM$", item)
                if "$TIMESTAMP$" in line:
                    line = line.replace("$TIMESTAMP$", time.strftime("%Y-%m-%d %H:%M:%S"))
                self.printer.text(line + "\n")
            self.printer.image(self.printer_logo_path)
            self.printer.image("assets/morality-flipped.png")
        else:
            self.printer.set(align="center")
            self.printer.image("assets/morality.png")
            self.printer.image(self.printer_logo_path)
            for line in self.printer_text:
                if "$FINE$" in line:
                    line = line.replace("$FINE$", xx)
                if isinstance(item, str):
                    line = line.replace("$ITEM$", item)
                if "$TIMESTAMP$" in line:
                    line = line.replace("$TIMESTAMP$", time.strftime("%Y-%m-%d %H:%M:%S"))
                self.printer.text(line + "\n")
            self.printer.image("assets/violation.png")
        self.printer.cut()

    def socket_thread_foo(self):
        print("S: socket thread started")
        while self.running:
            (r, w, e) = select.select(self.socket_list, [], [], 0.1)
            for s in r:
                data, addr = s.recvfrom(1024)
                # TODO: fix this, this needs buffering
                print(f"{addr} sent: '{data}'")
                data = str(data, "utf-8")
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

            pressed = False

            # block and wait for edge events
            for ev in self.gpio_button.read_edge_events():
                if ev.line_offset == self.pin_button:
                    pressed = True

            if pressed:
                self.socket_word_queue.put(True)
                # unprelling:
                time.sleep(0.3)
            else:
                time.sleep(0.01)

    def _init_gpio(self):
        if self.pin_running is not None or self.pin_fine is not None or self.pin_button is not None:
            print("initialising gpio")

            # this might not work on raspi <5, sorry, cannot test rn
            chip = gpiod.Chip("/dev/gpiochip4")

            if self.pin_running is not None:
                print(f"running pin on {self.pin_running}")
                self.gpio_running = chip.request_lines(
                    config={
                        self.pin_running: gpiod.LineSettings(
                            direction=Direction.OUTPUT,
                        ),
                    }
                )
            if self.pin_fine is not None:
                print(f"fine pin on {self.pin_fine}")
                self.gpio_fine = chip.request_lines(
                    config={
                        self.pin_fine: gpiod.LineSettings(
                            direction=Direction.OUTPUT,
                        ),
                    }
                )
            if self.pin_button is not None:
                print(f"button pin on {self.pin_button} (pulluped)")
                self.gpio_button = chip.request_lines(
                    config={
                        self.pin_button: gpiod.LineSettings(
                            edge_detection=Edge.BOTH,
                            bias=Bias.PULL_UP,
                            debounce_period=timedelta(milliseconds=10),
                        ),
                    }
                )
        else:
            print("skipping gpio initialisation")

    def _init_printer(self):
        if self.printer_dev or self.printer_vendor_id:

            import escpos.printer

            if self.printer_vendor_id:
                print(
                    f"initialising usb printer {self.printer_vendor_id}:"
                    f"{self.printer_device_id}"
                )
                self.printer = escpos.printer.Usb(
                    self.printer_vendor_id,
                    self.printer_device_id,
                    profile="TM-T88IV",
                )
            else:
                print(
                    f"initialising serial printer on device "
                    f"'{self.printer_dev}' at {self.printer_rate}"
                )
                self.printer = escpos.printer.Serial(
                    self.printer_dev, baudrate=self.printer_rate
                )
            assert self.printer.is_usable()
        else:
            print("no printer")

    def _init_socket(self):
        if self.udp_port:
            print(f"listening on UDP {self.udp_host}:{self.udp_port}")
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.udp_host, self.udp_port))
            self.socket_list.append(self.udp_socket)
        else:
            print("No UDP socket")

    def store_evidence(self, profanity):
        if self.evidence_file:
            data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "profanity": profanity,
            }
            try:
                with open(self.evidence_file, "a") as f:
                    json.dump(data, f)
                    f.write("\n")
            except Exception:
                logging.exception("Storing evidence failed")
        else:
            print("no evidence vault configured, cannot store evidence")

    def do_fine(self, item=True):
        # led on:
        self.fining = True
        if self.pin_fine:
            print(f"Turning on fine pin {self.pin_fine}")
            self.gpio_fine.set_value(self.pin_fine, Value.ACTIVE)
        else:
            print("No fine pin set")

        self.store_evidence(item)

        # start blocking stuff in threads:
        if self.audio_thread:
            self.audio_start_queue.put(True)
        if self.printer_thread:
            self.printer_start_queue.put(item)
        # wait for threads to do there stuff:
        if self.audio_thread:
            self.audio_finish_queue.get()
        if self.printer_thread:
            self.printer_finish_queue.get()

        # led off:
        if self.pin_fine:
            print(f"Turning off fine pin {self.pin_fine}")
            self.gpio_fine.set_value(self.pin_fine, Value.INACTIVE)
        self.fining = False

    def power_on(self):
        if self.pin_running:
            self.gpio_running.set_value(self.pin_running, Value.ACTIVE)

    def power_off(self):
        if self.pin_running:
            self.gpio_running.set_value(self.pin_running, Value.INACTIVE)

    def clean_up(self):
        print("cleaning up")
        if self.pin_running:
            self.gpio_running.set_value(self.pin_running, Value.INACTIVE)
        if self.pin_fine:
            self.gpio_fine.set_value(self.pin_running, Value.INACTIVE)

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
                except Empty:
                    # that's okay, dude! we'll just try again...
                    continue
                if item is True:
                    # this one came from button:
                    print("Tautologic, my dear Watson!")
                    self.do_fine()
                else:
                    print(f"got word: '{item}'")
                    print("VIOLATION DETECTED!")
                    self.do_fine(item)
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
