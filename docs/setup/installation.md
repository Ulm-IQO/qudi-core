---
layout: default
title: qudi-core
---

[back](../index.md)

---

# Installation

> **⚠ WARNING:**
> 
> In order to install qudi as a python package and application, we strongly recommend to create an 
> isolated virtual Python 3.8(!) environment. Qudi needs very specific package dependencies that 
> can otherwise mess up your system Python installation.
> 
> Another advantage of installing qudi in its own Python environment is, that you can easily 
> deinstall qudi and all dependencies again by simply deleting this environment.

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
install releases of qudi. If you are a developer and want to fiddle with the qudi-core source code 
of your installation, you might want to consider skipping ahead to 
[this alternative](#alternative-install-qudi-from-source).

With the active Python environment you can install the latest release of qudi like any other Python 
package from PyPI via:
```shell
> python -m pip install qudi
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
> Apart from installing the qudi package with all dependencies, the installation procedure will also 
register the qudi IPython kernel in your system (effectively calling `qudi-install-kernel`).
> 
> This has an effect on your entire system and not just the Python environment. 
> It will overwrite any other kernels with name "qudi" registered for that user.
> 
> In practice this should only pose a problem if you have multiple installations of qudi 
> (in different environments). In that case you should call `qudi-install-kernel` everytime you 
> switch qudi environments.


### Alternative: Install qudi from source
If you want to use the current development version of qudi and/or want to actively contribute to 
to the [qudi-core repository](https://github.com/Ulm-IQO/qudi-core), 

---

[back](../index.md)
