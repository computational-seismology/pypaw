#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parent class for general asdf processing. Wraps things like MPI
and parallel I/O so they are invisible to users.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (absolute_import, division, print_function)
import os
from pyasdf import ASDFDataSet
from mpi4py import MPI
from .utils import smart_read_yaml, smart_read_json, is_mpi_env
from .utils import smart_check_path, smart_remove_file


class ProcASDFBase(object):

    def __init__(self, path, param, verbose=False):

        self.comm = None
        self.rank = None

        self.path = path
        self.param = param
        self._verbose = verbose

    def _parse_yaml(self, content):
        """
        Parse yaml file

        :param content:
        :return:
        """
        if isinstance(content, dict) or isinstance(content, list):
            return content
        elif isinstance(content, str):
            return smart_read_yaml(content, mpi_mode=self.mpi_mode,
                                   comm=self.comm)
        else:
            raise ValueError("Not recogonized input: %s" % content)

    def _parse_json(self, content):
        """
        Parse json file

        :param content:
        :return:
        """
        if isinstance(content, dict) or isinstance(content, list):
            return content
        elif isinstance(content, str):
            return smart_read_json(content, mpi_mode=self.mpi_mode,
                                   comm=self.comm)
        else:
            raise ValueError("Not recogonized input: %s" % content)

    def _parse_path(self):
        """
        How you parse the path arugment to fit your requirements
        """
        return self._parse_json(self.path)

    def _parse_param(self):
        """
        How you parse the param argument to fit your requirements
        """
        return self._parse_yaml(self.param)

    def detect_env(self):
        """
        Detect environment, mpi or not

        :return:
        """
        self.mpi_mode = is_mpi_env()
        if not self.mpi_mode:
            raise EnvironmentError(
                "mpi environment required for parallel"
                "running window selection")
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()

    def print_info(self, dict_obj, extra_info=""):
        """
        Print dict. You can use it to print out information
        for path and param

        :param dict_obj:
        :param extra_info:
        :return:
        """
        def _print_subs(_dict, extra_info=""):
            print("-"*10 + extra_info + "-"*10)
            sorted_dict = sorted(((v, k) for v, k in _dict.iteritems()))
            for key, value in sorted_dict:
                print("%s:  %s" % (key, value))

        if not isinstance(dict_obj, dict):
            raise ValueError("Input dict_obj should be type of dict")

        if not self.mpi_mode:
            _print_subs(dict_obj, extra_info)
        else:
            if self.rank != 0:
                return
            _print_subs(dict_obj, extra_info)

    def load_asdf(self, filename, mode="a"):
        """
        Load asdf file

        :param filename:
        :param mode:
        :return:
        """
        if self.mpi_mode:
            return ASDFDataSet(filename, compression=None, debug=False,
                               mode=mode)
        else:
            return ASDFDataSet(filename, mode=mode)

    def check_input_file(self, filename):
        """
        Check existance of input file. If not, raise ValueError
        """
        if not smart_check_path(filename, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Input file not exists: %s" % filename)

    def check_output_file(self, filename, remove_flag=True):
        """
        Check existance of output file. If directory of output file
        not exists, raise ValueError; If output file exists, remove it
        """
        dirname = os.path.dirname(filename)
        if not smart_check_path(dirname, mpi_mode=self.mpi_mode,
                                comm=self.comm):
            raise ValueError("Output dir not exists: %s" % dirname)

        if smart_check_path(filename, mpi_mode=self.mpi_mode,
                            comm=self.comm):
            if remove_flag:
                if self.rank == 0:
                    print("Output file already exists and removed:%s"
                          % filename)
                smart_remove_file(filename)

    @staticmethod
    def clean_memory(asdf_ds):
        """
        Delete asdf dataset
        """
        del asdf_ds

    @staticmethod
    def _missing_keys(necessary_keys, _dict):
        """
        Check if necessary_keys exists in _dict

        :param necessary_keys:
        :param _dict:
        :return:
        """
        if not isinstance(_dict, dict):
            raise ValueError("Input _dict must be type of dict")
        error_code = 0
        for _key in necessary_keys:
            if _key not in _dict.keys():
                print("%s must be specified in parameter file" % _key)
                error_code = 1
        if error_code:
            raise ValueError("Key values missing in paramter file")

    def _core(self, par_obj, file_obj):
        """
        Dummy here. Core function to fit different purpose.
        """
        pass

    def smart_run(self):
        """
        Job launch method

        :return:
        """
        self.detect_env()

        path = self._parse_path()
        param = self._parse_param()

        if isinstance(path, list):
            for _path in path:
                self._core(_path, param)
        elif isinstance(path, dict):
            self._core(path, param)
        else:
            raise ValueError("Problem in input path...Check")
