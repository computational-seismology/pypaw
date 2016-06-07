#!/usr/bin/env python

import argparse

from pypaw import ProcASDF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='params_file',
                        required=True, help="parameter file")
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    proc = ProcASDF(args.path_file, args.params_file, args.verbose)
    proc.smart_run()


if __name__ == '__main__':
    main()
