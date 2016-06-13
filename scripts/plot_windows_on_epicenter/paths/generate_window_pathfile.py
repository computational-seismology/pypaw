from __future__ import print_function, division
import os
import json
import argparse

# ###################
syntbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/proc_synt/M15_NEX256"
winbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/window/M15_NEX256"
outputbase = "./figure"
period_list = ["17_40", "40_100", "90_250"]
pathfile_dir = "./path_files"
# ###################
if not os.path.exists(pathfile_dir):
    os.makedirs(pathfile_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_window_paths(event):
    for period in period_list:
        path_info = {}
        asdf = os.path.join(syntbase, "%s.proc_synt_%s.h5" %
                            (event, period))
        winfile = os.path.join(winbase, "%s.%s" % (event, period),
                               "windows.json")

        if not os.path.exists(winfile):
            print("No winfile found: %s" % winfile)
            continue
        else:
            path_info["asdf"] = asdf
            path_info["window"] = winfile
            path_info["outputdir"] = \
                os.path.join(outputbase, "%s.%s" % (event, period))

        output_fn = os.path.join(pathfile_dir, "%s.%s.json" % (event, period))
        print("Output path json:%s" % output_fn)
        with open(output_fn, 'w') as f:
            json.dump(path_info, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        generate_window_paths(event)
