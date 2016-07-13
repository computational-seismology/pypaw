#!/usr/bin/env python
"""
Convert asdf files to sac
"""
import argparse

from pypaw import convert_adjsrcs_from_asdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest='outputdir', default='.',
                        help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose")
    args = parser.parse_args()

    convert_adjsrcs_from_asdf(
        args.filename, args.outputdir, _verbose=args.verbose)


if __name__ == '__main__':
    main()
