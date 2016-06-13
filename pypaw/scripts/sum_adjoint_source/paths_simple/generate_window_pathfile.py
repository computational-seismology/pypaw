from __future__ import print_function, division
import os
import json
import argparse

# #########################
superbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/adjsrc/M15_NEX256"
outputbase = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/adjsrc/sum"

period_list = ["27_60", "60_120"]

output_json_dir = "./output_json"
# #########################

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


def generate_json_path(eventname, weight):
    path = {"input_file": {}, "rotate_flag": True}

    path["output_file"] = os.path.join(outputbase,
                                       "%s.adjoint.h5" % eventname)

    for period, period_weight in weight.iteritems():
        asdf_file = os.path.join(superbase, "%s.%s.h5" % (eventname, period))
        weight = period_weight
        path["input_file"][period] = {"asdf_file": asdf_file,
                                      "weight": weight}

    output_json = os.path.join(output_json_dir, "%s.path.json" % eventname)
    print("output json file: %s" % output_json)
    with open(output_json, 'w') as fh:
        json.dump(path, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    parser.add_argument('-w', action='store', dest='weight_file',
                        required=True)
    args = parser.parse_args()

    print("Eventlist file:", args.eventlist_file)
    print("Weight file:", args.weight_file)

    eventlist = read_txt_into_list(args.eventlist_file)
    weight = load_json(args.weight_file)
    for event in eventlist:
        print("="*20)
        print("Event:", event)
        generate_json_path(event, weight)
