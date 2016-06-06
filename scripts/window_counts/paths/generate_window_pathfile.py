from __future__ import print_function, division
import os
import json
import argparse

superbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/window"

period_list = ["27_60", "60_120"]

output_fn = "window.stats.path.json"


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_window_paths(eventlist):
    paths = {}

    for event in eventlist:
        paths[event] = {}
        for period in period_list:
            paths[event][period] = \
                os.path.join(superbase, "%s.%s" % (event, period),
                             "windows.stats.json")

    print("Output filename:%s" % output_fn)
    with open(output_fn, 'w') as f:
        json.dump(paths, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    generate_window_paths(eventlist)
