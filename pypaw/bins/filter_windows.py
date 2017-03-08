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
from pprint import pprint
from pytomo3d.window.filter_windows import filter_windows, count_windows
from .utils import load_json, dump_json, load_yaml


def check_keys(dictv, keys):
    set1 = set(dictv.keys())
    set2 = set(keys)
    if set1 != set2:
        print("Missing keys: %s" % (set2 - set1))
        print("Redundant keys: %s" % (set1 - set2))
        return False
    return True


def check_path(paths):
    keys = ["window_file", "station_file", "output_file", "measurement_file"]
    if not check_keys(paths, keys):
        raise ValueError("Path file is bad!")

    print("=" * 10 + " Path info " + "=" * 10)
    pprint(paths)


def check_param(params):
    keys = ["sensor", "measurement"]
    if not check_keys(params, keys):
        raise ValueError("Param file is bad!")

    keys = ["flag", "sensor_types"]
    if not check_keys(params["sensor"], keys):
        raise ValueError("Param['sensor'] is bad!")

    keys = ["flag", "component"]
    if not check_keys(params["measurement"], keys):
        raise ValueError("Param['measurement'] is bad!")

    print("=" * 10 + " Path info " + "=" * 10)
    pprint(params)


def assert_windows_and_measurements_same_length(windows, measures):
    if len(windows) != len(measures):
        raise ValueError("Length of windows and measures are not the same!")
    for sta in windows:
        if len(windows[sta]) != len(measures[sta]):
            raise ValueError("Length of windows and measures fails at "
                             "station level: %s" % sta)
        for chan in windows[sta]:
            if len(windows[sta][chan]) != len(measures[sta][chan]):
                raise ValueError("Length of windows and measures fails at: "
                                 "channel level: %s" % chan)


def run_window_filter(paths, params, verbose=False):
    check_path(paths)
    check_param(params)

    window_file = paths["window_file"]
    station_file = paths["station_file"]
    output_file = paths["output_file"]
    measurement_file = paths["measurement_file"]

    windows = load_json(window_file)
    # count the number of windows in the original window file
    nchans_old, nwins_old, nwins_comp_old = count_windows(windows)
    stations = load_json(station_file)
    measurements = load_json(measurement_file)

    # filter the window based on given sensor types
    windows_new, measures_new, log = filter_windows(
        windows, stations, measurements, params, verbose=verbose)

    nchans_new, nwins_new, nwins_comp_new = count_windows(windows_new)

    assert_windows_and_measurements_same_length(windows_new, measures_new)
    print("=" * 10 + " Summary " + "=" * 10)
    print("channels: %d --> %d" % (nchans_old, nchans_new))
    print("windows: %d -- > %d" % (nwins_old, nwins_new))
    print("Old component windows: %s" % (nwins_comp_old))
    print("New component windows: %s" % (nwins_comp_new))

    # dump the new windows file to replace the original one
    print("Filtered window files: %s" % output_file)
    dump_json(windows_new, output_file)

    new_measure_file = measurement_file + ".filter"
    print("Filtered measurement file: %s" % new_measure_file)
    dump_json(measures_new, new_measure_file)

    # dump the log file
    logfile = os.path.join(os.path.dirname(output_file), "filter.log")
    print("Log file located at: %s" % logfile)
    dump_json(log, logfile)


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

    run_window_filter(paths, params, verbose=args.verbose)


if __name__ == "__main__":
    main()
