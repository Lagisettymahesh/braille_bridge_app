"""Text-to-Braille conversion engine for Braille Bridge.
Conforms to Unified English Braille (UEB) Grade 1 & Grade 2 standards,
and the Bharati Braille standard for Hindi.

A Braille cell is composed of 6 dots numbered:
    1 (top-left)      4 (top-right)
    2 (middle-left)   5 (middle-right)
    3 (bottom-left)   6 (bottom-right)

Each cell is stored as an integer 0..63 where bit (n - 1) corresponds to dot n.
Mapped to Unicode Braille Patterns: U+2800 + value (U+2800 to U+283F).
"""

def cell(*dots):
    """Return an integer 0..63 encoding the specified 1-based dot positions."""
    return sum(1 << (d - 1) for d in dots)

def to_unicode(c):
    """Convert an integer cell 0..63 to a Unicode Braille character."""
    return chr(0x2800 + (c & 0x3F))

# ---------------- English Alphabet & Core Indicators ----------------
_AJ = {
    'a': (1,), 'b': (1, 2), 'c': (1, 4), 'd': (1, 4, 5), 'e': (1, 5),
    'f': (1, 2, 4), 'g': (1, 2, 4, 5), 'h': (1, 2, 5), 'i': (2, 4), 'j': (2, 4, 5)
}
EN = {k: cell(*v) for k, v in _AJ.items()}

# Letters k-t add dot 3 to a-j
for k, base in zip('klmnopqrst', 'abcdefghij'):
    EN[k] = EN[base] | cell(3)

# Letters u, v, x, y, z add dots 3 and 6 to a-e
for k, base in zip('uvxyz', 'abcde'):
    EN[k] = EN[base] | cell(3, 6)

# Letter w was added later in French Braille: dots 2, 4, 5, 6
EN['w'] = cell(2, 4, 5, 6)

# Indicators
CAP = cell(6)               # Capital letter indicator
NUM = cell(3, 4, 5, 6)      # Numeric indicator (dots 3, 4, 5, 6)
LETTER_PREFIX = cell(5, 6)  # Letter indicator following a number if necessary

# Digits 1-9 (a-i), 0 (j)
DIGIT = {str(i + 1): EN[c] for i, c in enumerate('abcdefghi')}
DIGIT['0'] = EN['j']

# Standard UEB Punctuation & Symbols
PUNCT = {
    '.': cell(2, 5, 6),
    ',': cell(2),
    ';': cell(2, 3),
    ':': cell(2, 5),
    '!': cell(2, 3, 5),
    '?': cell(2, 3, 6),
    "'": cell(3),
    '‘': cell(3),
    '’': cell(3),
    '-': cell(3, 6),
    '–': cell(6, 3, 6),       # En-dash
    '—': cell(6, 3, 6),       # Em-dash
}

# Multi-cell Symbols (UEB Standard)
SPECIAL_SYMBOLS = {
    '@': [cell(4), cell(1)],                       # At sign
    '&': [cell(4), cell(1, 2, 3, 4, 6)],           # Ampersand
    '%': [cell(4, 6), cell(3, 5, 6)],              # Percent
    '/': [cell(4, 5, 6), cell(3, 4)],              # Forward slash
    '\\': [cell(4, 5, 6), cell(1, 6)],             # Backslash
    '+': [cell(5), cell(2, 3, 5)],                 # Plus sign
    '=': [cell(5), cell(2, 3, 5, 6)],              # Equals sign
    '<': [cell(5), cell(1, 2, 6)],                 # Less than
    '>': [cell(5), cell(3, 4, 5)],                 # Greater than
    '*': [cell(5), cell(3, 5)],                    # Asterisk
    '_': [cell(4, 5, 6), cell(3, 6)],              # Underscore
    '$': [cell(4), cell(2, 3, 4)],                 # Dollar sign
    '#': [cell(4, 5, 6), cell(1, 4, 5, 6)],        # Hash / Number sign
    '~': [cell(4, 5), cell(3, 5)],                 # Tilde
    '^': [cell(4, 5), cell(2, 6)],                 # Caret
    '|': [cell(4, 5, 6), cell(1, 2, 5, 6)],        # Vertical bar
}

BRACKET = {
    '(': [cell(5), cell(1, 2, 6)],
    ')': [cell(5), cell(3, 4, 5)],
    '[': [cell(4, 6), cell(1, 2, 6)],
    ']': [cell(4, 6), cell(3, 4, 5)],
    '{': [cell(4, 5, 6), cell(1, 2, 6)],
    '}': [cell(4, 5, 6), cell(3, 4, 5)],
}

QUOTE = {
    True: [cell(4, 5), cell(2, 3, 6)],   # Open double quote
    False: [cell(4, 5), cell(3, 5, 6)]   # Close double quote
}

# ---------------- Grade 2 Contractions (UEB) ----------------
# Standalone Whole-Word Signs
WORDSIGN = {
    'but': 'b', 'can': 'c', 'do': 'd', 'every': 'e', 'from': 'f',
    'go': 'g', 'have': 'h', 'just': 'j', 'knowledge': 'k', 'like': 'l',
    'more': 'm', 'not': 'n', 'people': 'p', 'quite': 'q', 'rather': 'r',
    'so': 's', 'that': 't', 'us': 'u', 'very': 'v', 'will': 'w',
    'it': 'x', 'you': 'y', 'as': 'z'
}

# Strong Whole-Word Contractions (usable both standalone and within words)
STRONG_WORD = {
    'and': cell(1, 2, 3, 4, 6),
    'for': cell(1, 2, 3, 4, 5, 6),
    'of': cell(1, 2, 3, 5, 6),
    'the': cell(2, 3, 4, 6),
    'with': cell(2, 3, 4, 5, 6)
}

# Standard Group Signs (Parts of words)
GROUP = {
    'ch': cell(1, 6),
    'sh': cell(1, 4, 6),
    'th': cell(1, 4, 5, 6),
    'wh': cell(1, 5, 6),
    'ou': cell(1, 2, 5, 6),
    'st': cell(3, 4),
    'ing': cell(3, 4, 6),
    'ed': cell(1, 2, 4, 6),
    'er': cell(1, 2, 4, 5, 6),
    'ow': cell(2, 4, 6),
    'ar': cell(3, 4, 5),
    'gh': cell(1, 2, 6),
    'in': cell(3, 5),
    'en': cell(2, 6),
    'ble': cell(3, 4, 5, 6)
}

INSIDE = ['and', 'for', 'with', 'the', 'of']
GROUP_ORDER = sorted(GROUP, key=len, reverse=True)


def _word_g2(w):
    """Translate a single English word into Grade 2 Braille cells."""
    lw = w.lower()
    if lw in WORDSIGN:
        return [EN[WORDSIGN[lw]]]
    if lw in STRONG_WORD:
        return [STRONG_WORD[lw]]

    out, i, n = [], 0, len(lw)
    while i < n:
        # Check for strong word signs within word
        matched = False
        for s in INSIDE:
            if lw.startswith(s, i) and n > len(s):
                out.append(STRONG_WORD[s])
                i += len(s)
                matched = True
                break
        if matched:
            continue

        # Check for group signs
        for g in GROUP_ORDER:
            # Rule: 'ing' cannot appear at the beginning of a word
            if lw.startswith(g, i) and not (g == 'ing' and i == 0):
                # Rule: 'ea', 'bb', 'cc', 'ff', 'gg' only inside word (not start or end)
                if g in ('ea', 'bb', 'cc', 'ff', 'gg'):
                    if i == 0 or i + len(g) >= n:
                        continue
                out.append(GROUP[g])
                i += len(g)
                matched = True
                break
        if matched:
            continue

        # Single letter fallback
        out.append(EN[lw[i]])
        i += 1
    return out


def english(text, grade=1, unsupported=None):
    """Translate English text into Braille cells (Grade 1 or Grade 2 UEB)."""
    out, i, n, quote_open = [], 0, len(text), True

    while i < n:
        ch = text[i]

        # 1. Letters & Words
        if ch.isalpha() and ch.isascii():
            j = i
            while j < n and text[j].isalpha() and text[j].isascii():
                j += 1
            word = text[i:j]

            # Capitalization rules
            if len(word) > 1 and word.isupper():
                out += [CAP, CAP]   # Word capitalization indicator
            elif word[0].isupper():
                out.append(CAP)     # Single letter capital indicator

            if grade == 2 and not (word.isupper() and len(word) > 1):
                out += _word_g2(word)
            else:
                out += [EN[c] for c in word.lower()]
            i = j

        # 2. Numbers (with embedded decimals & commas)
        elif ch.isdigit():
            out.append(NUM)
            while i < n:
                if text[i].isdigit():
                    out.append(DIGIT[text[i]])
                    i += 1
                elif text[i] == '.' and (i + 1 < n) and text[i + 1].isdigit():
                    # Decimal point within numbers
                    out.append(PUNCT['.'])
                    i += 1
                elif text[i] == ',' and (i + 1 < n) and text[i + 1].isdigit():
                    # Thousands separator within numbers
                    out.append(PUNCT[','])
                    i += 1
                else:
                    break

        # 3. Special multi-cell symbols (@, &, %, /, =, +, etc.)
        elif ch in SPECIAL_SYMBOLS:
            out += SPECIAL_SYMBOLS[ch]
            i += 1

        # 4. Standard Punctuation
        elif ch in PUNCT:
            # Check for double-dash / em-dash '--'
            if ch == '-' and (i + 1 < n) and text[i + 1] == '-':
                out += [cell(6), cell(3, 6)]
                i += 2
            else:
                out.append(PUNCT[ch])
                i += 1

        # 5. Brackets
        elif ch in BRACKET:
            out += BRACKET[ch]
            i += 1

        # 6. Quotes
        elif ch in ('"', '“', '”'):
            out += QUOTE[quote_open]
            quote_open = not quote_open
            i += 1

        # 7. Whitespace (spaces, newlines, tabs)
        elif ch == '\n':
            out.append(0)  # Preserved as a blank cell / break
            i += 1
        elif ch == '\r':
            i += 1  # Skip standalone CR
        elif ch.isspace():
            out.append(0)
            i += 1

        # 8. Unsupported characters -> Full 6-dot cell (cell 1,2,3,4,5,6)
        else:
            out.append(cell(1, 2, 3, 4, 5, 6))
            if unsupported is not None:
                unsupported.append(ch)
            i += 1

    return out


# ---------------- Hindi (Bharati Braille Standard) ----------------
# Official Indian National Standard for Bharati Braille
HI_CONS = {
    'क': (1, 3), 'ख': (4, 6), 'ग': (1, 2, 4, 5), 'घ': (1, 2, 6), 'ङ': (3, 4, 6),
    'च': (1, 4), 'छ': (1, 6), 'ज': (2, 4, 5), 'झ': (3, 5, 6), 'ञ': (2, 5),
    'ट': (2, 3, 4, 5, 6), 'ठ': (2, 4, 5, 6), 'ड': (1, 2, 4, 6), 'ढ': (1, 2, 3, 4, 5, 6), 'ण': (3, 4, 5, 6),
    'त': (2, 3, 4, 5), 'थ': (1, 4, 5, 6), 'द': (1, 4, 5), 'ध': (2, 3, 4, 6), 'न': (1, 3, 4, 5),
    'प': (1, 2, 3, 4), 'फ': (2, 3, 5), 'ब': (1, 2), 'भ': (4, 5), 'म': (1, 3, 4),
    'य': (1, 3, 4, 5, 6), 'र': (1, 2, 3, 5), 'ल': (1, 2, 3), 'व': (1, 2, 3, 6),
    'श': (1, 4, 6), 'ष': (1, 2, 3, 4, 6), 'स': (2, 3, 4), 'ह': (1, 2, 5),
    'क्ष': (1, 2, 3, 4, 5), 'ज्ञ': (1, 5, 6), 'श्र': (1, 2, 4, 5, 6), 'त्र': (2, 3, 4, 5, 6)
}

HI_VOW = {
    'अ': (1,), 'आ': (3, 4, 5), 'इ': (2, 4), 'ई': (3, 5), 'उ': (1, 3, 6),
    'ऊ': (1, 2, 5, 6), 'ऋ': (1, 2, 3, 5, 6), 'ए': (1, 5), 'ऐ': (3, 4),
    'ओ': (1, 3, 5), 'औ': (2, 4, 6)
}

HI_MATRA = {
    'ा': 'आ', 'ि': 'इ', 'ी': 'ई', 'ु': 'उ', 'ू': 'ऊ',
    'ृ': 'ऋ', 'े': 'ए', 'ै': 'ऐ', 'ो': 'ओ', 'ौ': 'औ'
}

HI_MARK = {
    'ं': (5, 6),       # Anusvara
    'ः': (6,),         # Visarga
    'ँ': (3,),         # Chandrabindu
    '्': (4,),         # Halant / Virama
    '़': (5,),         # Nukta
    'ऽ': (2,),         # Avagraha
    '।': (2, 5, 6),    # Purna Viram / Danda
    ',': (2,),
    '?': (2, 3, 6),
    '!': (2, 3, 5),
    ':': (2, 5),
    ';': (2, 3)
}

# Devanagari Digits ०-९
HI_DIGIT = {chr(0x966 + i): EN[c] for i, c in enumerate('jabcdefghi')}


def hindi(text, unsupported=None):
    """Translate Hindi text into Bharati Braille cells, cleanly supporting mixed English and numbers."""
    out, i, n = [], 0, len(text)

    while i < n:
        ch = text[i]

        # Multi-char conjunct check: e.g. क्ष, ज्ञ, त्र, श्र
        conjunct_found = False
        for cj in ('क्ष', 'ज्ञ', 'श्र', 'त्र'):
            if text.startswith(cj, i):
                out.append(cell(*HI_CONS[cj]))
                i += len(cj)
                conjunct_found = True
                break
        if conjunct_found:
            continue

        # Hindi Consonants
        if ch in HI_CONS:
            out.append(cell(*HI_CONS[ch]))
            i += 1

        # Hindi Independent Vowels
        elif ch in HI_VOW:
            out.append(cell(*HI_VOW[ch]))
            i += 1

        # Hindi Dependent Vowels (Matras)
        elif ch in HI_MATRA:
            out.append(cell(*HI_VOW[HI_MATRA[ch]]))
            i += 1

        # Hindi Diacritics and Marks
        elif ch in HI_MARK:
            # Check for double danda '॥'
            if ch == '।' and (i + 1 < n) and text[i + 1] == '।':
                out += [cell(2, 5, 6), cell(2, 5, 6)]
                i += 2
            else:
                out.append(cell(*HI_MARK[ch]))
                i += 1

        # Hindi Devanagari Digits (०-९)
        elif ch in HI_DIGIT:
            out.append(NUM)
            while i < n and text[i] in HI_DIGIT:
                out.append(HI_DIGIT[text[i]])
                i += 1

        # Whitespace
        elif ch.isspace():
            out.append(0)
            i += 1

        # Mixed ASCII English & Numbers embedded in Hindi text
        elif ch.isascii():
            j = i
            # Group contiguous ASCII characters into an English block
            while j < n and text[j].isascii() and not text[j].isspace():
                j += 1
            ascii_block = text[i:j]
            out += english(ascii_block, grade=1, unsupported=unsupported)
            i = j

        # Unsupported Character
        else:
            out.append(cell(1, 2, 3, 4, 5, 6))
            if unsupported is not None:
                unsupported.append(ch)
            i += 1

    return out


def detect_language(text):
    """Automatically detect whether the text is predominantly Hindi or English."""
    devanagari_count = sum('ऀ' <= c <= 'ॿ' for c in text)
    latin_count = sum(('a' <= c.lower() <= 'z') for c in text)
    if devanagari_count > 0 and devanagari_count >= latin_count:
        return 'hi'
    return 'en'


def convert_full(text, lang='auto', grade=1):
    """Convert text to Braille with cells, Unicode Braille, ASCII Braille, and metadata."""
    if lang == 'auto':
        lang = detect_language(text)
    bad = []
    cells = hindi(text, bad) if lang == 'hi' else english(text, grade, bad)
    return {
        'lang': lang,
        'grade': 1 if lang == 'hi' else int(grade),
        'cells': cells,
        'braille': ''.join(to_unicode(c) for c in cells),
        'ascii': to_ascii(cells),
        'unsupported': sorted(set(bad)),
        'count': len(cells)
    }


def convert(text, lang='auto', grade=1):
    """Convenience wrapper returning (cells, unicode_string)."""
    r = convert_full(text, lang, grade)
    return r['cells'], r['braille']


# ---------------- North American Braille ASCII (BRF Standard) ----------------
# Index = 6-bit integer cell value (0..63)
_ASCII = " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)="

def to_ascii(cells):
    """Convert integer cells to standard North American Braille ASCII."""
    return ''.join(_ASCII[c & 0x3F] for c in cells)

def from_ascii(text):
    """Convert Braille ASCII characters back into integer cells 0..63."""
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


# ---------------- Bidirectional Reverse Decoder (Braille -> Text) ----------------
def decode_cells(cells, lang='en'):
    """Decode integer Braille cells back into plain readable English or Hindi text."""
    if lang == 'hi':
        res = []
        is_num = False
        hi_digit_rev = {v: k for k, v in HI_DIGIT.items()}
        cons_rev = {cell(*v): k for k, v in HI_CONS.items()}
        vow_rev = {cell(*v): k for k, v in HI_VOW.items()}
        mark_rev = {cell(*v): k for k, v in HI_MARK.items()}
        prev_was_cons = False

        i = 0
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
        # English Decoding (supporting Grade 1 & Grade 2 indicators)
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
                is_all_cap = False
                i += 1
                continue
            if c == CAP:
                if i + 1 < len(cells) and cells[i + 1] == CAP:
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
    """Decode either Unicode Braille or ASCII Braille string into readable text."""
    if any(0x2800 <= ord(c) <= 0x283F for c in braille_input):
        cells = from_unicode(braille_input)
    else:
        cells = from_ascii(braille_input)
    return decode_cells(cells, lang)


def to_brf(cells, width=40):
    """Word-wrapped Braille ASCII text (BRF format) with lines of at most `width` cells."""
    words = to_ascii(cells).split(' ')
    cur, lines = '', []
    for w in words:
        while len(w) > width:
            if cur:
                lines.append(cur)
                cur = ''
            lines.append(w[:width])
            w = w[width:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return '\r\n'.join(lines)
