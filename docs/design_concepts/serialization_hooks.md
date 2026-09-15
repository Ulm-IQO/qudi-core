---
title: qudi-core | A framework for modular measurement applications
---

[index](../index.md)

---

# Serialization Hooks

When qudi stores data — most commonly [status variables](status_variables.md) —
it serializes to YAML, which only understands native Python builtins and numpy
arrays. Any custom type must first be converted to and from those simple forms.

For a one-off type, the `constructor`/`representer` of a
[`StatusVar`](status_variables.md) suffice. For a type reused across modules,
qudi provides a shared conversion layer built on [cattrs](https://catt.rs): you
write one **hook** per type, and it is registered by discovery rather than as an
import-time side effect, so the conversion is available regardless of which
modules are imported.

## Concepts

A **hook** converts one custom type in two directions:

- `unstructure`: custom object → YAML-safe primitive.
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

> **NOTE:** cattrs already handles dataclasses, enums, and standard containers.
> You only need a hook for genuinely custom classes, or to override a default.

## Using the converter

```python
from qudi.util.hook import CattrsConverter

converter = CattrsConverter().converter

primitive = converter.unstructure(FancyDataType(42, 3.1415))
obj = converter.structure([42, 3.1415], FancyDataType)
```

Inside a `StatusVar`, the hook replaces a hand-written `constructor`/`representer`
pair. Since the `StatusVar` declares the type, the stored data stays tagless:

```python
converter = CattrsConverter().converter

_my_status_variable = StatusVar(
    default=FancyDataType(1, 2),
    constructor=lambda value: converter.structure(value, FancyDataType),
    representer=lambda value: converter.unstructure(value),
)
```

## Notes and gotchas

- **A target type is required.** A hook only converts when the converter knows
  the target — from a `StatusVar` declaration or an enclosing hook. This is why
  hooks stay tagless.
- **Hooks compose with the YAML layer.** cattrs reduces an object to primitives;
  `qudi.util.yaml` still does the final primitive-to-text step (e.g. numpy array
  encoding in the sample hook). A pass-through hook (`return obj`) just defers a type to that layer.
- **A `constructor` opts a `StatusVar` out of type reconciliation.** Reconciliation
  runs only for status variables without a `constructor`, so wiring a hook into
  one disables it for that variable — relevant for dict-valued status variables.

---

[index](../index.md)