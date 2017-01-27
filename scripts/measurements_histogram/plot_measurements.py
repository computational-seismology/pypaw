#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Plot the histogram of measurements. All the input files
are specified in the path json file.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division
import os
import json
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_txt(txtfile):
    with open(txtfile, 'r') as fh:
        return [line.rstrip() for line in fh]


def load_json(fn):
    with open(fn) as fh:
        return json.load(fh)


def dump_json(content, fn):
    with open(fn, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def check_file_exists(filename):
    if not os.path.exists(filename):
        raise ValueError("Missing file: %s" % filename)


def load_one_measurefile(measure_file):
    measure = load_json(measure_file)

    dt = {}
    dlna = {}
    for sta, stainfo in measure.iteritems():
        for chan, chaninfo in stainfo.iteritems():
            comp = chan.split(".")[-1]
            if comp not in dt:
                dt[comp] = []
            dt[comp].extend([m["dt"] for m in chaninfo])
            if comp not in dlna:
                dlna[comp] = []
            dlna[comp].extend([m["dlna"] for m in chaninfo])

    return dt, dlna


def update_overall(dict_one, dict_all, pb):
    if pb not in dict_all:
        dict_all[pb] = {}
    for comp in dict_one:
        if comp not in dict_all[pb]:
            dict_all[pb][comp] = []
        dict_all[pb][comp].extend(dict_one[comp])


def get_mean_and_std(dictv):
    mean = {}
    std = {}
    for pb, pbinfo in dictv.iteritems():
        mean[pb] = {}
        std[pb] = {}
        for comp, compinfo in pbinfo.iteritems():
            mean[pb][comp] = np.mean(compinfo)
            std[pb][comp] = np.std(compinfo)

    return mean, std


def stats_analysis(dts, dlnas, outputdir):
    dt_mean, dt_std = get_mean_and_std(dts)
    dlna_mean, dlna_std = get_mean_and_std(dlnas)

    log_content = {"dt": {"mean": dt_mean, "std": dt_std},
                   "dlna": {"mean": dlna_mean, "std": dlna_std}}

    outputfn = os.path.join(outputdir, "measure.log.json")
    print("log file: %s" % outputfn)
    dump_json(log_content, outputfn)


def load_measurements(inputs):
    dts = {}
    dlnas = {}
    for ev, evinfo in inputs.iteritems():
        for pb, pbinfo in evinfo["period_info"].iteritems():
            _dt, _dlna = load_one_measurefile(pbinfo["measure_file"])
            update_overall(_dt, dts, pb)
            update_overall(_dlna, dlnas, pb)

    return dts, dlnas


def plot_hist(data, figname=None):
    period_bands = ["17_40", "40_100", "90_250"]
    components = ["BHR", "BHT", "BHZ"]

    fig = plt.figure(figsize=(20, 20))

    irow = 0
    for pb in period_bands:
        icol = 0
        for comp in components:
            idx = irow * 3 + icol + 1
            plt.subplot(3, 3, idx)
            plt.hist(data[pb][comp], bins=30)
            mean = np.mean(data[pb][comp])
            std = np.std(data[pb][comp])
            xloc = plt.xlim()[0] + 0.05 * (plt.xlim()[1] - plt.xlim()[0])
            plt.text(xloc, plt.ylim()[1] * 0.9, "mean: %.4f" %
                     (mean))
            plt.text(xloc, plt.ylim()[1] * 0.85, "std: %.4f" %
                     (std))
            if icol == 0:
                plt.ylabel(pb)
            if irow == 2:
                plt.xlabel(comp)
            icol += 1
        irow += 1

    print("Save figure to: %s" % figname)
    plt.tight_layout()
    plt.savefig(figname)
    plt.close(fig)


def plot_measures(dts, dlnas, outputdir):

    figname = os.path.join(outputdir, "dt.histogram.pdf")
    plot_hist(dts, figname=figname)

    figname = os.path.join(outputdir, "dlna.histogram.pdf")
    plot_hist(dlnas, figname=figname)


def main(path):
    inputs = path["input"]
    outputdir = path["outputdir"]
    print("Number of events: %d" % len(inputs))
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    dts, dlnas = load_measurements(inputs)

    stats_analysis(dts, dlnas, outputdir)
    plot_measures(dts, dlnas, outputdir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path',
                        required=True)
    args = parser.parse_args()

    path = load_json(args.path)
    main(path)
