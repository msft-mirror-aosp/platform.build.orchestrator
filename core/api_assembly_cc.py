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

import os
import textwrap

ASSEMBLE_PHONY_TARGET = "multitree-sdk"

def assemble_cc_api_library(context, ninja, build_file, stub_library):
    staging_dir = context.out.api_library_dir(stub_library.api_surface,
            stub_library.api_surface_version, stub_library.name, base=context.out.Base.OUTER)
    work_dir = context.out.api_library_work_dir(stub_library.api_surface,
            stub_library.api_surface_version, stub_library.name, base=context.out.Base.OUTER)

    # Generate rules to copy headers
    api_deps = []
    for contrib in stub_library.contributions:
        for headers in contrib.library_contribution["headers"]:
            # Each header module gets its own include dir
            # TODO: Improve the readability of the generated out/ directory
            include_dir = os.path.join(staging_dir, headers["name"])
            root = headers["root"]
            for file in headers["headers"]:
                # TODO: Deal with collisions of the same name from multiple contributions
                # Remove the root from the full filepath
                # e.g. bionic/libc/include/stdio.h --> stdio.h
                relpath = os.path.relpath(file, root)
                include = os.path.join(include_dir, relpath)
                ninja.add_copy_file(include, os.path.join(contrib.inner_tree.root, file))
                api_deps.append(include)

        api = contrib.library_contribution["api"]
        api_out = os.path.join(staging_dir, os.path.basename(api))
        ninja.add_copy_file(api_out, os.path.join(contrib.inner_tree.root, api))
        api_deps.append(api_out)

        # TODO: Generate Android.bp files

    # Generate phony rule to build the library
    # TODO: This name probably conflictgs with something
    phony = "-".join([stub_library.api_surface, str(stub_library.api_surface_version),
                      stub_library.name])
    ninja.add_phony(phony, api_deps)
    # Add a global phony to assemnble all apis
    ninja.add_global_phony(ASSEMBLE_PHONY_TARGET, [phony])
