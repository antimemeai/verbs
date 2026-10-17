from conan import ConanFile
from conan.tools.files import copy, get
import os


class VerbsConan(ConanFile):
    name = "verbs"
    version = "0.1.0"
    description = "Explicit, named constraints for more verifiable code"
    license = "MIT"
    homepage = "https://github.com/antimemeai/verbs"
    url = "https://github.com/antimemeai/verbs"
    topics = ("constraints", "validation", "contracts")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "packages", "cpp", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "verbs")
        self.cpp_info.set_property("cmake_target_name", "verbs::verbs")
