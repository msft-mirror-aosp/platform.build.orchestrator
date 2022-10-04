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
import json
import sys

import common


class InnerBuildSoong(common.Commands):
    def describe(self, args):
        with open(args.input_json, encoding='iso-8859-1') as f:
            query = json.load(f)

        # TODO: The tree should have an idea of what *can* be built, which we
        # would indicate here for early error detection.  For now, simply reply
        # with the build domains requested.  We will need to figure this out as
        # part of implementing the single-tree bazel-only optimization.
        domain_data = [dict(domains=[query.get("build_domains", [])])]
        reply = dict(version=0, domain_data=domain_data)

        filename = args.output_json or os.path.join(args.out_dir,
                                                    "tree_info.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding='iso-8859-1') as f:
            json.dump(reply, f, indent=4)

    def export_api_contributions(self, args):
        pass


def main(argv):
    return InnerBuildSoong().Run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
