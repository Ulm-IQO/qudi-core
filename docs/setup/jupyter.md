---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Jupyter Notebook Integration

While it is great to have a GUI to control an experiment, direct programmatic access to measurement modules
is also required in many situations. For this purpose, qudi runs an interactive Python (IPython) kernel
that can be accessed from a [Jupyter notebook](https://jupyter.org/).

To get started, open a console (e.g. PowerShell) and activate the virtual environment or conda environment
where `qudi-core` is installed. Then, make sure that the qudi kernel is installed by running

  ```console
  qudi-install-kernel
  ```

The qudi kernel usally only needs to be installed once after the installation of qudi via `pip`.

> **Note**
> 
> A re-installation of the kernel is required if you run a different installation of qudi in
a different environment. During installation, any other kernels with name "qudi" registered for that user
> will be overwritten.

Now start qudi as usual by executing

  ```console
  qudi
  ```

from the console. Then, open a new console and move to the folder where you want your notebook files to be.
Start a JupyterLab server (don't forget to enable the qudi environment beforehand) with the command

  ```console
  jupyter lab
  ```

and wait for the lab to open in your browser (the classic notebook server is equally supported).
If nothing opens up automatically, try the default address [`http://localhost:8888/`](http://localhost:8888/)
in your browser.

A launcher should have started in JupyterLab. Create a new notebook connected to the qudi kernel
by clicking the `qudi` button in the top row of the launcher. 

We can now access the running qudi instance with the `qudi` command. You should get something like this:  

```
>>> qudi
<qudi.core.application.Qudi(0x29479756200) at 0x000002947A2F6940>
```

Every active measurement module is also available through its name. If you activate e.g. module
`red_laser` from the manager, you can run something like

```
>>> red_laser.turn_on_emission()
>>> red_laser.is_running
True
```

from your notebook, provided these attributes actually exist for this module of course.

The qudi logger is also accessible from the notebook. Try something like

```
>>> logger.info(f'Red laser in on: {red_laser.is_running}')
```

to see it in action.

In this way you can write your own measurements scripts that employ qudi modules. This can
be useful to configure a fully automated measurement sequence for example.
You can read more about the qudi kernel on the [Integrated IPython kernel](../404.md) page.

---

[index](../index.md)
