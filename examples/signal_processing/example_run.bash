#!/bin/bash

echo "Running examples for data processing..."

##################################################
# process observed asdf file
# Currently, there are two ways to launch the job
# 1) multi-processing
# 2) mpi
# Both examples are provided

echo "++++++"
echo "process observed file..."
# multi-processing
#python process_observed.py \
#  -p ./parfile/proc_obsd.params.json \
#  -f ./parfile/proc_obsd.dirs.json \
#  -v

# mpi
mpiexec -n 2 pypaw-process_asdf \
  -p ./parfile/proc_obsd.50_100.param.yml \
  -f ./parfile/proc_obsd.path.json \
  -v

##################################################
# process synthetic asdf file
# Currently, there are two ways to launch the job
# 1) multi-processing
# 2) mpi
# Both examples are provided

echo "++++++"
echo "process synthetic file..."
mpiexec -n 2 pypaw-process_asdf \
  -p ./parfile/proc_synt.50_100.param.yml \
  -f ./parfile/proc_synt.path.json \
  -v
