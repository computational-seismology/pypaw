## Instructions

#### Data Conversion
1. Run the convert which convert raw observed data(mseed file) and synthetic data(sac format) into ASDF. Also, it is nice to include quakeml file and stationxml files into ASDF. We also did that during the conversion.
  ```
  cd converter
  bash example_run.bash
  cd ..
  ```
and check the result.

#### Data Processing(step by step)
1. Run the signal processsing on the ASDF data we converted from step 1.
  ```
  cd signal_processing
  bash example_run.bash
  cd ..
  ```

2. Run the window selection on the ASDF data we processed from step 2.
  ```
  cd window_selection
  bash example_run.bash
  cd ..
  ```

3. Run the adjoint source constructor on the ASDF data and windows.
  ```
  cd adjoint_sources
  bash example_run.bash
  cd ..
  ```

#### Data Processing(as a whole)
Run the whole preprocessing as a whole, which includes the signal processing, window selection and adjoint sources. The output is adjoint source in ASDF file.
```
cd preproc_wf
bash example_run.bash
cd ..
```
