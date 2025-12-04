# VMSE2000 firmware

This is the orchestrator that takes in bad words, lights the lights,
prints the prints and speaks the speech.

## Installation

    poetry install

If this fails with 

    Error: The current project could not be installed: No file/folder found for package vmse2000-firmware

on your development machine, you are probably fine. See [Developing](#Developing) below.

## Configuration

See `vmse2000.default.ini`.

## System configuration

### Audio

You may need to configure ALSA to support down-sampling
to 44.1kHz mono.

An example configuration would look like this:

    pcm_slave.sl3 {
        pcm "hw:CARD=Set"
        format S16_LE
        channels 1
        rate 44100
    }

    pcm.complex_convert {
        type plug
        slave sl3
    }

Find more details [here](https://www.alsa-project.org/main/index.php/Asoundrc).
You may need to change `"hw:CARD=Set"` to however your sound card is called.
You may find this information via `aplay -L`.

You can test your settings with `aplay` or `./scripts/play_audio.py`,
depending on the stage you want to debug.


## Developing
If you are working on a machine that has no printer and no GPIOs, you can 
disable those. A useful `vmse2000.ini` could look like this:

    [printer]
    vendor_id = 0
    
    [gpio]
    running =
    fine =
    button =
    
    [audio]
    device = default

You should probably work with a virtual environment. After `poetry install`, you should 
be able to just run the VMSE 2000 locally with:

    poetry run python vmse2000.py

To trigger a fine, you can send a profanity to UDP port 1800, where the
VMSE 2000 listens. This can be done on the shell like this:

    echo -n "ass" | nc -u -w0 localhost 1800

Or when you are using bash:

    echo -n "bitch" > /dev/udp/localhost/1800

There is also a script `trigger.sh` that does this for you.
