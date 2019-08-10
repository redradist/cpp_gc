cmake_minimum_required(VERSION 3.13)
set(CMAKE_C_COMPILER clang-9)
set(CMAKE_CXX_COMPILER clang++-9)
project(NoMoreGarbadgeCollector)

set(CMAKE_CXX_STANDARD 17)

include_directories(..)

include(${CMAKE_CURRENT_LIST_DIR}/../scripts/gc_ptr_config.cmake)

#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fsanitize=address -fsanitize-address-use-after-scope -fsanitize=leak")

add_executable(NoMoreGarbadgeCollector main.cpp)
target_link_libraries(NoMoreGarbadgeCollector pthread c++)
use_gc_ptr(NoMoreGarbadgeCollector)