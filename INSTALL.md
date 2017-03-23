# Installing python dependencies

Pypaw has dependancies on the following packages:

1. [obspy](https://github.com/obspy/obspy)
2. [pytomo3d](https://github.com/wjlei1990/pytomo3d)
3. [hdf5-libray compiled with parallel support](https://www.hdfgroup.org/HDF5/)
4. [h5py](http://www.h5py.org/)
5. [mpi4py](https://mpi4py.scipy.org/docs/usrman/index.html)
6. [pyasdf](https://github.com/SeismicData/pyasdf)


## Manual installation

#### 1. load your compiler modules.
  You can choose any version you like(intel, gnu or pgi). But we are using GNU compiler on RHEA at ORNL.

  ```
  module load gcc/4.8.2
  module load openmpi/1.8.4
  ```

#### 2. downwnload Anaconda for Python 2.7 and 64 bit Linux and install it (http://continuum.io/downloads)(**optional**)

  Tips: If you are new to python, [anaconda](https://www.continuum.io/downloads) is recommmended. Please download the newest version( >= Anaconda2 - 2.5.0) since it already contains a lot of useful python packages, like pip, numpy and scipy.  Older versions is not recommended since it usually has compliers inside, like gfortran and gcc. It is always better to use comiplers coming from your system rather than the very old ones embeded in anaconda. If you are expert in python, please choose the way you like.

#### 3. uninstall all HDF5 and MPI related things.
  Those need to be recompiled to enable parallel I/O and use the MPI implementation of the current machine
  ```
  conda uninstall hdf5 h5py openmpi mpi4py
  ```

#### 4. install obspy using conda

  ```
  conda install -c obspy obspy
  ```

#### 5. Install pytomo3d.
  Pytomo3d also has dependancies(including obspy, pyflex and pyadjoint). Please see the *INSTALL.md* in pytomo3d to check the dependacies.

  Please carefully read the installtion documentation [here](https://github.com/wjlei1990/pytomo3d/blob/master/INSTALL.md). There are also some softwared depandancy to install pytomo3d, which means you need to additionally install some other python pakcages. For some packages(like pyadjoint and pyflex), we have our own modifications.
  ```
  git clone https://github.com/wjlei1990/pytomo3d
  cd pytomo3d
  pip install -v -e .
  cd ..
  ```
  
  To make sure you install this package correctly, you can try:
  ```
  cd pytomo3d
  py.test
  ```
  and see if all tests pass.


#### 6. install mpi4py
  ```
  pip install mpi4py==1.3.1
  ```

#### 7. load(or install) hdf5-parallel

  For large computing clusters, hdf5-parallel is usually pre-installed(or work as a module). So first you want to check if this library is pre-installed on your machine. If so, load the module and go to the next step. If not, you need to install hdf5-parallel yourself.  
  For some cases, even the hdf5-parallel is pre-installed on your machine, it might not work since it is not compiled with correct flags(shared library or so). If the system library doesn't work, install it yourself. For example, there is a module one tiger called `hdf5/intel-13.0/openmpi-1.8.8`. However, I could not use that since h5py fails on it. So I download hdf5 and compiled it myself.

  If you decided to install the library yourself, get it from this link: [https://www.hdfgroup.org/HDF5/release/obtainsrc.html](https://www.hdfgroup.org/HDF5/release/obtainsrc.html) or use command line:
  ```
  wget http://www.hdfgroup.org/ftp/HDF5/current/src/hdf5-1.8.16.tar
  tar -xvf hdf5-1.8.16.tar 
  ```

  Here is the instruction on how to build it up with parallel support: [https://www.hdfgroup.org/ftp/HDF5/current/src/unpacked/release_docs/INSTALL_parallel](https://www.hdfgroup.org/ftp/HDF5/current/src/unpacked/release_docs/INSTALL_parallel). Before installation, type in `which mpicc` to check your mpicc compiler

  A simple configure and compiled instruction:
  ```
  cd hdf5-1.8.16
  CC=mpicc ./configure --enable-fortran --enable-parallel --prefix=/path/to/hdf5/install/dir --enable-shared --enable-static
  make
  make install
  ```
  I found a very useful link to talk about how to install hdf5-parallel and h5py. It is here:
  ```
  http://alexis.praga.free.fr/computing/2014/04/02/rant-h5py.html
  ```

#### 10. install h5py
  Down load the code using:
  ```
  git clone https://github.com/h5py/h5py
  ```
  and then install the code.
  ```
  cd h5py
  export CC=mpicc
  python setup.py configure --mpi
  python setup.py configure --hdf5=/path/to/hdf5/install/dir
  python setup.py build
  python setup.py install
  ```
  See detailed instructions at [here](http://docs.h5py.org/en/latest/build.html)

#### 11. install PyASDF
  ```
  git clone https://github.com/wjlei1990/pyasdf
  cd pyasdf
  pip install -v -e .
  cd ..
  ```

#### 12. install pypaw
  ```
  git clone https://github.com/wjlei1990/pypaw
  cd pypaw
  pip install -v -e .
  cd ..
  ```
