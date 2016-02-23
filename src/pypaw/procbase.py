#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function)
from pyasdf import ASDFDataSet
from mpi4py import MPI
from .utils import smart_read_yaml, is_mpi_env


class ProcASDFBase(object):

    def __init__(self, path, param, verbose=False):

        self.comm = None
        self.rank = None

        self.path = path
        self.param = param
        self._verbose = verbose

    def _parse_yaml(self, content):
        if isinstance(content, dict) or isinstance(content, list):
            return content
        elif isinstance(content, str):
            return smart_read_yaml(content, mpi_mode=self.mpi_mode)
        else:
            raise ValueError("Not recogonized input: %s" % content)

    def _parse_path(self):
        """
        How you parse the path arugment to fit your requirements
        """
        return self._parse_yaml(self.path)

    def _parse_param(self):
        """
        How you parse the param argument to fit your requirements
        """
        return self._parse_yaml(self.param)

    def detect_env(self):
        # detect environment
        self.mpi_mode = is_mpi_env()
        if not self.mpi_mode:
            raise EnvironmentError(
                "mpi environment required for parallel"
                "running window selection")
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()

    def print_info(self, dict_obj, extra_info=""):
        print("-"*10 + extra_info + "-"*10)
        if not isinstance(dict_obj):
            raise ValueError("Input dict_obj should be type of dict")
        if self.rank != 0:
            return
        for key, value in dict_obj.iteritems():
            print("%s:%s" % (key, value))

    def load_asdf(self, filename):
        if self.mpi_mode:
            return ASDFDataSet(filename, compression=None, debug=False)
        else:
            return ASDFDataSet(filename)

    @staticmethod
    def clean_memory(asdf_ds):
        del asdf_ds

    @staticmethod
    def _missing_keys(necessary_keys, _dict):
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
        Dump example
        """
        pass

    def smart_run(self):

        self.detect_env()

        path = self._parse_path()
        param = self._parse_param()

        if isinstance(path, list) and isinstance(param, list):
            if len(path) != len(param):
                raise ValueError("Lengths of params and dirs files"
                                 "do not match")
            for _path, _param in zip(path, param):
                self._core(_path, _param)
        elif isinstance(path, list) and isinstance(param, dict):
            for _path in path:
                self._core(_path, param)
        elif isinstance(path, dict) and isinstance(param, dict):
            self._core(path, param)
        else:
            raise ValueError("Problem in input param and path...Check")
