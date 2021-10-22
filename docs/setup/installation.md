---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Installation

> **⚠ WARNING:**
> 
> In order to install qudi as a python package and application, we strongly recommend to create an 
> isolated virtual Python 3.8(!) environment. Qudi needs very specific package dependencies that 
> can otherwise mess up your system Python installation.
> 
> Another advantage of installing qudi in its own Python environment is, that you can easily 
> deinstall qudi and all dependencies again by simply deleting this environment directory.

### 1. Create a project directory 
Create a new directory for qudi and the Python virtual environment to reside in. We will relate to 
this directory path in the next steps as `<project_dir>`.

### 2. Create a virtual Python environment 
Create a virtual Python 3.8 environment in the project directory you just created. You can choose an arbitrary 
environment name. We are using `qudi-venv` in this example.\
Depending on your OS and the type of Python distribution you use, this step can differ.

We will assume here that you use the builtin `venv` package to create the virtual environment and 
have the command `python` point to a Python 3.8 interpreter (you can check with `python -V`):
```shell
> cd <project_dir>
> python -m venv qudi-venv
```
This should have created a subfolder named `qudi-venv`.

> **⚠ WARNING:**
> 
> It is imperative that the Python interpreter of the created environment is running Python 3.8.\
> You can check the version of the interpreter with:
> ```shell
> > python -V
> Python 3.8.x
> ```
> Any older Python version is not supported and some packages qudi depends on can not cope with 
> Python >= 3.9 yet.

### 3. Activate the new Python environment
Anything related to qudi and its package dependencies must be done in the new Python environment.
Make sure to activate the environment in your command line before starting or (de-)installing any 
Python packages that should be used by or alongside qudi.

If you were following the example above using `venv` to create the environment, you can activate it 
with:
```shell
> cd qudi-venv
> cd Scripts
> activate
```

### 4. Install qudi from PyPI
Installing from the Python Package Index (PyPI) is certainly the most user-friendly way to 
install releases of qudi. If you are a developer and want to fiddle with the `qudi-core` source code 
of your installation, you might want to consider skipping ahead to 
[installing qudi from source](#alternative-install-qudi-from-source).

> **⚠ WARNING:**
> 
> `qudi-core` contains only the qudi framework and a bare minimum running application with the main 
> GUI and the task runner without any 
> [measurement modules](../design_concepts/measurement_modules.md).
> 
> Measurement module libraries can be easily installed after `qudi-core` as namespace packages.
> So for most users it makes sense to NOT install `qudi-core` from source but from the PyPI and 
> just install the measurement modules in development mode. 

With the active Python environment you can install the latest release of qudi like any other Python 
package from PyPI via:
```shell
> python -m pip install qudi-core
```

Installing qudi via `pip` will automatically install all other dependencies as well as register 
several entry points that are executables within the Python environment:

| command                 | effect                                                        |
| ----------------------- | ------------------------------------------------------------- |
| `qudi`                  | Starts qudi                                                   |
| `qudi-config-editor`    | Starts a standalone graphical configuration editor for qudi   |
| `qudi-install-kernel`   | Installs and registers the qudi IPython kernel in your system |
| `qudi-uninstall-kernel` | Uninstalls the qudi IPython kernel from your system           |

> **⚠ WARNING:**
> 
> Installing qudi via pip will NOT automatically register the qudi IPython kernel in the system.
> You will lack the interactive Ipython console in the qudi main GUI as well as any jupyter notebook
> support.
> 
> While you can use qudi without this Ipython integration, we strongly recommend to call 
> `qudi-install-kernel` after installing qudi via pip.
> 
> This has an effect on your entire system and not just the Python environment. 
> It will overwrite any other kernels with name "qudi" registered for that user.
> In practice this should only pose a problem if you have multiple installations of qudi 
> (in different environments). In that case you should call `qudi-install-kernel` everytime you 
> switch qudi environments.
> 
> We are currently working on a full deployment of qudi including configuration of the installed 
> application and not just a plain Python package installation to get around this minor 
> inconvenience and some other usability issues.


### Alternative: Install qudi from source
If you want to use the most recent development version of qudi and/or want to actively contribute to 
to the [qudi-core repository](https://github.com/Ulm-IQO/qudi-core), you need to install the 
`qudi-core` repository directly from GitHub:

```shell
> python -m pip install -e git+https://github.com/Ulm-IQO/qudi-core@main#egg=qudi-core
```

The `qudi-core` repository will then be cloned into a source folder 
(default: `<python_environment>/src/`) and you can productively alter code while maintaining proper 
Python package resolution.


### 5. Install measurement module libraries
Unless you have a robust deployment of measurement modules at hand that do not need to be altered 
too often, you may want to install any measurement module namespace packages from source.

If your measurement module package deployment is following the 
[qudi project suggestions](../404.md), you can install them exactly like described in the previous 
section. You just need to exchange the url/name of the respective package repository.

If you are into quantum optics measurements with colorcenters in diamond or similar semiconductors, 
you may want to consider using the measurement modules package `qudi-iqo-modules` provided by the 
Institute for Quantum Optics ([Ulm-IQO](https://github.com/Ulm-IQO/)) under the LGPL v3 license.  
You can install this package from source in development mode with:
```shell
> python -m pip install -e git+https://github.com/Ulm-IQO/qudi-iqo-modules@main#egg=qudi-iqo-modules
```
or alternatively the latest non-editable release from the PyPI:
```shell
> python -m pip install qudi-iqo-modules
```

---

[index](../index.md)
