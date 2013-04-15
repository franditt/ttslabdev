#!/bin/bash

ttslab_make_phoneset.py bambara_default BambaraPhoneset
ttslab_make_g2p.py
ttslab_make_pronundicts.py
ttslab_make_voice.py frontend
ttslab_make_voice.py wordusfrontend
ttslab_make_voice.py wordus
