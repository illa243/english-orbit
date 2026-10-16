from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QListWidget, QInputDialog


class HintDialog(QDialog):
    def __init__(self, owner, agent, draft):
        super().__init__(owner)
        self.owner=owner;self.agent=agent;self.draft=draft
        self.setWindowTitle('Допоможи сформулювати');self.resize(500,340)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Конструкція → початок речення → повний приклад'))
        self.view=QTextBrowser();layout.addWidget(self.view)
        self.next=QPushButton('Показати підказку');layout.addWidget(self.next)
        self.next.clicked.connect(self.request)
        self.stage=0

    def request(self):
        if self.stage>=3:return
        stage=self.stage+1;self.next.setEnabled(False)
        payload=self.owner.chat_context(self.agent['id'])
        payload.update(draft=self.draft,stage=stage)
        latest=self.owner.store.one("SELECT id FROM messages WHERE agent=? AND role='user' ORDER BY created DESC LIMIT 1",(self.agent['id'],))
        def done(result):
            current_message=self.owner.store.one("SELECT id FROM messages WHERE agent=? AND role='user' ORDER BY created DESC LIMIT 1",(self.agent['id'],))
            if latest!=current_message:
                self.view.setPlainText('Розмова вже продовжилась. Відкрий нову підказку для наступної відповіді.');return
            self.stage=stage
            current=self.owner.store.get('hint_level_'+self.agent['id'],0)
            self.owner.store.set('hint_level_'+self.agent['id'],max(current,stage))
            self.view.setPlainText(result['hint'])
            self.next.setText('Показати початок речення' if stage==1 else 'Показати повний приклад' if stage==2 else 'Усі підказки показано')
            self.next.setEnabled(stage<3)
        def failed(error):self.view.setPlainText(error);self.next.setEnabled(True)
        self.owner.ai('hint',payload,done,self.agent['provider'],self.agent['model'],on_error=failed)


class MemoryDialog(QDialog):
    def __init__(self, owner, agent):
        super().__init__(owner);self.owner=owner;self.agent=agent
        self.setWindowTitle('Що пам’ятає '+agent['name']);self.resize(580,430)
        layout=QVBoxLayout(self)
        note=QLabel('Факти цього співрозмовника. Видалені теми більше не використовуються, навіть зі старої історії.');note.setWordWrap(True);layout.addWidget(note)
        self.items=QListWidget();layout.addWidget(self.items)
        edit=QPushButton('Редагувати вибраний факт');edit.clicked.connect(self.edit);layout.addWidget(edit)
        remove=QPushButton('Забути вибраний факт');remove.clicked.connect(self.forget);layout.addWidget(remove)
        self.refresh()

    def refresh(self):
        self.rows=self.owner.store.memories(self.agent['id']);self.items.clear()
        for row in self.rows:self.items.addItem(row['fact'])
        if not self.rows:self.items.addItem('Ще немає збережених фактів.')

    def selected(self):
        i=self.items.currentRow()
        return self.rows[i] if 0<=i<len(self.rows) else None

    def forget(self):
        row=self.selected()
        if row:self.owner.store.forget_memory(self.agent['id'],row['id']);self.refresh()

    def edit(self):
        row=self.selected()
        if not row:return
        value,ok=QInputDialog.getMultiLineText(self,'Редагувати пам’ять','Факт',row['fact'])
        if ok and value.strip():
            self.owner.store.execute('UPDATE character_memories SET fact=?,evidence=? WHERE id=? AND agent=?',(value.strip()[:1000],'Відредаговано користувачем',row['id'],self.agent['id']))
            self.refresh()
