"""Adaptive Braille learning module: Leitner spaced repetition system with tiered difficulty,
daily statistics, and revision of incorrect answers persisted in SQLite.
"""
import os
import random
import sqlite3
import time
import datetime
from braille import english, WORDSIGN, STRONG_WORD, GROUP, HI_CONS, HI_VOW, HI_MARK, cell

BOXES = 3  # box 0 = new / missed, box 1 = in progress, box 2 = mastered

# ---------------- Item Generators ----------------
def _en_letters():
    return [(c, c, english(c)[0], 'en-IN') for c in 'abcdefghijklmnopqrstuvwxyz']

def _en_wordsigns():
    return [(w, f'“{w}” ({c})', english(c)[0], 'en-IN') for w, c in WORDSIGN.items()]

def _en_contractions():
    items = [(w, f'“{w}” (word-sign)', STRONG_WORD[w], 'en-IN') for w in ('and', 'for', 'of', 'the', 'with')]
    items += [(g, f'“{g}” (group-sign)', GROUP[g], 'en-IN') for g in sorted(GROUP.keys())]
    return items

def _hi_vowels():
    return [(v, f'{v} (स्वर)', cell(*d), 'hi-IN') for v, d in HI_VOW.items()]

def _hi_cons():
    base_cons = [c for c in HI_CONS if c not in ('क्ष', 'ज्ञ', 'श्र', 'त्र')]
    return [(c, f'{c} (व्यंजन)', cell(*HI_CONS[c]), 'hi-IN') for c in base_cons]

def _hi_conjuncts_marks():
    items = [(c, f'{c} (संयुक्त अक्षर)', cell(*HI_CONS[c]), 'hi-IN') for c in ('क्ष', 'ज्ञ', 'श्र', 'त्र')]
    mark_labels = {'ं': 'ं (अनुस्वार)', 'ः': 'ः (विसर्ग)', 'ँ': 'ँ (चन्द्रबिन्दु)'}
    for m, d in HI_MARK.items():
        if m in mark_labels:
            items.append((m, mark_labels[m], cell(*d), 'hi-IN'))
    return items

SETS = {
    # Tiered Curricula
    'en-beginner': {'title': 'English Beginner: Letters a–z', 'level': 'Beginner', 'lang': 'en', 'items': _en_letters},
    'en-intermediate': {'title': 'English Intermediate: Grade 2 Wordsigns', 'level': 'Intermediate', 'lang': 'en', 'items': _en_wordsigns},
    'en-advanced': {'title': 'English Advanced: Grade 2 Signs', 'level': 'Advanced', 'lang': 'en', 'items': _en_contractions},
    'hi-beginner': {'title': 'Hindi Beginner: Vowels (स्वर)', 'level': 'Beginner', 'lang': 'hi', 'items': _hi_vowels},
    'hi-intermediate': {'title': 'Hindi Intermediate: Consonants (व्यंजन)', 'level': 'Intermediate', 'lang': 'hi', 'items': _hi_cons},
    'hi-advanced': {'title': 'Hindi Advanced: Conjuncts & Marks (संयुक्त)', 'level': 'Advanced', 'lang': 'hi', 'items': _hi_conjuncts_marks},

    # Backward-compatible aliases
    'en-letters': {'title': 'English letters a–z', 'level': 'Beginner', 'lang': 'en', 'items': _en_letters},
    'en-contractions': {'title': 'English Grade 2 signs', 'level': 'Advanced', 'lang': 'en', 'items': _en_contractions},
    'hi-vowels': {'title': 'Hindi vowels (स्वर)', 'level': 'Beginner', 'lang': 'hi', 'items': _hi_vowels},
    'hi-consonants': {'title': 'Hindi consonants (व्यंजन)', 'level': 'Intermediate', 'lang': 'hi', 'items': _hi_cons},
}


def items_of(set_id):
    if set_id not in SETS:
        raise KeyError(f"Unknown learning set: {set_id}")
    return [dict(id=i, label=l, cell=c, lang=lg) for i, l, c, lg in SETS[set_id]['items']()]


class Store:
    def __init__(self, path=None):
        self.path = path or os.environ.get('BRIDGE_DB') or os.path.join(os.path.dirname(__file__), 'data', 'progress.db')
        self._mem_conn = sqlite3.connect(':memory:') if self.path == ':memory:' else None
        if self.path != ':memory:' and os.path.dirname(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS progress(
                user TEXT, set_id TEXT, item TEXT, box INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0, last_seen REAL, PRIMARY KEY(user, set_id, item))""")
            db.execute("""CREATE TABLE IF NOT EXISTS daily_stats(
                user TEXT, day TEXT, attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0,
                PRIMARY KEY(user, day))""")

    def _db(self):
        if self._mem_conn:
            return self._mem_conn
        return sqlite3.connect(self.path)

    def boxes(self, user, set_id):
        with self._db() as db:
            rows = db.execute('SELECT item, box FROM progress WHERE user=? AND set_id=?', (user, set_id)).fetchall()
        return dict(rows)

    def next_item(self, user, set_id, last=None, rng=random, revision_only=False):
        items = items_of(set_id)
        boxes = self.boxes(user, set_id)

        if revision_only:
            # Filter specifically to unmastered items (box == 0 or attempts > correct)
            with self._db() as db:
                unmastered = db.execute(
                    'SELECT item FROM progress WHERE user=? AND set_id=? AND (box=0 OR attempts > correct)',
                    (user, set_id)
                ).fetchall()
            unmastered_ids = {r[0] for r in unmastered}
            rev_pool = [it for it in items if it['id'] in unmastered_ids]
            if rev_pool:
                items = rev_pool

        pool = [it for it in items if it['id'] != last] or items
        weights = [2 ** (BOXES - 1 - boxes.get(it['id'], 0)) for it in pool]
        return rng.choices(pool, weights=weights)[0]

    def record(self, user, set_id, item, correct):
        box = self.boxes(user, set_id).get(item, 0)
        box = min(box + 1, BOXES - 1) if correct else 0
        today = datetime.date.today().isoformat()

        with self._db() as db:
            # 1. Update item progress
            db.execute("""INSERT INTO progress(user,set_id,item,box,attempts,correct,last_seen) VALUES(?,?,?,?,1,?,?)
                ON CONFLICT(user,set_id,item) DO UPDATE SET box=excluded.box, attempts=attempts+1,
                correct=correct+excluded.correct, last_seen=excluded.last_seen""",
                (user, set_id, item, box, 1 if correct else 0, time.time()))

            # 2. Update daily statistics
            db.execute("""INSERT INTO daily_stats(user, day, attempts, correct) VALUES(?,?,1,?)
                ON CONFLICT(user, day) DO UPDATE SET attempts=attempts+1, correct=correct+excluded.correct""",
                (user, today, 1 if correct else 0))

        return box

    def mastery(self, user, set_id):
        n = len(SETS[set_id]['items']())
        if n == 0:
            return 0.0
        top = sum(1 for b in self.boxes(user, set_id).values() if b == BOXES - 1)
        return top / n

    def revision_count(self, user, set_id):
        """Count how many items in this set require revision (box 0 with previous errors)."""
        with self._db() as db:
            row = db.execute(
                'SELECT COUNT(*) FROM progress WHERE user=? AND set_id=? AND (box=0 OR attempts > correct)',
                (user, set_id)
            ).fetchone()
        return row[0] if row else 0

    def summary(self, user):
        # Exclude internal aliases from the public display list
        displayed_keys = ['en-beginner', 'en-intermediate', 'en-advanced', 'hi-beginner', 'hi-intermediate', 'hi-advanced']
        out = []
        with self._db() as db:
            for sid in displayed_keys:
                meta = SETS[sid]
                att, cor = db.execute(
                    'SELECT COALESCE(SUM(attempts),0), COALESCE(SUM(correct),0) FROM progress WHERE user=? AND set_id=?',
                    (user, sid)
                ).fetchone()
                rev_count = self.revision_count(user, sid)
                out.append(dict(
                    id=sid,
                    title=meta['title'],
                    level=meta.get('level', 'Beginner'),
                    lang=meta.get('lang', 'en'),
                    items=len(meta['items']()),
                    mastery=round(self.mastery(user, sid), 3),
                    attempts=att,
                    correct=cor,
                    revision_count=rev_count
                ))
        return out

    def stats(self, user):
        """Return daily and aggregate user learning statistics."""
        with self._db() as db:
            total_att, total_cor = db.execute(
                'SELECT COALESCE(SUM(attempts),0), COALESCE(SUM(correct),0) FROM progress WHERE user=?',
                (user,)
            ).fetchone()
            mastered_items = db.execute(
                'SELECT COUNT(*) FROM progress WHERE user=? AND box=?',
                (user, BOXES - 1)
            ).fetchone()[0]
            daily_rows = db.execute(
                'SELECT day, attempts, correct FROM daily_stats WHERE user=? ORDER BY day DESC LIMIT 7',
                (user,)
            ).fetchall()

        daily_history = [
            {'day': r[0], 'attempts': r[1], 'correct': r[2], 'accuracy': round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0}
            for r in daily_rows
        ]
        accuracy = round(total_cor / total_att * 100, 1) if total_att > 0 else 0.0

        return {
            'total_attempts': total_att,
            'total_correct': total_cor,
            'accuracy': accuracy,
            'mastered_items': mastered_items,
            'daily_history': daily_history
        }

    def reset(self, user):
        with self._db() as db:
            db.execute('DELETE FROM progress WHERE user=?', (user,))
            db.execute('DELETE FROM daily_stats WHERE user=?', (user,))
