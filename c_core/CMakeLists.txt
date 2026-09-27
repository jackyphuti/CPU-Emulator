cmake_minimum_required(VERSION 3.10)
project(CPU8_Emulator C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4 /O2)
else()
    add_compile_options(-Wall -Wextra -O3 -pedantic)
endif()

add_library(cpu8 SHARED cpu8.c cpu8.h)
add_library(cpu8_static STATIC cpu8.c cpu8.h)

add_executable(cpu8_cli main.c)
target_link_libraries(cpu8_cli PRIVATE cpu8_static)

add_executable(test_cpu8 test_cpu8.c)
target_link_libraries(test_cpu8 PRIVATE cpu8_static)

enable_testing()
add_test(NAME cpu8_unit_tests COMMAND test_cpu8)
