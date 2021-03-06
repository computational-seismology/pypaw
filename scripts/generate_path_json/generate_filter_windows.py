import os
import json
import argparse

# ###############
# User Parameter
superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_EBRU"

window_base = os.path.join(superbase, "window")
sensor_base = os.path.join(superbase, "stations")

tag = "90_250"

output_json_dir = "./output_json"
# ###############

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def dump_json(content, fn):
    with open(fn, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def generate_json_paths(event):
    parlist = {"sensor_types": ["STS1", "STS-1"]}

    parlist['window_file'] = \
        os.path.join(window_base, "%s.%s" % (event, tag), "windows.json")
    parlist["station_file"] = \
        os.path.join(sensor_base, "%s.stations.json" % event)
    parlist["output_file"] = \
        os.path.join(window_base, "%s.%s" % (event, tag),
                     "windows.filter.json")

    outputfn = os.path.join(output_json_dir, "%s.sensors.path.json" % event)
    print("output file: %s" % outputfn)
    dump_json(parlist, outputfn)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        print "="*20
        print "Event:", event
        generate_json_paths(event)
