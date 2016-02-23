import os
from convert_util import convert_asdf_to_other

# scripts that convert asdf to sac file
asdffile = "/lustre/atlas1/geo111/scratch/lei/source_inversion_toolkit/"\
    "run_scripts/job_ebru_extra_test_1/data/C200502151442A/synthetic.h5"
outputdir = None

if outputdir is None:
    outputdir = os.path.join(os.path.dirname(asdffile), "sac")

if not os.path.exists(outputdir):
    os.makedirs(outputdir)

convert_asdf_to_other(asdffile, outputdir, filetype="sac", output_staxml=True,
                      output_quakeml=True)
