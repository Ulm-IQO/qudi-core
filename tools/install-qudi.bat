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

:find_pypath
set pypath=
set pyversion=
for /f "tokens=1*" %%A in ('call find-pypath.bat 2^> nul') do (
  set pyversion=%%A
  set pypath=%%B
)

:report_pypath
if not defined pypath (
  >&2 echo ERROR: No suitable Python interpreter found on PATH or in registry!
  goto err_exit
)
echo Found suitable Python %pyversion% interpreter "%pypath%"

:find_gitpath
set gitpath=
set gitversion=
for /f "tokens=1*" %%A in ('call find-gitpath.bat 2^> nul') do (
  set gitversion=%%A
  set gitpath=%%B
)

:report_gitpath
if not defined gitpath (
  >&2 echo ERROR: git.exe not found on PATH, in registry or default paths!
  goto err_exit
)
echo Found Git %gitversion% executable "%gitpath%"

:add_gitpath_to_path
for %%i in ("%gitpath%") do set gitpathdir=%%~di%%~pi
if defined gitpathdir set PATH=%PATH%;%gitpathdir%

:create_venv
echo Creating qudi virtual Python environment "qudi-venv"...
call "%pypath%" -m venv qudi-venv
if %errorlevel% neq 0 (
  >&2 echo ERROR: Unable to create Python virtual environment using venv!
  goto err_exit
)
echo DONE

:activate_venv
echo Activating 'qudi-venv' environment...
call .\qudi-venv\Scripts\activate
if %errorlevel% neq 0 (
  >&2 echo ERROR: Unable to activate 'qudi-venv' virtual Python environment!
  goto err_exit
)
echo DONE

:update_install_packages
echo Updating 'pip' and 'wheel' packages...
call python -m pip install --upgrade pip >nul
call python -m pip install --upgrade wheel >nul
echo DONE

:clone_qudi_core
echo Cloning 'qudi-core' repository...
call "%gitpath%" clone --branch qt-resources "https://github.com/Ulm-IQO/qudi-core.git" >nul
if %errorlevel% neq 0 (
  >&2 echo ERROR: Unable to clone 'qudi-core' repository!
  goto err_exit
)
echo DONE

:install_qudi_core
echo Installing 'qudi-core' package in editable mode...
call python -m pip install -e .\qudi-core\
echo DONE

:prompt_install_qudi_iqo_modules
%SystemRoot%\System32\choice.exe /C YN /N /M "Do you want to download and install 'qudi-iqo-modules' [Y/N]?"
if errorlevel 2 goto configure_qudi

:clone_qudi_iqo_modules
echo Cloning 'qudi-iqo-modules' repository...
call "%gitpath%" clone --branch qt-resources "https://github.com/Ulm-IQO/qudi-iqo-modules.git" >nul
if %errorlevel% neq 0 (
  >&2 echo ERROR: Unable to clone 'qudi-iqo-modules' repository!
  goto err_exit
)
echo DONE

:install_qudi_iqo_modules
echo Installing 'qudi-iqo-modules' package in editable mode...
call python -m pip install -e .\qudi-iqo-modules\
echo DONE

:configure_qudi
echo Configuring qudi installation...
call python ".\qudi-core\src\qudi\configure.py"
echo DONE

goto end

:err_exit
pause
exit /b 2

:end
echo.
echo   qudi installed successfully!
echo   You can run qudi by simply calling 'qudi'.
echo   If you install a qudi addon later manually, remember to run the 'configure.py' script in the qudi-core repository inside the qudi environment again.
echo.
pause

REM :install_git
REM %SystemRoot%\System32\choice.exe /C YN /N /M "Do you want to download and install a temporary portable version now [Y/N]?"
REM echo.
REM if errorlevel 2 goto:eof

REM call install-portable-git.bat
REM echo.
REM if errorlevel 0 (
REM   set removegit=1
REM   set gitpath=%~dp0PortableGit\bin\git.exe
REM )



REM set /P installgit=Git for Windows not found. Do you want to download and install now? (y/[N])
REM if /I "%installgit%" neq "y" goto:eof

REM for /r %%f in (Git*.exe) do (
REM     call set file="%%f"
REM )

REM if [%file%]==[] (
REM     @echo on
REM     @echo Error finding "Git*.exe" install executable. File may not exist or is not named with the "Git" prefix.
REM     exit /b 2
REM )

REM @echo on
REM @echo Installing git from %file%...
REM @echo off

REM %file%
REM if errorlevel 1 (
REM     @echo on
REM     if %errorLevel% == 1 ( echo Error opening %file%. File may be corrupt. )
REM     if %errorLevel% == 2 ( echo Error reading %file%. May require elevated privileges. Run as administrator. )
REM     exit /b %errorlevel%
REM )
