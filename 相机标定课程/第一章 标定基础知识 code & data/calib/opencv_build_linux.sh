#!/bin/sh

# install cmake
sudo apt-get install -y cmake

# install compiler environment
sudo apt-get install build-essential libgtk2.0-dev libavcodec-dev libavformat-dev libjpeg-dev libswscale-dev libtiff5-dev
sudo apt-get install libgtk2.0-dev
sudo apt-get install pkg-config

# build opencv
mkdir build
cd build
cmake --DBUILD_JAVA=OFF \
-DBUILD_opencv_java=OFF \
-DBUILD_TESTS=OFF \
..
sudo make -j8 install
