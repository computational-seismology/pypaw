Tutorial
========

** This tutorial requires you to have some basic knowledge about `Obspy <https://github.com/obspy/obspy/wiki>`_ and `Pyasdf <http://seismicdata.github.io/pyasdf/>`_.  

If you hava difficulty plotting figures on cluster, check you X11 settings. Also, if you don't want to use X11 environment, please add add these two lines at the top of your python job script::
  
  import matplotlib as mpl
  mpl.use('Agg')  # NOQA 

1. Singal Processing
--------------------
There are two files you need to prepare for the signal processing part.

1. a **path** file which specifies the path of input asdf file and output asdf file, and tags asscociated with those files. A example 'path.json' file::

    {
      "input_asdf": "/path/to/input/asdf/file" 
      "input_tag": "input_tag",
      "output_asdf": "/path/to/output/asdf/file",
      "output_tag": "output_tag"
    } 

2. a **parameter** file which specifies the processing parameter, like filtering band, cutting starttime and endtime, etc. A example 'param.yml' file::
      
    # remove response flag to remove the instrument response from the
    # seismogram. For observed seismogram, you probably want to set this 
    # flag to True to get real gound displacement. For synthetic data,
    # please set this flag to False
    remove_response_flag: True

    # filtering the seismogram. If you set both remove_response_flag to True
    # and filter_flag to True, the filtering will happen at the same time
    # when you remove the instrument response(to make sure the taper is applied
    # only once)
    filter_flag: True

    # frequency band of filtering, unit in Hz
    pre_filt: [0.0067, 0.01, 0.02, 0.025]

    # cut time relative to CMT time. The final seismogram will be at
    # time range: [cmt_time+relative_time, cmt_time+relative_time]
    relative_starttime: 0
    relative_endtime: 6000

    # resample the seismogram. Sampling_rate in unit Hz.
    resample_flag: True
    sampling_rate: 5

    # taper
    taper_type: "hann"
    taper_percentage: 0.05

    # rotate flag
    rotate_flag: True

After preparing the path and parameter file, you need the job script::

  #!/usr/bin/env python                                                           
  import argparse                                                                 
  from pypaw import ProcASDF                                                      
                                                                                
  if __name__ == '__main__':                                                      
                                                                                
      parser = argparse.ArgumentParser()                                          
      parser.add_argument('-p', action='store', dest='params_file',               
                          required=True)                                          
      parser.add_argument('-f', action='store', dest='path_file', required=True)  
      parser.add_argument('-v', action='store_true', dest='verbose')              
      args = parser.parse_args()                                                  
      proc = ProcASDF(args.path_file, args.params_file, args.verbose)             
      proc.smart_run()  

Save it as `process_asdf.py` and you can run it using 16 cores::

  mpiexec -n 16 python process_asdf.py -f path.json -p param.yml

Examples of the observed and synthetic data processing are at ``examples/signal_processing`` 

2. Window Selection
-------------------
Window selection also requires two files to specify the data path and window parameters. For input, it requires one observed and one synthetic asdf file. The output is one window file. A example of 'path.json' file is::

  {  
    "obsd_asdf": "/path/to/obsd/asdf/file",
    "obsd_tag": "obsd_tag",
    "synt_asdf": "/path/to/synt/asdf/file",
    "synt_tag": "synt_tag",
    "output_dir": "/path/to/output/directory",
    "figure_mode": False
  } 

An example of 'param.yml' file is::

  "Z": "/path/to/window_selection.compZ.config.yaml"
  "R": "/path/to/window_selection.compR.config.yaml"
  "T": "/path/to/window_selection.compT.config.yaml"

Since sometimes people want to setup different criteria for different components, So in 'param.yml' file you can set different ``'window_selection.comp*.config.yaml'``. A example of 'config.yml' file is located at ``'examples/window_selection/parfile/50_100.BHZ.config.yml'``. It is a bit long so I won't list the file here.

Next step is prepare the job script, which is very similiar to the signal processing part::
  
  #!/usr/bin/env python
  import argparse
  from pypaw import WindowASDF

  if __name__ == '__main__':
      parser = argparse.ArgumentParser()
      parser.add_argument('-p', action='store', dest='params_file',
                          required=True)
      parser.add_argument('-f', action='store', dest='path_file', required=True)
      parser.add_argument('-v', action='store_true', dest='verbose')
      args = parser.parse_args()
      proc = WindowASDF(args.path_file, args.params_file, verbose=args.verbose)
      proc.smart_run()

Save it as ``window_selection_asdf.py`` and the job could be launched using 16 cores::
  
  mpiexec -n 16 python window_selection_asdf.py -f path.json -p param.yml -v

One tip, if you set the ``figure_mode`` as ``True``, then don't use too many cores because each core will generate a lot of  figures and output figure will take a lot of I/Os.

3. Adjoint Sources
------------------
Path and parameter files should be specified. For input, it requires an observed and synthetic asdf file, a window file. The output is an adjoint asdf file. A example of 'path.json' file::

  {
    "obsd_asdf": "/path/to/obsd/asdf/file",
    "obsd_tag": "obsd_tag",
    "synt_asdf": "/path/to/synt/asdf/file",
    "synt_tag": "synt_tag",
    "window_file": "/path/to/window/file",
    "output_file": "/path/to/output/adjoint/asdf/file",
    "figure_mode": false,
    "figure_dir": "/path/to/output/figure/dir"
  } 

For adjoint sources, you can choose different measurements. Currently, it supports three different measurements:
* Waveform misfit
* Cross-correlation traveltime misfit
* Multi-taper traveltime misfit

For different measurements, you need prepare different parameter files for this. A example of multi-taper misfit parameter file, 'param.yml' is listed::

  # adjoint source type
  adj_src_type: "multitaper_misfit"

  # min and max period(unit: second)
  min_period: 50.0
  max_period: 100.0

  # adjoint config parameter
  lnpt: 15
  transfunc_waterlevel: 1.0E-10
  ipower_costaper: 10
  min_cycle_in_window: 3
  taper_percentage: 0.3
  mt_nw: 4.0
  num_taper: 5
  phase_step: 1.5
  dt_fac: 2.0
  err_fac: 2.5
  dt_max_scale: 3.5
  measure_type: 'dt'
  taper_type: 'hann'
  use_cc_error: True
  use_mt_error: False

  # for postprocessing
  interp_delta: 0.1425
  interp_npts: 42000

Next step is also preparing the job script. Similiar to previous examples, the job script would be::

  #!/usr/bin/env python
  import matplotlib as mpl
  mpl.use('Agg')  # NOQA
  import argparse
  from pypaw import AdjointASDF

  if __name__ == '__main__':

      parser = argparse.ArgumentParser()
      parser.add_argument('-p', action='store', dest='params_file',
                          required=True)
      parser.add_argument('-f', action='store', dest='path_file', required=True)
      parser.add_argument('-v', action='store_true', dest='verbose')
      args = parser.parse_args()

      proc = AdjointASDF(args.path_file, args.params_file, verbose=args.verbose)
      proc.smart_run()

Save it as ``adjoint_asdf.py`` and you can launch the parallel job using 16 cores::
  
  mpiexec -n 16 python adjoint_asdf.py -f path.json -p param.json -v
  
For more examples of different measurements, please take a look at ``examples/adjoint_sources`` 

4. Advanced usage
-----------------

If you have already went through all the 3 steps above, a more advanced usage is provided, which combines all the 3 steps as a whole. The 'path.json' specifies the observed and synthetic file, and output adjoint asdf file::

  {
    "obsd_asdf": "/path/to/raw/observed/asdf/file",
    "obsd_tag": "observed",
    "synt_asdf": "/path/to/raw/synthetic/asdf/file",
    "synt_tag": "synthetic",
    "output_asdf": "/path/to/output/adjoint/asdf/file",
    "figure_mode": false,
    "figure_dir": "None"
  } 

The 'param.yaml' file specifies the parameter files for different parts::

  {
    "proc_obsd_param": "./proc_obsd.50_100.yml",
    "proc_synt_param": "./proc_synt.50_100.yml",
    "window_param": {
      "Z": "50_100.BHZ.config.yml",
      "R": "50_100.BHZ.config.yml",
      "T": "50_100.BHZ.config.yml"
    },
    "adjsrc_param": "multitaper.adjoint.config.yml"
  }

Job scripts::

  #!/usr/bin/env python
  import argparse
  from pypaw import AdjPreASDF

  if __name__ == '__main__':

      parser = argparse.ArgumentParser()
      parser.add_argument('-p', action='store', dest='params_file',
                          required=True)
      parser.add_argument('-f', action='store', dest='path_file', required=True)
      parser.add_argument('-v', action='store_true', dest='verbose')
      args = parser.parse_args()

      proc = AdjPreASDF(args.path_file, args.params_file, verbose=args.verbose)
      proc.smart_run()

Save it as 'adjproc.py' and launch the job on 16 cores::
  
  mpiexec -n 16 python adjproc.py -f path.json -p param.yml -v
