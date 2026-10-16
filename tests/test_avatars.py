from test_ui import app, window
from avatar_gallery import AvatarGallery
from core import ROOT, Store
from PySide6.QtGui import QImage


def test_gallery_has_40_valid_portraits_and_filters(app):
    gallery=AvatarGallery()
    assert gallery.items.count()==40
    for path in (ROOT/'assets/avatars').glob('*.png'):
        assert not QImage(str(path)).isNull()
    gallery.group.setCurrentIndex(1);assert gallery.items.count()==20
    gallery.group.setCurrentIndex(2);assert gallery.items.count()==20
    gallery.items.setCurrentRow(0);gallery.choose()
    assert gallery.selected_path.endswith('male-01.png')
    gallery.close()


def test_default_portraits_preserve_custom_avatar(tmp_path):
    store=Store(tmp_path/'avatars.sqlite')
    assert store.one("SELECT avatar FROM agents WHERE id='mia'")['avatar'].endswith('female-01.png')
    store.execute("UPDATE agents SET avatar='custom.png' WHERE id='mia'")
    Store(store.path)
    assert store.one("SELECT avatar FROM agents WHERE id='mia'")['avatar']=='custom.png'
