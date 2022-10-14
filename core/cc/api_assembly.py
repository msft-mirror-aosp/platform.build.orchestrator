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

import json
import os
import textwrap
from cc.stub_generator import StubGenerator, GenCcStubsInput

ARCHES = ["arm", "arm64", "x86", "x86_64"]

ASSEMBLE_PHONY_TARGET = "multitree-sdk"

class CcApiAssemblyContext(object):
    """Context object for managing global state of CC API Assembly."""
    def __init__(self):
        self._stub_generator = StubGenerator()
        self._api_levels_file_added = False

    def get_cc_api_assembler(self):
        """Return a callback to assemble CC APIs.

        The callback is a member of the context object,
        and therefore has access to its state."""
        return self.assemble_cc_api_library

    def assemble_cc_api_library(self, context, ninja, build_file, stub_library):
        staging_dir = context.out.api_library_dir(stub_library.api_surface,
                stub_library.api_surface_version, stub_library.name)
        work_dir = context.out.api_library_work_dir(stub_library.api_surface,
                stub_library.api_surface_version, stub_library.name)

        # Generate rules to copy headers.
        api_deps = []
        for contrib in stub_library.contributions:
            for headers in contrib.library_contribution["headers"]:
                # Each header module gets its own include dir.
                # TODO: Improve the readability of the generated out/ directory.
                include_dir = os.path.join(staging_dir, headers["name"])
                root = headers["root"]
                for file in headers["headers"]:
                    # TODO: Deal with collisions of the same name from multiple
                    # contributions.
                    # Remove the root from the full filepath.
                    # e.g. bionic/libc/include/stdio.h --> stdio.h
                    relpath = os.path.relpath(file, root)
                    include = os.path.join(include_dir, relpath)
                    ninja.add_copy_file(include, os.path.join(contrib.inner_tree.root, file))
                    api_deps.append(include)

            api = contrib.library_contribution["api"]
            api_out = os.path.join(staging_dir, os.path.basename(api))
            ninja.add_copy_file(api_out, os.path.join(contrib.inner_tree.root, api))
            api_deps.append(api_out)

            # Generate rules to run ndkstubgen.
            extra_args = self._additional_ndkstubgen_args(stub_library.api_surface)
            for arch in ARCHES:
                inputs = GenCcStubsInput(
                        arch = arch,
                        version = stub_library.api_surface_version,
                        version_map = self._api_levels_file(context),
                        api = api_out,
                        additional_args = extra_args,
                )
                # Generate stub.c files for each arch.
                # TODO: Compile .so files using stub.c files.
                stub_outputs = self._stub_generator.add_stubgen_action(ninja, inputs, work_dir)

            # TODO: Generate Android.bp files.

        # Generate rules to build the API levels map.
        if not self._api_levels_file_added:
            self._add_api_levels_file(context, ninja)
            self._api_levels_file_added = True


        # Generate phony rule to build the library.
        # TODO: This name probably conflictgs with something.
        phony = "-".join([stub_library.api_surface, str(stub_library.api_surface_version),
                          stub_library.name])
        ninja.add_phony(phony, api_deps)
        # Add a global phony to assemnble all apis
        ninja.add_global_phony(ASSEMBLE_PHONY_TARGET, [phony])

    def _additional_ndkstubgen_args(self, api_surface: str) -> str:
        if api_surface == "vendorapi":
            return "--llndk"
        if api_surface == "systemapi":
            # The "systemapi" surface has contributions from the following:
            # 1. Apex, which are annotated as #apex in map.txt
            # 2. Platform, which are annotated as #sytemapi in map.txt
            #
            # Run ndkstubgen with both these annotations.
            return "--apex --systemapi"
        return ""

    def _add_api_levels_file(self, context, ninja):
        # ndkstubgen uses a map for converting Android version codes to a
        # numeric code. e.g. "R" --> 30
        # The map contains active_codenames as well, which get mapped to a preview level
        # (9000+).
        # TODO: Keep this in sync with build/soong/android/api_levels.go.
        active_codenames = ["UpsideDownCake"]
        preview_api_level_base = 9000
        api_levels = {
            "G": 9,
            "I": 14,
            "J": 16,
            "J-MR1": 17,
            "J-MR2": 18,
            "K":     19,
            "L":     21,
            "L-MR1": 22,
            "M":     23,
            "N":     24,
            "N-MR1": 25,
            "O":     26,
            "O-MR1": 27,
            "P":     28,
            "Q":     29,
            "R":     30,
            "S":     31,
            "S-V2":  32,
            "Tiramisu": 33,
        }
        for index, codename in enumerate(active_codenames):
            api_levels[codename] = preview_api_level_base + index

        file = self._api_levels_file(context)
        ninja.add_write_file(file, json.dumps(api_levels))

    def _api_levels_file(self, context) -> str:
        """Returns a path in to generated api_levels map in the intermediates directory.

        This file is not specific to a single stub library, and can be generated once"""
        return context.out.api_surfaces_work_dir("api_levels.json")
