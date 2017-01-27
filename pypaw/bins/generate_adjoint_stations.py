#!/usr/bin/env python

"""
This script will generate the STATIONS_ADJOINT file from
measurements file and stations file(stations.json). The
STATIONS_ADJOINT will then be used in adjoint simulations.
"""
from __future__ import print_function, division, absolute_import
import os
import argparse
from pprint import pprint
from .utils import load_json
from pytomo3d.station.generate_adjoint_stations import \
    generate_adjoint_stations


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    paths = load_json(args.path_file)

    print("Path information:")
    pprint(paths)

    # load stations
    station_file = paths["station_file"]
    stations = load_json(station_file)

    # load measurements
    measure_files = paths["measure_files"]
    measurements = {}
    for period, fn in measure_files.iteritems():
        measurements[period] = load_json(fn)

    outputfile = paths["output_file"]
    outputdir = os.path.dirname(outputfile)
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    generate_adjoint_stations(measurements, stations, outputfile)


if __name__ == "__main__":
    main()
