#!/bin/bash

#################################################
# Parallel runing pyflex(mpi required)
# If you turned the figure mode on, please use less 
# cores since every core will write large figure files.
# Since the test file only contains 4 stream, please
# the numproc=2 and do not change it.
mpiexec -n 2 python window_selection.py \
  -p ./parfile/window.param.yaml \
  -f ./parfile/window.path.json \
  -v

################################################
# Test for another type of input json
#mpiexec -n 2 python parallel_pyflex.py \
#  -p ./parfile/body_window.params.json \
#  -f ./parfile/body_window.dirs.json \
#  -v
