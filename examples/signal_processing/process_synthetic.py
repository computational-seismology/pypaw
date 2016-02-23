#!/usr/bin/env python

import argparse
from pypaw.process import ProcASDF

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', action='store', dest='params_file',
                        required=True)
    parser.add_argument('-f', action='store', dest='path_file', required=True)
    parser.add_argument('-v', action='store_true', dest='verbose')
    args = parser.parse_args()

    proc = ProcASDF(args.path_file, args.params_file, args.verbose)
    proc.smart_run()
