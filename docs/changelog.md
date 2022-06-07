# Changelog

## Pre-Release

### Breaking Changes
- Changed event handling of qudi module state machine. `on_deactivate` will be run BEFORE the state 
machine actually changes into state `deactivated`.

### Bugfixes
None

### New Features
- Support for `enum.Enum` types in `qudi.util.yaml`, enabling use of enums in qudi config and 
status variables.
- `qudi.util.constraints.ScalarConstraint` data class to easily define bounds for, check and clip 
scalar values.

### Other
None