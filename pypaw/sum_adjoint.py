#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that sums the several adjoint source files from different period
bands together based on certain weights provided by the user. So each
adjoint asdf file should has one weight files, with weightings for
each channel

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import
import os
from pprint import pprint
from copy import deepcopy
from pyasdf import ASDFDataSet
from pytomo3d.adjoint.sum_adjoint import load_to_adjsrc, dump_adjsrc, \
    check_events_consistent, \
    create_weighted_adj, sum_adj_to_base, check_station_consistent, \
    rotate_adjoint_sources
from .utils import read_json_file, dump_json, read_yaml_file, \
    smart_remove_file


def validate_path(path):
    print("="*20 + " Path information " + "="*20)
    pprint(path)

    err = 0
    keys = ["input_file", "output_file"]
    for _key in keys:
        if _key not in path:
            print("Missing key(%s) in path" % _key)
            err = 1

    if len(path["input_file"]) == 0:
        print("No input information provided in path")
    for finfo in path["input_file"].itervalues():
        asdf_file = finfo["asdf_file"]
        weight_file = finfo["weight_file"]
        if not os.path.exists(asdf_file):
            print("No asdf file: %s" % asdf_file)
            err = 1
        if not os.path.exists(weight_file):
            print("No weight file: %s" % weight_file)
            err = 1

    if err != 0:
        raise ValueError("Error in path file")


def validate_param(param):
    print("=" * 20 + " Param information " + "=" * 20)
    pprint(param)

    err = 0
    keys = ["rotate_flag"]
    for k in keys:
        if k not in param:
            print("Missing key(%s) in param" % k)
            err = 1

    if err:
        raise ValueError("Error in param file")


def save_adjoint_to_asdf(outputfile, events, adjoint_sources, stations):
    """
    Save events(obspy.Catalog) and adjoint sources, together with
    staiton information, to asdf file on disk.
    """
    print("="*15 + "\nWrite to file: %s" % outputfile)
    outputdir = os.path.dirname(outputfile)
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    if os.path.exists(outputfile):
        print("Output file exists and removed:%s" % outputfile)
        os.remove(outputfile)

    ds = ASDFDataSet(outputfile, mode='a', compression=None)
    ds.add_quakeml(events)
    for adj_id in sorted(adjoint_sources):
        adj = adjoint_sources[adj_id]
        sta_tag = "%s_%s" % (adj.network, adj.station)
        sta_info = stations[sta_tag]
        adj_array, adj_path, parameters = \
            dump_adjsrc(adj, sta_info)
        ds.add_auxiliary_data(adj_array, data_type="AdjointSources",
                              path=adj_path, parameters=parameters)


def check_event_information_in_asdf_files(asdf_files):
    if len(asdf_files) == 0:
        raise ValueError("Number of input asdf files is 0")

    asdf_events = {}
    # extract event information from asdf file
    for asdf_fn in asdf_files:
        ds = ASDFDataSet(asdf_fn, mode='r')
        asdf_events[asdf_fn] = ds.events

    check_events_consistent(asdf_events)

    event_base = asdf_events[asdf_events.keys()[0]]
    origin = event_base[0].preferred_origin()
    return event_base, origin


class PostAdjASDF(object):

    def __init__(self, path, param, verbose=False):
        self.path = path
        self.param = param
        self.verbose = verbose

        # event information
        self.events = None
        self.event_latitude = None
        self.event_longitude = None
        self.event_time = None

        # station information
        self.stations = {}

        # adjoint sources
        self.adjoint_sources = {}
        self.misfits = {}

    def attach_adj_to_db(self, channel_id, adj, weight):
        """
        Attach adj to self.adjoint_sources based on weight information
        """
        if channel_id not in self.adjoint_sources:
            self.adjoint_sources[channel_id] = \
                create_weighted_adj(adj, weight)
        else:
            adj_base = self.adjoint_sources[channel_id]
            sum_adj_to_base(adj_base, adj, weight)

    def attach_station_to_db(self, station_info):
        """
        Attach station information to self.stations
        """
        station_id = "%s_%s" % (station_info["network"],
                                station_info["station"])

        if station_id not in self.stations:
            self.stations[station_id] = deepcopy(station_info)
            self.stations["location"] = ""
        else:
            # check consistency
            sta_base = self.stations[station_id]
            if not check_station_consistent(sta_base, station_info):
                raise ValueError("Station(%s) location inconsitent: %s, %s"
                                 % (station_id, station_info, sta_base))

    def add_adjoint_dataset_on_channel_weight(self, ds, weights):
        """
        Add adjoint source based on channel window weight
        The adjoint source's channel should be renamed to "MX"
        """
        if len(weights) == 0:
            # if not weights, then just return. For some events,
            # we found that there might not be no windows selected
            # for one period, for example, 90_250 period bands.
            return {}

        misfits = {}
        adjsrc_group = ds.auxiliary_data.AdjointSources
        for channel in weights:
            _nw, _sta, _, _comp = channel.split(".")
            adj_id = "%s_%s_MX%s" % (_nw, _sta, _comp[-1])
            adj = adjsrc_group[adj_id]
            new_adj, station_info = load_to_adjsrc(adj)

            channel_weight = weights[channel]["weight"]
            # add station information
            try:
                self.attach_station_to_db(station_info)
            except Exception as err:
                print("Failed to add station information(%s) to db due to: %s"
                      % (channel, str(err)))
                continue
            # add adjoint source
            try:
                self.attach_adj_to_db(adj_id, new_adj, channel_weight)
            except Exception as err:
                print("Failed to add station adjsrc(%s) to db due to: %s"
                      % (channel, str(err)))
            # get the component misfit values
            if _comp not in misfits:
                misfits[_comp] = {"misfit": 0, "raw_misfit": 0}
            misfits[_comp]["misfit"] += channel_weight * new_adj.misfit
            misfits[_comp]["raw_misfit"] += new_adj.misfit

        print("Misfit:")
        pprint(misfits)
        return misfits

    def check_all_event_info(self):
        """
        Gather event information to make sure every asdf file
        has the same event information, then add operation
        is allowed
        """
        asdf_files = []
        for file_info in self.path["input_file"].itervalues():
            asdf_files.append(file_info["asdf_file"])

        self.events, self.origin = \
            check_event_information_in_asdf_files(asdf_files)
        # extract event information
        self.event_latitude, self.event_longitude, self.event_time = \
            self.origin.latitude, self.origin.longitude, self.origin.time

    def sum_asdf(self):
        """
        Sum different asdf files
        """
        print("="*30 + "\nSumming asdf files...")
        for period, _file_info in self.path["input_file"].iteritems():
            filename = _file_info["asdf_file"]
            ds = ASDFDataSet(filename, mode='r')
            weight_file = _file_info["weight_file"]
            weights = read_json_file(weight_file)
            print("-" * 20)
            print("Adding asdf file(%s) using assigned weight_file(%s)"
                  % (filename, weight_file))
            print("Number of channel weights(adjoint sources): %d"
                  % len(weights))

            _misfit = self.add_adjoint_dataset_on_channel_weight(
                ds, weights)
            self.misfits[period] = _misfit

    def rotate_asdf(self):
        """
        Rotate self.adjoint_sources
        """
        self.adjoint_sources = rotate_adjoint_sources(
            self.adjoint_sources, self.stations, self.event_latitude,
            self.event_longitude)

    def dump_to_asdf(self, outputfile):
        """
        Dump self.adjoin_sources into adjoint file
        """
        nadjsrc = len(self.adjoint_sources)
        print("Number of adjoint sources: %d" % nadjsrc)
        if nadjsrc == 0:
            print("Exit without generate adjoint asdf file since "
                  "number of adjoint source is 0")
            return
        save_adjoint_to_asdf(outputfile, self.events, self.adjoint_sources,
                             self.stations)

    def _parse_path(self):
        if isinstance(self.path, str):
            path = read_json_file(self.path)
        elif isinstance(self.path, dict):
            path = self.path
        else:
            raise TypeError("Not recognized path: %s" % path)
        return path

    def _parse_param(self):
        if isinstance(self.param, str):
            param = read_yaml_file(self.param)
        elif isinstance(self.param, dict):
            param = self.param
        else:
            raise TypeError("Not recognized param: %s" % param)
        return param

    def smart_run(self):

        self.path = self._parse_path()
        self.param = self._parse_param()

        validate_path(self.path)
        validate_param(self.param)

        self.check_all_event_info()

        # sum asdf files
        self.sum_asdf()

        # rotate if needed
        if self.param["rotate_flag"]:
            self.rotate_asdf()

        outputfile = self.path["output_file"]
        smart_remove_file(outputfile, mpi_mode=False)
        self.dump_to_asdf(outputfile)

        # write out the misfit summary
        misfit_file = outputfile.rstrip("h5") + "adjoint.misfit.json"
        smart_remove_file(misfit_file, mpi_mode=False)
        print("Misfit log file: %s" % misfit_file)
        dump_json(self.misfits, misfit_file)
