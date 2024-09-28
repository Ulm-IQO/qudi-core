Changelog
=========

Pre-Release
-----------

Breaking Changes
~~~~~~~~~~~~~~~~

None

Bugfixes
~~~~~~~~

None

New Features
~~~~~~~~~~~~

None

Other
~~~~~

None

Version 1.5.0
-------------

Released on 16.11.2023

.. _breaking-changes-1:

Breaking Changes
~~~~~~~~~~~~~~~~

None

.. _bugfixes-1:

Bugfixes
~~~~~~~~

-  Fixes a bug where all fit configurations for a fit model/container
   fail to load upon activation of a module because the fit model saved
   in AppData is no longer available. Throws a warning now instead and
   ignores the respective fit configuration.
-  Fixed a bug that caused ``qudi.util.models.DictTableModel`` to raise
   ``IndexError`` when used in a ``ListView`` and/or when data at index
   zero is requested.

.. _new-features-1:

New Features
~~~~~~~~~~~~

-  Added helper functions in util/linear_transform.py to allow
   transformations (rotations and shifts) using the afﬁne transformation
   matrix formalism.

.. _other-1:

Other
~~~~~

-  Fine-tuning of string output of fit results from
   qudi.util.units.create_formatted_output(): Failed fits should provide
   error= np.nan. Fixed parameters are marked as such. Brackets
   introduced, eg. (2.67 ± 0.01) GHz.

Version 1.4.1
-------------

Released on 21.06.2023

.. _breaking-changes-2:

Breaking Changes
~~~~~~~~~~~~~~~~

None

.. _bugfixes-2:

Bugfixes
~~~~~~~~

None

.. _new-features-2:

New Features
~~~~~~~~~~~~

-  Added utility descriptor objects to new module
   ``qudi.util.descriptors``. Can be used to facilitate smart instance
   attribute handling.

.. _other-2:

Other
~~~~~

-  Support for Python 3.10
-  Better backwards compatibility of
   ``qudi.util.constraints.ScalarConstraint`` with the deprecated
   ``qudi.core.interface.ScalarConstraint`` object

Version 1.3.0
-------------

Released on 20.12.2022

.. _breaking-changes-3:

Breaking Changes
~~~~~~~~~~~~~~~~

None

.. _bugfixes-3:

Bugfixes
~~~~~~~~

-  NULL bytes in log messages are handled now and no longer lead to
   crashes of qudi. They are replaced by the corresponding hex literal
   “:raw-latex:`\x00`”.
-  Rubberband selection of utility plot widgets now works for
   ``pyqtgraph != 0.12.4``. This specific version is broken in that
   regard and a comprehensive error is thrown if it is detected.
-  Adjusted 2D gaussian fit arguments to be compatible with the
   datafitting toolchain.

.. _new-features-3:

New Features
~~~~~~~~~~~~

-  Multiple qudi sessions can now be run in parallel locally. However,
   the user must ensure non-conflicting socket server settings for
   namespace server and remote module server in the configs to load.

.. _other-3:

Other
~~~~~

-  Bumped minimum package requirement ``pyqtgraph >= 0.13.0``.
-  Introduced properties to make
   ``qudi.util.constraints.ScalarConstraint`` mostly backwards
   compatible with the deprecated
   ``qudi.core.interface.ScalarConstraint``. Only exception is ``unit``
   which should not be supported anymore.

Version 1.2.0
-------------

Released on 30.09.2022

.. _breaking-changes-4:

Breaking Changes
~~~~~~~~~~~~~~~~

None

.. _bugfixes-4:

Bugfixes
~~~~~~~~

None

.. _new-features-4:

New Features
~~~~~~~~~~~~

-  New general-purpose interactive data display widget
   ``qudi.util.widgets.plotting.interactive_curve.InteractiveCurvesWidget``
   providing multiple optional features:

   -  Legend creation and generic dataset naming
   -  Linking of fit curve to dataset and synchronous handling of both
   -  Rubberband zooming in 1 and 2 dimensions
   -  Data markers in 1 and 2 dimensions
   -  Data range selections in 1 and 2 dimensions
   -  Checkbox-based toggling of dataset visibility
   -  Plot editor for setting axis labels, units and view ranges
   -  Mouse cursor tracking and display in data coordinates
   -  Various signals to interface with the above-mentioned features

.. _other-4:

Other
~~~~~

None

Version 1.1.0
-------------

Released on 25.07.2022

.. _breaking-changes-5:

Breaking Changes
~~~~~~~~~~~~~~~~

-  Changed event handling of qudi module state machine.
   ``on_deactivate`` will be run BEFORE the state machine actually
   changes into state ``deactivated``.

-  | ``ConfigOption`` meta-attributes of qudi modules are no longer set
     in config under the module name section directly, but must be
     specified in an ``options`` subsection instead.
   | So something like

   .. code:: python

      my_module_name:
          module.Class: 'qudi.hardware.my_module.MyModule'
          first_option: 42
          second_option: 'hello world'

   must become now

   .. code:: python

      my_module_name:
          module.Class: 'qudi.hardware.my_module.MyModule'
          options:
              first_option: 42
              second_option: 'hello world'

.. _bugfixes-5:

Bugfixes
~~~~~~~~

-  Qudi logging facility active during startup procedure
-  Reduced RPyC related errors in qudi IPython kernel

.. _new-features-5:

New Features
~~~~~~~~~~~~

-  Support for ``enum.Enum`` types in ``qudi.util.yaml``, enabling use
   of enums in qudi config and status variables.
-  ``qudi.util.constraints.ScalarConstraint`` data class to easily
   define bounds for, check and clip scalar values.
-  Added qudi logger object to qudi IPython kernels to give users the
   possibility to directly log messages into qudi from e.g. a jupyter
   notebook.

.. _other-5:

Other
~~~~~

-  Structure and type checking as well as default value handling in the
   qudi configuration file is now done via JSON Schema (Draft-07). The
   applied schema is defined in ``qudi.core.config.schema``.
   Every time you load/dump a configuration from/to file or add/remove a
   module config or set a global config option using
   ``qudi.core.config.Configuration``, the config is validated against
   this JSON schema.
