---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Connectors

WORK IN PROGRESS

Calling a connector will return a reference to the connected module instance. More precisely, it 
will return a transparent object proxy to said module instance in order to hide the fact that 
modules should not own strong references on other modules. But this is an implementation detail.  
In case of [interface overloading](../404.md) this proxy will also provide access to the other 
modules members via the right interface. 

# Connector list

A connector list behaves as a list. Calling the attribute with an index
parameter will return the connected module instance to mimic the behavior of a
normal connector. However, you can also simply index the attribute as a normal
iterable.

An example use of `ConnectorList` would be to mutliplex an arbitrary number of
hardwares together. Here is a short version of the demo available [here](https://github.com/Klafyvel/test-qudi-connectorlist):
```python
from qudi.interface.switch_interface import SwitchInterface
from qudi.core.configoption import ConfigOption
from qudi.core.connector import ConnectorList

class MultiSwitch(SwitchInterface):
    switches = ConnectorList(interface="SwitchInterface")
    _hardware_name = ConfigOption(name='name', default=None, missing='nothing')
    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self.module_name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        new_dict = dict()
        for switchinstance in self.switches:
            new_dict.update(switchinstance.available_states)
        return new_dict

    @property
    def number_of_switches(self):
        """ Number of switches provided by the hardware.

        @return int: number of switches
        """
        return sum(switch.number_of_switches for switch in self.switches)

    @property
    def switch_names(self):
        """ Names of all available switches as tuple.

        @return str[]: Tuple of strings of available switch names.
        """
        return tuple(self.available_states)

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        new_dict = dict()
        for switchinstance in self.switches:
            new_dict.update(switchinstance.states)
        return new_dict

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        assert isinstance(state_dict,
                          dict), f'Property "state" must be dict type. Received: {type(state_dict)}'
        for switch, state in state_dict.items():
            switchname = ""
            hardware = None
            for hw in self.switches:
                hardware = hw
                switchname = switch
                break
            hardware.set_state(switchname, state)

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        for hw in self.switches:
            if switch in hw.available_states:
                return hw.get_state(switch)

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        for hw in self.switches:
            if switch in hw.available_states:
                return hw.get_state(switch, state)
```

---

[index](../index.md)
