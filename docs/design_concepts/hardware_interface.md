---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Hardware Interface
When we talk about an "interface" in the context of qudi, mean the hardware interface classes 
usually located in `qudi.interface`.

An interface is an [abstract class](https://en.wikipedia.org/wiki/Abstract_type) and a subclass of 
the module `Base` class. It defines a set of abstract methods and properties.  
These classes can not be instantiated directly (thus "abstract"). Instead they must be subclassed.

In order for the subclass to work and not be abstract itself, it needs to implement all the 
abstract members of the interface class it inherits.  
So every class that inherits the same interface is guaranteed to provide at least the set of 
methods and properties defined in the interface.

Since the interface subclass that implements all the abstract members is also a subclass of `Base`,
this class is then called a [hardware module](../404.md).

<!-- This link to the IQO modules needs to be updated once that documentation is up -->
See also the detailed [qudi modules](https://github.com/Ulm-IQO/qudi-iqo-modules/blob/main/docs/installation_guide.md) documentation if you want to know more about 
what defines a qudi module and the respective inheritance trees.

It's always good to have a look at some example... so here is a simple interface class for you.

## Example Interface:
```python
from abc import abstractmethod
from qudi.core import Base

class MySimpleInterface(Base):
    """ Interface description and license/copyright header goes here
    """
    @abstractmethod
    def read_value(self) -> float:
        """ Reads a value from the instrument and returns it
        """
        pass
    
    @property
    @abstractmethod
    def some_setting(self) -> int:
        """ Property holding some integer type setting in the instrument 
        """
        pass
    
    @some_setting.setter
    def some_setting(self, value: int) -> None:
        """ Setter for property "some_setting" 
        """
        pass
```
> **⚠ WARNING:**
> 
> Note the order of decorators when declaring an abstract property. You can not exchange 
> `@property` and `@abstractmethod`!

This interface declares a method `read_value` and a read/write property `some_setting`. 
Note also that it inherits `Base`.

An actual hardware module implementation satisfying this interface could look like below, assuming 
you placed the above code in `qudi/interface/my_simple_interface.py`.
## Hardware Implementation:
```python
from qudi.interface.my_simple_interface import MySimpleInterface

class MySimpleInstrument(MySimpleInterface):
    """ Hardware module description and license/copyright header goes here
    """
        
    def on_activate(self):
        """ Initialize module upon activation """
        # Perform any module initialization here, e.g. establish a connection to the instrument etc.
        ...
        
    def on_deactivate(self):
        """ Perform module cleanup upon deactivation """
        # Clean up your module and free all resources, e.g. terminate the instrument connection
        ...

    def read_value(self) -> float:
        """ Reads a value from the instrument and returns it """
        value = ...  # Read a value from the instrument
        return value
    
    @property
    def some_setting(self) -> int:
        """ Property holding some integer type setting in the instrument """
        value = ...  # Retrieve the setting value from the instrument
        return value
    
    @some_setting.setter
    def some_setting(self, value: int) -> None:
        """ Setter for property <some_setting> """
        ...  # Perform some sanity checking apply the new setting value to the instrument
```

Please note that in addition to the interface members you also needed to implement `on_activate` 
and `on_deactivate` which are abstract methods inherited from the `Base` class.

Implementing the members shown above is the bare minimum the hardware class needs to provide.  
Of course, you can always implement additional members (helper methods etc.) to structure your 
class in accordance with good programming practices.

> **⚠ WARNING:**
> 
> Other qudi modules that connect to a hardware class through an interface must only ever use/call 
> the members declared in the interface. All additional members must only ever be used by the 
> hardware class internally. Consequentially, you should consider making them protected or even 
> private, i.e. add single `_` or double underscore `__` name prefix, respectively. 

## Why Do All This?
An abstract interface class defines a common set of methods and properties to control and monitor a 
certain generalized type of hardware (CW microwave sources, lasers, AWGs, etc.).

Logic modules that orchestrate instruments via hardware modules usually just define what kind of 
interface they want to use and not the specific hardware module, i.e. they require a general type 
of hardware without explicitly specifying a specific device model.

This has the advantage that you can exchange your instruments with various devices of the same 
hardware type without changing the code for your experiment procedure (i.e. the logic modules). 
As long as all hardware modules use the same interface, you can freely exchange them in the config 
while GUI and logic modules will work just the same.  
This is also called "hardware abstraction".

---

[index](../index.md)
