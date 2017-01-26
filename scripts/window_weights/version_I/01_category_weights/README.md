### How to count windows for each categoryfor for all sources


##### Usage

1. Generate the path file
  * You need to provide the all the eventnames in `cmtlist.txt`.
  * Modify the default path in `generate_count_windows.py`.
  Then, run the script to generate path file.

  ```
    python generate_count_windows.py -f cmtlist.txt
  ```

2. Run the script:
  ```
    pypaw-count_overall_windows -f count_windows.path.json
  ```
  It will generate two files, one is `window_counts.log.json` and the other one is `window_weights.param.default.yml`. The first one is the log file for window counts. The second one is the parameter file for window weights, which gives you the ratio of category weightings. Be sure to check inside the param file and modify some values inside it, such as `search_ratio` and `plot` flag.
  Next, you can copy the `window_weights.param.default.yml` to the place you want and run the `pypaw-window_weights` to generate the window weights, including receiver weights and category weights.
