#!/usr/bin/env pythoiin
# -*- coding: utf-8 -*-
"""
Calculate the adjoint source weighting based on the station and source
distribution.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
import numpy as np
import logging
import matplotlib.pyplot as plt
plt.switch_backend('agg')  # NOQA

from pyasdf import ASDFDataSet
from pytomo3d.adjoint.sum_adjoint import check_events_consistent
from pytomo3d.window.window_weights import determine_receiver_weighting, \
    determine_category_weighting
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
    Extract receiver location information from asdf file
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
         "depth:": origin.depth}

    return src_info


def check_cat_consistency(cat_ratio, cat_wcounts):
    err = 0
    # check consistency
    for p, pinfo in cat_ratio:
        for c in pinfo:
            try:
                cat_wcounts[p][c]
            except KeyError:
                err = 1
                print("Missing %s.%s" % (p, c))
    if err:
        raise ValueError("category weighting ratio information is not "
                         "consistent with window information")


def plot_histogram(figname, array, nbins=50):
    # plot histogram of weights
    plt.hist(array, nbins)
    plt.savefig(figname)


def combine_weights(rec_weights, cat_weights):
    """
    Combine weights for receiver weighting and category weighting
    """
    logger_block("Combine Weighting")
    # combine weights
    weights = {}
    for period, period_info in rec_weights.iteritems():
        weights[period] = {}
        for comp, comp_info in period_info.iteritems():
            for chan_id in comp_info:
                rec_weight = comp_info[chan_id]
                cat_weight = cat_weights[period][comp]
                _weight = {"receiver": rec_weight,
                           "category": cat_weight}
                _weight["weight"] = \
                    rec_weight * cat_weight
                weights[period][chan_id] = _weight
    return weights


def validate_overall_weights(weights_array, nwins_array):
    wsum = np.dot(nwins_array, weights_array)
    if not np.isclose(wsum, 1.0):
        raise ValueError("The sum of all weights(%f) does not add "
                         "up to 1.0" % wsum)


def analyze_overall_weights(weights, rec_wcounts, logdir):
    nwins_array = []
    weights_array = []
    # validate the sum of all weights is 1
    for _p, _pw in weights.iteritems():
        for _chan, _chanw in _pw.iteritems():
            nwins_array.append(rec_wcounts[_p][_chan])
            weights_array.append(_chanw["weight"])

    validate_overall_weights(weights)

    figname = os.path.join(logdir, "weights.hist.png")
    plot_histogram(figname, weights_array)
    figname = os.path.join(logdir, "weights.hist.png")
    plot_histogram(figname, nwins_array)

    maxw = max(weights_array)
    minw = min(weights_array)
    logger.info("Total number of receivers: %d" % len(weights_array))
    logger.info("Total number of windows: %d" % np.sum(nwins_array))
    logger.info("Weight max, min, max/min: %f, %f, %f"
                % (maxw, minw, maxw/minw))

    return {"max_weights": maxw, "min_weights": minw,
            "total_nwindows": np.sum(nwins_array)}


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

        self.rec_weights = None
        self.rec_wcounts = None
        self.rec_ref_dists = None
        self.rec_cond_nums = None

        self.cat_wcounts = None
        self.cat_weights = None

    def analysis_receiver(self, logfile):
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

    def analysis_source(self, logfile):
        """
        dump source weights and some statistic information
        """
        log = {"source_weights": self.src_weights}
        summary = {}
        for _p, _pw in self.src_weights.iteritems():
            summary[_p] = {}
            for _comp, _compw in _pw.iteritems():
                maxw = 0
                minw = 10**9
                for _ev, _evw in _compw.iteritems():
                    if _evw > maxw:
                        maxw = _evw
                    if _evw < minw:
                        minw = _evw
                summary[_p][_comp] = \
                    {"maxw": maxw, "minw": minw,
                     "ref_distance": self.src_ref_dists[_p][_comp],
                     "cond_num": self.src_cond_nums[_p][_comp],
                     "nwindows": self.cat_wcounts[_p][_comp]}

        log["summary"] = summary
        dump_json(log, logfile)

    def analysis_category(self, logfile):
        log = {"category_weights": self.cat_weights}
        maxw = 0
        minw = 10**9
        for _p, _pw in self.cat_weights.iteritems():
            for _comp, _compw in _pw.iteritems():
                if _compw > maxw:
                    maxw = _compw
                if _compw < minw:
                    minw = _compw
        log["summary"] = {"maxw": maxw, "minw": minw,
                          "cond_num": maxw/minw}

        dump_json(log, logfile)

    def analysis(self):
        """
        Analyze the final weight and generate log file
        """
        logger_block("Summary")
        logdir = os.path.dirname(self.path["logfile"])
        logfile = os.path.join(logdir, "log.receiver_weights.json")
        logger.info("receiver log file: %s" % logfile)
        self.analysis_receiver(logfile)

        logfile = os.path.join(logdir, "log.category_weights.json")
        logger.info("category log file: %s" % logfile)
        self.analysis_category(logfile)

    def dump_weights(self):
        """ dump weights to files """
        for period, period_info in self.weights.iteritems():
            outputfn = self.path['input'][period]["output_file"]
            dump_json(period_info, outputfn)

    def calculate_receiver_weights(self):
        """
        calculate receiver weights for each asdf file
        detertmine source weightings based on source infor and window
        count and info
        """
        logger_block("Receiver Weighting")
        input_info = self.path["input"]

        weighting_param = self.param["receiver_weighting"]

        self.rec_weights = defaultdict(dict)
        self.rec_wcounts = defaultdict(dict)
        self.rec_ref_dists = defaultdict(dict)
        self.rec_cond_nums = defaultdict(dict)
        self.cat_wcounts = defaultdict(dict)

        nperiods = len(input_info)
        period_idx = 0
        # determine receiver weightings for each asdf file
        for period, period_info in input_info.iteritems():
            period_idx += 1
            logger.info("-" * 15 + "[%d/%d]Period band: %s"
                        % (period_idx, nperiods, period) + "-" * 15)

            _results = self.calculate_receiver_weights_asdf(
                period_info, weighting_param)

            self.rec_weights[period] = _results["rec_weights"]
            self.rec_wcounts[period] = _results["rec_wcounts"]
            self.rec_ref_dists[period] = _results["rec_ref_dists"]
            self.rec_cond_nums[period] = _results["rec_cond_nums"]
            self.cat_wcounts[period] = _results["cat_wcounts"]

    def calculate_receiver_weights_asdf(self, period_info, weighting_param):
        search_ratio = weighting_param["search_ratio"]
        plot_flag = weighting_param["plot"]
        weight_flag = weighting_param["flag"]
        # each file still contains 3-component
        logger.info("station file: %s" % period_info["station_file"])
        logger.info("window file: %s" % period_info["window_file"])
        logger.info("output file: %s" % period_info["output_file"])
        station_info = load_json(period_info["station_file"])
        window_info = load_json(period_info["window_file"])

        outputdir = os.path.dirname(period_info["output_file"])
        safe_mkdir(outputdir)
        figname_prefix = os.path.join(outputdir, "weights")

        _results = determine_receiver_weighting(
            self.src_info, station_info, window_info,
            search_ratio=search_ratio,
            weight_flag=weight_flag,
            plot_flag=plot_flag, figname_prefix=figname_prefix)

        return _results

    def smart_run(self):

        validate_path(self.path)
        validate_param(self.param)
        # extract source location information
        self.src_info = extract_source_location(self.path["input"])
        # calculate receiver weights
        self.calculate_receiver_weights()
        # calculate category weights
        self.cat_weights = determine_category_weighting(
            self.param["category_weighting"], self.cat_wcounts)
        # combine the receiver weights with category weights
        self.weights = combine_weights(self.rec_weights, self.cat_weights)
        # statistical analysis
        self.analysis()
        # dump the results out
        self.dump_weights()
