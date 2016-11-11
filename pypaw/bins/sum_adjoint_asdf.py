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
from __future__ import print_function, division, absolute_import
import argparse
from pypaw.sum_adjoint import PostAdjASDF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-p', action='store', dest='param_file', required=True,
                        help="param file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    job = PostAdjASDF(args.path_file, args.param_file, args.verbose)
    job.smart_run()


if __name__ == '__main__':
    main()
