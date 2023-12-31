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


def export_apis_from_tree(tree_key, inner_tree, cookie):
    """Call inner_build export_api_contributions."""
    cmd = ["export_api_contributions"]
    # Pass the abspath of the inner_tree.  The nsjail config will change
    # directory to this path at invocation.
    cmd.extend(["--inner_tree", os.path.join(os.getcwd(), inner_tree.root)])

    for domain_name in sorted(inner_tree.domains.keys()):
        cmd.append("--api_domain")
        cmd.append(domain_name)

    inner_tree.invoke(cmd)
