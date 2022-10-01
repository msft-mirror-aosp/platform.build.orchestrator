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

import enum
import os
import platform

class Context(object):
    """Mockable container for global state."""
    def __init__(self, out_root, errors):
        self.out = OutDir(out_root)
        self.errors = errors
        self.tools = HostTools()

class TestContext(Context):
    "Context for testing. The real Context is manually constructed in orchestrator.py."

    def __init__(self, test_work_dir, test_name):
        super(TestContext, self).__init__(os.path.join(test_work_dir, test_name),
                Errors(None))


@enum.unique
class OutDirBase(enum.Enum):
    """The basepath to use for output paths.

    ORIGIN: Path is relative to ${OUT_DIR}. Use this when the path will be
            consumed while not nsjailed. (default)
    OUTER:  Path is relative to the outer tree root.  Use this when the path
            will be consumed while nsjailed in the outer tree.
    """
    DEFAULT = 0
    ORIGIN = 1
    OUTER = 2


class OutDir(object):
    """Encapsulates the logic about the out directory at the outer-tree level.
    See also inner_tree.OutDirLayout for inner tree out dir contents."""

    # For ease of use.
    Base = OutDirBase

    def __init__(self, out_origin, out_path="out"):
        """Initialize with the root of the OUT_DIR for the inner tree.

        Args:
          out_origin: The OUT_DIR path to use.  Usually "out".
          out_path: Where the outer tree out_dir will be mapped, relative to the
                    outer tree root. Usually "out".
        """
        self._intermediates = "intermediates"
        self._base = {}
        self._base[self.Base.ORIGIN] = out_origin
        self._base[self.Base.OUTER] = out_path
        self._base[self.Base.DEFAULT] = self._base[self.Base.ORIGIN]

    def _generate_path(self, relpath, *args,
                       base: OutDirBase = OutDirBase.DEFAULT,
                       abspath=False):
        """Return the path to the file.

        Args:
          relpath: The inner tree out_dir relative path to use.
          base: Which base path to use.
          abspath: return the absolute path.
        """
        ret = os.path.join(self._base[base], relpath, *args)
        if abspath:
            ret = os.path.abspath(ret)
        return ret

    def root(self, **kwargs):
        """The provided out_dir, mapped into "out/" for ninja."""
        return self._generate_path("", **kwargs)

    def inner_tree_dir(self, tree_root, product, **kwargs):
        """True root directory for inner tree inside the out dir."""
        product = product or "unbundled"
        out_root = f'{tree_root}_{product}'
        return self._generate_path("trees", out_root, **kwargs)

    def api_ninja_file(self, **kwargs):
        """The ninja file that assembles API surfaces."""
        return self._generate_path("api_surfaces.ninja", **kwargs)

    def api_library_dir(self, surface, version, library, **kwargs):
        """Directory for all the contents of a library inside an API surface, including
        the build files.  Any intermediates should go in api_library_work_dir."""
        return self._generate_path("api_surfaces", surface, str(version), library, **kwargs)

    def api_library_work_dir(self, surface, version, library, **kwargs):
        """Intermediates / scratch directory for library inside an API surface."""
        return self._generate_path(self._intermediates, "api_surfaces",
                                   surface, str(version), library, **kwargs)

    def outer_ninja_file(self, **kwargs):
        return self._generate_path("multitree.ninja", **kwargs)

    def module_share_dir(self, module_type, module_name, **kwargs):
        return self._generate_path("shared", module_type, module_name, **kwargs)

    def staging_dir(self, **kwargs):
        return self._generate_path("staging", **kwargs)

    def dist_dir(self, **kwargs):
        "The DIST_DIR provided or out/dist" # TODO: Look at DIST_DIR
        return self._generate_path("dist", **kwargs)

    def nsjail_config_file(self, **kwargs):
        "The nsjail config file used for the ninja run."
        return self._generate_path("nsjail.cfg", **kwargs)

class Errors(object):
    """Class for reporting and tracking errors."""
    def __init__(self, stream):
        """Initialize Error reporter with a file-like object."""
        self._stream = stream
        self._all = []

    def error(self, message, file=None, line=None, col=None):
        """Record the error message."""
        s = ""
        if file:
            s += str(file)
            s += ":"
        if line:
            s += str(line)
            s += ":"
        if col:
            s += str(col)
            s += ":"
        if s:
            s += " "
        s += str(message)
        if s[-1] != "\n":
            s += "\n"
        self._all.append(s)
        if self._stream:
            self._stream.write(s)

    def had_error(self):
        """Return if there were any errors reported."""
        return len(self._all)

    def get_errors(self):
        """Get all errors that were reported."""
        return self._all


class HostTools(object):
    def __init__(self):
        if platform.system() == "Linux":
            self._arch = "linux-x86"
        else:
            raise Exception("Orchestrator running on an unknown system: %s" % platform.system())

        # Some of these are called a lot, so pre-compute the strings to save memory
        self._prebuilts = os.path.join("orchestrator", "prebuilts", "build-tools", self._arch, "bin")
        self._acp = os.path.join(self._prebuilts, "acp")
        self._ninja = os.path.join(self._prebuilts, "ninja")
        self._nsjail = os.path.join(self._prebuilts, "nsjail")

    # TODO: @property
    def acp(self):
        return self._acp

    # TODO: @property
    def ninja(self):
        return self._ninja

    @property
    def nsjail(self):
        return self._nsjail


def choose_out_dir():
    """Get the root of the out dir, either from the environment or by picking
    a default."""
    result = os.environ.get("OUT_DIR")
    if result:
        return result
    else:
        return "out"
