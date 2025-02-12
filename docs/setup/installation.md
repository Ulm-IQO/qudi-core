---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Installation

## Step 1: Create a Python 3.10 (or 3.9, or 3.8) environment 
The following documentation will only describe the installation for Python 3.10 but you can simply 
switch any mention of "3.10" with "3.9" or "3.8". 

In order to install qudi as a python package and application, we strongly recommend creating an 
isolated Python 3.10 environment. Qudi needs very specific package dependencies that can 
otherwise mess up your system Python installation.
 
Another advantage of installing qudi in its own Python environment is, that you can easily 
uninstall qudi and all dependencies again by simply deleting this environment.

You can choose any environment name you like. For this guide we will choose `qudi-env` as the 
environment name.

> **⚠ WARNING:**
> 
> There are many ways to create a Python environment depending on your OS, Python distribution and 
> personal taste. There is no "standard way" of setting this up and you can find tons of tutorials 
> and documentation out there on how to do this.
> 
> Outlined below are just two very common ways, using either the Python standard library 
> (recommended) __OR__ Miniconda/Anaconda.

### Variant 1: Python standard library
> **⚠ WARNING:**
> 
> Do not use this method if you are running an Anaconda/Miniconda distribution!  
> See [variant 2](#variant-2-anacondaminiconda) in that case.

Using the builtin `venv` module from the Python standard library we can create a Python environment 
in the current directory.  
The entire environment will be placed in a sub-folder with the corresponding name and can be 
tracelessly uninstalled by simply deleting this folder again.

While this is to our knowledge the most robust and preferred way of setting up a Python environment 
for qudi, it has a small disadvantage.
You can not change the Python version for the environment, meaning you can only set up an 
environment with the same Python version you created the environment with.  
So make sure the Python interpreter you use for calling the following commands has version `3.10.x`.
If you are missing Python 3.10 on your system, you can download and install the right version from 
[https://www.python.org/](https://www.python.org/).

You can find OS specific commands to create the environment below.  
If your Python 3.10 interpreter is not found on your `PATH` (e.g. if you have multiple versions of 
Python installed), you need to replace all `python`/`python3` calls with the full path to the 
correct interpreter. On Windows you may also use the `py` launcher instead.

<details>
  <summary> <b>Windows</b> users click here to expand</summary>

  Check first if you are using Python version 3.10:

  ```console
  C:\> python -V
  Python 3.10.11
  ```

  Change to a desired working directory to create the environment in (here: `C:\Software\qudi\`):

  ```console
  C:\Software\qudi> python -m venv qudi-env
  ```

  You should now see a new folder `qudi-env` in your current working directory.

  ---

</details>


<details>
  <summary> <b>Unix</b> users click here to expand</summary>

  Check first if you are using Python version 3.10:

  ```bash
  foo@bar:~$ python3 -V
  Python 3.10.11
  ```

  Change to a desired working directory to create the environment in (here: `/opt/qudi`):
  
  ```bash
  foo@bar:/opt/qudi$ python3 -m venv qudi-env
  ```

  You should now see a new folder `qudi-env` in your current working directory.

  ---

</details>

### Variant 2: Anaconda/Miniconda
> **⚠ WARNING:**
> 
> While Anaconda and Miniconda are very popular Python distributions in the scientific community, 
> we encountered occasional instabilities with binary package distributions like `PySide2` 
> in conjunction with `conda` environments.  
> We have not been able to narrow down the source of these problems so far.
> 
> Most of the time, qudi runs without any issues but should you encounter crashes or error messages 
> coming from C++ extensions during startup, consider installing a "plain" Python distribution 
> instead and install a Python environment according to 
> [variant 1](#variant-1-python-standard-library).

If you are using Anaconda or Miniconda Python distributions, this is probably the way to go for you.
This method uses `conda` to create the Python 3.10 environment.

If you have not installed a distribution yet, you should install the latest version of [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html#latest-miniconda-installer-links) first.

You can find OS specific commands to create the environment below.

<details>
  <summary> <b>Windows</b> users click here to expand</summary>

  You can execute these commands from any working directory since the environment will be created 
  in an Anaconda/Miniconda specific default directory.

  ```console
  C:\> conda create --name qudi-env python=3.10
  ```

  ---

</details>


<details>
  <summary> <b>Unix</b> users click here to expand</summary>

  You can execute these commands from any working directory since the environment will be created 
  in an Anaconda/Miniconda specific default directory.

  ```bash
  foo@bar:~$ conda create --name qudi-env python=3.10
  ```

  ---

</details>

You can delete the environment again by calling:

```console
conda env remove --name qudi-env
```

## Step 2: Activate the new Python environment
Anything related to qudi and its package dependencies must be done in the new Python environment.
Make sure to activate the environment in your command line before starting or (de-)installing any 
Python packages that should be used with qudi.

The process of activating the Python environment differs again depending on how you set up the 
environment in the first place.  
We will describe environment activation for the two variants described in the previous step.

### Variant 1: Python standard library
If you have installed the Python environment with the builtin `venv` package, you can find OS 
specific activation commands below (assuming `qudi-env` as environment name).  
Basically there is an `activate` executable for every OS type in the newly created environment 
folder under `.../qudi-env/Scripts/` .

<details>
  <summary> <b>Windows</b> users click here to expand</summary>

  > **⚠ WARNING:**
  > 
  > If you are using the MS Windows PowerShell, you may need to allow script execution on your 
  > system if you have not done this before at some point.  
  > Please refer to 
  > [this thread](https://superuser.com/questions/106360/how-to-enable-execution-of-powershell-scripts) 
  > for further information if you encounter any errors with the commands below.

  Execute the `activate` script in `qudi-env\Scripts\`

  ```console
  C:\Software\qudi> cd qudi-env\Scripts\
  
  C:\Software\qudi\qudi-env\Scripts> .\activate
  ```

  Your command prompt should now have a prefix showing your environment name. In this example it 
  would look like:

  ```console
  (qudi-env) C:\Software\qudi\qudi-env\Scripts>
  ```

  ---

</details>

<details>
  <summary> <b>Unix</b> users click here to expand</summary>

  Execute the `activate` script in `qudi-env/Scripts/`

  ```bash
  foo@bar:/opt/qudi$ cd qudi-env/Scripts
  
  foo@bar:/opt/qudi/qudi-env/Scripts$ source activate
  ```

  ---

</details>

You can deactivate the environment with the command `deactivate`.

### Variant 2: Anaconda/Miniconda
If you have installed the Python environment with `conda`, you can activate the environment in your 
command line (assuming `qudi-env` as environment name) with:
```console
conda activate qudi-env
```

And you can deactivate the environment with:
```console
conda deactivate
```


## Step 3: Install qudi-core
The `qudi-core` package installation provides you with the general qudi framework and a minimum 
running application. User application measurement modules need to be installed as namespace 
packages on top of the `qudi-core` package at a later stage (see 
[step 4](#step-4-install-measurement-module-addons)).

> **⚠ WARNING:**
> 
> Basically you have to decide at this point what packages to install from source in development 
> mode (code can be changed without installing qudi again).  
> Most users will not want to actively develop the `qudi-core` source code. On the other hand you 
> probably want to edit your measurement modules source code occasionally while using qudi.  
> 
> For this most common use-case we recommend installing `qudi-core` directly from the Python Package 
> Index (PyPI) and installing the measurement module addons from source in development mode.  
> This enables you to fiddle with your measurement code later on and have the `qudi-core` installed 
> as stable version that can be maintained via `pip` and the PyPI in a user-friendly way known from 
> other Python packages.

> **⚠ WARNING:**
> 
> Make sure you have your Python environment activated before executing anything described below 
> (see previous step).

### Variant 1: Installing from PyPI
This is as easy as installing any other Python package:

```console
python -m pip install qudi-core
```

### Variant 2: Installing from source (dev)
In order to install `qudi-core` from source, you need to copy the `qudi-core` repository to your 
computer.  
There are mainly two ways of doing that:
- Download and extract the latest 
[release from GitHub](https://github.com/Ulm-IQO/qudi-core/releases)

OR

- Clone the [repository `main` branch](https://github.com/Ulm-IQO/qudi-core) to your local machine 
using [`git`](https://git-scm.com/)

The latter option enables you to contribute code and/or to pull the latest development 
version from all branches, but it requires you to install [`git`](https://git-scm.com/) on your 
system.

NOTE: The exact directory location on your local machine does not matter as long as you keep it there and do not copy it around later on.

Once you have a copy of the source code on your local machine, you can change into this directory 
(top directory containing `pyproject.toml`) and install `qudi-core` using `pip` with the development
flag `-e` set:
```console
python -m pip install -e .
```

---

All dependencies will be installed by `pip` and it will register several entry points that are 
executables within the Python environment:

| command                 | effect                                                        |
| ----------------------- | ------------------------------------------------------------- |
| `qudi`                  | Starts qudi                                                   |
| `qudi-config-editor`    | Starts a standalone graphical configuration editor for qudi   |
| `qudi-install-kernel`   | Installs and registers the qudi IPython kernel in your system |
| `qudi-uninstall-kernel` | Uninstalls the qudi IPython kernel from your system           |

> **⚠ WARNING:**
> 
> Installing qudi via pip will NOT automatically register the qudi IPython kernel in the system.
> You will lack the interactive IPython console in the qudi main GUI as well as any jupyter notebook
> support.
> 
> While you can use qudi without this IPython integration, we strongly recommend to call 
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

## Step 4: Install measurement module addons
Unless you have a robust deployment of measurement modules at hand that do not need to be altered 
too often, you may want to install any measurement module namespace packages from source.

If your measurement module package deployment is following the 
[qudi project suggestions](../404.md), you can install them exactly like described in the previous 
step.

If you are into quantum optics measurements with colorcenters in diamond or similar semiconductors, 
you may want to consider using the [measurement modules package `qudi-iqo-modules`](https://github.com/Ulm-IQO/qudi-iqo-modules) provided by the Institute for 
Quantum Optics ([Ulm-IQO](https://github.com/Ulm-IQO/)) under the LGPL v3 license.

---

[index](../index.md)
