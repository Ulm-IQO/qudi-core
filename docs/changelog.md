# Changelog

## Pre-Release

### Breaking Changes
None

### Bugfixes
None

### New Features
None

### Other
None


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
