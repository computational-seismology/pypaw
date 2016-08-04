#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Filter the window based on the sensor type. For example, in long
period band(90-250s), we want to keep only STS-1 instrument windows.
For the input file, it requires 1) sensor type as json file; 2) windows
as json file. For the output, it is going to replace the origin window file
and keep a copy of original windows as "***.origin.json"

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (absolute_import, division, print_function)

import os
import argparse
from .utils import load_json, dump_json


def filter_windows(windows, stations, sensor_types, verbose=False):
    nchans_old = 0
    nchans_new = 0
    nwins_old = 0
    nwins_new = 0
    new_wins = {}

    if verbose:
        print("channel name             |" + " " * 30
              + "sensor type |   pick flag |   windows | total windows |")
    for sta, sta_info in windows.iteritems():
        sta_wins = {}
        for chan, chan_info in sta_info.iteritems():
            pick_flag = False
            nwins_old += len(chan_info)
            if len(chan_info) > 0:
                nchans_old += 1
            if len(chan_info) == 0:
                continue
            try:
                # since windows are on RTZ component and
                # instruments are on NEZ compoennt, so
                # just use Z component instrument information
                zchan = chan[:-1] + "Z"
                _st = stations[zchan]["sensor"]
            except:
                continue
            for stype in sensor_types:
                if stype in _st:
                    nchans_new += 1
                    nwins_new += len(chan_info)
                    sta_wins[chan] = chan_info
                    pick_flag = True
                    break
            if verbose:
                print("channel(%15s) | %40s | %11s | %9s | %12d |"
                      %(chan, _st[:40], pick_flag, len(chan_info), nwins_new))
        if len(sta_wins) > 0:
            new_wins[sta] = sta_wins

    print("Number of channels old and new: %d --> %d"
          % (nchans_old, nchans_new))
    print("Number of windows old and new:  %d --> %d"
          % (nwins_old, nwins_new))
    return new_wins


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    paths = load_json(args.path_file)
    window_file = paths["window_file"]
    station_file = paths["station_file"]
    sensor_types = paths["sensor_types"]
    output_file = paths["output_file"]

    print("window file: %s" % window_file)
    print("station_file: %s" % station_file)
    print("sensor types: %s" % sensor_types)
    print("output filtered window file: %s" % output_file)

    windows = load_json(window_file)
    stations = load_json(station_file)

    # filter the window based on given sensor types
    windows_new = filter_windows(windows, stations, sensor_types,
                                 verbose=args.verbose)

    # dump the new windows file to replace the original one
    dump_json(windows_new, output_file)


if __name__ == "__main__":
    main()
