from __future__ import print_function, division
import json
import numpy as np
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def read_txt_into_list(txtfile):
    with open(txtfile, 'r') as f:
        content = f.readlines()
        eventlist = [line.rstrip() for line in content]
    return eventlist


def extract_window_info(window_file):
    event_info = {}

    with open(window_file) as fh:
        windows = json.load(fh)

    for sta, sta_info in windows.iteritems():
        for chan, chan_info in sta_info.iteritems():
            comp = chan.split(".")[-1]
            if comp not in event_info:
                event_info[comp] = {"cc_shift": [], "dlnA": []}
            event_info[comp]["cc_shift"].extend(
                [_win["cc_shift_in_seconds"] for _win in chan_info])
            event_info[comp]["dlnA"].extend(
                [_win["dlnA"] for _win in chan_info])
    return event_info


def add_event_to_period(event_wininfo, period_wininfo):
    for comp, comp_info in event_wininfo.iteritems():
        if comp not in period_wininfo:
            period_wininfo[comp] = {"cc_shift": [], "dlnA": []}
        period_wininfo[comp]["cc_shift"] += comp_info["cc_shift"]
        period_wininfo[comp]["dlnA"] += comp_info["dlnA"]


def gather_windows(path):
    results = {}
    with open(path) as fh:
        content = json.load(fh)

    results = {}
    for period, period_info in content.iteritems():
        print("Gather on period: %s" % period)
        period_wininfo = {}
        for event, event_info in period_info.iteritems():
            event_wininfo = extract_window_info(event_info)
            print("event wininfo:", event_wininfo.keys())
            add_event_to_period(event_wininfo, period_wininfo)
        results[period] = period_wininfo
    return results


def _stats_(windows, outputfn):

    stats_var = {}
    keys = ["cc_shift", "dlnA"]
    for period, period_info in results.iteritems():
        stats_var[period] = {}
        for comp, comp_info in period_info.iteritems():
            stats_var[period][comp] = {}
            for key in keys:
                array = np.array(comp_info[key])
                stats_var[period][comp][key] = \
                    {"mean": np.mean(array), "counts": len(array)}
    print("output file: %s" % outputfn)
    with open(outputfn, 'w') as fh:
        json.dump(stats_var, fh, indent=2, sort_keys=True)


def plot_results(windows):
    keys = ["cc_shift", "dlnA"]
    #ps = ["17_40", "40_100", "90_250"]
    ps = ["17_40", "40_100", "90_150", "90_250"]
    #ps = ["90_250", ]
    cs = ["BHZ", "BHR", "BHT"]
    figsize = (8*len(cs), 8*len(ps))

    for key in keys:
        plt.figure(figsize=figsize, facecolor="w", edgecolor="k")
        g = gridspec.GridSpec(len(ps), len(cs))
        for ip, p in enumerate(ps):
            for ic, c in enumerate(cs):
                array = np.array(windows[p][c][key])
                plt.subplot(g[ip, ic])
                plt.hist(array, 20, alpha=0.75)
        plt.savefig("%s.stats.png" % key)
        plt.tight_layout()
        plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path',
                        required=True)
    args = parser.parse_args()

    results = gather_windows(args.path)

    _stats_(results, outputfn="windows.stats_val.json")
    plot_results(results)
