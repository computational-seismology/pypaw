# plot stats histogram for each event
from __future__ import print_function, division
import os
import json
import argparse

# ###################
superbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/window/M15_NEX256"
outputbase = "./figure"

# period_list = ["17_40", "40_100", "90_250", "90_150"]
period_list = ["90_150", ]
jsondir = "./path_files"
# ###################
if not os.path.exists(jsondir):
    os.makedirs(jsondir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_window_paths(eventlist, jsonfile):
    paths = {"outputdir": "./figure/all"}

    inputs = {}
    for period in period_list:
        inputs[period] = {}
        for event in eventlist:
            winfile = \
                os.path.join(superbase, "%s.%s" % (event, period),
                             "windows.json")
            if not os.path.exists(winfile):
                print("No winfile found: %s" % winfile)
            else:
                inputs[period][event] = winfile
    paths["input"] = inputs

    print("Output filename:%s" % jsonfile)
    with open(jsonfile, 'w') as f:
        json.dump(paths, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)

    jsonfile = os.path.join(jsondir, "all.path.json")
    generate_window_paths(eventlist, jsonfile)
