#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This script takes a phoneset and attempts to generate questions
    for tree construction in HTS automatically based on the features
    defined... The resulting file should be manually reviewed as not
    all phoneset features might be relevant during acoustic model
    tying.
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import sys

import ttslab

PHONESETFN = "phoneset.pickle"

ALL_CONTEXTS = {"LL": "%s^*",
                "L": "*^%s-*",
                "C": "*-%s+*",
                "R": "*+%s=*",
                "RR": "*=%s@*"}
VOWEL_CONTEXTS = {"C-Syl": "*|%s/C:*"}

if __name__ == "__main__":
    try:
        phset = ttslab.fromfile(PHONESETFN)
    except IOError:
        print("Could not find file: '%s'" % (PHONESETFN))

    #get all feature categories:
    categories = set()
    for phn in phset.phones:
        categories.update(phset.phones[phn])

    #get feature categories involving vowels:
    vcategories = set()
    for phn in phset.phones:
        if "vowel" in phset.phones[phn]:
            vcategories.update(phset.phones[phn])

    #do all contexts:
    for context in ALL_CONTEXTS:
        for cat in categories:
            phonelist = [phset.map[phn] for phn in phset.phones if cat in phset.phones[phn]]
            if len(phonelist) > 1:
                print('QS "%s" {%s}' % ("-".join([context, cat]), ",".join([ALL_CONTEXTS[context] % phone for phone in phonelist])))
        for phone in [phset.map[phn] for phn in phset.phones]:
            print('QS "%s" {%s}' % ("-".join([context, phone]), ALL_CONTEXTS[context] % phone))

    print()
    # do vowel contexts:
    for context in VOWEL_CONTEXTS:
        for cat in vcategories:
            phonelist = [phset.map[phn] for phn in phset.phones if cat in phset.phones[phn] and "vowel" in phset.phones[phn]]
            if len(phonelist) > 1:
                print('QS "%s" {%s}' % ("_".join([context, cat]), ",".join([VOWEL_CONTEXTS[context] % phone for phone in phonelist])))
        for vowel in [phset.map[phn] for phn in phset.phones if "vowel" in phset.phones[phn]]:
            print('QS "%s" {%s}' % ("_".join([context, vowel]), VOWEL_CONTEXTS[context] % vowel))
