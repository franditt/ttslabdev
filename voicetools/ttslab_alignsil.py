#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Performs automatic phonetic alignment using ttslab as text
    analysis frontend...

    DEMITASSE: THIS NEEDS A SERIOUS REWRITE...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import os
import sys
import codecs
import re
import signal
import shutil
from tempfile import mkstemp, mkdtemp
from glob import glob
from collections import defaultdict

import ttslab
from ttslab.waveform import Waveform
from HAlign2sil import GenHAlign, GenHAlignRealign
import speechlabels as sl

#sometimes the limit needs to be increased to pickle large utts...
sys.setrecursionlimit(10000) #default is generally 1000

ETC_DIR = "etc"
TRANSCR_FILE = "utts.data"
HALIGNCONF_FILE = "halign.conf"
WAV_DIR = "wavs"
HALIGNWORK_DIR = "halign"
HALIGNINPUT_SUBDIR = "input"
HALIGNINPUTTRANSCR_DIR = "trancr"
TEXTGRID_DIR = "textgrids"
ALIGNED_UTT_DIR = "utts"
LAB_EXT = "lab"
DICT_EXT = "dict"
UTT_EXT = "utt.pickle"

NONE_WORD = "NONE"

HTK_SPEC_CHARS = "'" #characters that need to be escaped a start of
                     #words in HTK dicts: this is incomplete at the
                     #moment...

########################################
## MANAGE TEMPFILES
TEMPS = []
def cleanup_temps(signal, frame):
    """ Make sure temp dirs and files are removed...
    """
    for temp in TEMPS:
        if os.path.isfile(temp):
            os.remove(temp)
        elif os.path.isdir(temp):
            shutil.rmtree(temp)
        else:
            pass
signal.signal(signal.SIGHUP, cleanup_temps)
signal.signal(signal.SIGINT, cleanup_temps)
signal.signal(signal.SIGQUIT, cleanup_temps)
signal.signal(signal.SIGTERM, cleanup_temps)

def make_tempdir(prefix='', suffix=''):
    tempdir = mkdtemp(prefix=prefix, suffix=suffix)
    TEMPS.append(tempdir)
    return tempdir

def make_tempfile(prefix='', suffix=''):
    fd, tempfile = mkstemp(prefix=prefix, suffix=suffix)
    TEMPS.append(tempfile)
    #we're leaking file descriptors here but don't care...
    return tempfile


########################################
## SIMPLE FUNCTIONS
def load_transcriptions_schemefile(filepath):
    """ Load from festival style transcriptions file...
    """
    quoted = re.compile('".*"')
    bracketed = re.compile('\(.*\)')

    wordlevel = {}

    with codecs.open(filepath, "r", encoding="utf-8") as infh:
        lines = infh.readlines()

    for line in lines:
        transcr = quoted.search(line).group().strip("\"")
        whatsleft = re.sub(quoted, "", line)
        key = bracketed.search(whatsleft).group().strip("(").strip(")").strip()
        if key in wordlevel:
            raise Exception("Non unique utterance names present...")
        wordlevel[key] = transcr

    return wordlevel


def get_2tiers_from_utt(voice, utt):
    """ Inserting closures here... Closure insertion should actually be
        implemented as an Utterance processor one day...
    """
    phmap = voice.phonemap
    word_seg_structure = []
    wordcounter = 0

    firstseg = utt.get_relation("Segment").head_item
    firstword = utt.get_relation("Word").head_item

    seg_iter = firstseg
    word_iter = firstword

    while seg_iter is not None:
        if not seg_iter.in_relation("SylStructure"):
            wordfield = "_".join([NONE_WORD, str(wordcounter).zfill(3)])
            word_seg_structure.append([wordfield, [seg_iter["name"]]])
        else:
            try:
                if "_" in word_iter["name"]:
                    print("WARNING: Underscore in word representation (%s: %s)" % (utt["file_id"], utt["text"]))
            except KeyError:
                pass #DEMITASSE
            wordfield = "_".join([word_iter["name"], str(wordcounter).zfill(3)])
            word_seg_structure.append([wordfield, []])
            syl_iter = seg_iter.get_item_in_relation("SylStructure").parent_item
            while syl_iter is not None:
                seg_iter_sylstruct = syl_iter.first_daughter
                while seg_iter_sylstruct is not None:
                    #insert closure - this should actually also check for preceding nasal...
                    if ("manner_affricate" in voice.phones[seg_iter_sylstruct["name"]] or
                        "manner_plosive"  in voice.phones[seg_iter_sylstruct["name"]] or
                        "manner_click" in voice.phones[seg_iter_sylstruct["name"]]):
                        word_seg_structure[-1][1].append(phmap[voice.phoneset.features["closure_phone"]])
                    word_seg_structure[-1][1].append(phmap[seg_iter_sylstruct["name"]])
                    last_valid_seg = seg_iter_sylstruct
                    seg_iter_sylstruct = seg_iter_sylstruct.next_item
                syl_iter = syl_iter.next_item

            seg_iter = last_valid_seg.get_item_in_relation("Segment")
            word_iter = word_iter.next_item

        wordcounter += 1
        seg_iter = seg_iter.next_item

    return word_seg_structure


def transplant_segtime_info(voice, sc_utt, utt):
    
    phmap = voice.phonemap

    seg_iter = utt.get_relation("Segment").head_item
    index = 0

    while seg_iter is not None:
        if sc_utt.entries[index][1] == phmap[voice.phoneset.features["closure_phone"]]:
            index += 1
        if phmap[seg_iter["name"]] == sc_utt.entries[index][1]:
            seg_iter["end"] = float(sc_utt.entries[index][0])
        else:
            raise Exception("Segment sequence missmatch...")
        seg_iter = seg_iter.next_item
        index += 1

    return utt


# def add_sylls_to_textgrid(voice, sc_utt, utt):
#     """ Add syllable tier to TextGrid based on Utterance
#         SylStructure...
#     """

#     utt = transplant_segtime_info(voice, sc_utt, utt)

#     tiers = dict(sc_utt.tiers)
#     syltier = []
    
#     #add sylls from utt...
#     syl_iter = utt.get_relation("Syllable").head_item
#     while syl_iter is not None:
#         try:
#             last_seg = syl_iter.get_item_in_relation("SylStructure").last_daughter
#             syltier.append([last_seg["end"], syl_iter["name"]])
#             syl_iter = syl_iter.next_item
#         except TypeError:
#             print(utt["file_id"])
#             print("\n".join(syl_iter.get_item_in_relation("SylStructure").parent_item.toStringLines()))
#             raise Exception
    
#     #add NONE_WORD placeholders where segs are not part of a syllable...
#     seg_iter = utt.get_relation("Segment").head_item
#     while seg_iter is not None:
#         if not seg_iter.get_item_in_relation("SylStructure"):
#             syltier.append([seg_iter["end"], NONE_WORD])
#         seg_iter = seg_iter.next_item

#     #sort according to end times...
#     syltier.sort(key=lambda x: x[0])
    
#     tiers["syllable"] = syltier

#     return tiers


def add_sylls_to_textgrid(voice, sc_utt):
    """ Reconstruct syllable tier by getting segments based on word
        alignments and re-running voice's syllabification algorithm on
        (potentially) new pronunciations...
    """
    
    #get phoneset map and invert to map back to native representations
    #in order to use phoneset's syllabify method...
    phonemap = dict((v, k) for k, v in voice.phonemap.items())

    words = sc_utt.tiers["word"]
    segs = sc_utt.tiers["segment"]

    #Once we activate the SIL detection code in HAlign, we need to add code here to postprocess these SILs: TODO!
    # - remove spurious short SILs
    # - seperate SILs from words...
    # - make sure these segments don't get in the way when re-determining the sylls...
    tiers = dict(sc_utt.tiers)
    syltier = []
    for prevword, word in zip([[0.0, None]] + words, words):
        if word[1] != NONE_WORD:
            segsword = [seg for seg in segs if
                        float(seg[0]) > float(prevword[0]) and float(seg[0]) <= float(word[0])
                        and seg[1] != voice.phoneset.features["closure_phone"]]
            phones = [phonemap[phone[1]] for phone in segsword]
            if not any([ph.startswith("eng_") for ph in phones]):
                sylls = voice.phoneset.syllabify(phones)
            else:
                phoness = []
                for ph in phones:
                    if not ph.startswith("eng_"):
                        phoness.append("eng_" + ph)
                    else:
                        phoness.append(ph)
                phones = phoness
                sylls = voice.engphoneset.syllabify([ph[4:] for ph in phones])   #removing "eng_" ...
                for syl in sylls:
                    for i in range(len(syl)):
                        syl[i] = "eng_" + syl[i]                                 #... and adding back
            syllens = [len(syl) for syl in sylls]
            for syllen in syllens:
                syltier.append([segsword[syllen - 1][0], "syl"])
                segsword = segsword[syllen:]
        else:
            syltier.append([word[0], NONE_WORD])

    #sort according to end times...
    #syltier.sort(key=lambda x: x[0])
    
    tiers["syllable"] = syltier

    return tiers
        
    


def complete_utt_from_textgrid(voice, sc_utt, utt):
    """ Take 3-tier TextGrid and Utterance completed up to
        Words relation and fill in Syllables, SylStructure and
        Segments relations from edited TextGrid
        
        Entries in tiers must be sorted according to time...
    """
    phmap = dict([[v,k] for k,v in voice.phonemap.items()])
    silence_phone = voice.phoneset.features["silence_phone"]
    
    #assert words match between both sources...
#    try:
    word_iter = utt.get_relation("Word").head_item
    for word in sc_utt.tiers["word"]:
        if word[1] == NONE_WORD:
            continue
        print(" == ".join([word_iter["name"], word[1]]))
        if word_iter["name"] != word[1]:
            print("WARNING: Apparent word sequence missmatch")
        word_iter = word_iter.next_item
#    except AssertionError:
#        raise Exception("Word sequence missmatch...")
        
    #create relations and transplant items...
    syl_rel = utt.new_relation("Syllable")
    seg_rel = utt.new_relation("Segment")
    sylstruct_rel = utt.new_relation("SylStructure")

    closure_end = None
    word_starttime = 0.0
    word_iter = utt.get_relation("Word").head_item
    for word in sc_utt.tiers["word"]:
        word_endtime = float(word[0])
        if word[1] == NONE_WORD:
            #add segments directly to seg_rel...
            for seg in sc_utt.tiers["segment"]:
                if float(seg[0]) > word_starttime and float(seg[0]) <= word_endtime:
                    seg_item = seg_rel.append_item()
                    seg_item["name"] = phmap[seg[1]]
                    seg_item["end"] = float(seg[0])
        else:
            if word[1] != word_iter["name"]:
                print("WARNING: Apparent word sequence missmatch")
            #add syls to sylstruct_rel and syl_rel...
            word_sylstruct = sylstruct_rel.append_item(word_iter)
            syl_starttime = word_starttime
            for syl in sc_utt.tiers["syllable"]:
                syl_endtime = float(syl[0])
                if syl_endtime > word_starttime and syl_endtime <= word_endtime:
                    syl_item = syl_rel.append_item()
                    syl_item["name"] = syl[1]
                    syl_sylstruct = word_sylstruct.add_daughter(syl_item)
                    #add segs to sylstruct and seg_rel...
                    for seg in sc_utt.tiers["segment"]:
                        if float(seg[0]) > syl_starttime and float(seg[0]) <= syl_endtime:
                            if seg[1] == voice.phoneset.features["closure_phone"]:
                                closure_end = seg[0]
                                continue
                            seg_item = seg_rel.append_item()
                            seg_item["name"] = phmap[seg[1]]
                            seg_item["end"] = float(seg[0])
                            if closure_end is not None:
                                seg_item["cl_end"] = float(closure_end)
                                closure_end = None
                            if seg[1] != silence_phone:
                                seg_sylstruct = syl_sylstruct.add_daughter(seg_item)
                syl_starttime = syl_endtime
            word_iter = word_iter.next_item
        word_starttime = word_endtime
                
    return utt



########################################
## BATCH FUNCTIONS
def make_halign_input(voice, utts, halign_working_dir):
    """ Make 2-tier HAlign source from utts...

        Makes dict with variants if alternative utts found in utts.

        TODO HERE: seperate SILs at the start of words...DEMITASSE
    """
    pronundict = defaultdict(list)

    transcrdir = os.path.join(halign_working_dir, HALIGNINPUT_SUBDIR, HALIGNINPUTTRANSCR_DIR)
    outdictfilelocation = os.path.join(halign_working_dir, HALIGNINPUT_SUBDIR, "wordinstances" + "." + DICT_EXT)

    for i, utt in enumerate(utts):
        tiers = get_2tiers_from_utt(voice, utt)
        #add words to dict...
        for item in tiers:
            word = item[0]
            #add escapes where necessary:
            if any([word.startswith(c) for c in HTK_SPEC_CHARS]): #HTK_SPEC_CHARS is not currently complete!
                word = "\\" + word
            wordinstance = "_".join([word, str(i).zfill(4)])
            pronundict[wordinstance].append(item[1])
        #save orthographic label file...
        with codecs.open(os.path.join(transcrdir, ".".join([utt["file_id"], LAB_EXT])), 'w', encoding="utf-8") as outfh:
            outfh.write("\n".join(["_".join([item[0], str(i).zfill(4)]) for item in tiers]) + "\n")

        #if alt_utts: add pronunciations from there if they do not
        #agree with what already exists. We preserve order of entry
        #deliberately because the idea that alt_utts are really
        #"non-standard" variations/dialects - thus we want those
        #entries to follow the standard in the HTK dict.
        #DEMITASSE: THIS CODE RELIES ON THE FACT THAT WORDS IN WORD RELATION CORRESPOND EXACTLY!
        try:
            for u in utt["alt_utts"].values():
                tiers = get_2tiers_from_utt(voice, u)
                for item in tiers:
                    word = item[0]
                    #add escapes where necessary:
                    if any([word.startswith(c) for c in HTK_SPEC_CHARS]): #HTK_SPEC_CHARS is not currently complete!
                        word = "\\" + word
                    wordinstance = "_".join([word, str(i).zfill(4)])
                    if item[1] not in pronundict[wordinstance]:
                        pronundict[wordinstance].append(item[1])
        except AttributeError:
            pass #alt_utts not found...

    #save pronundictionary to file...
    with codecs.open(outdictfilelocation, "w", encoding="utf-8") as outfh:
        for word, entry in sorted(pronundict.items()):
            for variant in entry:
                outfh.write(" ".join([word, " ".join(variant)]) + "\n")

    return transcrdir, outdictfilelocation


def make_base_utts(voice, transcriptions):
    """ Step through all the relevant NLP modules of the voice to
        generate structure for alignment...
    """

    utts = []

    for uttname in sorted(transcriptions):
        print("Synthesizing:", uttname)
        utt = voice.synthesize(transcriptions[uttname], 'text-to-segments')
        utt["file_id"] = uttname
        utts.append(utt)

    return utts


def add_sylls_to_textgrids(voice, sc_corpus, output_dir):
    """ Add syllables from utterance structure to TextGrids...
    """

    for sc_utt in sc_corpus.utterances:
        # for utt in utts:
        #     if utt["file_id"] == sc_utt.name:
        tiers = add_sylls_to_textgrid(voice, sc_utt)

        sl.Utterance.writeTextgrid(os.path.join(output_dir, sc_utt.filename), tiers)


def make_aligned_utts(voice, transcriptions, sc_corpus, wav_dir, output_dir):
    """ Make Word level utts and complete from 3-tier TextGrids...
    """
    def copyuttfeats(u, u2):
        for relname in ["Word", "Syllable"]:
            items = u.gr(relname).as_list()
            items2 = u2.gr(relname).as_list()
            assert [i["name"] for i in items] == [i2["name"] for i2 in items2]
            for i, i2 in zip(items, items2):
                for k in i2:
                    if not k in i:
                        i[k] = i2[k]
        return u

    for sc_utt, uttname, wavfilename in zip(sc_corpus.utterances, sorted(transcriptions), sorted(glob(os.path.join(wav_dir, "*")))):
        assert sc_utt.name == uttname, "Utterance missmatch..."
        assert os.path.basename(wavfilename).startswith(uttname), "Utterance missmatch..."

        print("Synthesizing:", uttname)
        utt = voice.synthesize(transcriptions[uttname], 'text-to-words')
        utt["file_id"] = uttname

        utt = complete_utt_from_textgrid(voice, sc_utt, utt)
        utt2 = voice.synthesize(transcriptions[uttname], 'text-to-segments')
        try:
            utt = copyuttfeats(utt, utt2)
        except AssertionError:
            print("WARNING: could not copy item feats for %s" % utt["file_id"])

        #add waveform to utt:
        utt["waveform"] = Waveform(wavfilename)

        #save utt...
        ttslab.tofile(utt, os.path.join(output_dir, ".".join([uttname, UTT_EXT])))


########################################
## MAIN PROCEDURES

def to_textgrid(voice):
    """ Should pull Word and Segment info from set of utterances make
        input compatible with HAlign2 (align from orthography), and
        run alignment process to make a set of TextGrid files
        including Syllables...
        
        or 

        Should pull Word and Segment info from a special set of
        utterances where alternative utts are embedded. Makes input
        compatible with HAlign2 (align from orthography) with
        dictionary containing variants, and run alignment process
        (with re-alignment stage) to make a set of TextGrid files
        including Syllables...
    """
    
    #create necessary output dirs...
    CWD = os.getcwd()
    wav_dir                  = os.path.join(CWD, WAV_DIR)
    transcr_location         = os.path.join(CWD, ETC_DIR, TRANSCR_FILE)
    halign_config_location   = os.path.join(CWD, ETC_DIR, HALIGNCONF_FILE)

    halign_working_dir       = os.path.join(CWD, HALIGNWORK_DIR)
    halign_input_transcr_dir = os.path.join(halign_working_dir, HALIGNINPUT_SUBDIR, HALIGNINPUTTRANSCR_DIR)
    textgrid_dir             = os.path.join(CWD, TEXTGRID_DIR)

    os.makedirs(textgrid_dir)
    os.makedirs(halign_input_transcr_dir)

    #get silence phone..
    silence_phone = voice.phoneset.features["silence_phone"]

    #start alignment process..
    transcriptions = load_transcriptions_schemefile(transcr_location)

    utts = make_base_utts(voice, transcriptions)

    halign_input_transcr_dir, pronundict_location = make_halign_input(voice, utts, halign_working_dir)

    # if not any("alt_utts" in u for u in utts):
    #     GenHAlign(halign_config_location,
    #               overrides={"SOURCE:ORTHOGRAPHIC_TRANSCRIPTIONS" : halign_input_transcr_dir,
    #                          "SOURCE:PRONUNCIATION_DICTIONARY" : pronundict_location,
    #                          "SOURCE:AUDIO" : wav_dir,
    #                          "PARMS:WORKING_DIR" : halign_working_dir,
    #                          "PARMS:SILENCE_PHONE" : silence_phone})
    # else:
    GenHAlignRealign(halign_config_location,
                     overrides={"SOURCE:ORTHOGRAPHIC_TRANSCRIPTIONS" : halign_input_transcr_dir,
                                "SOURCE:PRONUNCIATION_DICTIONARY" : pronundict_location,
                                "SOURCE:AUDIO" : wav_dir,
                                "PARMS:WORKING_DIR" : halign_working_dir,
                                "PARMS:SILENCE_PHONE" : silence_phone})
    
    alignments = sl.Corpus(os.path.join(halign_working_dir, "textgrids"))

    add_sylls_to_textgrids(voice, alignments, textgrid_dir)

    #cleanup...
    #shutil.rmtree(halign_input_transcr_dir)
    #os.remove(pronundict_location)


def from_textgrid(voice):
    """ Create aligned Utterances by synthesising to Word level from
        the orthography and filling in further SylStructure from the
        TextGrid input... 
        Normalised orthography must match for this to be successful...
    """
    #Setup and create necessary dirs...
    CWD = os.getcwd()
    wav_dir = os.path.join(CWD, WAV_DIR)
    transcr_location = os.path.join(CWD, ETC_DIR, TRANSCR_FILE)
    textgrid_dir = os.path.join(CWD, TEXTGRID_DIR)
    aligned_utts_dir = os.path.join(CWD, ALIGNED_UTT_DIR)
    
    os.makedirs(aligned_utts_dir)

    #correct utterances from textgrids...
    transcriptions = load_transcriptions_schemefile(transcr_location)

    alignments = sl.Corpus(textgrid_dir)

    make_aligned_utts(voice, transcriptions, alignments, wav_dir, aligned_utts_dir)


def alignments_from_textgrid(voice):
    """ Create aligned Utterances by synthesising to Segment level
        from the orthography and simply copying label end times into
        segment items as "end" feature.
    """
    #Setup and create necessary dirs...
    CWD = os.getcwd()
    wav_dir = os.path.join(CWD, WAV_DIR)
    transcr_location = os.path.join(CWD, ETC_DIR, TRANSCR_FILE)
    textgrid_dir = os.path.join(CWD, TEXTGRID_DIR)
    aligned_utts_dir = os.path.join(CWD, ALIGNED_UTT_DIR)
    
    os.makedirs(aligned_utts_dir)

    #update utts from textgrids...
    transcriptions = load_transcriptions_schemefile(transcr_location)

    alignments = sl.Corpus(textgrid_dir)

    #################
    for sc_utt, uttname, wavfilename in zip(alignments.utterances, sorted(transcriptions), sorted(glob(os.path.join(wav_dir, "*")))):
        assert sc_utt.name == uttname, "Utterance missmatch..."
        assert os.path.basename(wavfilename).startswith(uttname), "Utterance missmatch..."

        print("Synthesizing:", uttname)
        utt = voice.synthesize(transcriptions[uttname], 'text-to-segments')
        utt["file_id"] = uttname

        utt = transplant_segtime_info(voice, sc_utt, utt)

        #add waveform to utt:
        utt["waveform"] = Waveform(wavfilename)

        #save utt...
        ttslab.tofile(utt, os.path.join(aligned_utts_dir, ".".join([uttname, UTT_EXT])))


def auto(voice):
    """ Automatic alignment with no interaction...
    """
    #do alignments...
    to_textgrid(voice)
    #reconstruct utterances from textgrid...
    from_textgrid(voice)


class CLIException(Exception):
    pass

def main():

    try:
        try:
            voicefile = sys.argv[1]
            proc = sys.argv[2]
        except IndexError:
            raise CLIException

        voice = ttslab.fromfile(voicefile)
        
        if proc == "auto":
            auto(voice)
        elif proc == "to_textgrid":
            to_textgrid(voice)
        elif proc == "from_textgrid":
            from_textgrid(voice)
        elif proc == "alignments_from_textgrid":
            alignments_from_textgrid(voice)
        else:
            raise CLIException
    except CLIException:
        print("USAGE: ttslab_alignsil.py [VOICEFILE] [auto | to_textgrid | from_textgrid | alignments_from_textgrid]")
    

if __name__ == "__main__":
    main()
