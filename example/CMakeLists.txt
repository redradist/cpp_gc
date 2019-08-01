cmake_minimum_required(VERSION 3.13)
project(NoMoreGarbadgeCollector)

set(CMAKE_CXX_STANDARD 17)

include_directories(..)

add_executable(NoMoreGarbadgeCollector main.cpp)
target_link_libraries(NoMoreGarbadgeCollector pthread)