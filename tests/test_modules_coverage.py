# -*- coding: utf-8 -*-

"""
This file contains unit tests for all qudi fit routines for exponential decay models.

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

import coverage
import os
import time

    
def test_coverage_individual(qt_app, module_manager, config):
        for base in ['gui', 'logic', 'hardware']:
            for module_name, module_cfg in list(config[base].items()):
                module_manager.add_module(module_name, base, module_cfg, allow_overwrite=False, emit_change=True )
        gui_base = 'gui'
        for module_name, _ in list(config[gui_base].items()):
            #print(module_name)
            cov = coverage.Coverage()
            cov.start()
            
        
            module_manager.activate_module(module_name)
            cov.stop()
            assert module_manager.modules[module_name].is_active
            # Create a unique directory for each test function
            test_dir =  os.path.join('coverage',f"coverage_{module_name} qudi iqo")
            os.makedirs(test_dir, exist_ok=True)
            
            # Save the coverage report
            cov.html_report(directory=test_dir)
            cov.annotate(directory=test_dir)

            cov.save()

            #print(f"Coverage report saved to {test_dir}")
            #module_manager.deactivate_module(module_name)



