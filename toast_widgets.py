from PySide6.QtCore import Qt
from PySide6.QtGui import QTextLayout, QTextOption
from PySide6.QtWidgets import QLabel, QDialog, QVBoxLayout, QPushButton


class ToastPreview(QLabel):
    """Two complete lines, with an ellipsis fitted using the actual font metrics."""
    def __init__(self, text):
        super().__init__()
        self.full_text=' '.join(text.split())
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setFixedHeight(36)
        self.setMinimumWidth(0)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.update_preview()

    def update_preview(self):
        width=max(1,self.contentsRect().width())
        layout=QTextLayout(self.full_text,self.font())
        option=QTextOption();option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option);layout.beginLayout()
        first=layout.createLine()
        if not first.isValid():layout.endLayout();self.setText('');return
        first.setLineWidth(width);end=first.textLength()
        layout.endLayout()
        # QTextLayout offsets are UTF-16; Python indexes Unicode codepoints.
        raw=self.full_text.encode('utf-16-le')
        head=raw[:end*2].decode('utf-16-le').rstrip()
        tail=raw[end*2:].decode('utf-16-le').lstrip()
        second=self.fontMetrics().elidedText(tail,Qt.ElideRight,width) if tail else ''
        self.setText(head+('\n'+second if second else ''))


class HideAllToast(QDialog):
    def __init__(self,callback):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(320,32)
        self.setStyleSheet('QDialog{background:#17212b;border:0;} QPushButton{background:transparent;border:0;color:#64b5ed;font-family:Segoe UI;font-size:12px;padding:0;} QPushButton:hover{color:white;}')
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.button=QPushButton('Hide all');self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(callback);layout.addWidget(self.button)
