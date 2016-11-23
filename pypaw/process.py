#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parent class for singal processing asdf file and
handles parallel I/O so they are invisible to users.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (print_function, division, absolute_import)
import inspect
from functools import partial
from pytomo3d.signal.process import process_stream
from .procbase import ProcASDFBase


def check_param_keywords(param):
    """
    Check the param keywords are the same with the keywords list of
    the function of process_stream
    """
    default_param = inspect.getargspec(process_stream).args
    default_param.remove("st")
    default_param.remove("inventory")
    if set(default_param) != set(param.keys()):
        print("Missing: %s" % (set(default_param) - set(param.keys())))
        print("Redundant: %s" % (set(param.keys()) - set(default_param)))
        raise ValueError("Param is not consistent with function argument list")


def process_wrapper(stream, inv, param=None):
    """
    Process function wrapper for pyasdf

    :param stream:
    :param inv:
    :param param:
    :return:
    """
    param["inventory"] = inv
    return process_stream(stream, **param)


def update_param(event, param):
    """ update the param based on event information """
    origin = event.preferred_origin()
    origin = event.preferred_origin()
    event_latitude = origin.latitude
    event_longitude = origin.longitude
    event_time = origin.time

    # figure out interpolation parameter
    param["starttime"] = event_time + param["relative_starttime"]
    param.pop("relative_starttime")
    param["endtime"] = event_time + param["relative_endtime"]
    param.pop("relative_endtime")
    param["event_latitude"] = event_latitude
    param["event_longitude"] = event_longitude


class ProcASDF(ProcASDFBase):

    def __init__(self, path, param, verbose=False, debug=False):
        ProcASDFBase.__init__(self, path, param, verbose=verbose,
                              debug=debug)

    def _validate_path(self, path):
        necessary_keys = ["input_asdf", "input_tag",
                          "output_asdf", "output_tag"]

        self._missing_keys(necessary_keys, path)

    def _validate_param(self, param):
        necessary_keys = ("remove_response_flag", "filter_flag", "pre_filt",
                          "relative_starttime", "relative_endtime",
                          "resample_flag", "sampling_rate", "rotate_flag",
                          "sanity_check")

        self._missing_keys(necessary_keys, param)

    def _core(self, path, param):

        input_asdf = path["input_asdf"]
        input_tag = path["input_tag"]
        output_asdf = path["output_asdf"]
        output_tag = path["output_tag"]

        self.check_input_file(input_asdf)
        self.check_output_file(output_asdf, remove_flag=True)

        # WJ: set to 'a' for now since SPECFEM output is
        # a incomplete asdf file, missing the "auxiliary_data"
        # part. So give it 'a' permission to add the part.
        # otherwise, it there will be errors
        ds = self.load_asdf(input_asdf, mode='a')

        # update param based on event information
        update_param(ds.events[0], param)
        # check final param to see if the keys are right
        check_param_keywords(param)

        process_function = \
            partial(process_wrapper, param=param)

        tag_map = {input_tag: output_tag}
        ds.process(process_function, output_asdf, tag_map=tag_map)

        del ds
