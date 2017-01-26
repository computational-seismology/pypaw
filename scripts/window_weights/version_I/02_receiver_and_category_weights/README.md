### Window Weights(version I)

Remember in this weighting strategy, the weights, which only contains receiver and category weights, are calculate event-wise.

##### Usage
1. Prepare the param file, which you get from step 1: `01_category_weights`.

2. Prepare the path file, one path file for one event.

3. Run the script for each event:
  ```
    pypaw-window_weights -p params/window_weights.param.yml -f paths/C052603A.path.json
  ```
  Attention here, you need to run this for every source you used in the inversion.
  After generating the weights, you can sum the adjoint source from different categories belonging to one event and launch and adjoint simulations. Once the kernel is generated, the sum of kerenls will then need the source weights, which is in step 3.
