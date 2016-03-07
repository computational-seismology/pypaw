Data Format and Conversion
==========================

** This part requires you to have some basic knowledge about `Obspy <https://github.com/obspy/obspy/wiki>`_ and `Pyasdf <http://seismicdata.github.io/pyasdf/>`_.

1. Data Format
--------------
The data format here we used is `ASDF <https://github.com/SeismicData>`_. If you are not familiar with this data format, please have a look at this link: `ASDF <http://asdf.readthedocs.org/en/latest/index.html>`_.

The ASDf is developed with many great features. But here I will mention two of them:

1. One asdf file contains the complimentary information for general purpose processing, including the waveform, StationXML and event information. You can add as many as waveforms you want, for example, all data for one event could be stored in a single ASDF file. 

   To compare with *sac*, people usually need to store with SAC(waveform), RESPONSE file and event file separatly. The number of files are large and usually stored at different places. This kind of directory complexity increase the possiblities of making erros dramatically.

2. It has internal support for parallel computation, which is very easy to use and reduce the processing time by a factor of number of processors.

For more features of asdf, please take a look at the offcial doc of ASDF project.

2. Data Conversion
------------------
The data conversion to ASDF is simple, with the tools provided by Pyasdf. A detailed instruction could be found in `pyasdf <http://seismicdata.github.io/pyasdf/tutorial.html#creating-an-asdf-data-set>`_. Here, for user's simplicity, I created an tool for easy data conversion. 

**1. Data requirements**:

1. **Waveform data**: any data format supported by `obspy <https://docs.obspy.org/packages/autogen/obspy.core.stream.read.html>`_ could be used as waveform data.
2. **Quakeml file**: Quakeml file that contains event information.
3. **StationXML files(*optional*)**: StationXML files are reuquired here if you want to extrace station information, for example, station location and instrument response information. 

   * For observed data, including StationXML files into For people using SAC, they are familiar with RESPONSE or POLES_AND_ZEROS files.

   * For synthetic data, you don't need the response information you don't need to include the StationXMl files. You could create you own StationXML in memory(no real I/O) and add them into the ASDF file. For example, in you are using SAC, if station location information are already stored in the SAC header, you don't need to bother with StationXML files. Pypaw will help you automatically extract station information and store them into ASDF file.

**2. Conversion to ASDF**

Once the data is ready, then you can start to convert them into ASDF file.
You need to prepare a path file to specify the path of waveforms, stationxmls and quakeml.

For example, for observed data in MSEED, the path file(in json format)::

  {
    "waveform_dir": "/path/to/observed/waveform/dir",
    "filetype": "mseed", 
    "quakeml_file": "/path/to/quakeml/file", 
    "staxml_dir": "/path/to/stationxml/dir",
    "output_file": "path/to/output/asdf/file", 
    "tag": "observed"
  }

The ``tag`` is waveform tags required by ASDF.

For synthetic data in SAC, if station location information(laitude, longitude, elevation and depth) is already stored in the header, then you don't need external stationxml files. During the conversion, a simple stationxml will be generated in the memory::

  {
    "waveform_dir": "/path/to/synthetic/waveform/dir",
    "filetype": "sac", 
    "quakeml_file": "/path/to/quakeml/file", 
    "output_file": "path/to/output/asdf/file", 
    "tag": "synthetic"
  }

Then you need to write the data conversion script::

  #!/usr/bin/env python

  import argparse
  from pypaw import ConvertASDF

  if __name__ == '__main__':

      parser = argparse.ArgumentParser()
      parser.add_argument('-f', action='store', dest='path_file', required=True)  
      parser.add_argument('-v', action='store_true', dest='verbose')
      parser.add_argument('-s', action='store_true', dest='status_bar')
                          args = parser.parse_args()

      converter = ConvertASDF(args.path_file, args.verbose, args.status_bar)
      converter.run()

Save this as `convert_asdf.py` and you can use it::

  python convert_asdf.py -f convert.obsd.path.json -v -s

Examples of data conversion is located at `'examples/converter'`.

**3. Conversion to SAC from ASDF**

You can also convert ASDF to sac files. The script is located at ``examples/converter_to_sac/convert_to_sac.py``. Type::

  convert_to_sac.py --help

to check the usages.

**4. Genarate station file from ASDF**

Station file(used in SPECFEM3D_GLOBE) could be generated from ASDF file. The script is located at ``scripts/bins/generate_stations_asdf.py``. Type::

  generate_stations_asdf.py --help

to check the usage.

* You could add `'scripts/bins'` to your `~/.bashrc`. So you can directly use scripts inside pypaw.
