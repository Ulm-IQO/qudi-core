---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Starting qudi
If you have followed the [installation instructions](installation.md), the easiest way of running 
qudi is by command line (do not forget to activate the Python environment beforehand):
```shell
> qudi
```

There are also two additional supported ways to run qudi:
1. Run as a Python module with:
   ```shell
   > python -m qudi
   ```
2. Execute the startup script `runnable.py` located in the qudi main directory: 
   ```shell
   > python runnable.py
   ```
   This is especially helpful when you have qudi installed in development mode and want to run qudi 
   from within an IDE like e.g. PyCharm.

### Command Line Arguments
The above mentioned commands takes several optional command line arguments to pass to qudi upon 
startup:

| argument        | description                                                   |
| --------------- | ------------------------------------------------------------- |
| `-h`<br/>`--help`   | Print help message about available command line arguments. |
| `-g`<br/>`--no-gui` | Run qudi "headless" without GUI support.<br/>User interaction can only happen via IPython kernel interface. |
| `-d`<br/>`--debug`  | Run qudi in debug mode to log all debug messages.<br/>This might impact performance. |
| `-c`<br/>`--config` | Must be followed by the file path to a qudi config file to use for this qudi session. |
| `-l`<br/>`--logdir` | Must be followed by the full path to a directory where qudi should dump log messages into. |

You can execute `qudi -h` to receive a help message about available command line arguments:
```
usage: python -m qudi [-h] [-g] [-d] [-c CONFIG] [-l LOGDIR]

optional arguments:
  -h, --help            show this help message and exit
  -g, --no-gui          Run qudi "headless", i.e. without GUI. User interaction only possible via IPython kernel.
  -d, --debug           Run qudi in debug mode to log all debug messages. Can affect performance.
  -c CONFIG, --config CONFIG
                        Path to the configuration file to use for for this qudi session.
  -l LOGDIR, --logdir LOGDIR
                        Absolute path to log directory to use instead of the default one "<user_home>/qudi/log/"
```

---

[index](../index.md)