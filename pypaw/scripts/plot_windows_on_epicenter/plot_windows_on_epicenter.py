#!/usr/bin/env python
# #####################################
# Scripts for plotting the windows on epicenter distance.
# #####################################
from __future__ import print_function, division

import argparse
import json
import os

import numpy as np
import warnings
import matplotlib as mpl
mpl.use("Agg")  # NOQA
import matplotlib.pyplot as plt
from matplotlib import cm

from obspy.geodetics import locations2degrees
from obspy.taup import TauPyModel
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
    event_depth = origin.depth / 1000.0

    dists = {}
    for sta_id, sta_loc in sta_dict.iteritems():
        dists[sta_id] = locations2degrees(event_lat, event_lon,
                                          sta_loc[0], sta_loc[1])
    return dists, event_depth


def sort_windows(windows):
    windows_comp = {}
    """ sort windows based on components """
    for sta, sta_info in windows.iteritems():
        for chan, chan_info in sta_info.iteritems():
            comp = chan.split(".")[-1]
            if comp not in windows_comp:
                windows_comp[comp] = {}
            windows_comp[comp][sta] = \
                [[_win["relative_starttime"], _win["relative_endtime"],
                  _win["cc_shift_in_seconds"], _win["dlnA"]] for
                 _win in chan_info]
    return windows_comp


def reformat_info(comp_info, dist_info):
    dist_array = []
    win_array = []
    cc_shifts = []
    dlnAs = []
    for sta, win_time in comp_info.iteritems():
        for _win in win_time:
            dist_array.append(dist_info[sta])
            win_array.append(_win[0:2])
            cc_shifts.append(_win[2])
            dlnAs.append(_win[3])
    return dist_array, win_array, cc_shifts, dlnAs


def plot_one_component_one_key(dist_array, win_array, colors, outputfn,
                               tag=None, unit=None, arrivals=None):
    colors = np.array(colors)
    _colors = np.array(colors)
    win_array = np.array(win_array)

    fig = plt.figure(figsize=(20, 28))

    norm_factor = np.max(np.abs(colors))
    colors = np.array(colors) / norm_factor * 0.5 + 0.5

    # plot windows
    plt.axes([0.05, 0.28, 0.90, 0.68])
    print("norm factor: %f" % norm_factor)
    for idx in range(len(dist_array)):
        plt.plot([dist_array[idx], dist_array[idx]],
                 win_array[idx], color=cm.jet(colors[idx]))

    # plot theoretical arrivals
    if arrivals is not None:
        # Plot and some formatting.
        for key, value in arrivals.items():
            plt.plot(value[0], value[1], '.', label=key)

    plt.grid()
    plt.xlabel('Distance (degrees)')
    plt.ylabel('Time (seconds)')
    plt.xlim(0, 180)
    plt.ylim(0, win_array.max() + 200.0)
    # plt.legend(numpoints=1)
    plt.legend(loc=2)

    # plot colorbar
    plt.axes([0.05, 0.05, 0.30, 0.01])
    ax1 = plt.gca()
    cmap = cm.jet
    norm = mpl.colors.Normalize(vmin=-norm_factor, vmax=norm_factor)
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm,
                                    orientation='horizontal')
    cb1.set_label(tag)

    # plot text
    plt.axes([0.05, 0.10, 0.40, 0.12])
    ax = plt.gca()
    plt.text(0.05, 1.0, "Total number of windows: %d" % len(dist_array),
             fontsize=20)
    plt.text(0.05, 0.9, "Measurements: %s" % tag,
             fontsize=20)
    plt.text(0.05, 0.8, "Mean: %f" % (np.mean(_colors)),
             fontsize=20)
    plt.text(0.05, 0.7, "Standard deviation: %f" % (np.std(_colors)),
             fontsize=20)
    plt.axis('off')

    # plot colorbar histogram
    plt.axes([0.45, 0.05, 0.2, 0.18])
    plt.hist(_colors)
    plt.xlabel(tag)
    plt.ylabel("count")

    # plot window time histogram
    plt.axes([0.75, 0.05, 0.2, 0.18])
    plt.hist(win_array[:, 1] - win_array[:, 0])
    plt.xlabel("window length(s)")
    plt.ylabel("count")

    plt.savefig(outputfn)


def plot_one_component(comp_info, dist_info, output_prefix, arrivals=None):

    dist_array, win_array, cc_shifts, dlnAs = \
        reformat_info(comp_info, dist_info)

    print("plot cc shifts")
    outputfn = "%s.cc_shifts.pdf" % output_prefix
    plot_one_component_one_key(dist_array, win_array, cc_shifts, outputfn,
                               tag="cc_shifts", unit="s", arrivals=arrivals)

    print("plot dlnA")
    outputfn = "%s.dlnA.png" % output_prefix
    plot_one_component_one_key(dist_array, win_array, dlnAs, outputfn,
                               tag="dlnA", unit="", arrivals=arrivals)


def calculate_traveltime(src_depth):
    print("Calculate theorecial travel time")
    model = TauPyModel(model="prem")
    phases = ['P', 'PP', 'PcP', 'Pdiff', 'PKP', 'PKKP',
              'S', 'SS', 'ScS', 'SSS', 'Sdiff', 'SKS', 'SKKS']
    data = {}

    degrees = np.linspace(0, 180, 200)
    # Loop over all degrees.
    for degree in degrees:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            tt = model.get_travel_times(source_depth_in_km=src_depth,
                                        distance_in_degree=degree,
                                        phase_list=phases)
        # Mirror if necessary.
        for item in tt:
            phase = item.name
            if phase not in data:
                data[phase] = [[], []]
            data[phase][1].append(item.time)
            data[phase][0].append(degree)

    return data


def plot_windows_on_epicenter(path):

    path_info = load_json(path)
    winfile = path_info["window"]
    asdffile = path_info["asdf"]
    outputdir = path_info["outputdir"]

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    windows = load_json(winfile)
    print("Extract event and stations location information")
    dist_info, event_depth = extract_distance_info(asdffile, windows)

    windows_comp = sort_windows(windows)

    arrivals = calculate_traveltime(event_depth)

    for comp, comp_info in windows_comp.iteritems():
        print("Plot component: %s" % comp)
        output_prefix = os.path.join(outputdir, "windows.%s" % comp)
        plot_one_component(comp_info, dist_info, output_prefix, arrivals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path',
                        required=True)
    args = parser.parse_args()

    plot_windows_on_epicenter(args.path)

