vcpkg_download_distfile(ARCHIVE
    URLS "https://codeload.github.com/antimemeai/verbs/tar.gz/refs/tags/v0.1.0"
    FILENAME "verbs-0.1.0.tar.gz"
    SHA512 387ddf0bbb82503fb8202fde8b30edd4dc1e64fe479e3d12eed8ceefbb3761d726c1b0ef8790cc6ce69b87532e319677a78d87c073bde46c0088299c1855479c)
vcpkg_extract_source_archive(SOURCE_PATH ARCHIVE "${ARCHIVE}")
vcpkg_cmake_configure(SOURCE_PATH "${SOURCE_PATH}/packages/cpp")
vcpkg_cmake_install()
vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/verbs)
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug" "${CURRENT_PACKAGES_DIR}/lib")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
