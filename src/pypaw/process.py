#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parent class for singal processing asdf file and
handles parallel I/O so they are invisible to users.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (print_function, division, absolute_import)
from functools import partial
from pytomo3d.signal.process import process
from .procbase import ProcASDFBase
from .utils import smart_remove_file, smart_check_file


def process_wrapper(stream, inv, param=None):
    """
    Process function wrapper for pyasdf

    :param stream:
    :param inv:
    :param param:
    :return:
    """
    param["inventory"] = inv

    return process(stream, **param)


class ProcASDF(ProcASDFBase):

    def __init__(self, path, param, verbose=False):
        ProcASDFBase.__init__(self, path, param, verbose=verbose)

    def _validate_path(self, path):
        necessary_keys = ["input_asdf", "input_tag",
                          "output_asdf", "output_tag"]

        self._missing_keys(necessary_keys, path)

    def _validate_param(self, param):
        necessary_keys = ["remove_response_flag", "filter_flag", "pre_filt",
                          "relative_starttime", "relative_endtime",
                          "resample_flag", "sampling_rate", "rotate_flag"]

        self._missing_keys(necessary_keys, param)

    def _core(self, path, param):

        self._validate_path(path)
        self._validate_param(param)

        self.print_info(path, extra_info="Path Info")
        self.print_info(param, extra_info="Param Info")

        input_asdf = path["input_asdf"]
        input_tag = path["input_tag"]
        output_asdf = path["output_asdf"]
        output_tag = path["output_tag"]

        if not smart_check_file(input_asdf, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Input file not exists: %s" % input_asdf)
        ds = self.load_asdf(input_asdf, mode='r')

        # read in event
        event = ds.events[0]
        origin = event.preferred_origin() or event.origins[0]
        event_latitude = origin.latitude
        event_longitude = origin.longitude
        event_time = origin.time

        # figure out interpolation parameter
        param["starttime"] = event_time + param["relative_starttime"]
        param["endtime"] = event_time + param["relative_endtime"]
        param["event_latitude"] = event_latitude
        param["event_longitude"] = event_longitude

        process_function = \
            partial(process_wrapper, param=param)

        smart_remove_file(output_asdf, mpi_mode=self.mpi_mode,
                          comm=self.comm)

        tag_map = {input_tag: output_tag}
        ds.process(process_function, output_asdf, tag_map=tag_map)
        del ds
