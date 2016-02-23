#!/usr/bin/env python
import matplotlib as mpl
mpl.use('Agg')
import argparse
from pypaw.window import WindowASDF

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='params_file',
                        required=True)
    parser.add_argument('-f', action='store', dest='path_file', required=True)
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    proc = WindowASDF(args.path_file, args.params_file, verbose=args.verbose)
    proc.smart_run()
