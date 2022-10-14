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

import sys
from typing import List

import common
from inner_build_soong import InnerBuildSoong


class InnerBuildCfVendor(InnerBuildSoong):
    """Class to override functions for cf_vendor branch."""

    # TODO: Once there are no overrides here, this file should be removed.

    def analyze(self, args: List):
        """Analyze the tree."""
        # TODO: Once we are publishing a lightweight API surfaces tree, we
        # should not need to set the environment variables.
        with common.setenv(ALLOW_MISSING_DEPENDENCIES="true",
                           SKIP_VNDK_VARIANTS_CHECK="true"):
            super().analyze(args)


def main(argv: List):
    return InnerBuildCfVendor().Run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))