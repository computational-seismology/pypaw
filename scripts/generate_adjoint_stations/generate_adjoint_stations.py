#!/usr/bin/env python
from __future__ import (print_function)
import pyasdf
import os
import argparse
import collections


def generate_adjoint_station(asdf_fn, outputdir=".", verbose=True):
    if isinstance(asdf_fn, str):
        ds = pyasdf.ASDFDataSet(asdf_fn)
    elif isinstance(asdf_fn, pyasdf.ASDFDataSet):
        ds = asdf_fn
    else:
        raise TypeError("Input asdf_fn either be a filename or "
                        "pyasdf.ASDFDataSet")
    sta_dict = {}
    adjsrcs = ds.auxiliary_data.AdjointSources
    adj_list = adjsrcs.list()
    for adj_name in adj_list:
        adj = getattr(adjsrcs, adj_name)
        pars = adj.parameters

        station_id = pars["station_id"]
        network, station = station_id.split(".")
        comp = pars["component"]
        latitude = pars["latitude"]
        longitude = pars["longitude"]
        elevation = pars["elevation_in_m"]
        depth = pars["depth_in_m"]
        if station_id not in sta_dict:
            sta_dict[station_id] = [network, station, latitude, longitude,
                                    elevation, depth]

    filename = os.path.join(outputdir, "STATIONS_ADJOINT")
    print("Input asdf: %s" % asdf_fn)
    print("Output file: %s" % filename)
    if verbose:
        print("Number of stations: %d" % len(sta_dict))

    with open(filename, 'w') as fh:
        od = collections.OrderedDict(sorted(sta_dict.items()))
        for _sta_id, _sta in od.iteritems():
            fh.write("%-9s %5s %15.4f %12.4f %10.1f %6.1f\n"
                    % (_sta[1], _sta[0], _sta[2], _sta[3], _sta[4], _sta[5]))
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest="outputdir",
                        default=".", help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")
    parser.add_argument('-v', action='store_true', dest='verbose')

    args = parser.parse_args()
    generate_adjoint_station(args.filename, args.outputdir, args.verbose)
