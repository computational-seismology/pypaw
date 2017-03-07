#!/usr/bin/env pythoiin
# -*- coding: utf-8 -*-
"""
Porgram: Window weights version I

Calculate the adjoint source weighting based on the window, station
and category information(category info shoud be provided by user).

This program evaluates the weightings given one source. For example,
if one event has three period bands, then the inputs are three period
bands windows. Then it will calculate the receiver weightings.
Combined with category weighting(provide by user), it will generate
the weightings.

So this program is station weighting + category weighting combined.
The source weighting could be determined later when the kernels
are summed together.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from copy import deepcopy
import numpy as np
import logging
import matplotlib.pyplot as plt
plt.switch_backend('agg')  # NOQA

from pyasdf import ASDFDataSet
from pytomo3d.adjoint.sum_adjoint import check_events_consistent
from pytomo3d.window.window_weights import \
    calculate_receiver_weights_interface, \
    calculate_category_weights_interface,\
    combine_receiver_and_category_weights
from pypaw.bins.utils import load_json, dump_json, load_yaml


# Setup the logger.
logger = logging.getLogger("window-weight")
logger.setLevel(logging.INFO)
# Prevent propagating to higher loggers.
logger.propagate = 0
# Console log handler.
ch = logging.StreamHandler()
# Add formatter
FORMAT = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s"
formatter = logging.Formatter(FORMAT)
ch.setFormatter(formatter)
logger.addHandler(ch)


def logger_block(string, symbol="="):
    one_side = 15
    total_len = one_side * 2 + 2 + len(string)
    logger.info(symbol * total_len)
    logger.info(symbol * one_side + " %s " % string + symbol * one_side)
    logger.info(symbol * total_len)


def safe_mkdir(dirname):
    if os.path.exists(dirname):
        if not os.path.isdir(dirname):
            raise ValueError("Check (%s) is not a dir" % dirname)
    else:
        os.makedirs(dirname)


def _file_not_exists(fn):
    if not os.path.exists(fn):
        print("Missing file: %s" % fn)
        return 1
    else:
        return 0


def validate_path(path):
    err = 0
    logger.info("Validate input path")
    input_info = path["input"]
    for period, period_info in input_info.iteritems():
        asdf_file = period_info["asdf_file"]
        window_file = period_info["window_file"]
        station_file = period_info["station_file"]
        err += _file_not_exists(asdf_file)
        err += _file_not_exists(window_file)
        err += _file_not_exists(station_file)

    logfile = path["logfile"]
    logdir = os.path.dirname(logfile)
    safe_mkdir(logdir)

    if err != 0:
        raise ValueError("Error in path file. Please "
                         "double check!")


def validate_param(param):
    err = 0
    logger.info("Validate input param")
    keys = ["receiver_weighting", "category_weighting"]
    for key in keys:
        if key not in param:
            print("Key(%s) not in param file" % key)
            err = 1

    keys = ["flag", "ratio"]
    for key in keys:
        if key not in param["category_weighting"]:
            print("Key(%s) not in param['category_weighting']" % key)
            err = 1

    keys = ["flag", "search_ratio", "plot"]
    for key in keys:
        if key not in param['receiver_weighting']:
            print("Key(%s) not in param['receiver_weighting']" % key)
            err = 1

    if err != 0:
        raise ValueError("Error in param file. Please double check!")


def extract_receiver_locations(station_file, windows):
    """
    Extract receiver location information from station json file
    """
    station_info = load_json(station_file)
    return station_info


def extract_source_location(input_info):
    """
    Extract source location information from asdf file
    """
    logger_block("Extracting source location information")
    asdf_events = {}
    for period, period_info in input_info.iteritems():
        asdf_fn = period_info["asdf_file"]
        logger.info("Period band: %s -- asdf file: %s"
                    % (period, asdf_fn))
        ds = ASDFDataSet(asdf_fn, mode='r')
        asdf_events[period] = ds.events[0]
        del ds

    # check event information all the same across period bands
    check_events_consistent(asdf_events)

    event_base = asdf_events[asdf_events.keys()[0]]
    origin = event_base.preferred_origin()
    src_info = {
        "latitude": origin.latitude, "longitude": origin.longitude,
        "depth_in_m": origin.depth}

    return src_info


def plot_histogram(figname, array, nbins=50):
    # plot histogram of weights
    plt.hist(array, nbins)
    plt.savefig(figname)


def analyze_category_weights(cat_weights, logfile):
    log = {"category_weights": cat_weights}
    maxw = 0
    minw = 10**9
    for _p, _pw in cat_weights.iteritems():
        for _comp, _compw in _pw.iteritems():
            if _compw > maxw:
                maxw = _compw
            if _compw < minw:
                minw = _compw
    log["summary"] = {"maxw": maxw, "minw": minw,
                      "cond_num": maxw/minw}

    dump_json(log, logfile)


def validate_overall_weights(weights_array, nwins_array):
    """
    Validate the overall weights.
    """
    wsum = np.dot(nwins_array, weights_array)
    logger.info("Summation of weights*nwindows: %.5e" % wsum)
    nwins_total = np.sum(nwins_array)
    if not np.isclose(wsum, nwins_total):
        raise ValueError("The sum of all weights(%f) does not add "
                         "up to total number of windows"
                         % (wsum, nwins_total))


def analyze_overall_weights(weights, rec_wcounts, log_prefix):
    nwins_array = []
    weights_array = []
    # validate the sum of all weights is 1
    for _p, _pw in weights.iteritems():
        for _chan, _chanw in _pw.iteritems():
            comp = _chan.split(".")[-1]
            nwins_array.append(rec_wcounts[_p][comp][_chan])
            weights_array.append(_chanw["weight"])

    validate_overall_weights(weights_array, nwins_array)

    figname = log_prefix + ".weights.hist.png"
    plot_histogram(figname, weights_array)
    figname = log_prefix + ".wcounts.hist.png"
    plot_histogram(figname, nwins_array)

    nreceivers = len(weights_array)
    nwindows = np.sum(nwins_array)
    if len(weights_array) > 0:
        maxw = max(weights_array)
        minw = min(weights_array)
        max_over_min = maxw / minw
    else:
        maxw = 0.0
        minw = 0.0
        max_over_min = 0.0

    logger.info("Total number of receivers: %d" % nreceivers)
    logger.info("Total number of windows: %d" % nwindows)
    logger.info("Weight max, min, max/min: %f, %f, %f"
                % (maxw, minw, max_over_min))

    logfile = log_prefix + ".weights.summary.json"
    content = {"max_weights": maxw, "min_weights": minw,
               "total_nwindows": np.sum(nwins_array),
               "windows": nwindows, "receivers": nreceivers}
    logger.info("Overall log file: %s" % logfile)
    dump_json(content, logfile)


class WindowWeight(object):
    """
    Determine the weighting for one event, including several period bands
    and component. So each `period_band + component` is defined as a
    category.
    """
    def __init__(self, path, param):
        self.path = load_json(path)
        self.param = load_yaml(param)

        # source information is only used in plotting
        self.src_info = None

        self.weights = None

        self.rec_weights = {}
        self.rec_wcounts = {}
        self.rec_ref_dists = {}
        self.rec_cond_nums = {}

        self.cat_wcounts = {}
        self.cat_weights = None

    def analyze_receiver_weights(self, logfile):
        log = {}
        for _p, _pw in self.weights.iteritems():
            log[_p] = {}
            maxw = defaultdict(lambda: 0)
            minw = defaultdict(lambda: 10**9)
            for _chan, _chanw in _pw.iteritems():
                comp = _chan.split(".")[-1]
                if _chanw["weight"] > maxw[comp]:
                    maxw[comp] = _chanw["weight"]
                if _chanw["weight"] < minw[comp]:
                    minw[comp] = _chanw["weight"]
            for comp in maxw:
                log[_p][comp] = \
                    {"maxw": maxw[comp], "minw": minw[comp],
                     "nwindows": self.cat_wcounts[_p][comp],
                     "ref_dist": self.rec_ref_dists[_p][comp],
                     "cond_num": self.rec_cond_nums[_p][comp]}

        dump_json(log, logfile)

    def analyze(self):
        """
        Analyze the final weight and generate log file
        """
        logger_block("Summary")
        log_prefix = self.path["logfile"]
        logfile = log_prefix + ".receiver_weights.json"
        logger.info("receiver log file: %s" % logfile)
        self.analyze_receiver_weights(logfile)

        logfile = log_prefix + ".category_weights.json"
        logger.info("category log file: %s" % logfile)
        analyze_category_weights(self.cat_weights, logfile)

        analyze_overall_weights(self.weights, self.rec_wcounts,
                                log_prefix)

    def dump_weights(self):
        """ dump weights to files """
        for period, period_info in self.weights.iteritems():
            outputfn = self.path['input'][period]["output_file"]
            dump_json(period_info, outputfn)

    def calculate_receiver_weights_asdf(self):
        """
        calculate receiver weights for each asdf file. Since
        each asdf file contains three components from one period
        band, there are 3 categories which should be treated(weighted
        and normalized)separately.
        """
        logger_block("Receiver Weighting")

        weighting_param = self.param["receiver_weighting"]

        input_info = self.path["input"]
        nperiods = len(input_info)
        period_idx = 0
        # determine receiver weightings for each asdf file
        for period, period_info in input_info.iteritems():
            period_idx += 1
            logger.info("-" * 15 + "[%d/%d]Period band: %s"
                        % (period_idx, nperiods, period) + "-" * 15)
            _path_info = deepcopy(period_info)
            _path_info.pop("asdf_file", None)
            # the _results contains three components data
            _results = calculate_receiver_weights_interface(
                self.src_info, _path_info, weighting_param)

            self.rec_weights[period] = _results["rec_weights"]
            self.rec_wcounts[period] = _results["rec_wcounts"]
            self.rec_ref_dists[period] = _results["rec_ref_dists"]
            self.rec_cond_nums[period] = _results["rec_cond_nums"]
            self.cat_wcounts[period] = _results["cat_wcounts"]

    def smart_run(self):
        validate_path(self.path)
        validate_param(self.param)
        # extract source location information
        self.src_info = extract_source_location(self.path["input"])
        # calculate receiver weights
        self.calculate_receiver_weights_asdf()
        # calculate category weights
        logger_block("Category Weighting")
        self.cat_weights = calculate_category_weights_interface(
            self.param["category_weighting"], self.cat_wcounts)

        # combine the receiver weights with category weights
        logger_block("Combine Weights")
        self.weights = combine_receiver_and_category_weights(
            self.rec_weights, self.cat_weights)

        # statistical analysis
        self.analyze()
        # dump the results out
        self.dump_weights()
