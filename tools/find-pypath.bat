@echo off

REM Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
REM distribution and on <https://github.com/Ulm-IQO/qudi-core/>

REM This file is part of qudi.

REM Qudi is free software: you can redistribute it and/or modify it under the terms of
REM the GNU Lesser General Public License as published by the Free Software Foundation,
REM either version 3 of the License, or (at your option) any later version.

REM Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
REM without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
REM See the GNU Lesser General Public License for more details.

REM You should have received a copy of the GNU Lesser General Public License along with qudi.
REM If not, see <https://www.gnu.org/licenses/>.

set pypath=
set pyversion=

setlocal EnableDelayedExpansion
set "output_cnt=0"
for /F "delims=" %%f in ('where pythonn 2^> nul') do (
    set /a output_cnt+=1
    set "output[!output_cnt!]=%%f"
)
if [!output[1]!] neq [] set pypath=!output[1]!
setlocal DisableDelayedExpansion

if not defined pypath goto find_pypath_in_registry

for /f "tokens=2" %%A in ('"%pypath%" -V') do set pyversion=%%A
if defined pyversion (
  if /i "%pyversion:~0,4%"=="3.9." (
    goto report_pypath
  )
  if /i "%pyversion:~0,4%"=="3.8." (
    goto report_pypath
  )
)

set pypath=
set pyversion=

:find_pypath_in_registry
for /f "tokens=2*" %%A in ('reg Query "HKLM\SOFTWARE\Python\PythonCore\3.9\InstallPath" /v ExecutablePath 2^> nul') do set pypath=%%B
if defined pypath goto get_pyversion

for /f "tokens=2*" %%A in ('reg Query "HKCU\SOFTWARE\Python\PythonCore\3.9\InstallPath" /v ExecutablePath 2^> nul') do set pypath=%%B
if defined pypath goto get_pyversion

for /f "tokens=2*" %%A in ('reg Query "HKLM\SOFTWARE\Python\PythonCore\3.8\InstallPath" /v ExecutablePath 2^> nul') do set pypath=%%B
if defined pypath goto get_pyversion

for /f "tokens=2*" %%A in ('reg Query "HKCU\SOFTWARE\Python\PythonCore\3.8\InstallPath" /v ExecutablePath 2^> nul') do set pypath=%%B
if defined pypath goto get_pyversion

:report_error
>&2 echo ERROR: No suitable Python 3.8 or 3.9 interpreter found on PATH or in registry!
exit /b 2

:get_pyversion
for /f "tokens=2" %%A in ('"%pypath%" -V') do set pyversion=%%A
if not defined pyversion goto report_error

:report_pypath
echo %pyversion% %pypath%
