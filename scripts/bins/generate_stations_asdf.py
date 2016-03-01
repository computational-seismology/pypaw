#!/usr/bin/env python
"""
Scripts that generate stations file from asdf file. If
there are stations in waveforms, then a file `STATIONS_waveform`
will be generated. Or if there are stations in AuxlilaryData,
then a file `STATIONS_ADJOINT` will be generated.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (print_function)
import pyasdf
import os
import argparse
import collections


def write_stations_file(sta_dict, filename="STATIONS", _verbose=False):
    with open(filename, 'w') as fh:
        od = collections.OrderedDict(sorted(sta_dict.items()))
        for _sta_id, _sta in od.iteritems():
            if _verbose:
                print("Station:%s" % _sta_id)
            fh.write("%-9s %5s %15.4f %12.4f %10.1f %6.1f\n"
                     % (_sta[1], _sta[0], _sta[2], _sta[3], _sta[4], _sta[5]))


def generate_waveform_station(asdf_fn, outputdir=".", verbose=True):
    if isinstance(asdf_fn, str):
        ds = pyasdf.ASDFDataSet(asdf_fn)
    elif isinstance(asdf_fn, pyasdf.ASDFDataSet):
        ds = asdf_fn
    else:
        raise TypeError("Input asdf_fn either be a filename or "
                        "pyasdf.ASDFDataSet")

    sta_dict = {}
    waveform_list = ds.waveforms.list()
    for _st_tag in waveform_list:
        st_id = _st_tag.replace(".", "_")
        nw, station = _st_tag.split(".")
        station_group = getattr(ds.waveforms, st_id)
        if "StationXML" not in dir(station_group):
            continue
        staxml = getattr(station_group, "StationXML")
        sta_dict[st_id] = [nw, station, staxml[0][0].latitude,
                           staxml[0][0].longitude, staxml[0][0].elevation,
                           staxml[0][0][0].depth]

    if len(sta_dict) == 0:
        print("Number of stations found in waveforms is 0")
        return

    filename = os.path.join(outputdir, "STATIONS_waveforms")
    print("Input asdf: %s" % asdf_fn)
    print("Output file: %s" % filename)
    if verbose:
        print("Number of stations: %d" % len(sta_dict))
    write_stations_file(sta_dict, filename)


def generate_adjoint_station(asdf_fn, outputdir=".", verbose=True):
    if isinstance(asdf_fn, str):
        ds = pyasdf.ASDFDataSet(asdf_fn)
    elif isinstance(asdf_fn, pyasdf.ASDFDataSet):
        ds = asdf_fn
    else:
        raise TypeError("Input asdf_fn either be a filename or "
                        "pyasdf.ASDFDataSet")

    try:
        adjsrcs = ds.auxiliary_data.AdjointSources
    except:
        print("No Adjoint sources found in this file")
        return

    sta_dict = {}
    adj_list = adjsrcs.list()
    if len(adj_list) == 0:
        print("No adjoint sourcs in this file. Skip.")
    for adj_name in adj_list:
        adj = getattr(adjsrcs, adj_name)
        pars = adj.parameters

        station_id = pars["station_id"]
        network, station = station_id.split(".")
        latitude = pars["latitude"]
        longitude = pars["longitude"]
        elevation = pars["elevation_in_m"]
        depth = pars["depth_in_m"]
        if station_id not in sta_dict:
            sta_dict[station_id] = [network, station, latitude, longitude,
                                    elevation, depth]

    if len(sta_dict) == 0:
        print("Number of station found in AuxlilaryData/AdjointSources is 0")
        return

    filename = os.path.join(outputdir, "STATIONS_ADJOINT")
    print("Input asdf: %s" % asdf_fn)
    print("Output file: %s" % filename)
    if verbose:
        print("Number of stations: %d" % len(sta_dict))
    write_stations_file(sta_dict, filename)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest="outputdir",
                        default=".", help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")
    parser.add_argument('-v', action='store_true', dest='verbose')

    args = parser.parse_args()
    ds = pyasdf.ASDFDataSet(args.filename)
    generate_waveform_station(ds, args.outputdir, args.verbose)
    generate_adjoint_station(ds, args.outputdir, args.verbose)
