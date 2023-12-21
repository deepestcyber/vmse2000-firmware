# VMSE2000 firmware

This is the orchestrator that takes in bad words, lights the lights,
prints the prints and speaks the speech.

## Installation

    poetry install

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
