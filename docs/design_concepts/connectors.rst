`index <../index.md>`__

--------------

Connectors
==========

WORK IN PROGRESS

| Calling a connector will return a reference to the connected module
  instance. More precisely, it will return a transparent object proxy to
  said module instance in order to hide the fact that modules should not
  own strong references on other modules. But this is an implementation
  detail.
| In case of `interface overloading <../404.md>`__ this proxy will also
  provide access to the other modules members via the right interface.

--------------

`index <../index.md>`__
