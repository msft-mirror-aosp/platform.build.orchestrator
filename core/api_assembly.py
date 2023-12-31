#!/usr/bin/python3
#
# Copyright (C) 2022 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import json
import os
import sys

from cc.api_assembly import CcApiAssemblyContext
from java.api_assembly import JavaApiAssemblyContext
from build_file_generator import BuildFileGenerator
import ninja_tools

ContributionData = collections.namedtuple("ContributionData",
                                          ("inner_tree", "json_data"))


def assemble_apis(context, inner_trees):
    # Find all of the contributions from the inner tree
    contribution_files_dict = inner_trees.for_each_tree(
        api_contribution_files_for_inner_tree)

    # Load and validate the contribution files
    # TODO: Check timestamps and skip unnecessary work
    contributions = []
    for tree_key, filenames in contribution_files_dict.items():
        for filename in filenames:
            json_data = load_contribution_file(context, filename)
            if not json_data:
                continue
            # TODO: Validate the configs, especially that the domains match what we asked for
            # from the lunch config.
            contributions.append(
                ContributionData(inner_trees.get(tree_key), json_data))

    # Group contributions by language and API surface
    stub_libraries = collate_contributions(contributions)

    # Initialize the build file writer
    build_file_generator = BuildFileGenerator()

    # Initialize the ninja file writer
    with open(context.out.api_ninja_file(), "w",
              encoding='iso-8859-1') as ninja_file:
        ninja = ninja_tools.Ninja(context, ninja_file)

        # Iterate through all of the stub libraries and generate rules to assemble them
        # and Android.bp/BUILD files to make those available to inner trees.
        # TODO: Parallelize? Skip unnecessary work?
        for stub_library in stub_libraries:
            # TODO (b/265962882): Export APIs of version < current.
            # API files of older versions (29,30,...) are currently not
            # available in out/api_surfaces.
            # This cause isssues during CC API import, since Soong
            # cannot resolve the dependency for rdeps that specify
            # `sdk_version:<num>`.
            # Create a short-term hack that unconditionally generates Soong
            # modules for all NDK libraries, starting from version=1.
            # This does not compromise on API correctness though, since the correct
            # version number will be passed to the ndkstubgen invocation.
            # TODO(b/266830850): Revisit stubs versioning for Module-lib API
            # surface.
            if stub_library.language == "cc_libraries" and stub_library.api_surface in ["publicapi", "module-libapi"]:
                versions = list(range(1,34)) # 34 is current
                versions.append("current")
                for version in versions:
                    stub_library.api_surface_version = str(version)
                    STUB_LANGUAGE_HANDLERS[stub_library.language](
                        context, ninja, build_file_generator, stub_library)
            else:
                STUB_LANGUAGE_HANDLERS[stub_library.language](context, ninja,
                                                          build_file_generator,
                                                          stub_library)

        # TODO: Handle host_executables separately or as a StubLibrary language?

        # Finish writing the ninja file
        ninja.write()

    build_file_generator.write()
    build_file_generator.clean(
        context.out.api_surfaces_dir())  # delete stale Android.bp files


def api_contribution_files_for_inner_tree(tree_key, inner_tree, cookie):
    "Scan an inner_tree's out dir for the api contribution files."
    directory = inner_tree.out.api_contributions_dir()
    result = []
    with os.scandir(directory) as it:
        for dirent in it:
            if not dirent.is_file():
                break
            if dirent.name.endswith(".json"):
                result.append(os.path.join(directory, dirent.name))
    return result


def load_contribution_file(context, filename):
    "Load and return the API contribution at filename. On error report error and return None."
    with open(filename, encoding='iso-8859-1') as f:
        try:
            return json.load(f)
        except json.decoder.JSONDecodeError as ex:
            # TODO: Error reporting
            context.errors.error(ex.msg, filename, ex.lineno, ex.colno)
            raise ex


class StubLibraryContribution(object):

    def __init__(self, inner_tree, api_domain, library_contribution):
        self.inner_tree = inner_tree
        self.api_domain = api_domain
        self.library_contribution = library_contribution


class StubLibrary(object):

    def __init__(self, language, api_surface, api_surface_version, name):
        self.language = language
        self.api_surface = api_surface
        self.api_surface_version = api_surface_version
        self.name = name
        self.contributions = []

    def add_contribution(self, contrib):
        self.contributions.append(contrib)


def collate_contributions(contributions):
    """Take the list of parsed API contribution files, and group targets by API Surface, version,
    language and library name, and return a StubLibrary object for each of those.
    """
    grouped = {}
    for contribution in contributions:
        for language in STUB_LANGUAGE_HANDLERS.keys():
            for library in contribution.json_data.get(language, []):
                key = (language, contribution.json_data["name"],
                       contribution.json_data["version"], library["name"])
                stub_library = grouped.get(key)
                if not stub_library:
                    stub_library = StubLibrary(
                        language, contribution.json_data["name"],
                        contribution.json_data["version"], library["name"])
                    grouped[key] = stub_library
                stub_library.add_contribution(
                    StubLibraryContribution(
                        contribution.inner_tree,
                        contribution.json_data["api_domain"], library))
    return list(grouped.values())


def assemble_resource_api_library(context, ninja, build_file, stub_library):
    print("assembling resource_api_library %s-%s %s from:" %
          (stub_library.api_surface, stub_library.api_surface_version,
           stub_library.name))
    for contrib in stub_library.contributions:
        print("  %s %s" %
              (contrib.api_domain, contrib.library_contribution["api"]))
    # TODO: Implement me


STUB_LANGUAGE_HANDLERS = {
    "cc_libraries": CcApiAssemblyContext().get_cc_api_assembler(),
    "java_libraries": JavaApiAssemblyContext().get_java_api_assembler(),
    "resource_libraries": assemble_resource_api_library,
}
