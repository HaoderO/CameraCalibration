# CMake
sudo apt-get install cmake
# google-glog + gflags
sudo apt-get install -y libgoogle-glog-dev libgflags-dev
# BLAS & LAPACK
sudo apt-get install -y libatlas-base-dev
# Eigen3
sudo apt-get install -y libeigen3-dev
# SuiteSparse and CXSparse (optional)
sudo apt-get install -y libsuitesparse-dev
#build ceres
cd ceres-solver-2.0.0rc1
mkdir ceres_build
cd ceres_build
cmake -DMINIGLOG=ON \
..
sudo make install -j8

