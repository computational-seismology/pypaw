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


def filter_windows(windows, sensors, sensor_types, verbose=False):
    nchans_old = 0
    nchans_new = 0
    new_wins = {}
    for sta, sta_info in windows.iteritems():
        sta_wins = {}
        for chan, chan_info in sta_info.iteritems():
            nchans_old += len(chan_info)
            print(chan, nchans_old)
            if len(chan_info) == 0:
                continue
            try:
                _st = sensors[chan]
            except:
                continue
            for stype in sensor_types:
                if stype in _st:
                    nchans_new += len(chan_info)
                    sta_wins[chan] = chan_info
                    break
        if len(sta_wins) > 0:
            new_wins[sta] = sta_wins

    print("number of windows old and new: %d, %d" % (nchans_old, nchans_new))
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
    sensor_file = paths["sensor_file"]
    sensor_types = paths["sensor_types"]

    print("window file: %s" % window_file)
    print("sensor_file: %s" % sensor_file)
    print("sensor types: %s" % sensor_types)

    windows = load_json(window_file)
    sensors = load_json(sensor_file)

    # filter the window based on given sensor types
    windows_new = filter_windows(windows, sensors, sensor_types,
                                 verbose=args.verbose)

    # dump the new windows file to replace the original one
    window_file_filter = os.path.join(os.path.dirname(window_file),
                                      "windows.filter.json")
    dump_json(windows_new, window_file_filter)


if __name__ == "__main__":
    main()
