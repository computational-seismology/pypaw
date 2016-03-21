#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class for window selection on asdf file and handles parallel I/O
so they are invisible to users.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (absolute_import, division, print_function)
from functools import partial
import os
import json
import numpy as np
from .procbase import ProcASDFBase
from pytomo3d.window.window import window_on_stream
import pyflex
from .utils import smart_read_yaml, smart_mkdir
from .write_window import write_window_json


def window_wrapper(obsd_station_group, synt_station_group, config_dict=None,
                   obsd_tag=None, synt_tag=None,
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
                            station=inv, event=event,
                            figure_mode=figure_mode, figure_dir=figure_dir,
                            _verbose=_verbose)


class WindowASDF(ProcASDFBase):

    def __init__(self, path, param, components=["Z", "R", "T"],
                 verbose=False):

        ProcASDFBase.__init__(self, path, param, verbose=verbose)
        self.components = components

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

        if set(param.keys()) != set(self.components):
            raise ValueError("param should contains the same key(%s) as "
                             "component keys(%s)" % (param.keys(),
                                                     self.components))

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
    def _merge_multiple_instruments(windows):
        """
        Merge windows from multiple instruments by picking the one
        with most number of windows(thus keep only one)
        """
        new_windows = {}

        for sta, sta_win in windows.iteritems():
            sort_dict = {}
            if sta_win is None:
                continue
            for idx, chan in enumerate(sta_win):
                chan_id = chan[0].channel_id
                comp = chan_id.split('.')[-1]
                if comp not in sort_dict:
                    sort_dict[comp] = []
                sort_dict[comp].append([idx, len(chan)])

            choosen_list = []
            for comp, comp_info in sort_dict.iteritems():
                _max_idx = np.array(comp_info)[:, 1].argmax()
                choosen_list.append(sta_win[comp_info[_max_idx][0]])

            new_windows[sta] = choosen_list
        return new_windows

    @staticmethod
    def _stats_all_windows(windows, obsd_tag, synt_tag,
                           instrument_merge_flag,
                           outputdir):
        window_stats = {"obsd_tag": obsd_tag, "synt_tag": synt_tag,
                        "instrument_merge_flag": instrument_merge_flag}
        for sta_name, sta_win in windows.iteritems():
            if sta_win is None:
                continue
            for channel_win in sta_win:
                channel_id = channel_win[0].channel_id
                comp = channel_id.split(".")[-1]
                if comp not in window_stats:
                    window_stats[comp] = {"window": 0, "station": 0}
                window_stats[comp]["window"] += len(channel_win)
                window_stats[comp]["station"] += 1

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

        config_dict, instrument_merge_flag = self.load_window_config(param)

        winfunc = partial(window_wrapper, config_dict=config_dict,
                          obsd_tag=obsd_tag, synt_tag=synt_tag,
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
