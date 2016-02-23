#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Methods that contains utils for adjoint sources

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (absolute_import, division, print_function)
import os
import glob
from .utils import JSONObject, smart_read_json, drawProgressBar, timing
from pyasdf import ASDFDataSet
import obspy


def create_simple_inventory(network, station, latitude=None, longitude=None,
                            elevation=None, depth=None, start_date=None,
                            end_date=None, location_code="S3"):
    """
    Create simple inventory for synthetic data
    """
    azi_dict = {"MXZ": 0.0,  "MXN": 0.0, "MXE": 90.0}
    dip_dict = {"MXZ": 90.0, "MXN": 0.0, "MXE": 0.0}
    channel_list = []

    if start_date is None:
        start_date = obspy.UTCDateTime(0)

    for _chan_code in ["MXZ", "MXE", "MXN"]:
        chan = obspy.Channel(_chan_code, location_code, latitude=latitude,
                             longitude=longitude, elevation=elevation,
                             depth=depth, azimuth=azi_dict[_chan_code],
                             dip=dip_dict[_chan_code], start_date=start_date,
                             end_date=end_date)
        channel_list.append(chan)

    site = obspy.Site("N/A")
    sta = obspy.Station(station, latitude=latitude, longitude=longitude,
                        elevation=elevation, channels=channel_list, site=site,
                        creation_date=start_date, total_number_of_channels=3,
                        selected_number_of_channels=3)

    nw = obspy.Network(network, stations=[sta, ], total_number_of_stations=1,
                       selected_number_of_stations=1)

    inv = obspy.Inventory([nw, ], source="SPECFEM3D_GLOBE", sender="Princeton",
                          created=start_date)

    return inv


@timing
def convert_to_asdf(asdf_fn, waveform_filelist, tag, quakemlfile,
                    staxml_filelist=None, verbose=False, status_bar=False,
                    create_simple_inv=False):
    """
    Convert files(sac or mseed) to asdf
    """

    if verbose:
        print("*"*10 + " ASDF Converter " + "*"*10)

    nwaveform = len(waveform_filelist)
    if nwaveform == 0:
        print("No file specified. Return...")
        return
    if os.path.exists(asdf_fn):
        raise Exception("File '%s' exists." % asdf_fn)

    ds = ASDFDataSet(asdf_fn)

    # Add event
    if quakemlfile is not None and os.path.exists(quakemlfile):
        ds.add_quakeml(quakemlfile)
        event = ds.events[0]
        if status_bar:
            drawProgressBar(1.0, "Adding Quakeml data")
    else:
        raise ValueError("No Event file")

    sta_dict = {}
    # Add waveforms.
    for _i, filename in enumerate(waveform_filelist):
        if not os.path.exists(filename):
            raise ValueError("File not exist %i of %i: %s"
                             % (_i, nwaveform, filename))

        st = obspy.read(filename)
        ds.add_waveforms(st, tag=tag, event_id=event)
        if create_simple_inv:
            for tr in st:
                sta_tag = "%s_%s" % (tr.stats.network, tr.stats.station)
                if sta_tag not in sta_dict.keys():
                    _sac = tr.stats.sac
                    sta_dict[sta_tag] = [tr.stats.network, tr.stats.station,
                                         _sac["stla"], _sac["stlo"],
                                         _sac["stel"], _sac["stdp"]]
        if status_bar:
            drawProgressBar((_i+1)/nwaveform, "Adding Waveform data")

    # Add StationXML files.
    if create_simple_inv:
        nstaxml = len(sta_dict)
        count = 0
        for tag, value in sta_dict.iteritems():
            count += 1
            origin = event.preferred_origin() or event.origins[0]
            event_time = origin.time
            start_date = event_time - 120.0
            inv = create_simple_inventory(
                    value[0], value[1], latitude=value[2], longitude=value[3],
                    elevation=value[4], depth=value[5], start_date=start_date)
            ds.add_stationxml(inv)
            if status_bar > 0:
                drawProgressBar((count)/nstaxml, "Adding StationXML data")
    else:
        nstaxml = len(staxml_filelist)
        if staxml_filelist is not None and nstaxml > 0:
            for _i, filename in enumerate(staxml_filelist):
                if not os.path.exists(filename):
                    raise ValueError("Staxml not exist %i of %i: %s"
                                     % (_i, nstaxml, filename))
                ds.add_stationxml(filename)
                if status_bar > 0:
                    drawProgressBar((_i+1)/nstaxml, "Adding StationXML data")
        else:
            print("No stationxml added")

    if verbose:
        print("ASDF filesize: %s" % ds.pretty_filesize)
    del ds


def write_stream_to_sac(stream, outputdir, tag=""):
    for tr in stream:
        if tag == "":
            filename = os.path.join(outputdir, "%s.sac" % tr.id)
        else:
            filename = os.path.join(outputdir, "%s.%s.sac" % (tr.id, tag))
        tr.write(filename, format="SAC")


def convert_asdf_to_other(asdf_fn, outputdir, tag=None, filetype="sac",
                          output_staxml=True, output_quakeml=True,
                          _verbose=True):
    """
    Convert asdf to different types of file
    """
    filetype = filetype.upper()
    if filetype not in ["SAC", "MSEED"]:
        raise ValueError("Supported filetype: 1) sac; 2) mseed")

    if not os.path.exists(asdf_fn):
        raise ValueError("No asdf file: %s" % asdf_fn)
    if not os.path.exists(outputdir):
        raise ValueError("No output dir: %s" % outputdir)

    if isinstance(tag, str):
        tag_list = [tag]

    ds = ASDFDataSet(asdf_fn)

    if output_quakeml:
        for event in ds.events:
            event_id = event.event_descriptions[0].text
            filename = os.path.join(outputdir, "CMT_%s.xml" % event_id)
            if _verbose:
                print("Quakeml file: %s" % filename)
            event.write(filename, format="QUAKEML")

    sta_list = ds.waveforms.list()

    for station_name in sta_list:
        if _verbose:
            print("Convert station: %s" % station_name)
        station_name2 = station_name.replace(".", "_")
        station = getattr(ds.waveforms, station_name2)
        if tag is None:
            tag_list = station.get_waveform_tags()
        for _tag in tag_list:
            stream, inv = ds.get_data_for_tag(station_name2, _tag)
            if filetype == "SAC":
                write_stream_to_sac(stream, outputdir, _tag)
            elif filetype == "MSEED":
                filename = os.path.join(outputdir, "%s.%s.mseed"
                                        % (station_name, _tag))
                stream.write(filename, format="MSEED")
            if output_staxml:
                filename = os.path.join(outputdir, "%s.%s.xml"
                                        % (station_name, _tag))
                inv.write(filename, format="STATIONXML")

    del ds


class ConvertASDF(object):

    def __init__(self, parfile, verbose, status_bar=False):
        self.parfile = parfile
        self._verbose = verbose
        self._status_bar = status_bar

    @staticmethod
    def print_info(waveform_files, tag, staxml_files, quakemlfile,
                   output_fn, create_simple_inv):
        waveform_dir = set([os.path.dirname(_i) for _i in waveform_files])
        print("-"*20)
        print("Quakeml files: ", quakemlfile)
        print("Waveform dirs:", waveform_dir)
        print("Number of waveform files:", len(waveform_files))
        if not create_simple_inv:
            staxml_dir = set([os.path.dirname(_i) for _i in staxml_files])
            print("Stationxml dirs:", staxml_dir)
            print("Number of Stationxml files:", len(staxml_files))
        else:
            print("Stationxml files: generated based on input waveform")
        print("Output filename:", output_fn)

    @staticmethod
    def clean_output_dir(output_fn):
        basepath = os.path.dirname(output_fn)
        if not os.path.exists(basepath):
            print("Output dir not exists so created: %s" % basepath)
            os.makedirs(basepath)
        if os.path.exists(output_fn):
            print("Outfile exist and being removed:", output_fn)
            os.remove(output_fn)

    @staticmethod
    def _parse_json(data):

        if "waveform_files" in dir(data):
            waveformfiles = data.waveform_files
        elif "waveform_dir" in dir(data):
            waveformdir = data.waveform_dir
            filetype = data.filetype
            waveform_pattern = os.path.join(waveformdir, "*"+filetype)
            waveformfiles = glob.glob(waveform_pattern)
        else:
            raise ValueError("missing keywords in json file, 'waveform_files'"
                             "or 'waveformdir'")

        if "staxml_files" in dir(data):
            staxmlfiles = data.staxml_files
            create_simple_inv = False
        elif "staxml_dir" in dir(data):
            staxmldir = data.staxml_dir
            staxml_pattern = os.path.join(staxmldir, '*.xml')
            staxmlfiles = glob.glob(staxml_pattern)
            create_simple_inv = False
        else:
            if "sac" not in data.filetype.lower():
                raise ValueError("create_simple_inv only support sac format")
            staxmlfiles = None
            create_simple_inv = True

        tag = data.tag
        quakemlfile = data.quakeml_file
        outputfile = data.output_file

        return waveformfiles, tag, staxmlfiles, quakemlfile, outputfile,\
            create_simple_inv

    def _run_subs(self, _json_par, _verbose, _status_bar):
        waveformfiles, tag, staxmlfiles, quakemlfile, outputfile, \
            create_simple_inv = self._parse_json(_json_par)

        self.print_info(waveformfiles, tag, staxmlfiles, quakemlfile,
                        outputfile, create_simple_inv)
        self.clean_output_dir(outputfile)

        convert_to_asdf(outputfile, waveformfiles, tag, quakemlfile,
                        staxml_filelist=staxmlfiles,
                        verbose=_verbose, status_bar=_status_bar,
                        create_simple_inv=create_simple_inv)

    def convert(self):
        json_data = smart_read_json(self.parfile, False)
        if isinstance(json_data, list):
            for _json in json_data:
                self._run_subs(_json, self._verbose, self._status_bar)
        elif isinstance(json_data, JSONObject):
            self._run_subs(json_data, self._verbose, self._status_bar)
