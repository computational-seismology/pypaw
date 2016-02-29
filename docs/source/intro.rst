============
Introduction
============

This is package provides people with tools for easy usage of pyasdf in seismic data processing. including signal processing, window selection and calculation of adjoint sources.

Using ASDF as the data format, it helps users to handle the parallel I/O without paying too much attention to the implementation details. Users just need to specify some path and parameter files and job would be done in a easy and clean way.

This package constains two parts: **I/O** and **Processing Kernel**. I will illustrate these two concepts.

1. I/O
------
   The I/O part is handled in `Pyasdf <https://github.com/SeismicData/pyasdf>`_. The provides some APIs how you would view the asdf file and extract the trace. For example, singal processing requires one asdf file and window selection requires two asdf file. Pyasdf provides different APIs for these two different service. However, users don't need to worry to much about it since t is totaly hidden under the hood.

2. Processing Kernel
--------------------
   It defines the behaviour on the seismograms. 

   For the singal processing part, the processing kernel means how you define the operation on one seismogram. Once this behavior is defined, the pypaw will apply the same operation to all the seimograms in the asdf file(with parallel capability). 

   For the window selection part, the processing kernel means the operation how you select windows on a pair of observed and synthetic traces. Once this behavior is defined, the pypaw will extract the two traces from two ASDF files with same trace id and apply the operation to all pairs of seismograms.

   For the adjoint part, it is similar to window selection part. The processing kernel means given a pair of observed and synthetic data, together with windows, how to calculate the adjoint sources.

