#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
from importlib import metadata

from bandit.core import config  # noqa
from bandit.core import context  # noqa
from bandit.core import manager  # noqa
from bandit.core import meta_ast  # noqa
from bandit.core import node_visitor  # noqa
from bandit.core import test_set  # noqa
from bandit.core import tester  # noqa
from bandit.core import utils  # noqa
from bandit.core.constants import *  # noqa
from bandit.core.issue import *  # noqa
from bandit.core.test_properties import *  # noqa

try:
    __version__ = metadata.version("bandit")
except metadata.PackageNotFoundError:
    # Sphinx has trouble with this call to get the version.
    __version__ = "0.0.0"
