#!/usr/bin/env python

import argparse

from pypaw import ConvertASDF


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    parser.add_argument('-s', action='store_true', dest='status_bar',
                        help="status bar flag")
    args = parser.parse_args()

    converter = ConvertASDF(args.path_file, args.verbose, args.status_bar)
    converter.run()


if __name__ == '__main__':
    main()
