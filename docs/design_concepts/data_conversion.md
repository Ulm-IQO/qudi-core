---
title: qudi-core | A framework for modular measurement applications
---

[index](../index.md)

---

# Serialization Hooks

When qudi stores/loads data (e.g. for [`StatusVar`](../design_concepts/status_variables.md) or [`DataStorage`](../core_elements/data_storage.md)) it needs to be serialized, most commonly into a standard Python data type so the storage interface can store/load the data.
This conversion is done centrally with the [cattrs](https://catt.rs) package so each storage interface can expect only a standardized format of data.
A lot of standard datatypes are supported out of the box, additionally this implementation offers the ability to add unstructure/structure hooks in the qudi namespace to also add more complex custom datatype serialization.

## Concepts

A cattrs hook converts one custom type in two directions:

- `unstructure`: custom object → serializable primitive.
- `structure`: primitive → custom object.

`qudi.util.data_conversion.ValueConverter` is the base class for all custom hooks that set `target` to the type they
handle and implement both methods.

`get_converter()` discovers every ValueConverter subclass in the qudi.util.value_converters namespace and registers it on a single shared cattrs Converter. The converter is built once, on first use, and reused afterwards.

## Writing a hook

Place a `ValueConverter` subclass in the `qudi.util.value_converters` namespace:

```python
from __future__ import annotations
from qudi.util.data_conversion import ValueConverter

class FancyDataTypeConverter(ValueConverter):
    target = FancyDataType

    def unstructure(self, obj):
        return [obj.a, obj.b]

    def structure(self, value, type_):
        return FancyDataType(*value)
```

That is the whole registration — no manual `register(...)` call and no YAML tag.
The converter object finds the hook by scanning the namespace.

## Using the converter
With the existing datetime converter , string values can be converted/structured to datetime objects

```python
from qudi.util.data_conversion import get_converter, structure
from datetime import datetime

conv = get_converter()

dt = "2026-05-21"

dt = conv.structure(dt, datetime)

```


```python
converter =  get_converter()

_my_status_variable = StatusVar(
    default=FancyDataType(1, 2),
    constructor=lambda value: converter.structure(value, FancyDataType),
    representer=lambda value: converter.unstructure(value),
)
```

---

[index](../index.md)
