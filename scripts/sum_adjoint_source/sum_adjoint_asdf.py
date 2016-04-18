#!/usr/bin/env python
"""
Class that sums the several adjoint source files together based
on certain weights provided by the user

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (print_function, division)
import os
import numpy as np
import json
import argparse
from obspy import Stream, Trace
from pyasdf import ASDFDataSet
from pytomo3d.signal.rotate import rotate_one_station_stream
from pytomo3d.adjoint.process_adjsrc import convert_stream_to_adjs
from pytomo3d.adjoint.process_adjsrc import add_missing_components
from pprint import pprint


class PostAdjASDF(object):

    def __init__(self, path, verbose=False):
        self.path = path
        self.verbose = verbose

        self.events = None
        self.adjoint_sources = {}

    def add_adjoint_dataset(self, ds, weight):
        # loop all input files
        adjsrc_group = ds.auxiliary_data.AdjointSources
        for adj in adjsrc_group:
            nw = adj.parameters["station_id"].split(".")[0]
            sta = adj.parameters["station_id"].split(".")[1]

            comp = adj.parameters["component"]
            # if len(weight.keys()[0]) == 1:
            #    comp_weight = weight[comp[-1]]
            # elif len(weight.keys()[0]) == 3:
            #    comp_weight = weight[comp]
            # else:
            #    raise ValueError("Incorrect length of weight.keys(%s)"
            #                     % weight.keys())
            comp_weight = weight["BH%s" % comp[-1]]

            station_id = "%s_%s_%s" % (nw, sta, comp)
            if station_id not in self.adjoint_sources:
                self.adjoint_sources[station_id] = adj
                _array = np.array(self.adjoint_sources[station_id].data)
                self.adjoint_sources[station_id].data = comp_weight * _array
            else:
                adj_base = self.adjoint_sources[station_id]
                if len(adj_base.data) != len(adj.data):
                    raise ValueError("Dimension of current adjoint_source(%d)"
                                     "and new adj(%d) not the same" %
                                     (len(adj_base.data), len(adj.data)))
                adj_base.data += comp_weight * np.array(adj.data)

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

    def sum_asdf(self):
        """
        Sum different asdf files
        """
        print("="*15 + "\nSumming asdf files...")
        self.check_all_event_info()
        # then sum
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

    def _convert_adjs_to_stream(self, sta_adjs):
        """
        Convert adjoint source from hdf5 file into stream object.
        Attention: this adjoint source is different from the AdjointSource
            defined in pyadjoint
        """
        meta_info = {}
        stream = Stream()
        for adj in sta_adjs:
            tr = Trace()
            tr.data = adj.data
            tr.starttime = self.event_time + adj.parameters["time_offset"]
            tr.stats.delta = adj.parameters["dt"]
            tr.stats.channel = adj.parameters["component"]
            tr.stats.station = adj.parameters["station_id"].split(".")[1]
            tr.stats.network = adj.parameters["station_id"].split(".")[0]

            stream.append(tr)
            meta_info[tr.id] = \
                {"adj_src_type": adj.parameters["adjoint_source_type"],
                 "misfit": adj.parameters["misfit"],
                 "min_period": adj.parameters["min_period"],
                 "max_period": adj.parameters["max_period"]}
        return stream, meta_info

    def _rotate_one_station(self, sta_adjs, slat, slon):
        adj_stream, meta_info = self._convert_adjs_to_stream(sta_adjs)
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

    def _extract_event_info(self):
        event = self.events[0]
        origin = event.preferred_origin()
        self.event_latitude = origin.latitude
        self.event_longitude = origin.longitude
        self.event_time = origin.time

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
            network, station = adj.parameters["station_id"].split(".")
            sta_tag = "%s_%s" % (network, station)

            if sta_tag not in done_sta_list:
                slat = adj.parameters["latitude"]
                slon = adj.parameters["longitude"]
                station_locations[sta_tag] = \
                    {"latitude": slat, "longitude": slon,
                     "depth_in_m": adj.parameters["depth_in_m"],
                     "elevation_in_m": adj.parameters["elevation_in_m"]}

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

        ds = ASDFDataSet(outputfile)
        event = self.events[0]
        origin = event.preferred_origin()
        event_time = origin.time

        for adj_id in sorted(self.adjoint_sources):
            adj = self.adjoint_sources[adj_id]
            adj_array = np.asarray(adj.adjoint_source, dtype=dtype)

            time_offset = adj.starttime - event_time
            sta_tag = "%s_%s" % (adj.network, adj.station)
            sta_info = self.station_locations[sta_tag]
            parameters = \
                {"dt": adj.dt, "time_offset": time_offset,
                 "misfit": adj.misfit,
                 "adjoint_source_type": adj.adj_src_type,
                 "min_period": adj.min_period,
                 "max_period": adj.max_period,
                 "latitude": sta_info["latitude"],
                 "longitude": sta_info["longitude"],
                 "elevation_in_m": sta_info["elevation_in_m"],
                 "depth_in_m": sta_info["depth_in_m"],
                 "station_id": adj_id, "component": adj.component,
                 "units": "m"}
            adj_path = "AdjointSources/%s" % adj_id

            ds.add_auxiliary_data(adj_array, data_type="AuxiliaryData",
                                  path=adj_path, parameters=parameters)

    def smart_run(self):

        if isinstance(self.path, str):
            with open(self.path) as fh:
                self.path = json.load(fh)
        self.print_info(self.path, extra_info="Input Parameter")

        # sum asdf files
        self.sum_asdf()

        # rotate components from RT to EN
        if self.path["rotate_flag"]:
            self._extract_event_info()
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
