#!/usr/bin/env python
"""
Scripts that contains methods that deals with station information in the
asdf file.

:copyright:
    Wenjie Lei (lei@princeton.edu), 2016
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
from __future__ import (print_function, division, absolute_import)
import pyasdf
from pytomo3d.station import extract_staxml_info


def extract_station_info_from_asdf(asdf, verbose=False):
    """ extract the sensor type from stationxml in asdf file """
    if isinstance(asdf, str) or isinstance(asdf, unicode):
        ds = pyasdf.ASDFDataSet(asdf, mode='r')
    elif isinstance(asdf, pyasdf.ASDFDataSet):
        ds = asdf
    else:
        raise TypeError("Input asdf either be a filename or "
                        "pyasdf.ASDFDataSet")

    asdf_sensors = dict()
    ntotal = len(ds.waveforms)
    for idx, st_group in enumerate(ds.waveforms):
        if verbose:
            print("[%4d/%d]Station: %s"
                  % (idx, ntotal, st_group._station_name))
        try:
            inv = st_group.StationXML
            info = extract_staxml_info(inv)
            asdf_sensors.update(info)
        except Exception as msg:
            print("Failed to extract due to: %s" % msg)
            continue

    print("Number of stations and channels: %d, %d"
          % (ntotal, len(asdf_sensors)))

    return asdf_sensors


def extract_waveform_stations(asdf, stations=None):
    """
    Extract station information from wavefrom group
    """
    if isinstance(asdf, str):
        ds = pyasdf.ASDFDataSet(asdf, mode='r')
    elif isinstance(asdf, pyasdf.ASDFDataSet):
        ds = asdf
    else:
        raise TypeError("Input asdf either be a filename or "
                        "pyasdf.ASDFDataSet")

    sta_dict = {}
    if stations is None:
        stations = ds.waveforms.list()
    for st_id in stations:
        station_group = getattr(ds.waveforms, st_id)
        if "StationXML" not in dir(station_group):
            continue
        staxml = getattr(station_group, "StationXML")
        sta_dict[st_id] = [staxml[0][0].latitude, staxml[0][0].longitude,
                           staxml[0][0].elevation,
                           staxml[0][0][0].depth]

    return sta_dict


def extract_adjoint_stations(asdf, stations=None):
    """
    Extract station information from adjoint source group
    """
    if isinstance(asdf, str):
        ds = pyasdf.ASDFDataSet(asdf, mode='r')
    elif isinstance(asdf, pyasdf.ASDFDataSet):
        ds = asdf
    else:
        raise TypeError("Input asdf either be a filename or "
                        "pyasdf.ASDFDataSet")

    sta_dict = {}
    try:
        adjsrcs = ds.auxiliary_data.AdjointSources
    except:
        return {}

    if stations is None:
        stations = adjsrcs.list()
    for adj_name in stations:
        adj = getattr(adjsrcs, adj_name)
        pars = adj.parameters
        station_id = pars["station_id"]
        if station_id not in sta_dict:
            sta_dict[station_id] = [pars["latitude"], pars["longitude"],
                                    pars["elevation_in_m"],
                                    pars["depth_in_m"]]

    return sta_dict
