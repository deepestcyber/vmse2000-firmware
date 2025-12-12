#!/bin/env python3
# simple script for generating random tokens for testing the handling of tokens in the vmse2000

import random
import string

FILENAME = "tokens.txt"

for _i in range(100):
    with open(FILENAME, "a") as f:
        f.write("".join(random.choices(string.ascii_lowercase + string.digits, k=20)) + "\n")
