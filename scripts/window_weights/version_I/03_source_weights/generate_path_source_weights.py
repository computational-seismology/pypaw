import os
import json


def load_txt(filename):
    with open(filename) as fh:
        return [line.rstrip() for line in fh]


def dump_json(content, filename):
    with open(filename, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def generate_paths(cmtlist, cmtdir, weightdir, outputdir="."):
    inputs = {}
    for e in cmtlist:
        cmtfile = os.path.join(cmtdir, e)
        if not os.path.exists(cmtfile):
            raise ValueError("Missing cmtfile: %s" % cmtfile)

        wcounts_file = os.path.join(
            weightdir, "%s.weight.log.weights.summary.json" % e)
        if not os.path.exists(wcounts_file):
            raise ValueError("Missing weight file: %s" % wcounts_file)

        inputs[e] = {"cmtfile": cmtfile, "window_counts_file": wcounts_file}

    outputfile = os.path.join(outputdir, "source_weights.txt")

    content = {"input": inputs, "output_file": outputfile}
    dump_json(content, "source_weights.path.json")


if __name__ == "__main__":
    cmtlist = load_txt("../cmtlist.all")
    cmtdir = "/lustre/atlas/proj-shared/geo111/TEST-KERNELS/Wenjie/" + \
        "9_events_kernels/cmt"
    weightdir = "/lustre/atlas/proj-shared/geo111/Wenjie/" + \
        "DATA_TEST_12_EVENTS/weight"
    generate_paths(cmtlist, cmtdir, weightdir, outputdir=".")
