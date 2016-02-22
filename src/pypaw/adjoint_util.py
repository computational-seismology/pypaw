from __future__ import (absolute_import, division, print_function)
import os
from functools import partial

from pyadjoint import AdjointSource


def ensemble_fake_adj(stream, time_offset=0.0):
    """
    Ensemble fake adjoint sources from stream, for test purpose
    """

    adjsrc_dict = dict()
    comps = ["Z", "R", "T"]
    nwin_dict = dict()
    for comp in comps:
        tr = stream.select(channel="*%s" % comp)[0]
        adj = AdjointSource("waveform_misfit", misfit=0.0, dt=tr.stats.delta,
                            min_period=50.0, max_period=100.0,
                            component=tr.stats.channel[-1],
                            adjoint_source=tr.data, network=tr.stats.network,
                            station=tr.stats.station)
        adjsrc_dict[tr.id] = adj
        nwin_dict[tr.id] = 1

    return adjsrc_dict, nwin_dict


def reshape_adj(adjsrcs, time_offset):
    """
    Reshape adjsrcs to a certain structure required by pyasdf writer
    """
    if not isinstance(adjsrcs, list):
        raise ValueError("Input ajdsrcs must be a list of adjoint sources")

    vtype = "AuxiliaryData"
    reshape_list = []
    tag_list = []
    for adj in adjsrcs:
        adj_array = adj.adjoint_source

        station_id = "%s.%s" % (adj.network, adj.station)

        parameters = {"dt": adj.dt, "time_offset": time_offset,
                      "misfit": adj.misfit,
                      "adjoint_source_type": adj.adj_src_type,
                      "min_period": adj.min_period,
                      "max_period": adj.max_period,
                      "latitude": 0.0, "longitude": 0.0,
                      "elevation_in_m": 0.0,
                      "station_id": station_id, "component": adj.component,
                      "units": "m"}

        tag = "%s_%s_MX%s" % (adj.network, adj.station, adj.component)
        tag_list.append(tag)

        dataset_path = "AdjointSources/%s" % tag

        _reshape = {"object": adj_array, "type": vtype,
                    "path": dataset_path, "parameters": parameters}

        reshape_list.append(_reshape)

    # check if there are different adjoint sources with the same tag. If so,
    # the writer won't be able to write out because of the same dataset path
    if len(set(tag_list)) != len(tag_list):
        raise ValueError("Duplicate tag in adjoint sources list: %s" %
                         tag_list)

    return reshape_list


def calculate_chan_weight(nwins_dict):

    comp_dict = {}
    for chan_id, nwins in nwins_dict.iteritems():
        comp = chan_id.split(".")[-1][-1]
        if comp not in comp_dict.keys():
            comp_dict[comp] = {}
        comp_dict[comp][chan_id] = nwins

    for comp, comp_wins in comp_dict.iteritems():
        ntotal = 0
        for chan_id, chan_win in comp_wins.iteritems():
            ntotal += chan_win
        for chan_id, chan_win in comp_wins.iteritems():
            comp_dict[comp][chan_id] = chan_win / ntotal

    return comp_dict
