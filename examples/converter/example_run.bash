#!/bin/bash

echo "Running examples..."

# #############################
# convert together using combined json file
#echo "+++++++++++++++"
#echo "Convert obsd and synt into asdf"
#python convert_asdf.py -p ./parfile/convert.par.json -v

# #############################
# convert seperately
# convert observed mseed files into hdf5 file
echo "++++++++++"
echo "Convert obsd files into asdf..."
pypaw-convert_to_asdf -f ./parfile/convert.obsd.json -v -s

# convert synthetic mseed files into hdf5 file
echo "+++++++++"
echo "Convert synt files into hdf5"
pypaw-convert_to_asdf -f ./parfile/convert.synt.json -v -s



