#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class that sums the several adjoint source files together based
on certain weights provided by the user

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import print_function, division, absolute_import
import os
import numpy as np
import argparse
import copy
from pyasdf import ASDFDataSet
from pytomo3d.signal.rotate import rotate_one_station_stream
from pytomo3d.adjoint.process_adjsrc import convert_stream_to_adjs
from pytomo3d.adjoint.process_adjsrc import convert_adjs_to_stream
from pytomo3d.adjoint.process_adjsrc import add_missing_components
from pprint import pprint
from pyadjoint import AdjointSource
from utils import load_json, dump_json, check_adj_consistency


def _rotate_one_station(sta_adjs, slat, slon, elat, elon):
    adj_stream, meta_info = convert_adjs_to_stream(sta_adjs)
    add_missing_components(adj_stream)
    rotate_one_station_stream(adj_stream, elat, elon,
                              station_latitude=slat,
                              station_longitude=slon,
                              mode="RT->NE")
    new_adjs = convert_stream_to_adjs(adj_stream, meta_info)
    adj_dict = {}
    for _adj in new_adjs:
        adj_id = "%s_%s_%s" % (_adj.network, _adj.station, _adj.component)
        adj_dict[adj_id] = _adj
    return adj_dict


def print_info(content, title=""):
    print("="*20 + title + "="*20)
    if not isinstance(content, dict):
        raise TypeError("Type of content(%s) must by dict" % type(content))
    pprint(content)


def load_to_adjsrc(adj, event_time):
    """
    Load from asdf file adjoint source to pyadjoint.AdjointSources
    """
    starttime = event_time + adj.parameters["time_offset"]
    _id = adj.parameters["station_id"]
    nw, sta = _id.split(".")
    comp = adj.parameters["component"]
    loc = adj.parameters["location"]

    new_adj = AdjointSource(adj.parameters["adjoint_source_type"],
                            adj.parameters["misfit"],
                            adj.parameters["dt"],
                            adj.parameters["min_period"],
                            adj.parameters["max_period"],
                            comp,
                            adjoint_source=np.array(adj.data),
                            network=nw, station=sta,
                            location=loc,
                            starttime=starttime)

    station_info = {"latitude": adj.parameters["latitude"],
                    "longitude": adj.parameters["longitude"],
                    "elevation_in_m": adj.parameters["elevation_in_m"],
                    "depth_in_m": adj.parameters["depth_in_m"],
                    "station": sta, "network": nw,
                    "location": loc}
    return new_adj, station_info


def dump_adjsrc(adj, station_info, event_time):
    adj_array = np.asarray(adj.adjoint_source, dtype=np.float32)
    station_id = "%s.%s" % (adj.network, adj.station)

    time_offset = adj.starttime - event_time
    parameters = \
        {"dt": adj.dt, "time_offset": time_offset,
         "misfit": adj.misfit,
         "adjoint_source_type": adj.adj_src_type,
         "min_period": adj.min_period,
         "max_period": adj.max_period,
         "location": adj.location,
         "latitude": station_info["latitude"],
         "longitude": station_info["longitude"],
         "elevation_in_m": station_info["elevation_in_m"],
         "depth_in_m": station_info["depth_in_m"],
         "station_id": station_id, "component": adj.component,
         "units": "m"}

    adj_path = "%s_%s_%s" % (adj.network, adj.station, adj.component)

    return adj_array, adj_path, parameters


def _get_station_adjsrcs(adjsrcs, sta_tag):
    """
    Extract three components for a specific sta_tag
    """
    comp_list = ["MXZ", "MXR", "MXT"]
    adj_list = []
    for comp in comp_list:
        adj_name = "%s_%s" % (sta_tag, comp)
        if adj_name in adjsrcs:
            adj_list.append(adjsrcs[adj_name])
    return adj_list


def extract_event_info(event):
    origin = event.preferred_origin()
    return origin.latitude, origin.longitude, origin.time


class PostAdjASDF(object):

    def __init__(self, path, verbose=False):
        self.path = path
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

    def _attach_adj(self, station_id, adj, weight):
        """
        Attach adj to self.adjoint_sources based on weight information
        """
        if station_id not in self.adjoint_sources:
            adj_base = copy.deepcopy(adj)
            adj_base.adjoint_source *= weight
            adj_base.misfit *= weight
            adj_base.location = ""
            self.adjoint_sources[station_id] = adj_base
        else:
            adj_base = self.adjoint_sources[station_id]
            check_adj_consistency(adj_base, adj)
            adj_base.adjoint_source += weight * adj.adjoint_source
            adj_base.misfit += weight * adj.misfit
            adj_base.min_period = min(adj.min_period, adj_base.min_period)
            adj_base.max_period = max(adj.max_period, adj_base.max_period)

    def _attach_station(self, station_info):
        """
        Attach station information to self.stations
        """

        def __same_location(loc1, loc2):
            for key in loc1:
                if key not in loc2:
                    return False
                if isinstance(loc1[key], float):
                    if not np.isclose(loc1[key], loc2[key]):
                        return False
                else:
                    if loc1[key] != loc2[key]:
                        return False
            return True

        station_id = "%s_%s" % (station_info["network"],
                                station_info["station"])
        if station_id not in self.stations:
            self.stations[station_id] = station_info
        else:
            # check consistency
            loc_base = self.stations[station_id]
            if not __same_location(loc_base, station_info):
                raise ValueError("Station(%s) location inconsitent: %s, %s"
                                 % (station_id, station_info, loc_base))

    def add_adjoint_dataset_on_category_weight(self, ds, weight):
        """
        Add adjoint source based on category weight
        """
        misfits = {}
        adjsrc_group = ds.auxiliary_data.AdjointSources
        for adj in adjsrc_group:
            new_adj, station_info = load_to_adjsrc(adj, self.event_time)

            nw = new_adj.network
            sta = new_adj.station
            comp = new_adj.component
            comp_weight = weight["BH%s" % comp[-1]]

            chan_id = "%s_%s_%s" % (nw, sta, comp)
            self._attach_adj(chan_id, new_adj, comp_weight)

            self._attach_station(station_info)

            if comp not in misfits:
                misfits[comp] = {"misfit": 0, "raw_misfit": 0}
            misfits[comp]["misfit"] += comp_weight * new_adj.misfit
            misfits[comp]["raw_misfit"] += new_adj.misfit

        return misfits

    def add_adjoint_dataset_on_channel_weight(self, ds, weight_file):
        """
        Add adjoint source based on channel window weight
        """
        weights = load_json(weight_file)
        misfits = {}
        adjsrc_group = ds.auxiliary_data.AdjointSources
        for channel in weights:
            _nw, _sta, _, _comp = channel.split(".")
            adj_id = "%s_%s_MX%s" % (_nw, _sta, _comp[-1])
            adj = adjsrc_group[adj_id]
            new_adj, station_info = load_to_adjsrc(adj, self.event_time)

            channel_weight = weights[channel]["weight"]
            self._attach_adj(adj_id, new_adj, channel_weight)

            self._attach_station(station_info)

            if _comp not in misfits:
                misfits[_comp] = {"misfit": 0, "raw_misfit": 0}
            misfits[_comp]["misfit"] += channel_weight * new_adj.misfit
            misfits[_comp]["raw_misfit"] += new_adj.misfit

        return misfits

    def check_all_event_info(self):
        """
        Gather event information to make sure every asdf file
        has the same event information, then add operation
        is allowed
        """
        error_code = 0
        error_list = []
        for _file_info in self.path["input_file"].itervalues():
            asdf_fn = _file_info["asdf_file"]
            ds = ASDFDataSet(asdf_fn)
            if self.events is None:
                self.events = ds.events
            elif self.events != ds.events:
                error_list.append(asdf_fn)
                error_code = 1
            del ds
        if error_code == 1:
            raise ValueError("Event information in %s not the same as others"
                             % (error_list))

        # extract event information
        self.event_latitude, self.event_longitude, self.event_time = \
            extract_event_info(self.events[0])

    def sum_asdf(self):
        """
        Sum different asdf files
        """
        print("="*15 + "\nSumming asdf files...")
        for period, _file_info in self.path["input_file"].iteritems():
            filename = _file_info["asdf_file"]
            ds = ASDFDataSet(filename)

            if "weight" in _file_info:
                _weight = _file_info["weight"]
                misfits = self.add_adjoint_dataset_on_category_weight(
                    ds, _weight)
            elif "weight_file" in _file_info:
                _weight = _file_info["weight_file"]
                misfits = self.add_adjoint_dataset_on_channel_weight(
                    ds, _weight)
            else:
                raise NotImplementedError("Not implemented")

            print("Adding asdf file(%s) using assigned weight(%s)"
                  % (filename, _weight))

            self.misfits[period] = misfits

    def rotate_asdf(self):
        """
        Rotate self.adjoint_sources
        """
        print("="*15 + "\nRotate adjoint sources from RT to EN")
        done_sta_list = []
        old_adjs = self.adjoint_sources
        new_adjs = {}
        station_locations = {}

        for adj_id, adj in old_adjs.iteritems():
            network = adj.network
            station = adj.station
            sta_tag = "%s_%s" % (network, station)

            if sta_tag not in done_sta_list:
                slat = self.stations[sta_tag]["latitude"]
                slon = self.stations[sta_tag]["longitude"]

                sta_adjs = _get_station_adjsrcs(old_adjs, sta_tag)
                adj_dict = _rotate_one_station(sta_adjs, slat, slon,
                                               self.event_latitude,
                                               self.event_longitude)
                new_adjs.update(adj_dict)

        self.station_locations = station_locations
        self.adjoint_sources = new_adjs

    def dump_to_asdf(self, outputfile):
        """
        Dump self.adjoin_sources into adjoint file
        """
        print("="*15 + "\nWrite to file: %s" % outputfile)
        if os.path.exists(outputfile):
            print("Output file exists and removed:%s" % outputfile)
            os.remove(outputfile)

        ds = ASDFDataSet(outputfile, compression=None)
        ds.add_quakeml(self.events)
        event = self.events[0]
        origin = event.preferred_origin()
        event_time = origin.time

        for adj_id in sorted(self.adjoint_sources):
            adj = self.adjoint_sources[adj_id]
            sta_tag = "%s_%s" % (adj.network, adj.station)
            sta_info = self.stations[sta_tag]
            adj_array, adj_path, parameters = \
                dump_adjsrc(adj, sta_info, event_time)
            ds.add_auxiliary_data(adj_array, data_type="AdjointSources",
                                  path=adj_path, parameters=parameters)

    def smart_run(self):

        if isinstance(self.path, str):
            self.path = load_json(self.path)

        print_info(self.path, title="Input Parameter")

        self.check_all_event_info()

        # sum asdf files
        self.sum_asdf()

        if self.path["rotate_flag"]:
            self.rotate_asdf()

        outputfile = self.path["output_file"]
        self.dump_to_asdf(outputfile)

        # write out the misfit summary
        misfit_file = outputfile.rstrip("h5") + "misfit.json"
        dump_json(self.misfits, misfit_file)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    job = PostAdjASDF(args.path_file, args.verbose)
    job.smart_run()
