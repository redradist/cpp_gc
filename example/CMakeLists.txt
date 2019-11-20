cmake_minimum_required(VERSION 3.13)
set(CMAKE_CXX_COMPILER ${CMAKE_CURRENT_LIST_DIR}/../scripts/clang_extras.py)
project(NoMoreGarbadgeCollector)

set(CMAKE_CXX_STANDARD 17)

include_directories(.)
include_directories(..)

#NOTE(redra): This flags set for testing purposes
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=address -fsanitize-address-use-after-scope -fsanitize=leak")

add_executable(NoMoreGarbadgeCollector main.cpp some_lib.hpp)
target_link_libraries(NoMoreGarbadgeCollector pthread c++)
