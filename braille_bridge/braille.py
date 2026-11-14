"""Text-to-Braille conversion engine.
English Grade 1 / simplified Grade 2 (UEB) and Hindi (Bharati Braille).
A Braille cell is 6 dots numbered 1-3 (left column, top->bottom), 4-6 (right column).
Each cell is stored as an int 0..63 (bit n-1 = dot n) -> Unicode U+2800+value.
"""
def cell(*dots):
    return sum(1 << (d - 1) for d in dots)

def to_unicode(c):
    return chr(0x2800 + c)

# ---------------- English ----------------
_AJ = {'a': (1,), 'b': (1,2), 'c': (1,4), 'd': (1,4,5), 'e': (1,5),
       'f': (1,2,4), 'g': (1,2,4,5), 'h': (1,2,5), 'i': (2,4), 'j': (2,4,5)}
EN = {k: cell(*v) for k, v in _AJ.items()}
for k, base in zip('klmnopqrst', 'abcdefghij'):          # add dot 3
    EN[k] = EN[base] | cell(3)
for k, base in zip('uvxyz', 'abcde'):                     # add dots 3,6
    EN[k] = EN[base] | cell(3, 6)
EN['w'] = cell(2,4,5,6)
CAP, NUM = cell(6), cell(3,4,5,6)
DIGIT = {str(i+1): EN[c] for i, c in enumerate('abcdefghi')}; DIGIT['0'] = EN['j']
PUNCT = {'.': cell(2,5,6), ',': cell(2), ';': cell(2,3), ':': cell(2,5), '!': cell(2,3,5),
         '?': cell(2,3,6), "'": cell(3), '-': cell(3,6)}
BRACKET = {'(': [cell(5), cell(1,2,6)], ')': [cell(5), cell(3,4,5)]}
QUOTE = {True: [cell(4,5), cell(2,3,6)], False: [cell(4,5), cell(3,5,6)]}   # open / close
# Simplified Grade-2 tables (UEB)
WORDSIGN = {'but':'b','can':'c','do':'d','every':'e','from':'f','go':'g','have':'h','just':'j',
            'knowledge':'k','like':'l','more':'m','not':'n','people':'p','quite':'q','rather':'r',
            'so':'s','that':'t','us':'u','very':'v','will':'w','it':'x','you':'y','as':'z'}
STRONG_WORD = {'and': cell(1,2,3,4,6), 'for': cell(1,2,3,4,5,6), 'of': cell(1,2,3,5,6),
               'the': cell(2,3,4,6), 'with': cell(2,3,4,5,6)}
GROUP = {'ch': cell(1,6), 'sh': cell(1,4,6), 'th': cell(1,4,5,6), 'wh': cell(1,5,6),
         'ou': cell(1,2,5,6), 'st': cell(3,4), 'ing': cell(3,4,6), 'ed': cell(1,2,4,6),
         'er': cell(1,2,4,5,6), 'ow': cell(2,4,6), 'ar': cell(3,4,5), 'gh': cell(1,2,6)}
INSIDE = ['and', 'for', 'with', 'the']                       # strong contractions inside words
GROUP_ORDER = sorted(GROUP, key=len, reverse=True)

def _word_g2(w):
    lw = w.lower()
    if lw in WORDSIGN:
        return [EN[WORDSIGN[lw]]]
    if lw in STRONG_WORD:
        return [STRONG_WORD[lw]]
    out, i = [], 0
    while i < len(lw):
        for s in INSIDE:
            if lw.startswith(s, i) and len(lw) > len(s):
                out.append(STRONG_WORD[s]); i += len(s); break
        else:
            for g in GROUP_ORDER:
                if lw.startswith(g, i) and not (g == 'ing' and i == 0):
                    out.append(GROUP[g]); i += len(g); break
            else:
                out.append(EN[lw[i]]); i += 1
    return out

def english(text, grade=1, unsupported=None):
    out, i, n, quote_open = [], 0, len(text), True
    while i < n:
        ch = text[i]
        if ch.isalpha() and ch.isascii():
            j = i
            while j < n and text[j].isalpha() and text[j].isascii():
                j += 1
            word = text[i:j]
            if len(word) > 1 and word.isupper():
                out += [CAP, CAP]
            elif word[0].isupper():
                out.append(CAP)
            if grade == 2 and not (word.isupper() and len(word) > 1):
                if word[0].islower() or len(word) == 1 or word[1:].islower():
                    out += _word_g2(word)
                else:
                    out += [EN[c] for c in word.lower()]
            else:
                out += [EN[c] for c in word.lower()]
            i = j
        elif ch.isdigit():
            out.append(NUM)
            while i < n and text[i].isdigit():
                out.append(DIGIT[text[i]]); i += 1
        elif ch in PUNCT:
            out.append(PUNCT[ch]); i += 1
        elif ch in BRACKET:
            out += BRACKET[ch]; i += 1
        elif ch == '"':
            out += QUOTE[quote_open]; quote_open = not quote_open; i += 1
        elif ch.isspace():
            out.append(0); i += 1
        else:
            out.append(cell(1,2,3,4,5,6)); i += 1      # unsupported -> full cell
            if unsupported is not None: unsupported.append(ch)
    return out

# ---------------- Hindi (Bharati Braille) ----------------
HI_CONS = {'क':(1,3),'ख':(4,6),'ग':(1,2,4,5),'घ':(1,2,6),'ङ':(3,4,6),'च':(1,4),'छ':(1,6),
 'ज':(2,4,5),'झ':(3,5,6),'ञ':(2,5),'ट':(2,3,4,5,6),'ठ':(2,4,5,6),'ड':(1,2,4,6),'ढ':(1,2,3,4,5,6),
 'ण':(3,4,5,6),'त':(2,3,4,5),'थ':(1,4,5,6),'द':(1,4,5),'ध':(2,3,4,6),'न':(1,3,4,5),'प':(1,2,3,4),
 'फ':(2,3,5),'ब':(1,2),'भ':(4,5),'म':(1,3,4),'य':(1,3,4,5,6),'र':(1,2,3,5),'ल':(1,2,3),
 'व':(1,2,3,6),'श':(1,4,6),'ष':(1,2,3,4,6),'स':(2,3,4),'ह':(1,2,5)}
HI_VOW = {'अ':(1,),'आ':(3,4,5),'इ':(2,4),'ई':(3,5),'उ':(1,3,6),'ऊ':(1,2,5,6),'ए':(1,5),
          'ऐ':(3,4),'ओ':(1,3,5),'औ':(2,4,6)}
HI_MATRA = {'ा':'आ','ि':'इ','ी':'ई','ु':'उ','ू':'ऊ','े':'ए','ै':'ऐ','ो':'ओ','ौ':'औ'}
HI_MARK = {'ं': (5,6), 'ः': (6,), 'ँ': (3,), '्': (4,), '।': (2,5,6), ',': (2,),
           '?': (2,3,6), '!': (2,3,5)}
HI_DIGIT = {chr(0x966 + i): EN[c] for i, c in enumerate('jabcdefghi')}   # ०-९

def hindi(text, unsupported=None):
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in HI_CONS: out.append(cell(*HI_CONS[ch]))
        elif ch in HI_VOW: out.append(cell(*HI_VOW[ch]))
        elif ch in HI_MATRA: out.append(cell(*HI_VOW[HI_MATRA[ch]]))
        elif ch in HI_MARK: out.append(cell(*HI_MARK[ch]))
        elif ch in HI_DIGIT:
            out.append(NUM)
            while i < n and text[i] in HI_DIGIT:
                out.append(HI_DIGIT[text[i]]); i += 1
            continue
        elif ch.isspace(): out.append(0)
        elif ch.isascii() and (ch.isalnum() or ch in PUNCT or ch in '()"'):
            out += english(ch)
        else:
            out.append(cell(1,2,3,4,5,6))
            if unsupported is not None: unsupported.append(ch)
        i += 1
    return out

def detect_language(text):
    dev = sum('ऀ' <= c <= 'ॿ' for c in text)
    return 'hi' if dev > 0 and dev >= 0.3 * max(1, sum(c.isalpha() for c in text)) else 'en'

def convert(text, lang='auto', grade=1):
    """Return (cells, unicode_string)."""
    r = convert_full(text, lang, grade)
    return r['cells'], r['braille']

def convert_full(text, lang='auto', grade=1):
    """Convert text; return a dict with cells, Unicode Braille, ASCII Braille (BRF) and any unsupported characters."""
    if lang == 'auto':
        lang = detect_language(text)
    bad = []
    cells = hindi(text, bad) if lang == 'hi' else english(text, grade, bad)
    return {'lang': lang, 'grade': 1 if lang == 'hi' else grade, 'cells': cells,
            'braille': ''.join(to_unicode(c) for c in cells), 'ascii': to_ascii(cells),
            'unsupported': sorted(set(bad)), 'count': len(cells)}

# North American Braille ASCII (BRF): index = 6-bit cell value
_ASCII = " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)="

def to_ascii(cells):
    return ''.join(_ASCII[c] for c in cells)

def from_ascii(text):
    return [_ASCII.index(ch) for ch in text.upper() if ch in _ASCII]

def from_unicode(text):
    """Convert Unicode Braille patterns (U+2800..U+283F) to list of integer cells 0..63."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x2800 <= cp <= 0x283F:
            out.append(cp - 0x2800)
        elif ch.isspace():
            out.append(0)
    return out

def decode_cells(cells, lang='en'):
    """Decode Braille cells back into English or Hindi text."""
    if lang == 'hi':
        res = []
        is_num = False
        hi_digit_rev = {v: k for k, v in HI_DIGIT.items()}
        cons_rev = {cell(*v): k for k, v in HI_CONS.items()}
        vow_rev = {cell(*v): k for k, v in HI_VOW.items()}
        mark_rev = {cell(*v): k for k, v in HI_MARK.items()}
        i = 0
        prev_was_cons = False
        while i < len(cells):
            c = cells[i]
            if c == 0:
                res.append(' ')
                is_num = False
                prev_was_cons = False
                i += 1
                continue
            if c == NUM:
                is_num = True
                prev_was_cons = False
                i += 1
                continue
            if is_num and c in hi_digit_rev:
                res.append(hi_digit_rev[c])
                i += 1
                continue
            if c in cons_rev:
                res.append(cons_rev[c])
                prev_was_cons = True
                i += 1
                continue
            if c in vow_rev:
                v = vow_rev[c]
                if prev_was_cons:
                    matra = next((m for m, orig in HI_MATRA.items() if orig == v), None)
                    res.append(matra if matra else v)
                else:
                    res.append(v)
                prev_was_cons = False
                i += 1
                continue
            if c in mark_rev:
                res.append(mark_rev[c])
                prev_was_cons = False
                i += 1
                continue
            res.append('?')
            prev_was_cons = False
            i += 1
        return ''.join(res)
    else:
        res = []
        is_cap = False
        is_all_cap = False
        is_num = False
        en_rev = {v: k for k, v in EN.items()}
        digit_rev = {v: k for k, v in DIGIT.items()}
        punct_rev = {v: k for k, v in PUNCT.items()}
        strong_rev = {v: k for k, v in STRONG_WORD.items()}
        group_rev = {v: k for k, v in GROUP.items()}
        i = 0
        while i < len(cells):
            c = cells[i]
            if c == 0:
                res.append(' ')
                is_num = False
                is_cap = False
                i += 1
                continue
            if c == CAP:
                if i + 1 < len(cells) and cells[i+1] == CAP:
                    is_all_cap = True
                    i += 2
                    continue
                is_cap = True
                i += 1
                continue
            if c == NUM:
                is_num = True
                i += 1
                continue
            if is_num and c in digit_rev:
                res.append(digit_rev[c])
            elif c in strong_rev:
                res.append(strong_rev[c])
            elif c in group_rev:
                res.append(group_rev[c])
            elif c in en_rev:
                ch = en_rev[c]
                if is_all_cap or is_cap:
                    ch = ch.upper()
                    if not is_all_cap:
                        is_cap = False
                res.append(ch)
            elif c in punct_rev:
                res.append(punct_rev[c])
                is_num = False
            else:
                res.append('?')
            i += 1
        return ''.join(res)

def decode(braille_input, lang='en'):
    """Decode either Unicode Braille or ASCII Braille into readable text."""
    if any(0x2800 <= ord(c) <= 0x283F for c in braille_input):
        cells = from_unicode(braille_input)
    else:
        cells = from_ascii(braille_input)
    return decode_cells(cells, lang)

def to_brf(cells, width=40):
    """Word-wrapped Braille ASCII text, lines of at most `width` cells, CRLF line ends."""
    words, cur, lines = to_ascii(cells).split(' '), '', []
    for w in words:
        while len(w) > width:
            if cur: lines.append(cur); cur = ''
            lines.append(w[:width]); w = w[width:]
        if not cur: cur = w
        elif len(cur) + 1 + len(w) <= width: cur += ' ' + w
        else: lines.append(cur); cur = w
    lines.append(cur)
    return '\r\n'.join(lines)

