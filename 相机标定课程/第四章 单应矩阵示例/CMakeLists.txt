# cmake needs this line
cmake_minimum_required(VERSION 3.1)

# Define project name
project(opencv_homograph_project)

# Find OpenCV, you may need to set OpenCV_DIR variable
# to the absolute path to the directory containing OpenCVConfig.cmake file
# via the command line or GUI
# Please comment the following sentence under Linux 
set(OpenCV_DIR "E:/SDK/opencv/build")
find_package(OpenCV REQUIRED)

# If the package has been found, several variables will
# be set, you can find the full list with descriptions
# in the OpenCVConfig.cmake file.
# Print some message showing some of them
# # message(status "opencv library status:")
# # message(status "    config: ${opencv_dir}")
# # message(status "    version: ${opencv_version}")
# # message(status "    libraries: ${opencv_libs}")
# # message(status "    include path: ${opencv_include_dirs}")

# Declare the executable target built from your sources
add_executable(opencv_homograph_demo virtual-billboard.cpp)

# Link your application with OpenCV libraries
target_link_libraries(opencv_homograph_demo PRIVATE ${OpenCV_LIBS})
