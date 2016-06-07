import os
import json
import argparse

# ###############
# User Parameter
superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_SI/ASDF"

input_asdfbase = os.path.join(superbase, "raw", "obsd")
output_asdfbase = os.path.join(superbase, "proc", "obsd")
old_tag = "observed"
new_tag_list = ["proc_obsd_50_100", "proc_obsd_60_100"]

output_json_dir = "./output_json"
# ###############

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_dirfiles(eventname):
    parlist = {}
    parlist['input_asdf'] = \
        os.path.join(input_asdfbase, "%s.%s.h5" % (event, old_tag))
    parlist["input_tag"] = old_tag

    for tag in new_tag_list:
        parlist['output_asdf'] = \
            os.path.join(output_asdfbase, "%s.%s.h5" % (event, tag))
        parlist['output_tag'] = tag
        par_jsonfile = \
            os.path.join(output_json_dir, "%s.%s.path.json" % (event, tag))
        print "Output dir json file:", par_jsonfile
        with open(par_jsonfile, 'w') as f:
            json.dump(parlist, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        print "="*20
        print "Event:", event
        generate_json_dirfiles(event)
