"""Settings replacement: one sidebar shell, no legacy tab dialog."""
import json, math
from PySide6.QtCore import Qt, QSize, QRectF, QPointF, QUrl, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QIcon, QPixmap, QPainterPath, QLinearGradient, QDesktopServices
from PySide6.QtWidgets import *
from core import ROOT
from providers import PROVIDERS, login, discover
from design import Surface, TitleBar, Toggle, Portrait, text as base_text

def text(value,size=18,color="#f3f5fa",bold=False):
    return base_text(value,max(12,round(size*.78)),color,bold)

STYLE='''
QDialog#settings {background:#101b25;}
QWidget#settingsNav {background:#14212d;border-right:1px solid #293e50;}
QPushButton#settingsNavButton {background:transparent;text-align:left;padding:10px 10px;font-size:14px;font-weight:400;border-radius:6px;color:#e4edf7;}
QPushButton#settingsNavButton:checked {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #173b55,stop:1 #1d3e58);border-left:4px solid #42c5ff;}
QPushButton#settingsNavButton:hover {background:#203648;}
QFrame#settingsCard {background:#1b2835;border:0;border-radius:6px;}
QFrame#settingsRow {background:rgba(21,34,47,175);border:1px solid #2b4256;border-radius:6px;}
QFrame#settingsNote {background:#1b2c3c;border:1px solid #2c455d;border-radius:6px;}
QFrame#settingsFooter {background:#111e29;border-top:1px solid #2d4355;}
QDialog#settings QComboBox,QDialog#settings QPlainTextEdit,QDialog#settings QLineEdit {font-size:14px;border-color:#354e63;min-height:20px;padding:8px;}
QDialog#settings QComboBox::drop-down {border:0;width:32px;}
QDialog#settings QComboBox::down-arrow {image:url(ARROW_ASSET);width:16px;height:10px;}
QPushButton#settingsAction {font-size:14px;background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #269fec,stop:1 #208fdf);border:1px solid #48b8f5;border-radius:10px;color:white;padding:9px 12px;}
QPushButton#settingsAction:disabled {background:#223444;border-color:#304558;color:#8294a6;}
QPushButton#settingsAction:hover {background:#32acf7;}
QPushButton#settingsOutline {background:transparent;border:1px solid #77c9fa;border-radius:10px;font-size:14px;padding:8px 14px;}
QPushButton#settingsLink {background:transparent;color:#89c9f5;font-size:16px;text-align:left;padding:4px 0;}
QPushButton#step {background:#213343;border:1px solid #3a5368;border-radius:8px;padding:0;font-size:26px;color:#c5dcef;}
QLineEdit#stepValue {background:#152330;border:1px solid #30495d;border-radius:0;padding:0;font-size:19px;}
'''.replace('ARROW_ASSET',(ROOT/'assets/chevron-down.svg').as_posix())

def icon(kind,size=32,color='#b7cfe4'):
    pix=QPixmap(size,size);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.scale(size/32,size/32);p.setPen(QPen(QColor(color),1.8));p.setBrush(Qt.NoBrush)
    if kind in ('profile','user'):
        p.drawEllipse(11,3,10,10);path=QPainterPath();path.moveTo(5,28);path.cubicTo(3,12,29,12,27,28);path.closeSubpath();p.drawPath(path)
    elif kind=='calendar':
        p.drawRoundedRect(4,6,24,23,2,2);p.drawLine(4,13,28,13);p.drawLine(10,2,10,10);p.drawLine(22,2,22,10)
    elif kind=='folder':
        path=QPainterPath();path.moveTo(3,27);path.lineTo(3,6);path.lineTo(12,6);path.lineTo(16,10);path.lineTo(29,10);path.lineTo(29,27);path.closeSubpath();p.drawPath(path)
    elif kind in ('export','import'):
        p.drawLine(4,22,4,29);p.drawLine(4,29,28,29);p.drawLine(28,29,28,22);p.drawLine(16,3,16,23)
        y=20 if kind=='export' else 5;dy=-6 if kind=='export' else 6;p.drawLine(16,y,9,y+dy);p.drawLine(16,y,23,y+dy)
    elif kind in ('clock','info'):
        p.drawEllipse(4,4,24,24)
        if kind=='clock':p.drawLine(16,8,16,16);p.drawLine(16,16,22,19)
        else:p.drawLine(16,14,16,23);p.drawPoint(16,10)
    elif kind=='ai':
        for y in (3,10,17):
            path=QPainterPath();path.moveTo(3,y+6);path.lineTo(16,y);path.lineTo(29,y+6);path.lineTo(16,y+12);path.closeSubpath();p.drawPath(path)
    else:
        path=QPainterPath();path.moveTo(7,2);path.lineTo(21,2);path.lineTo(27,9);path.lineTo(27,29);path.lineTo(7,29);path.closeSubpath();p.drawPath(path);p.drawLine(20,2,20,10);p.drawLine(20,10,27,10)
        for y in (15,20,25):p.drawLine(11,y,22,y)
    p.end();return QIcon(pix)

def glyph(kind,size=32,color='#b7cfe4'):
    w=QLabel();w.setPixmap(icon(kind,size,color).pixmap(size,size));w.setFixedSize(size,size);return w

def action(title,callback,primary=True):
    b=QPushButton(title);b.setObjectName('settingsAction' if primary else 'settingsOutline');b.setCursor(Qt.PointingHandCursor);b.clicked.connect(callback);return b

def card(title=None):
    w=QFrame();w.setObjectName('settingsCard');l=QVBoxLayout(w);l.setContentsMargins(16,12,16,12);l.setSpacing(10)
    if title:l.addWidget(text(title,23,bold=True))
    return w,l

def note(value,kind='info'):
    w=QFrame();w.setObjectName('settingsNote');l=QHBoxLayout(w);l.setContentsMargins(16,12,16,12);l.setSpacing(16);l.addWidget(glyph(kind,27,'#49c1ff'));l.addWidget(text(value,15,'#adc5dd'),1);return w

def divider():
    w=QFrame();w.setFixedHeight(1);w.setStyleSheet('background:#2a4052;border:0;');return w

class Stepper(QWidget):
    def __init__(self,maximum,value):
        super().__init__();self.maximum=maximum;self.current=value;l=QHBoxLayout(self);l.setContentsMargins(0,0,0,0);l.setSpacing(0)
        self.minus=QPushButton('−');self.plus=QPushButton('+');self.display=QLineEdit(str(value));self.display.setObjectName('stepValue');self.display.setReadOnly(True);self.display.setAlignment(Qt.AlignCenter);self.display.setFixedSize(54,44)
        for b in (self.minus,self.plus):b.setObjectName('step');b.setFixedSize(42,44)
        self.minus.clicked.connect(lambda:self.setValue(self.current-1));self.plus.clicked.connect(lambda:self.setValue(self.current+1));l.addWidget(self.minus);l.addWidget(self.display);l.addWidget(self.plus);self.setValue(value)
    def setValue(self,value):self.current=max(0,min(self.maximum,value));self.display.setText(str(self.current));self.minus.setEnabled(self.current>0);self.plus.setEnabled(self.current<self.maximum)
    def value(self):return self.current

class ProfileThumbnail(QWidget):
    def __init__(self,path):super().__init__();self.path=path;self.setFixedSize(64,64)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);clip=QPainterPath();clip.addEllipse(0,0,64,64);p.setClipPath(clip);p.fillRect(self.rect(),QColor('#536574'));photo=QPixmap(self.path)
        if not photo.isNull():
            scaled=photo.scaled(64,64,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);p.drawPixmap((64-scaled.width())//2,(64-scaled.height())//2,scaled)
        else:
            p.setPen(Qt.NoPen);p.setBrush(QColor('#d7e4ee'));p.drawEllipse(22,13,21,21);p.drawEllipse(12,38,42,42)

class ProviderMark(QWidget):
    def __init__(self,name):super().__init__();self.name=name;self.setFixedSize(64,64)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen)
        if self.name=='Gemini':
            g=QLinearGradient(0,5,62,60)
            for at,c in [(0,'#e2509d'),(.35,'#6384fd'),(.65,'#31a5fb'),(1,'#6ccf75')]:g.setColorAt(at,QColor(c))
            p.setBrush(g);path=QPainterPath();path.moveTo(32,1);path.cubicTo(37,22,42,27,63,32);path.cubicTo(42,37,37,42,32,63);path.cubicTo(27,42,22,37,1,32);path.cubicTo(22,27,27,22,32,1);p.drawPath(path)
        else:
            p.setBrush(QColor('#04a58b' if self.name=='ChatGPT' else '#d87553'));p.drawRoundedRect(0,0,64,64,12,12);p.translate(32,32);p.setBrush(Qt.NoBrush);p.setPen(QPen(QColor('white'),2.8))
            if self.name=='Claude':
                for i in range(12):p.rotate(30);p.drawLine(5,0,24 if i%2 else 21,0)
            else:
                for i in range(6):
                    p.rotate(60);path=QPainterPath();path.moveTo(-4,-10);path.lineTo(9,-18);path.cubicTo(24,-25,30,-7,18,1);path.lineTo(8,7);p.drawPath(path)

class SettingsDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.store=owner.store;self.setObjectName('settings');self.setStyleSheet(STYLE);self.setWindowTitle('Налаштування · English Orbit');self.setWindowFlags(self.windowFlags()|Qt.FramelessWindowHint);self.setSizeGripEnabled(True)
        available=QApplication.primaryScreen().availableGeometry();self.resize(min(1000,available.width()-40),min(800,available.height()-40));self.setMinimumSize(850,600)
        outer=QVBoxLayout(self);outer.setContentsMargins(1,1,1,1);outer.setSpacing(0);bar=TitleBar(self);bar.setFixedHeight(32);outer.addWidget(bar)
        body=QHBoxLayout();body.setSpacing(0);outer.addLayout(body,1)
        nav=QWidget();nav.setObjectName('settingsNav');nav.setFixedWidth(200);nl=QVBoxLayout(nav);nl.setContentsMargins(8,18,8,12);nl.setSpacing(4);heading=text('Налаштування',26,bold=True);heading.setContentsMargins(12,0,0,14);nl.addWidget(heading);body.addWidget(nav)
        self.pages=QStackedWidget();body.addWidget(self.pages,1);self.nav_buttons=[]
        self.statuses={};self.refresh_buttons={};self.connect_buttons={};self.limit_labels={};self.limit_buttons={};self.plan_labels={};self.login_pending=owner.accounts.pending;self.busy=owner.accounts.busy;self.effort_values=dict(self.store.get("efforts",{}));self.effort_key=None;self.provider_actions=[];self.responsive_rows=[];self.nav_panel=nav
        for i,(title,kind,subtitle,builder) in enumerate([
            ('AI-підписки','ai','Твої підписки. Твої моделі.',self.build_ai),('Збір текстів','document','Твої тексти стають матеріалом для навчання',self.build_capture),('Розклад','calendar','Англійська у твоєму ритмі',self.build_schedule),('Профіль і дані','user','Усе важливе залишається тут',self.build_data)]):
            b=QPushButton('   '+title);b.setObjectName('settingsNavButton');b.setIcon(icon(kind));b.setIconSize(QSize(22,22));b.setCheckable(True);b.setMinimumHeight(42);b.clicked.connect(lambda checked,index=i:self.select_page(index));nl.addWidget(b);self.nav_buttons.append(b)
            page=Surface();l=QVBoxLayout(page);l.setContentsMargins(20,18,20,18);l.setSpacing(12);l.addWidget(text(title,38,bold=True));l.addWidget(text(subtitle,22,'#94adc5'));builder(l);l.addStretch()
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.pages.addWidget(scroll)
        nl.addStretch();footer=QFrame();footer.setObjectName('settingsFooter');fl=QHBoxLayout(footer);fl.setContentsMargins(18,10,18,10);fl.addStretch();self.save_button=QPushButton('Зберегти налаштування');self.save_button.setObjectName('primary');self.save_button.setMinimumSize(210,38);self.save_button.clicked.connect(self.save);fl.addWidget(self.save_button);outer.addWidget(footer);self.select_page(0);self.owner.accounts.changed.connect(self.account_changed)
        if self.owner.services:QTimer.singleShot(0,self.owner.refresh_accounts)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        narrow=self.width()<1000
        self.nav_panel.setFixedWidth(180 if narrow else 200)
        for actions in self.provider_actions+self.responsive_rows:actions.setDirection(QBoxLayout.TopToBottom if narrow else QBoxLayout.LeftToRight)
    def select_page(self,index):
        self.pages.setCurrentIndex(index)
        for i,b in enumerate(self.nav_buttons):b.setChecked(i==index)
    def build_ai(self,l):
        l.addWidget(text('Вхід через офіційні клієнти, без API-ключів.',17,'#8fa9c1'))
        box,rows=card();rows.setContentsMargins(24,8,24,8);rows.setSpacing(0)
        for i,p in enumerate(PROVIDERS):
            if i:rows.addWidget(divider())
            row=QHBoxLayout();row.setContentsMargins(0,16,0,16);row.setSpacing(14);row.addWidget(ProviderMark(p),0,Qt.AlignTop)
            col=QVBoxLayout();col.setSpacing(8);title=QHBoxLayout();title.addWidget(text(p,24,bold=True));plan=text('',15,'#7bd0ff',True);plan.hide();title.addWidget(plan);title.addStretch();self.plan_labels[p]=plan;col.addLayout(title)
            status=text('',17,'#a6bfd6');self.statuses[p]=status;col.addWidget(status)
            limits=QPushButton('Переглянути ліміти');limits.setObjectName('settingsLink');limits.setCheckable(True);details=text('',14,'#9cb7cf');details.hide();limits.toggled.connect(details.setVisible);col.addWidget(limits);col.addWidget(details);self.limit_labels[p]=details;self.limit_buttons[p]=limits;row.addLayout(col,1)
            connect=action('Підключити',lambda checked=False,provider=p:self.connect(provider));refresh=action('Оновити моделі',lambda checked=False,provider=p:self.refresh(provider));self.connect_buttons[p]=connect;self.refresh_buttons[p]=refresh
            connect.setMinimumWidth(105);refresh.setMinimumWidth(135);actions=QBoxLayout(QBoxLayout.LeftToRight);actions.setSpacing(16);actions.addWidget(connect);actions.addWidget(refresh);self.provider_actions.append(actions);row.addLayout(actions);rows.addLayout(row);self.update_provider(p)
        l.addWidget(box)
        box,c=card('Аналіз і практика');c.addWidget(text('Налаштування для аналізу текстів і практичних завдань.',17,'#94adc5'))
        row=QHBoxLayout();row.setSpacing(24);self.provider=QComboBox();self.provider.addItems(PROVIDERS);self.provider.setCurrentText(self.store.get('provider'));self.model=QComboBox();self.effort=QComboBox();self.model.currentIndexChanged.connect(self.update_efforts)
        for title,widget in [('Провайдер',self.provider),('Модель',self.model)]:
            col=QVBoxLayout();col.addWidget(text(title,17,bold=True));col.addWidget(widget);row.addLayout(col,1)
        self.provider.currentTextChanged.connect(self.models);self.models(self.store.get('provider'),self.store.get('model'));c.addLayout(row);c.addWidget(text('Рівень міркування',17,bold=True));c.addWidget(self.effort);self.effort.currentIndexChanged.connect(self.remember_effort);self.update_efforts();c.addWidget(text('Без API-ключів і автоматичної зміни провайдера. Якщо каталог або ліміти недоступні, програма так і повідомляє.',15,'#91a9bf'));l.addWidget(box)
    def update_provider(self,p):
        info=self.store.get('provider_'+p,{});connected=bool(info.get('connected'));pending=p in self.login_pending or 'Очікується' in info.get('status','')
        status=('Підключено  ·  '+str(len(info.get('models',[])))+' моделей') if connected else ('Завершіть вхід' if pending else 'Не підключено')
        identity=info.get('account_name') or ('Ім’я акаунту недоступне' if connected else '')
        self.statuses[p].setText('●  '+status+('\n'+identity if identity else ''));self.statuses[p].setStyleSheet('color:'+('#49db94' if connected else '#f6c257' if pending else '#9aafc3')+';font-size:14px;');self.statuses[p].setToolTip(info.get('status',''))
        self.connect_buttons[p].setText('Вийти' if connected else 'Очікуємо вхід…' if pending else 'Підключити');self.refresh_buttons[p].setEnabled(p not in self.busy);self.connect_buttons[p].setEnabled(p not in self.busy and not pending)
        self.limit_buttons[p].setVisible(connected);limits=info.get('limits');self.limit_labels[p].setText(json.dumps(limits,ensure_ascii=False,indent=2) if limits else 'Ліміти: дані недоступні.');plan=info.get('plan') or info.get('planType')
        self.plan_labels[p].setText(str(plan or ''));self.plan_labels[p].setVisible(bool(plan))
    def models(self,provider=None,selected=None):
        old=(self.model.currentData() if provider is None else '') if selected is None else selected;self.model.clear();self.model.addItem('Вибір офіційного клієнта','')
        for m in self.store.get('provider_'+self.provider.currentText(),{}).get('models',[]):self.model.addItem(m.get('name') or m['id'],m['id'])
        if old and self.model.findData(old)<0:self.model.addItem(str(old)+' · недоступна в каталозі',old)
        self.model.setCurrentIndex(max(0,self.model.findData(old or '')))
    def remember_effort(self):
        if self.effort_key:self.effort_values[self.effort_key]=self.effort.currentData() or ''
    def update_efforts(self):
        self.effort_key=self.provider.currentText()+'|'+str(self.model.currentData() or '')
        catalog=self.store.get('provider_'+self.provider.currentText(),{}).get('models',[])
        choices=next((m.get('efforts',[]) for m in catalog if m['id']==self.model.currentData()),[])
        self.effort.blockSignals(True);self.effort.clear();self.effort.addItem('Автоматично — вибір моделі' if choices else 'Клієнт не надає вибору для цієї моделі','')
        for value in choices:self.effort.addItem(value,value)
        self.effort.setCurrentIndex(max(0,self.effort.findData(self.effort_values.get(self.effort_key,''))));self.effort.setEnabled(bool(choices));self.effort.blockSignals(False)
    def account_changed(self,p):
        self.update_provider(p)
        error=self.owner.accounts.errors.get(p)
        if error:self.statuses[p].setText(error)
        if self.provider.currentText()==p:self.models()
    def connect(self,p):
        if self.store.get('provider_'+p,{}).get('connected'):self.owner.accounts.logout(p)
        else:self.owner.accounts.connect(p)
    def refresh(self,p):self.owner.accounts.refresh(p)
    def build_capture(self,l):
        box,c=card('Джерела текстів');self.enabled=Toggle('');self.enabled.setChecked(self.store.get('capture'));self.all=Toggle('');self.all.setChecked(self.store.get('listen_all'))
        self.setting_row(c,'Збирати відредаговані англійські тексти',self.enabled);c.addWidget(divider());self.setting_row(c,'Listen to everything',self.all);c.addWidget(text('Усі доступні поля, коли активна англійська розкладка.',16,'#97afc7'));l.addWidget(box)
        box,c=card('Застосунки та сайти');row=QHBoxLayout();row.setSpacing(20)
        self.apps=QPlainTextEdit('\n'.join(self.store.get('apps')));self.sites=QPlainTextEdit('\n'.join(self.store.get('sites')))
        for title,help,widget in [('Застосунки','Назви .exe, по одній на рядок',self.apps),('Сайти Chrome','Домени, по одному на рядок',self.sites)]:
            col=QVBoxLayout();col.addWidget(text(title,19,bold=True));col.addWidget(text(help,15,'#97afc7'));widget.setFixedHeight(155);col.addWidget(widget);row.addLayout(col,1)
        c.addLayout(row);c.addWidget(note('Зберігається текст після редагувань. Після 20 секунд паузи запис зберігається; продовження того самого тексту оновлює його.'));l.addWidget(box)
        box,c=card('Розширення Chrome');c.addWidget(text('chrome://extensions → Режим розробника → Завантажити розпаковане розширення.',16,'#97afc7'));c.addWidget(action('Відкрити папку розширення',lambda:self.open_path(ROOT/'chrome-extension'),False))
        self.token=QLineEdit(self.store.get('bridge_token',''));self.token.setReadOnly(True);self.token.setEchoMode(QLineEdit.Password);row=QHBoxLayout();row.addWidget(self.token,1);row.addWidget(action('Скопіювати код',lambda:QApplication.clipboard().setText(self.token.text()),False));c.addLayout(row);l.addWidget(box)
        l.addWidget(note('Автоматичний збір залежить від доступності поля через Windows UI Automation. Ctrl+Alt+S — зберегти текст; Ctrl+Alt+W — додати слово.'))
    def setting_row(self,l,title,widget):
        row=QHBoxLayout();row.setContentsMargins(0,4,0,4);row.addWidget(text(title,19),1);row.addWidget(widget);l.addLayout(row)
    def build_schedule(self,l):
        box,c=card('Час для спілкування');c.addWidget(text('Коли можна надсилати повідомлення',18,'#95b4d1'));row=QHBoxLayout();row.setSpacing(28)
        self.start=QComboBox();self.end=QComboBox()
        for title,widget,key,hours in [('Початок',self.start,'hours_start',range(24)),('Завершення',self.end,'hours_end',range(1,25))]:
            for h in hours:widget.addItem(icon('clock'),f'{h:02}:00',h)
            widget.setCurrentIndex(widget.findData(self.store.get(key)));col=QVBoxLayout();col.addWidget(text(title,18));col.addWidget(widget);row.addLayout(col,1)
        c.addLayout(row);l.addWidget(box)
        box,c=card('Денний ліміт');self.daily=Stepper(20,self.store.get('daily_chats'));self.reminders=Stepper(5,self.store.get('review_reminders'));self.setting_row(c,'Нові розмови',self.daily);c.addWidget(divider());self.setting_row(c,'Запрошення до повторення',self.reminders);l.addWidget(box)
        box,c=card('Додатково');self.dnd=Toggle('');self.dnd.setChecked(self.store.get('dnd'));self.autostart=Toggle('');self.autostart.setChecked(self.store.get('autostart'));self.setting_row(c,'Не турбувати',self.dnd);c.addWidget(divider());self.setting_row(c,'Автозапуск із Windows',self.autostart);c.addWidget(note('Повідомлення чату з’являються одразу, навіть коли програма згорнута.\nНагадування про практику чекають 20 секунд бездіяльності. Фокус не перемикається.'));c.addWidget(action('Перевірити сповіщення',self.owner.test_notification,False));l.addWidget(box)
    def data_row(self,kind,title,subtitle,button=None):
        w=QFrame();w.setObjectName('settingsRow');r=QHBoxLayout(w);r.setContentsMargins(20,14,16,14);r.setSpacing(22);r.addWidget(ProfileThumbnail(self.store.get('avatar','')) if kind=='avatar' else glyph(kind,38));col=QVBoxLayout();col.setSpacing(4);col.addWidget(text(title,19,bold=True));description=text(subtitle.replace('\\','\\\u200b').replace('/','/\u200b'),17,'#a2bbd3');description.setMinimumWidth(0);description.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);col.addWidget(description);r.addLayout(col,1)
        if button:r.addWidget(button)
        return w
    def build_data(self,l):
        box,c=card('Профіль');c.addWidget(self.data_row('avatar','Особистий профіль','Ім’я, аватар і навчальні цілі',action('Редагувати',self.edit_profile)));l.addWidget(box)
        box,c=card('Локальні дані');c.addWidget(self.data_row('folder','Папка з даними',str(ROOT/'data'),action('Відкрити',lambda:self.open_path(ROOT/'data'),False)));c.addWidget(self.data_row('document','Інструкції для AI','AGENT.md',action('Відкрити',lambda:self.open_path(ROOT/'agents/AGENT.md'),False)));l.addWidget(box)
        box,c=card('Резервна копія');row=QBoxLayout(QBoxLayout.LeftToRight);row.setSpacing(14);self.responsive_rows.append(row)
        for kind,title,subtitle,fn in [('export','Експорт копії','Зберегти резервну копію даних',self.owner.export_backup),('import','Імпорт копії','Відновити дані з резервної копії',self.import_backup)]:
            b=QPushButton();b.setObjectName('settingsOutline');b.setStyleSheet('padding:0;border-color:#2b455b;');b.setMinimumHeight(88);b.clicked.connect(fn);r=QHBoxLayout(b);r.setContentsMargins(12,8,12,8);r.setSpacing(18);r.addWidget(glyph(kind,38,'#46c4ff'));col=QVBoxLayout();col.addWidget(text(title,19,bold=True));col.addWidget(text(subtitle,16,'#9fb9d2'));r.addLayout(col);
            for child in b.findChildren(QWidget):child.setAttribute(Qt.WA_TransparentForMouseEvents,True)
            row.addWidget(b,1)
        c.addLayout(row);c.addWidget(note('Авторизаційні дані AI не входять у резервну копію.'));l.addWidget(box)
        box,c=card('Політика зберігання');c.addWidget(note('Неопрацьовані й незакріплені записи зберігаються 7 днів.','clock'));l.addWidget(box)
    def open_path(self,path):QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def edit_profile(self):
        from ui import ProfileDialog
        d=ProfileDialog(self.owner);d.exec();self.autostart.setChecked(self.store.get('autostart'))
        for thumbnail in self.findChildren(ProfileThumbnail):thumbnail.path=self.store.get('avatar','');thumbnail.update()
    def import_backup(self):
        self.owner.import_backup();self.reject()
    def save(self):
        start=self.start.currentData();end=self.end.currentData()
        if start>=end:QMessageBox.information(self,'Розклад','Початок має бути раніше завершення.');self.select_page(2);return
        self.remember_effort()
        settings={'efforts':self.effort_values,'provider':self.provider.currentText(),'model':self.model.currentData() or '', 'capture':self.enabled.isChecked(),'listen_all':self.all.isChecked(),'apps':[s.strip().lower() for s in self.apps.toPlainText().splitlines() if s.strip()],'sites':[s.strip().lower().removeprefix('https://').removeprefix('http://').rstrip('/') for s in self.sites.toPlainText().splitlines() if s.strip()],'hours_start':start,'hours_end':end,'daily_chats':self.daily.value(),'review_reminders':self.reminders.value(),'dnd':self.dnd.isChecked(),'autostart':self.autostart.isChecked()}
        for k,v in settings.items():self.store.set(k,v)
        if not settings['capture']:self.owner.collector.flush()
        self.owner.set_autostart(settings['autostart']);self.owner.capture_action.setChecked(not settings['capture']);self.owner.dnd_action.setChecked(settings['dnd']);self.accept();self.owner.navigate(self.owner.page,self.owner.active_agent)
