import os
import json
import argparse

superbase = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_SI/ASDF_new"

obsd_asdfbase = os.path.join(superbase, "proc", "obsd")
synt_asdfbase = os.path.join(superbase, "proc", "synt")
window_base = os.path.join(superbase, "window")
period_list = ["50_100", "60_100"]

output_json_dir = "./output_json"

if not os.path.exists(output_json_dir):
    os.makedirs(output_json_dir)


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def generate_json_dirfiles(eventname):
    parlist = {}

    for period in period_list:
        obsd_tag = "proc_obsd_%s" % (period)
        synt_tag = "proc_synt_%s" % (period)
        parlist['obsd_asdf'] = os.path.join(obsd_asdfbase, "%s.%s.h5"
                                            % (event, obsd_tag))
        parlist['obsd_tag'] = obsd_tag
        parlist['synt_asdf'] = os.path.join(synt_asdfbase, "%s.%s.h5"
                                            % (event, synt_tag))
        parlist['synt_tag'] = synt_tag
        parlist['output_dir'] = os.path.join(window_base, "%s.%s"
                                             % (event, period))
        parlist['figure_mode'] = False
        par_jsonfile = os.path.join(output_json_dir, "%s.%s.window.path.json"
                                    % (event, period))

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
