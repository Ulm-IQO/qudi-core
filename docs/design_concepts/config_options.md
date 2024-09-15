---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Configuration Options

When working with [measurement modules](measurement_modules.md) (hardware/logic/GUI) you may want 
to give the user the opportunity to statically configure certain aspects of the measurement module.

[Static configuration](configuration.md) in qudi is generally handled via a YAML configuration file 
that is read and parsed during the application startup process.  
All [measurement modules](measurement_modules.md) included in the qudi session are declared in this 
file (among other things). But apart from the mandatory properties you can declare any number of 
additional properties inside the `options` property for each measurement module.  
Please refer to the [qudi configuration documentation](configuration.md) for more details on config 
files.

A measurement module constant that is automatically initialized from the qudi configuration is 
called a "configuration option" or "config option".

> **⚠ WARNING:**
> 
> Config options are initialized only ONCE during instantiation of a measurement module and NOT 
> every time the module is activated.  
> So it is good practice to keep config option data members constant during runtime.

## Usage
In order to simplify and automate the process of initializing these data members and prevent each 
measurement module to implement their own solution, qudi provides the meta object 
`qudi.core.configoption.ConfigOption`.

When implementing a [measurement module](measurement_modules.md) (hardware/logic/GUI) you can 
simply instantiate `ConfigOption` class variables. These meta objects will be transformed into 
regular variable members of your measurement module instances and can be used like any normal 
instance variable in Python:
```python
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase

class MyExampleLogic(LogicBase):
    """ Module description goes here """
    
    _my_config_option = ConfigOption(name='my_config_option', 
                                     default='Not configured', 
                                     missing='warn')

    ...

    def print_my_config_option(self):
        print(self._my_config_option)

    ...
```
The corresponding module section in the config file would look like:
```yaml
global:
    ...

gui:
    ...

hardware:
    ...

logic:
    example_logic_identifier_name:
        module.Class: my_example_logic.MyExampleLogic
        options:
            my_config_option: 'I am a string from the qudi configuration'
        connect:
            ...
    ...
```

#### name
Please note here that the variable name in the measurement module definition is `_my_config_option`,
while the name given in the config file is `my_config_option` (without underscore). This is 
possible because of the optional `name` argument of `ConfigOption`. This argument specifies the 
field name of the config option in the qudi configuration and can be any YAML-compatible string as 
long as it is unique within a measurement module.

#### default
This example is also defining an optional `default` value for the config option. If you specify a 
default value, this config option is considered optional, i.e. if you do not provide the config 
option via qudi configuration, it will be initialized to this default value instead.  
Non-optional config options (omitting the `default` argument) will cause the measurement module to 
raise an exception during initialization if the corresponding field is not specified in the qudi 
configuration.

#### missing
The optional `missing` argument can be used to define the behaviour in case the config option is 
missing from the configuration and has a default value. Ignored for non-optional config options.  
Possible argument values are:

| value           | effect                                                                                    |
| --------------- | ----------------------------------------------------------------------------------------- |
| `'nothing'`     | Silently use the default value.                                                           |
| `'info'`        | Use default value but also logs an info message about the missing config option.          |
| `'warn'`        | Use default value but also logs a warning about the missing config option.                |
| `'error'`       | Fail to initialize the module with an exception. Same as for non-optional config options. |

#### checker
If you want to establish sanity checking for your config option at module initialization, you can 
provide a static function to the optional `checker` argument of `ConfigOption`.  
This function should accept a single argument (the configured value coming from the YAML loader) 
and return a boolean indicating if the check has passed (`True`) or not.

#### constructor
Since config options must be provided via YAML format you are limited in what data types can be 
configured. The qudi YAML loader currently supports any native Python builtin type and numpy arrays.

If your config option should be of any other type, you need to provide a `constructor` function to 
the `ConfigOption` meta object.  
This function must accept the simple YAML data and return converted data that is then used to 
initialize the module data member.  
You can provide a callable as `constructor` argument to `ConfigOption` or you can register a 
callable member of your measurement module as such via decorator, e.g.:
```python
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase

class FancyDataType:
    def __init__(self, a, b):
        self.a = a
        self.b = b


class MyExampleLogic(LogicBase):
    """ Module description goes here """
    
    _my_config_option = ConfigOption(name='my_config_option')
    _my_other_config_option = ConfigOption(name='my_other_config_option',
                                           constructor=lambda yaml_data: FancyDataType(*yaml_data))
    
    ...

    @_my_config_option.constructor
    def my_config_option_constructor(self, yaml_data):
        return FancyDataType(*yaml_data)

    ...
```
Since the `constructor` function is usually static (as the example above also shows), you could 
combine that with the `@staticmethod` decorator. But this is not necessary and just good style.

---

[index](../index.md)
