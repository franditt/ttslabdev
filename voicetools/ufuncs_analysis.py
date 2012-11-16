# -*- coding: utf-8 -*-
""" Implements a number of functions used to analyse utterances
    (research purposes)...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import shutil, os
from tempfile import mkdtemp
from collections import OrderedDict

import ttslab
from ttslab.trackfile import Track
ttslab.extend(Track, "tfuncs_analysis")
import speechlabels as sl

NONE_WORD = "NONE"
WAV_EXT = "wav"
FEAT_EXT = "featvecs"
TEXTGRID_EXT = "TextGrid"

SIG2FV = "sig2fv -coefs melcep -delta melcep -melcep_order 12 -fbank_order 24 -shift 0.005 -factor 5.0 -preemph 0.97 -otype est %(inputfile)s -o %(outputfile)s"


def fill_startendtimes(utt):
    """ Use 'end' time feature in segments to fill info for other
        items in other common relations..
    """
    #segments (are contiguous in time)...
    currtime = 0.0
    for seg_item in utt.get_relation("Segment"):
        seg_item["start"] = currtime
        currtime = seg_item["end"]

    for syl_item in utt.get_relation("Syllable"):
        syl_item["start"] = syl_item.get_item_in_relation("SylStructure").first_daughter["start"]
        syl_item["end"] = syl_item.get_item_in_relation("SylStructure").last_daughter["end"]

    for word_item in utt.get_relation("Word"):
        word_item["start"] = word_item.get_item_in_relation("SylStructure").first_daughter["start"]
        word_item["end"] = word_item.get_item_in_relation("SylStructure").last_daughter["end"]

    for phrase_item in utt.get_relation("Phrase"):
        phrase_item["start"] = phrase_item.first_daughter["start"]
        phrase_item["end"] = phrase_item.last_daughter["end"]


def populate_items_relationwide(utt, track, featname, relation="Segment"):
    """ Extracts segments from track and adds as features to items in specific relation...
    """
    try:
        for item in utt.get_relation(relation):
            item[featname] = track.slice(track.index_at(item["start"]), track.index_at(item["end"]) + 1, copy=False)
    except:
        utt.fill_startendtimes()
        for item in utt.get_relation(relation):
            item[featname] = track.slice(track.index_at(item["start"]), track.index_at(item["end"]) + 1, copy=False)


def apply_items_relationwide(utt, func, featname, relation="Segment"):
    """ Applies 'func' to each item in 'relation' saving the
        result as 'featname'
    """
    for item in utt.get_relation(relation):
        item[featname] = func(item)


def utt_distance(utt, utt2, method="dtw", metric="euclidean", sig2fv=SIG2FV, VI=None):
    """ Uses Trackfile class' distance measurements to compare utts...
        See docstring in tfuncs_analysis.py for more details...
    """

    temppath = mkdtemp()

    #wavs
    wfn1 = os.path.join(temppath, "1." + WAV_EXT)
    wfn2 = os.path.join(temppath, "2." + WAV_EXT)
    utt["waveform"].write(wfn1)
    utt2["waveform"].write(wfn2)
    #feats
    ffn1 = os.path.join(temppath, "1." + FEAT_EXT)
    ffn2 = os.path.join(temppath, "2." + FEAT_EXT)
    cmds = SIG2FV % {"inputfile": wfn1,
                     "outputfile": ffn1}
    #print(cmds)
    os.system(cmds)
    cmds = SIG2FV % {"inputfile": wfn2,
                     "outputfile": ffn2}
    #print(cmds)
    os.system(cmds)

    #tracks
    t1 = Track()
    t1.load_track(ffn1)
    t2 = Track()
    t2.load_track(ffn2)

    #compare and save
    t3 = t1.distances(t2, method=method, metric=metric, VI=VI)

    shutil.rmtree(temppath)

    return t3


def utt2tiers(utt):
    """ Creates 'tiers' dict for use by speechlabels.writeTextgrid...
    """
    uttendtime = utt.get_relation("Segment").tail_item["end"]

    tiers = OrderedDict()

    for relname in ["Segment", "Syllable", "Word", "Phrase"]:
        lastendtime = 0.0
        entries = []
        for item in utt.get_relation(relname):
            try:
                if item["start"] != lastendtime:
                    entries.append([str(item["start"]), NONE_WORD])
                entries.append([str(item["end"]), item["name"]])
                lastendtime = item["end"]
            except KeyError:
                pass
        if entries:
            if float(entries[-1][0]) != uttendtime:
                entries.append([str(uttendtime), NONE_WORD])
            tiers[relname.lower()] = entries
    #also add text:
    tiers["text"] = [[str(uttendtime), utt["text"]]]

    return tiers


def write_textgrid(utt, tgfname=None):
    """ Writes a TextGrid from item endtimes..
    """
    if tgfname is None:
        tgfname = ".".join([utt["file_id"], TEXTGRID_EXT])
    sl.Utterance.writeTextgrid(tgfname, utt.utt2tiers())
