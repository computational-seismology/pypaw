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
from pytomo3d.window import filter_windows
from .utils import load_json, dump_json, load_yaml


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-p', action='store', dest='param_file', required=True,
                        help="param file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    paths = load_json(args.path_file)
    params = load_yaml(args.param_file)

    window_file = paths["window_file"]
    station_file = paths["station_file"]
    output_file = paths["output_file"]
    measurement_file = paths["measurement_file"]

    print("window file: %s" % window_file)
    print("station_file: %s" % station_file)
    print("measurement_file: %s" % measurement_file)
    print("output filtered window file: %s" % output_file)

    windows = load_json(window_file)
    stations = load_json(station_file)
    measurements = load_json(measurement_file)

    # filter the window based on given sensor types
    windows_new, log = filter_windows(
        windows, stations, measurements, params, verbose=args.verbose)
    # dump the new windows file to replace the original one
    dump_json(windows_new, output_file)

    # dump the log file
    logfile = os.path.join(os.path.dirname(output_file), "filter.log")
    print("Log file located at: %s" % logfile)
    dump_json(log, logfile)


if __name__ == "__main__":
    main()
