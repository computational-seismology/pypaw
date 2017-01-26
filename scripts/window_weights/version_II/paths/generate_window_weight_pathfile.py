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

cmtdir = "/lustre/atlas/proj-shared/geo111/TEST-KERNELS/Wenjie/9_events_kernels/cmt"
superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_TEST_12_EVENTS"
#asdfbase = os.path.join(superbase, "proc_synt")
windowbase = os.path.join(superbase, "window")
stationbase = os.path.join(superbase, "stations")
outputbase = os.path.join(superbase, "weight")
# #############################


def load_txt(txtfile):
    with open(txtfile, 'r') as fh:
        return [line.rstrip() for line in fh]


def check_file_exists(filename):
    if not os.path.exists(filename):
        raise ValueError("Missing file: %s" % filename)


def generate_json_paths(eventlist, outputfile):
    logfile = os.path.join(outputbase, "weight.log")
    parlist = {"input": {}, "logfile": logfile}

    for event in eventlist:
        event_info = {}
        cmtfile = os.path.join(cmtdir, event)
        check_file_exists(cmtfile)
        stationfile = os.path.join(stationbase, "%s.stations.json" % event)
        check_file_exists(stationfile)
        period_info = {}
        for period in period_list:
            window_file = \
                os.path.join(windowbase, "%s.%s" % (event, period),
                             "windows.filter.json")
            check_file_exists(window_file)
            output_file = \
                os.path.join(outputbase, "%s.%s" % (event, period),
                             "%s.%s.weights.json" % (event, period))
            period_info[period] = {"window_file": window_file,
                                   "output_file": output_file}
        event_info = {"cmtfile": cmtfile, "stationfile": stationfile,
                      "period_info": period_info}
        parlist["input"][event] = event_info

    print("Output dir json file: ", outputfile)
    with open(outputfile, 'w') as f:
        json.dump(parlist, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = load_txt(args.eventlist_file)
    generate_json_paths(eventlist, "window_weight.path.json")
