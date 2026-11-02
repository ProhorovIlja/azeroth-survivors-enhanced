cmake_minimum_required(VERSION 3.21)
project(azeroth_survivors_native_bootstrap LANGUAGES CXX)

if(NOT WIN32)
  message(FATAL_ERROR "This bootstrap is Windows-only and must not be used on other platforms")
endif()
if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "The original 0.139 game and native bootstrap require x64")
endif()

add_library(azse_native_bootstrap SHARED
  src/azse_native_bootstrap.cpp
  include/azse_native_bootstrap.h)
target_include_directories(azse_native_bootstrap PUBLIC include)
target_compile_features(azse_native_bootstrap PUBLIC cxx_std_17)
target_compile_definitions(azse_native_bootstrap PRIVATE AZSE_BUILDING_DLL)
target_link_libraries(azse_native_bootstrap PRIVATE bcrypt)

if(MSVC)
  target_compile_options(azse_native_bootstrap PRIVATE /W4 /WX)
endif()

enable_testing()
add_executable(azse_native_bootstrap_tests tests/native_bootstrap_tests.cpp)
target_link_libraries(azse_native_bootstrap_tests PRIVATE azse_native_bootstrap)
target_compile_features(azse_native_bootstrap_tests PRIVATE cxx_std_17)
if(MSVC)
  target_compile_options(azse_native_bootstrap_tests PRIVATE /W4 /WX)
endif()
add_test(NAME WindowsNativeBootstrapFailClosed
  COMMAND azse_native_bootstrap_tests)
