from __future__ import print_function, division
import os
import argparse
from pprint import pprint

from utils import read_txt_into_list, dump_json, load_json


def sum_adjoint_misfits(filelist):
    misfits = {}
    for _file in filelist:
        _misfit = load_json(_file)
        for period, period_info in _misfit.iteritems():
            misfits.setdefault(period, {})
            for comp, comp_info in period_info.iteritems():
                if comp not in misfits[period]:
                    misfits[period][comp] = 0
                misfits[period][comp] += comp_info["misfit"]

    print("*"*20 + "\nOverall misfit information:")
    pprint(misfits)
    return misfits


def construct_filelist(base, eventlist):
    filelist = []
    for event in eventlist:
        filelist.append(os.path.join(base, "%s.adjoint.misfit.json"
                        % event))
    return filelist


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='event_file', required=True,
                        help="event list file")
    args = parser.parse_args()

    base = "/lustre/atlas/proj-shared/geo111/rawdata/asdf/adjsrc/sum"
    eventlist = read_txt_into_list(args.event_file)
    print("Number of event: %d" % len(eventlist))

    filelist = construct_filelist(base, eventlist)
    print("filelist: %s" % filelist)

    misfits = sum_adjoint_misfits(filelist)

    outputfile = os.path.join(base, "adjoint_misfit.summary.json")
    print("output json file: %s" % outputfile)
    dump_json(misfits, outputfile)
