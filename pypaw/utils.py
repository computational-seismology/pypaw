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
import sys
import json
import os
import time
import yaml


def is_mpi_env():
    """
    Test if current environment is MPI or not
    """
    try:
        import mpi4py
    except ImportError:
        return False

    try:
        import mpi4py.MPI
    except ImportError:
        return False

    if mpi4py.MPI.COMM_WORLD.size == 1 and mpi4py.MPI.COMM_WORLD.rank == 0:
        return False

    return True


def _get_mpi_comm():
    from mpi4py import MPI
    return MPI.COMM_WORLD


def dump_json(content, filename):
    with open(filename, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


class JSONObject(object):
    def __init__(self, d):
        self.__dict__ = d


def read_json_file(parfile, obj_hook=True):
    """
    Hook json to an JSONObject instance
    """
    if not os.path.exists(parfile):
        raise ValueError("parfile not exists:%s" % parfile)
    with open(parfile, 'r') as f:
        if obj_hook:
            data = json.load(f, object_hook=JSONObject)
        else:
            data = json.load(f)
    return data


def smart_read_json(json_file, mpi_mode=True, comm=None, object_hook=False):
    """
    read json file under mpi and multi-processing environment.
    Hook it to an JSONObject(not the conventional way to
    read it as object)
    """
    if not mpi_mode:
        json_obj = read_json_file(json_file, obj_hook=object_hook)
    else:
        if comm is None:
            comm = _get_mpi_comm()
        rank = comm.Get_rank()
        if rank == 0:
            try:
                json_obj = read_json_file(json_file, obj_hook=object_hook)
            except Exception as err:
                print("Error in %s:%s" % (json_file, err))
                comm.Abort()
        else:
            json_obj = None
        json_obj = comm.bcast(json_obj, root=0)
    return json_obj


def read_yaml_file(filename):
    with open(filename) as fh:
        return yaml.load(fh)


def smart_read_yaml(yaml_file, mpi_mode=True, comm=None):
    """
    Read yaml file into python dict, in mpi_mode or not
    """
    if not mpi_mode:
        yaml_dict = read_yaml_file(yaml_file)
    else:
        if comm is None:
            comm = _get_mpi_comm()
        rank = comm.rank
        if rank == 0:
            try:
                yaml_dict = read_yaml_file(yaml_file)
            except Exception as err:
                print("Error in read %s as yaml file: %s" % (yaml_file, err))
                comm.Abort()
        else:
            yaml_dict = None
        yaml_dict = comm.bcast(yaml_dict, root=0)
    return yaml_dict


def smart_check_path(path, mpi_mode=True, comm=None):
    if not mpi_mode:
        path_exists = os.path.exists(path)
    else:
        if comm is None:
            comm = _get_mpi_comm()
        rank = comm.rank
        if rank == 0:
            path_exists = os.path.exists(path)
        else:
            path_exists = None
        path_exists = comm.bcast(path_exists, root=0)
    return path_exists


def smart_remove_file(filename, mpi_mode=True, comm=None):
    if not smart_check_path(filename, mpi_mode=mpi_mode, comm=comm):
        return
    if mpi_mode:
        if comm is None:
            comm = _get_mpi_comm()
        rank = comm.rank
        comm.Barrier()
        if rank == 0:
            os.remove(filename)
        comm.Barrier()
    else:
        os.remove(filename)


def smart_mkdir(dirname, mpi_mode=True, comm=None):
    if os.path.exists(dirname):
        return
    if mpi_mode:
        if comm is None:
            comm = _get_mpi_comm()
        rank = comm.rank
        comm.Barrier()
        if rank == 0:
            os.makedirs(dirname)
        comm.Barrier()
    else:
        os.makedirs(dirname)


def drawProgressBar(percent, user_text="", barLen=20):
    """
    Draw status progress bars in terminal.
    Not recommendded used for job scripts(will create
    thousands of lines of output)
    """

    if user_text == "":
        user_text = "Status"

    sys.stdout.write("\r")
    progress = ""
    for i in range(barLen):
        if i < int(barLen * percent):
            progress += "="
        else:
            progress += " "
    sys.stdout.write(
        "%s: [ %s ] %.2f%%" % (user_text, progress, percent * 100))
    sys.stdout.flush()

    if percent >= 1.0:
        sys.stdout.write("\n")


def timing(f):
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()
        print '%s function took %0.3f s' % (f.func_name, (time2-time1))
        return ret
    return wrap


def isclose(a, b, rel_tol=1.0e-09, abs_tol=0.0):
    """
    Compare two numbers see if they are close to each other to a
    tolerance level
    """
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
