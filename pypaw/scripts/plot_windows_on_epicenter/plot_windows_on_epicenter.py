from __future__ import print_function, division

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from obspy.geodetics import locations2degrees
import pyasdf
from pypaw import extract_waveform_stations


def load_json(filename):
    with open(filename) as fh:
        return json.load(fh)


def extract_distance_info(asdffile, windows):
    stations = []
    for sta in windows:
        stations.append(sta)
    ds = pyasdf.ASDFDataSet(asdffile)
    sta_dict = extract_waveform_stations(ds, stations=stations)

    event = ds.events[0]
    origin = event.preferred_origin()
    event_lat = origin.latitude
    event_lon = origin.longitude

    dists = {}
    for sta_id, sta_loc in sta_dict.iteritems():
        dists[sta_id] = locations2degrees(event_lat, event_lon,
                                          sta_loc[0], sta_loc[1])
    return dists


def sort_windows(windows):
    windows_comp = {}
    """ sort windows based on components """
    for sta, sta_info in windows.iteritems():
        for chan, chan_info in sta_info.iteritems():
            comp = chan.split(".")[-1]
            if comp not in windows_comp:
                windows_comp[comp] = {}
            windows_comp[comp][sta] = \
                [[_win["relative_starttime"], _win["relative_endtime"]] for
                 _win in chan_info]
    return windows_comp


def plot_one_component(comp_info, dist_info, outputfn):
    plt.figure(figsize=(20, 20))
    for sta, win_time in comp_info.iteritems():
        dist = dist_info[sta]
        for _win in win_time:
            plt.plot([dist, dist], _win)

    plt.savefig(outputfn)


def calculate_traveltime():


def plot_windows_on_epicenter(path):

    path_info = load_json(path)
    winfile = path_info["window"]
    asdffile = path_info["asdf"]
    outputdir = path_info["outputdir"]

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    windows = load_json(winfile)
    dist_info = extract_distance_info(asdffile, windows)

    windows_comp = sort_windows(windows)

    for comp, comp_info in windows_comp.iteritems():
        outputfn = os.path.join(outputdir, "windows.%s.png" % comp)
        plot_one_component(comp_info, dist_info, outputfn)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path',
                        required=True)
    args = parser.parse_args()

    plot_windows_on_epicenter(args.path)

