# Changelog

## Pre-Release

### Breaking Changes
- Got rid of the `fysom` package for qudi module state machines. This increases complexity and 
readability for these very easy state machines and concentrates state transition procedure in the 
FSM itself.
- Intoduced new enum types `ModuleState` and `ModuleBase` in `qudi.core.module` for state and 
module base type representation.
- Changed `qudi.core.module.Base` properties `is_module_threaded` and `module_base` to read-only 
class descriptors
- Turned `ConfigOption`, `StatusVar` and `Connector` into descriptors, eliminating the need to call 
or explicitly construct them
- Combined meta object, id, logging and appdata functionality in new general purpose 
`QudiObjectMeta` and `QudiObject` (meta)classes. This new object serves as base class for 
`qudi.core.module.Base`
- `Connector` and `ConfigOption` now need to be initialized in `QudiObject.__init__`
- Refactoring of `qudi.util.overload.OverloadProxy` which is now a subclass of a more general 
object proxy found in the new module `qudi.util.proxy`.
- Adjusted `ModuleManager` according to the meta object changes in `qudi.core.module`. Now there is 
no more distinction between `loaded` and `activated` module state. Module `__init__` is called upon 
activation and it is destroyed upon deactivation.
- `qudi.core.modulemanager.ModuleManager` is now a subclass of `QtCore.QAbstractTableModel` and 
serves as singular central data source for all managed qudi modules and their status. The main GUI 
and module servers (remote and local) have been adjusted accordingly.
- GUI modules can no longer be shared by the remote module and local namespace servers.
- Refactored `qudi.core.gui` into a set of static functions
- moved all popup and balloon message prompt functions into new `qudi.core.message` module. Works 
for both GUI and headless mode. Also removed the corresponding member methods from 
`qudi.core.module.Base` class. If you need to use it, import it from the new module.
- Moved `qudi.core.application.SystemTrayIcon` to `qudi.core.trayicon.QudiTrayIcon` and made it a 
singleton

### Bugfixes
- Python module reload during runtime is now only performed if explicitly requested by the user
- Fixed a `scipy` warning about the deprecated `scipy.ndimage.filters` namespace

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

### Other
- Deprecated calling `qudi.core.module.Base.module_state` and `Connector` meta attributes.
- Deprecated `qudi.util.paths.get_module_app_data_path` in favor of 
`qudi.util.paths.get_module_appdata_path`
- Improved performance reading and mutating `qudi.util.models.DictTableModel` and 
`qudi.util.models.ListTableModel` from


## Version 1.5.1
Released on 18.08.2024

### Breaking Changes
None

### Bugfixes
- Fixed deprecated import path for `windows` module from `scipy.signal` in `qudi.util.math`
- Fixed decay parameter estimation in `qudi.util.fit_models.exp_decay.ExponentialDecay` fit model
- Fixed syntax error in `qudi.util.fit_models.lorentzian.LorentzianLinear` fit model

### New Features
None

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
