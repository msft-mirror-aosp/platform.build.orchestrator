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

import json
import unittest
from unittest.mock import patch, mock_open

from find_api_packages import read, BazelLabel, ApiPackageFinder, \
        ApiPackageDecodeException, ContributionData
from finder import FileFinder


class TestBazelLabel(unittest.TestCase):
    def test_label_to_string(self):
        label = BazelLabel(package="//build/bazel", target="mytarget")
        self.assertEqual("//build/bazel:mytarget", label.to_string())
        label = BazelLabel(package="build/bazel",
                           target="target/in/another/dir/mytarget")
        self.assertEqual("build/bazel:target/in/another/dir/mytarget",
                         label.to_string())

    def test_colon_handling(self):
        label = BazelLabel(package="//build/bazel:", target=":mytarget.txt")
        self.assertEqual("//build/bazel:mytarget.txt", label.to_string())


class TestApiPackageReadUtils(unittest.TestCase):
    def test_read_empty_file(self):
        test_data = ""
        with patch("builtins.open", mock_open(read_data=test_data)):
            self.assertRaises(ApiPackageDecodeException, read,
                              "some_file.json")

    def test_read_malformed_file(self):
        test_data = "not a json file"
        with patch("builtins.open", mock_open(read_data=test_data)):
            self.assertRaises(ApiPackageDecodeException, read,
                              "some_file.json")

    def test_read_file_missing_api_domain(self):
        data = {"api_package": "//frameworks/base"}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            self.assertRaises(ApiPackageDecodeException, read,
                              "some_file.json")

    def test_read_file_missing_api_package(self):
        data = {"api_domain": "system"}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            self.assertRaises(ApiPackageDecodeException, read,
                              "some_file.json")

    def test_read_well_formed_json(self):
        data = {"api_domain": "system", "api_package": "//frameworks/base"}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            results = read("some_file.json")
            self.assertEqual("system", results.api_domain)
            self.assertEqual("//frameworks/base",
                             results.api_contribution_bazel_label.package)
            self.assertEqual("contributions",
                             results.api_contribution_bazel_label.target)

    def test_read_target_provided_by_user(self):
        data = {
            "api_domain": "system",
            "api_package": "//frameworks/base",
            "api_target": "mytarget"
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            results = read("some_file.json")
            self.assertEqual("system", results.api_domain)
            self.assertEqual("//frameworks/base",
                             results.api_contribution_bazel_label.package)
            self.assertEqual("mytarget",
                             results.api_contribution_bazel_label.target)


class TestApiPackageFinder(unittest.TestCase):
    @patch.object(FileFinder, "find")
    def test_exception_if_api_package_file_is_missing(self, find_mock):
        find_mock.return_value = []  # no files found
        api_package_finder = ApiPackageFinder("mock_inner_tree")
        self.assertEqual(None,
                         api_package_finder.find_api_label_string("system"))

    @patch("find_api_packages.read")
    @patch.object(FileFinder, "find")
    def test_exception_if_api_domain_not_found(self, find_mock, read_mock):
        # api_packages.json files exist in the tree, but none of them contain
        # the api_domain we are interested in.
        find_mock.return_value = ["somefile.json"]
        read_mock.return_value = ContributionData(
            "com.android.foo",
            BazelLabel("//packages/modules/foo", "contributions"))
        api_package_finder = ApiPackageFinder("mock_inner_tree")
        self.assertEqual(None,
                         api_package_finder.find_api_label_string("system"))
        self.assertEqual(
            "//packages/modules/foo:contributions",
            api_package_finder.find_api_label_string("com.android.foo"))

    @patch("find_api_packages.read")
    @patch.object(FileFinder, "find")
    def test_first_find_wins(self, find_mock, read_mock):
        find_mock.return_value = ["first.json", "second.json"]
        first_contribution_data = ContributionData(
            "com.android.foo",
            BazelLabel("//packages/modules/foo", "contributions"))
        second_contribution_data = ContributionData(
            "com.android.foo",
            BazelLabel("//packages/modules/foo_other", "contributions"))
        read_mock.side_effect = [
            first_contribution_data, second_contribution_data
        ]
        api_package_finder = ApiPackageFinder("mock_inner_tree")
        self.assertEqual(
            "//packages/modules/foo:contributions",
            api_package_finder.find_api_label_string("com.android.foo"))


if __name__ == "__main__":
    unittest.main()
