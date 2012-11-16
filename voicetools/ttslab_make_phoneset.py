#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a phoneset object and saves this to be loaded by
    other modules and scripts...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys, os

import ttslab

PHONESET_FILE = "phoneset.pickle"

if __name__ == "__main__":
    try:
        phonesetmodule = sys.argv[1]
        phonesetclass = sys.argv[2]
    except IndexError:
        print("USAGE: ttslab_make_phoneset.py [PHONESET_MODULE] [PHONESET_CLASS]")
        sys.exit(1)
    try:
        exec("from ttslab.voices.%s import %s" % (phonesetmodule, phonesetclass))
    except ImportError:
        raise Exception("Could not import ttslab.voices.%s.%s" % (phonesetmodule, phonesetclass))
    phoneset = eval("%s()" % (phonesetclass))
    ttslab.tofile(phoneset, PHONESET_FILE)
