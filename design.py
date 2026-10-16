"""Reference-matched live Qt components; AI-generated texture in assets/."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame, QCheckBox, QStyleOption, QStyle

def text(value, size=18, color='#f3f5fa', bold=False):
    w=QLabel(value);w.setWordWrap(True)
    w.setStyleSheet(f'background:transparent;color:{color};font-size:{size}px;font-weight:{600 if bold else 400};')
    return w

class Surface(QWidget):
    def __init__(self, orbits=False):
        super().__init__();self.orbits=orbits
        self.texture=QPixmap(str(Path(__file__).parent/'assets/navy-texture.png'))
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#17212b'))

class Orbit(QWidget):
    def __init__(self,size=68):
        super().__init__();self.setFixedSize(size,size);self.icon=QPixmap(str(Path(__file__).parent/'assets/app-icon.png'))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.SmoothPixmapTransform);p.drawPixmap(self.rect(),self.icon)

class TitleBar(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.setFixedHeight(32);self.setAttribute(Qt.WA_StyledBackground,True);self.setStyleSheet('background:#222e3b;')
        l=QHBoxLayout(self);l.setContentsMargins(12,0,0,0);l.setSpacing(8);l.addWidget(Orbit(20));l.addWidget(text('English Orbit',12));l.addStretch()
        for glyph,tip,callback in [('—','Згорнути',window.showMinimized),('□','Розгорнути',self.toggle),('×','Закрити',window.close)]:
            b=QPushButton(glyph);b.setToolTip(tip);b.setFixedSize(36,30);b.setStyleSheet('QPushButton{background:transparent;color:#b3c3d3;font-size:17px;padding:0;} QPushButton:hover{background:#284155;}');b.clicked.connect(callback);l.addWidget(b)
    def toggle(self):self.window.showNormal() if self.window.isMaximized() else self.window.showMaximized()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton and self.window.windowHandle():self.window.windowHandle().startSystemMove()
    def mouseDoubleClickEvent(self,e):self.toggle()

class Toggle(QCheckBox):
    def __init__(self,title):
        super().__init__(title);self.setStyleSheet('QCheckBox{spacing:12px;font-size:14px;padding:6px 0;} QCheckBox::indicator{width:40px;height:22px;border-radius:11px;background:#354758;border:0;} QCheckBox::indicator:checked{background:#40b3fc;}')
    def paintEvent(self,event):
        super().paintEvent(event);p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(QColor('white'));p.drawEllipse(21 if self.isChecked() else 3,(self.height()-16)//2,16,16)

class Portrait(QPushButton):
    def __init__(self,path=''):super().__init__();self.path=path;self.setFixedSize(104,104);self.setCursor(Qt.PointingHandCursor);self.setToolTip('Вибрати аватар')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.scale(self.width()/140,self.height()/140);p.setPen(QPen(QColor('#526b81'),2));p.setBrush(QColor('#213141'));p.drawEllipse(6,3,124,124)
        photo=QPixmap(self.path)
        if not photo.isNull():
            p.save();clip=QPainterPath();clip.addEllipse(7,4,122,122);p.setClipPath(clip);p.drawPixmap(7,4,122,122,photo);p.restore()
        else:
            p.setPen(Qt.NoPen);p.setBrush(QColor('#8b9eaf'));p.drawEllipse(53,38,30,30);p.drawRoundedRect(42,74,52,26,13,13)
        p.setBrush(QColor('#40b3fc'));p.setPen(Qt.NoPen);p.drawEllipse(100,94,40,40);p.setPen(QPen(QColor('white'),2));p.setBrush(Qt.NoBrush);p.drawRoundedRect(111,106,19,15,3,3);p.drawEllipse(117,110,7,7);p.drawLine(116,103,123,103)

class FeatureIcon(QWidget):
    def __init__(self,kind):super().__init__();self.kind=kind;self.setFixedSize(44,48)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#6ccdfb'),3));p.setBrush(Qt.NoBrush)
        if self.kind=='♧':
            path=QPainterPath();path.moveTo(8,34);path.cubicTo(-4,8,40,0,40,23);path.cubicTo(40,38,22,41,15,36);path.lineTo(3,41);path.lineTo(8,34);p.drawPath(path)
        elif self.kind=='▥':
            p.setPen(QPen(QColor('#6ccdfb'),6,Qt.SolidLine,Qt.RoundCap))
            for x,y in [(7,30),(19,20),(31,9)]:p.drawLine(x,y,x,41)
        else:
            p.drawArc(QRectF(5,6,33,33),30*16,145*16);p.drawArc(QRectF(5,6,33,33),210*16,145*16);p.drawLine(35,6,38,17);p.drawLine(38,17,27,15);p.drawLine(5,40,3,29);p.drawLine(3,29,14,31)

class Welcome(Surface):
    def __init__(self,connect):
        super().__init__();self.setMinimumWidth(300)
        l=QVBoxLayout(self);l.setContentsMargins(24,32,24,32);l.setSpacing(12);l.addStretch()
        l.addWidget(Orbit(64),0,Qt.AlignHCenter)
        heading=text('English Orbit',24,bold=True);heading.setAlignment(Qt.AlignCenter);l.addWidget(heading)
        hint=text('Обери співрозмовника, щоб почати розмову.\nТексти, словник і практика — у меню ліворуч.',14,'#8da6bb');hint.setAlignment(Qt.AlignCenter);l.addWidget(hint)
        l.addSpacing(10);b=QPushButton('AI-підписки');b.setObjectName('primary');b.setFixedSize(230,40);b.clicked.connect(connect);l.addWidget(b,0,Qt.AlignHCenter);l.addStretch()

EXTRA_STYLE='''
QWidget#rail {background:#0e1b27;border-right:1px solid #243547;}
QWidget#sidebar {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #142230,stop:1 #111e2b);border:1px solid #253648;border-top-left-radius:12px;}
QFrame#feature {background:rgba(21,35,49,210);border:1px solid #28455d;border-radius:15px;}
QPushButton#primary {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3fbeef,stop:1 #4aaffb);color:#052238;border-radius:12px;font-size:18px;font-weight:600;}
QToolButton {font-size:13px;color:#a4b8cc;}
QToolButton:checked {background:#142f45;color:#f0f7ff;}
QLineEdit,QPlainTextEdit,QComboBox {background:#1c2b3b;border:1px solid #506b83;border-radius:10px;padding:12px;color:#f1f5fa;}
QDialog#profile QLineEdit,QDialog#profile QComboBox,QDialog#profile QPlainTextEdit {font-size:18px;}
QDialog#profile QLabel#field {font-size:18px;font-weight:600;}
'''

EXTRA_STYLE += """
QWidget#rail {background:#17212b;border-right:1px solid #243343;}
QWidget#sidebar {background:#17212b;border:0;border-right:1px solid #243343;border-radius:0;}
QFrame#feature,QFrame#card {background:#1c2936;border:0;border-radius:6px;}
QPushButton#primary {background:#3478ad;color:#ffffff;border:0;border-radius:5px;font-size:14px;padding:8px 14px;}
QPushButton#primary:hover {background:#418abd;}
QToolButton {font-size:10px;padding:4px 0;border-radius:6px;}
QLineEdit,QPlainTextEdit,QComboBox {background:#232f3d;border:1px solid #344658;border-radius:5px;padding:8px;}
QDialog#profile QLineEdit,QDialog#profile QComboBox,QDialog#profile QPlainTextEdit {font-size:14px;}
QDialog#profile QLabel#field {font-size:14px;}
"""
