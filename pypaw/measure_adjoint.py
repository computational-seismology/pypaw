#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that calculate adjoint source using asdf

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (absolute_import, division, print_function)
from functools import partial
from pyasdf import ASDFDataSet
from pytomo3d.adjoint import measure_adjoint_on_stream
from .adjoint import load_adjoint_config, AdjointASDF
from .utils import dump_json


def write_measurements(content, filename):
    content_filter = dict(
        (k, v) for k, v in content.iteritems() if v is not None)
    dump_json(content_filter, filename)


def measure_adjoint_wrapper(
        obsd_station_group, synt_station_group, config=None,
        obsd_tag=None, synt_tag=None, windows=None,
        adj_src_type="multitaper_misfit"):

    # Make sure everything thats required is there.
    if not hasattr(obsd_station_group, obsd_tag):
        print("Missing tag '%s' from obsd_station_group %s. Skipped." %
              (obsd_tag, obsd_station_group._station_name))
        return
    if not hasattr(synt_station_group, synt_tag):
        print("Missing tag '%s' from synt_station_group %s. Skipped." %
              (synt_tag, synt_station_group._station_name))
        return
    if not hasattr(obsd_station_group, "StationXML"):
        print("Missing tag 'STATIONXML' from obsd_station_group %s. Skipped" %
              (obsd_tag, obsd_station_group._station_name))

    try:
        window_sta = windows[obsd_station_group._station_name]
    except:
        return

    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)

    results = measure_adjoint_on_stream(
        observed, synthetic, window_sta, config, adj_src_type,
        figure_mode=False, figure_dir=None)

    return results


class MeasureAdjointASDF(AdjointASDF):
    """
    Make measurements on ASDF file. The output file is the json
    file which contains measurements for all the windows in
    the window file
    """
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
        adjoint_param = param["adjoint_config"]
        postproc_param = param["process_config"]
        self._validate_path(path)
        self._validate_param(adjoint_param)

        self.print_info(path, extra_info="Path information")
        self.print_info(adjoint_param,
                        extra_info="Adjoint parameter information")
        self.print_info(postproc_param,
                        extra_info="Postprocess parameter information")

        obsd_file = path["obsd_asdf"]
        synt_file = path["synt_asdf"]
        obsd_tag = path["obsd_tag"]
        synt_tag = path["synt_tag"]
        window_file = path["window_file"]
        output_filename = path["output_file"]

        self.check_input_file(obsd_file)
        self.check_input_file(synt_file)
        self.check_input_file(window_file)
        self.check_output_file(output_filename)

        obsd_ds = self.load_asdf(obsd_file, mode="r")
        synt_ds = self.load_asdf(synt_file, mode="r")

        windows = self.load_windows(window_file)

        adj_src_type = adjoint_param["adj_src_type"]
        adjoint_param.pop("adj_src_type", None)

        config = load_adjoint_config(adjoint_param, adj_src_type)

        if self.mpi_mode and self.rank == 0:
            output_ds = ASDFDataSet(output_filename, mpi=False)
            if output_ds.events:
                output_ds.events = obsd_ds.events
            del output_ds
        if self.mpi_mode:
            self.comm.barrier()

        measure_adj_func = \
            partial(measure_adjoint_wrapper, config=config,
                    obsd_tag=obsd_tag, synt_tag=synt_tag,
                    windows=windows,
                    adj_src_type=adj_src_type)

        results = obsd_ds.process_two_files(synt_ds, measure_adj_func)

        if self.rank == 0:
            print("output filename: %s" % output_filename)
            write_measurements(results, output_filename)
