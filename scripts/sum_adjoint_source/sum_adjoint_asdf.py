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
from __future__ import print_function, division
import os
import numpy as np
import json
import argparse
from pyasdf import ASDFDataSet
from pytomo3d.signal.rotate import rotate_one_station_stream
from pytomo3d.adjoint.process_adjsrc import convert_stream_to_adjs
from pytomo3d.adjoint.process_adjsrc import convert_adjs_to_stream
from pytomo3d.adjoint.process_adjsrc import add_missing_components
from pprint import pprint
from pyadjoint import AdjointSource


def _load_to_adjsrc(adj, event_time):
    """
    Load from asdf file adjoint source to pyadjoint.AdjointSources
    """
    starttime = event_time + adj.parameters["time_offset"]
    _id = adj.parameters["station_id"]
    nw, sta = _id.split(".")
    new_adj = AdjointSource(adj.parameters["adjoint_source_type"],
                            adj.parameters["misfit"],
                            adj.parameters["dt"],
                            adj.parameters["min_period"],
                            adj.parameters["max_period"],
                            adj.parameters["component"],
                            adjoint_source=np.array(adj.data),
                            network=nw, station=sta,
                            location=adj.parameters["location"],
                            starttime=starttime)
    station_info = {"latitude": adj.parameters["latitude"],
                    "longitude": adj.parameters["longitude"],
                    "elevation_in_m": adj.parameters["elevation_in_m"],
                    "depth_in_m": adj.parameters["depth_in_m"]}
    return new_adj, station_info


def _check_adj_consistency(adj_base, adj):
    """
    Check the consistency of adj_base and adj
    If passed, return, then adj could be added into adj_base
    If not, raise ValueError
    """
    if len(adj_base.adjoint_source) != len(adj.adjoint_source):
        raise ValueError("Dimension of current adjoint_source(%d)"
                         "and new added adj(%d) not the same" %
                         (len(adj_base.adjoint_source),
                          len(adj.adjoint_source)))
    if not np.isclose(adj_base.dt, adj.dt):
        raise ValueError("DeltaT of current adjoint source(%f)"
                         "and new added adj(%f) not the same"
                         % (adj_base.dt, adj.dt))

    if np.abs(adj_base.starttime - adj.starttime) > 0.5 * adj.dt:
        raise ValueError("Start time of current adjoint source(%s)"
                         "and new added adj(%s) not the same"
                         % (adj_base.dt, adj.dt))


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

    def _attach_adj(self, station_id, adj, weight):
        """
        Attach adj to self.adjoint_sources
        """
        if station_id not in self.adjoint_sources:
            adj.adjoint_source *= weight
            adj.misfit *= weight
            adj.location = ""
            self.adjoint_sources[station_id] = adj
        else:
            adj_base = self.adjoint_sources[station_id]

            _check_adj_consistency(adj_base, adj)

            adj_base.adjoint_source += weight * adj.adjoint_source
            adj_base.misfit += weight * adj.misfit
            adj_base.min_period = min(adj.min_period, adj_base.min_period)
            adj_base.max_period = max(adj.max_period, adj_base.max_period)

    def _attach_station(self, station_id, station_info):

        def __same_location(loc1, loc2):
            for key in loc1:
                if key not in loc2:
                    return False
                if not np.isclose(loc1[key], loc2[key]):
                    return False
            return True

        if station_id not in self.stations:
            self.stations[station_id] = station_info
        else:
            # check consistency
            loc_base = self.stations[station_id]
            if not __same_location(loc_base, station_info):
                raise ValueError("Station(%s) location inconsitent: %s, %s"
                                 % (station_id, station_info, loc_base))

    def add_adjoint_dataset(self, ds, weight):
        adjsrc_group = ds.auxiliary_data.AdjointSources
        for adj in adjsrc_group:
            new_adj, station_info = _load_to_adjsrc(adj, self.event_time)
            nw = new_adj.network
            sta = new_adj.station
            comp = new_adj.component
            # if len(weight.keys()[0]) == 1:
            #    comp_weight = weight[comp[-1]]
            # elif len(weight.keys()[0]) == 3:
            #    comp_weight = weight[comp]
            # else:
            #    raise ValueError("Incorrect length of weight.keys(%s)"
            #                     % weight.keys())
            comp_weight = weight["BH%s" % comp[-1]]

            chan_id = "%s_%s_%s" % (nw, sta, comp)
            self._attach_adj(chan_id, new_adj, comp_weight)

            station_id = "%s_%s" % (nw, sta)
            self._attach_station(station_id, station_info)

    def _extract_event_info(self):
        event = self.events[0]
        origin = event.preferred_origin()
        self.event_latitude = origin.latitude
        self.event_longitude = origin.longitude
        self.event_time = origin.time

    def check_all_event_info(self):
        """
        Gather event information to make sure every asdf file
        has the same event information, then add operation
        is allowed
        """
        error_code = 0
        error_list = []
        for _file_info in self.path["input_file"]:
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
        self._extract_event_info()

    def sum_asdf(self):
        """
        Sum different asdf files
        """
        print("="*15 + "\nSumming asdf files...")
        for _file_info in self.path["input_file"]:
            filename = _file_info["asdf_file"]
            ds = ASDFDataSet(filename)
            if "AdjointSources" not in ds.auxiliary_data.list():
                raise ValueError("AdjointSources not exists in the file: %s"
                                 % filename)
            _weight = _file_info["weight"]
            if self.verbose:
                print("Adding asdf file(%s) using assigned weight(%s)"
                      % (filename, _weight))
            self.add_adjoint_dataset(ds, _weight)

    @staticmethod
    def print_info(content, extra_info=""):
        print("="*20 + extra_info + "="*20)
        if not isinstance(content, dict):
            raise TypeError("Type of content(%s) must by dict" % type(content))
        pprint(content)

    def _rotate_one_station(self, sta_adjs, slat, slon):
        adj_stream, meta_info = convert_adjs_to_stream(sta_adjs)
        add_missing_components(adj_stream)
        elat = self.event_latitude
        elon = self.event_longitude
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

    @staticmethod
    def _get_station_adjsrcs(adjsrcs, sta_tag):
        comp_list = ["MXZ", "MXR", "MXT"]
        adj_list = []
        for comp in comp_list:
            adj_name = "%s_%s" % (sta_tag, comp)
            if adj_name in adjsrcs:
                adj_list.append(adjsrcs[adj_name])
        return adj_list

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

                sta_adjs = self._get_station_adjsrcs(old_adjs, sta_tag)
                adj_dict = self._rotate_one_station(sta_adjs, slat, slon)
                new_adjs.update(adj_dict)

        self.station_locations = station_locations
        self.adjoint_sources = new_adjs

    def dump_to_asdf(self, outputfile, dtype=np.float32):
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
            adj_array = np.asarray(adj.adjoint_source, dtype=dtype)
            station_id = "%s.%s" % (adj.network, adj.station)

            time_offset = adj.starttime - event_time
            sta_tag = "%s_%s" % (adj.network, adj.station)
            sta_info = self.stations[sta_tag]
            parameters = \
                {"dt": adj.dt, "time_offset": time_offset,
                 "misfit": adj.misfit,
                 "adjoint_source_type": adj.adj_src_type,
                 "min_period": adj.min_period,
                 "max_period": adj.max_period,
                 "location": adj.location,
                 "latitude": sta_info["latitude"],
                 "longitude": sta_info["longitude"],
                 "elevation_in_m": sta_info["elevation_in_m"],
                 "depth_in_m": sta_info["depth_in_m"],
                 "station_id": station_id, "component": adj.component,
                 "units": "m"}
            adj_path = "%s" % adj_id

            ds.add_auxiliary_data(adj_array, data_type="AdjointSources",
                                  path=adj_path, parameters=parameters)

    def smart_run(self):

        if isinstance(self.path, str):
            with open(self.path) as fh:
                self.path = json.load(fh)
        self.print_info(self.path, extra_info="Input Parameter")

        # check event information for all files
        self.check_all_event_info()
        # sum asdf files
        self.sum_asdf()

        # rotate components from RT to EN
        if self.path["rotate_flag"]:
            self.rotate_asdf()

        outputfile = self.path["output_file"]
        # write out adjoint asdf file
        self.dump_to_asdf(outputfile)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', action='store', dest='path_file', required=True,
                        help="path file")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help="verbose flag")
    args = parser.parse_args()

    job = PostAdjASDF(args.path_file, args.verbose)
    job.smart_run()
