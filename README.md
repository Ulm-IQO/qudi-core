# qudi-core
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
![PyPI release](https://github.com/Ulm-IQO/qudi-core/actions/workflows/release_pypi.yml/badge.svg)

---
The qudi-core repository represents the base installation for the `qudi` Python package.

It provides a versatile framework for modular multi-instrument and multi-computer measurement 
applications.
It enables scientists and engineers to easily develop specialized multithreaded graphical or 
non-graphical applications.

Most of the more technical details about a complex measurement suite are handled automatically by 
`qudi` so the developer can focus on what matters most... the measurement control logic and the 
optional graphical user interface.

An incomplete list of functionality `qudi` provides:
- logging
- thread management
- automatic app status dumping/loading
- runtime resource management
- base modules for hardware interfaces, measurement logics and graphical user interfaces
- inter-module communication
- support for installable `qudi` namespace package addons
- interactive local IPython kernel interface
- high-level automation framework via tasks/scripts
- measurement setup configuration via YAML config file
- various tooling as a Python library
- basic data storage facility
- ...

## Attribution
If you are publishing any work based on using qudi as a framework/tool it is good practice to 
mention the qudi project, e.g. in the methods description.

Even better, you could simply cite our initial publication about qudi:\
[Qudi: A modular python suite for experiment control and data processing](http://doi.org/10.1016/j.softx.2017.02.001)

The qudi contributors will appreciate this and it helps our open-source community to gain attention.
This will hopefully attract more people willing to help in improving the qudi project which in turn 
benefits everyone using this software. 

Thank you! 

## Installation
For installation instructions please refer to our 
[qudi installation guide](https://ulm-iqo.github.io/qudi-core/setup/installation.html).

## Documentation
The official qudi documentation homepage can be found [here](https://ulm-iqo.github.io/qudi-core/).

## Forum
For questions concerning qudi on any level, there is a [forum](https://github.com/Ulm-IQO/qudi-core/discussions) to discuss with the qudi community. Feel free to ask! 
If you found a bug and located it already, please note GitHub's [issue tracking](https://github.com/Ulm-IQO/qudi-core/issues) feature.

## Contributing
You want to contribute to the qudi project? Great! Please start by reading through our 
[contributing guideline]().

To file a bug report or feature request please open an 
[issue on GitHub](https://github.com/Ulm-IQO/qudi-core/issues).

To contribute source code to the qudi-core repository please open a 
[pull request on GitHub](https://github.com/Ulm-IQO/qudi-core/pulls).

[Issues](https://github.com/Ulm-IQO/qudi-core/issues) and 
[pull requests](https://github.com/Ulm-IQO/qudi-core/pulls) should be discussed openly in their 
respective comment sections on GitHub.\
For any other development-related questions or discussions please subscribe to and use our 
[qudi-dev mailing list](http://www.freelists.org/list/qudi-dev). Please also consider using 
[gists](https://gist.github.com/) to showcase and discuss topics publicly within the qudi community.

## News and Updates
We will occasionally inform the qudi community about releases and breaking changes (no discussions).

If you are using qudi and want to stay in the loop, please subscribe to our 
[qudi-announce mailing list](http://www.freelists.org/list/qudi-announce).

## License
Qudi is licensed under the 
[GNU Lesser General Public License Version 3 (LGPL v3)](https://www.gnu.org/licenses/lgpl-3.0.en.html).

A copy of the full license text can be found in the repository root directory in 
[LICENSE](LICENSE) and [LICENSE.LESSER](LICENSE.LESSER)

For more information please check the 
[license section in the qudi documentation](https://ulm-iqo.github.io/qudi-core/license.html). 

## Copyright
Check [AUTHORS.md](AUTHORS.md) for a list of authors and the git history for their individual 
contributions.
