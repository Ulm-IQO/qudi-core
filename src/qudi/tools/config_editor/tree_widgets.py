# -*- coding: utf-8 -*-
"""

"""

__all__ = ['AvailableModulesTreeWidget', 'SelectedModulesTreeWidget', 'ConfigModulesTreeWidget']

from re import compile
from PySide6 import QtCore, QtWidgets, QtGui
from typing import Optional, Iterable, Mapping, Tuple, Dict, List, Sequence


class AvailableModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """
    def __init__(self,
                 modules: Optional[Iterable[str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self.setColumnCount(2)
        self.setHeaderLabels(('Base', 'module.Class'))
        self.setSelectionMode(self.ExtendedSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setDragEnabled(True)

        self.top_level_items = dict()
        self.clear_modules()
        if modules is not None:
            self.set_modules(sorted(modules))

    @property
    def modules(self) -> List[str]:
        modules = list()
        for base, top_item in self.top_level_items.items():
            items = [top_item.child(index) for index in range(top_item.childCount())]
            modules.extend(f'{base}.{it.text(1)}' for it in items)
        return modules

    def set_modules(self, modules: Iterable[str]) -> None:
        # Clear all modules
        self._clear_modules()
        # Add new modules
        for module in modules:
            self._add_module(module)
        # Resize columns
        self.resize_columns_to_content()

    def add_module(self, module: str) -> None:
        self._add_module(module)
        self.resize_columns_to_content()

    def _add_module(self, module: str) -> None:
        base, module_class = module.split('.', 1)
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, module_class)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled
        )
        self.top_level_items[base].addChild(item)

    def remove_module(self, module: str) -> None:
        self._remove_module(module)
        self.resize_columns_to_content()

    def _remove_module(self, module: str) -> None:
        base, module_class = module.split('.', 1)
        top_level_item = self.top_level_items[base]
        for index in range(top_level_item.childCount()):
            child = top_level_item.child(index)
            if child.text(1) == module_class:
                top_level_item.removeChild(child)
                break

    def clear_modules(self) -> None:
        self._clear_modules()
        self.resize_columns_to_content()

    def _clear_modules(self) -> None:
        self.clear()
        for disp_base in ('GUI', 'Logic', 'Hardware'):
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            self.top_level_items[disp_base.lower()] = item

    def resize_columns_to_content(self) -> None:
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

    def mimeData(self, items: Sequence) -> QtCore.QMimeData:
        """ Add text to mime data. This is the quick (but not necessarily dirty) way.
        """
        texts = tuple(f'{it.parent().text(0).lower()}.{it.text(1)}' for it in items)
        mime = super().mimeData(items)
        mime.setText(';'.join(texts))
        return mime


class ConfigModulesTreeWidget(QtWidgets.QTreeWidget):
    """
    """

    def __init__(self,
                 named_modules: Optional[Mapping[str, str]] = None,
                 unnamed_modules: Optional[Iterable[str]] = None,
                 parent: Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent=parent)

        self.setDragEnabled(False)
        self.setDropIndicatorShown(False)
        self.setAcceptDrops(True)
        self.setColumnCount(3)
        self.setHeaderLabels(['Base', 'Name', 'module.Class'])
        self.setSelectionMode(self.SingleSelection)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.itemDoubleClicked.connect(self._edit_item_column)

        self.top_level_items = dict()
        self.set_modules(named_modules, unnamed_modules)
        self._valid_foreground = next(iter(self.top_level_items.values())).foreground(0)
        self._name_regex = compile(r'^[a-zA-Z_]+[a-zA-Z0-9_]*$')

    @property
    def modules(self) -> Tuple[Dict[str, str], List[str]]:
        named_modules = dict()
        unnamed_modules = list()
        for base, top_item in self.top_level_items.items():
            items = [top_item.child(index) for index in range(top_item.childCount())]
            for it in items:
                name = it.text(1)
                module = f'{base}.{it.text(2)}'
                if self.is_valid_name(name) and name not in named_modules:
                    named_modules[name] = module
                else:
                    unnamed_modules.append(module)
        return named_modules, unnamed_modules

    def set_modules(self,
                    named_modules: Optional[Mapping[str, str]] = None,
                    unnamed_modules: Optional[Iterable[str]] = None
                    ) -> None:
        if named_modules is None:
            named_modules = dict()
        if unnamed_modules is None:
            unnamed_modules = list()
        # Clear all modules
        self._clear_modules()
        # Add new modules
        for name, module in named_modules.items():
            self._add_module(module, name)
        for module in unnamed_modules:
            self._add_module(module)
        # Resize columns
        self.resize_columns_to_content()

    def add_module(self, module: str, name: Optional[str] = None) -> None:
        self._add_module(module, name)
        self.resize_columns_to_content()

    def _add_module(self, module: str, name: Optional[str] = None) -> None:
        base, module_class = module.split('.', 1)
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, '<enter unique name>' if name is None else name)
        item.setText(2, module_class)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        )
        self.top_level_items[base].addChild(item)

    def remove_module(self, name: str) -> None:
        self._remove_module(name)
        self.resize_columns_to_content()

    def _remove_module(self, name: str) -> None:
        found = False
        for base, top_item in self.top_level_items.items():
            for index in range(top_item.childCount()):
                child = top_item.child(index)
                if child.text(1) == name:
                    top_item.removeChild(child)
                    found = True
                    break
            if found:
                break

    def clear_modules(self) -> None:
        self._clear_modules()
        self.resize_columns_to_content()

    def _clear_modules(self) -> None:
        self.clear()
        for disp_base in ['GUI', 'Logic', 'Hardware']:
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setText(0, disp_base)
            self.addTopLevelItem(item)
            item.setExpanded(True)
            self.top_level_items[disp_base.lower()] = item

    def resize_columns_to_content(self) -> None:
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

    def is_valid_name(self, name: str) -> bool:
        set_names = list()
        for base, top_item in self.top_level_items.items():
            items = [top_item.child(index) for index in range(top_item.childCount())]
            set_names.extend(it.text(1) for it in items)
        return self._name_regex.match(name) is not None and set_names.count(name) <= 1

    @QtCore.Slot(QtWidgets.QTreeWidgetItem, int)
    def _edit_item_column(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        if item and column == 1 and item.parent() is not None:
            self.editItem(item, column)


class SelectedModulesTreeWidget(ConfigModulesTreeWidget):
    """
    """
    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if isinstance(event.source(), AvailableModulesTreeWidget):
            full_text = event.mimeData().text()
            for module in full_text.split(';'):
                self._add_module(module)
            self.resize_columns_to_content()
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Delete:
            for item in self.selectedItems():
                if item.parent() is not None:
                    item.parent().removeChild(item)
            event.accept()
        else:
            super().keyPressEvent(event)
