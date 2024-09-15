---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Configuration

Since qudi is a very modular and versatile application, it is only natural to have means of 
customizing a qudi session.  
This customization or configuration is done once at startup of each qudi session by parsing a 
configuration text file. It contains global constants/settings as well as the custom naming 
and setting for each qudi module to be used and instructions on how to interconnect them. What 
qudi modules you have available during a qudi session is therefore defined by this configuration.

Because the configuration file is just parsed once during startup, the qudi configuration should be 
considered static and constant during a qudi session and is not to be altered during runtime.

## File Format
The configuration file is a text file in [YAML](https://en.wikipedia.org/wiki/YAML) format with 
filename extension `.cfg`.  
Qudi implements a relaxed syntax for YAML - straying a bit from the official specifications - in 
order to allow more verbose Python input (e.g. `True` in addition to `true`).

Non-mandatory properties with default values are automatically inserted upon file parsing.

The content is structured as a nested mapping with string keys and is divided into 2 main parts:

### Global Section
This section contains all settings that are not tied to a specific qudi module. It contains some 
predefined properties with default values but currently none of them is required to be provided by 
the config file. It is also allowed to add additional properties to this section by simply 
incorporating them in the config file.

The default content of the `global` section looks as follows:
```yaml
global:
    startup_modules: []
    remote_modules_server: null
    namespace_server_port: 18861
    force_remote_calls_by_value: True
    hide_manager_window: False
    stylesheet: 'qdark.qss'
    default_data_dir: null
    daily_data_dirs: True
    extension_paths: []
```
Please note that the above content will be created even if leave out the `global` section entirely.

Let's give a rundown on each default property:

#### startup_modules
This is an optional list of configured module (gui/logic/hardware) name strings. More detail on the 
module names can be found further down in the ["modules sections"](#modules-sections) section.

Each module in that list will be automatically loaded and activated after qudi startup.

Please note that it is sufficient to just state the highest-level module you want to automatically 
activate and _**not**_ all dependencies as well. E.g. if you want to automatically load a 
certain measurement toolchain at qudi startup, it is enough to just give the name of the 
corresponding GUI module.

Example:
```yaml
global:
    startup_modules:
        - 'my_gui_module'

gui:
    my_gui_module:
        ...
```

#### remote_modules_server
If you want to expose qudi modules running on the local machine to networked remote qudi instances, 
you need to specify the server settings with this property.
By default this property will be `null`, meaning the remote module server is disabled.  
Please note that you are still able to connect to remote running qudi modules even if the local 
remote modules server is disabled (as long as the remote qudi instance has a server running of 
course).

> **⚠ WARNING:**
> 
> It is highly recommended to use closed local area networks to communicate between different qudi 
> instances due to security reasons.  
> The connection of qudi modules using SSL is still very experimental and secure connections can not 
> be guaranteed.
> 
> If you want to use SSL encryption, you need to generate client and server certificates with an 
> external tool.

In case you want to serve local modules to other qudi instances, the server configuration is a 
mapping with the following properties:

| property   | type             | description                                                                                                                         |
|:-----------|:-----------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `address`  | `str`            | Host name of the server to be reached with. <br/>If you want to serve only local qudi instances, you can set this to `'localhost'`. |
| `port`     | `int`            | Port number to bind the server to.                                                                                                  |
| `certfile` | `Optional[str]`  | Path to the SSL certificate file to use for connection encryption. Unsecured if omitted.                                            |
| `keyfile`  | `Optional[str]`  | Path to the SSL key file to use for connection encryption. Unsecured if omitted.                                                    |

Example:
```yaml
global:
    remote_modules_server:
        address: '192.168.1.100'
        port: 12345
        certfile: '/path/to/certfile.cert'  # omit for unsecured
        keyfile: '/path/to/keyfile.key'     # omit for unsecured
```

#### namespace_server_port
Qudi namespace server port number (`int`) to bind to.  
The qudi namespace server is similar to the remote modules server except it always runs only on 
`localhost` and is unencrypted. It serves as interface to qudi for local running IPython kernels 
(Jupyter notebooks, qudi console, etc.).

#### force_remote_calls_by_value
Boolean flag to enable (`True`) or disable (`False`) all arguments passed to qudi module APIs from 
remote (jupyter notebook, qudi console, remote modules) to be wrapped and passed "by value" 
(serialized and de-serialized) instead of "by reference". This is avoiding a lot of inconveniences 
with using `numpy` in remote clients.

By default this feature is enabled but if you know what you are doing you can unset this flag.

#### hide_manager_window
Optional boolean flag to hide the qudi manager window upon startup. This can be useful in tandem 
with the `startup_modules` property to restrict GUI access.

#### stylesheet
Full path or filename (`str`) to a Qt compatible QSS stylesheet to be used for this qudi session.
If only a filename is given, qudi assumes to find this file in `qudi.artwork.styles`.

#### default_data_dir
If given an absolute directory path (`str`), it overwrites the default root directory for qudi to 
store measurement data in (assuming used data storage is file system based).

By default qudi is using `<user home>/qudi/Data/` as data root directory.

Example:
```yaml
global:
    default_data_dir: 'C:\\Data\\'
```

#### daily_data_dirs
Boolean flag used by some file based data storage methods to determine if daily data 
sub-directories should be automatically created.

#### extension_paths
List of absolute paths (`str`) to be inserted to the beginning of `sys.path` at runtime in order to 
overwrite module import path resolution with custom locations.

> **⚠ WARNING:**
> 
> This feature is deprecated and will be removed in future releases of `qudi-core` because it is 
> unpredictable and causes more harm than it does good.
> 
> Since `qudi-core v1.0.0` `qudi` is a proper namespace package that can be extended by installing 
> more modules into it via e.g. `pip`.

### Modules Sections
The second part of the config file is actually divided into 3 properties with the same structure 
configuring `gui`, `logic` and `hardware` modules to be available in the qudi session.

Each qudi module configured must be given a name which must be unique throughout the configuration.
This name string will be the property name under the respective qudi module category 
(`gui`, `logic`, `hardware`) containing the module-specific configuration.  
Module names must not start with a number and contain only ASCII word characters (standard letters 
a-z, number digits and underscores).

The individual module configuration must follow one of two possible structures:

#### Local Module
Local modules are modules to be run natively in the qudi instance configured by this config file. 
This is the "normal" way to configure a module and each module used in a network of qudi instances 
must be configured like this in exactly one qudi instance.

An example for a minimum local logic module configuration looks like this:
```yaml
logic:
    my_module:  # unique custom name for this module
        module.Class: 'my_module.MyModuleClass'
```
In this example the respective `qudi.core.module.LogicBase` subclass is called `MyModuleClass` and 
can be imported from `qudi.logic.my_module`.

If you are running a remote modules server to make a qudi module available to a remote qudi 
instance, you need to flag each module that should be accessible from remote.  
To do so you need to set the module config property `allow_remote` to `True` (it is `False` by default):
```yaml
logic:
    my_module:  # unique custom name for this module
        module.Class: 'my_module.MyModuleClass'
        allow_remote: True
```

In order to interface different modules with each other, qudi modules are employing a meta-object 
called a `Connector` ([more details here](connectors.md)).  
If the logic module in our example needs to be connected to other modules (logic or hardware), you 
have to specify this in the module configuration as well. The modules to connect to are addressed 
by their module names given in the same config:
```yaml
logic:
    my_module:
        module.Class: 'my_module.MyModuleClass'
        connect:
            my_connector_name: 'my_other_module'  
```

Now in order to configure static variables in the module configuration qudi modules use 
`ConfigOption` meta-objects ([more details here](config_options.md)).  
If the logic module in our example needs to have options configured, you have to specify this in 
the module configuration as well. The name of the config option is determined by the respective 
`ConfigOption` meta attribute in the qudi module class:
```yaml
logic:
    my_module:
        module.Class: 'my_module.MyModuleClass'
        connect:
            my_connector_name: 'my_other_module'
        options:
            my_first_config_option: 'hello world'
            my_second_config_option:
                - 42
                - 123.456
                - ['a', 'b', 'c']
```

#### Remote Module
A remote module is declared in its respective local qudi instance as local module of course. But if 
you are configuring a qudi instance to connect to a module running in another remote qudi instance, 
you need to specify that properly.  
When naming a remote qudi module you can do so without regarding the original module name in its 
local qudi instance configuration.

Contrary to a local module you can not configure options or connections in remote modules (this is 
done in their respective local qudi config). The only thing you have to configure is the network 
connection details (address and port), the native module name on the remote qudi instance and, in 
case the connection is SSL secured, also key and certificate file paths:

```yaml
hardware:
    my_remote_module:
        native_module_name: 'module_name_on_remote_host'
        address: '192.168.1.100'
        port: 12345
        certfile: '/path/to/certfile.cert'                  # omit for unsecured
        keyfile: '/path/to/keyfile.key'                     # omit for unsecured
```

As you can probably see, the config looks very much like the `remote_module_server` global config 
entry [above](#remote_modules_server). In fact the `address` and `port` items must mirror the 
`remote_module_server` config on the remote qudi instance to connect to.


## Validation
Generally you should be able to express any property in the config as one of these types:
- scalar (`float`, `int`, `str`, `bool`, `null`)
- sequence (`list`)
- mapping (`dict`) 

Of course you can also nest sequences and mappings.

Validation, type checking and default value insertion is performed via 
[JSON Schema](https://json-schema.org/) 
([Draft-07](https://json-schema.org/draft-07/json-schema-release-notes.html)) each time a config 
file is loaded or dumped.  
The schema to be used can be found in 
[`qudi.core.config.schema`](https://github.com/Ulm-IQO/qudi-core/blob/config-refactoring/src/qudi/core/config/schema.py).


## Graphical Configuration Editor

> **⚠ WARNING:**
> 
> The graphical configuration editor is still in an early development phase and may not be 
> functional yet.
> 
> When starting the editor you will probably encounter a long series of warnings and errors coming 
> from qudi module imports.  
> This is expected behaviour and should not influence the functionality 
> of the editor. In the future these errors will be properly handled behind the scenes.

You can start a standalone graphical qudi configuration editor currently in two different ways:

1. By running `qudi-config-editor` inside your qudi Python environment:
   ```console
   (qudi-venv) C:\> qudi-config-editor
   ```
2. By executing the runnable qudi module `qudi.tools.config_editor` inside your qudi Python 
environment:
   ```console
   (qudi-venv) C:\Software\qudi-core\src\qudi\tools\> python -m config_editor
   ```

---

[index](../index.md)
