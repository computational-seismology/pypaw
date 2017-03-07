#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Methods that contains utils for adjoint sources

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU Lesser General Public License, version 3 (LGPLv3)
    (http://www.gnu.org/licenses/lgpl-3.0.en.html)
"""
from __future__ import (absolute_import, division, print_function)
import os
import glob
import numpy as np
from obspy import UTCDateTime, read
from pytomo3d.station.utils import create_simple_inventory
from pyasdf import ASDFDataSet
from .utils import smart_read_json, drawProgressBar, timing


def add_waveform_to_asdf(ds, waveform_filelist, tag, event=None,
                         create_simple_inv=False, status_bar=False):

    nwaveform = len(waveform_filelist)
    sta_dict = {}
    # Add waveforms.
    for _i, filename in enumerate(waveform_filelist):
        if not os.path.exists(filename):
            raise ValueError("File not exist %i of %i: %s"
                             % (_i, nwaveform, filename))

        try:
            st = read(filename)
            ds.add_waveforms(st, tag=tag, event_id=event)
        except Exception as err:
            print("Error converting(%s) due to: %s" % (filename, err))
            continue
        if create_simple_inv:
            for tr in st:
                sta_tag = "%s_%s" % (tr.stats.network, tr.stats.station)
                if sta_tag not in sta_dict.keys():
                    try:
                        _sac = tr.stats.sac
                    except:
                        raise ValueError("The original data format should be"
                                         "sac format to extract station"
                                         "information")
                    sta_dict[sta_tag] = [tr.stats.network, tr.stats.station,
                                         _sac["stla"], _sac["stlo"],
                                         _sac["stel"], _sac["stdp"]]
                else:
                    continue

        if status_bar:
            drawProgressBar((_i+1)/nwaveform, "Adding Waveform data")
    return sta_dict


def add_stationxml_to_asdf(ds, staxml_filelist, event=None,
                           create_simple_inv=False, sta_dict=None,
                           status_bar=False):
    # Add StationXML files.
    if create_simple_inv:
        if event is None:
            start_date = UTCDateTime.now()
        else:
            origin = event.preferred_origin() or event.origins[0]
            event_time = origin.time
            start_date = event_time - 300.0
        nstaxml = len(sta_dict)
        count = 0
        for tag, value in sta_dict.iteritems():
            count += 1
            inv = create_simple_inventory(
                value[0], value[1], latitude=value[2], longitude=value[3],
                elevation=value[4], depth=value[5], start_date=start_date)
            ds.add_stationxml(inv)
            if status_bar > 0:
                drawProgressBar((count)/nstaxml,
                                "Adding StationXML(created) data")
    else:
        nstaxml = len(staxml_filelist)
        if staxml_filelist is not None and nstaxml > 0:
            for _i, filename in enumerate(staxml_filelist):
                if not os.path.exists(filename):
                    raise ValueError("Staxml not exist %i of %i: %s"
                                     % (_i, nstaxml, filename))
                try:
                    ds.add_stationxml(filename)
                except Exception as err:
                    print("Error convert(%s) due to:%s" % (filename, err))
                if status_bar > 0:
                    drawProgressBar((_i+1)/nstaxml, "Adding StationXML data")
        else:
            print("No stationxml added")


@timing
def convert_to_asdf(asdf_fn, waveform_filelist, tag, quakemlfile=None,
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

    ds = ASDFDataSet(asdf_fn, mode='a')

    # Add event
    if quakemlfile:
        if not os.path.exists(quakemlfile):
            raise ValueError("Quakeml file not exists:%s" % quakemlfile)
        ds.add_quakeml(quakemlfile)
        event = ds.events[0]
        if status_bar:
            drawProgressBar(1.0, "Adding Quakeml data")
    else:
        raise ValueError("No Event file")

    sta_dict = add_waveform_to_asdf(ds, waveform_filelist, tag, event=event,
                                    create_simple_inv=create_simple_inv,
                                    status_bar=status_bar)

    add_stationxml_to_asdf(ds, staxml_filelist, event=event,
                           create_simple_inv=create_simple_inv,
                           sta_dict=sta_dict,
                           status_bar=status_bar)

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


@timing
def convert_from_asdf(asdf_fn, outputdir, tag=None, filetype="sac",
                      output_staxml=True, output_quakeml=True,
                      _verbose=True):
    """
    Convert the waveform in asdf to different types of file
    """
    filetype = filetype.upper()
    if filetype not in ["SAC", "MSEED"]:
        raise ValueError("Supported filetype: 1) sac; 2) mseed")

    if not os.path.exists(asdf_fn):
        raise ValueError("No asdf file: %s" % asdf_fn)
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    if isinstance(tag, str):
        tag_list = [tag]

    print("Input ASDF: %s" % asdf_fn)
    print("Output dir: %s" % outputdir)
    print("Output StationXML and Quakeml: [%s, %s]" % (output_staxml,
                                                       output_quakeml))

    ds = ASDFDataSet(asdf_fn, mode='r')

    if output_quakeml:
        if len(ds.events) >= 1:
            filename = os.path.join(outputdir, "Quakeml.xml")
            if _verbose:
                print("Quakeml file: %s" % filename)
            ds.events.write(filename, format="QUAKEML")

    sta_list = ds.waveforms.list()

    for station_name in sta_list:
        if _verbose:
            print("Convert station: %s" % station_name)
        station_name2 = station_name.replace(".", "_")
        station = getattr(ds.waveforms, station_name2)
        default_tag_list = station.get_waveform_tags()
        if tag is None:
            tag_list = default_tag_list
        for _tag in tag_list:
            if _tag not in default_tag_list:
                print("Tag(%s) not in Station(%s) taglist(%s)" %
                      (_tag, station_name2, default_tag_list))
                continue
            try:
                stream, inv = ds.get_data_for_tag(station_name2, _tag)
            except:
                print("Error for station:", station_name2)
            if filetype == "SAC":
                write_stream_to_sac(stream, outputdir, _tag)
            elif filetype == "MSEED":
                filename = os.path.join(outputdir, "%s.%s.mseed"
                                        % (station_name, _tag))
                stream.write(filename, format="MSEED")
            if output_staxml:
                filename = os.path.join(outputdir, "%s.%s.xml"
                                        % (station_name, _tag))
                try:
                    inv.write(filename, format="STATIONXML")
                except:
                    print("Error creating STATIONXML: %f" % filename)

    del ds


@timing
def convert_adjsrcs_from_asdf(asdf_fn, outputdir, _verbose=True):
    """
    Convert adjoint sources from asdf to ASCII file(for specfem3d_globe use)
    """
    if not os.path.exists(asdf_fn):
        raise ValueError("No asdf file: %s" % asdf_fn)
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    print("Input ASDF: %s" % asdf_fn)
    print("Output dir: %s" % outputdir)

    ds = ASDFDataSet(asdf_fn, mode='r')
    if "AdjointSources" not in ds.auxiliary_data:
        print("No adjoint source exists in asdf file: %s" % asdf_fn)
        return
    adjsrcs = ds.auxiliary_data.AdjointSources
    nadj = len(adjsrcs)
    print("Number of adjoint sources: %d" % nadj)

    # get event time
    origin = ds.events[0].preferred_origin()
    eventtime = origin.time

    for idx, adj in enumerate(adjsrcs):
        if _verbose:
            print("Adjoint sources(%d/%d) from: %s" % (idx, nadj, adj.path))
        trace_starttime = UTCDateTime(adj.parameters["starttime"])
        time_offset = trace_starttime - eventtime

        dt = adj.parameters['dt']
        npts = len(adj.data)
        times = np.array([time_offset + i * dt for i in range(npts)])
        _data = np.zeros([npts, 2])
        _data[:, 0] = times[:]
        _data[:, 1] = adj.data[:]
        adj_path = adj.path.replace("_", ".")
        filename = os.path.join(outputdir, "%s.adj" % adj_path)
        np.savetxt(filename, _data)


class ConvertASDF(object):

    def __init__(self, path, verbose=False, status_bar=False):
        self.path = path
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
    def clean_output(output_fn):
        basepath = os.path.dirname(output_fn)
        if not os.path.exists(basepath):
            print("Output dir not exists so created: %s" % basepath)
            os.makedirs(basepath)
        if os.path.exists(output_fn):
            print("Outfile exist and being removed:", output_fn)
            os.remove(output_fn)

    @staticmethod
    def _parse_path(path):

        if "waveform_files" in path:
            waveformfiles = path["waveform_files"]
            filetype = None
        elif "waveform_dir" in path:
            waveformdir = path["waveform_dir"]
            filetype = path["filetype"].lower()
            waveform_pattern = os.path.join(waveformdir, "*"+filetype)
            waveformfiles = glob.glob(waveform_pattern)
        else:
            raise ValueError("missing keywords in json file, 'waveform_files'"
                             "or 'waveformdir'")

        if "staxml_files" in path:
            staxmlfiles = path["staxml_files"]
            create_simple_inv = False
        elif "staxml_dir" in path:
            staxmldir = path["staxml_dir"]
            staxml_pattern = os.path.join(staxmldir, '*.xml')
            staxmlfiles = glob.glob(staxml_pattern)
            create_simple_inv = False
        else:
            if filetype != "sac":
                raise ValueError("create_simple_inv only supports sac")
            staxmlfiles = None
            create_simple_inv = True

        tag = path["tag"]
        quakemlfile = path["quakeml_file"]
        outputfile = path["output_file"]

        return waveformfiles, tag, staxmlfiles, quakemlfile, outputfile,\
            create_simple_inv

    def _run_subs(self, path):

        waveformfiles, tag, staxmlfiles, quakemlfile, outputfile, \
            create_simple_inv = self._parse_path(path)

        self.print_info(waveformfiles, tag, staxmlfiles, quakemlfile,
                        outputfile, create_simple_inv)

        self.clean_output(outputfile)

        convert_to_asdf(outputfile, waveformfiles, tag,
                        quakemlfile=quakemlfile,
                        staxml_filelist=staxmlfiles,
                        verbose=self._verbose, status_bar=self._status_bar,
                        create_simple_inv=create_simple_inv)

    def run(self):
        path = smart_read_json(self.path, mpi_mode=False)
        if isinstance(path, list):
            for _path in path:
                self._run_subs(_path)
        else:
            self._run_subs(path)
