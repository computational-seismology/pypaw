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

from spaceweight import SpherePoint
from spaceweight import SphereDistRel
from pyasdf import ASDFDataSet
from pypaw.bins.utils import load_json, dump_json, load_yaml


# Setup the logger.
logger = logging.getLogger(" window-weight")
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


def validate_path(path):
    err = 0
    logger.info("Validate inputp path")
    input_info = path["input"]
    for period, period_info in input_info.iteritems():
        for event, event_info in period_info.iteritems():
            asdf_file = event_info["asdf_file"]
            window_file = event_info["window_file"]
            station_file = event_info["station_file"]
            if not os.path.exists(asdf_file):
                print("Missing asdf file: %s" % asdf_file)
                err = 1
            if not os.path.exists(window_file):
                print("Missing window file: %s" % window_file)
                err = 1
            if not os.path.exists(station_file):
                print("Missing station file: %s" % station_file)
                err = 1
            if "output_file" not in event_info:
                print("Missing key 'output_file' in %s.%s"
                      % (event, period))
                err = 1
    try:
        logdir = path["log_dir"]
        safe_mkdir(logdir)
    except KeyError:
        print("Missing key 'log_dir' in path")
        err = 1

    if err != 0:
        raise ValueError("Error in path file. Please "
                         "double check!")


def validate_param(param):
    err = 0
    logger.info("Validate input param")
    keys = ["source_weighting", "source_search_ratio",
            "receiver_weighting", "receiver_search_ratio",
            "plot"]
    for key in keys:
        if key not in param:
            print("Key(%s) not in param file")
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
    src_info = defaultdict(dict)
    for period, period_info in input_info.iteritems():
        logger.info("Period band: %s -- Number of files: %s"
                    % (period, len(period_info)))
        for eventname, event_info in period_info.iteritems():
            asdf_fn = event_info["asdf_file"]
            ds = ASDFDataSet(asdf_fn, mode='r')
            event = ds.events[0]
            origin = event.preferred_origin()
            latitude = origin.latitude
            longitude = origin.longitude
            depth = origin.depth
            src_info[period][eventname] = {
                "latitude": latitude, "longitude": longitude,
                "depth:": depth}

    return src_info


def _receiver_validator(weights, rec_wcounts, src_wcounts):

    for comp in weights:
        wsum = 0
        for trace_id, trace_weight in weights[comp].iteritems():
            nwin = rec_wcounts[trace_id]
            wsum += trace_weight * nwin

        if not np.isclose(wsum, src_wcounts[comp]):
            raise ValueError("receiver validator fails: %f, %f" %
                             (wsum, src_wcounts[comp]))


def determine_receiver_weighting(src, stations, windows, max_ratio=0.35,
                                 flag=True, plot=False,
                                 figname_prefix=None):
    """
    Given one station and window information, determine the receiver
    weighting
    In one asdf file, there are still 3 components, for example,
    ["BHR", "BHT", "BHZ"]. These three components should be treated
    indepandently and weights will be calculated independantly.

    :return: dict of weights which contains 3 components. Each components
        contains weights values
    """
    center = SpherePoint(src["latitude"], src["longitude"],
                         tag="source")

    # extract window information
    weights = {}
    rec_wcounts = {}
    src_wcounts = defaultdict(lambda: 0)
    for sta, sta_window in windows.iteritems():
        for chan, chan_win in sta_window.iteritems():
            comp = chan.split(".")[-1]
            _nwin = len(chan_win)
            if _nwin == 0:
                continue
            weights.setdefault(comp, {}).update({chan: 0.0})
            rec_wcounts[chan] = _nwin
            src_wcounts[comp] += _nwin

    # in each components, calculate weight
    ref_dists = {}
    cond_nums = {}
    for comp, comp_info in weights.iteritems():
        points = []
        logger.info("Components:%s" % comp)
        for chan in comp_info:
            _comp = chan[-1]
            if _comp == "Z":
                point = SpherePoint(stations[chan]["latitude"],
                                    stations[chan]["longitude"],
                                    tag=chan, weight=1.0)
            else:
                # for R and T component. In station file, there
                # are only E and N component. So we need transfer
                echan = chan[:-1] + "E"
                chan1 = chan[:-1] + "1"
                zchan = chan[:-1] + "Z"
                if echan in stations:
                    point = SpherePoint(stations[echan]["latitude"],
                                        stations[echan]["longitude"],
                                        tag=chan, weight=1.0)
                elif chan1 in stations:
                    point = SpherePoint(stations[chan1]["latitude"],
                                        stations[chan1]["longitude"],
                                        tag=chan, weight=1.0)
                elif zchan in stations:
                    point = SpherePoint(stations[zchan]["latitude"],
                                        stations[zchan]["longitude"],
                                        tag=chan, weight=1.0)
            points.append(point)

        if flag:
            # calculate weight; otherwise, leave it as default value(1)
            weightobj = SphereDistRel(points, center=center)
            scan_figname = figname_prefix + "%s.smart_scan.png" % comp
            ref_dists[comp], cond_nums[comp] = weightobj.smart_scan(
                max_ratio=max_ratio, start=0.5, gap=0.5,
                drop_ratio=0.95, plot=plot,
                figname=scan_figname)
            if plot:
                figname = figname_prefix + "%s.weight.png" % comp
                weightobj.plot_global_map(figname=figname, lon0=180.0)
        else:
            ref_dists[comp] = None
            cond_nums[comp] = None

        wsum = 0
        for point in points:
            nwin = rec_wcounts[point.tag]
            wsum += point.weight * nwin
        norm_factor = src_wcounts[comp] / wsum

        for point in points:
            weights[comp][point.tag] = point.weight * norm_factor

    _receiver_validator(weights, rec_wcounts, src_wcounts)

    return {"rec_weights": weights, "rec_wcounts": rec_wcounts,
            "src_wcounts": src_wcounts, "rec_ref_dists": ref_dists,
            "rec_cond_nums": cond_nums}


def _source_validator(weights, src_wcounts, cat_counts):
    for comp, comp_weights in weights.iteritems():
        wsum = 0
        for event, event_weights in comp_weights.iteritems():
            wsum += event_weights * src_wcounts[event][comp]
        if not np.isclose(wsum, cat_counts[comp]):
            raise ValueError("Source validator fails!")


def determine_source_weighting(src_info, src_wcounts, max_ratio=0.35,
                               flag=True, plot=False,
                               figname_prefix=None):
    """
    Determine the source weighting based on source distribution and
    window counts.
    Attention here, there is still 3 components and each category
    should be weighting independently with the window count information
    in this components.
    """
    logger.info("Number of sources: %s" % len(src_info))
    logger.info("Window counts information: %s" % src_wcounts)

    # determine the weightins based on location
    points = []
    for eventname, event_info in src_info.iteritems():
        point = SpherePoint(event_info["latitude"],
                            event_info["longitude"],
                            tag=eventname,
                            weight=1.0)
        points.append(point)

    if flag:
        weightobj = SphereDistRel(points)
        scan_figname = figname_prefix + ".smart_scan.png"
        _ref_dist, _cond_num = weightobj.smart_scan(
            max_ratio=max_ratio, start=0.5, gap=0.5,
            drop_ratio=0.80, plot=plot,
            figname=scan_figname)
        if plot:
            figname = figname_prefix + ".weight.png"
            weightobj.plot_global_map(figname=figname, lon0=180.0)

    # stats window counts in category level
    cat_wcounts = {}
    for event, event_info in src_wcounts.iteritems():
        for comp, comp_info in event_info.iteritems():
            cat_wcounts.setdefault(comp, 0)
            cat_wcounts[comp] += comp_info

    weights = {}
    ref_dists = {}
    cond_nums = {}
    # nomalization
    for comp in cat_wcounts:
        # ref dist and condition number are the same for different components
        # because the source distribution is exactly the same
        ref_dists[comp] = _ref_dist
        cond_nums[comp] = _cond_num
        wsum = 0
        for point in points:
            nwin = src_wcounts[point.tag][comp]
            wsum += point.weight * nwin
        norm_factor = cat_wcounts[comp] / wsum
        weights[comp] = {}
        for point in points:
            eventname = point.tag
            weights[comp][eventname] = point.weight * norm_factor

    _source_validator(weights, src_wcounts, cat_wcounts)
    return {"src_weights": weights, "cat_wcounts": cat_wcounts,
            "src_ref_dists": ref_dists, "src_cond_nums": cond_nums}


def _category_validator(weights, counts):
    wsum = 0.0
    ncat = 0
    for pw in weights.itervalues():
        wsum += sum(pw.values())
        ncat += len(pw)

    wsum_true = 0.0
    ncat_true = 0
    for pw in counts.itervalues():
        for cw in pw.itervalues():
            wsum_true += 1.0 / cw
            ncat_true += 1
    wsum_true /= ncat

    if ncat_true != ncat:
        raise ValueError("Category validator fails on number of category!")

    if not np.isclose(wsum, wsum_true):
        raise ValueError("Category validator fails: %f, %f" %
                         (wsum, wsum_true))


def determine_category_weighting(cat_wcounts):
    """
    determine the category weighting based on window counts in each category
    """
    logger_block("Category Weighting")
    weights = {}

    ncat = 0
    for period_info in cat_wcounts.itervalues():
        for comp in period_info:
            ncat += 1

    for period, period_info in cat_wcounts.iteritems():
        weights[period] = {}
        for comp in period_info:
            weights[period][comp] = 1.0 / (ncat * period_info[comp])

    logger.info("Category window counts: %s" % cat_wcounts)
    logger.info("Category weights: %s" % weights)
    _category_validator(weights, cat_wcounts)
    return weights


class WindowWeight(object):

    def __init__(self, path, param):
        self.path = load_json(path)
        self.param = load_yaml(param)

        self.src_info = None
        self.weights = None

        self.rec_weights = None
        self.rec_wcounts = None
        self.rec_ref_dists = None
        self.rec_cond_nums = None

        self.src_wcounts = None
        self.src_ref_dists = None
        self.src_cond_nums = None
        self.src_weights = None

        self.cat_wcounts = None
        self.cat_weights = None

    def combine_weights(self):
        """
        Combine weights for receiver weighting, source weighting and
        category weighting
        """
        logger_block("Combine Weighting")
        # combine weights
        # print("source weights:", self.src_weights)
        weights = {}
        for period, period_info in self.rec_weights.iteritems():
            weights[period] = {}
            for event, event_info in period_info.iteritems():
                weights[period][event] = {}
                for comp, comp_info in event_info.iteritems():
                    for chan_id in comp_info:
                        rec_weight = comp_info[chan_id]
                        src_weight = self.src_weights[period][comp][event]
                        cat_weight = self.cat_weights[period][comp]
                        _weight = {"receiver": rec_weight,
                                   "source": src_weight,
                                   "category": cat_weight}
                        _weight["weight"] = \
                            rec_weight * src_weight * cat_weight
                        weights[period][event][chan_id] = _weight

        nwins_array = []
        weights_array = []
        # validate the sum of all weights is 1
        for _p, _pw in weights.iteritems():
            for _e, _ew in _pw.iteritems():
                for _chan, _chanw in _ew.iteritems():
                    nwins_array.append(self.rec_wcounts[_p][_e][_chan])
                    weights_array.append(_chanw["weight"])

        wsum = np.dot(nwins_array, weights_array)
        if not np.isclose(wsum, 1.0):
            raise ValueError("The sum of all weights(%f) does not add "
                             "up to 1.0" % wsum)

        # plot histogram of weights
        logdir = self.path["log_dir"]

        figname = os.path.join(logdir, "weights.hist.png")
        plt.hist(weights_array, 50)
        plt.savefig(figname)

        figname = os.path.join(logdir, "number_of_windows.hist.png")
        plt.hist(nwins_array, 50)
        plt.savefig(figname)

        maxw = max(weights_array)
        minw = min(weights_array)
        logger.info("Total number of receivers: %d" % len(weights_array))
        logger.info("Total number of windows: %d" % np.sum(nwins_array))
        logger.info("Weight max, min, max/min: %f, %f, %f"
                    % (maxw, minw, maxw/minw))

        self.weights = weights
        return {"max_weights": maxw, "min_weights": minw,
                "total_nwindows": np.sum(nwins_array)}

    def analysis_receiver(self, logfile):
        log = {}
        for _p, _pw in self.weights.iteritems():
            log[_p] = {}
            for _e, _ew in _pw.iteritems():
                log[_p][_e] = {}
                maxw = defaultdict(lambda: 0)
                minw = defaultdict(lambda: 10**9)
                for _chan, _chanw in _ew.iteritems():
                    comp = _chan.split(".")[-1]
                    if _chanw["weight"] > maxw[comp]:
                        maxw[comp] = _chanw["weight"]
                    if _chanw["weight"] < minw[comp]:
                        minw[comp] = _chanw["weight"]
                for comp in maxw:
                    log[_p][_e][comp] = \
                        {"maxw": maxw[comp], "minw": minw[comp],
                         "nwindows": self.src_wcounts[_p][_e][comp],
                         "ref_dist": self.rec_ref_dists[_p][_e][comp],
                         "cond_num": self.rec_cond_nums[_p][_e][comp]}

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
        logdir = self.path["log_dir"]
        logfile = os.path.join(logdir, "log.receiver_weights.json")
        logger.info("receiver log file: %s" % logfile)
        self.analysis_receiver(logfile)

        logfile = os.path.join(logdir, "log.source_weights.json")
        logger.info("source log file: %s" % logfile)
        self.analysis_source(logfile)

        logfile = os.path.join(logdir, "log.category_weights.json")
        logger.info("category log file: %s" % logfile)
        self.analysis_category(logfile)

    def dump_weights(self):
        """ dump weights to files """
        for period, period_info in self.weights.iteritems():
            for event, event_info in period_info.iteritems():
                outputfn = self.path['input'][period][event]["output_file"]
                dump_json(event_info, outputfn)

    def calculate_receiver_weights(self):
        """
        calculate receiver weights for each asdf file
        detertmine source weightings based on source infor and window
        count and info
        """
        logger_block("Receiver Weighting")
        input_info = self.path["input"]
        receiver_weighting = self.param["receiver_weighting"]
        plot = self.param["plot"]
        search_ratio = self.param["receiver_search_ratio"]

        self.rec_weights = defaultdict(dict)
        self.rec_wcounts = defaultdict(dict)
        self.rec_ref_dists = defaultdict(dict)
        self.rec_cond_nums = defaultdict(dict)
        self.src_wcounts = defaultdict(dict)

        nperiods = len(input_info)
        period_idx = 0
        # determine receiver weightings for each asdf file
        for period, period_info in input_info.iteritems():
            period_idx += 1
            logger.info("-" * 15 + "[%d/%d]Period band: %s"
                        % (period_idx, nperiods, period) + "-" * 15)
            nevents = len(period_info)
            event_idx = 0
            for event, event_info in period_info.iteritems():
                event_idx += 1
                logger.info("*" * 6 + " [%d/%d]Event: %s "
                            % (event_idx, nevents, event) + "*" * 6)
                # each file still contains 3-component
                logger.info("station file: %s" % event_info["station_file"])
                logger.info("window file: %s" % event_info["window_file"])
                logger.info("output file: %s" % event_info["output_file"])
                src = self.src_info[period][event]
                station_info = load_json(event_info["station_file"])
                window_info = load_json(event_info["window_file"])
                outputdir = os.path.dirname(event_info["output_file"])
                safe_mkdir(outputdir)
                figname_prefix = os.path.join(
                    outputdir, "%s.%s" % (event, period))
                _results = determine_receiver_weighting(
                    src, station_info, window_info,
                    max_ratio=search_ratio,
                    flag=receiver_weighting,
                    plot=plot, figname_prefix=figname_prefix)

                self.rec_weights[period][event] = _results["rec_weights"]
                self.rec_wcounts[period][event] = _results["rec_wcounts"]
                self.rec_ref_dists[period][event] = _results["rec_ref_dists"]
                self.rec_cond_nums[period][event] = _results["rec_cond_nums"]
                self.src_wcounts[period][event] = _results["src_wcounts"]

    def calculate_source_weights(self):
        input_info = self.path["input"]
        logdir = self.path["log_dir"]
        source_weighting = self.param["source_weighting"]
        plot = self.param["plot"]
        search_ratio = self.param["source_search_ratio"]

        self.src_weights = {}
        self.cat_wcounts = {}
        self.src_ref_dists = {}
        self.src_cond_nums = {}
        logger_block("Source Weighting")
        for period, period_info in input_info.iteritems():
            logger.info("-" * 30)
            logger.info("period: %s" % period)
            figname_prefix = os.path.join(
                logdir, "source.%s" % period)
            _results = determine_source_weighting(
                self.src_info[period], self.src_wcounts[period],
                max_ratio=search_ratio,
                flag=source_weighting,
                plot=plot, figname_prefix=figname_prefix)

            self.src_weights[period] = _results["src_weights"]
            self.cat_wcounts[period] = _results["cat_wcounts"]
            self.src_ref_dists[period] = _results["src_ref_dists"]
            self.src_cond_nums[period] = _results["src_cond_nums"]

    def run(self):

        validate_path(self.path)
        validate_param(self.param)

        input_info = self.path["input"]

        self.src_info = extract_source_location(input_info)

        self.calculate_receiver_weights()
        self.calculate_source_weights()
        self.cat_weights = determine_category_weighting(self.cat_wcounts)

        self.combine_weights()
        # statistical analysis
        self.analysis()

        # dump the results out
        self.dump_weights()
