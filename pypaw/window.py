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
import importlib
import inspect
import json
import numpy as np
from .procbase import ProcASDFBase
from pytomo3d.window.window import window_on_stream
import pyflex
from .utils import smart_read_yaml, smart_mkdir
from .write_window import write_window_json


def check_param_with_function_args(config):
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

    return window_on_stream(observed, synthetic, config_dict,
                            station=inv, event=event, user_modules=user_modules,
                            figure_mode=figure_mode, figure_dir=figure_dir,
                            _verbose=_verbose)


class WindowASDF(ProcASDFBase):

    def __init__(self, path, param, verbose=False, debug=False):

        ProcASDFBase.__init__(self, path, param, verbose=verbose,
                              debug=debug)

    def _parse_param(self):
        """
        Load param into memory if it is a file. Need a special treatment
        for WindowASDF because we need 3-components parameter file
        """
        param = self.param
        if isinstance(param, str):
            # should be a file
            param = smart_read_yaml(param, mpi_mode=self.mpi_mode)
        if not isinstance(param, dict):
            raise ValueError(
                "param must be dictionary, for example, {'Z': '/path/Z/file',"
                "'R':'/path/R/config', 'T': '/path/T/config'} or "
                "{'Z': pyflex.Config, 'R': pyflex.Config, 'T': pyflex.Config}")

        print("param:", param)

        param_dict = {}
        for key, value in param.iteritems():
            param_dict[key] = self._parse_yaml(value)

        return param_dict

    def _validate_path(self, path):
        necessary_keys = ["obsd_asdf", "obsd_tag", "synt_asdf", "synt_tag",
                          "output_dir", "figure_mode"]
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

    @staticmethod
    def __merge_instruments_window(sta_win):
        """
        Merge windows from the same channel, for example, if
        there are windows from 00.BHZ and 10.BHZ, kepy only one
        with the most windows
        """
        if len(sta_win) == 0:
            return sta_win

        sort_dict = {}
        for trace_id, trace_win in sta_win.iteritems():
            chan = trace_id.split('.')[-1][0:2]
            loc = trace_id.split('.')[-2]
            if chan not in sort_dict:
                sort_dict[chan] = {}
            if loc not in sort_dict[chan]:
                sort_dict[chan][loc] = {"traces": [], "nwins": 0}
            sort_dict[chan][loc]["traces"].append(trace_id)
            sort_dict[chan][loc]["nwins"] += len(trace_win)

        choosen_wins = {}
        for chan, chan_info in sort_dict.iteritems():
            if len(chan_info.keys()) == 1:
                choosen_loc = chan_info.keys()[0]
            else:
                _locs = []
                _nwins = []
                for loc, loc_info in chan_info.iteritems():
                    _locs.append(loc)
                    _nwins.append(loc_info["nwins"])
                _max_idx = np.array(_nwins).argmax()
                choosen_loc = _locs[_max_idx]

            choosen_traces = sort_dict[chan][choosen_loc]["traces"]
            for _trace_id in choosen_traces:
                choosen_wins[_trace_id] = sta_win[_trace_id]

        return choosen_wins

    @staticmethod
    def __merge_channels_window(sta_win):
        """
        Merge windows from different channels.
        This step should be done after merge instruments windows
        because after that there will only one instrument left
        on one channel
        """
        sort_dict = {}

        if len(sta_win) == 0:
            return sta_win

        for trace_id, trace_win in sta_win.iteritems():
            chan = trace_id.split(".")[-1][0:2]
            if chan not in sort_dict:
                sort_dict[chan] = {"traces": [], "nwins": 0}
            sort_dict[chan]["traces"].append(trace_id)
            sort_dict[chan]["nwins"] += len(trace_win)

        choosen_wins = {}
        if len(sort_dict.keys()) == 1:
            choosen_chan = sort_dict.keys()[0]
        else:
            _chans = []
            _nwins = []
            for chan, chan_info in sort_dict.iteritems():
                _chans.append(chan)
                _nwins.append(chan_info["nwins"])
            _max_idx = np.array(_nwins).argmax()
            choosen_chan = _chans[_max_idx]

        choosen_traces = sort_dict[choosen_chan]["traces"]
        for _trace_id in choosen_traces:
            choosen_wins[_trace_id] = sta_win[_trace_id]

        return choosen_wins

    def _merge_multiple_instruments(self, windows):
        """
        Merge windows from multiple instruments by picking the one
        with most number of windows(thus keep only one), for example,
        II.AAK.00.BHZ has 10 windows while II.AAK.10.BHZ has 5 windows.
        Then only II.AAK.00.BHZ will be kept.
        Attention, this flag also merges different channel, for example,
        BH and LH.
        """
        new_windows = {}

        for sta, sta_win in windows.iteritems():
            if sta_win is None:
                continue
            sta_win = self.__merge_instruments_window(sta_win)
            sta_win = self.__merge_channels_window(sta_win)
            new_windows[sta] = sta_win

        return new_windows

    @staticmethod
    def _stats_all_windows(windows, obsd_tag, synt_tag,
                           instrument_merge_flag,
                           outputdir):

        window_stats = {"obsd_tag": obsd_tag, "synt_tag": synt_tag,
                        "instrument_merge_flag": instrument_merge_flag,
                        "stations": 0, "stations_with_windows": 0}
        for sta_name, sta_win in windows.iteritems():
            if sta_win is None:
                continue
            nwin_sta = 0
            for trace_id, trace_win in sta_win.iteritems():
                comp = trace_id.split(".")[-1]
                if comp not in window_stats:
                    window_stats[comp] = {"window": 0, "traces": 0,
                                          "traces_with_windows": 0}
                window_stats[comp]["window"] += len(trace_win)
                if len(trace_win) > 0:
                    window_stats[comp]["traces_with_windows"] += 1
                window_stats[comp]["traces"] += 1
                nwin_sta += len(trace_win)

            window_stats["stations"] += 1
            if nwin_sta > 0:
                window_stats["stations_with_windows"] += 1

        filename = os.path.join(outputdir, "windows.stats.json")
        with open(filename, "w") as fh:
            json.dump(window_stats, fh, indent=2, sort_keys=True)

    @staticmethod
    def load_window_config(param):
        config_dict = {}
        flag_list = []

        for key, value in param.iteritems():
            # pop the "instrument_merge_flag" value out
            flag_list.append(value["instrument_merge_flag"])
            value.pop("instrument_merge_flag")

            check_param_with_function_args(value)
            config_dict[key] = pyflex.Config(**value)

        if not all(_e == flag_list[0] for _e in flag_list):
            raise ValueError("Instrument_merge_flag not consistent amonge"
                             "different parameter yaml files(%s). Check!"
                             % flag_list)

        return config_dict, flag_list[0]

    def _core(self, path, param):

        self._validate_path(path)
        self._validate_param(param)

        self.print_info(path, "Path Info")
        self.print_info(param, "Param Info")

        obsd_file = path["obsd_asdf"]
        synt_file = path["synt_asdf"]
        output_dir = path["output_dir"]

        self.check_input_file(obsd_file)
        self.check_input_file(synt_file)
        smart_mkdir(output_dir, mpi_mode=self.mpi_mode,
                    comm=self.comm)

        obsd_tag = path["obsd_tag"]
        synt_tag = path["synt_tag"]
        figure_mode = path["figure_mode"]
        figure_dir = path["output_dir"]

        obsd_ds = self.load_asdf(obsd_file)
        synt_ds = self.load_asdf(synt_file)

        event = obsd_ds.events[0]

        # Ridvan Orsvuran, 2016
        # take out the user module values
        user_modules = {}
        for key, value in param.iteritems():
            user_modules[key] = value.pop("user_module", None)

        config_dict, instrument_merge_flag = self.load_window_config(param)


        winfunc = partial(window_wrapper, config_dict=config_dict,
                          obsd_tag=obsd_tag, synt_tag=synt_tag,
                          user_modules=user_modules,
                          event=event, figure_mode=figure_mode,
                          figure_dir=figure_dir, _verbose=self._verbose)

        results = \
            obsd_ds.process_two_files(synt_ds, winfunc)

        if self.rank == 0:
            if instrument_merge_flag:
                # merge multiple instruments
                results = self._merge_multiple_instruments(results)
            # stats windows on rand 0
            self._stats_all_windows(results, obsd_tag, synt_tag,
                                    instrument_merge_flag,
                                    path["output_dir"],)

        if self.rank == 0:
            write_window_json(results, output_dir)
