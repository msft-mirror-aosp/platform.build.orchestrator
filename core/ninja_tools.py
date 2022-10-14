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
import sys

# Workaround for python include path
# pylint: disable=wrong-import-position,import-error
_ninja_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "ninja"))
if _ninja_dir not in sys.path:
    sys.path.append(_ninja_dir)
import ninja_writer
from ninja_syntax import Variable, BuildAction, Rule, Pool, Subninja, Line
# pylint: enable=wrong-import-position,import-error


class Ninja(ninja_writer.Writer):
    """Some higher level constructs on top of raw ninja writing.

    TODO: Not sure where these should be.
    """

    def __init__(self, context, file, **kwargs):
        super().__init__(file, builddir=context.out.root(base=context.out.Base.OUTER), **kwargs)
        self._context = context
        self._did_copy_file = False
        self._write_rule = None
        self._phonies = {}

    def add_copy_file(self, copy_to, copy_from):
        if not self._did_copy_file:
            self._did_copy_file = True
            rule = Rule("copy_file")
            rule.add_variable("command", "mkdir -p ${out_dir} && " + self._context.tools.acp()
                    + " -f ${in} ${out}")
            self.add_rule(rule)
        build_action = BuildAction(output=copy_to, rule="copy_file", inputs=[copy_from,],
                implicits=[self._context.tools.acp()])
        build_action.add_variable("out_dir", os.path.dirname(copy_to))
        self.add_build_action(build_action)

    def add_global_phony(self, name, deps):
        """Add a global phony target.

        This should be used when there are multiple places that will want to add
        to the same phony. If you can, to save memory, use add_phony instead of
        this function.
        """
        if type(deps) not in (list, tuple):
            raise Exception(f"Assertion failed: bad type of deps: {type(deps)}")
        self._phonies.setdefault(name, []).extend(deps)

    def write(self):
        for phony, deps in self._phonies.items():
            self.add_phony(phony, deps)
        super().write()

    def add_write_file(self, filepath:str , content:str):
        """Writes the content as a string to filepath
        The content is written as-is, special characters are not escaped
        """
        if not self._write_rule:
            rule = Rule("write_file")
            rule.add_variable("description", "Writes content to out")
            rule.add_variable("command", "printf '${content}' > ${out}")
            self.add_rule(rule)
            self._write_rule = rule

        build_action = BuildAction(output=filepath, rule="write_file")
        build_action.add_variable("content", content)
        self.add_build_action(build_action)
