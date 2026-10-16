"""Locally bundled fictional AI portraits; no network or personal photos."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QListWidget, QListWidgetItem, QDialogButtonBox, QFileDialog
from core import ROOT


class AvatarGallery(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path=''
        self.setWindowTitle('Аватар AI-співрозмовника')
        self.resize(650,580)
        layout=QVBoxLayout(self)
        note=QLabel('40 вигаданих AI-портретів. Обери обличчя або завантаж власне зображення.')
        note.setWordWrap(True);layout.addWidget(note)
        self.group=QComboBox();self.group.addItems(['Усі','Жіночі','Чоловічі']);layout.addWidget(self.group)
        self.items=QListWidget();self.items.setViewMode(QListWidget.IconMode)
        self.items.setResizeMode(QListWidget.Adjust);self.items.setMovement(QListWidget.Static)
        self.items.setIconSize(QSize(96,96));self.items.setGridSize(QSize(116,132))
        layout.addWidget(self.items)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        upload=buttons.addButton('Власне фото…',QDialogButtonBox.ActionRole)
        upload.clicked.connect(self.upload);buttons.accepted.connect(self.choose);buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.group.currentIndexChanged.connect(self.populate)
        self.items.itemDoubleClicked.connect(lambda _:self.choose())
        self.populate()

    def populate(self):
        self.items.clear();index=self.group.currentIndex()
        for path in sorted((ROOT/'assets/avatars').glob('*.png')):
            female=path.name.startswith('female-')
            if index==1 and not female or index==2 and female:continue
            item=QListWidgetItem(QIcon(str(path)),('Жіночий ' if female else 'Чоловічий ')+path.stem.split('-')[-1])
            item.setData(Qt.UserRole,str(path));self.items.addItem(item)

    def choose(self):
        item=self.items.currentItem()
        if item:self.selected_path=item.data(Qt.UserRole);self.accept()

    def upload(self):
        path,_=QFileDialog.getOpenFileName(self,'Аватар','','Зображення (*.png *.jpg *.jpeg *.webp)')
        if path:self.selected_path=path;self.accept()
