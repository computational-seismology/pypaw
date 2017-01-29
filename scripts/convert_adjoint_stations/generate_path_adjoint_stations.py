"""
Generate path file for convert adjoint stations
"""
import os
import json


def load_txt(fn):
    with open(fn) as fh:
        return [line.rstrip() for line in fh]


def dump_json(content, fn):
    with open(fn, 'w') as fh:
        json.dump(content, fh, indent=2, sort_keys=True)


def file_exists(fn):
    if not os.path.exists(fn):
        raise ValueError("File not exists: %s" % fn)


def generate_adjoint_station_paths(
        eventname, period_bands, basedir, path_dir):
    measure_dir = os.path.join(basedir, "measure")
    station_dir = os.path.join(basedir, "stations")
    output_dir = os.path.join(basedir, "stations_adjoint")

    measure_files = {}
    for pb in period_bands:
        # use filtered measurements file
        fn = os.path.join(
            measure_dir, "%s.%s.measure_adj.json.filter" % (eventname, pb))
        file_exists(fn)
        measure_files[pb] = fn

    station_file = os.path.join(station_dir, "%s.stations.json" % eventname)
    output_file = os.path.join(output_dir, "STATIONS_ADJOINT.%s" % eventname)

    content = {"measure_files": measure_files, "station_file": station_file,
               "output_file": output_file}

    path_json = os.path.join(path_dir, "%s.adjoint_stations.path.json" %
                             eventname)
    dump_json(content, path_json)


def main():
    period_bands = ["17_40", "40_100", "90_250"]
    basedir = "/lustre/atlas/proj-shared/geo111/Wenjie/DATA_M16"
    pathdir = "paths"

    print("Output path dir: %s" % pathdir)
    if not os.path.exists(pathdir):
        os.makedirs(pathdir)

    eventlist = load_txt("../eventlist.wenjie")
    print("Number of events: %d" % len(eventlist))
    for event in eventlist:
        generate_adjoint_station_paths(event, period_bands, basedir, pathdir)



if __name__ == "__main__":
    main()
