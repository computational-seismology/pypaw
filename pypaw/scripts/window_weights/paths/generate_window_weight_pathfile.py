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
superbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf"

asdfbase = os.path.join(superbase, "proc_synt", "M15_NEX256")
windowbase = os.path.join(superbase, "window")
period_list = ["27_60", "60_120"]
outputbase = os.path.join(superbase, "window_weight")
# #############################


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_paths(eventlist, outputfile):
    parlist = {"input": {}, "outputdir": outputbase}

    for period in period_list:
        period_info = {}
        for event in eventlist:
            asdf_file = \
                os.path.join(asdfbase, "%s.proc_synt_%s.h5" % (event, period))
            window_file = \
                os.path.join(windowbase, "%s.%s" % (event, period),
                             "windows.json")
            event_info = {"asdf": asdf_file, "window": window_file}
            period_info[event] = event_info
        parlist["input"][period] = period_info

    print("Output dir json file: ", outputfile)
    with open(outputfile, 'w') as f:
        json.dump(parlist, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    parser.add_argument('-o', action='store', dest='outputfile',
                        default="window_weight.path.json")
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    generate_json_paths(eventlist, args.outputfile)
