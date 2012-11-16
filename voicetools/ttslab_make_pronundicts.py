#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script makes a pronunciation addendum and dictionary from
    simple text files. It requires a phoneset and g2p rules.

    It looks for specific files and location and should thus be run
    from the appropriate location.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import codecs

import ttslab
from ttslab.pronundict import PronunciationDictionary

PRONUNDICT_INFN = "data/pronun/main.pronundict"
DICT_INFN = "data/pronun/main.dict"
ADDENDUM_INFN = "data/pronun/addendum.dict"
WORDLIST_INFN = "data/pronun/words.txt"
DICT_OUTFN = "pronundict.pickle"
ADDENDUM_OUTFN = "pronunaddendum.pickle"
PHSET_FILE = "phoneset.pickle"
G2P_FILE = "g2p.pickle"


def load_simplepronundict(infn, phmap):
    pronundict = {}
    try:
        with codecs.open(infn, encoding="utf-8") as infh:
            for line in infh:
                linelist = line.split()
                pronundict[linelist[0]] = [phmap[phone] for phone in linelist[1:]]
    except IOError:
        pass
    return pronundict

def prepredict(wordsfn, g2p, skipwords):
    with codecs.open(wordsfn, encoding="utf-8") as infh:
        words = [word.strip() for word in infh.readlines() if word.strip() not in skipwords]
    pronundict = {}
    numwords = len(words)
    for i, word in enumerate(words):
        print("%s/%s: %s" % (i+1, numwords, word))
        pronundict[word] = g2p.predict_word(word)
    return pronundict

if __name__ == "__main__":
    phset = ttslab.fromfile(PHSET_FILE)
    phmap = dict([(v, k) for k, v in phset.map.items()])
    assert len(phmap) == len(phset.map), "mapping not one-to-one..."
    g2p = ttslab.fromfile(G2P_FILE)
    #load
    try:
        pronundict = PronunciationDictionary()
        pronundict.fromtextfile(PRONUNDICT_INFN, phmap)
    except IOError:
        pronundict = load_simplepronundict(DICT_INFN, phmap)
    addendum = load_simplepronundict(ADDENDUM_INFN, phmap)
    #pre-predict from wordlist and add to addendum
    try:
        skipwords = set(list(pronundict) + list(addendum))
        addendum.update(prepredict(WORDLIST_INFN, g2p, skipwords))
    except IOError:
        pass
    #save
    ttslab.tofile(addendum, ADDENDUM_OUTFN)
    ttslab.tofile(pronundict, DICT_OUTFN)
