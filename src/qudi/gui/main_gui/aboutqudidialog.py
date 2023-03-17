# -*- coding: utf-8 -*-
"""
This module contains a QWidgets.QDialog subclass representing an "about qudi" dialog.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-core/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from PySide2 import QtCore, QtWidgets


class AboutQudiDialog(QtWidgets.QDialog):
    """
    QWidgets.QDialog subclass representing an "about qudi" dialog
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)

        buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttonbox.setOrientation(QtCore.Qt.Horizontal)
        self.ok_button = buttonbox.button(buttonbox.Ok)
        self.ok_button.clicked.connect(self.accept)

        self.header_label = QtWidgets.QLabel('qudi')
        self.header_label.setObjectName('headerLabel')
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(20)
        self.header_label.setFont(font)
        self.version_label = QtWidgets.QLabel('Version number goes here...')
        self.version_label.setObjectName('versionLabel')
        self.version_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                   | QtCore.Qt.TextBrowserInteraction)
        self.version_label.setOpenExternalLinks(True)

        self.about_label = QtWidgets.QLabel('<html><head/><body><p>Qudi is a suite of tools for '
                                            'operating multi-instrument and multi-computer '
                                            'laboratory experiments. Originally built around a '
                                            'confocal fluorescence microscope experiments, it has '
                                            'grown to be a generally applicaple framework for '
                                            'controlling experiments.</p></body></html>')
        self.about_label.setWordWrap(True)
        self.about_label.setObjectName('aboutLabel')
        self.about_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                 | QtCore.Qt.TextBrowserInteraction)
        self.about_label.setOpenExternalLinks(True)

        self.credits_label = QtWidgets.QLabel(
            '<html><head/><body><p><span style=" text-decoration: underline;">Qudi was originally '
            'developed by the Institute for Quantum Optics at Ulm University. </span></p><p>'
            'Kay D. Jahnke</p><p><span style=" text-decoration: underline;">External Contributors:'
            '</span></p><p>Tobias Gehring, DTU Copenhagen</p><p>...</p></body></html>'
        )
        self.credits_label.setWordWrap(True)
        self.credits_label.setObjectName('creditsLabel')
        self.credits_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextBrowserInteraction
        )
        self.credits_label.setOpenExternalLinks(True)

        self.license_label = QtWidgets.QLabel(
            '<html>\n<head/>\n<body>\n<p><span style=" font-family:"monospace";">\n'
            'Qudi is free software: you can redistribute it and/or modify it under the terms '
            '<br/>\nof the GNU Lesser General Public License as published by the Free Software '
            'Foundation,<br/>\neither version 3 of the License, or (at your option) any later '
            'version.\n</span></p>\n<p><span style=" font-family:"monospace";">\nQudi is '
            'distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;<br/>\n'
            'without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR '
            'PURPOSE.<br/>\nSee the GNU Lesser General Public License for more details.<br/>\n'
            '</span>\n</p><p><span style=" font-family:"monospace";">\nYou should have received a '
            'copy of the GNU Lesser General Public License along with qudi.<br/>\nIf not, see\n'
            '</span>\n<a href="https://www.gnu.org/licenses/"><span style=" text-decoration: '
            'underline; color:#00ffff;">https://www.gnu.org/licenses/</span></a>.<br/>\n</p>\n'
            '<p><span style=" text-decoration: underline;">\nQudi is derived in parts from ACQ4, '
            'so here is its license:</span></p>\n<p><span style=" font-family:"monospace";">\n'
            'Permission is hereby granted, free of charge, to any person obtaining a copy <br/>\nof'
            ' this software and associated documentation files (the &quot;Software&quot;), to deal '
            '<br/>\nin the Software without restriction, including without limitation the rights '
            '<br/>\nto use, copy, modify, merge, publish, distribute, sublicense, and/or sell '
            '<br/>\ncopies of the Software, and to permit persons to whom the Software is <br/>\n'
            'furnished to do so, subject to the following conditions: <br/>\n<br/>\nThe above '
            'copyright notice and this permission notice shall be included in all <br/>\ncopies or '
            'substantial portions of the Software. <br/>\n<br/>\nTHE SOFTWARE IS PROVIDED &quot;AS '
            'IS&quot;, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR <br/>\nIMPLIED, INCLUDING BUT NOT '
            'LIMITED TO THE WARRANTIES OF MERCHANTABILITY, <br/>\nFITNESS FOR A PARTICULAR PURPOSE '
            'AND NONINFRINGEMENT. IN NO EVENT SHALL THE <br/>\nAUTHORS OR COPYRIGHT HOLDERS BE '
            'LIABLE FOR ANY CLAIM, DAMAGES OR OTHER <br/>\nLIABILITY, WHETHER IN AN ACTION OF '
            'CONTRACT, TORT OR OTHERWISE, ARISING FROM, <br/>\nOUT OF OR IN CONNECTION WITH THE '
            'SOFTWARE OR THE USE OR OTHER DEALINGS IN THE <br/>\nSOFTWARE.<br/>\n</span></p>\n'
            '<p><span style=" font-family:"monospace"; text-decoration: underline;">\n<br/>\n<br/>'
            '\n</span></p>\n</body>\n</html>'
        )
        self.license_label.setWordWrap(True)
        self.license_label.setOpenExternalLinks(True)
        self.license_label.setObjectName('licenseLabel')
        self.license_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse
                                                   | QtCore.Qt.TextBrowserInteraction)
        self.license_label.setOpenExternalLinks(True)

        self.citation_label = QtWidgets.QLabel(
            '<html><head/><body><p>'
            'If you are publishing scientific results, mentioning Qudi in your methods decscription <br/>\n'
            'is the least you can do as good scientific practice. You should cite our paper <br/>\n<br/>\n'
            'Qudi: A modular python suite for experiment control and data processing.<br/>\n'
            '</span>\n<a href="https://doi.org/10.1016/j.softx.2017.02.001"><span style=" text-decoration: '
            'underline; color:#00ffff;">https://doi.org/10.1016/j.softx.2017.02.001</span></a><br/>\n</p>\n'
            '@article{BINDER201785,<br/>\n'
            'title = {Qudi: A modular python suite for experiment control and data processing},<br/>\n'
            'journal = {SoftwareX},<br/>\n'
            'volume = {6},<br/>\n'
            'pages = {85-90},<br/>\n'
            'year = {2017},<br/>\n'
            'issn = {2352-7110},<br/>\n'
            'doi = {https://doi.org/10.1016/j.softx.2017.02.001},<br/>\n'
            'url = {https://www.sciencedirect.com/science/article/pii/S2352711017300055},<br/>\n'
            'author = {Jan M. Binder and Alexander Stark and Nikolas Tomek and Jochen Scheuer and Florian Frank and Kay D. Jahnke and Christoph Müller and Simon Schmitt and Mathias H. Metsch and Thomas Unden and Tobias Gehring and Alexander Huck and Ulrik L. Andersen and Lachlan J. Rogers and Fedor Jelezko},<br/>\n'
            'keywords = {Python 3, Qt, Experiment control, Automation, Measurement software, Framework, Modular},<br/>\n'
            'abstract = {Qudi is a general, modular, multi-operating system suite written in Python 3 for controlling laboratory experiments. It provides a structured environment by separating functionality into hardware abstraction, experiment logic and user interface layers. The core feature set comprises a graphical user interface, live data visualization, distributed execution over networks, rapid prototyping via Jupyter notebooks, configuration management, and data recording. Currently, the included modules are focused on confocal microscopy, quantum optics and quantum information experiments, but an expansion into other fields is possible and encouraged.}<br/>\n'
            '}<br/>\n'
            '</p></body></html>'
        )
        self.citation_label.setWordWrap(True)
        self.citation_label.setObjectName('creditsLabel')
        self.citation_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextBrowserInteraction
        )
        self.citation_label.setOpenExternalLinks(True)

        about_scroll_widget = QtWidgets.QScrollArea()
        about_scroll_widget.setWidgetResizable(True)
        about_scroll_widget.setWidget(self.about_label)
        about_scroll_widget.setObjectName('aboutScrollArea')
        credits_scroll_widget = QtWidgets.QScrollArea()
        credits_scroll_widget.setWidgetResizable(True)
        credits_scroll_widget.setWidget(self.credits_label)
        credits_scroll_widget.setObjectName('creditsScrollArea')
        license_scroll_widget = QtWidgets.QScrollArea()
        license_scroll_widget.setWidgetResizable(True)
        license_scroll_widget.setWidget(self.license_label)
        license_scroll_widget.setObjectName('licenseScrollArea')
        citation_scroll_widget = QtWidgets.QScrollArea()
        citation_scroll_widget.setWidgetResizable(True)
        citation_scroll_widget.setWidget(self.citation_label)
        citation_scroll_widget.setObjectName('citationScrollArea')

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName('tabWidget')
        self.tab_widget.addTab(about_scroll_widget, 'About')
        self.tab_widget.addTab(credits_scroll_widget, 'Credits')
        self.tab_widget.addTab(license_scroll_widget, 'License')
        self.tab_widget.addTab(citation_scroll_widget, 'Cite Qudi')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.tab_widget)
        layout.addWidget(buttonbox)

        self.setLayout(layout)
        self.about_label.setFocus()
        return
   
