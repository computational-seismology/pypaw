"""
This script to used to generate the path json file for count
number of windows for each category and also generate the
weightings for each category based on window counts.
"""

import os
import json


def load_txt(filename):
    with open(filename) as fh:
        return [line.rstrip() for line in fh]


def dump_json(content, filename):
    with open(filename, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def generate_paths(cmtlist, period_bands, winbase, outputdir="."):
    inputs = {}
    for e in cmtlist:
        inputs[e] = {}
        for p in period_bands:
            winfile = os.path.join(winbase, "%s.%s" % (e, p),
                                   "windows.filter.json")
            if not os.path.exists(winfile):
                raise ValueError("Missing window file: %s" % winfile)
            inputs[e][p] = winfile

    outputfile = os.path.join(outputdir, "window_counts.log.json")
    weight_outputfile = os.path.join(
        outputdir, "window_weights.param.default.yml")

    content = {"input": inputs, "output_file": outputfile,
               "weight_output_file": weight_outputfile}
    dump_json(content, "count_windows.path.json")


if __name__ == "__main__":
    cmtlist = load_txt("../cmtlist.all")
    winbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_TEST_12_EVENTS/window"
    period_bands = ["17_40", "40_100", "90_250"]
    generate_paths(cmtlist, period_bands, winbase)
