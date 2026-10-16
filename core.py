"""Local, versioned learning data. No credentials or network calls in this module."""
from __future__ import annotations
import json, sqlite3, time, uuid, re, unicodedata, zipfile, tempfile, shutil
from pathlib import Path
from contextlib import closing
from learning import LearningStore

ROOT = Path(__file__).resolve().parent
DEFAULTS = {
    'onboarded': False, 'name': '', 'level': 'B1', 'goal': '', 'avatar': '',
    'provider': 'ChatGPT', 'model': '', 'capture': False, 'listen_all': False,
    'apps': ['codex.exe', 'chatgpt.exe', 'claude.exe', 'telegram.exe', 'discord.exe'],
    'sites': ['chatgpt.com', 'claude.ai', 'gemini.google.com'],
    'dnd': False, 'hours_start': 10, 'hours_end': 20, 'daily_chats': 2,
    'review_reminders': 1, 'autostart': True, 'retention_days': 7,
}
PERSONAS = [
    ('mia', 'Mia', 'Everyday English', '#b18af5', 'M', 'A warm, curious friend. Discuss everyday life, habits and small experiences. Ask one natural follow-up at a time. Never sound like a worksheet.'),
    ('leo', 'Leo', 'Ideas & technology', '#54b5d4', 'L', 'A thoughtful friend interested in games, technology and creative projects. Explore opinions and decisions in accessible English.'),
    ('emma', 'Emma', 'Stories & culture', '#e7a56a', 'E', 'An encouraging friend who enjoys music, films and stories. Help the learner describe experiences and express preferences.'),
]

def now(): return time.time()
def uid(): return uuid.uuid4().hex
def normalize(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', s).casefold().strip().strip('.!?'))

def learning_text(text):
    """Conservative prefilter; original always remains intact."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`\n]+`', '', text)
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith(('>', 'Traceback ', 'File "', 'at ', 'INFO ', 'DEBUG ', 'ERROR ', 'WARN ')):
            continue
        if re.match(r'^\s*(?:\d{4}-\d\d-\d\d[T ]\d|\[\d\d:\d\d|(?:const|let|var|import|from|def|class)\s)', line):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()

def has_english(text):
    return len(re.findall(r'[A-Za-z]', text)) >= 4

class Store(LearningStore):
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT,topic TEXT,color TEXT,avatar TEXT,instructions TEXT,provider TEXT,model TEXT,enabled INTEGER DEFAULT 1);
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,agent TEXT,role TEXT,body TEXT,created REAL,corrections TEXT DEFAULT '',unread INTEGER DEFAULT 0,status TEXT DEFAULT 'sent');
            CREATE TABLE IF NOT EXISTS texts(id TEXT PRIMARY KEY,source TEXT,body TEXT,created REAL,updated REAL,version INTEGER DEFAULT 1,final INTEGER DEFAULT 0,pinned INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY,text_id TEXT,version INTEGER,original TEXT,selected TEXT,result TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS dictionaries(id TEXT PRIMARY KEY,name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS words(id TEXT PRIMARY KEY,dictionary TEXT,english TEXT,ukrainian TEXT,example TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,kind TEXT,item TEXT,direction TEXT,due REAL,streak INTEGER DEFAULT 0,lapses INTEGER DEFAULT 0,UNIQUE(kind,item,direction));
            CREATE TABLE IF NOT EXISTS constructions(id TEXT PRIMARY KEY,pattern TEXT UNIQUE,explanation TEXT,example TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT,created REAL,payload TEXT);
            CREATE TABLE IF NOT EXISTS drafts(key TEXT PRIMARY KEY,body TEXT);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,status TEXT,error TEXT,created REAL);
            ''')
        self.init_learning()
        for key, value in DEFAULTS.items():
            if self.get(key, None) is None: self.set(key, value)
        if not self.rows('SELECT id FROM agents'):
            for aid, name, topic, color, avatar, instructions in PERSONAS:
                self.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,1)', (aid,name,topic,color,avatar,instructions,'ChatGPT',''))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=15000')
        return closing_db(db)

    def rows(self, sql, params=()):
        with self.connect() as db: return [dict(r) for r in db.execute(sql, params).fetchall()]
    def one(self, sql, params=()):
        result = self.rows(sql, params)
        return result[0] if result else None
    def execute(self, sql, params=()):
        with self.connect() as db: db.execute(sql, params)
    def get(self, key, default=None):
        row = self.one('SELECT value FROM settings WHERE key=?',(key,))
        return json.loads(row['value']) if row else default
    def set(self, key, value):
        self.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(value,ensure_ascii=False)))
    def profile(self): return {k:self.get(k,v) for k,v in DEFAULTS.items() if k in ('name','level','goal')}

    def save_text(self, source, body, record_id=None, final=False):
        body=body.strip()
        if not body: return record_id
        old=self.one('SELECT * FROM texts WHERE id=?',(record_id,)) if record_id else None
        if old:
            if old['body'] != body:
                self.execute('UPDATE texts SET body=?,updated=?,version=version+1,final=? WHERE id=?',(body,now(),int(final),record_id))
            elif final: self.execute('UPDATE texts SET final=1 WHERE id=?',(record_id,))
            return record_id
        record_id=uid()
        self.execute('INSERT INTO texts VALUES(?,?,?,?,?,1,?,0)',(record_id,source,body,now(),now(),int(final)))
        return record_id

    def cleanup(self):
        cutoff=now()-self.get('retention_days',7)*86400
        self.execute('DELETE FROM texts WHERE updated<? AND pinned=0 AND id NOT IN(SELECT text_id FROM analyses)',(cutoff,))

    def add_message(self, agent, role, body, corrections='', unread=0, status='sent'):
        mid=uid()
        self.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)',(mid,agent,role,body,now(),corrections,int(unread),status))
        return mid
    def shared_learning(self):
        return self.rows('SELECT pattern,explanation FROM constructions ORDER BY created DESC LIMIT 15')

    def save_analysis(self, record, selected, result):
        aid=uid()
        self.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?,?)',(aid,record['id'],record['version'],record['body'],selected,json.dumps(result,ensure_ascii=False),now()))
        self.add_patterns(result.get('patterns',[]))
        self.record_learning('text:'+record['id']+':'+str(record['version']),selected,result)
        return aid
    def add_patterns(self, patterns):
        for p in patterns:
            if not isinstance(p,dict) or not p.get('pattern'): continue
            pattern=str(p['pattern']).strip()[:500]
            existing=self.one('SELECT id FROM constructions WHERE lower(trim(pattern))=lower(trim(?))',(pattern,))
            cid=existing['id'] if existing else uid()
            if not existing:
                self.execute('INSERT INTO constructions VALUES(?,?,?,?,?)',(cid,pattern,str(p.get('explanation','')),str(p.get('example','')),now()))
            self.execute('INSERT OR IGNORE INTO reviews VALUES(?,?,?,?,?,0,0)',(uid(),'construction',cid,'produce',now()))

    def dictionary(self, name):
        name=name.strip()
        if not name: raise ValueError('Введіть назву словника.')
        old=self.one('SELECT id FROM dictionaries WHERE name=?',(name,))
        if old: return old['id']
        did=uid(); self.execute('INSERT INTO dictionaries VALUES(?,?)',(did,name)); return did
    def add_word(self,dictionary,english,ukrainian,example):
        if not english.strip() or not ukrainian.strip(): raise ValueError('Потрібні слово та переклад.')
        old=self.one('SELECT id FROM words WHERE dictionary=? AND lower(english)=lower(?) AND ukrainian=?',(dictionary,english.strip(),ukrainian.strip()))
        if old: return old['id']
        wid=uid()
        self.execute('INSERT INTO words VALUES(?,?,?,?,?,?)',(wid,dictionary,english.strip(),ukrainian.strip(),example.strip(),now()))
        self.execute('INSERT INTO reviews VALUES(?,?,?,?,?,0,0)',(uid(),'word',wid,'en-uk',now()))
        return wid
    def due(self): return self.rows('SELECT * FROM reviews WHERE due<=? ORDER BY due',(now(),))
    def grade(self,review_id,grade):
        row=self.one('SELECT * FROM reviews WHERE id=?',(review_id,))
        if not row: return
        if grade not in ('correct','typo','wrong'): raise ValueError('Invalid grade')
        streak=row['streak']+1 if grade=='correct' else 0
        intervals=[1,3,7,14,30,60,120]
        due=now()+ (intervals[min(max(streak-1,0),6)]*86400 if grade=='correct' else (1800 if grade=='typo' else 600))
        self.execute('UPDATE reviews SET due=?,streak=?,lapses=lapses+? WHERE id=?',(due,streak,int(grade!='correct'),review_id))
        if row['kind']=='word' and row['direction']=='en-uk' and grade=='correct':
            self.execute('INSERT OR IGNORE INTO reviews VALUES(?,?,?,?,?,0,0)',(uid(),'word',row['item'],'uk-en',now()+86400))
        self.execute('INSERT INTO events VALUES(?,?,?,?)',(uid(),'review',now(),json.dumps({'review':review_id,'grade':grade})))

    def backup(self,target,agents_dir):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot=Path(tmp)/'orbit.sqlite'
            with self.connect() as db, closing(sqlite3.connect(snapshot)) as dest:
                db.backup(dest)
                dest.execute("DELETE FROM settings WHERE key='bridge_token' OR key LIKE 'provider_%'")
                dest.commit()
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(snapshot,'orbit.sqlite')
                for path in Path(agents_dir).glob('*.md'): z.write(path,'agents/'+path.name)
                for path in self.path.parent.glob('*avatar*.png'): z.write(path,'avatars/'+path.name)
                z.writestr('manifest.json',json.dumps({'format':'english-orbit','version':1,'created':now()}))
    def restore(self,source,agents_dir):
        bridge_token=self.get('bridge_token')
        with zipfile.ZipFile(source) as z, tempfile.TemporaryDirectory() as tmp:
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('format')!='english-orbit' or manifest.get('version')!=1: raise ValueError('Непідтримувана резервна копія.')
            candidate=Path(tmp)/'restore.sqlite';candidate.write_bytes(z.read('orbit.sqlite'))
            with closing(sqlite3.connect(candidate)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Пошкоджена база.')
                for table in ('settings','texts','messages','reviews','agents','words'): db.execute('SELECT * FROM '+table+' LIMIT 1')
            self.backup(self.path.parent/('before-restore-'+str(int(now()))+'.zip'),agents_dir)
            shutil.copy2(candidate,self.path)
            self.init_learning()
            if bridge_token:self.set('bridge_token',bridge_token)
            self.set('capture',False)
            for name in z.namelist():
                if re.fullmatch(r'agents/[A-Za-z0-9_-]+\.md',name):
                    (Path(agents_dir)/Path(name).name).write_bytes(z.read(name))
                if re.fullmatch(r'avatars/[A-Za-z0-9_-]+\.png',name):
                    destination=self.path.parent/Path(name).name;destination.write_bytes(z.read(name))
            avatar=self.get('avatar','')
            if avatar:self.set('avatar',str(self.path.parent/Path(avatar).name))
            for agent in self.rows('SELECT id,avatar FROM agents'):
                if agent['avatar'].lower().endswith('.png'):
                    self.execute('UPDATE agents SET avatar=? WHERE id=?',(str(self.path.parent/Path(agent['avatar']).name),agent['id']))

class closing_db:
    def __init__(self,db): self.db=db
    def __enter__(self): return self.db
    def __exit__(self,typ,val,tb):
        try:
            self.db.rollback() if typ else self.db.commit()
        finally: self.db.close()

class Collector:
    """Identity is field + document/conversation. Idle saves are not boundaries."""
    def __init__(self,store,clock=now): self.store=store; self.clock=clock; self.sessions={}
    def receive(self,key,source,text,final=False):
        state=self.sessions.get(key)
        if not text.strip():
            if state and state['text'].strip():
                self.store.save_text(state['source'],state['text'],state['id'],True)
                self.sessions.pop(key,None)
            return
        if not has_english(text): return
        if not state: state={'text':'','id':None,'source':source,'changed':self.clock()};self.sessions[key]=state
        if state['text']!=text:
            state['text']=text;state['changed']=self.clock()
        if final:
            state['id']=self.store.save_text(source,text,state['id'],True)
            self.sessions.pop(key,None)
    def tick(self):
        for key,state in list(self.sessions.items()):
            if self.clock()-state['changed']>=20:
                state['id']=self.store.save_text(state['source'],state['text'],state['id'])
            if self.clock()-state['changed']>86400: self.sessions.pop(key,None)
    def flush(self):
        for state in self.sessions.values():
            self.store.save_text(state['source'],state['text'],state['id'])
        self.sessions.clear()
