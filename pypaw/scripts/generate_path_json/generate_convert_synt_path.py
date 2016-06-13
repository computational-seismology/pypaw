import os
import json
import argparse

# ######################
# USER DEFINED PARAMETER
superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_SI"

quakemlbase = "/ccs/home/lei/SOURCE_INVERSION/quakeml"
waveformbase = "/lustre/atlas/scratch/lei/geo111/SOURCE_INVERSION/Archive"
staxmlbase = os.path.join(superbase, "OBSD", "stationxml")
outputbase = os.path.join(superbase, "ASDF_new", "raw", "synt")

output_json_dir = "./output_json"
filetype = "sac"
tag = "synthetic"

# extlist=["", "Mrr", "Mtt", "Mpp", "Mrt", "Mrp", "Mtp", "dep", "lat", "lon"]
extlist = ["", ]
# ######################

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_parfiles(event):
    for ext in extlist:
        parlist = {}
        print "="*20
        print "Event:", event
        if ext == "":
            parlist['waveform_dir'] = os.path.join(waveformbase,
                                                   "%s" % (event))
            parlist['output_file'] = os.path.join(outputbase, "%s.%s.h5"
                                                  % (event, tag))
            path_jsonfile = os.path.join(
                output_json_dir, "%s.%s.convert.path.json" % (event, tag))
        else:
            parlist['waveform_dir'] = os.path.join(waveformbase, "%s_%s"
                                                   % (event, ext))
            parlist['output_file'] = os.path.join(outputbase, "%s.%s.%s.h5"
                                                  % (event, ext, tag))
            path_jsonfile = os.path.join(
                output_json_dir, "%s.%s.%s.convert.path.json"
                % (event, ext, tag))

        parlist['filetype'] = filetype
        parlist['tag'] = tag
        parlist['quakemlfile'] = os.path.join(quakemlbase, "%s.xml" % event)

        print "Output json file:", path_jsonfile

        with open(path_jsonfile, 'w') as f:
            json.dump(parlist, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='eventlist_file',
                        required=True)
    args = parser.parse_args()

    eventlist = read_txt_into_list(args.eventlist_file)
    for event in eventlist:
        generate_json_parfiles(event)
