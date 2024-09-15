`index <../index.rst>`__

--------------

.. _startup:

Starting qudi
=============

If you have followed the :ref:`installation instructions <installation>`, the easiest way of running qudi is by
command line (do not forget to activate the Python environment beforehand):

.. code:: shell

   qudi

There are also two additional supported ways to run qudi:

1. Run as a Python module with:


   .. code:: shell

      python -m qudi.core

2. Execute the startup script ``runnable.py`` located in the qudi main directory:


   .. code:: shell

      python runnable.py

   This is especially helpful when you have qudi installed in development mode and want to run qudi from within
   an IDE like PyCharm.

Command Line Arguments
----------------------

The above-mentioned commands take several optional command line
arguments to pass to qudi upon startup:

+------------------------+--------------------------------------------------------+
| argument               | description                                            |
+========================+========================================================+
| ``-h``, ``--help``     | Print help message about available command line        |
|                        | arguments.                                             |
+------------------------+--------------------------------------------------------+
| ``-g``, ``--no-gui``   | Run qudi "headless" without GUI support.               |
|                        | User interaction only via IPython kernel.              |
+------------------------+--------------------------------------------------------+
| ``-d``, ``--debug``    | Run qudi in debug mode to log all debug messages.      |
|                        | This might impact performance.                         |
+------------------------+--------------------------------------------------------+
| ``-c``, ``--config``   | Must be followed by the file path to a qudi config     |
|                        | file to use for this qudi session.                     |
+------------------------+--------------------------------------------------------+
| ``-l``, ``--logdir``   | Must be followed by the full path to a directory where |
|                        | qudi should dump log messages into.                    |
+------------------------+--------------------------------------------------------+

You can execute ``qudi -h`` to receive a help message about available
command line arguments:

::

   usage: python -m qudi.core [-h] [-g] [-d] [-c CONFIG] [-l LOGDIR]

   optional arguments:
     -h, --help            show this help message and exit
     -g, --no-gui          Run qudi "headless", i.e., without GUI. User interaction only possible via IPython kernel.
     -d, --debug           Run qudi in debug mode to log all debug messages. Can affect performance.
     -c CONFIG, --config CONFIG
                           Path to the configuration file to use for this qudi session.
     -l LOGDIR, --logdir LOGDIR
                           Absolute path to log directory to use instead of the default one "<user_home>/qudi/log/"

--------------
