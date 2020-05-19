# -*- coding:utf-8 -*-
#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0

r"""
==================================================
B103: Test for setting permissive file permissions
==================================================

POSIX based operating systems utilize a permissions model to protect access to
parts of the file system. This model supports three roles "owner", "group"
and "world" each role may have a combination of "read", "write" or "execute"
flags sets. Python provides ``chmod`` to manipulate POSIX style permissions.

This plugin test looks for the use of ``chmod`` and will alert when it is used
to set particularly permissive control flags. A MEDIUM warning is generated if
a file is set to group executable and a HIGH warning is reported if a file is
set world writable. Warnings are given with HIGH confidence.

:Example:

.. code-block:: none

    >> Issue: Probable insecure usage of temp file/directory.
       Severity: Medium   Confidence: Medium
       Location: ./examples/os-chmod-py2.py:15
    14  os.chmod('/etc/hosts', 0o777)
    15  os.chmod('/tmp/oh_hai', 0x1ff)
    16  os.chmod('/etc/passwd', stat.S_IRWXU)

    >> Issue: Chmod setting a permissive mask 0777 on file (key_file).
       Severity: High   Confidence: High
       Location: ./examples/os-chmod-py2.py:17
    16  os.chmod('/etc/passwd', stat.S_IRWXU)
    17  os.chmod(key_file, 0o777)
    18

.. seealso::

 - https://security.openstack.org/guidelines/dg_apply-restrictive-file-permissions.html  # noqa
 - https://en.wikipedia.org/wiki/File_system_permissions
 - https://security.openstack.org

.. versionadded:: 0.9.0

"""

import stat

import bandit
from bandit.core.issue import Cwe as Cwe
from bandit.core import test_properties as test


@test.checks('Call')
@test.test_id('B103')
def set_bad_file_permissions(context):
    if 'chmod' in context.call_function_name:
        if context.call_args_count == 2:
            mode = context.get_call_arg_at_position(1)

            if (mode is not None and isinstance(mode, int) and
                    (mode & stat.S_IWOTH or mode & stat.S_IXGRP)):
                # world writable is an HIGH, group executable is a MEDIUM
                if mode & stat.S_IWOTH:
                    sev_level = bandit.HIGH
                else:
                    sev_level = bandit.MEDIUM

                filename = context.get_call_arg_at_position(0)
                if filename is None:
                    filename = 'NOT PARSED'
                return bandit.Issue(
                    severity=sev_level,
                    cwe=Cwe.INCORRECT_PERMISSION_ASSIGNMENT,
                    confidence=bandit.HIGH,
                    text="Chmod setting a permissive mask %s on file (%s)." %
                    (oct(mode), filename)
                )
