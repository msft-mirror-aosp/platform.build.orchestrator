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

import argparse
import json
import os


def _parser():
    """Return the argument parser"""
    # Top-level parser
    parser = argparse.ArgumentParser(prog=".inner_build")

    parser.add_argument(
        "--out_dir",
        action="store",
        required=True,
        help=
        "root of the output directory for this inner tree's API contributions")

    parser.add_argument(
        "--api_domain",
        action="append",
        required=True,
        help="which API domains are to be built in this inner tree")

    parser.add_argument(
        "--inner_tree",
        action="store",
        required=True,
        help="root of the inner tree that is building the API domain")

    subparsers = parser.add_subparsers(required=True,
                                       dest="command",
                                       help="subcommands")

    # inner_build describe command
    describe_parser = subparsers.add_parser(
        "describe",
        help="describe the capabilities of this inner tree's build system")
    describe_parser.add_argument('--input-json',
                                 '--input_json',
                                 required=True,
                                 help="The json encoded request information.")
    describe_parser.add_argument('--output-json',
                                 '--output_json',
                                 required=True,
                                 help="The json encoded description.")

    # create the parser for the "export_api_contributions" command.
    _export_parser = subparsers.add_parser(
        "export_api_contributions",
        help="export the API contributions of this inner tree")

    # create the parser for the "analyze" command.
    _analyze_parser = subparsers.add_parser(
        "analyze", help="main build analysis for this inner tree")

    return parser


class Commands(object):
    """Base class for inner_build commands."""

    valid_commands = ("describe", "export_api_contributions", "analyze")

    def Run(self, argv):
        """Parse command arguments and call the named subcommand.

        Throws AttributeError if the method for the command wasn't found.
        """
        args = _parser().parse_args(argv[1:])
        if args.command not in self.valid_commands:
            raise Exception(f"invalid command: {args.command}")
        return getattr(self, args.command)(args)

    def describe(self, args):
        """Perform the default 'describe' processing."""

        with open(args.input_json, encoding='iso-8859-1') as f:
            query = json.load(f)

        # This version of describe() simply replies with the build_domains
        # requested.  If the inner tree can't build the requested build_domain,
        # then the build will fail later.  If the inner tree has knowledge of
        # what can be built, it should override this method with a method that
        # returns the appropriate information.
        # TODO: bazel-only builds will need to figure this out.
        domain_data = [{"domains": [query.get("build_domains", [])]}]
        reply = {"version": 0, "domain_data": domain_data}

        filename = args.output_json or os.path.join(args.out_dir,
                                                    "tree_info.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding='iso-8859-1') as f:
            json.dump(reply, f, indent=4)

    def export_api_contributions(self, args):
        raise Exception(f"export_api_contributions({args}) not implemented")

    def analyze(self, args):
        raise Exception(f"analyze({args}) not implemented")
