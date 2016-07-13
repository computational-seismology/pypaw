import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name="pypaw",
    version="0.1.0",
    license='GNU Lesser General Public License, version 3 (LGPLv3)',
    description="Seismic tomograpy and ASDF toolkits",
    author="Wenjie Lei",
    author_email="lei@princeton.edu",
    url="https://github.com/wjlei1990/pypaw",
    packages=["pypaw"],
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    zip_safe=False,
    classifiers=[
        # complete classifier list:
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    keywords=[
        "seismology", "tomography", "adjoint", "signal", "inversion", "window"
    ],
    install_requires=[
        "numpy", "obspy>=1.0.0", "flake8", "pytest", "nose", "future>=0.14.1",
        "pytomo3d", "pyasdf"
    ],
    entry_points={
        'console_scripts':
            ['pypaw-process_asdf=pypaw.bins.process_asdf:main',
             'pypaw-window_selection_asdf=pypaw.bins.window_selection_asdf:main',  # NOQA
             'pypaw-adjoint_asdf=pypaw.bins.adjoint_asdf:main',
             'pypaw-extract_sensor_type=pypaw.bins.extract_sensor_type:main',
             'pypaw-calculate_window_weights=pypaw.bins.window_weights.calculate_window_weights:main',  # NOQA
             'pypaw-sum_adjoint_asdf=pypaw.bins.sum_adjoint_source.sum_adjoint_asdf:main',  # NOQA
             'pypaw-adjoint_misfit_from_asdf=pypaw.bins.adjoint_misfit_from_asdf:main',     # NOQA
             'pypaw-convert_adjsrcs_from_asdf=pypaw.bins.convert_adjsrcs_from_asdf:main',   # NOQA
             'pypaw-convert_to_asdf=pypaw.bins.convert_to_asdf:main',
             'pypaw-convert_to_sac=pypaw.bins.convert_to_sac:main',
             'pypaw-generate_stations_asdf=pypaw.bins.generate_stations_asdf:main',        # NOQA
             ]
    },
    extras_require={
        "docs": ["sphinx", "ipython", "runipy"]
    }
)
