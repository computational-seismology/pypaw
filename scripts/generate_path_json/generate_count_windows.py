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
                                   "windows.json")
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
    cmtlist = load_txt("../cmtlist")
    winbase = "/lustre/atlas/proj-shared/geo111/TEST-KERNELS/Wenjie/data/ebru_benchmark/window"
    period_bands = ["17_40", "40_100", "90_250"]
    generate_paths(cmtlist, period_bands, winbase)
