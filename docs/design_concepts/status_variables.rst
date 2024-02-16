`index <../index.rst>`__

--------------

Status Variables
================

When working with `measurement modules <measurement_modules.rst>`__
(hardware/logic/GUI) you may want to preserve some variable values
across consecutive runs of qudi.

We call measurement module instance variables that are automatically
dumped/loaded upon deactivation/activation a “status variable”.

| The parent ``Base`` class will take care of dumping all status
  variables upon deactivation of the module. This will happen
  automatically at the end of ``on_deactivate`` and does NOT need to be
  triggered explicitly in the ``on_deactivate`` method definition.
| This will also happen in case ``on_deactivate`` raises an exception.

   **⚠ WARNING:**

   | Status variables will NOT be automatically saved if the measurement
     modules are not deactivated properly (i.e. by the module manager).
   | This can happen for example if the user is just killing the qudi
     process instead of shutting it down as intended (e.g. by pressing
     the “stop” button in the PyCharm IDE).

   If this happens, the next startup of the modules will load the status
   variables from the last graceful deactivation.

| Upon module activation, immediately before ``on_activate`` is run,
  status variables are read from disk and initialized in the module
  instance. This means that ``on_activate`` can already use these
  variables.
| If there are any exceptions raised during this process, the module
  activation will still proceed but the status variable will be
  initialized with its default value instead if defined. This can
  however easily lead to follow-up errors in ``on_activate``.

The status variables are stored in YAML format in one file per module
using the qudi utilities in ``qudi.util.yaml``. They are stored in an OS
dependent qudi “AppData” directory.

Usage
-----

In order to simplify the process of dumping/loading these variables
to/from disk and prevent each measurement module to implement their own
solution, qudi provides the meta object
``qudi.core.statusvariable.StatusVar``.

When implementing a `measurement module <measurement_modules.rst>`__
(hardware/logic/GUI) you can simply instantiate ``StatusVar`` class
variables. These meta objects will be transformed into regular variable
members of your measurement module instances and can be used like any
normal instance variable in Python:

.. code:: python

   from qudi.core.statusvariable import StatusVar
   from qudi.core.module import LogicBase

   class MyExampleLogic(LogicBase):
       """ Module description goes here """
       
       _my_status_variable = StatusVar(name='my_storage_name', default=42,)

       ...

       def increment_my_variable(self):
           self._my_status_variable += 1

       ...

constructor & representer
~~~~~~~~~~~~~~~~~~~~~~~~~

| Since status variables are dumped as YAML file you are limited in what
  data types can be stored.
| Qudi YAML dumper and loader currently supports any native Python
  builtin type and numpy arrays.

If your status variables should be of any other type, you need to
provide conversion functions to the ``StatusVar`` meta object: - The
``constructor`` is a callable that accepts a simplified variable from
the YAML loader and returns the data as custom data type to initialize
the status variable with. - The ``representer`` is a callable that
accepts the custom status variable data and returns a simplified data
representation that is digestible by the YAML dumper.

You can provide ``constructor`` and ``representer`` callables as
arguments to ``StatusVar`` or you can register a callable member of your
module as such via decorators, e.g.:

.. code:: python

   from qudi.core.statusvariable import StatusVar
   from qudi.core.module import LogicBase

   class FancyDataType:
       def __init__(self, a, b):
           self.a = a
           self.b = b


   class MyExampleLogic(LogicBase):
       """ Module description goes here """
       
       _my_status_variable = StatusVar(default=FancyDataType(42, 3.1415))
       _my_other_status_variable = StatusVar(
           default=FancyDataType(1, 2),
           constructor=lambda yaml_data: FancyDataType(*yaml_data), 
           representer=lambda data: [data.a, data.b]
       )
       
       ...

       @_my_status_variable.constructor
       def my_status_variable_constructor(self, yaml_data):
           return FancyDataType(*yaml_data)
       
       @_my_status_variable.representer
       def my_status_variable_constructor(self, data):
           return [data.a, data.b]

       ...

Since these conversion functions are usually static (as the example
above also shows), you could also combine that with the
``@staticmethod`` decorator. But this is not necessary and just good
style.

name
~~~~

| There is an optional ``name`` argument for ``StatusVar``. The name
  given here is used by the YAML dumper as field name for the variable
  data. So the ``name`` argument can be used to store the status
  variable under a different (e.g. better readable) name in the app
  status file that is created.
| A common use case is (as shown in the example above) to exclude the
  Pythonic (double-)underscore from the variable name.
| By default, the declared variable name in the class body will be used
  and since the user usually never opens the AppStatus files, this
  feature is not quite too useful.

--------------

`index <../index.rst>`__
