"""Compact messenger view, message actions, replies and persistent pins."""
import json
import random
from datetime import datetime
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFontMetrics, QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import *


def action_icon(kind):
    pix=QPixmap(24,24);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(QPen(QColor('#95b2c5'),1.5))
    if kind in ('back','reply'):
        p.drawLine(5,12,19,12);p.drawLine(5,12,11,6);p.drawLine(5,12,11,18)
    elif kind=='plus':p.drawLine(5,12,19,12);p.drawLine(12,5,12,19)
    elif kind=='more':
        p.setBrush(QColor('#95b2c5'))
        for y in (5,12,19):p.drawEllipse(11,y,2,2)
    elif kind=='send':
        p.drawLine(4,4,20,12);p.drawLine(20,12,4,20);p.drawLine(4,20,8,12);p.drawLine(8,12,4,4);p.drawLine(8,12,20,12)
    elif kind=='copy':p.drawRoundedRect(8,7,11,14,2,2);p.drawLine(5,17,5,3);p.drawLine(5,3,15,3)
    elif kind=='delete':p.drawLine(4,6,20,6);p.drawRect(7,6,10,15);p.drawLine(9,3,15,3)
    else:
        p.drawLine(7,3,16,3);p.drawLine(9,3,9,10);p.drawLine(14,3,14,10);p.drawLine(6,11,17,11);p.drawLine(6,11,9,8);p.drawLine(17,11,14,8);p.drawLine(12,11,12,21)
        if kind=='pins':
            for y in (7,12,17):p.drawLine(19,y,23,y)
    p.end();return QIcon(pix)


def compact_icon(button,kind):
    button.setText('');button.setIcon(action_icon(kind));button.setIconSize(QSize(22,22));button.setStyleSheet('QPushButton{background:transparent;border:0;padding:0;} QPushButton::menu-indicator{image:none;width:0;} QPushButton:hover{background:#243746;border-radius:4px;}')
    return button


class ChatView:
    def update_presence_label(self,aid):
        if self.page!='chats' or self.active_agent!=aid:return
        status=getattr(self,'chat_presence_label',None)
        if status:
            online=aid in self.online_agents
            status.setText('online' if online else 'last seen recently')
            status.setStyleSheet('font-size:12px;color:'+('#64b5ed' if online else '#7f9db6')+';')

    def set_agent_online(self,aid):
        timer=self.presence_timers.get(aid)
        if timer:timer.stop()
        self.online_agents.add(aid);self.update_presence_label(aid)

    def finish_agent_presence(self,aid,failed=False):
        timer=self.presence_timers.get(aid)
        if timer:timer.stop()
        if failed:
            self.online_agents.discard(aid);self.update_presence_label(aid);return
        if timer is None:
            timer=QTimer(self);timer.setSingleShot(True);self.presence_timers[aid]=timer
            def offline():
                if aid not in self.pending_agents:
                    self.online_agents.discard(aid);self.update_presence_label(aid)
            timer.timeout.connect(offline)
        timer.start(random.randint(3000,7000))

    def pins(self,aid):
        return self.store.rows('SELECT m.* FROM messages m JOIN message_links l ON l.message=m.id WHERE m.agent=? AND l.pinned>0 ORDER BY l.pinned DESC',(aid,))

    def set_pin(self,message,enabled=True):
        from core import now
        self.store.execute('INSERT INTO message_links(message,pinned) VALUES(?,?) ON CONFLICT(message) DO UPDATE SET pinned=excluded.pinned',(message['id'],now() if enabled else 0))
        self.navigate('chats',message['agent'])

    def show_pins(self,aid):
        self.pins_agent=aid;self.navigate('chats',aid)

    def jump_to_message(self,aid,mid):
        if not self.store.one('SELECT id FROM messages WHERE id=? AND agent=?',(mid,aid)):return
        self.pins_agent=None;self.jump_message=mid
        self.history_limit=max(self.history_limit,self.store.one('SELECT count(*) n FROM messages WHERE agent=? AND created >= (SELECT created FROM messages WHERE id=?)',(aid,mid))['n'])
        self.navigate('chats',aid)

    def start_reply(self,message):
        self.store.set('reply_to_'+message['agent'],message['id'])
        self.pins_agent=None;self.navigate('chats',message['agent']);self.chat_composer.setFocus()

    def delete_message(self,message):
        if message['agent'] in self.pending_agents:return
        if QMessageBox.question(self,'Видалити повідомлення','Видалити це повідомлення з чату?')!=QMessageBox.Yes:return
        self.store.execute('DELETE FROM message_links WHERE message=?',(message['id'],))
        self.store.execute('DELETE FROM messages WHERE id=? AND agent=?',(message['id'],message['agent']))
        self.navigate('chats',message['agent'])

    def message_menu(self,message,selected=''):
        from ui import WordDialog
        menu=QMenu(self);menu.setStyleSheet('QMenu{background:#17212b;border:0;border-radius:8px;padding:6px;} QMenu::item{padding:9px 26px;} QMenu::item:selected{background:#253746;border-radius:4px;}')
        menu.addAction(action_icon('reply'),'Reply',lambda:self.start_reply(message))
        pinned=self.store.one('SELECT pinned FROM message_links WHERE message=?',(message['id'],))
        menu.addAction(action_icon('pin'),'Unpin' if pinned and pinned['pinned'] else 'Pin',lambda:self.set_pin(message,not(pinned and pinned['pinned'])))
        menu.addAction(action_icon('copy'),'Copy Text',lambda:QApplication.clipboard().setText(selected or message['body']))
        action=menu.addAction(action_icon('delete'),'Delete',lambda:self.delete_message(message));action.setEnabled(message['agent'] not in self.pending_agents)
        if selected:
            menu.addSeparator();menu.addAction('Додати у словник',lambda:self.keep_dialog(WordDialog(self,selected)))
        return menu

    def build_chats(self):
        self.chat_presence_label=None
        from ui import label,button,avatar,AgentDialog,MemoryDialog,HintDialog,Welcome,Composer
        splitter=QSplitter(Qt.Horizontal);splitter.setChildrenCollapsible(False);splitter.setHandleWidth(1)
        sidebar=QWidget();sidebar.setObjectName('sidebar');sidebar.setMinimumWidth(240);sidebar.setMaximumWidth(660)
        sl=QVBoxLayout(sidebar);sl.setContentsMargins(8,8,8,0);sl.setSpacing(6)
        top=QHBoxLayout();search=QLineEdit();search.setPlaceholderText('Пошук');search.setFixedHeight(36)
        search.setStyleSheet('background:#242f3d;border:0;border-radius:18px;padding:8px 16px;')
        top.addWidget(search);plus=button('+',lambda:self.keep_dialog(AgentDialog(self)));plus.setFixedSize(30,32);compact_icon(plus,'plus');top.addWidget(plus);sl.addLayout(top)
        agents=self.store.rows('SELECT * FROM agents ORDER BY rowid');items=QListWidget();items.setSpacing(0);items.setStyleSheet('QListWidget{border:0;background:#17212b;} QListWidget::item:selected{background:#2b5278;border-radius:0;}')
        for agent in agents:
            last=self.store.one('SELECT body,created FROM messages WHERE agent=? ORDER BY created DESC LIMIT 1',(agent['id'],))
            item=QListWidgetItem();item.setData(Qt.UserRole,agent['id']);item.setData(Qt.UserRole+1,agent['name']);item.setSizeHint(QSize(240,64));items.addItem(item)
            widget=QWidget();r=QHBoxLayout(widget);r.setContentsMargins(4,6,8,6);r.setSpacing(10);r.addWidget(avatar(agent['name'],agent['color'],46,agent['avatar']))
            col=QVBoxLayout();col.setSpacing(4);heading=QHBoxLayout();heading.addWidget(label(agent['name']));heading.addStretch()
            if last:heading.addWidget(label(datetime.fromtimestamp(last['created']).strftime('%H:%M'),'muted'))
            col.addLayout(heading);preview=label((last['body'].replace('\n',' ')[:48]+'…') if last and len(last['body'])>48 else last['body'] if last else 'Почни розмову','muted');col.addWidget(preview);r.addLayout(col,1);items.setItemWidget(item,widget)
            if agent['id']==self.active_agent:items.setCurrentItem(item)
        def choose(item):self.pins_agent=None;self.navigate('chats',item.data(Qt.UserRole))
        items.itemClicked.connect(choose);search.textChanged.connect(lambda value:[items.item(i).setHidden(value.casefold() not in items.item(i).data(Qt.UserRole+1).casefold()) for i in range(items.count())]);sl.addWidget(items)
        splitter.addWidget(sidebar);chat=QWidget();chat.setMinimumWidth(340);cl=QVBoxLayout(chat);cl.setContentsMargins(0,0,0,0);cl.setSpacing(0);splitter.addWidget(chat);splitter.setStretchFactor(1,1)
        self.workspace_layout.addWidget(splitter);splitter.setSizes([int(self.width()*.34),int(self.width()*.66)])
        agent=next((a for a in agents if a['id']==self.active_agent),None)
        if not agent:cl.addWidget(Welcome(self.show_settings));return
        aid=agent['id'];pinned_view=getattr(self,'pins_agent',None)==aid;pins=self.pins(aid)
        header=QWidget();header.setObjectName('header');header.setFixedHeight(54);hl=QHBoxLayout(header);hl.setContentsMargins(14,4,12,4)
        if pinned_view:
            back=button('←',lambda:self.leave_pins(aid));back.setFixedWidth(34);compact_icon(back,'back');hl.addWidget(back);hl.addWidget(label(f'{len(pins)} закріплених повідомлень'));hl.addStretch()
        else:
            title=QVBoxLayout();title.setSpacing(2);title.addWidget(label(agent['name']));status=label('online' if aid in self.online_agents else 'last seen recently','muted');self.chat_presence_label=status;status.setObjectName('chatPresence');status.setStyleSheet('font-size:12px;color:'+('#64b5ed' if aid in self.online_agents else '#7f9db6')+';');title.addWidget(status);hl.addLayout(title);hl.addStretch()
            more=button('⋮');more.setFixedSize(30,34);menu=QMenu(more);menu.addAction('Пам’ять',lambda:self.keep_dialog(MemoryDialog(self,agent)));menu.addAction('Редагувати',lambda:self.keep_dialog(AgentDialog(self,agent)));menu.addAction('Закріплені повідомлення',lambda:self.show_pins(aid));more.setMenu(menu);compact_icon(more,'more');hl.addWidget(more)
        cl.addWidget(header)
        if pins and not pinned_view:
            bar=QWidget();bar.setStyleSheet('background:#1d2b38;');bar.setFixedHeight(48);bl=QHBoxLayout(bar);bl.setContentsMargins(14,2,6,2)
            pin=button('Закріплене повідомлення\n'+' '.join(pins[0]['body'].split())[:100],lambda:self.jump_to_message(aid,pins[0]['id']));pin.setStyleSheet('text-align:left;border:0;border-left:2px solid #64b5ed;border-radius:0;padding:2px 10px;color:#8ecbfa;');bl.addWidget(pin,1)
            open_pins=button('☷',lambda:self.show_pins(aid));open_pins.setObjectName('openPinnedMessages');open_pins.setToolTip('Усі закріплені повідомлення');open_pins.setFixedSize(34,36);compact_icon(open_pins,'pins');bl.addWidget(open_pins);cl.addWidget(bar)
        if self.viewing_chat(aid) and not pinned_view:self.store.execute('UPDATE messages SET unread=0 WHERE agent=?',(aid,))
        messages=QVBoxLayout();messages.setContentsMargins(12,8,16,8);messages.setSpacing(5);messages.addStretch()
        history=list(reversed(pins)) if pinned_view else self.store.rows('SELECT * FROM messages WHERE agent=? ORDER BY created',(aid,))
        if len(history)>self.history_limit and not pinned_view:
            def older():self.history_limit+=100;self.navigate('chats',aid)
            messages.addWidget(button('Показати попередні повідомлення',older))
        self.message_widgets={};last_date=None
        for m in (history if pinned_view else history[-self.history_limit:]):
            day=datetime.fromtimestamp(m['created']).strftime('%d.%m.%Y')
            if day!=last_date:
                date_label=label(day,'muted');date_label.setAlignment(Qt.AlignCenter);messages.addWidget(date_label);last_date=day
            widget=self.bubble(m,agent,pinned_view);messages.addWidget(widget);self.message_widgets[m['id']]=widget
        if not history:messages.addWidget(label('Немає закріплених повідомлень.' if pinned_view else 'Напиши про свій день або почни з будь-якої думки.','muted'))
        if aid in self.pending_agents and not pinned_view:messages.addWidget(label(agent['name']+' пише…','muted'))
        sc=self.scroll(messages);self.chat_scroll=sc;cl.addWidget(sc,1)
        target=getattr(self,'jump_message',None);self.jump_message=None
        def position():
            if target in self.message_widgets:
                widget=self.message_widgets[target];sc.ensureWidgetVisible(widget,0,60)
                widget.setStyleSheet('QWidget#messageRow{background:#203a50;border-radius:6px;}')
                QTimer.singleShot(1600,widget,lambda:widget.setStyleSheet(''))
            else:sc.verticalScrollBar().setValue(sc.verticalScrollBar().maximum())
        QTimer.singleShot(50,sc,position)
        if pinned_view:
            unpin=button('Відкріпити всі повідомлення',lambda:self.unpin_all(aid));unpin.setFixedHeight(44);cl.addWidget(unpin);return
        footer=QWidget();footer.setObjectName('header');fl=QVBoxLayout(footer);fl.setContentsMargins(10,4,10,4);fl.setSpacing(2)
        reply_id=self.store.get('reply_to_'+aid,'');reply=self.store.one('SELECT * FROM messages WHERE id=? AND agent=?',(reply_id,aid))
        if reply:
            rl=QHBoxLayout();rl.addWidget(label('Відповідь: '+' '.join(reply['body'].split())[:100],'muted'),1);rl.addWidget(button('×',lambda:self.cancel_reply(aid)));fl.addLayout(rl)
        compose_row=QHBoxLayout();composer=Composer();self.chat_composer=composer;composer.setPlaceholderText('Напиши повідомлення…');composer.setFixedHeight(40);composer.setStyleSheet('background:transparent;border:0;padding:6px;font-size:13px;');composer.setPlainText(self.draft('chat:'+aid))
        composer.textChanged.connect(lambda:self.save_draft('chat:'+aid,composer.toPlainText()))
        def send():
            text=composer.toPlainText().strip()
            if text:self.send_message(aid,text)
        composer.submitted.connect(send);compose_row.addWidget(composer,1)
        help_button=button('?',lambda:self.keep_dialog(HintDialog(self,agent,composer.toPlainText())));help_button.setToolTip('Допоможи сформулювати');help_button.setFixedSize(32,34);help_button.setStyleSheet('border:0;padding:0;background:transparent;color:#7cbce6;font-size:18px;');compose_row.addWidget(help_button)
        send_button=button('➤',send);send_button.setToolTip('Надіслати');send_button.setFixedSize(36,34);compact_icon(send_button,'send');compose_row.addWidget(send_button);fl.addLayout(compose_row);cl.addWidget(footer)

    def leave_pins(self,aid):self.pins_agent=None;self.navigate('chats',aid)
    def cancel_reply(self,aid):self.store.set('reply_to_'+aid,'');self.navigate('chats',aid)
    def unpin_all(self,aid):
        if QMessageBox.question(self,'Відкріпити всі','Відкріпити всі повідомлення цього чату?')!=QMessageBox.Yes:return
        self.store.execute('UPDATE message_links SET pinned=0 WHERE message IN (SELECT id FROM messages WHERE agent=?)',(aid,));self.navigate('chats',aid)

    def bubble(self,m,agent,pinned_view=False):
        from ui import label,button,avatar
        outer=QWidget();outer.setObjectName('messageRow');outer.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum);row=QHBoxLayout(outer);row.setContentsMargins(0,0,0,0);row.setSpacing(8);out=m['role']=='user'
        row.addWidget(avatar(self.store.get('name','You') if out else agent['name'],'#4b9cdb' if out else agent['color'],32,self.store.get('avatar','') if out else agent['avatar']),0,Qt.AlignBottom)
        box=QFrame();box.setStyleSheet('QFrame{background:'+('#2b5278' if out else '#182733')+';border-radius:12px;}');bl=QVBoxLayout(box);bl.setContentsMargins(11,7,11,5);bl.setSpacing(3)
        body=label(m['body'],'',True);body.setStyleSheet('font-size:13px;');body.setTextFormat(Qt.PlainText);body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.ensurePolished();metrics=QFontMetrics(body.font());width=min(440,max(100,metrics.horizontalAdvance(m['body'])+85))
        box.setFixedWidth(min(width,max(180,int((self.width()-300)*.7))))
        reply=self.store.one('SELECT m.* FROM messages m JOIN message_links l ON l.reply_to=m.id WHERE l.message=?',(m['id'],))
        if reply:
            quote=button(('Ти' if reply['role']=='user' else agent['name'])+'\n'+' '.join(reply['body'].split())[:65],lambda:self.jump_to_message(m['agent'],reply['id']));quote.setStyleSheet('text-align:left;border:0;border-left:2px solid #78b9e8;border-radius:2px;padding:4px;color:#b9ddfa;background:#24435b;');bl.addWidget(quote)
        bl.addWidget(body)
        if m['corrections']:
            result=json.loads(m['corrections']);count=len(result.get('errors',[]))
            if count or result.get('english_version'):
                b=button(f'{count} правок' if count else 'Англійський варіант',lambda:self.show_corrections(result));b.setStyleSheet('border:0;background:transparent;color:#83c6f5;padding:2px;text-align:left;font-size:11px;');bl.addWidget(b)
        if m['status']=='failed':bl.addWidget(button('Повторити надсилання',lambda:self.send_message(agent['id'],m['body'],m['id'])))
        stamp=label(datetime.fromtimestamp(m['created']).strftime('%H:%M')+('  ✓' if out and m['status']=='sent' else ''),'muted');stamp.setAlignment(Qt.AlignRight);stamp.setStyleSheet('font-size:11px;color:#80a7c5;');bl.addWidget(stamp)
        if not reply and not m['corrections'] and m['status']!='failed' and '\n' not in m['body'] and metrics.horizontalAdvance(m['body'])<330:
            bl.removeWidget(body);bl.removeWidget(stamp);inline=QHBoxLayout();inline.setSpacing(10);stamp.setFixedWidth(stamp.fontMetrics().horizontalAdvance(stamp.text())+4);inline.addWidget(body,1);inline.addWidget(stamp,0,Qt.AlignBottom);bl.insertLayout(0,inline)
        for widget in (box,body,outer):
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos,widget=widget:self.message_menu(m,body.selectedText()).exec(widget.mapToGlobal(pos)))
        if pinned_view:
            body.setTextInteractionFlags(Qt.NoTextInteraction)
            body.mousePressEvent=lambda event:self.jump_to_message(m['agent'],m['id']) if event.button()==Qt.LeftButton else QLabel.mousePressEvent(body,event)
            box.mousePressEvent=lambda event:self.jump_to_message(m['agent'],m['id']) if event.button()==Qt.LeftButton else QFrame.mousePressEvent(box,event)
            body.setCursor(Qt.PointingHandCursor)
        row.addWidget(box,0,Qt.AlignLeft)
        if pinned_view:
            jump=button('',lambda:self.jump_to_message(m['agent'],m['id']));jump.setFixedSize(32,32);compact_icon(jump,'send');row.addWidget(jump,0,Qt.AlignBottom)
        row.addStretch(1);return outer
