"""Evidence-backed learning observations and per-character, user-controlled memory."""
import re
import time
import uuid


def key(value):
    return re.sub(r'\s+', ' ', str(value).strip().casefold())[:500]


class LearningStore:
    def init_learning(self):
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS learning_observations(
                source TEXT, pattern TEXT, outcome TEXT, evidence TEXT, assisted INTEGER,
                created REAL, PRIMARY KEY(source,pattern));
            CREATE TABLE IF NOT EXISTS character_memories(
                id TEXT PRIMARY KEY, agent TEXT, topic TEXT, fact TEXT, evidence TEXT,
                source TEXT, updated REAL, deleted INTEGER DEFAULT 0, UNIQUE(agent,topic));
            CREATE TABLE IF NOT EXISTS message_links(message TEXT PRIMARY KEY,pinned REAL DEFAULT 0,reply_to TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS message_assistance(message TEXT PRIMARY KEY,level INTEGER);
            ''')

    def record_learning(self, source, text, result, assisted=0):
        observations=result.get('observations',[])
        if not isinstance(observations,list):return
        for item in observations[:20]:
            if not isinstance(item,dict):continue
            pattern=key(item.get('pattern','')); evidence=item.get('evidence','')
            outcome=item.get('outcome')
            if not pattern or outcome not in ('error','correct'):continue
            if not isinstance(evidence,str) or not evidence.strip() or evidence not in text:continue
            self.add_patterns([{'pattern':pattern,'explanation':str(item.get('explanation',''))[:1000],'example':str(item.get('example',''))[:1000]}])
            self.execute('INSERT OR IGNORE INTO learning_observations VALUES(?,?,?,?,?,?)',
                         (source,pattern,outcome,evidence[:2000],int(bool(assisted)),time.time()))

    def learning_stats(self):
        return self.rows('''SELECT c.*,
            COALESCE(SUM(o.outcome='error'),0) AS mistakes,
            COALESCE(SUM(o.outcome='correct' AND o.assisted=0),0) AS independent,
            COALESCE(SUM(o.outcome='correct' AND o.assisted=1),0) AS assisted,
            MAX(o.created) AS last_seen
            FROM constructions c LEFT JOIN learning_observations o ON o.pattern=lower(trim(c.pattern))
            GROUP BY c.id ORDER BY (COALESCE(SUM(o.outcome='error'),0)-COALESCE(SUM(o.outcome='correct' AND o.assisted=0),0)) DESC,c.created DESC''')

    def conversation_learning(self):
        return [{k:p[k] for k in ('pattern','explanation','mistakes','independent','assisted')} for p in self.learning_stats()[:3]]

    def memories(self, agent):
        return self.rows('SELECT * FROM character_memories WHERE agent=? AND deleted=0 ORDER BY updated DESC LIMIT 40',(agent,))

    def remember(self, agent, source, text, result):
        candidates=result.get('memories',[])
        if not isinstance(candidates,list):return
        for item in candidates[:4]:
            if not isinstance(item,dict):continue
            topic=key(item.get('topic',''))[:100];fact=item.get('fact','');evidence=item.get('evidence','')
            if not topic or not isinstance(fact,str) or not fact.strip():continue
            if not isinstance(evidence,str) or not evidence.strip() or evidence not in text:continue
            old=self.one('SELECT * FROM character_memories WHERE agent=? AND topic=?',(agent,topic))
            # Tombstones prevent forgotten facts from returning via retries or old context.
            if old and (old['deleted'] or old['source']==source):continue
            fact=fact.strip()[:1000]
            if old and item.get('operation')!='replace' and fact not in old['fact']:
                # New details must not erase durable facts sharing a model-selected topic.
                fact=old['fact']+'\n'+fact if len(old['fact'])+len(fact)<6000 else old['fact']
            self.execute('''INSERT INTO character_memories VALUES(?,?,?,?,?,?,?,0)
                ON CONFLICT(agent,topic) DO UPDATE SET fact=excluded.fact,evidence=excluded.evidence,
                source=excluded.source,updated=excluded.updated''',
                (uuid.uuid4().hex,agent,topic,fact,evidence[:2000],source,time.time()))

    def forget_memory(self, agent, memory_id):
        self.execute("UPDATE character_memories SET deleted=1,fact='',evidence='' WHERE id=? AND agent=?",(memory_id,agent))
