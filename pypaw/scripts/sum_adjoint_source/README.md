### Sum of the adjoint source

In specfem, we need to sum adjoint source from different band together.
For example, we filter the seismogram into two period band, 27s-60s and
60s-120s. We process them and generate the adjoint sources in these
two period bands. Then we are goint to sum them up and feed into SPECFEM.
There are two weighting strategy.

##### Weighting strategy 1
This strategy only takes into account of weighting on category. 

"Category" here, 
is defined as period band together with component. Using the above example, we 
have two period band and three components, "BHZ", "BHR" and "BHT". So there 
are total 6 categories. This operation means all events and receivers will be
treated equally if there have the same period band and category. For on asdf file,
which is usually one period band and three components, only limited information is
required, which is the weighting for each component. See example in directory 
"paths_simple".

##### Weightin strategy 2
This strategy is more sophicated, which taks into account of receiver, source,
and category information. Thus, a weighting profile file needs to be provided.
See examples in directory "paths".
