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
import inspect
import pyadjoint
from pyasdf import ASDFDataSet
from pytomo3d.adjoint import calculate_and_process_adjsrc_on_stream
from pytomo3d.adjoint.process_adjsrc import process_adjoint
from pytomo3d.adjoint.utils import reshape_adj
from .procbase import ProcASDFBase
from .utils import smart_read_json


def check_process_config_keywords(config):
    """ check process_config contains all necessary keywords """
    default_keywords = inspect.getargspec(process_adjoint).args
    deletes = ["adjsrcs", "interp_starttime", "weight_dict", "inventory",
               "event"]
    for d in deletes:
        default_keywords.remove(d)

    if set(default_keywords) != set(config.keys()):
        print("Missing: %s" % (set(default_keywords) - set(config.keys())))
        print("Redundant: %s" % (set(config.keys()) - set(default_keywords)))
        raise ValueError("Process Config Error")


def check_adjoint_config_keywords(config, ConfigClass):
    """
    check adjoint_config contains all necessary keywords when
    loading the keyworkds
    """
    default_keywords = inspect.getargspec(ConfigClass.__init__).args
    deletes = ["self"]
    for d in deletes:
        default_keywords.remove(d)

    if set(default_keywords) != set(config.keys()):
        print("Missing: %s" % (set(default_keywords) - set(config.keys())))
        print("Redundant: %s" % (set(config.keys()) - set(default_keywords)))
        raise ValueError("Adjoint Config Error")


def load_adjoint_config(config, adjsrc_type):
    """
    Load config into pyadjoint.Config
    :param param:
    :return:
    """
    ConfigClass = None
    adjsrc_type = adjsrc_type.lower()
    if adjsrc_type == "multitaper_misfit":
        ConfigClass = pyadjoint.ConfigMultiTaper
    elif adjsrc_type == "cc_traveltime_misfit":
        ConfigClass = pyadjoint.ConfigCrossCorrelation
    elif adjsrc_type == "waveform_misfit":
        ConfigClass = pyadjoint.ConfigWaveForm
    else:
        raise ValueError("Unrecoginsed adj_src_type(%s)" % adjsrc_type)

    check_adjoint_config_keywords(config, ConfigClass)
    return ConfigClass(**config)


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
    if not hasattr(obsd_station_group, "StationXML"):
        print("Missing tag 'STATIONXML' from obsd_station_group %s. Skipped" %
              (obsd_tag, obsd_station_group._station_name))

    try:
        window_sta = windows[obsd_station_group._station_name]
    except:
        return

    observed = getattr(obsd_station_group, obsd_tag)
    synthetic = getattr(synt_station_group, synt_tag)
    obsd_staxml = getattr(obsd_station_group, "StationXML")

    adjsrcs = calculate_and_process_adjsrc_on_stream(
        observed, synthetic, window_sta, obsd_staxml, config, event,
        adj_src_type, postproc_param,
        figure_mode=figure_mode, figure_dir=figure_dir)

    _final = reshape_adj(adjsrcs, obsd_staxml)

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

    @staticmethod
    def _validate_adjoint_param(adjoint_param):
        """
        Check the adjoint parameters. Since we don't know which type
        of adjoint it will be, so we just do a simple check. More
        detailed check will be done later on in function
        `check_config_keywords`.
        """
        if adjoint_param["min_period"] > adjoint_param["max_period"]:
            raise ValueError(
                "Error in param file, min_period(%5.1f) is larger"
                "than max_period(%5.1f)" % (adjoint_param["min_period"],
                                            adjoint_param["max_period"]))

    def _validate_param(self, param):
        """
        Valicate path information

        :param path: path information
        :type path: dict
        :return:
        """
        necessary_keys = ["adjoint_config", "process_config"]
        self._missing_keys(necessary_keys, param)

        self._validate_adjoint_param(param["adjoint_config"])

        process_config = param["process_config"]
        check_process_config_keywords(process_config)

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
        adjoint_param = param["adjoint_config"]
        postproc_param = param["process_config"]

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

        config = load_adjoint_config(adjoint_param, adj_src_type)

        if self.mpi_mode and self.rank == 0:
            output_ds = ASDFDataSet(output_filename, mpi=False)
            if obsd_ds.events:
                output_ds.events = obsd_ds.events
            output_ds.flush()
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
