#!/usr/bin/env python
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
import json
import yaml
import argparse
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')  # NOQA
import matplotlib.pyplot as plt
from spaceweight import SpherePoint
from spaceweight import SphereDistRel
from pyasdf import ASDFDataSet
from pypaw.stations import extract_waveform_stations


def load_yaml(filename):
    with open(filename) as fh:
        return yaml.load(fh)


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def dump_json(values, filename):
    with open(filename, 'w') as fh:
        json.dump(values, fh, indent=2, sort_keys=True)


def extract_receiver_locations(asdf, windows):
    """
    Extract receiver location information from asdf file
    """
    stations = [sta_id for sta_id, sta_win in windows.items()
                if len(sta_win) > 0]
    sta_dict = extract_waveform_stations(asdf, stations=stations)
    return sta_dict


def extract_source_location(asdf):
    """
    Extract source location information from asdf file
    """
    event = asdf.events[0]
    origin = event.preferred_origin()
    event_latitude = origin.latitude
    event_longitude = origin.longitude
    event_depth = origin.depth
    return [event_latitude, event_longitude, event_depth]


def _receiver_validator(weights, rec_wcounts, src_wcounts):

    for comp in weights:
        wsum = 0
        for trace_id, trace_weight in weights[comp].iteritems():
            nwin = rec_wcounts[trace_id]
            wsum += trace_weight * nwin

        if not np.isclose(wsum, src_wcounts[comp]):
            raise ValueError("receiver validator fails: %f, %f" %
                             (wsum, src_wcounts[comp]))


def determine_receiver_weighting(asdf_file, window_file, flag=True,
                                 outputdir=None):
    """
    Given one asdf file and window file, determine the receiver
    weighting
    In one asdf file, there are still 3 components, for example,
    ["BHR", "BHT", "BHZ"]. These three components should be treated
    indepandently.

    :return:
    """
    asdf_fh = ASDFDataSet(asdf_file)
    windows = load_json(window_file)
    recs = extract_receiver_locations(asdf_fh, windows)
    src = extract_source_location(asdf_fh)

    center = SpherePoint(src[0], src[1], tag="source")

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
            sta_id = ".".join(chan.split('.')[:2])
            point = SpherePoint(recs[sta_id][0], recs[sta_id][1], tag=chan,
                                weight=1.0)
            points.append(point)

        if flag:
            weightobj = SphereDistRel(points, center=center)
            weightobj.smart_scan(max_ratio=0.35)
            figbase = os.path.basename(asdf_file).rstrip("h5") + \
                "%s.png" % (comp)
            figname = os.path.join(outputdir, figbase)
            weightobj.plot_global_map(figname=figname, lon0=180.0)

        wsum = 0
        for point in points:
            nwin = rec_wcounts[point.tag]
            wsum += point.weight * nwin
        norm_factor = src_wcounts[comp] / wsum

        for point in points:
            weights[comp][point.tag] = point.weight * norm_factor

    _receiver_validator(weights, rec_wcounts, src_wcounts)

    del asdf_fh
    return weights, rec_wcounts, src_wcounts, src


def _source_validator(weights, src_wcounts, cat_counts):
    for comp, comp_weights in weights.iteritems():
        wsum = 0
        for event, event_weights in comp_weights.iteritems():
            wsum += event_weights * src_wcounts[event][comp]
        if not np.isclose(wsum, cat_counts[comp]):
            raise ValueError("Source validator fails!")


def determine_source_weighting(src_info, src_wcounts, flag=True,
                               outputdir=".", tag=""):
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
        point = SpherePoint(event_info[0], event_info[1], tag=eventname,
                            weight=1.0)
        points.append(point)
    if flag:
        weightobj = SphereDistRel(points)
        weightobj.smart_scan(max_ratio=0.35)
        figbase = "source.%s.png" % tag
        figname = os.path.join(outputdir, figbase)
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

    def run(self):
        input_info = self.path["input"]

        # calculate receiver weights for each asdf file
        print("="*30 + "\nCalculating receiver weighting")
        rec_weights = defaultdict(dict)
        rec_wcounts = defaultdict(dict)
        src_wcounts = defaultdict(dict)
        src_info = defaultdict(dict)
        # determine receiver weightings for each file
        for period, period_info in input_info.iteritems():
            print("-"*15 + "\nPeriod band: %s" % period)
            for event, event_info in period_info.iteritems():
                print("*"*8 + "\nEvent %s" % event)
                print("asdf file: %s" % event_info["asdf"])
                print("window file: %s" % event_info["window"])
                _weights, _rec_wcounts, _src_wcounts, _src = \
                    determine_receiver_weighting(
                        event_info["asdf"], event_info["window"],
                        flag=self.param["receiver_weighting"],
                        outputdir=self.path["outputdir"])
                rec_weights[period][event] = _weights
                rec_wcounts[period][event] = _rec_wcounts
                src_wcounts[period][event] = _src_wcounts
                src_info[period][event] = _src

        self.rec_weights = rec_weights
        self.rec_wcounts = rec_wcounts
        self.src_wcounts = src_wcounts
        self.src_info = src_info

        # detertmine source weightings based on source infor and window
        # count and info
        src_weights = {}
        cat_wcounts = {}
        print("="*30 + "\nCalculating source weighting")
        for period, period_info in input_info.iteritems():
            print("-"*15 + "\nperiod: %s" % period)
            _weights, _windows = determine_source_weighting(
                src_info[period], src_wcounts[period],
                flag=self.param["source_weighting"],
                outputdir=self.path["outputdir"],
                tag=period)
            src_weights[period] = _weights
            cat_wcounts[period] = _windows
        self.src_weights = src_weights
        self.cat_wcounts = cat_wcounts

        # determine category weighting
        print("="*30 + "\nCalculating category weighting")
        cat_weights = determine_category_weighting(cat_wcounts)
        self.cat_weights = cat_weights

        print("="*30 + "\nCombine weighting")
        # combine weights
        self.combine_weights()

        # statistical analysis
        print("="*30 + "\nSummary")
        self.analysis()

        # dump the results out
        self.dump_weights()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-p', action='store', dest='param_file', required=True,
                        help="param file")
    args = parser.parse_args()

    weightobj = WindowWeight(args.path_file, args.param_file)
    weightobj.run()
