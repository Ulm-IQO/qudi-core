# Changelog

## Pre-Release

### Breaking Changes
- Got rid of the `fysom` package for qudi module state machines. This increases readability for 
these very easy state machines and concentrates state transition procedure in the FSM itself.
- Intoduced new enum types `ModuleState` and `ModuleBase` in `qudi.core.module` for state and 
module base type representation.
- Changed `qudi.core.module.Base` properties `is_module_threaded` and `module_base` to read-only 
class descriptors. Renamed `is_module_threaded` to `module_threaded`.
- Turned `ConfigOption`, `StatusVar` and `Connector` into descriptors, eliminating the need to call 
or explicitly construct them in the qudi modules
- `Connector` meta attribute now needs to be initialized with the actual interface type instead of 
a name string. This requires changing all qudi modules that have not already done this before.
- Combined meta object, id, logging, appdata and abc functionality in new general purpose mixin 
class `QudiQObjectMixin` that can be inherited in conjunction with any `QObject` or `QWidget`
(sub-)class. This new mixin is used as base class for `qudi.core.module.Base` among others.
- `Connector` and `ConfigOption` now need to be initialized in `Base.__init__`
- Refactoring of `qudi.util.overload.OverloadProxy` which is now a subclass of a more general 
object proxy found in the new module `qudi.util.proxy`.
- Adjusted `ModuleManager` according to the meta object changes in `qudi.core.module`. Now there is 
no more distinction between `loaded` and `activated` module state. Module `__init__` is called upon 
activation and it is destroyed upon deactivation.
- `qudi.core.modulemanager.ModuleManager` now serves as singular central data source for all 
managed qudi modules and their status. The main GUI and module servers (remote and local) have been
adjusted accordingly.
- GUI modules can no longer be shared by the remote module and local namespace servers.
- Refactored `qudi.core.gui` into a set of static functions
- moved all popup and balloon message prompt functions into new `qudi.core.message` module. Works 
for both GUI and headless mode. Also removed the corresponding member methods from 
`qudi.core.module.Base` class. If you need to use it, import it from the new module.
- Moved `qudi.core.application.SystemTrayIcon` to `qudi.core.trayicon.QudiTrayIcon` and made it a 
singleton
- All qudi modules are now configured and imported upon `Qudi.__init__` and not as before during
`Qudi.run`. This means qudi modules are imported and the `ModuleManager` is fully configured before
the `Qt` event loop starts.
- Qudi configuration is now considered static after loading during `Qudi.__init__` and all
modification during runtime results in undefined behaviour.
- The ensemble of modules handled by `ModuleManager` is considered static as well and all methods
used to mutate this collection have been removed.
- `qudi.util.paths.get_default_data_dir` will now return the path set by qudi global configuration
options `default_data_dir` and `daily_data_dirs` instead of a static path. If no `Qudi` instance
has been created, the previous default path is still returned. If you just want the data root
directory without daily subdirectories (if configured) use `qudi.util.paths.get_default_data_root`
instead.
- `Connector` meta object will now check interface compliance upon connection with a target by
importing the target class by name and checking with `issubclass`. This works with
`rpyc.core.netref` proxies (remote modules) as well as with local modules.
This results in a hard requirement of the remote qudi environment and local qudi environment to
have the same qudi namespace packages installed.
- Reloading modules will now simply deactivate them and re-activate them if they have been active 
before. Reloading will no longer invalidate the import cache and reload the module from file so 
that code changes are applied during runtime. This has been causing too many problems in the past 
since most users and even developers are not aware about the many caveats that come with it.

### Bugfixes
- Fixed a `scipy` warning about the deprecated `scipy.ndimage.filters` namespace
- Exceptions during initialization and construction of `ConfigOption` and `StatusVar` will now
cause the affected descriptor to be initialized to its default value and no longer prevent the
module from activating. `Connector` behaves similar if it is optional.
- Fixed a bug where qudi would deadlock when starting a GUI module via the ipython terminal
- Fixed a bug with the `qtconsole` package no longer being part of `jupyter`. It is now listed
explicitly in the dependencies.
- Remote modules should work now with `rpyc>=6.0.0`
- Fixed `EOFError` messages in remote clients occurring upon client shutdown if host
server has shut down first. This sometimes even prevented remote clients to shut down altogether.
- Improved thread safety of the `ThreadManager` which should get rid of bugs related to rapid 
module activation/deactivation cycles.

### New Features
- New context manager `qudi.util.mutex.acquire_timeout` to facilitate (Recursive)Mutex/(R)Lock
acquisition with a timeout
- Added helper methods `call_slot_from_native_thread`, `current_is_native_thread` and
`current_is_main_thread` to `qudi.util.helpers` for easy handling of `QObject` thread affinity
- Added `qudi.util.yaml.YamlFileHandler` helper object to easily dump/load/clear/check a qudi
status file
- Global config option `default_data_dir` accepts strings with a leading `~` character to be
expanded into the current users home directory
- A main GUI that does not show up in the `ModuleManager` model can be configured in the global
configuration section (`main_gui` keyword). The default is the known manager GUI. If you set this
config option to `None`, no main GUI will be opened on startup. Configured startup modules work the
same as before.
- Added a "clear all AppData" action to the main GUI menus that deletes the AppData files of all
configured modules at once.
- Added a "deactivate all modules" action to the main GUI menus that deactivates all configured
modules at once.
- Remote module server will now keep track of shared module instance count. This is used to
dynamically react to remote module deactivation calls by only deactivating if no module (remote or
local) is using the respective module. The module will not deactivate on the host otherwise and a
warning will be logged on the remote client.
- Added "Clear all AppData" and "Dump all AppData" actions to the main GUI menus that manually dump
or clear all module appdata at once.
- Added "Dump AppData" button to each module in manager/main GUI to manually force an AppData dump
of the respective module.

### Other
- Deprecated calling `qudi.core.module.Base.module_state` property and `Connector` meta attributes.
- Deprecated `qudi.util.paths.get_module_app_data_path` in favor of 
`qudi.util.paths.get_module_appdata_path`
- Improved performance reading and mutating `qudi.util.models.DictTableModel` and 
`qudi.util.models.ListTableModel`
- Removed `setup.py` and moved fully to `pyproject.toml` instead


## Version 1.5.1
Released on 18.08.2024

### Breaking Changes
None

### Bugfixes
- Fixed deprecated import path for `windows` module from `scipy.signal` in `qudi.util.math`
- Fixed decay parameter estimation in `qudi.util.fit_models.exp_decay.ExponentialDecay` fit model
- Fixed syntax error in `qudi.util.fit_models.lorentzian.LorentzianLinear` fit model

### New Features
- Introduced `DiscreteScalarConstraint` that expands the functionality of `ScalarConstraint` to check whether a value 
is in a set of discrete values

### Other
- Improved documentation [`getting_started.md`](getting_started.md)
- Added documentation [`programming_guidelines/data_fitting_integration.md`](programming_guidelines/data_fitting_integration.md)


## Version 1.5.0
Released on 16.11.2023

### Breaking Changes
None

### Bugfixes
- Fixes a bug where all fit configurations for a fit model/container fail to load upon activation
of a module because the fit model saved in AppData is no longer available. Throws a warning now
instead and ignores the respective fit configuration.
- Fixed a bug that caused `qudi.util.models.DictTableModel` to raise `IndexError` when used in a
`ListView` and/or when data at index zero is requested.

### New Features
- Added helper functions in util/linear_transform.py to allow transformations (rotations and shifts) using the afﬁne transformation matrix formalism.

### Other
- Fine-tuning of string output of fit results from qudi.util.units.create_formatted_output(): Failed fits should provide
  error= np.nan. Fixed parameters are marked as such. Brackets introduced, eg. (2.67 ± 0.01) GHz.


## Version 1.4.1
Released on 21.06.2023

### Breaking Changes
None

### Bugfixes
None

### New Features
- Added utility descriptor objects to new module `qudi.util.descriptors`. Can be used to
facilitate smart instance attribute handling.

### Other
- Support for Python 3.10
- Better backwards compatibility of `qudi.util.constraints.ScalarConstraint` with the deprecated
`qudi.core.interface.ScalarConstraint` object


## Version 1.3.0
Released on 20.12.2022

### Breaking Changes
None

### Bugfixes
- NULL bytes in log messages are handled now and no longer lead to crashes of qudi. They are
replaced by the corresponding hex literal "\x00".
- Rubberband selection of utility plot widgets now works for `pyqtgraph != 0.12.4`. This specific
version is broken in that regard and a comprehensive error is thrown if it is detected.
- Adjusted 2D gaussian fit arguments to be compatible with the datafitting toolchain.

### New Features
- Multiple qudi sessions can now be run in parallel locally. However, the user must ensure
non-conflicting socket server settings for namespace server and remote module server in the
configs to load.

### Other
- Bumped minimum package requirement `pyqtgraph >= 0.13.0`.
- Introduced properties to make `qudi.util.constraints.ScalarConstraint` mostly backwards
compatible with the deprecated `qudi.core.interface.ScalarConstraint`. Only exception is `unit`
which should not be supported anymore.


## Version 1.2.0
Released on 30.09.2022

### Breaking Changes
None

### Bugfixes
None

### New Features
- New general-purpose interactive data display widget
`qudi.util.widgets.plotting.interactive_curve.InteractiveCurvesWidget` providing multiple optional
features:
  - Legend creation and generic dataset naming
  - Linking of fit curve to dataset and synchronous handling of both
  - Rubberband zooming in 1 and 2 dimensions
  - Data markers in 1 and 2 dimensions
  - Data range selections in 1 and 2 dimensions
  - Checkbox-based toggling of dataset visibility
  - Plot editor for setting axis labels, units and view ranges
  - Mouse cursor tracking and display in data coordinates
  - Various signals to interface with the above-mentioned features

### Other
None


## Version 1.1.0
Released on 25.07.2022

### Breaking Changes
- Changed event handling of qudi module state machine. `on_deactivate` will be run BEFORE the state
machine actually changes into state `deactivated`.
- `ConfigOption` meta-attributes of qudi modules are no longer set in config under the module name
section directly, but must be specified in an `options` subsection instead.
So something like
  ```python
  my_module_name:
      module.Class: 'qudi.hardware.my_module.MyModule'
      first_option: 42
      second_option: 'hello world'
  ```
  must become now
  ```python
  my_module_name:
      module.Class: 'qudi.hardware.my_module.MyModule'
      options:
          first_option: 42
          second_option: 'hello world'
  ```

### Bugfixes
- Qudi logging facility active during startup procedure
- Reduced RPyC related errors in qudi IPython kernel

### New Features
- Support for `enum.Enum` types in `qudi.util.yaml`, enabling use of enums in qudi config and
status variables.
- `qudi.util.constraints.ScalarConstraint` data class to easily define bounds for, check and clip
scalar values.
- Added qudi logger object to qudi IPython kernels to give users the possibility to directly log
messages into qudi from e.g. a jupyter notebook.

### Other
- Structure and type checking as well as default value handling in the qudi configuration file is
now done via JSON Schema (Draft-07). The applied schema is defined in `qudi.core.config.schema`.
Every time you load/dump a configuration from/to file or add/remove a module config or set a global
config option using `qudi.core.config.Configuration`, the config is validated against this JSON
schema.
