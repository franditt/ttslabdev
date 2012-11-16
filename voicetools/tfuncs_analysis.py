# -*- coding: utf-8 -*-
""" Some functions operating on Track objects for research purposes...
"""
from __future__ import unicode_literals, division, print_function #Py2

__author__ = "Daniel van Niekerk"
__email__ = "dvn.demitasse@gmail.com"

import numpy as np
from scipy.spatial.distance import cdist

from ttslab.trackfile import Track

def dtw_align(track, track2, metric="euclidean", VI=None):
    """DP alignment between tracks....
       Returns: cumdist, dist, path (corresponding sample indices)

       The functionality is based on the distance implementations
       available in scipy.spatial.distance.cdist thus refer to
       this documentation for explanation of function args...
    """

    assert track.numchannels == track2.numchannels, "Tracks don't have the same number of channels..."

    dpp = np.zeros((track.numframes, track2.numframes), dtype=int)
    cumdist = cdist(track.values, track2.values, metric=metric, VI=VI)
    dist = np.array(cumdist)

    dpp[0][0] = -1

    for i in range(1, track.numframes):
        cumdist[i][0] += cumdist[i-1][0]
        dpp[i][0] = -1

    for i in range(1, track2.numframes):
        cumdist[0][i] += cumdist[0][i-1]
        dpp[0][i] = 1

    for i in range(1, track.numframes):
        for j in range(1, track2.numframes):
            if cumdist[i-1][j] < cumdist[i-1][j-1]:
                if cumdist[i][j-1] < cumdist[i-1][j]:
                    cumdist[i][j] += cumdist[i][j-1]
                    dpp[i][j] = 1   #hold
                else: #horizontal best
                    cumdist[i][j] += cumdist[i-1][j]
                    dpp[i][j] = -1  #jump
            elif cumdist[i][j-1] < cumdist[i-1][j-1]:
                cumdist[i][j] += cumdist[i][j-1]
                dpp[i][j] = 1       #hold
            else:
                cumdist[i][j] += cumdist[i-1][j-1]
                dpp[i][j] = 0       #jump

    mapping = np.zeros(track.numframes, dtype=int)
    cost = -1
    j = track2.numframes - 1
    for i in range(track.numframes - 1, -1, -1): #n-1 downto 0
        if cost == -1:
            cost = cumdist[i][j]
        mapping[i] = j
        while dpp[i][j] == 1:
            j -= 1
        if dpp[i][j] == 0:
            j -= 1

    path = []
    for i, c in enumerate(mapping):
        if i == 0:
            path.append((i, c))
            continue
        repeating = range(path[-1][-1], c)
        if repeating:
            path.pop()
            for j in repeating:
                path.append((i-1, j))
        path.append((i, c))

    return cumdist, dist, path


def dtw_distances(track, track2, metric="euclidean", VI=None):

    cumdist, dist, path = track.dtw_align(track2, metric=str(metric), VI=VI)

    framedists = []
    frametimes = []
    for pathcoord in path:
        x, y = pathcoord
        framedists.append(dist[x][y])
        frametimes.append(track.times[x])

    t = Track()
    t.values = np.array(framedists)
    t.values = t.values.reshape(-1, 1)
    t.times = np.array(frametimes)
    
    return t


def linearpath_distances(track, track2, metric="euclidean", VI=None):

    dist = cdist(track.values, track2.values, metric=str(metric), VI=VI)
    framedists = []
    try:
        for i in range(len(track.times)):
            framedists.append(dist[i][i])
    except IndexError:
        pass
    t = Track()
    t.values = np.array(framedists)
    t.values = t.values.reshape(-1, 1)
    t.times = np.array([track.times[i] for i in range(len(t.values))])
    if track2.numframes != track.numframes:
        print("linearpath_distances: WARNING: num frames difference is %s" % (track2.numframes - track.numframes))
    return t


def distances(track, track2, method="dtw", metric="euclidean", VI=None):

    if method == "dtw":
        return track.dtw_distances(track2, metric=metric, VI=VI)
    if method == "linear":
        return track.linearpath_distances(track2, metric=metric, VI=VI)
    else:
        raise NotImplementedError("method: " + method)


def mask_indices(track, intervals):
    """ return indices falling within intervals:
        [[starttime, endtime], [starttime, endtime], ...]
    """
    indices = np.array([], dtype=int)
    for interval in intervals:
        ca = track.times >= interval[0]
        cb = track.times < interval[1]
        indices = np.append(indices, np.nonzero(ca & cb))
        #indices.extend([e[1] for e in zip(track.times, range(len(track.times))) if e[0] >= interval[0] and e[0] < interval[1]])
    return indices
