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
import json
import yaml
import matplotlib.pyplot as plt


def load_json(filename):
    with open(filename, 'r') as fh:
        return json.load(fh)


def dump_json(content, filename):
    with open(filename, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def load_yaml(filename):
    with open(filename, 'r') as fh:
        return yaml.load(fh)


def dump_yaml(content, filename):
    with open(filename, 'w') as fh:
        yaml.dump(content, fh, indent=2)


def reset_matplotlib():
    plt.switch_backend('agg')
