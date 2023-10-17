# Remote Modules

Qudi supports accessing modules of a qudi instance that is running on a different (remote) computer within the same LAN. A possible configuration for this looks like:

### Server


    global:
        remote_modules_server:
            address: "ip.address.of.this.machine"
            port: port_of_the_server(int)
          
    hardware:
        name_of_hardware:
            module.class: "hardwarefile.classname"
            allow_remote: True
            options:
                ...

### Client

    global:
        force_remote_calls_by_value: True
        # If this flag is set (True), all arguments passed to qudi module APIs from remote
        # (jupyter notebook, qudi console, remote modules) will be wrapped and passed "per value"
        # (serialized and de-serialized). This is avoiding a lot of inconveniences with using numpy in
        # remote clients.
        # If you do not want to use this workaround and know what you are doing, you can disable this
        # feature by setting this flag to False.

    hardware:
        remote_hardware:
            native_module_name: "name of module in server's config file"
            address: "ip.address.of.remote.hardware.server"
            port: port_of_remote_hardware_server(int)

For a  more elaborate explanation refer to the [configuration documentation](https://github.com/Ulm-IQO/qudi-core/blob/main/docs/design_concepts/configuration.md).
Moreover, subsequent processing of python objects in a corresponding logic on the client side may need a preliminary netobtain, which migth look like this:
    
    from qudi.util.network import netobtain
    ...
    data = ...get_data_from_remote_hardware()
    data = netobatin(data)

For a detailed explanation refer to the rpyc (netref) [documentation](https://rpyc.readthedocs.io/en/latest/index.html).

In case you can not access your remote module, it might be also worth checking your firewall settings and the ethernet adapter settings (public/private network) of your machines.
