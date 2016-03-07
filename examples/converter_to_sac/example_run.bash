#!/bin/bash

echo "Running examples..."

# convert observed asdf into sac
echo "++++++++++"
echo "Convert obsd files into asdf..."
python convert_to_sac.py -s -q -v -o ../../tests/data/converted_sac/obsd ../../tests/data/asdf/raw/C200912240023A.observed.h5 

# convert synthetic asdf into sac
echo "+++++++++"
echo "Convert synt files into hdf5"
#python convert_to_sac.py



