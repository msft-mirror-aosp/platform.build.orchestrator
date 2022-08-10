#!/usr/bin/env python3
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

"""Module that searches the tree for files named api_packages.json and returns the
Fully Qualified Bazel label of API domain contributions to API surfaces.
"""

from collections import namedtuple

import json
import os

from finder import FileFinder

# GLOBALS
# Filename to search for
API_PACKAGES_FILENAME = "api_packages.json"
# Default name of the api contribution Bazel target. Can be overridden by module authors in api_packages.json
DEFAULT_API_TARGET = "contributions"
# Directories inside inner_tree that will be searched for api_packages.json
# This pruning improves the speed of the API export process
INNER_TREE_SEARCH_DIRS = [
("frameworks", "base"),
("packages", "modules")]

class BazelLabel:
    """Class to represent a Fully qualified API contribution Bazel target
    https://docs.bazel.build/versions/main/skylark/lib/Label.html"""
    def __init__(self, package: str, target:str):
        self.package = package.rstrip(":")
        self.target = target.lstrip(":")

    def to_string(self):
        return self.package + ":" + self.target

class ApiPackageDecodeException(Exception):
    def __init__(self, filepath: str, msg: str):
        self.filepath = filepath
        msg = f"Found malformed api_packages.json file at {filepath}: " + msg
        super().__init__(msg)

ContributionData = namedtuple("ContributionData", ("api_domain", "api_contribution_bazel_label"))

def read(filepath: str) -> ContributionData:
    """Deserialize the contents of the json file at <filepath>
    Arguments:
        filepath
    Returns:
        ContributionData object
    """
    def _deserialize(filepath, json_contents) ->ContributionData:
        domain = json_contents.get("api_domain")
        package = json_contents.get("api_package")
        target = json_contents.get("api_target", "") or DEFAULT_API_TARGET
        if not domain:
            raise ApiPackageDecodeException(filepath, "api_domain is a required field in api_packages.json")
        if not package:
             raise ApiPackageDecodeException(filepath, "api_package is a required field in api_packages.json")
        return ContributionData(domain, BazelLabel(package=package,target=target))

    with open(filepath) as f:
        try:
            return json.load(f, object_hook=lambda json_contents: _deserialize(filepath,json_contents))
        except json.decoder.JSONDecodeError as ex:
            raise ApiPackageDecodeException(filepath, "") from ex

class ApiPackageFinder:
    """A class that searches the tree for files named api_packages.json and returns the fully qualified Bazel label of the API contributions of API domains

    Example api_packages.json
    ```
    {
        "api_domain": "system",
        "api_package": "//build/orchestrator/apis",
        "api_target": "system"
    }
    ```

    The search is restricted to $INNER_TREE_SEARCH_DIRS
    """
    def __init__(self,
            inner_tree_root: str,
            search_depth=6):
        self.inner_tree_root = inner_tree_root
        self.search_depth = search_depth
        self.finder = FileFinder(filename=API_PACKAGES_FILENAME,
                                 ignore_paths=[],
                                 )
        self._cache = dict()

    def _find_api_label(self, api_domain: str) -> BazelLabel:
        if api_domain in self._cache:
            return self._cache.get(api_domain)

        search_paths = [os.path.join(self.inner_tree_root, *search_dir) for search_dir in INNER_TREE_SEARCH_DIRS]
        for search_path in search_paths:
            for packages_file in self.finder.find(path=search_path, search_depth=self.search_depth):
                # Read values and add them to cache
                results = read(packages_file)
                self._cache[results.api_domain] = results.api_contribution_bazel_label
                # If an entry is found, stop searching
                if api_domain in self._cache:
                    return self._cache.get(api_domain)

        # Do not raise exception if a contribution target could not be found for an api domain
        # e.g. vendor might not have any api contributions
        return None

    def find_api_label_string(self, api_domain: str) -> str:
        """ Return the fully qualified bazel label of the contribution target

        Parameters:
            api_domain: Name of the API domain, e.g. system

        Raises:
            ApiPackageDecodeException: If a malformed api_packages.json is found during search

        Returns:
            Bazel label, e.g. //frameworks/base:contribution
            None if a contribution could not be found
        """
        label = self._find_api_label(api_domain)
        return label.to_string() if label else None

    def find_api_package(self, api_domain_name: str) -> str:
        """ Return the Bazel package of the contribution target

        Parameters:
            api_domain: Name of the API domain, e.g. system

        Raises:
            ApiPackageDecodeException: If a malformed api_packages.json is found during search

        Returns:
            Bazel label, e.g. //frameworks/base
            None if a contribution could not be found
        """
        label = self._find_api_label(api_domain)
        return label.package if label else None
