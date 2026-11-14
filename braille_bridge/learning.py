"""Adaptive Braille learning: Leitner boxes persisted in SQLite, one set of single-cell items per lesson."""
import os, random, sqlite3, time
from braille import english, STRONG_WORD, GROUP, HI_CONS, HI_VOW, cell

BOXES = 3                                   # box 0 = new / missed, box 2 = mastered

def _letters():
    return [(c, c, english(c)[0], 'en-IN') for c in 'abcdefghijklmnopqrstuvwxyz']

def _contractions():
    items = [(w, f'“{w}” (word-sign)', STRONG_WORD[w], 'en-IN') for w in ('and', 'for', 'of', 'the', 'with')]
    items += [(g, f'“{g}” (group-sign)', GROUP[g], 'en-IN') for g in GROUP]
    return items

def _hi_vowels():
    return [(v, v, cell(*d), 'hi-IN') for v, d in HI_VOW.items()]

def _hi_cons():
    return [(c, c, cell(*d), 'hi-IN') for c, d in HI_CONS.items()]

SETS = {
    'en-letters': {'title': 'English letters a–z', 'items': _letters},
    'en-contractions': {'title': 'English Grade 2 signs', 'items': _contractions},
    'hi-vowels': {'title': 'Hindi vowels (स्वर)', 'items': _hi_vowels},
    'hi-consonants': {'title': 'Hindi consonants (व्यंजन)', 'items': _hi_cons},
}

def items_of(set_id):
    return [dict(id=i, label=l, cell=c, lang=lg) for i, l, c, lg in SETS[set_id]['items']()]

class Store:
    def __init__(self, path=None):
        self.path = path or os.environ.get('BRIDGE_DB') or os.path.join(os.path.dirname(__file__), 'data', 'progress.db')
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS progress(
                user TEXT, set_id TEXT, item TEXT, box INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0, last_seen REAL, PRIMARY KEY(user, set_id, item))""")

    def _db(self):
        return sqlite3.connect(self.path)

    def boxes(self, user, set_id):
        with self._db() as db:
            rows = db.execute('SELECT item, box FROM progress WHERE user=? AND set_id=?', (user, set_id)).fetchall()
        return dict(rows)

    def next_item(self, user, set_id, last=None, rng=random):
        items = items_of(set_id)
        boxes = self.boxes(user, set_id)
        pool = [it for it in items if it['id'] != last] or items
        weights = [2 ** (BOXES - 1 - boxes.get(it['id'], 0)) for it in pool]    # unmastered items come up more often
        return rng.choices(pool, weights=weights)[0]

    def record(self, user, set_id, item, correct):
        box = self.boxes(user, set_id).get(item, 0)
        box = min(box + 1, BOXES - 1) if correct else 0
        with self._db() as db:
            db.execute("""INSERT INTO progress(user,set_id,item,box,attempts,correct,last_seen) VALUES(?,?,?,?,1,?,?)
                ON CONFLICT(user,set_id,item) DO UPDATE SET box=excluded.box, attempts=attempts+1,
                correct=correct+excluded.correct, last_seen=excluded.last_seen""",
                (user, set_id, item, box, 1 if correct else 0, time.time()))
        return box

    def mastery(self, user, set_id):
        n = len(SETS[set_id]['items']())
        top = sum(1 for b in self.boxes(user, set_id).values() if b == BOXES - 1)
        return top / n

    def summary(self, user):
        out = []
        with self._db() as db:
            for sid, meta in SETS.items():
                att, cor = db.execute('SELECT COALESCE(SUM(attempts),0), COALESCE(SUM(correct),0) FROM progress WHERE user=? AND set_id=?',
                                      (user, sid)).fetchone()
                out.append(dict(id=sid, title=meta['title'], items=len(meta['items']()), mastery=round(self.mastery(user, sid), 3),
                                attempts=att, correct=cor))
        return out

    def reset(self, user):
        with self._db() as db:
            db.execute('DELETE FROM progress WHERE user=?', (user,))
