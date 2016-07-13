#!/usr/bin/env python

# This script extract channel instrument information for one asdf file
# and store in json file. This will save up time for re-parsing the
# stationxml file
from __future__ import print_function, division, absolute_import
import json
import argparse
import pyasdf
from pytomo3d.station import extract_sensor_type


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def dump_json(content, filename):
    with open(filename, "w") as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def extract_sensor_from_asdf(asdf_file, outputfn, verbose=False):
    asdf_sensors = dict()

    ds = pyasdf.ASDFDataSet(asdf_file, mode="r")
    ntotal = len(ds.waveforms)
    for idx, st_group in enumerate(ds.waveforms):
        if verbose:
            print("[%4d/%d]Station: %s"
                  % (idx, ntotal, st_group._station_name))
        try:
            inv = st_group.StationXML
            sensors = extract_sensor_type(inv)
            asdf_sensors.update(sensors)
        except Exception as msg:
            print("Failed to extract due to: %s" % msg)
            continue

    return asdf_sensors


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

    asdf_sensors = extract_sensor_from_asdf(input_asdf, outputfn,
                                            verbose=args.verbose)

    dump_json(asdf_sensors, outputfn)


if __name__ == "__main__":

    main()
