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
from __future__ import (print_function, division)
import os
import argparse
import collections
import pyasdf
from pypaw.stations import extract_waveform_stations
from pypaw.stations import extract_adjoint_stations


def write_stations_file(sta_dict, filename="STATIONS"):
    """
    Write station information out to a file
    """
    with open(filename, 'w') as fh:
        od = collections.OrderedDict(sorted(sta_dict.items()))
        print("Stations list: %s" % od.keys())
        for _sta_id, _sta in od.iteritems():
            network, station = _sta_id.split(".")
            fh.write("%-9s %5s %15.4f %12.4f %10.1f %6.1f\n"
                     % (station, network, _sta[0], _sta[1], _sta[2], _sta[3]))


def generate_waveform_stations(asdf, outputdir="."):
    print("Input asdf: %s" % asdf)
    sta_dict = extract_waveform_stations(asdf)

    filename = os.path.join(outputdir, "STATIONS_waveforms")
    print("Output file: %s" % filename)
    print("Number of stations: %d" % len(sta_dict))
    if len(sta_dict) > 0:
        write_stations_file(sta_dict, filename)


def generate_adjoint_stations(asdf, outputdir="."):
    print("Input asdf: %s" % asdf)
    sta_dict = extract_adjoint_stations(asdf)

    filename = os.path.join(outputdir, "STATIONS_ADJOINT")
    print("Output file: %s" % filename)
    print("Number of stations: %d" % len(sta_dict))
    if len(sta_dict) > 0:
        write_stations_file(sta_dict, filename)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest="outputdir",
                        default=".", help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")

    args = parser.parse_args()
    ds = pyasdf.ASDFDataSet(args.filename)
    generate_waveform_stations(ds, args.outputdir)
    generate_adjoint_stations(ds, args.outputdir)
