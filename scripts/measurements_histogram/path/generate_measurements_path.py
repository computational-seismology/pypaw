#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate weights for each window based on the number of windows, location
of stations and receivers

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

# #############################
period_list = ["17_40", "40_100", "90_250"]

superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_M16"
measurebase = os.path.join(superbase, "measure")
stationbase = os.path.join(superbase, "stations")
# #############################


def load_txt(txtfile):
    with open(txtfile, 'r') as fh:
        return [line.rstrip() for line in fh]


def check_file_exists(filename):
    if not os.path.exists(filename):
        raise ValueError("Missing file: %s" % filename)


def generate_json_paths(eventlist, outputfile, mtype=""):
    paths = {"input": {}, "outputdir": "./output%s" % mtype}

    for event in eventlist:
        event_info = {}
        stationfile = os.path.join(stationbase, "%s.stations.json" % event)
        check_file_exists(stationfile)
        period_info = {}
        for period in period_list:
            measure_file = \
                os.path.join(measurebase, "%s.%s.measure_adj.json%s"
                             % (event, period, mtype))
            check_file_exists(measure_file)
            period_info[period] = {"measure_file": measure_file}
        event_info = {"stationfile": stationfile,
                      "period_info": period_info}

        paths["input"][event] = event_info

    print("Output dir json file: ", outputfile)
    with open(outputfile, 'w') as f:
        json.dump(paths, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = load_txt(args.eventlist_file)

    generate_json_paths(eventlist, "window_weight.path.json", mtype="")

    generate_json_paths(eventlist, "window_weight.filter.path.json",
                        mtype=".filter")
