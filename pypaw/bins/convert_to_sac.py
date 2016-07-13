#!/usr/bin/env python
"""
Convert asdf files to sac
"""
import argparse

from pypaw import convert_from_asdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', action='store', dest='outputdir', default='.',
                        help="output directory")
    parser.add_argument('filename', help="Input ASDF filename")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose")
    parser.add_argument('-s', action='store_true', dest="stationxml",
                        help="Output StationXML files")
    parser.add_argument('-q', action='store_true', dest="quakeml",
                        help="Output Quakeml file")
    args = parser.parse_args()

    convert_from_asdf(
        args.filename, args.outputdir, filetype="sac",
        output_staxml=args.stationxml, output_quakeml=args.quakeml,
        _verbose=args.verbose)


if __name__ == '__main__':
    main()
