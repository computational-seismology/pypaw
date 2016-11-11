# -*- coding: utf-8 -*-
# Ridvan Orsvuran, 2016
# Example user module

import numpy as np
from obspy.geodetics import calcVincentyInverse


def get_dist_in_km(station, event, obsd):
    """
    Returns distance in km
    """
    stats = obsd.stats
    # station inventory only includes synthetic data.
    name = ".".join([stats.network,
                     stats.station,
                     "S3",
                     "MXZ"])
    station_coor = station.get_coordinates(name)

    evlat = event.origins[0].latitude
    evlon = event.origins[0].longitude

    dist = calcVincentyInverse(
        station_coor["latitude"], station_coor["longitude"],
        evlat, evlon)[0] / 1000

    return dist


def get_time_array(obsd, event):
    stats = obsd.stats
    dt = stats.delta
    npts = stats.npts
    start = stats.starttime - event.origins[0].time
    return np.arange(start, start+npts*dt, dt)[:npts]


# raise levels after rayleigh
def generate_user_levels(config, station, event, obsd, synt):
    """Returns a list of acceptance levels
    """
    stats = obsd.stats
    npts = stats.npts

    base_water_level = config.stalta_waterlevel
    base_cc = config.cc_acceptance_level
    base_tshift = config.tshift_acceptance_level
    base_dlna = config.dlna_acceptance_level
    base_s2n = config.s2n_limit

    stalta_waterlevel = np.ones(npts)*base_water_level
    cc = np.ones(npts)*base_cc
    tshift = np.ones(npts)*base_tshift
    dlna = np.ones(npts)*base_dlna
    s2n = np.ones(npts)*base_s2n

    dist = get_dist_in_km(station, event, obsd)

    # Rayleigh
    r_vel = config.min_surface_wave_velocity
    r_time = dist/r_vel

    times = get_time_array(obsd, event)

    for i, time in enumerate(times):
        if time > r_time:
            stalta_waterlevel[i] = base_water_level*2.0
            tshift[i] = base_tshift/3.0
            cc[i] = 0.95
            dlna[i] = base_dlna/3.0
            s2n[i] = 10*base_s2n

    return stalta_waterlevel, tshift, dlna, cc, s2n
