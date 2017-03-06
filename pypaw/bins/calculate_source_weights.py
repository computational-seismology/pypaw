#!/usr/bin/env pythoiin
# -*- coding: utf-8 -*-
"""
Calculate the adjoint source weighting based on the cmtsource
distribution.

This is the script working together with window weight
version I since in that script, only receiver and category
weightins are calculated.

The source weightings are then used in summing kernels from
different events.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import

import argparse
import matplotlib
matplotlib.use('Agg')  # NOQA
from obspy import read_events
from pytomo3d.source.source_weights import calculate_source_weights
from .utils import load_json, load_yaml, reset_matplotlib


def src_weights(path, param, _verbose=False):
    inputs = path["input"]
    output_file = path["output_file"]

    eventlist = inputs.keys()
    eventlist.sort()
    nevents = len(eventlist)
    print("Number of sources: %d" % nevents)

    # load the source information and window counts into memory
    info = {}
    for event in eventlist:
        cmt = read_events(inputs[event]["cmtfile"], format="CMTSOLUTION")
        window_counts = \
            load_json(inputs[event]["window_counts_file"])["windows"]
        info[event] = {"source": cmt, "window_counts": window_counts}

    calculate_source_weights(info, param, output_file, _verbose=_verbose)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-p', action='store', dest='param_file', required=True,
                        help="param file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    path = load_json(args.path_file)
    param = load_yaml(args.param_file)

    reset_matplotlib()
    src_weights(path, param, _verbose=args.verbose)


if __name__ == "__main__":
    main()
