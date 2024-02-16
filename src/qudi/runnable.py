#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import subprocess
import sys
import os


def main():
    """ """
    myenv = os.environ.copy()

    # Set parent process PID as environment variable for qudi main process
    if sys.platform == "win32":
        try:
            from _winapi import DuplicateHandle, GetCurrentProcess
            from _winapi import DUPLICATE_SAME_ACCESS
        except ImportError:
            from _subprocess import DuplicateHandle, GetCurrentProcess
            from _subprocess import DUPLICATE_SAME_ACCESS
        pid = GetCurrentProcess()
        handle = DuplicateHandle(pid, pid, pid, 0, True, DUPLICATE_SAME_ACCESS)
        myenv["QUDI_PARENT_PID"] = str(int(handle))
    else:
        myenv["QUDI_PARENT_PID"] = str(os.getpid())

    argv = [sys.executable, "-m", "core"] + sys.argv[1:]
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    while True:
        process = subprocess.Popen(
            argv,
            close_fds=False,
            env=myenv,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            shell=False,
        )
        try:
            retval = process.wait()
            if retval == 0:
                break
            elif retval == 42:
                print("Restarting...")
                continue
            elif retval == 2:
                # invalid commandline argument
                break
            elif retval == -6:
                # called if QFatal occurs
                break
            elif retval == 4:
                print(
                    "Import Error: Qudi could not be started due to missing packages."
                )
                sys.exit(retval)
            else:
                print("Unexpected return value {0}. Exiting.".format(retval))
                sys.exit(retval)
        except KeyboardInterrupt:
            print("\nQudi terminated by keyboard interrupt event!")
            try:
                process.terminate()
                process.wait()
            except:
                pass
            sys.exit(0)
        except:
            process.kill()
            process.wait()
            raise


if __name__ == "__main__":
    main()
