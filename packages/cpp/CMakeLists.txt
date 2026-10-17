cmake_minimum_required(VERSION 3.15)
project(verbs VERSION 0.1.0 LANGUAGES CXX)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

add_library(verbs INTERFACE)
add_library(verbs::verbs ALIAS verbs)
target_compile_features(verbs INTERFACE cxx_std_17)
target_include_directories(verbs INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

install(TARGETS verbs EXPORT verbsTargets)
install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES ../../LICENSE DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/verbs)
install(EXPORT verbsTargets NAMESPACE verbs::
    FILE verbsConfig.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/verbs)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/verbsConfigVersion.cmake"
    VERSION ${PROJECT_VERSION} COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/verbsConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/verbs)

option(VERBS_BUILD_TESTS "Build constraint contract tests" OFF)
if(VERBS_BUILD_TESTS)
    enable_testing()
    add_executable(verbs_check tests/check.cpp)
    target_link_libraries(verbs_check PRIVATE verbs::verbs)
    add_test(NAME verbs_check COMMAND verbs_check)
endif()
