#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a g2p from rules and mappings in source text
    files.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs

import ttslab
from ttslab.g2p import *

RULES_INFN = "data/pronun/main.rules"
GNULLS_INFN = "data/pronun/main.rules.gnulls"
GRAPHMAP_INFN = "data/pronun/main.rules.graphmap"
PHONEMAP_INFN = "data/pronun/main.rules.phonemap"
G2P_FILE = "g2p.pickle"

if __name__ == "__main__":
    #load from files:
    g2p = G2P_Rewrites_Semicolon()
    g2p.load_ruleset_semicolon(RULES_INFN)
    try:
        g2p.load_gnulls(GNULLS_INFN)
    except IOError:
        pass
    #map graphs:
    try:
        g2p.load_simple_graphmapfile(GRAPHMAP_INFN)
        g2p.map_graphs()
    except IOError:
        pass
    #map to phones from onechar to IPA:
    try:
        g2p.load_simple_phonemapfile(PHONEMAP_INFN)
        g2p.map_phones()
    except IOError:
        pass
    #save:
    ttslab.tofile(g2p, G2P_FILE)
