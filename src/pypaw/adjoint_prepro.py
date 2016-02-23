#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that handles the whole preprocessing workflow, including:
    1) signal processing
    2) window selection
    3) adjoint sources

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (absolute_import, division, print_function)
import os
from functools import partial

from .procbase import ProcASDFBase
from pytomo3d.signal.proc_util import process
from pytomo3d.adjsrc.adjsrc_function import adjsrc_function
from pytomo3d.adjsrc.adjsrc_function import postprocess_adjsrc
from pytomo3d.window.window import window_on_stream
from .adjoint_util import calculate_chan_weight, reshape_adj


def func_wrapper(obsd_station_group, synt_station_group, obsd_tag=None,
                 synt_tag=None, event=None, param=None, _verbose=False,
                 figure_mode=False):
    """
    combo function, including:
    1) observed data signal processing
    2) synthetic data signal processing
    3) window selection based on a pair of data
    4) adjoint source constructor
    """
    # Make sure everything thats required is there.
    if not hasattr(obsd_station_group, "StationXML") or \
            not hasattr(obsd_station_group, obsd_tag) or \
            not hasattr(synt_station_group, synt_tag) or \
            not hasattr(synt_station_group, "StationXML"):
        print("Missing attr, return")
        return

    obsd_staxml = obsd_station_group.StationXML
    synt_staxml = synt_station_group.StationXML
    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)

    _raw_synt = synthetic.copy()

    obsd_param = param["obsd_param"]
    new_obsd = process(observed, inventory=obsd_staxml, **obsd_param)

    synt_param = param["synt_param"]
    new_synt = process(synthetic, inventory=synt_staxml, **synt_param)

    window_config = param["window_param"]
    windows = window_on_stream(new_obsd, new_synt, window_config,
                               station=synt_staxml, event=event,
                               figure_mode=figure_mode, figure_dir=None,
                               _verbose=_verbose)

    adjsrc_config = param["adjoint_param"]
    adj_src_type = adjsrc_config["adj_src_type"]
    del adjsrc_config["adj_src_type"]
    adjsrcs, nwins_dict = adjsrc_function(
        new_obsd, new_synt, windows, adjsrc_config,  adj_src_type,
        adjoint_src_flag=True, figure_mode=figure_mode)

    # adjsrcs, nwins_dict = ensemble_fake_adj(new_synt)

    chan_weight_dict = calculate_chan_weight(nwins_dict)

    adj_new, time_offset = \
        postprocess_adjsrc(adjsrcs, new_synt[0].stats.starttime,
                           _raw_synt, synt_staxml, event,
                           sum_over_comp=True,
                           weight_dict=chan_weight_dict)

    results = reshape_adj(adj_new, time_offset)

    return results


class AdjPreASDF(ProcASDFBase):

    def __init__(self, path, param, components=["Z", "R", "T"],
                 verbose=False):

        ProcASDFBase.__init__(path, param, verbose=verbose)

        self.components = components

    def _parse_param(self):
        """
        Load param file
        """
        param = self.param
        if isinstance(param, str):
            param = self.__parse_yaml(param)

        param_dict = {}
        keys = ["proc_obsd_param", "proc_synt_param", "adjsrc_param"]
        for key in keys:
            param_dict[key] = self.__parse_yaml(param[key])

        param_dict["window_param"] = \
            self.__load_window_param(param["window_param"])

        self.param = param_dict

    def __load_window_param(self, window_param):
        """
        load window param
        """
        if set(window_param.keys()) == set(self.components):
            raise ValueError("window param '%s' components(%s) is "
                             "inconsistent with init settings(%s)"
                             % (window_param, window_param.keys,
                                self.components))
        param_dict = {}
        for key, value in window_param:
            param_dict[key] = self.__parse_yaml(value)
        return param_dict

    def _validate_path(self, path):
        necessary_keys = ["obsd_asdf", "obsd_tag", "synt_asdf", "synt_tag",
                          "output_asdf"]
        self.__missing_keys(necessary_keys, path)

    def _valicate_param(self, param):
        necessary_keys = ["proc_obsd_param", "proc_synt_param", "adjsrc_param",
                          "window_param"]
        self.__missing_keys(necessary_keys, param)

    def __refine_signalproc_param(sparam, event):
        origin = event.preferred_origin() or event.origin[0]
        event_time = origin.time
        event_latitude = origin.event_latitude
        event_longitude = origin.event_longitude
        sparam["starttime"] = event_time + sparam["relative_starttime"]
        sparam["endtime"] = event_time + sparam["relative_endtime"]
        sparam["event_latitude"] = event_latitude
        sparam["event_longitude"] = event_longitude

    def _refine_param(self, event):
        """
        Refine event-based parameter, for example, some parameters
        in signal processing stage
        """
        obsd_param = self.param["proc_obsd_param"]
        self.__refine_signalproc_param(obsd_param, event)
        synt_param = self.param["proc_synt_param"]
        self.__refine_signalproc_param(synt_param, event)

    def _launch(self, path, param):

        self._validate_path(path)
        self._validate_param(param)

        obsd_ds = self.load_asdf(path["obsd_asdf"])
        obsd_tag = path["obsd_tag"]
        synt_ds = self.load_asdf(path["synt_asdf"])
        synt_tag = path["synt_tag"]
        output_asdf = path["output_asdf"]

        event = obsd_ds.events[0]

        self._refine_param(event)

        proc_func = partial(func_wrapper, event=event, obsd_tag=obsd_tag,
                            synt_tag=synt_tag, param=self.param)

        if self.rank == 0:
            if os.path.exists(output_asdf):
                print("remove output:", output_asdf)
                os.remove(output_asdf)
        self.comm.Barrier()

        obsd_ds.process_two_files(
            synt_ds, proc_func, output_filename=output_asdf)
