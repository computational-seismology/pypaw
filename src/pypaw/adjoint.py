#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that calculate adjoint source using asdf

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (absolute_import, division, print_function)
from functools import partial
import pyadjoint
from pyasdf import ASDFDataSet
from pytomo3d.adjoint.adjsrc import calculate_adjsrc_on_stream
from pytomo3d.adjoint.process_adjsrc import process_adjoint
from .procbase import ProcASDFBase
from .adjoint_util import reshape_adj, calculate_chan_weight
from .utils import smart_read_json


def adjoint_wrapper(obsd_station_group, synt_station_group, config=None,
                    obsd_tag=None, synt_tag=None, windows=None, event=None,
                    adj_src_type="multitaper_misfit",
                    postproc_param=None,
                    figure_mode=False, figure_dir=False,
                    adjoint_src_flag=True):

    """
    Function wrapper for pyasdf.

    :param obsd_station_group: observed station group, which contains
        seismogram(stream) and station information(inventory)
    :param synt_station_group: synthetic station group. Same as
        obsd_station_group
    :param config: config object for adjoint source
    :type config: pyadjoint.Config
    :param obsd_tag: observed seismogram tag, used for extracting the
        seismogram in observed asdf file
    :type obsd_tag: str
    :param synt_tag: synthetic seismogram tag, used for extracting the
        seismogram in synthetic asdf file
    :type synt_tag: str
    :param windows: windows for this station group. Two dimension list.
        The first dimension is different channels, the second dimension
        is windows for this channel, like [[chan1_win1, chan1_win2],
        [chan2_win1,], ...]
    :type windows: list
    :param event: event information
    :type event: obspy.Inventory
    :param adj_src_type: adjoint source type, currently support:
        1) "cc_traveltime_misfit"
        2) "multitaper_misfit"
        3) "waveform_misfit"
    :type adj_src_type: st
    :param adjoint_src_flag: calcualte adjoint source, put this to true.
        If false, only make measurements but no adjoint sources.
    :type adjoint_src_flag: bool
    :param figure_mode: plot figures for adjoint source or not
    :type figure_mode: bool
    :param figure_dir: output figure directory
    :type figure_dir: str
    :return: adjoint sources for pyasdf write out(reshaped)
    """
    # Make sure everything thats required is there.
    if not hasattr(obsd_station_group, obsd_tag):
        print("Missing tag '%s' from obsd_station_group %s. Skipped." %
              (obsd_tag, obsd_station_group._station_name))
        return
    if not hasattr(synt_station_group, synt_tag):
        print("Missing tag '%s' from synt_station_group %s. Skipped." %
              (synt_tag, synt_station_group._station_name))
        return
    if not hasattr(synt_station_group, "StationXML"):
        print("Missing tag 'STATIONXML' from synt_station_group %s. Skipped" %
              (synt_tag, synt_station_group._station_name))

    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)
    synt_staxml = getattr(synt_station_group, "StationXML")

    try:
        window_sta = windows[obsd_station_group._station_name]
    except:
        return

    # window_sta = smart_transform_window(window_sta)

    adjsrcs = calculate_adjsrc_on_stream(
        observed, synthetic, window_sta, config, adj_src_type,
        figure_mode=figure_mode, figure_dir=figure_dir,
        adjoint_src_flag=adjoint_src_flag)

    if postproc_param["weight_flag"]:
        chan_weight_dict = calculate_chan_weight(adjsrcs, window_sta)
    else:
        chan_weight_dict = None

    origin = event.preferred_origin() or event.origins[0]
    focal = event.preferred_focal_mechanism()
    hdr = focal.moment_tensor.source_time_function.duration
    # according to SPECFEM starttime convention
    time_offset = -1.5 * hdr
    starttime = origin.time + time_offset

    new_adjsrcs = process_adjoint(
        adjsrcs, interp_starttime=starttime,
        inventory=synt_staxml, event=event,
        weight_dict=chan_weight_dict,
        **postproc_param)

    _final = reshape_adj(new_adjsrcs, time_offset, synt_staxml)

    if _final is None:
        return
    else:
        return _final


class AdjointASDF(ProcASDFBase):
    """
    Adjoint Source ASDF
    """

    def _validate_path(self, path):
        """
        Valicate path information

        :param path: path information
        :type path: dict
        :return:
        """
        necessary_keys = ["obsd_asdf", "obsd_tag", "synt_asdf", "synt_tag",
                          "window_file", "output_file"]
        self._missing_keys(necessary_keys, path)

    def _validate_param(self, param):
        """
        Valicate path information

        :param path: path information
        :type path: dict
        :return:
        """
        necessary_keys = ["adj_src_type", "min_period", "max_period"]
        self._missing_keys(necessary_keys, param)
        if param["min_period"] > param["max_period"]:
            raise ValueError("Error in param file, min_period(%5.1f) is larger"
                             "than max_period(%5.1f)" % (param["min_period"],
                                                         param["max_period"]))

    @staticmethod
    def load_adjoint_config(config):
        """
        Load config into pyadjoint.Config
        :param param:
        :return:
        """
        return pyadjoint.Config(**config)

    def load_windows(self, winfile):
        """
        load window json file

        :param winfile:
        :return:
        """
        return smart_read_json(winfile, mpi_mode=self.mpi_mode,
                               object_hook=False)

    def _core(self, path, param):
        """
        Core function that handles one pair of asdf file(observed and
        synthetic), windows and configuration for adjoint source

        :param path: path information, path of observed asdf, synthetic
            asdf, windows files, observed tag, synthetic tag, output adjoint
            file, figure mode and figure directory
        :type path: dict
        :param param: parameter information for constructing adjoint source
        :type param: dict
        :return:
        """
        adjoint_param = param[0]
        postproc_param = param[1]
        self._validate_path(path)
        self._validate_param(adjoint_param)

        self.print_info(path, extra_info="Path information")
        self.print_info(adjoint_param,
                        extra_info="Adjoint parameter information")
        self.print_info(postproc_param,
                        extra_info="Postprocess parameter information")

        obsd_file = path["obsd_asdf"]
        synt_file = path["synt_asdf"]
        window_file = path["window_file"]
        output_filename = path["output_file"]

        self.check_input_file(obsd_file)
        self.check_input_file(synt_file)
        self.check_input_file(window_file)
        self.check_output_file(output_filename)

        obsd_ds = self.load_asdf(obsd_file, mode="r")
        obsd_tag = path["obsd_tag"]
        synt_ds = self.load_asdf(synt_file, mode="r")
        synt_tag = path["synt_tag"]
        figure_mode = path["figure_mode"]
        figure_dir = path["figure_dir"]

        event = obsd_ds.events[0]
        windows = self.load_windows(window_file)

        adj_src_type = adjoint_param["adj_src_type"]
        adjoint_param.pop("adj_src_type", None)

        config = self.load_adjoint_config(adjoint_param)

        if self.mpi_mode and self.rank == 0:
            output_ds = ASDFDataSet(output_filename, mpi=False)
            if output_ds.events:
                output_ds.events = obsd_ds.events
            del output_ds
        if self.mpi_mode:
            self.comm.barrier()

        adjsrc_func = \
            partial(adjoint_wrapper, config=config,
                    obsd_tag=obsd_tag, synt_tag=synt_tag,
                    windows=windows, event=event,
                    adj_src_type=adj_src_type,
                    postproc_param=postproc_param,
                    figure_mode=figure_mode, figure_dir=figure_dir)

        results = obsd_ds.process_two_files(synt_ds, adjsrc_func,
                                            output_filename)
        return results
