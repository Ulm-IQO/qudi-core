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

set gitpath=
set gitversion=

:find_git_on_path
setlocal EnableDelayedExpansion
set "output_cnt=0"
for /F "delims=" %%f in ('where git 2^> nul') do (
    set /a output_cnt+=1
    set "output[!output_cnt!]=%%f"
)
if [!output[1]!] neq [] set gitpath=!output[1]!
setlocal DisableDelayedExpansion

if defined gitpath goto get_gitversion

:find_git_in_registry
for /f "tokens=2*" %%A in ('reg Query "HKCU\SOFTWARE\GitForWindows" /v InstallPath 2^> nul') do set gitpath=%%B\bin\git.exe
if defined gitpath goto get_gitversion

for /f "tokens=2*" %%A in ('reg Query "HKLM\SOFTWARE\GitForWindows" /v InstallPath 2^> nul') do set gitpath=%%B\bin\git.exe
if defined gitpath goto get_gitversion

:find_git_in_other
set gitpath=%ProgramFiles%\Git\bin\git.exe
if exist "%gitpath%" goto get_gitversion

set gitpath=%ProgramFiles(x86)%\Git\bin\git.exe
if exist "%gitpath%" goto get_gitversion

set gitpath=%userprofile%\AppData\Local\Programs\Git\bin\git.exe
if exist "%gitpath%" goto get_gitversion

set gitpath=

:report_error
>&2 echo ERROR: Git for Windows not found on PATH, in registry or in default paths!
exit /b 2

:get_gitversion
for /f "tokens=3" %%A in ('"%gitpath%" --version') do set gitversion=%%A

if not defined gitversion goto report_error

echo %gitversion% %gitpath%
