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

    hardware:
        remote_hardware:
            native_module_name: "name of module in server's config file"
            address: "ip.address.of.remote.hardware.server"
            port: port_of_remote_hardware_server(int)
