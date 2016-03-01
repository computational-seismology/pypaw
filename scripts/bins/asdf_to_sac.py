#!/usr/bin/env python

import argparse
from pypaw.convert import convert_from_asdf


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest="outputdir", default=".",
                        help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")
    parser.add_argument('-v', action='store_true', dest='verbose')

    args = parser.parse_args()
    convert_from_asdf(args.filename, args.outputdir, filetype="sac",
                      output_staxml=True, output_quakeml=True,
                      _verbose=args.verbose)
