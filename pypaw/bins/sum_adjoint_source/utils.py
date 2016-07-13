#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that sums the several adjoint source files together based
on certain weights provided by the user

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division
import numpy as np
import json


def read_txt_into_list(filename):
    with open(filename) as fh:
        return [line.rstrip() for line in fh]


def dump_json(content, filename):
    with open(filename, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def check_adj_consistency(adj_base, adj):
    """
    Check the consistency of adj_base and adj
    If passed, return, then adj could be added into adj_base
    If not, raise ValueError
    """
    if len(adj_base.adjoint_source) != len(adj.adjoint_source):
        raise ValueError("Dimension of current adjoint_source(%d)"
                         "and new added adj(%d) not the same" %
                         (len(adj_base.adjoint_source),
                          len(adj.adjoint_source)))
    if not np.isclose(adj_base.dt, adj.dt):
        raise ValueError("DeltaT of current adjoint source(%f)"
                         "and new added adj(%f) not the same"
                         % (adj_base.dt, adj.dt))

    if np.abs(adj_base.starttime - adj.starttime) > 0.5 * adj.dt:
        raise ValueError("Start time of current adjoint source(%s)"
                         "and new added adj(%s) not the same"
                         % (adj_base.dt, adj.dt))
