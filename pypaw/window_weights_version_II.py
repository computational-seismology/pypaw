#!/usr/bin/env pythoiin
# -*- coding: utf-8 -*-
"""
Program: window weights version II

Unlike version I, this script doesn't not evaluate only one
event, it evaluate everything in the eventlist, by calculating
the receiver, source and category weightings.

It first evaluate the receiver weightings, for each events and
category, which is identical to version I. Then it evaluate the
source weighting based on source locations. Then using eqaul
category weighting principle, it calculates the category weightings.
Finally, it combines the all and generate the final weightings.

So to run this script, you need to provide information for all
the sources, and your database should stay fixed afterwards.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
import time
import numpy as np
import logging
from pprint import pprint
import matplotlib.pyplot as plt
plt.switch_backend('agg')  # NOQA

import obspy
from pytomo3d.source.source_weights import assign_source_to_points, \
    calculate_source_weights_on_location
from pytomo3d.window.window_weights import \
    calculate_receiver_weights_interface, calculate_receiver_window_counts
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
    for e, einfo in input_info.iteritems():
        cmtfile = einfo["cmtfile"]
        err += _file_not_exists(cmtfile)
        stationfile = einfo["stationfile"]
        err += _file_not_exists(stationfile)
        for p, pinfo in einfo["period_info"].iteritems():
            window_file = pinfo["window_file"]
            err += _file_not_exists(window_file)
            if "output_file" not in pinfo:
                raise ValueError("Missing key output_file in path file")

    logfile = path["logfile"]
    logdir = os.path.dirname(logfile)
    safe_mkdir(logdir)

    if err != 0:
        raise ValueError("Error in path file. Please "
                         "double check!")


def _missing_keys(keys, dictv):
    for k in keys:
        if k not in dictv:
            raise ValueError("Key(%s) not in dict: %s" % (k, dictv.keys()))


def validate_param(param):
    logger.info("Validate input param")
    keys = ["receiver_weighting", "source_weighting", "category_weighting"]

    _missing_keys(keys, param)

    keys = ["flag"]
    _missing_keys(keys, param["category_weighting"])

    keys = ["flag", "search_ratio", "plot"]
    _missing_keys(keys, param["receiver_weighting"])
    _missing_keys(keys, param["source_weighting"])


def extract_receiver_locations(station_file, windows):
    """
    Extract receiver location information from station json file
    """
    station_info = load_json(station_file)
    return station_info


def extract_source_location(input_info):
    """
    Extract source location information from cmtsolution file
    """
    src_info = {}
    logger_block("Extracting source location information")
    for e, einfo in input_info.iteritems():
        cmtfile = einfo["cmtfile"]
        cat = obspy.read_events(cmtfile, format="CMTSOLUTION")
        src_info[e] = cat

    return src_info


def plot_histogram(figname, array, nbins=50):
    # plot histogram of weights
    plt.hist(array, nbins)
    plt.savefig(figname)


def normalize_source_weights(points):
    """ Normalize the sum of source weights to number of sources """
    wsum = 0
    for p in points:
        wsum += p.weight

    print("The sum of source weights: %f" % wsum)
    npoints = len(points)
    factor = npoints / wsum
    print("The norm factor: %f" % factor)

    weights = {}
    for p in points:
        weights[p.tag] = p.weight * factor

    # validate
    wsum = 0.0
    for ev in weights:
        wsum += weights[ev]
    if not np.isclose(wsum, npoints):
        raise ValueError("Error normalize source weights: %f" % wsum)
    print("The normalized sum is: %s" % wsum)
    return weights


def calculate_source_weights(src_info, param, logdir):
    logger_block("Source Weighting")
    points = assign_source_to_points(src_info)

    ref_distance = -1.0
    cond_numb = -1.0
    if param["flag"]:
        ref_distance, cond_numb = calculate_source_weights_on_location(
            points, param["search_ratio"], param["plot"], logdir)

    src_weights = normalize_source_weights(points)

    # generate log file
    log_content = \
        {"weights": src_weights, "reference_distance": ref_distance,
         "cond_num": cond_numb, "weight_flag": param["flag"],
         "search_ratio": param["search_ratio"]}
    outputfn = os.path.join(logdir, "source_weights.log.json")
    print("Source weights log file: %s" % outputfn)
    dump_json(log_content, outputfn)

    return src_weights


def calculate_receiver_weights_asdf_one_event(cat, event_info, param):
    results = {}
    nperiods = len(event_info)
    period_idx = 0
    origin = cat[0].preferred_origin()
    src_info = {"latitude": origin.latitude, "longitude": origin.longitude,
                "depth_in_m": origin.depth}
    # determine receiver weightings for each asdf file
    for period, period_info in event_info["period_info"].iteritems():
        period_idx += 1
        logger.info("-" * 15 + "[%d/%d]Period band: %s"
                    % (period_idx, nperiods, period) + "-" * 15)
        _path_info = {"station_file": event_info["stationfile"],
                      "window_file": period_info["window_file"],
                      "output_file": period_info["output_file"]}
        # the _results contains three components data
        results[period] = calculate_receiver_weights_interface(
            src_info, _path_info, param)

        outputdir = os.path.dirname(period_info["output_file"])
        receiver_weights_file = os.path.join(
            outputdir, "receiver_weights.json")
        print("Receiver weights log file: %s" % receiver_weights_file)
        dump_json(results[period], receiver_weights_file)

    return results


def get_event_category_window_counts(path_info):
    cat_wcounts = {}
    print("Reading window files to get events cateogry window counts")
    t1 = time.time()

    for ev, evinfo in path_info.iteritems():
        cat_wcounts[ev] = {}
        for pb, pbinfo in evinfo["period_info"].iteritems():
            winfile = pbinfo["window_file"]
            windows = load_json(winfile)
            _, _wcounts = calculate_receiver_window_counts(windows)
            cat_wcounts[ev][pb] = _wcounts
    t2 = time.time()
    print("Category weighting I/O time: %.2f sec" % (t2 - t1))
    return cat_wcounts


def calculate_category_weights(src_weights, path_info, param, logdir):

    cat_wcounts = get_event_category_window_counts(path_info)
    # category weight = 1 / (N_c * \sum_{s} w_{s} N_{sc})
    sumv = {}
    for ev in cat_wcounts:
        srcw = src_weights[ev]
        for pb in cat_wcounts[ev]:
            if pb not in sumv:
                sumv[pb] = {}
            for comp in cat_wcounts[ev][pb]:
                if comp not in sumv[pb]:
                    sumv[pb][comp] = 0
                sumv[pb][comp] += srcw * cat_wcounts[ev][pb][comp]

    print("\sum_{s} source_weight * N_{sc}: %s" % sumv)

    cat_weights, ratios = normalize_category_weights(sumv)

    print("Final value of category weightings:")
    pprint(cat_weights)
    print("Ratio:")
    pprint(ratios)

    log_content = {"weights": cat_weights, "ratio": ratios}
    outputfn = os.path.join(logdir, "category_weights.log.json")
    print("category weighting log file: %s" % outputfn)
    dump_json(log_content, outputfn)

    return cat_weights


def normalize_category_weights(sumv):
    # count number of categories
    ncats = 0
    for pb in sumv:
        for comp in sumv[pb]:
            ncats += 1
    print("Number of categories: %d" % ncats)

    # get final values
    cat_weights = {}
    minval = 9999999.0
    for pb in sumv:
        cat_weights[pb] = {}
        for comp in sumv[pb]:
            _w = 1.0 / (ncats * sumv[pb][comp])
            if _w < minval:
                minval = _w
            cat_weights[pb][comp] = _w

    ratios = {}
    for pb in cat_weights:
        ratios[pb] = {}
        for comp in cat_weights[pb]:
            ratios[pb][comp] = cat_weights[pb][comp] / minval

    return cat_weights, ratios


def combine_receiver_and_category_weights(
        rec_weights, cat_weights, src_weights):
    weights = {}
    for ev, ev_info in rec_weights.iteritems():
        srcw = src_weights[ev]
        weights[ev] = {}
        for pb, pb_info in ev_info.iteritems():
            weights[ev][pb] = {}
            for comp, comp_info in pb_info.iteritems():
                catw = cat_weights[pb][comp]
                for chan_id in comp_info:
                    recw = comp_info[chan_id]
                    _weight = {"receiver": recw, "category": catw,
                               "source": srcw}
                    _w_all = recw * catw * srcw
                    _weight["weight"] = _w_all
                    weights[ev][pb][chan_id] = _weight

    return weights


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

    maxw = max(weights_array)
    minw = min(weights_array)
    nreceivers = len(weights_array)
    nwindows = np.sum(nwins_array)
    logger.info("Total number of receivers: %d" % nreceivers)
    logger.info("Total number of windows: %d" % nwindows)
    logger.info("Weight max, min, max/min: %f, %f, %f"
                % (maxw, minw, maxw/minw))

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
        self.src_weights = None

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
        for ev, ev_info in self.weights.iteritems():
            for period, period_info in ev_info.iteritems():
                _info = self.path['input'][ev]["period_info"]
                outputfn = _info[period]["output_file"]
                # print("Final weights dumped to: %s" % outputfn)
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
        nevents = len(input_info)
        idx = 0
        for ev, evinfo in input_info.iteritems():
            idx += 1
            logger.info("=" * 15 + "[%d/%d]Event: %s"
                        % (idx, nevents, ev) + "=" * 15)
            cat = self.src_info[ev]
            _results = calculate_receiver_weights_asdf_one_event(
                cat, evinfo, weighting_param)

            self.attach_event_receiver_weights(ev, _results)

    def attach_event_receiver_weights(self, ev, results):
        self.rec_weights[ev] = {}
        self.cat_wcounts[ev] = {}
        # self.rec_wcounts[ev] = {}
        self.rec_ref_dists[ev] = {}
        self.rec_cond_nums[ev] = {}
        for p in results:
            # store each period band results
            self.rec_weights[ev][p] = results[p]["rec_weights"]
            self.cat_wcounts[ev][p] = results[p]["cat_wcounts"]
            # self.rec_wcounts[ev][p] = results[p]["rec_wcounts"]
            self.rec_ref_dists[ev][p] = results[p]["rec_ref_dists"]
            self.rec_cond_nums[ev][p] = results[p]["rec_cond_nums"]

    def save_log(self):
        def _get_max_and_min(dictv):
            minv = 9999999999
            maxv = -1
            for e, einfo in dictv.iteritems():
                for p, pinfo in einfo.iteritems():
                    for c, cinfo in pinfo.iteritems():
                        if minv > cinfo:
                            minv = cinfo
                        if maxv < cinfo:
                            maxv = cinfo
            return minv, maxv

        logfile = self.path["logfile"]
        cond_min, cond_max = _get_max_and_min(self.rec_cond_nums)
        ref_min, ref_max = _get_max_and_min(self.rec_ref_dists)
        log_content = {
            "receiver_ref_dist": self.rec_ref_dists,
            "recevier_cond_numb": self.rec_cond_nums,
            "summary": {
                "receiver_ref_dist": {"min": ref_min, "max": ref_max},
                "receiver_cond_num": {"min": cond_min, "max": cond_max}}}
        print("log file: %s" % logfile)
        dump_json(log_content, logfile)

    def smart_run(self):
        validate_path(self.path)
        validate_param(self.param)

        logdir = os.path.dirname(self.path["logfile"])
        # extract source location information for all events
        self.src_info = extract_source_location(self.path["input"])
        # calculate source weightings
        self.src_weights = calculate_source_weights(
            self.src_info, self.param["source_weighting"], logdir)

        # calculate category weights first
        # In theory, we may calculate receiver weights first to
        # read in the windows. But here, we calculate category weights
        # first so window file will be read twice. However, in this
        # manner, we would see category weighting very fast.
        logger_block("Category Weighting")
        self.cat_weights = calculate_category_weights(
            self.src_weights, self.path["input"],
            self.param["category_weighting"], logdir)

        # calculate receiver weights
        self.calculate_receiver_weights_asdf()

        # combine the receiver weights with category weights
        logger_block("Combine Weights")
        self.weights = combine_receiver_and_category_weights(
            self.rec_weights, self.cat_weights, self.src_weights)

        # statistical analysis
        # self.analyze()
        # dump the results out
        self.dump_weights()

        self.save_log()
