#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Print utterance structure...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

if __name__ == '__main__':
    try:
        uttfn = sys.argv[1]
    except IndexError:
        print("USAGE: uttplay.py UTTFNAME")
        sys.exit(1)

    print(ttslab.fromfile(uttfn))
