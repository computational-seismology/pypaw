#!/usr/bin/env python
import matplotlib as mpl
mpl.use('Agg')  # NOQA
import argparse
from pypaw import WindowASDF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='params_file',
                        required=True, help="parameter file")
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose")
    args = parser.parse_args()

    proc = WindowASDF(args.path_file, args.params_file,
                      verbose=args.verbose)
    proc.smart_run()


if __name__ == '__main__':
    main()
