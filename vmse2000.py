#!/bin/env python2.7

import threading
import time


class Vmse(object):
    running = False

    def finer(self):
        print("Starting fine thread")
        time.sleep(2)
        print("Exiting fine thread")

    def run(self):
        running = True


def vmse():
    print("VMSE 2000")
    v = Vmse()
    v.run()

if __name__ == "__main__":
    vmse()
