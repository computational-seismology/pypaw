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
import matplotlib.pyplot as plt
plt.switch_backend('agg')  # NOQA

from spaceweight import SpherePoint
from spaceweight import SphereDistRel
from pyasdf import ASDFDataSet
from pypaw.bins.utils import load_json, dump_json, load_yaml


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
    print("Extracting source location information")
    src_info = defaultdict(dict)
    for period, period_info in input_info.iteritems():
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
    Given one asdf file and window file, determine the receiver
    weighting
    In one asdf file, there are still 3 components, for example,
    ["BHR", "BHT", "BHZ"]. These three components should be treated
    indepandently.

    :return:
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
    for comp, comp_info in weights.iteritems():
        points = []
        print("Components:%s" % comp)
        for chan in comp_info:
            zchan = chan[:-3] + "BHZ"
            point = SpherePoint(stations[zchan]["latitude"],
                                stations[zchan]["longitude"],
                                tag=chan,
                                weight=1.0)
            points.append(point)

        if flag:
            # calculate weight; otherwise, leave it as default value(1)
            weightobj = SphereDistRel(points, center=center)
            weightobj.smart_scan(max_ratio=max_ratio)
            if plot:
                figname = figname_prefix + "%s.png" % comp
                weightobj.plot_global_map(figname=figname, lon0=180.0)

        wsum = 0
        for point in points:
            nwin = rec_wcounts[point.tag]
            wsum += point.weight * nwin
        norm_factor = src_wcounts[comp] / wsum

        for point in points:
            weights[comp][point.tag] = point.weight * norm_factor

    _receiver_validator(weights, rec_wcounts, src_wcounts)

    return weights, rec_wcounts, src_wcounts


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
    Determine the source weighting based on source distribution
    Attention here, there is still 3 components and each category
    should be weighting independently with the window count information
    in this components
    """
    print("Number of sources: %s" % len(src_info))
    print("Window counts information: %s" % src_wcounts)

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
        weightobj.smart_scan(max_ratio=max_ratio)
        if plot:
            figname = figname_prefix + ".png"
            weightobj.plot_global_map(figname=figname, lon0=180.0)

    # stats window counts in category level
    cat_wcounts = {}
    for event, event_info in src_wcounts.iteritems():
        for comp, comp_info in event_info.iteritems():
            cat_wcounts.setdefault(comp, 0)
            cat_wcounts[comp] += comp_info

    weights = {}
    # nomalization
    for comp in cat_wcounts:
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
    return weights, cat_wcounts


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
    print("="*30 + "\nCalculating category weighting")
    weights = {}

    ncat = 0
    for period_info in cat_wcounts.itervalues():
        for comp in period_info:
            ncat += 1

    for period, period_info in cat_wcounts.iteritems():
        weights[period] = {}
        for comp in period_info:
            weights[period][comp] = 1.0 / (ncat * period_info[comp])

    print("Category window counts:%s" % cat_wcounts)
    print("Category weights: %s" % weights)
    _category_validator(weights, cat_wcounts)
    return weights


class WindowWeight(object):

    def __init__(self, path, param):
        self.path = load_json(path)
        self.param = load_yaml(param)

        self.weights = None

        self.rec_weights = None
        self.rec_wcounts = None

        self.src_info = None
        self.src_wcounts = None
        self.src_weights = None

        self.cat_wcounts = None
        self.cat_weights = None

    def combine_weights(self):
        """
        Combine weights
        """
        print("="*30 + "\nCombine weighting")
        # combine weights
        print("source weights:", self.src_weights)
        print("category weights:", self.cat_weights)
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
        self.weights = weights

    def analysis(self):
        print("="*30 + "\nSummary")
        weights = []
        nwins = []
        for _p, _pw in self.weights.iteritems():
            for _e, _ew in _pw.iteritems():
                for _c, _cw in _ew.iteritems():
                    nwins.append(self.rec_wcounts[_p][_e][_c])
                    weights.append(_cw["weight"])

        weights = np.array(weights)
        nwins = np.array(nwins)
        minv = np.min(weights)
        maxv = np.max(weights)

        print("Total number of receivers:", len(weights))
        print("Total number of windows:", np.sum(nwins))
        print("Weight max, min, max/min:", maxv, minv, maxv/minv)
        print("The summation of weights: %f" % np.dot(nwins, weights))

        # plot histogram of weights
        plt.hist(weights, 50)
        figname = os.path.join(self.path["outputdir"], "weights.hist.png")
        plt.savefig(figname)

    def dump_weights(self):
        outputdir = self.path["outputdir"]
        print("output directory:", outputdir)
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)

        for period, period_info in self.weights.iteritems():
            for event, event_info in period_info.iteritems():
                outputfn = os.path.join(
                    outputdir, "%s.%s.weight.json" % (event, period))
                dump_json(event_info, outputfn)

    def calculate_receiver_weights(self):
        """
        calculate receiver weights for each asdf file
        detertmine source weightings based on source infor and window
        count and info
        """
        print("="*30 + "\nCalculating receiver weighting")
        input_info = self.path["input"]
        outputdir = self.path["outputdir"]
        receiver_weighting = self.param["receiver_weighting"]
        plot = self.param["plot"]

        rec_weights = defaultdict(dict)
        rec_wcounts = defaultdict(dict)
        src_wcounts = defaultdict(dict)
        # determine receiver weightings for each file
        for period, period_info in input_info.iteritems():
            print("-"*15 + "\nPeriod band: %s" % period)
            for event, event_info in period_info.iteritems():
                print("*"*8 + "\nEvent %s" % event)
                print("station file: %s" % event_info["station_file"])
                print("window file: %s" % event_info["window_file"])
                src = self.src_info[period][event]
                station_info = load_json(event_info["station_file"])
                window_info = load_json(event_info["window_file"])
                figname_prefix = os.path.join(
                    outputdir, "%s.%s." % (event, period))
                _weights, _rec_wcounts, _src_wcounts = \
                    determine_receiver_weighting(
                        src, station_info, window_info,
                        flag=receiver_weighting,
                        plot=plot, figname_prefix=figname_prefix)

                rec_weights[period][event] = _weights
                rec_wcounts[period][event] = _rec_wcounts
                src_wcounts[period][event] = _src_wcounts

        self.rec_weights = rec_weights
        self.rec_wcounts = rec_wcounts
        self.src_wcounts = src_wcounts

    def calculate_source_weights(self):
        input_info = self.path["input"]
        outputdir = self.path["outputdir"]
        source_weighting = self.param["source_weighting"]
        plot = self.param["plot"]

        src_weights = {}
        cat_wcounts = {}
        print("="*30 + "\nCalculating source weighting")
        for period, period_info in input_info.iteritems():
            print("-"*15 + "\nperiod: %s" % period)
            figname_prefix = os.path.join(
                outputdir, "source.%s." % period)
            _weights, _windows = determine_source_weighting(
                self.src_info[period], self.src_wcounts[period],
                flag=source_weighting,
                plot=plot, figname_prefix=figname_prefix)
            src_weights[period] = _weights
            cat_wcounts[period] = _windows

        self.src_weights = src_weights
        self.cat_wcounts = cat_wcounts

    def run(self):

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
