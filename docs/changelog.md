# Changelog

## Pre-Release

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
None

### New Features
- Support for `enum.Enum` types in `qudi.util.yaml`, enabling use of enums in qudi config and 
status variables.
- `qudi.util.constraints.ScalarConstraint` data class to easily define bounds for, check and clip 
scalar values.

### Other
- Structure and type checking as well as default value handling in the qudi configuration file is 
now done via JSON Schema (Draft-07). The applied schema is defined in `qudi.core.config.schema`.  
Every time you load/dump a configuration from/to file or add/remove a module config or set a global 
config option using `qudi.core.config.Configuration`, the config is validated against this JSON 
schema.
