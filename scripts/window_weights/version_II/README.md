### Weighting Strategy II

This weighting strategy determines all the weightins, including receiver weighting, source weighting and category weighting, at once.

#### Usage

1. Prepare the path file.
  Details are in `path` directory.

2. Prepare the param file.
  * `plot` flag in receiver weighting is very expensive if you have large number of events.
  * be careful about the `search_ratio` since it will change dramatically the weightings.
  * `category_weighting` are dummy here because it will run at any. I put it here just to remind people.

3. Run the script.
  ```
    pypaw-window_weights_version_ii -p param/window_weights.param.yml -p path/window_weights.path.json -v
  ```
  Notice that you need to put ALL events used in the path file. Also, you need to make sure the sources do not change afterwards.

#### Future improvements
  1. Currently, all the weightings are stored in the memory and only after everything is done, it get write out. If you have large number of sources, it might get memory overflow. I will improve this later. But for my test, 64GB memory can easily handle 1000 events for now.
