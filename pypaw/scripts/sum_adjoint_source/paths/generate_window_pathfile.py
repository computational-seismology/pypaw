from __future__ import print_function, division
import os
import json
import argparse

# #############################################################
superbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf"
outputbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/adjsrc/sum"

adjbase = os.path.join(superbase, "adjsrc", "M15_NEX256")
weightbase = os.path.join(superbase, "window_weight")

period_list = ["27_60", "60_120"]

output_json_dir = "./output_json"
# #############################################################

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_path(eventname):
    path = {"input_file": {}, "rotate_flag": True}

    path["output_file"] = os.path.join(outputbase,
                                       "%s.adjoint.h5" % eventname)

    for period in period_list:
        asdf_file = os.path.join(adjbase, "%s.%s.h5" % (eventname, period))
        weight_file = os.path.join(weightbase, "%s.%s.weight.json"
                                   % (eventname, period))
        path["input_file"][period] = {"asdf_file": asdf_file,
                                      "weight_file": weight_file}

    output_json = os.path.join(output_json_dir, "%s.path.json" % eventname)
    print("output json: %s" % output_json)
    with open(output_json, 'w') as fh:
        json.dump(path, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    print("Eventlist file:", args.eventlist_file)

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        print("="*20)
        print("Event:", event)
        generate_json_path(event)
