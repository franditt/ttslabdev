#!/bin/bash

ttslab_make_phoneset.py yoruba_default YorubaPhoneset
ttslab_make_g2p.py
ttslab_make_pronundicts.py
ttslab_make_voice.py frontend
ttslab_make_voice.py hts
