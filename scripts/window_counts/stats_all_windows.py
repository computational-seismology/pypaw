#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Methods that stats the number of windows in each category

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division
import os
import json
import argparse
import sys


def count_to_weight(wcount):
    weight = wcount.copy()
    for period, pinfo in wcount.iteritems():
        for comp in pinfo:
            weight[period][comp] = 1.0 / weight[period][comp]
    return weight


def write_weight(results, outputfn):
    weight = count_to_weight(results)
    with open(outputfn, 'w') as fh:
        json.dump(weight, fh, indent=2, sort_keys=True)


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def parse_one_file(window_file):
    info = {}
    if not os.path.exists(window_file):
        raise ValueError("File not exists: %s" % window_file)
    content = load_json(window_file)
    for key in content:
        if key[2] in ["Z", "R", "T"] and len(key) == 3:
            info[key] = content[key]["window"]
    return info


def stats_windows(path):
    count = {}
    for eventname, event_info in path.iteritems():
        for period, window_file in event_info.iteritems():
            if period not in count:
                count[period] = {}
            content = parse_one_file(window_file)
            # print("content:", content)
            for comp in content:
                if comp not in count[period]:
                    count[period][comp] = 0
                count[period][comp] += content[comp]
            # print("count:", count)
    return count


def write_output(results, outputfn):
    if os.path.exists(outputfn):
        print("Output file exists:%s" % outputfn)
        answer = raw_input("Removed[Y/n]:")
        if answer == "Y":
            os.remove(outputfn)
        elif answer == "n":
            sys.exit()
        else:
            raise ValueError("Answer not understood!")

    with open(outputfn, 'w') as fh:
        json.dump(results, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="input window path file")
    parser.add_argument('-o', action='store', dest='outputfn',
                        default="windows.stats.json",
                        help="filename for output window count")
    parser.add_argument('-w', action='store', dest='output_weight',
                        default="windows.stats.weight.json",
                        help="filename for output weight")
    args = parser.parse_args()

    path = load_json(args.path_file)
    results = stats_windows(path)

    write_output(results, args.outputfn)
    write_weight(results, args.output_weight)
