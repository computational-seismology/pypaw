#!/usr/bin/env python

# This script extract channel instrument information for one asdf file
# and store in json file. This will save up time for re-parsing the
# stationxml file
from __future__ import print_function, division, absolute_import
import argparse
from .utils import load_json, dump_json
from pypaw.stations import extract_station_info_from_asdf


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    paths = load_json(args.path_file)
    input_asdf = paths["input_asdf"]
    outputfn = paths["outputfile"]

    print("input asdf: %s" % input_asdf)
    print("output sensors json: %s" % outputfn)

    asdf_sensors = extract_station_info_from_asdf(
        input_asdf, verbose=args.verbose)

    dump_json(asdf_sensors, outputfn)


if __name__ == "__main__":

    main()
