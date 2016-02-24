#!/bin/bash

#################################################
# Parallel runing pyflex(mpi required)
# If you turned the figure mode on, please use less 
# cores since every core will write large figure files.
# Since the test file only contains 4 stream, please
# the numproc=2 and do not change it.
mpiexec -n 2 python adjproc.py \
  -p adjproc.param.json \
  -f adjproc.path.json \
  -v
