#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a voice object by loading sub modules and data
    and initialising the appropriate class...

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os

import ttslab

PHONESET_FILE = "phoneset.pickle"
PRONUNDICT_FILE = "pronundict.pickle"
PRONUNADDENDUM_FILE = "pronunaddendum.pickle"
G2P_FILE = "g2p.pickle"
ENGPHONESET_FILE = "engphoneset.pickle"
ENGPRONUNDICT_FILE = "engpronundict.pickle"
ENGPRONUNADDENDUM_FILE = "engpronunaddendum.pickle"
ENGG2P_FILE = "engg2p.pickle"
HTSMODELS_DIR = "data/hts"
USCATALOGUE_FILE = "data/unitcatalogue.pickle"



def hts():
    from ttslab.defaultvoice import LwaziHTSVoice
    from ttslab.voices.yoruba_default import SynthesizerHTSME_Tone_NoTone
    voice = LwaziHTSVoice(phoneset=ttslab.fromfile(PHONESET_FILE),
                          g2p=ttslab.fromfile(G2P_FILE),
                          pronundict=ttslab.fromfile(PRONUNDICT_FILE),
                          pronunaddendum=ttslab.fromfile(PRONUNADDENDUM_FILE),
                          synthesizer=SynthesizerHTSME_Tone_NoTone(voice=None, models_dir=os.path.join(os.getcwd(), HTSMODELS_DIR)))
    ttslab.tofile(voice, "hts.voice.pickle")

if __name__ == "__main__":
    try:
        switch = sys.argv[1]
        assert switch in ["hts"]
    except IndexError:
        print("USAGE: ttslab_make_tonevoice.py [hts|...]")
        sys.exit(1)
    
    if switch == "hts":
        hts()
    else:
        raise NotImplementedError
