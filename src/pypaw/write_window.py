#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Methods for write out windows

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function
import os
import json
import obspy
import numpy as np


def get_json_content(window):
    # to be compatable with old version of pyflex, which doesn't
    # have window.channel_id_2
    info = {
        "left_index": window.left,
        "right_index": window.right,
        "center_index": window.center,
        "channel_id": window.channel_id,
        "time_of_first_sample": window.time_of_first_sample,
        "max_cc_value":  window.max_cc_value,
        "cc_shift_in_samples":  window.cc_shift,
        "cc_shift_in_seconds":  window.cc_shift_in_seconds,
        "dlnA":  window.dlnA,
        "dt": window.dt,
        "min_period": window.min_period,
        # "phase_arrivals": window.phase_arrivals,
        "absolute_starttime": window.absolute_starttime,
        "absolute_endtime": window.absolute_endtime,
        "relative_starttime": window.relative_starttime,
        "relative_endtime": window.relative_endtime,
        "window_weight": window.weight}

    if "channel_id_2" in dir(window):
        info["channel_id_2"] = window.channel_id_2

    return info


class WindowEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, obspy.UTCDateTime):
            return str(obj)
        # Numpy objects also require explicit handling.
        elif isinstance(obj, np.int64):
            return int(obj)
        elif isinstance(obj, np.int32):
            return int(obj)
        elif isinstance(obj, np.float64):
            return float(obj)
        elif isinstance(obj, np.float32):
            return float(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def write_window_json(results, outputdir):

    output_json = os.path.join(outputdir, "windows.json")
    print("Output window file: %s" % output_json)
    window_all = {}
    for station, sta_win in results.iteritems():
        if sta_win is None:
            continue
        window_all[station] = {}
        _window_comp = {}
        for trace_id, trace_win in sta_win.iteritems():
            _window = [get_json_content(_i) for _i in trace_win]
            _window_comp[trace_id] = _window
        window_all[station] = _window_comp

    with open(output_json, 'w') as fh:
        j = json.dumps(window_all, cls=WindowEncoder, sort_keys=True,
                       indent=2, separators=(',', ':'))
        try:
            fh.write(j)
        except TypeError:
            fh.write(j.encode())
