from __future__ import annotations
import os, sys, json, random, time, html, shutil, ctypes
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont, QAction, QDesktopServices, QPainterPath, QLinearGradient
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import *
from core import Store, Collector, ROOT, uid, now, normalize, learning_text, PERSONAS
from providers import PROVIDERS, discover, login, query, make_prompt, ProviderError
from capture import NativeCapture, Bridge, idle_seconds
from learning_ui import HintDialog, MemoryDialog
from toast_widgets import ToastPreview, HideAllToast
from chat_view import ChatView

STYLE='''
* { font-family: "Segoe UI"; font-size: 14px; color: #e8eef4; }
QMainWindow,QDialog { background: #0e1621; }
QWidget#rail { background: #111b26; border-right:1px solid #263343; }
QWidget#sidebar { background:#17212b; border-right:1px solid #263343; }
QWidget#header { background:#17212b; border-bottom:1px solid #263343; }
QWidget#canvas { background:#0e1621; }
QLabel { background:transparent; }
QLabel#muted { color:#8498ab; font-size:12px; }
QLabel#title { font-size:23px; font-weight:600; }
QLabel#section { color:#67baf0; font-weight:600; font-size:12px; }
QFrame#card { background:#182634; border:1px solid #293b4c; border-radius:14px; }
QFrame#incoming { background:#192a39; border-radius:16px; }
QFrame#outgoing { background:#244d68; border-radius:16px; }
QPushButton { background:#233548; border:0; border-radius:8px; padding:10px 15px; font-weight:500; }
QPushButton:hover { background:#2d445b; }
QPushButton:pressed { background:#1a2d40; }
QPushButton:disabled { color:#708496; background:#1d2b39; }
QPushButton#primary { background:#4ba8df; color:#081e2d; font-weight:600; }
QPushButton#primary:hover { background:#6abbed; }
QPushButton#railButton { background:transparent; padding:9px; border-radius:12px; color:#8fa3b6; }
QPushButton#railButton:checked { background:#24425a; color:#77c7f5; }
QPushButton#flat { background:transparent; color:#72bdec; padding:6px; }
QToolButton { background:transparent; border:0; border-radius:12px; padding:7px 2px; font-size:11px; color:#94aabd; }
QToolButton:checked { background:#24425a; color:#79c9f5; }
QToolButton:hover { background:#203548; }
QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox { background:#202e3c; border:1px solid #304254; border-radius:8px; padding:9px; selection-background-color:#3983b3; }
QLineEdit:focus,QTextEdit:focus,QPlainTextEdit:focus { border-color:#4ba8df; }
QComboBox QAbstractItemView { background:#203244; selection-background-color:#335572; }
QListWidget { background:transparent; border:0; outline:0; }
QListWidget::item { border:0; border-radius:8px; margin:2px 8px; padding:2px; }
QListWidget::item:selected { background:#2a4e69; }
QListWidget::item:hover { background:#203448; }
QScrollArea { border:0; background:transparent; }
QScrollBar:vertical { background:transparent; width:7px; margin:3px; }
QScrollBar::handle:vertical { background:#3b5266; border-radius:3px; min-height:35px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:none; }
QCheckBox { spacing:9px; padding:5px 0; }
QCheckBox::indicator { width:17px; height:17px; border:1px solid #587087; border-radius:4px; background:#17212b; }
QCheckBox::indicator:checked { background:#4ba8df; border-color:#4ba8df; }
QMenu { background:#213141; border:1px solid #3a4e62; padding:5px; }
QMenu::item { padding:8px 18px; } QMenu::item:selected { background:#355572; }
QToolTip { background:#2a4157; color:white; border:0; padding:6px; }
QTextBrowser { border:0; background:transparent; padding:8px; }
QTabWidget::pane { border:0; } QTabBar::tab { background:#17212b; padding:10px 15px; }
QTabBar::tab:selected { background:#29475f; }
'''

def label(text,style='',wrap=False):
    w=QLabel(text);w.setWordWrap(wrap);w.setTextFormat(Qt.TextFormat.PlainText)
    if style:w.setObjectName(style)
    return w
def button(text,callback=None,primary=False):
    w=QPushButton(text)
    if primary:w.setObjectName('primary')
    if callback:w.clicked.connect(callback)
    return w
def clear(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget():item.widget().deleteLater()
        elif item.layout():clear(item.layout())
def panel(layout):
    w=QWidget();w.setLayout(layout);return w
def form_field(layout,title,widget):
    layout.addWidget(label(title,'section'));layout.addWidget(widget)
def date(ts):return datetime.fromtimestamp(ts).strftime('%d.%m · %H:%M')

def avatar(text,color,size=48,path=''):
    pix=QPixmap(size,size);pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient=QLinearGradient(0,0,size,size);gradient.setColorAt(0,QColor(color).lighter(115));gradient.setColorAt(1,QColor(color));p.setBrush(gradient);p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(0,0,size,size)
    if path and Path(path).is_file():
        clip=QPainterPath();clip.addEllipse(0,0,size,size);p.setClipPath(clip)
        photo=QPixmap(path).scaled(size,size,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
        p.drawPixmap((size-photo.width())//2,(size-photo.height())//2,photo)
    else:
        p.setPen(QColor('#ffffff'));p.setFont(QFont('Segoe UI',int(size*.31),QFont.Weight.DemiBold));p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,text[:2].upper())
    p.end();w=QLabel();w.setPixmap(pix);w.setFixedSize(size,size);return w

def app_icon():
    return QIcon(str(ROOT/'assets/app-icon.ico'))


def nav_icon(kind):
    pix=QPixmap(30,30);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#9fc4dc'),1.8));p.setBrush(Qt.BrushStyle.NoBrush)
    if kind=='chats':
        p.drawRoundedRect(4,5,22,17,5,5);p.drawLine(9,22,7,27);p.drawLine(7,27,16,22)
    elif kind=='texts':
        p.drawRoundedRect(6,3,18,24,3,3)
        for y in (10,15,20):p.drawLine(10,y,20,y)
    elif kind=='words':
        p.drawRoundedRect(3,5,24,21,2,2);p.drawLine(15,5,15,26);p.drawLine(7,11,11,11);p.drawLine(19,11,23,11)
    elif kind=='settings':
        p.drawEllipse(5,5,20,20);p.drawEllipse(11,11,8,8)
        for x1,y1,x2,y2 in [(15,1,15,5),(15,25,15,29),(1,15,5,15),(25,15,29,15),(5,5,8,8),(22,22,25,25),(5,25,8,22),(22,8,25,5)]:p.drawLine(x1,y1,x2,y2)
    else:
        p.drawEllipse(5,5,20,20);p.drawLine(10,15,14,19);p.drawLine(14,19,21,11)
    p.end();return QIcon(pix)

from design import Surface, Orbit, TitleBar, Toggle, Portrait, Welcome, EXTRA_STYLE, text as design_text
STYLE += EXTRA_STYLE

class WorkerSignals(QObject):
    ok=Signal(object);error=Signal(str)
class Worker(QRunnable):
    def __init__(self,fn):super().__init__();self.fn=fn;self.signals=WorkerSignals()
    def run(self):
        try:self.signals.ok.emit(self.fn())
        except Exception as e:self.signals.error.emit(str(e))

class Composer(QPlainTextEdit):
    submitted=Signal()
    def keyPressEvent(self,e):
        if e.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not e.modifiers()&Qt.KeyboardModifier.ShiftModifier:
            self.submitted.emit();e.accept()
        else:super().keyPressEvent(e)

class ProfileDialog(QDialog):
    def __init__(self,owner=None,first=False,store=None):
        super().__init__(owner);self.owner=owner;self.store=store if store is not None else owner.store;self.first=first;self.avatar_path=self.store.get('avatar','')
        self.setSizeGripEnabled(True);self.setObjectName('profile');self.setWindowTitle('English Orbit');self.setWindowFlags(self.windowFlags()|Qt.FramelessWindowHint)
        available=QApplication.primaryScreen().availableGeometry();self.resize(min(580,available.width()-40),min(780,available.height()-40))
        outer=QVBoxLayout(self);outer.setContentsMargins(1,1,1,1);outer.setSpacing(0);bar=TitleBar(self);bar.setFixedHeight(32);outer.addWidget(bar)
        sc=QScrollArea();sc.setWidgetResizable(True);outer.addWidget(sc);surface=Surface();sc.setWidget(surface)
        lay=QVBoxLayout(surface);lay.setContentsMargins(36,18,36,22);lay.setSpacing(12)
        heading=design_text('Твоя англійська починається тут',23,bold=True);heading.setAlignment(Qt.AlignCenter);lay.addWidget(heading)
        sub=design_text('Жива англійська починається з твоїх думок.',14,'#8fa7be');sub.setAlignment(Qt.AlignCenter);lay.addWidget(sub)
        lay.addSpacing(6);self.portrait=Portrait(self.avatar_path);self.portrait.clicked.connect(self.choose_avatar);lay.addWidget(self.portrait,0,Qt.AlignHCenter)
        self.avatar_btn=button('Вибрати аватар',self.choose_avatar);self.avatar_btn.setObjectName('flat');self.avatar_btn.setStyleSheet('font-size:18px;padding:0;background:transparent;color:#44bbff;');lay.addWidget(self.avatar_btn,0,Qt.AlignHCenter)
        self.name=QLineEdit(self.store.get('name'));self.name.setPlaceholderText('Як до тебе звертатися?');self.name.setMinimumHeight(38)
        self.level=QComboBox();self.level.addItems(['A1','A2','B1','B2','C1','C2']);self.level.setCurrentText(self.store.get('level'));self.level.setMinimumHeight(38)
        self.goal=QPlainTextEdit(self.store.get('goal'));self.goal.setPlaceholderText('Напиши українською: навіщо ти хочеш вивчати англійську?');self.goal.setFixedHeight(88)
        for title,widget in [('Ім’я',self.name),('Початковий рівень',self.level),('Твоя мета',self.goal)]:
            field=QVBoxLayout();field.setSpacing(8);field.addWidget(label(title,'field'));field.addWidget(widget);lay.addLayout(field)
        self.autostart=Toggle('Запускати разом із Windows');self.autostart.setChecked(self.store.get('autostart'));lay.addWidget(self.autostart)
        lay.addWidget(design_text('Підключення підписок і джерела текстів — у налаштуваннях.\nДо завершення профілю збір вимкнений.',15,'#8fa7be'))
        lay.addStretch();self.save_button=button('Почати навчання    →' if first else 'Зберегти профіль',self.save,True);self.save_button.setMinimumHeight(40);lay.addWidget(self.save_button)
    def choose_avatar(self):
        file,_=QFileDialog.getOpenFileName(self,'Аватар','','Зображення (*.png *.jpg *.jpeg *.webp)')
        if file:
            dest=ROOT/'data/avatar.png';dest.parent.mkdir(parents=True,exist_ok=True);pix=QPixmap(file)
            if not pix.isNull():
                pix.scaled(256,256,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation).save(str(dest));self.avatar_path=str(dest);self.portrait.path=str(dest);self.portrait.update()
    def save(self):
        if not self.name.text().strip():QMessageBox.information(self,'Профіль','Введіть ім’я.');return
        for k,v in {'name':self.name.text().strip(),'level':self.level.currentText(),'goal':self.goal.toPlainText().strip(),'avatar':self.avatar_path,'onboarded':True,'autostart':self.autostart.isChecked()}.items():self.store.set(k,v)
        if self.first:self.store.set('capture',True)
        if self.owner:self.owner.set_autostart(self.autostart.isChecked());self.owner.navigate('chats')
        self.accept()

class AgentDialog(QDialog):
    def __init__(self,owner,agent=None):
        super().__init__(owner);self.owner=owner;self.agent=agent or {};self.avatar_path=self.agent.get('avatar','')
        self.setWindowTitle('AI-співрозмовник');self.resize(570,650);lay=QVBoxLayout(self);lay.setSpacing(12)
        self.name=QLineEdit(self.agent.get('name',''));form_field(lay,'ІМ’Я',self.name)
        self.topic=QLineEdit(self.agent.get('topic',''));form_field(lay,'ТЕМА',self.topic)
        self.provider=QComboBox();self.provider.addItems(PROVIDERS);self.provider.setCurrentText(self.agent.get('provider','ChatGPT'));form_field(lay,'ПРОВАЙДЕР',self.provider)
        self.model=QComboBox();self.model.setEditable(True);self.provider.currentTextChanged.connect(self.load_models);self.load_models();self.model.setCurrentText(self.agent.get('model',''));form_field(lay,'МОДЕЛЬ · ПОРОЖНЬО = ВИБІР КЛІЄНТА',self.model)
        self.instructions=QPlainTextEdit(self.agent.get('instructions',''));form_field(lay,'ІНСТРУКЦІЇ .MD',self.instructions)
        row=QHBoxLayout();row.addWidget(button('Імпортувати .md',self.import_md));row.addWidget(button('Аватар',self.choose_avatar));lay.addLayout(row)
        self.enabled=QCheckBox('Може писати першим');self.enabled.setChecked(bool(self.agent.get('enabled',1)));lay.addWidget(self.enabled)
        lay.addWidget(button('Зберегти',self.save,True))
    def load_models(self):
        self.model.clear();self.model.addItem('')
        for m in self.owner.store.get('provider_'+self.provider.currentText(),{}).get('models',[]):self.model.addItem(m['id'])
    def import_md(self):
        path,_=QFileDialog.getOpenFileName(self,'Інструкції','','Markdown (*.md)')
        if path:self.instructions.setPlainText(Path(path).read_text(encoding='utf-8-sig'))
    def choose_avatar(self):
        path,_=QFileDialog.getOpenFileName(self,'Аватар','','Зображення (*.png *.jpg *.webp)')
        if path:
            dest=ROOT/'data'/('agent-avatar-'+uid()+'.png');pix=QPixmap(path)
            if not pix.isNull():pix.scaled(160,160,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation).save(str(dest));self.avatar_path=str(dest)
    def save(self):
        if not self.name.text().strip():return
        aid=self.agent.get('id') or uid();name=self.name.text().strip();instructions=self.instructions.toPlainText()
        self.owner.store.execute('INSERT OR REPLACE INTO agents VALUES(?,?,?,?,?,?,?,?,?)',(aid,name,self.topic.text(),self.agent.get('color','#7e9cdb'),self.avatar_path or name[:1],instructions,self.provider.currentText(),self.model.currentText(),int(self.enabled.isChecked())))
        (ROOT/'agents'/f'{aid}.md').write_text(instructions,encoding='utf-8')
        self.accept();self.owner.navigate('chats',aid)

from settings_ui import SettingsDialog

class WordDialog(QDialog):
    def __init__(self,owner,text=''):
        super().__init__(owner);self.owner=owner;self.setWindowTitle('Додати до словника');self.resize(510,570);lay=QVBoxLayout(self);lay.setSpacing(12)
        lay.addWidget(label('Збережи слово в контексті','title'))
        self.en=QLineEdit(text);form_field(lay,'СЛОВО АБО ФРАЗА',self.en)
        self.uk=QLineEdit();form_field(lay,'ЗНАЧЕННЯ УКРАЇНСЬКОЮ',self.uk)
        self.example=QPlainTextEdit();self.example.setMaximumHeight(100);form_field(lay,'ПРИКЛАД АНГЛІЙСЬКОЮ',self.example)
        self.dictionary=QComboBox();self.dictionary.setEditable(True)
        for d in owner.store.rows('SELECT * FROM dictionaries ORDER BY name'):self.dictionary.addItem(d['name'])
        self.dictionary.setPlaceholderText('Назва першого словника');form_field(lay,'СЛОВНИК · МОЖНА ВВЕСТИ НОВУ НАЗВУ',self.dictionary)
        self.status=label('Перевір значення перед збереженням.','muted',True);lay.addWidget(self.status)
        self.suggest=button('Запропонувати переклад і приклад',self.lookup);lay.addWidget(self.suggest);lay.addStretch();lay.addWidget(button('Підтвердити й зберегти',self.save,True))
    def lookup(self):
        if not self.en.text().strip():return
        self.suggest.setEnabled(False);self.status.setText('Шукаємо відповідне значення…')
        def done(r):
            self.suggest.setEnabled(True);self.en.setText(r.get('english',self.en.text()));self.uk.setText(r.get('ukrainian',''));self.example.setPlainText(r.get('example',''));self.status.setText('Перевір значення й підтвердь збереження.')
        self.owner.ai('word',{'text':self.en.text()},done,on_error=lambda e:(self.suggest.setEnabled(True),self.status.setText(e)))
    def save(self):
        try:
            did=self.owner.store.dictionary(self.dictionary.currentText());self.owner.store.add_word(did,self.en.text(),self.uk.text(),self.example.toPlainText());self.accept()
            if self.owner.page=='words':self.owner.navigate('words')
        except ValueError as e:self.status.setText(str(e))

class AnalysisDialog(QDialog):
    def __init__(self,owner,record):
        super().__init__(owner);self.owner=owner;self.record=record.copy();self.result=None;self.setWindowTitle('Аналіз тексту');self.resize(790,780)
        lay=QVBoxLayout(self);lay.addWidget(label('Твоя думка. Точніша англійська.','title'))
        lay.addWidget(label(f"{record['source']} · версія {record['version']} · {date(record['updated'])}",'muted'))
        self.editor=QPlainTextEdit(learning_text(record['body']));self.editor.setMaximumHeight(180);lay.addWidget(self.editor)
        lay.addWidget(label('Надсилається лише текст у полі вище. Код, логи й цитати попередньо прибрано — перевір вибір.','muted',True))
        self.analyze=button('Analyze',self.start,True);lay.addWidget(self.analyze)
        self.output=QTextBrowser();self.output.setOpenExternalLinks(False);lay.addWidget(self.output,1)
        self.practice=button('Потренувати конструкції',self.train);self.practice.setEnabled(False);lay.addWidget(self.practice)
        previous=owner.store.one('SELECT * FROM analyses WHERE text_id=? ORDER BY created DESC LIMIT 1',(record['id'],))
        if previous:
            self.render(json.loads(previous['result']))
            if previous['version']!=record['version']:self.output.insertHtml('<p style="color:#e6b566">Текст змінився. Нижче розбір попередньої версії.</p>')
    def start(self):
        text=self.editor.toPlainText().strip()
        if not text:return
        self.analyze.setEnabled(False);self.output.setPlainText('Аналізуємо через підключену підписку…')
        def done(r):
            self.owner.store.save_analysis(self.record,text,r);self.analyze.setEnabled(True);self.render(r)
        self.owner.ai('analyze',{'text':text},done,on_error=lambda e:(self.analyze.setEnabled(True),self.output.setPlainText(e)),context={'record':self.record,'selected':text})
    def render(self,r):
        self.result=r;esc=html.escape
        body='<h3>Мінімальні правки</h3><p>'+esc(str(r.get('minimal',''))).replace('\n','<br>')+'</p><h3>Природніше</h3><p>'+esc(str(r.get('natural',''))).replace('\n','<br>')+'</p>'
        for e in r.get('errors',[]):body+='<p><b>'+esc(str(e.get('kind','')))+':</b> '+esc(str(e.get('before','')))+' → <b>'+esc(str(e.get('after','')))+'</b><br>'+esc(str(e.get('explanation','')))+'</p>'
        self.output.setHtml(body);self.practice.setEnabled(bool(r.get('patterns')))
    def train(self):PracticeDialog(self.owner,patterns=self.result.get('patterns',[])).show()

class PracticeDialog(QDialog):
    def __init__(self,owner,patterns=None,corner=False):
        super().__init__(owner);self.owner=owner;self.patterns=patterns;self.exercises=[];self.current=None;self.attempt=0;self.index=0;self.locked=False;self.typo_pending=False
        self.queue=owner.store.due()[:5] if patterns is None else []
        self.setWindowTitle('Коротка практика · English Orbit');self.resize(510,570)
        if corner:self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint);self.move_corner()
        lay=QVBoxLayout(self);lay.setContentsMargins(24,24,24,24);lay.setSpacing(15)
        self.heading=label('Маленька практика. Помітний прогрес.','title',True);lay.addWidget(self.heading)
        self.progress=label('','muted');lay.addWidget(self.progress)
        self.question=label('','',True);self.question.setStyleSheet('font-size:21px;');self.question.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);lay.addWidget(self.question)
        self.context=label('','muted',True);lay.addWidget(self.context)
        self.answer=QLineEdit();self.answer.setPlaceholderText('Твоя відповідь · «-» = не знаю');self.answer.returnPressed.connect(self.submit);lay.addWidget(self.answer)
        self.feedback=label('','',True);lay.addWidget(self.feedback);lay.addStretch()
        row=QHBoxLayout();self.check=button('Перевірити',self.submit,True);row.addWidget(self.check);row.addWidget(button('Не знаю',self.dont_know));lay.addLayout(row)
        self.next_button=button('Далі',self.next);lay.addWidget(self.next_button);self.next_button.hide()
        owner.dialogs.append(self)
        self.show()
        if patterns:self.generate(patterns)
        else:self.next()
    def move_corner(self):
        g=QApplication.primaryScreen().availableGeometry();self.move(g.right()-self.width()-20,g.bottom()-self.height()-20)
    def generate(self,patterns):
        self.question.setText('Готуємо вправи за твоїми помилками…');self.check.setEnabled(False)
        def done(r):
            self.exercises=r.get('exercises',[])[:5]
            if not self.exercises:self.feedback.setText('Модель не повернула завдань. Спробуй ще раз.');return
            self.next()
        self.owner.ai('exercise',{'patterns':patterns},done,on_error=self.failure)
    def failure(self,e):self.feedback.setText(e);self.check.setEnabled(True)
    def next(self):
        self.attempt=0;self.typo_pending=False;self.locked=False;self.answer.clear();self.feedback.clear();self.context.clear();self.next_button.hide();self.check.setEnabled(True);self.answer.setEnabled(True)
        if self.exercises:
            self.current={'exercise':self.exercises.pop(0)};self.index+=1;self.question.setText(self.current['exercise']['question']);self.progress.setText(f'Вправа {self.index}')
        elif self.queue:
            review=self.queue.pop(0);self.current={'review':review};self.index+=1
            if review['kind']=='construction':
                p=self.owner.store.one('SELECT * FROM constructions WHERE id=?',(review['item'],))
                if not p:self.next();return
                self.question.setText('Готуємо завдання на '+p['pattern']);self.check.setEnabled(False)
                def got(r):
                    ex=r.get('exercises',[])
                    if not ex:self.failure('Не вдалося створити вправу.');return
                    self.current['exercise']=ex[-1];self.question.setText(ex[-1]['question']);self.check.setEnabled(True)
                self.owner.ai('exercise',{'patterns':[p]},got,on_error=self.failure)
            else:
                word=self.owner.store.one('SELECT * FROM words WHERE id=?',(review['item'],))
                if not word:self.next();return
                self.current['word']=word;reverse=review['direction']=='uk-en'
                self.question.setText(word['ukrainian'] if reverse else word['english'])
                example=word['example']
                if reverse and word['english']:example=__import__('re').sub(__import__('re').escape(word['english']),'____',example,flags=__import__('re').I)
                self.context.setText(example)
                self.progress.setText(f"Картка {self.index} · {'українська → англійська' if reverse else 'англійська → українська'}")
        else:
            self.current=None;self.heading.setText('На сьогодні — ще один крок уперед');self.question.setText('Сесію завершено.' if self.index else 'Зараз немає карток на повторення.');self.progress.setText('Закриття вікна не зараховується як помилка.');self.answer.hide();self.check.hide()
            if self.owner.page=='practice':self.owner.navigate('practice')
    def expected(self):
        if self.current.get('exercise'):return self.current['exercise'].get('answer','')
        return self.current['word']['english' if self.current['review']['direction']=='uk-en' else 'ukrainian']
    def dont_know(self):self.answer.setText('-');self.submit()
    def submit(self):
        if not self.current or self.locked:return
        text=self.answer.text().strip()
        if not text:return
        expected=self.expected()
        if text=='-':self.finish('wrong','Правильний варіант: '+expected);return
        if normalize(text)==normalize(expected):self.finish('typo' if self.typo_pending else 'correct','Правильно ✓');return
        self.check.setEnabled(False)
        self.owner.ai('grade',{'answer':text,'expected':expected,'context':self.current,'attempt':self.attempt},self.graded,on_error=self.failure)
    def graded(self,r):
        self.check.setEnabled(True);grade=r.get('grade','wrong')
        if grade=='correct':self.finish('typo' if self.typo_pending else 'correct',r.get('explanation','Правильно ✓'))
        elif grade=='typo':
            self.typo_pending=True;self.feedback.setText('Майже правильно. Введи ще раз: '+r.get('correct_answer',self.expected()));self.answer.clear()
        elif self.attempt==0:
            self.attempt=1;self.feedback.setText('Підказка: '+r.get('hint','Перевір конструкцію та значення.'));self.answer.selectAll()
        else:self.finish('wrong',r.get('explanation','')+'\nПравильний варіант: '+r.get('correct_answer',self.expected()))
    def finish(self,grade,feedback):
        self.locked=True;self.feedback.setText(feedback);self.answer.setEnabled(False);self.check.setEnabled(False);self.next_button.show()
        review=self.current.get('review')
        if review:self.owner.store.grade(review['id'],grade)
        if grade=='wrong' and self.current.get('exercise'):
            # A fresh transfer item, rather than repeating the displayed answer.
            def fresh(r):
                if r.get('exercises'):self.exercises.append(r['exercises'][0])
            if self.index<8:self.owner.ai('exercise',{'previous':self.current['exercise'],'instruction':'Create a different short transfer exercise for the same construction.'},fresh,on_error=lambda e:None)

class ToastCloseButton(QPushButton):
    def __init__(self,callback,parent):
        super().__init__(parent);self.setFixedSize(20,20);self.setCursor(Qt.PointingHandCursor);self.setToolTip('Закрити сповіщення');self.setAccessibleName('Закрити сповіщення');self.clicked.connect(callback)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#b3c2ce' if self.underMouse() else '#596c7b'),1.2));p.drawLine(6,6,14,14);p.drawLine(14,6,6,14)
    def enterEvent(self,event):super().enterEvent(event);self.update()
    def leaveEvent(self,event):super().leaveEvent(event);self.update()

class Popup(QDialog):
    """Independent, non-activating toast that remains visible when the app is hidden."""
    def __init__(self,owner,agent=None,review=False,preview=False):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        self.owner=owner;self.agent=agent;self.review=review;self.setAttribute(Qt.WA_ShowWithoutActivating);self.setWindowTitle('English Orbit · Сповіщення');self.setFixedSize(320,80);self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet('QDialog{background:#17212b;border:0;} QLabel{background:transparent;border:0;} QPushButton{background:transparent;border:0;color:#8fa5b9;padding:0;font-size:18px;} QPushButton:hover{color:white;}')
        row=QHBoxLayout(self);row.setContentsMargins(10,8,26,8);row.setSpacing(14)
        face=avatar(agent['name'] if agent else 'EO',agent['color'] if agent else '#3478ad',60,agent.get('avatar','') if agent else '')
        row.addWidget(face,0,Qt.AlignTop);col=QVBoxLayout();col.setSpacing(4)
        title=label('Час для практики' if review else agent['name']);title.setStyleSheet('font-family:Segoe UI;font-size:13px;font-weight:600;');col.addWidget(title)
        message=self.owner.store.one("SELECT body FROM messages WHERE agent=? AND role='assistant' ORDER BY created DESC LIMIT 1",(agent['id'],)) if agent else None
        body=('Тестове сповіщення. Натисни, щоб відкрити чат.' if preview else 'Кілька слів готові до повторення.' if review else message['body'] if message else 'Відкрити розмову')
        self.body=ToastPreview(body);self.body.setStyleSheet('font-family:Segoe UI;font-size:13px;color:#7f9db6;');self.body.setMaximumHeight(36);col.addWidget(self.body);col.addStretch();row.addLayout(col,1)
        self.dismiss=ToastCloseButton(self.close,self);self.dismiss.move(self.width()-26,6);self.dismiss.raise_()
        for widget in (face,title,self.body):widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.close)
    def showEvent(self,event):
        super().showEvent(event)
        screen=self.owner.screen() or QApplication.primaryScreen();g=screen.availableGeometry()
        self.move(g.right()+1-self.width()-5,g.bottom()+1-self.height()-7);self.body.update_preview();self.timer.start(12000)
    def enterEvent(self,event):self.timer.stop();super().enterEvent(event)
    def leaveEvent(self,event):self.timer.start(6000);super().leaveEvent(event)
    def closeEvent(self,event):
        self.timer.stop();super().closeEvent(event)
        self.owner.remove_toast(self)
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            if self.review:self.practice()
            else:self.open_chat()
            event.accept()
        else:super().mousePressEvent(event)
    def open_chat(self):
        self.close()
        for dialog in self.owner.dialogs:
            if dialog.isVisible():dialog.hide()
        self.owner.open_window();self.owner.store.execute('UPDATE messages SET unread=0 WHERE agent=?',(self.agent['id'],));self.owner.navigate('chats',self.agent['id'])
    def practice(self):
        self.close();self.owner.open_window();self.owner.navigate('practice');self.owner.keep_dialog(PracticeDialog(self.owner))

class MainWindow(ChatView,QMainWindow):
    capture_event=Signal(str,str,str,bool);selection_event=Signal(str,str)
    def __init__(self,store,start_services=True):
        super().__init__();self.store=store;self.pool=QThreadPool(self);self.pool.setMaxThreadCount(3);self.workers=set();self.dialogs=[];self.pending_agents=set();self.online_agents=set();self.presence_timers={};self.active_agent=None;self.page='chats';self.notifications=[];self.popup=None;self.popups=[];self.hide_all_toast=None;self.exiting=False;self.services=start_services
        from accounts import Accounts
        self.accounts=Accounts(self)
        self.store.execute('CREATE TABLE IF NOT EXISTS notification_receipts(message_id TEXT PRIMARY KEY,shown REAL NOT NULL)')
        for row in self.store.rows("SELECT DISTINCT agent FROM messages WHERE role='assistant' AND unread=1 AND id NOT IN (SELECT message_id FROM notification_receipts)"):
            self.notifications.append(('chat',row['agent']))
        self.text_limit=200;self.history_limit=100;self.resize_grip=QSizeGrip(self)
        self.setWindowTitle('English Orbit');self.setWindowIcon(app_icon());screen=QApplication.primaryScreen().availableGeometry();self.resize(min(1280,screen.width()-40),min(820,screen.height()-40));self.setMinimumSize(850,600);self.setWindowFlags(self.windowFlags()|Qt.FramelessWindowHint)
        (ROOT/'agents').mkdir(parents=True,exist_ok=True)
        for agent in self.store.rows('SELECT * FROM agents'):
            path=ROOT/'agents'/f"{agent['id']}.md"
            if not path.exists():path.write_text(agent['instructions'],encoding='utf-8')
        self.store.execute("UPDATE jobs SET status='failed',error='Програму було закрито. Можна повторити запит.' WHERE status='running'")
        self.collector=Collector(store);self.capture_event.connect(self.collector.receive);self.selection_event.connect(self.selection)
        self.native=None;self.bridge=None
        root=Surface();self.setCentralWidget(root);outer=QVBoxLayout(root);outer.setContentsMargins(1,1,1,1);outer.setSpacing(0);outer.addWidget(TitleBar(self));shell=QHBoxLayout();outer.addLayout(shell,1);shell.setContentsMargins(0,0,0,0);shell.setSpacing(0)
        rail=QWidget();rail.setObjectName('rail');rail.setFixedWidth(64);rl=QVBoxLayout(rail);rl.setContentsMargins(4,12,4,10);rl.setSpacing(8)
        rl.addSpacing(0)
        self.nav={}
        for page,glyph,name in [('chats','◉','Чати'),('texts','▤','Тексти'),('words','▣','Словник'),('practice','◇','Практика')]:
            b=QToolButton();b.setText(name);b.setToolTip(name);b.setIcon(nav_icon(page));b.setIconSize(QSize(25,25));b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon);b.setCheckable(True);b.setFixedSize(56,58);b.clicked.connect(lambda _,p=page:self.navigate(p));rl.addWidget(b);self.nav[page]=b
        rl.addStretch();settings=button('',self.show_settings);settings.setToolTip('Налаштування');settings.setIcon(nav_icon('settings'));settings.setIconSize(QSize(28,28));settings.setObjectName('flat');settings.setStyleSheet('font-size:28px;');rl.addWidget(settings);profile=QToolButton();profile.setText('профіль');profile.setIcon(QIcon(avatar((store.get('name') or 'EO'),'#37536d',34,store.get('avatar')).pixmap()));profile.setIconSize(QSize(34,34));profile.setToolButtonStyle(Qt.ToolButtonTextUnderIcon);profile.clicked.connect(lambda:ProfileDialog(self).exec());rl.addWidget(profile);shell.addWidget(rail)
        self.workspace=QWidget();self.workspace_layout=QVBoxLayout(self.workspace);self.workspace_layout.setContentsMargins(0,0,0,0);self.workspace_layout.setSpacing(0);shell.addWidget(self.workspace,1)
        self.statusBar().setStyleSheet('background:#111b26;color:#8498ab;font-size:11px;');self.statusBar().showMessage('Локальні дані · English Orbit');self.statusBar().hide()
        self.tray=QSystemTrayIcon(app_icon(),self);self.tray.setToolTip('English Orbit')
        menu=QMenu();menu.addAction('Відкрити',self.open_window)
        self.capture_action=menu.addAction('Призупинити збір текстів');self.capture_action.setCheckable(True);self.capture_action.setChecked(not store.get('capture'));self.capture_action.triggered.connect(lambda checked:store.set('capture',not checked))
        self.dnd_action=menu.addAction('Не турбувати');self.dnd_action.setCheckable(True);self.dnd_action.setChecked(store.get('dnd'));self.dnd_action.triggered.connect(lambda checked:store.set('dnd',checked));menu.addSeparator();menu.addAction('Вийти',self.quit)
        self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.open_window() if reason==QSystemTrayIcon.ActivationReason.Trigger else None)
        if start_services:
            self.tray.show();self.native=NativeCapture(store);self.native.captured.connect(self.capture_event);self.native.selected.connect(self.selection_event);self.native.health.connect(self.statusBar().showMessage);self.native.start()
            self.bridge=Bridge(store,lambda *a:self.capture_event.emit(*a),lambda *a:self.selection_event.emit(*a))
            try:self.bridge.start()
            except OSError:self.statusBar().showMessage('Chrome-міст зайнятий. Перевірте, чи немає іншого екземпляра програми.')
        elif not store.get('bridge_token'):store.set('bridge_token','preview-only')
        self.tick_timer=QTimer(self);self.tick_timer.timeout.connect(self.tick);self.tick_timer.start(1000)
        self.scheduler=QTimer(self);self.scheduler.timeout.connect(self.schedule);self.scheduler.start(60000)
        self.next_proactive=now()+random.randint(900,1800);self.next_reminder=now()+600;self.last_cleanup=0
        self.navigate('chats')
        if start_services:QTimer.singleShot(2500,self.refresh_accounts)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.resize_grip.move(self.width()-18,self.height()-18);self.resize_grip.resize(18,18);self.resize_grip.raise_()
    def refresh_accounts(self):
        for provider in PROVIDERS:self.accounts.refresh(provider)
    def onboard(self):self.keep_dialog(ProfileDialog(self,True))
    def keep_dialog(self,d):self.dialogs.append(d);d.show();return d
    def open_window(self):self.showNormal();self.raise_();self.activateWindow()
    def work(self,fn,done,error=None):
        w=Worker(fn);self.workers.add(w)
        def ok(value):
            self.workers.discard(w)
            try:done(value)
            except RuntimeError:pass
        def fail(message):
            self.workers.discard(w)
            if error:
                try:error(message)
                except RuntimeError:pass
            else:self.statusBar().showMessage(message[:250],15000)
        w.signals.ok.connect(ok);w.signals.error.connect(fail);self.pool.start(w)
    def ai(self,task,payload,done,provider=None,model=None,instructions='',on_error=None,context=None):
        provider=provider or self.store.get('provider');model=self.store.get('model') if model is None else model
        data={'task':task,'payload':payload,'provider':provider,'model':model,'instructions':instructions,'context':context}
        jid=uid();self.store.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)',(jid,task,json.dumps(data,ensure_ascii=False),'running','',now()))
        def failed(e):
            self.store.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",(e,jid))
            if on_error:on_error(e)
            else:self.statusBar().showMessage(e[:250],20000)
        if not self.store.get('provider_'+provider,{}).get('connected'):
            failed(f'Підключіть {provider} у Налаштуваннях → AI-підписки та натисніть «Оновити моделі».');return jid
        prompt=make_prompt(task,self.store.profile(),payload,instructions)
        def execute():
            effort=self.store.get('efforts',{}).get(provider+'|'+model,'')
            supported=next((m.get('efforts',[]) for m in self.store.get('provider_'+provider,{}).get('models',[]) if m['id']==model),[])
            if effort and effort not in supported:raise ProviderError('Обраний рівень міркування більше недоступний. Оновіть вибір моделі.')
            r=query(provider,model,prompt,effort)
            required={'analyze':['minimal','natural'],'chat':['reply'],'opener':['reply'],'word':['english','ukrainian'],'exercise':['exercises'],'grade':['grade'],'hint':['hint']}[task]
            if not isinstance(r,dict) or any(k not in r for k in required):raise ProviderError('Неповна відповідь моделі. Повторіть запит.')
            for key in required:
                if key!='exercises' and not isinstance(r[key],str):raise ProviderError('Некоректний формат відповіді. Повторіть запит.')
            for key in ('errors','patterns','exercises'):
                if key in r and (not isinstance(r[key],list) or not all(isinstance(item,dict) for item in r[key])):
                    raise ProviderError('Некоректна структура відповіді моделі. Повторіть запит.')
            if task=='exercise' and (not r['exercises'] or any(not isinstance(item.get('question'),str) or not isinstance(item.get('answer'),str) for item in r['exercises'])):
                raise ProviderError('Модель не повернула повні вправи. Повторіть запит.')
            if task=='grade' and r['grade'] not in ('correct','typo','wrong'):raise ProviderError('Невідома оцінка від моделі.')
            return r
        def success(r):self.store.execute("UPDATE jobs SET status='done' WHERE id=?",(jid,));done(r)
        self.work(execute,success,failed);return jid
    def draft(self,key):
        r=self.store.one('SELECT body FROM drafts WHERE key=?',(key,));return r['body'] if r else ''
    def save_draft(self,key,text):self.store.execute('INSERT OR REPLACE INTO drafts VALUES(?,?)',(key,text))
    def header(self,title,subtitle,actions=()):
        w=QWidget();w.setObjectName('header');row=QHBoxLayout(w);row.setContentsMargins(18,10,18,10);col=QVBoxLayout();col.addWidget(label(title,'title'));col.addWidget(label(subtitle,'muted'));row.addLayout(col);row.addStretch()
        for text,fn in actions:row.addWidget(button(text,fn))
        return w
    def scroll(self,layout):
        sc=QScrollArea();sc.setWidgetResizable(True);w=panel(layout);w.setObjectName('canvas');sc.setWidget(w);return sc
    def navigate(self,page,agent=None):
        self.page=page
        if agent:self.active_agent=agent
        clear(self.workspace_layout)
        for name,b in self.nav.items():b.setChecked(name==page)
        if page=='chats':self.build_chats()
        elif page=='texts':self.build_texts()
        elif page=='words':self.build_words()
        elif page=='practice':self.build_practice()
    def show_corrections(self,result):
        d=QDialog(self);d.setWindowTitle('Правки без переривання розмови');d.resize(580,500);l=QVBoxLayout(d);view=QTextBrowser();l.addWidget(view)
        content=''
        if result.get('english_version'):content+='<h3>Твоя думка англійською</h3><p>'+html.escape(result['english_version'])+'</p>'
        for e in result.get('errors',[]):content+='<p><b>'+html.escape(str(e.get('before','')))+' → '+html.escape(str(e.get('after','')))+'</b><br>'+html.escape(str(e.get('explanation','')))+'</p>'
        view.setHtml(content)
        if result.get('patterns'):l.addWidget(button('Потренувати',lambda: self.keep_dialog(PracticeDialog(self,patterns=result['patterns'])),True))
        self.keep_dialog(d)
    def chat_context(self, aid):
        latest=self.store.one("SELECT id FROM messages WHERE agent=? AND role='user' ORDER BY created DESC LIMIT 1",(aid,))
        reply=self.store.one('SELECT m.role,m.body FROM messages m JOIN message_links l ON l.reply_to=m.id WHERE l.message=? AND m.agent=?',(latest['id'],aid)) if latest else None
        return {'reply_to':reply,'history':self.store.rows('SELECT role,body FROM messages WHERE agent=? ORDER BY created DESC LIMIT 30',(aid,))[::-1],
                'learning':self.store.conversation_learning(),
                'memory':[{'topic':m['topic'],'fact':m['fact']} for m in self.store.memories(aid)],
                'forgotten_topics':[r['topic'] for r in self.store.rows('SELECT topic FROM character_memories WHERE agent=? AND deleted=1',(aid,))]}
    def send_message(self,aid,text,message_id=None):
        if aid in self.pending_agents:return False
        agent=self.store.one('SELECT * FROM agents WHERE id=?',(aid,))
        if not agent:return False
        mid=message_id or self.store.add_message(aid,'user',text,status='sending')
        if not message_id:
            reply=self.store.get('reply_to_'+aid,'')
            if self.store.one('SELECT id FROM messages WHERE id=? AND agent=?',(reply,aid)):
                self.store.execute('INSERT INTO message_links(message,reply_to) VALUES(?,?)',(mid,reply))
            self.store.set('reply_to_'+aid,'')
            self.store.execute('INSERT OR IGNORE INTO message_assistance VALUES(?,?)',(mid,self.store.get('hint_level_'+aid,0)))
            self.store.set('hint_level_'+aid,0)
        self.store.execute("UPDATE messages SET status='sending' WHERE id=?",(mid,));self.save_draft('chat:'+aid,'');self.pending_agents.add(aid);self.set_agent_online(aid)
        history=self.store.rows('SELECT role,body FROM messages WHERE agent=? ORDER BY created DESC LIMIT 30',(aid,))[::-1]
        path=ROOT/'agents'/f'{aid}.md';instructions=path.read_text(encoding='utf-8') if path.exists() else agent['instructions']
        def done(r):
            self.pending_agents.discard(aid);self.finish_agent_presence(aid);self.store.execute("UPDATE messages SET status='sent',corrections=? WHERE id=?",(json.dumps(r,ensure_ascii=False),mid))
            self.store.execute("UPDATE jobs SET status='done' WHERE kind='chat' AND json_extract(payload,'$.context.message')=?",(mid,))
            self.store.add_message(aid,'assistant',r['reply'],unread=not self.viewing_chat(aid));self.store.add_patterns(r.get('patterns',[]))
            assistance=self.store.one('SELECT level FROM message_assistance WHERE message=?',(mid,))
            self.store.record_learning('chat:'+mid,text,r,assistance['level'] if assistance else 0)
            self.store.remember(aid,mid,text,r)
            if self.page=='chats':self.navigate('chats',self.active_agent)
            if not self.viewing_chat(aid):self.queue_notification('chat',aid)
        def failed(e):
            self.pending_agents.discard(aid);self.finish_agent_presence(aid,failed=True);self.store.execute("UPDATE messages SET status='failed' WHERE id=?",(mid,));self.statusBar().showMessage(e[:220],25000)
            if self.page=='chats':self.navigate('chats',self.active_agent)
        self.ai('chat',self.chat_context(aid),done,agent['provider'],agent['model'],instructions,failed,context={'agent':aid,'message':mid})
        if self.page=='chats':self.navigate('chats',self.active_agent)
        return True
    def build_texts(self):
        self.workspace_layout.addWidget(self.header('Твої тексти','Збережені думки → зрозумілі правки → нові навички',[('+ Додати текст',lambda:self.selection('text',''))]))
        lay=QVBoxLayout();lay.setContentsMargins(26,24,26,24);lay.setSpacing(14)
        rows=self.store.rows('SELECT t.*, (SELECT max(version) FROM analyses WHERE text_id=t.id) analyzed FROM texts t ORDER BY updated DESC LIMIT ?',(self.text_limit,))
        if not rows:lay.addWidget(label('Тут з’являться збережені промпти.\nУвімкни джерела в налаштуваннях або додай текст вручну.','muted',True))
        for r in rows:
            card=QFrame();card.setObjectName('card');c=QVBoxLayout(card);c.setContentsMargins(20,18,20,16)
            status=' · проаналізовано' if r['analyzed']==r['version'] else (' · текст змінився' if r['analyzed'] else '')
            c.addWidget(label(r['source']+' · '+date(r['updated'])+status,'section'));body=label(r['body'][:700]+('…' if len(r['body'])>700 else ''),'',True);body.setTextFormat(Qt.TextFormat.PlainText);body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);c.addWidget(body)
            buttons=QHBoxLayout();buttons.addWidget(button('Analyze',lambda _,r=r:self.keep_dialog(AnalysisDialog(self,r)),True));buttons.addWidget(button('Збережено ✓' if r['pinned'] else 'Зберегти',lambda _,r=r:self.pin(r)));buttons.addStretch();buttons.addWidget(button('Видалити',lambda _,r=r:self.delete_text(r)));c.addLayout(buttons);lay.addWidget(card)
        if len(rows)>=self.text_limit:
            def more():self.text_limit+=200;self.navigate('texts')
            lay.addWidget(button('Показати старіші записи',more))
        lay.addStretch();self.workspace_layout.addWidget(self.scroll(lay))
    def pin(self,r):self.store.execute('UPDATE texts SET pinned=? WHERE id=?',(int(not r['pinned']),r['id']));self.navigate('texts')
    def delete_text(self,r):
        if QMessageBox.question(self,'Видалення','Видалити запис та його розбори?')!=QMessageBox.StandardButton.Yes:return
        self.store.execute('DELETE FROM analyses WHERE text_id=?',(r['id'],));self.store.execute('DELETE FROM texts WHERE id=?',(r['id'],));self.navigate('texts')
    def build_words(self):
        self.workspace_layout.addWidget(self.header('Словники','Слова, які ти хочеш повернути в розмову',[('+ Додати слово',lambda:self.keep_dialog(WordDialog(self)))]))
        lay=QVBoxLayout();lay.setContentsMargins(28,24,28,24);lay.setSpacing(14)
        dictionaries=self.store.rows('SELECT * FROM dictionaries ORDER BY name')
        if not dictionaries:lay.addWidget(label('Створи перший словник, додаючи слово.\nУ будь-якій програмі: виділи слово → Ctrl+Alt+W.','muted',True))
        for d in dictionaries:
            lay.addWidget(label(d['name'],'title'))
            for w in self.store.rows('SELECT * FROM words WHERE dictionary=? ORDER BY created DESC',(d['id'],)):
                card=QFrame();card.setObjectName('card');c=QVBoxLayout(card);c.setContentsMargins(18,14,18,14);c.addWidget(label(w['english'],'section'));c.addWidget(label(w['ukrainian'],'',True));c.addWidget(label(w['example'],'muted',True));lay.addWidget(card)
        lay.addStretch();self.workspace_layout.addWidget(self.scroll(lay))
    def build_practice(self):
        self.workspace_layout.addWidget(self.header('Практика','Менше вгадування правил. Більше власних речень.'))
        lay=QVBoxLayout();lay.setContentsMargins(40,35,40,30);lay.setSpacing(18)
        due=self.store.due();count=self.store.one('SELECT count(*) n FROM events WHERE kind="review"')['n']
        row=QHBoxLayout()
        for number,text in [(str(sum(r['kind']=='word' for r in due)),'слів на повторення'),(str(sum(r['kind']=='construction' for r in due)),'конструкцій на практику'),(str(count),'відповідей збережено')]:
            frame=QFrame();frame.setObjectName('card');c=QVBoxLayout(frame);c.setContentsMargins(22,22,22,22);big=label(number);big.setStyleSheet('font-size:38px;color:#70c3ee;');c.addWidget(big);c.addWidget(label(text,'muted'));row.addWidget(frame)
        lay.addLayout(row);lay.addWidget(button('Почати коротку сесію',lambda:self.keep_dialog(PracticeDialog(self)),True));lay.addWidget(label('Твої конструкції','title'))
        for p in self.store.learning_stats()[:20]:
            card=QFrame();card.setObjectName('card');c=QVBoxLayout(card);c.addWidget(label(p['pattern'],'section'));c.addWidget(label(p['explanation'],'',True));c.addWidget(label(p['example'],'muted',True));c.addWidget(label(f"Помилки: {p['mistakes']} · Самостійно правильно: {p['independent']} · З допомогою: {p['assisted']}",'muted',True));lay.addWidget(card)
        failures=self.store.rows("SELECT * FROM jobs WHERE status='failed' ORDER BY created DESC LIMIT 8")
        if failures:
            lay.addWidget(label('Запити, що потребують уваги','section'))
            for job in failures:
                card=QFrame();card.setObjectName('card');c=QVBoxLayout(card);c.addWidget(label(job['kind']+' · '+date(job['created']),'muted'));c.addWidget(label(job['error'][:260],'',True));c.addWidget(button('Переглянути й повторити',lambda _,j=job:self.retry_job(j)));lay.addWidget(card)
        lay.addStretch();self.workspace_layout.addWidget(self.scroll(lay))
    def retry_job(self,job):
        data=json.loads(job['payload'])
        if data['task']=='hint':
            self.navigate('chats',self.active_agent)
            self.statusBar().showMessage('Відкрий «Допоможи сформулювати» для поточної відповіді.',10000)
            return
        if data['task']=='chat' and (data.get('context') or {}).get('agent'):
            self.navigate('chats',data['context']['agent']);return
        d=QDialog(self);d.setWindowTitle('Повторити запит');d.resize(650,550);l=QVBoxLayout(d)
        l.addWidget(label('Повтор використовує початкового провайдера: '+data['provider']+'.\nРезультат буде показано тут.','muted',True))
        browser=QTextBrowser();browser.setPlainText(json.dumps(data['payload'],ensure_ascii=False,indent=2));l.addWidget(browser)
        b=button('Повторити',primary=True);l.addWidget(b)
        def retry():
            b.setEnabled(False)
            def done(result):
                browser.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));b.setEnabled(True);self.store.execute("UPDATE jobs SET status='done' WHERE id=?",(job['id'],))
                context=data.get('context') or {}
                if data['task']=='analyze' and context.get('record'):
                    self.store.save_analysis(context['record'],context['selected'],result)
            self.ai(data['task'],data['payload'],done,provider=data['provider'],model=data['model'],instructions=data.get('instructions',''),on_error=lambda e:(browser.setPlainText(e),b.setEnabled(True)),context=data.get('context'))
        b.clicked.connect(retry);self.keep_dialog(d)
    def selection(self,kind,text):
        if kind=='word':self.keep_dialog(WordDialog(self,text));return
        d=QDialog(self);d.setWindowTitle('Зберегти текст');d.resize(640,450);lay=QVBoxLayout(d);lay.addWidget(label('Текст для майбутнього аналізу','title'));editor=QPlainTextEdit(text);editor.setPlaceholderText('Встав текст, якщо застосунок не надав виділення.');lay.addWidget(editor)
        def save():
            if editor.toPlainText().strip():self.store.save_text('Додано вручну',editor.toPlainText(),final=True);d.accept();self.navigate('texts')
        lay.addWidget(button('Зберегти локально',save,True));self.keep_dialog(d)
    def show_settings(self):self.keep_dialog(SettingsDialog(self))
    def export_backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Експорт',str(ROOT/'EnglishOrbit-backup.zip'),'Backup (*.zip)')
        if path:
            try:self.store.backup(path,ROOT/'agents');QMessageBox.information(self,'Готово','Резервну копію збережено. Авторизаційні дані не включені.')
            except Exception as e:QMessageBox.warning(self,'Помилка',str(e))
    def import_backup(self):
        path,_=QFileDialog.getOpenFileName(self,'Імпорт','','Backup (*.zip)')
        if not path:return
        if self.workers:QMessageBox.information(self,'Зачекайте','Дочекайтеся завершення AI-запитів перед імпортом.');return
        if QMessageBox.question(self,'Імпорт','Замінити локальну базу? Перед цим буде створено резервну копію поточного стану.')!=QMessageBox.StandardButton.Yes:return
        try:self.collector.flush();self.store.restore(path,ROOT/'agents');self.navigate('chats');QMessageBox.information(self,'Готово','Дані відновлено. Перезапустіть програму для перепідключення розширення.')
        except Exception as e:QMessageBox.warning(self,'Помилка',str(e))
    def set_autostart(self,enabled):
        if not self.services or os.name!='nt':return
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run',0,winreg.KEY_SET_VALUE) as key:
                if enabled:winreg.SetValueEx(key,'EnglishOrbit',0,winreg.REG_SZ,f'"{ROOT / ".qt-env/Scripts/pythonw.exe"}" "{ROOT / "main.py"}" --tray')
                else:
                    try:winreg.DeleteValue(key,'EnglishOrbit')
                    except FileNotFoundError:pass
        except OSError as e:self.statusBar().showMessage('Автозапуск не налаштовано: '+str(e),10000)
    def tick(self):
        self.collector.tick()
        if now()-self.last_cleanup>3600:self.store.cleanup();self.last_cleanup=now()
        self.deliver_notifications()
    def deliver_notifications(self):
        if not self.notifications or self.store.get('dnd'):return
        if not self.store.get('hours_start')<=datetime.now().hour<self.store.get('hours_end'):return
        # Keyboard/mouse activity in another app must not block incoming chat.
        # Only practice reminders wait for a quiet moment; never block chats behind them.
        for kind,aid in list(self.notifications):
            capacity=max(1,min(3,(self.screen().availableGeometry().height()-46)//88))
            if len(self.popups)>=capacity:break
            if kind=='review' and idle_seconds()<20:continue
            self.notifications.remove((kind,aid))
            agent=self.store.one('SELECT * FROM agents WHERE id=?',(aid,)) if aid else None
            if kind=='chat':
                if not agent or self.viewing_chat(aid):continue
                unseen=self.store.rows("SELECT id FROM messages WHERE agent=? AND role='assistant' AND unread=1 AND id NOT IN (SELECT message_id FROM notification_receipts)",(aid,))
                if not unseen:continue
            self.show_notification(agent,kind=='review')
            if kind=='chat' and self.popup.isVisible():
                for message in unseen:self.store.execute('INSERT OR IGNORE INTO notification_receipts VALUES(?,?)',(message['id'],now()))
    def viewing_chat(self,aid):
        return self.isVisible() and not self.isMinimized() and self.isActiveWindow() and self.page=='chats' and self.active_agent==aid
    def queue_notification(self,kind,aid):
        item=(kind,aid)
        if kind=='chat' and self.viewing_chat(aid):return
        if item not in self.notifications:self.notifications.append(item)
    def show_notification(self,agent=None,review=False,preview=False):
        self.popup=Popup(self,agent,review,preview);self.popups.append(self.popup)
        self.popup.show();self.popup.raise_();self.layout_toasts()
    def remove_toast(self,toast):
        if toast in self.popups:self.popups.remove(toast)
        self.layout_toasts()
    def layout_toasts(self):
        g=(self.screen() or QApplication.primaryScreen()).availableGeometry()
        bottom=g.bottom()+1-7
        for toast in reversed(self.popups):
            bottom-=toast.height();toast.move(g.right()+1-toast.width()-5,bottom);bottom-=8
        if len(self.popups)>1:
            if self.hide_all_toast is None:self.hide_all_toast=HideAllToast(self.hide_notifications)
            self.hide_all_toast.move(g.right()+1-320-5,bottom-32)
            self.hide_all_toast.show();self.hide_all_toast.raise_()
        elif self.hide_all_toast:self.hide_all_toast.hide()
    def hide_notifications(self):
        # Dismissal preserves unread state but must not replay queued messages later.
        for kind,aid in self.notifications:
            if kind=='chat':
                for m in self.store.rows("SELECT id FROM messages WHERE agent=? AND role='assistant' AND unread=1",(aid,)):
                    self.store.execute('INSERT OR IGNORE INTO notification_receipts VALUES(?,?)',(m['id'],now()))
        self.notifications.clear()
        for toast in list(self.popups):toast.close()
        if self.hide_all_toast:self.hide_all_toast.hide()
    def test_notification(self):
        agent=self.store.one('SELECT * FROM agents ORDER BY rowid LIMIT 1')
        if agent:self.show_notification(agent,preview=True)
    def schedule(self):
        if not self.services or not self.store.get('onboarded') or self.store.get('dnd'):return
        dt=datetime.now()
        if not self.store.get('hours_start')<=dt.hour<self.store.get('hours_end'):return
        today=dt.strftime('%Y-%m-%d');stats=self.store.get('schedule_stats',{})
        if stats.get('day')!=today:stats={'day':today,'chats':0,'reviews':0}
        if now()>=self.next_reminder and stats['reviews']<self.store.get('review_reminders') and self.store.due():
            self.queue_notification('review',None);stats['reviews']+=1;self.next_reminder=now()+7200
        if now()>=self.next_proactive and stats['chats']<self.store.get('daily_chats'):
            agents=self.store.rows('SELECT * FROM agents WHERE enabled=1');random.shuffle(agents)
            for agent in agents:
                if agent['id'] in self.pending_agents or not self.store.get('provider_'+agent['provider'],{}).get('connected'):continue
                last=self.store.one('SELECT * FROM messages WHERE agent=? ORDER BY created DESC LIMIT 1',(agent['id'],))
                if last and (last['role']=='assistant' or last['status']!='sent'):continue
                aid=agent['id'];self.pending_agents.add(aid);self.set_agent_online(aid);stats['chats']+=1
                instructions=(ROOT/'agents'/f'{aid}.md').read_text(encoding='utf-8')
                def done(result,aid=aid):
                    self.pending_agents.discard(aid);self.finish_agent_presence(aid);self.store.add_message(aid,'assistant',result['reply'],unread=1);self.queue_notification('chat',aid)
                    if self.page=='chats':self.navigate('chats',self.active_agent)
                self.ai('opener',self.chat_context(aid),done,agent['provider'],agent['model'],instructions,lambda e,aid=aid:(self.pending_agents.discard(aid),self.finish_agent_presence(aid,failed=True)));break
            self.next_proactive=now()+random.randint(3600,9000)
        self.store.set('schedule_stats',stats)
    def closeEvent(self,event):
        if not self.exiting and self.services:event.ignore();self.hide()
        else:
            for toast in list(self.popups):toast.close()
            if self.hide_all_toast:self.hide_all_toast.close()
            event.accept()
    def quit(self):
        self.exiting=True;self.tick_timer.stop();self.scheduler.stop();self.collector.flush()
        if self.native:self.native.stop();self.native.wait(1500)
        if self.bridge:self.bridge.stop()
        self.tray.hide()
        if self.popup:self.popup.close()
        self.close();QApplication.quit()
