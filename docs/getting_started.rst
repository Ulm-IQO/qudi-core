.. _getting_started:

--------------

How to get started with qudi
============================

This article is an attempt at guiding new users through the process of
installing, understanding and using qudi.

Installation
------------

If you are new to qudi, you may want to try it out in a demo environment
on your own computer first.

| Luckily, the way qudi is built lets you have a look at most user
  interfaces and tools even if your computer isn’t connected to real
  instrumentation hardware.
| For every hardware interface in qudi, there must be a dummy module to
  simulate this hardware type in the absence of a real instrument.

The installation however is always the same. You can refer to the
detailed step-by-step :ref:`installation guide <installation>` to
install qudi.

Startup
-------

Time to fire up the engines… Please refer to the detailed :ref:`startup guide <startup>` to run qudi.

If you have set up everything correctly, you should see the main window
of qudi coming up.

Playtime
--------

Qudi user applications revolve around “qudi measurement toolchains” that
are deployed separately from the framework functionality in qudi-core. A
toolchain usually consists out of modules dedicated to - **Logic**:
“Brains” of each application. Configure, control and monitor the
measurement. Orchestrate hardware. - **Hardware**: Similar to a driver.
Provide simple, abstracted
:ref:`interfaces <hardware_interface>` to avoid the
logic from needing to “speak” the language of each specific device. -
**GUI**: User-friendly graphical interfaces.

An example for an addon repository that providess several measurement
toolchains is the
:ref:`qudi-iqo-modules <iqo>`
package (developed by the Institute for Quantum Optics of Ulm
University). Installing it is a great and simple way to play around with
qudi, as it comes with dummy hardware modules that run even without
connecting real instrumentation hardware.

After a fresh installation of qudi-iqo-modules, make sure that you load
the ``default.cfg`` as described in the :ref:`iqo-modules installation
guide <iqo>`.
Qudi should then run with only dummy hardware modules configured after a
restart. That means you can load any toolchain you like by clicking on
the respective GUI module name in the main window without breaking
anything.

So… feel free to play around and get familiar with some of the GUIs and
the main manager window.

Close qudi if you had enough by selecting ``File -> Quit qudi`` in the
top left menu bar of the manager window. Alternatively you can also
press the shortcut ``Ctrl + Q`` while the manager window is selected.

Configuration
-------------

| If you want to use qudi productively in your setup, we have to get rid
  of all the dummy modules and replace them with real hardware modules.
| You probably also want to get rid of some toolchains
  (GUI/logic/hardware) entirely if you are not using them in your
  specific setup. They will just clutter you manager GUI otherwise.

For telling qudi what modules to use and how they should connect to each
other, you need to provide a setup-specific config file.

Please refer to the detailed :ref:`configuration
guide <configuration>` to set up a proper qudi
config for your needs.

Extending qudi
--------------

You might be lucky enough to find all the tools you need to conduct you
experiment. But there’s a good chance you will need something that has
not been developed before. This may be just a hardware module to control
a new instrument, a new button in a GUI or a whole new
(hardware/logic/GUI) toolchain.

Choose a qudi addon repository to work in
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| In that case, you will need to go even deeper in the code. There are
  two alternative ways of approaching qudi development: 1. You can
  :ref:`install
  qudi-iqo-modules <iqo>`
  in dev mode (mind ``python -m pip install -e .`` in the instruction)
  and change or add modules there locally at your liking.
| If you need to share changes with others online, it might be advisable
  to fork
  `qudi-iqo-modules <https://github.com/Ulm-IQO/qudi-iqo-modules>`__ and
  perform the installation pointing to your forked github repository. 2.
  You may setup a fresh repository that follows the structure of our
  `qudi-addon-template <https://github.com/Ulm-IQO/qudi-addon-template>`__.
| This is the recommended way if you want to develop your own
  toolchains. You can still install multiple addon packages
  (e.g. qudi-iqo-modules) and list them as dependencies.

With both ways, you’ll be able to install your own developments on top
of an existing qudi-core installation, as described in `Step
4 </docs/_build/html/setup/installation.html#step-4-install-measurement-module-addons>`__ of
the installation instructions.

| You may even want to share your hard work with others or find people
  who can give you input on the matter. Please approach us if you like
  to contribute to our repos or want your repo mentioned in this
  documentation.
| We’re happy to build an active development community with you.

New qudi measurement modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is no need to delve into the very core of qudi to understand its
entirety before implementing new measurement modules. The first simple
step to develop your own measurement that’s separate from the existing
toolchains, is a custom logic module. Logic modules control the
measurement, orchestrate the hardware and optionally connect to GUIs for
user-friendly configuration and data analysis.

| A simple `example
  logic <https://github.com/Ulm-IQO/qudi-addon-template/tree/main/src/qudi/logic>`__
  module can be found in our addon-template repo. Alongside, there’s
  also everything you’ll need to develop your own complete toolchain in
  that repo.
| For your custom logic module, we suggest starting by copying the
  ``template_logic.py`` into a new Python file located in
  ``your-or-iqo-qudi-modules/src/qudi/logic``.
| You can see from the short TemplateLogic class excerpt taken from
  ``template_logic.py`` below, how few lines of codes are needed for
  your own module:

.. code:: python

   class TemplateLogic(LogicBase):

       # Declare signals to send events to other modules connecting to this module
       sigCounterUpdated = QtCore.Signal(int)  # update signal for the current integer counter value

       # Declare static parameters that can/must be declared in the qudi configuration
       _increment_interval = ConfigOption(name='increment_interval', default=1, missing='warn')

       # Declare status variables that are saved in the AppStatus upon deactivation of the module and
       # are initialized to the saved value again upon activation.
       _counter_value = StatusVar(name='counter_value', default=0)

       # Declare connectors to other logic modules or hardware modules to interact with
       _template_hardware = Connector(name='template_hardware',
                                      interface='TemplateInterface',
                                      optional=True)

       def on_activate(self) -> None:
           ...

       def on_deactivate(self) -> None:
           ...

The TemplateLogic makes use of four central concepts: - ``Connector`` to
communicate with other qudi modules, - ``StatusVar`` to store variables
across restarts of qudi, - ``ConfigOption`` to define runtime constants
via config file, and - ``Signal`` for easy (asynchronous) communication
with connected qudi modules.

For more info on the software infrastructure that your custom module may
use, please refer to the :ref:`measurement
modules <measurement_modules>` documentation.

| After you successfully loaded your custom logic in the qudi manager,
  you can go on by adding more functions and stripping away not needed
  parts.
| Functions of a module can be executed by calling the loaded module
  from the manager console, eg. by

.. code:: python

   example_logic.reset_counter()

--------------

