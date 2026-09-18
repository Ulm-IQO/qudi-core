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

A **hook** converts one custom type in two directions:

- `unstructure`: custom object → serializable primitive.
- `structure`: primitive → custom object.

It is a subclass of `qudi.util.hook.Hook` that sets `target` to the type it
handles and implements both methods.

The converter, `qudi.util.hook.CattrsConverter`, discovers every `Hook` subclass
in the `qudi.util.hooks` namespace, registers them on a single cattrs
`Converter`, and exposes it via `.converter`.

## Writing a hook

Place a `Hook` subclass in the `qudi.util.hooks` namespace:

```python
from __future__ import annotations
from qudi.util.hook import Hook

class FancyDataTypeHook(Hook):
    target = FancyDataType

    def unstructure(self, obj):
        return [obj.a, obj.b]

    def structure(self, value, type_):
        return FancyDataType(*value)
```

That is the whole registration — no manual `register(...)` call and no YAML tag.
`CattrsConverter` finds the hook by scanning the namespace.

## Using the converter

```python
from qudi.util.hook import CattrsConverter

converter = CattrsConverter().converter

primitive = converter.unstructure(FancyDataType(42, 3.1415))
obj = converter.structure([42, 3.1415], FancyDataType)
```


```python
converter = CattrsConverter().converter

_my_status_variable = StatusVar(
    default=FancyDataType(1, 2),
    constructor=lambda value: converter.structure(value, FancyDataType),
    representer=lambda value: converter.unstructure(value),
)
```

---

[index](../index.md)
