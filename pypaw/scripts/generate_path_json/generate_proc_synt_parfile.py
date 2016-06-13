import os
import json
import argparse

# ################
# User parameter
superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_SI/ASDF"

input_asdfbase = os.path.join(superbase, "raw", "synt")
output_asdfbase = os.path.join(superbase, "proc", "synt")

output_json_dir = "./output_json"

old_tag = "synthetic"
taglist = ["proc_synt_50_100", "proc_synt_60_100"]
# extlist=["", "Mrr", "Mtt", "Mpp", "Mrt", "Mrp", "Mtp", "dep", "lat", "lon"]
extlist = ["", ]
# ###############

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_parfiles(event, ext=""):
    for tag in taglist:
        parlist = {}
        if ext == "":
            parlist['input_asdf'] = \
                os.path.join(input_asdfbase, "%s.%s.h5"
                             % (event, old_tag))
            parlist["input_tag"] = old_tag
            parlist['output_asdf'] = \
                os.path.join(output_asdfbase, "%s.%s.h5"
                             % (event, tag))
            parlist["output_tag"] = tag
            par_jsonfile = \
                os.path.join(output_json_dir, "%s.%s.path.json"
                             % (event, tag))
        else:
            parlist['input_asdf'] = \
                os.path.join(input_asdfbase, "%s.%s.%s.h5"
                             % (event, ext, old_tag))
            parlist["input_tag"] = old_tag
            parlist['output_asdf'] = \
                os.path.join(output_asdfbase, "%s.%s.%s.h5"
                             % (event, ext, tag))
            parlist["output_tag"] = tag
            par_jsonfile = \
                os.path.join(output_json_dir, "%s.%s.%s.path.json"
                             % (event, ext, tag))

        print "Output json file:", par_jsonfile

        with open(par_jsonfile, 'w') as f:
            json.dump(parlist, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        for ext in extlist:
            print "="*20
            print "Event:", event
            generate_json_parfiles(event, ext=ext)
