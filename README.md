# qudi-core [![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

The qudi-core installation provides a versatile framework for modular multi-instrument and multi-computer measurement applications.
It enables scientists and engineers to easily develop specialized multithreaded graphical or non-graphical applications. 
Most of the more technical details about a complex measurement suite are handled automatically by the qudi-core so the developer can focus on what matters most... the measurement logic and the optional user interface.

An incomplete list of functionality the qudi-core provides:
- logging
- thread management
- automatic app status dumping/loading
- runtime resource management
- Python module structure
- support for installable `qudi` package addons
- interactive local IPython kernel interface
- high-level automation framework via tasks/scripts
- measurement setup configuration via YAML config file
- various tooling as a Python library
- basic data storage facility

## Installation
For installation instructions please refer to our 
[qudi installation guide](docs/setup/installation.md).

## Citation
If you are publishing scientific results, mentioning Qudi in your methods decscription is the least you can do as good scientific practice.
You should cite our paper [Qudi: A modular python suite for experiment control and data processing](http://doi.org/10.1016/j.softx.2017.02.001) for this purpose.

## Documentation
The official qudi documentation homepage can be found [here](https://ulm-iqo.github.io/qudi-core/).

## Collaboration
For development-related questions and discussion, please use the [qudi-dev mailing list](http://www.freelists.org/list/qudi-dev).

If you just want updates about releases and breaking changes to Qudi without discussion or issue reports,
subscribe to the [qudi-announce mailing list](http://www.freelists.org/list/qudi-announce).

Feel free to add issues and pull requests for improvements on github [here](https://github.com/Ulm-IQO/qudi-core/issues).

The code in pull requests should be clean, PEP8-compliant and commented, as with every academic institution in Germany,
our resources in the area of software development are quite limited.

Do not expect help, debugging efforts or other support.

## License

Almost all parts of Qudi are licensed under GNU Lesser General Public License Version 3 a.k.a. 
LGPLv3 (see [LICENSE](LICENSE) and [LICENSE.LESSER](LICENSE.LESSER)) with the exception of some 
files that originate from the Jupyter/IPython project. These are under BSD license, check the file 
headers and the documentation folder.

Check [AUTHORS.md](AUTHORS.md) for a list of authors and the git history for their individual 
contributions.
