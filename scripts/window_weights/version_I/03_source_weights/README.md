### Source Weights

#### Usage

1. prepare path file.
  * modify the content in `generate_path_source_weights.py`.
  * run the script:
    ```
      python generate_path_source_weights.py
    ```

2. prepare the param file.

3. run the script to generate source weights:
  ```
  pypaw-source_weights -p param/source_weights.param.yml -f path/source_weights.path.json -v
  ```
  The source weights can then be applied during kernel summations.
