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


def extract_adjoint_misfit(asdf_file, outputdir, verbose):

    print("Input asdf file: %s" % asdf_file)

    if not os.path.exists(asdf_file):
        raise ValueError("ASDF file not exists: %s" % asdf_file)
    ds = ASDFDataSet(asdf_file)
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

    outputfn = os.path.join(outputdir, "%s.misfit_summary.json"
                            % asdf_file[:-3])

    print("Output file: %s" % outputfn)
    with open(outputfn, 'w') as fh:
        json.dump(content, fh, indent=2)

    if verbose:
        print("Number of adjoint sources:", nadj)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest='outputdir', default='.',
                        help='output directory')
    parser.add_argument('filename', help='Input ASDF filename')
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    job = extract_adjoint_misfit(args.filename, args.outputdir, args.verbose)
