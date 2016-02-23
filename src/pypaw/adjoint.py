#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function)
from functools import partial
import pyadjoint
from pytomo3d.adjoint.adjsrc import calculate_adjsrc_on_stream
from pytomo3d.adjoint.adjsrc import postprocess_adjsrc
from .procbase import ProcASDFBase
from .adjoint_util import reshape_adj, calculate_chan_weight
from .adjoint_util import smart_transform_window
from .utils import smart_read_json, smart_remove_file, smart_check_file


def adjoint_wrapper(obsd_station_group, synt_station_group, config=None,
                    obsd_tag=None, synt_tag=None, windows=None, event=None,
                    adj_src_type="multitaper_misfit", adjoint_src_flag=False,
                    figure_mode=False, figure_dir=False):

    """
    Wrapper for asdf I/O
    """
    # Make sure everything thats required is there.
    if not hasattr(obsd_station_group, obsd_tag):
        print("Missing tag '%s' from obsd_station_group %s" %
              (obsd_tag, obsd_station_group._station_name))
        return
    if not hasattr(synt_station_group, synt_tag):
        print("Missing tag '%s' from synt_station_group" %
              (synt_tag, synt_station_group._station_name))
        return
    if not hasattr(synt_station_group, "StationXML"):
        print("Missing tag 'STATIONXML' from synt_station_group")

    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)
    synt_staxml = getattr(synt_station_group, "StationXML")

    try:
        window_sta = windows[obsd_station_group._station_name]
    except:
        return

    window_sta = smart_transform_window(window_sta)

    adjsrcs = calculate_adjsrc_on_stream(
        observed, synthetic, window_sta, config, adj_src_type,
        figure_mode=figure_mode)

    chan_weight_dict = calculate_chan_weight(adjsrcs, window_sta)

    interp_starttime = adjsrcs[0].starttime - 5.0
    interp_delta = 0.1475
    interp_npts = 42000
    new_adjsrcs = postprocess_adjsrc(
        adjsrcs, interp_starttime, interp_delta,
        interp_npts, rotate_flag=True, inventory=synt_staxml,
        event=event, sum_over_comp_flag=True, weight_flag=True,
        weight_dict=chan_weight_dict, filter_flag=False)

    _final = reshape_adj(new_adjsrcs, 0.0)

    if _final is None:
        return
    else:
        return _final


class AdjointASDF(ProcASDFBase):

    def _validate_path(self, path):
        necessary_keys = ["obsd_asdf", "obsd_tag", "synt_asdf", "synt_tag",
                          "window_file", "output_file"]
        self._missing_keys(necessary_keys, path)

    def _validate_param(self, param):
        necessary_keys = ["adj_src_type", "min_period", "max_period"]
        self._missing_keys(necessary_keys, param)
        if param["min_period"] > param["max_period"]:
            raise ValueError("Error in param file, min_period(%5.1f) is larger"
                             "than max_period(%5.1f)" % (param["min_period"],
                                                         param["max_period"]))

    @staticmethod
    def load_adjoint_config(param):
        return pyadjoint.Config(**param)

    def load_windows(self, winfile):
        return smart_read_json(winfile, mpi_mode=self.mpi_mode,
                               object_hook=False)

    def _core(self, path, param):

        self._validate_path(path)
        self._validate_param(param)

        obsd_file = path["obsd_asdf"]
        synt_file = path["synt_asdf"]
        window_file = path["window_file"]
        if not smart_check_file(obsd_file, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Input obsd_asdf not exists: %s" % obsd_file)
        if not smart_check_file(synt_file, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Input synt_asdf not exists: %s" % synt_file)
        if not smart_check_file(window_file, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Input window_file not exists: %s" % window_file)

        obsd_ds = self.load_asdf(obsd_file)
        obsd_tag = path["obsd_tag"]
        synt_ds = self.load_asdf(synt_file)
        synt_tag = path["synt_tag"]
        output_filename = path["output_file"]
        figure_mode = path["figure_mode"]
        figure_dir = path["figure_dir"]

        smart_remove_file(output_filename, mpi_mode=self.mpi_mode,
                          comm=self.comm)

        event = obsd_ds.events[0]
        windows = self.load_windows(window_file)

        adj_src_type = param["adj_src_type"]
        del param["adj_src_type"]

        config = self.load_adjoint_config(param)

        adjsrc_func = \
            partial(adjoint_wrapper, config=config,
                    obsd_tag=obsd_tag, synt_tag=synt_tag,
                    windows=windows, event=event,
                    adj_src_type=adj_src_type,
                    figure_mode=figure_mode, figure_dir=figure_dir)

        results = obsd_ds.process_two_files(synt_ds, adjsrc_func,
                                            output_filename)
        return results
