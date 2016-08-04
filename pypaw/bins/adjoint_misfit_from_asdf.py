#!/usr/bin/env python
"""
Class that sums the several adjoint source files together based
on certain weights provided by the user
"""
from __future__ import (print_function, division)
import os
import json
import argparse
from pyasdf import ASDFDataSet


def extract_adjoint_misfit(asdf_file, verbose):

    print("Input asdf file: %s" % asdf_file)

    if not os.path.exists(asdf_file):
        raise ValueError("ASDF file not exists: %s" % asdf_file)
    ds = ASDFDataSet(asdf_file, mode='r')
    try:
        adjsrc_group = ds.auxiliary_data.AdjointSources
    except Exception as err:
        raise ValueError("Can not get adjoint misfit information(due to %s). "
                         "Check if the adjoint source group exists in the "
                         "file" % err)

    nadj = 0
    nadj_cat = {}
    misfit_cat = {}
    misfit_dict = {}
    for adj in adjsrc_group:
        nadj += 1

        nw = adj.parameters["station_id"].split(".")[0]
        sta = adj.parameters["station_id"].split(".")[1]
        comp = adj.parameters["component"]
        loc = adj.parameters["location"]
        station_id = "%s.%s.%s.%s" % (nw, sta, loc, comp)
        misfit = adj.parameters["misfit"]

        misfit_dict[station_id] = misfit
        if comp not in misfit_cat:
            misfit_cat[comp] = 0
            nadj_cat[comp] = 0
        misfit_cat[comp] += misfit
        nadj_cat[comp] += 1

    content = {"asdf_file": asdf_file, "misfit": misfit_dict,
               "misfit_category": misfit_cat,
               "nadj_total": nadj, "nadj_category": nadj_cat}

    if verbose:
        print("Number of adjoint sources:", nadj)

    return content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest='output_fn',
                        default='adjoint.misfit.json',
                        help='output misfit filename')
    parser.add_argument('filename', help='Input ASDF filename')
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    content = extract_adjoint_misfit(args.filename, args.verbose)

    output_fn = args.output_fn
    print("Output file: %s" % output_fn)
    with open(output_fn, 'w') as fh:
        json.dump(content, fh, indent=2)


if __name__ == '__main__':
    main()
