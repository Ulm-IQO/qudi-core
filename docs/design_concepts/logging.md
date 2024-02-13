---
layout: default
title: qudi-core
---

[index](../index.md)

---

# Logging
Qudi uses the `logging` module from the Python standard library to manage log messages. Please 
refer to the [official Python documentation](https://docs.python.org/3/library/logging.html) to get 
familiar with the concept.

Running qudi will initialize the `qudi.core.logger` module which configures the `logging` module 
settings and installs log handlers in order to centrally manage all log messages.  

All log records are displayed in the qudi main window where they can also be filtered.  
Log messages of level "error" or higher will additionally trigger a modal error dialog pop-up 
displaying the error message and traceback.

> **⚠ WARNING:**
> 
> Qudi additionally installs a global `sys.excepthook` handler to catch all unhandled exceptions 
> and prevent the application from terminating.
> 
> All exceptions handled that way are diverted to the qudi logging facility with logging level 
> "error".

Furthermore, all log records are written into a text file located in the qudi subdirectory of the 
user home directory (OS dependent). The log files of the last 5 qudi sessions are preserved. 

## Levels
The predefined most common logging levels are the same as described in the `logging` package 
documentation:

| Level Name | Numeric Value |
| ---------: | ------------- |
| critical   | 50            |
| error      | 40            |
| warn       | 30            |
| info       | 20            |
| debug      | 10            |

### critical
When a log record of level "critical" and higher is detected qudi will immediately attempt to kill 
all running tasks and processes.

In 99.99% of the cases there should be no reason to log a record of this level. So don't do it 
unless you have very good reasons and know what you are doing.

### error
Records of level "error" or higher should usually only be logged while handling an exception 
(see: [exception handling guidelines](../404.md)).

Unhandled exceptions will automatically be logged on the "error" level.

### warn
Warning messages can be used as a tool by application programmers to point out possible problems, 
e.g. an occurring edge case that is not yet well handled and often leads to errors.

### info
Info messages should be used by an application programmer to inform the user of major events or 
milestones in the intended program execution flow.  

> **⚠ WARNING:**
> 
> There is a fine line between spam and useful information density.  
> Think carefully what to log and use "debug" level while developing code and debugging.

### debug
Use debug messages for information only interesting for programmers, e.g. to simplify debugging.
Records of this level and below are ignored by default and are not logged unless you run qudi in 
debug mode (command line argument `--debug`).

## Usage
The usual way to create a log record is to get a `logging.Logger` instance and call the level names 
on it with the desired log message as argument, i.e.:
```python
<logger>.debug('my debug message')
<logger>.info('my info message')
<logger>.warn('my warning message')
<logger>.error('my error message')
<logger>.critical('my critical message')
```
 For this purpose you want to include the 
traceback in the log record. You can do this easily by calling `exception` on the logger instance:
```python
try:
    0/0
except ZeroDivisionError:
    # This will include the traceback in the log record:
    <logger>.exception('There was an exception while trying to divide two numbers')
```

### qudi Measurement Modules
The base class of any [qudi measurement module](measurement_modules.md) already provides you with 
an appropriate `Logger` object that can be accessed with the `log` property:
```python
from qudi.core.module import LogicBase

class MyExampleLogic(LogicBase):
    """ Module description goes here """
    
    ...

    def add_numbers(self, x, y):
        """ Just a basic example method to add two numbers and log an info message. """
        result = x + y
        self.log.info(f'Just added two number {x} and {y} resulting in {result}')
        return result
    
    ...
```

### Other modules
For any module that is not a qudi measurement module but part of the `qudi` package namespace, you 
should use `get_logger` from `qudi.core.logger` and initialize the logger with the modules 
`__name__` attribute:
```python
from qudi.core.logger import get_logger

logger = get_logger(__name__)
logger.info('Module initialized')  # create example log record
```
For any other Python module you can simply get a `Logger` object as described in the 
[official Python documentation](https://docs.python.org/3/library/logging.html):
```python
from logging import getLogger

logger = getLogger(__name__)
logger.info('Module initialized')  # create example log record
```

---

[index](../index.md)
