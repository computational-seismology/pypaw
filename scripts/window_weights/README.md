### Introduction

This directory contains example files for two different weighting strategies,
both of which are already implemented in pypaw.

##### Weighting Strategy Version I

The weightings is determined in order of category, receiver and finally, source.
  1. determine the category weightings ratio based on number of window counts in each category.
    Attention here that we determined is the ratio between each category but not the absolute
    values. The absolut values will be determined on each event level(to satisfy the
    normalization equation).
  2. determine the receiver weightings based on station geographic distribution(ratios) and window
    counts(normalization) of each receiver given one event.
    Also, determine the absolute values of category weightings for each source.
    Once you reach this step, you can use the weights
    (category and receiver combined) to sum the adjoint source from each category for each event.
    And once you get summed adjoint source for each event, you can then launch the adjoint simulation
    to calculate the kernel for each source.
  3. determine the source weightings based on source geographic distribution(ratio) and
    number of windows(normalization) of each source. The source weightings are applied on kernels
    when summing all the kernels together.

The benefit of version I is that you can freely combine kernels from different number of sources.
For example, if you have certain number of failed adjoint simulations, whose kernels are missing,
as long as the number of missing sources are not large(which doesn't impact the category weightings
that much), you are assign the sources weights depands on real source distributions(for what you have)

Another case is that you split you dataset into two(no duplicate events) and calculate receiver
and category weightings in these two sets. Once you get the kernels, you can calculate source
weightins based on all sources(two sets combined) and add the kernels together. So basically,
this weighting gives you more freedom when combining kernels.

The draw back of that is it doesn't gurantee the weightins for different categories are
evenly balanced(but will not be too deviated, based on my experiment).


###### Weighting Strategy Version II
The weightings are determined in order of receiver, source and finally category.
  1. determine the receiver weightings based on window counts and station distribution.
    (same as version I)
  2. determine the source weightings based on source geographic distribution(ratio) and
    number of sources(the sum of source weights eqaul to number of sources)
  3. determine the category weightings based on source weights(ws) number of windows in
    each category(Nsc) and number of categories(C).
      wc = 1 / (C * \sum_{s} ws * Nsc)
  4. Finally, you combine the receiver, source and category weightings

The benefit of this weighting is you can guarantee that the sum of weightings from each
categor are balanced. However, the price you need to pay is the weighting is not so flexible
as version I. Because the category weightins are build upon source weightings, which means
the source has to be fixed before the adjoint simulation. If there is one source failed at
adjoint simulation, you have to finished it otherwise the sum of weightings won't be
normalized to 1.0.
