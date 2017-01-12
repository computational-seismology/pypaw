"""
This is script is used for stats the overall window counts on all window
files.

Suppose you have 1,000 events and 3 period bands, then the number of window
files will be about 3,000. Next, you want to know how many windows do
each category have and the number will then be used in the weighting
stage.
If "weight_output_file" is in the path file, then a default weight param
file will also be genrated. Be sure to modify some values and then it can
be used in the weighting stage.
"""
from __future__ import print_function, division, absolute_import
import numpy as np
import argparse
from pprint import pprint
from pytomo3d.window.utils import generate_log_content
from .utils import load_json, dump_json, dump_yaml


def stats_one_window_file(filename):
    """
    Given one window file, return the window counts for different
    component
    """
    windows = load_json(filename)
    log = generate_log_content(windows)
    results = {}
    for comp in log["component"]:
        results[comp] = log["component"][comp]["windows"]
    return results


def update_overall_wcounts(overall_wcounts, period, one_file_results):
    """
    Given the window counts from one file, update the overall
    window counts
    """
    if period not in overall_wcounts:
        overall_wcounts[period] = {}
    for comp in one_file_results:
        if comp == "total":
            # skip the total, which is not a component
            continue
        if comp not in overall_wcounts[period]:
            overall_wcounts[period][comp] = 0
        overall_wcounts[period][comp] += one_file_results[comp]


def _validate_ratio(overall_wcounts, ratio):
    prods = []
    for p, pinfo in overall_wcounts.iteritems():
        for c, cinfo in pinfo.iteritems():
            prods.append(cinfo * ratio[p][c])

    if not all([np.isclose(prods[0], _v) for _v in prods]):
        print("Failed wcounts and ratio validator!")


def ensemble_default_weight_param_file(overall_wcounts, outputfile):
    """
    Ensemble a default weight file based on overall window counts
    """
    maxv = 0
    # find max first
    for p, pinfo in overall_wcounts.iteritems():
        for c, cinfo in pinfo.iteritems():
            if cinfo > maxv:
                maxv = cinfo

    ratio = {}
    for p, pinfo in overall_wcounts.iteritems():
        ratio[str(p)] = {}
        for c, cinfo in pinfo.iteritems():
            ratio[str(p)][str(c)] = maxv / cinfo

    _validate_ratio(overall_wcounts, ratio)

    default_content = {
        "receiver_weighting": {
            "flag": True, "plot": False, "search_ratio": "TO BE FILLED"},
        "category_weighting": {
            "flag": True, "ratio": ratio}
    }
    dump_yaml(default_content, outputfile)


def stats_all_window_file(path, _verbose):
    detailed_event_windows = {}
    overall_wcounts = {}

    print("=" * 10 + " Start counting windows " + "=" * 10)
    eventlist = path["input"].keys()
    eventlist.sort()
    nevents = len(eventlist)
    for idxe, e in enumerate(eventlist):
        period_bands = path["input"][e].keys()
        period_bands.sort()
        print("-" * 8 + "[%d/%d]%s" % (idxe, nevents, e) +
              "-" * 8)
        detailed_event_windows[e] = {}
        event_total = 0
        for p in period_bands:
            one_file_results = stats_one_window_file(path["input"][e][p])
            print("period[%s]: %s" % (p, one_file_results))
            detailed_event_windows[e][p] = one_file_results
            period_total = 0
            for comp, comp_counts in one_file_results.iteritems():
                period_total += comp_counts
            detailed_event_windows[e][p]["total"] = period_total
            event_total += period_total
            # update for overall window counts
            update_overall_wcounts(overall_wcounts, p, one_file_results)
        detailed_event_windows[e]["total"] = event_total

    # dump results
    print("=" * 10 + " dump results " + "=" * 10)
    outputfile = path["output_file"]
    content = {"detailed_information": detailed_event_windows,
               "summary": overall_wcounts}
    print("outputfile: %s" % outputfile)
    dump_json(content, outputfile)

    if "weight_output_file" in path:
        print("weight default param file: %s" % path["weight_output_file"])
        ensemble_default_weight_param_file(
            overall_wcounts, path["weight_output_file"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file',
                        required=True, help='path file')
    parser.add_argument('-p', action='store', dest='param_file',
                        help='path file')
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help='verbose flag')
    args = parser.parse_args()

    path = load_json(args.path_file)
    print("=" * 10 + " Path information " + "=" * 10)
    pprint(path)

    stats_all_window_file(path, args.verbose)


if __name__ == "__main__":
    main()
