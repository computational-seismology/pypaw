#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class for window selection on asdf file and handles parallel I/O
so they are invisible to users.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (absolute_import, division, print_function)
from functools import partial
import os
import inspect
from copy import deepcopy
import json
import pyflex
from pytomo3d.window.window import window_on_stream
from pytomo3d.window.utils import merge_windows, stats_all_windows
from pytomo3d.window.io import get_json_content, WindowEncoder
from .utils import smart_mkdir
from .procbase import ProcASDFBase


def check_param_keywords(config):
    deletes = ["self", "noise_start_index", "noise_end_index",
               "signal_start_index", "signal_end_index",
               "window_weight_fct"]

    default_keywords = inspect.getargspec(pyflex.Config.__init__).args
    for d in deletes:
        default_keywords.remove(d)

    if set(default_keywords) != set(config.keys()):
        print("Missing: %s" % (set(default_keywords) - set(config.keys())))
        print("Redundant: %s" % (set(config.keys()) - set(default_keywords)))
        raise ValueError("config file is missing values compared to "
                         "pyflex.Config")


def load_window_config(param):
    config_dict = {}
    flag_list = []

    for key, value in param.iteritems():
        # pop the "instrument_merge_flag" value out
        flag_list.append(value["instrument_merge_flag"])
        value.pop("instrument_merge_flag")

        check_param_keywords(value)
        config_dict[key] = pyflex.Config(**value)

    if not all(_e == flag_list[0] for _e in flag_list):
        raise ValueError("Instrument_merge_flag not consistent amonge"
                         "different parameter yaml files(%s). Check!"
                         % flag_list)

    return config_dict, flag_list[0]


def write_window_json(results, output_file):

    print("Output window file: %s" % output_file)
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

    with open(output_file, 'w') as fh:
        j = json.dumps(window_all, cls=WindowEncoder, sort_keys=True,
                       indent=2, separators=(',', ':'))
        try:
            fh.write(j)
        except TypeError:
            fh.write(j.encode())


def window_wrapper(obsd_station_group, synt_station_group, config_dict=None,
                   obsd_tag=None, synt_tag=None, user_modules=None,
                   event=None, figure_mode=False, figure_dir=None,
                   _verbose=False):
    """
    Wrapper for asdf I/O
    """
    # Make sure everything thats required is there.
    if not hasattr(synt_station_group, "StationXML"):
        print("Missing StationXML from synt_staiton_group")
        return
    if not hasattr(obsd_station_group, obsd_tag):
        print("Missing tag '%s' from obsd_station_group" % obsd_tag)
        return
    if not hasattr(synt_station_group, synt_tag):
        print("Missing tag '%s' from synt_station_group" % synt_tag)
        return

    inv = synt_station_group.StationXML
    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)

    return window_on_stream(
        observed, synthetic, config_dict, station=inv,
        event=event, user_modules=user_modules,
        figure_mode=figure_mode, figure_dir=figure_dir,
        _verbose=_verbose)


class WindowASDF(ProcASDFBase):

    def __init__(self, path, param, verbose=False, debug=False):

        ProcASDFBase.__init__(self, path, param, verbose=verbose,
                              debug=debug)

    def _parse_param(self):
        myrank = self.comm.Get_rank()
        param = self._parse_yaml(self.param)

        # reform the param from default
        default = param["default"]
        comp_settings = param["components"]
        results = {}
        for _comp, _settings in comp_settings.iteritems():
            if myrank == 0:
                print("Preapring params for components: %s" % _comp)
            results[_comp] = deepcopy(default)
            if _settings is None:
                continue
            for k, v in _settings.iteritems():
                if myrank == 0:
                    print("--> Modify key[%s] to value: %s --> %s"
                          % (k, results[_comp][k], v))
                results[_comp][k] = v

        return results

    def _validate_path(self, path):
        necessary_keys = ["obsd_asdf", "obsd_tag", "synt_asdf", "synt_tag",
                          "output_file", "figure_mode"]
        self._missing_keys(necessary_keys, path)

    def _validate_param(self, param):
        for key, value in param.iteritems():
            necessary_keys = ["min_period", "max_period", "selection_mode"]
            self._missing_keys(necessary_keys, value)
            minp = value["min_period"]
            maxp = value["max_period"]
            if minp > maxp:
                raise ValueError("min_period(%6.2f) is larger than max_period"
                                 "(%6.2f)" % (minp, maxp))

    def _core(self, path, param):

        obsd_file = path["obsd_asdf"]
        synt_file = path["synt_asdf"]
        output_file = path["output_file"]
        output_dir = os.path.dirname(output_file)

        self.check_input_file(obsd_file)
        self.check_input_file(synt_file)
        smart_mkdir(output_dir, mpi_mode=self.mpi_mode,
                    comm=self.comm)

        obsd_tag = path["obsd_tag"]
        synt_tag = path["synt_tag"]
        figure_mode = path["figure_mode"]
        figure_dir = output_dir

        obsd_ds = self.load_asdf(obsd_file)
        synt_ds = self.load_asdf(synt_file)

        event = obsd_ds.events[0]

        # Ridvan Orsvuran, 2016
        # take out the user module values
        user_modules = {}
        for key, value in param.iteritems():
            user_modules[key] = value.pop("user_module", None)

        config_dict, instrument_merge_flag = load_window_config(param)

        winfunc = partial(window_wrapper, config_dict=config_dict,
                          obsd_tag=obsd_tag, synt_tag=synt_tag,
                          user_modules=user_modules,
                          event=event, figure_mode=figure_mode,
                          figure_dir=figure_dir, _verbose=self._verbose)

        windows = \
            obsd_ds.process_two_files(synt_ds, winfunc)

        if self.rank == 0:
            if instrument_merge_flag:
                # merge multiple instruments
                results = merge_windows(windows)
            else:
                # nothing is done
                results = windows

            stats_logfile = os.path.join(output_dir, "windows.stats.json")
            # stats windows on rand 0
            stats_all_windows(results, obsd_tag, synt_tag,
                              instrument_merge_flag,
                              stats_logfile)

            write_window_json(results, output_file)
