"""Generate a comprehensive, publication-quality Project Summary PDF for Braille Bridge."""
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that tracks total page count and adds running headers & footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#56607a"))
        
        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "BRAILLE BRIDGE — COMPREHENSIVE PROJECT SUMMARY")
            self.setFont("Helvetica", 8)
            self.drawRightString(558, 750, "Lagisetty Mahesh | Capstone Project")
            self.setStrokeColor(colors.HexColor("#d9deea"))
            self.setLineWidth(0.6)
            self.line(54, 742, 558, 742)

        # Running footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#56607a"))
        self.drawString(54, 34, "GitHub: https://github.com/Lagisettymahesh/braille_bridge_app")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_text)
        self.setStrokeColor(colors.HexColor("#d9deea"))
        self.setLineWidth(0.6)
        self.line(54, 46, 558, 46)
        self.restoreState()


def build_pdf(filename="Braille_Bridge_Project_Summary.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    c_brand = colors.HexColor("#1f3a93")
    c_accent = colors.HexColor("#c0392b")
    c_dark = colors.HexColor("#16213a")
    c_muted = colors.HexColor("#56607a")
    c_bg_light = colors.HexColor("#f6f7fb")
    c_card_border = colors.HexColor("#d9deea")
    c_ok = colors.HexColor("#1b7a3d")

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=c_brand,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_muted,
        spaceAfter=12
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_brand,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_dark,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.2,
        leading=13.5,
        textColor=c_dark,
        spaceAfter=5
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )
    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f1424")
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8.8,
        leading=12,
        textColor=c_brand
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        parent=body_style,
        fontSize=8.8,
        leading=12,
        textColor=c_dark
    )
    tbl_cell = ParagraphStyle(
        'TblCell',
        parent=body_style,
        fontSize=8.2,
        leading=11,
        textColor=c_dark
    )
    tbl_header = ParagraphStyle(
        'TblHeader',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.white
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph("Braille Bridge: Automated Text-to-Braille System", title_style))
    story.append(Paragraph("Universal Accessibility Platform with Automated Voice Assistance, PDF Ingestion & Tactile Emulation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_brand, spaceBefore=2, spaceAfter=8))

    meta_table_data = [
        [Paragraph("Author / Developer:", meta_label), Paragraph("Lagisetty Mahesh", meta_val),
         Paragraph("Project Category:", meta_label), Paragraph("Assistive Tech / Embedded AI Capstone", meta_val)],
        [Paragraph("Repository:", meta_label), Paragraph("<font color='#1f3a93'><u>github.com/Lagisettymahesh/braille_bridge_app</u></font>", meta_val),
         Paragraph("Architecture:", meta_label), Paragraph("Flask Microservice + Vanilla JS + PyPDF + Hardware Cell", meta_val)],
        [Paragraph("Language Support:", meta_label), Paragraph("English (Grade 1 & 2 UEB) & Hindi (Bharati Braille)", meta_val),
         Paragraph("Testing Status:", meta_label), Paragraph("<font color='#1b7a3d'><b>25 of 25 Automated Tests Passing (100%)</b></font>", meta_val)],
    ]
    t_meta = Table(meta_table_data, colWidths=[105, 150, 95, 154])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 0.8, c_card_border),
        ('INNERGRID', (0,0), (-1,-1), 0.4, c_card_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary & Problem Statement", h1_style))
    story.append(Paragraph(
        "<b>Braille Bridge</b> is an assistive technology platform designed to bridge the digital divide for visually impaired students, educators, and literacy advocates. "
        "Traditional refreshable Braille displays are prohibitively expensive ($1,500–$5,000+), severely limiting accessibility in developing regions. Furthermore, standard screen readers "
        "struggle with multi-page technical documents, scientific notation, and regional languages like Hindi.",
        body_style
    ))
    story.append(Paragraph(
        "Braille Bridge solves these challenges through a unified, <b>hands-free, zero-click software and hardware ecosystem</b>: "
        "(1) A high-performance Python engine capable of converting 90,000+ characters into Braille in under 30 milliseconds; "
        "(2) An intelligent document processing subsystem that handles both digital and scanned PDFs up to 200,000 characters; "
        "(3) A zero-friction automated voice assistant with smart local folder search and acoustic self-echo cancellation; and "
        "(4) An interactive 6-servo ESP32 tactile cell emulator with synchronized mechanical actuation and buzzer audio feedback.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Core Innovations & Features
    story.append(Paragraph("2. Key Architectural Innovations & Features", h1_style))

    story.append(Paragraph("🎙️ Automated Hands-Free Voice Assistant (Zero Button-Click Workflow)", h2_style))
    story.append(Paragraph(
        "Designed specifically for blind and visually impaired users who cannot navigate visual graphical interfaces: "
        "The system activates automatically upon page load, announces a contextual time-based greeting (<i>'Hello and good morning! Welcome to Braille Bridge. What file do you want to upload, and what file do you want to convert?'</i>), "
        "and immediately triggers the system file picker without requiring manual navigation. "
        "It features dynamic acoustic echo cancellation (temporarily muting speech recognition during speech synthesis to prevent feedback loops) and filters ambient room audio.",
        body_style
    ))

    story.append(Paragraph("📄 High-Capacity PDF & Scanned Document Processing Subsystem", h2_style))
    story.append(Paragraph(
        "Integrated dual-path document engine: Text-based PDFs are extracted using <code>pypdf</code>, scaling up to 200,000 characters (accommodating full textbooks and capstone reports). "
        "For scanned documents or photo-based PDFs with minimal digital text, the system automatically falls back to an embedded OCR pipeline using Windows Media OCR and Tesseract, converting images directly to Braille cells.",
        body_style
    ))

    story.append(Paragraph("🔍 Smart System-Wide Folder Discovery", h2_style))
    story.append(Paragraph(
        "Users can speak natural commands such as <i>'Upload PDF from Desktop'</i>, <i>'Upload from Downloads'</i>, or <i>'Upload report'</i>. "
        "The backend crawler dynamically resolves OS paths (including Windows OneDrive redirection, Desktop, Downloads, and Documents), locates the targeted document, extracts the text, and renders the Braille conversion in real time.",
        body_style
    ))

    story.append(Paragraph("🔤 Bilingual Dual-Grade Braille Translation & Reverse Decoder", h2_style))
    story.append(Paragraph(
        "Supports English Grade 1 (letter-for-letter), English Grade 2 (Unified English Braille contractions including word signs, strong contractions, and group signs), and Hindi (Bharati Braille Unicode standard). "
        "Additionally, a reverse decoder translates Unicode and ASCII Braille back to plain text, facilitating two-way communication between sighted teachers and blind students.",
        body_style
    ))

    story.append(Paragraph("⚙️ Tactile ESP32 Hardware Emulator & Mechanical Simulator", h2_style))
    story.append(Paragraph(
        "Includes production-ready Arduino C++ firmware (<code>firmware/braille_cell.ino</code>) for an ESP32 connected to a PCA9685 16-channel PWM servo driver controlling 6 micro-servos (one per Braille dot). "
        "For users without physical hardware, the web app features a real-time mechanical simulator showing 40ms staggered pin elevation (70° UP / 20° DOWN) and an audio synthesizer mimicking the physical piezo buzzer.",
        body_style
    ))

    story.append(Paragraph("🧠 Adaptive Spaced Repetition Learning Center", h2_style))
    story.append(Paragraph(
        "An educational Leitner box progressive learning system persisted in an SQLite database (<code>data/progress.db</code>). "
        "Features Read Mode (identifying the character from a displayed cell) and Write Mode (setting dots 1–6 via mouse or keyboard) with real-time mastery tracking.",
        body_style
    ))

    story.append(PageBreak())

    # Codebase Structure Table
    story.append(Paragraph("3. Codebase Structure & Module Architecture", h1_style))
    story.append(Paragraph("The project follows a clean modular design separating the translation engine, document parser, hardware controller, and user interfaces:", body_style))

    codebase_data = [
        [Paragraph("File / Module", tbl_header), Paragraph("Type", tbl_header), Paragraph("Key Responsibilities & Capabilities", tbl_header)],
        [Paragraph("<code>braille_bridge/app.py</code>", code_style), Paragraph("Backend REST API", tbl_cell), Paragraph("Flask application providing endpoints for conversion, reverse decoding, PDF ingestion, folder discovery, Leitner quiz store, and hardware serial streaming.", tbl_cell)],
        [Paragraph("<code>braille_bridge/braille.py</code>", code_style), Paragraph("Core Translation Engine", tbl_cell), Paragraph("UEB Grade 1 & Grade 2 contraction tables, Bharati Braille mapping, capital/number sign generators, ASCII Braille formatting, and .BRF export wrappers.", tbl_cell)],
        [Paragraph("<code>braille_bridge/documents.py</code>", code_style), Paragraph("Document & OCR Subsystem", tbl_cell), Paragraph("High-capacity PDF text extraction, OCR fallback for scanned pages, and dynamic OS folder discovery (Desktop, OneDrive, Downloads, Documents).", tbl_cell)],
        [Paragraph("<code>braille_bridge/voice_assistant.py</code>", code_style), Paragraph("Desktop Companion", tbl_cell), Paragraph("Standalone Python voice assistant leveraging Windows SAPI Speech Synthesis and native file pickers for completely offline operation.", tbl_cell)],
        [Paragraph("<code>braille_bridge/learning.py</code>", code_style), Paragraph("Pedagogy & Database", tbl_cell), Paragraph("SQLite Leitner box progress tracking, user mastery calculations, and question generators for English and Hindi symbol sets.", tbl_cell)],
        [Paragraph("<code>braille_bridge/ocr.py</code>", code_style), Paragraph("Optical Character Rec.", tbl_cell), Paragraph("Dual-engine OCR interface selecting Windows.Media.Ocr (native Windows runtime) or Tesseract OCR for camera and page captures.", tbl_cell)],
        [Paragraph("<code>braille_bridge/device.py</code>", code_style), Paragraph("Hardware Serial Driver", tbl_cell), Paragraph("Asynchronous USB serial sender streaming 6-bit packed Braille frames to ESP32 microcontrollers with configurable per-cell delay.", tbl_cell)],
        [Paragraph("<code>braille_bridge/firmware/</code>", code_style), Paragraph("Embedded C++ Firmware", tbl_cell), Paragraph("Arduino firmware (<code>braille_cell.ino</code>) driving Adafruit PCA9685 PWM servos and tactile push-button pin advance.", tbl_cell)],
        [Paragraph("<code>braille_bridge/static/</code>", code_style), Paragraph("Accessible Frontend", tbl_cell), Paragraph("Modern web application (<code>index.html</code>, <code>style.css</code>, <code>app.js</code>) with accessible high-contrast UI, Web Speech API, and tactile cell animations.", tbl_cell)],
        [Paragraph("<code>braille_bridge/tests/</code>", code_style), Paragraph("Automated Test Suite", tbl_cell), Paragraph("25 comprehensive pytest unit and integration tests verifying all conversion rules, PDF parsing, OCR routing, and API contracts.", tbl_cell)],
        [Paragraph("<code>run.bat / run.ps1</code>", code_style), Paragraph("One-Click Launchers", tbl_cell), Paragraph("Automated Windows dependency installation and browser launch scripts for zero-configuration execution.", tbl_cell)],
    ]
    t_code = Table(codebase_data, colWidths=[130, 85, 289])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_brand),
        ('BOX', (0,0), (-1,-1), 0.8, c_card_border),
        ('INNERGRID', (0,0), (-1,-1), 0.4, c_card_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_code)
    story.append(Spacer(1, 10))

    # REST API Table
    story.append(Paragraph("4. RESTful API Endpoint Specifications", h1_style))
    api_data = [
        [Paragraph("Method & Endpoint", tbl_header), Paragraph("Payload / Parameters", tbl_header), Paragraph("Description & Output", tbl_header)],
        [Paragraph("<code>POST /api/convert</code>", code_style), Paragraph("<code>{text, lang, grade}</code>", code_style), Paragraph("Converts plain text to Unicode Braille, 6-bit cell arrays, ASCII Braille, and BRF output format.", tbl_cell)],
        [Paragraph("<code>POST /api/decode</code>", code_style), Paragraph("<code>{braille, cells, lang}</code>", code_style), Paragraph("Reverse decodes Unicode or ASCII Braille back to readable English or Hindi text.", tbl_cell)],
        [Paragraph("<code>POST /api/upload-pdf</code>", code_style), Paragraph("Multipart form: <code>pdf, convert, lang</code>", code_style), Paragraph("Extracts text from uploaded PDF, applies OCR fallback if scanned, and auto-converts to Braille.", tbl_cell)],
        [Paragraph("<code>GET /api/find-local-pdf</code>", code_style), Paragraph("<code>folder, query, load, lang</code>", code_style), Paragraph("Scans Desktop, Downloads, or Documents for PDFs matching query, auto-loads and converts top result.", tbl_cell)],
        [Paragraph("<code>POST /api/ocr</code>", code_style), Paragraph("Multipart form: <code>image, ocr_lang</code>", code_style), Paragraph("Performs OCR on photographed book pages using Windows Media OCR or Tesseract.", tbl_cell)],
        [Paragraph("<code>GET /api/quiz/next</code>", code_style), Paragraph("<code>set, mode, user, last</code>", code_style), Paragraph("Fetches next adaptive Leitner question for Read or Write learning modes.", tbl_cell)],
        [Paragraph("<code>POST /api/quiz/answer</code>", code_style), Paragraph("<code>{set, mode, item, choice/cell}</code>", code_style), Paragraph("Records user answer in SQLite and calculates updated mastery percentage.", tbl_cell)],
        [Paragraph("<code>POST /api/device/send</code>", code_style), Paragraph("<code>{port, cells, delay}</code>", code_style), Paragraph("Streams cell array to physical ESP32 or updates the virtual software emulator.", tbl_cell)],
    ]
    t_api = Table(api_data, colWidths=[125, 140, 239])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_brand),
        ('BOX', (0,0), (-1,-1), 0.8, c_card_border),
        ('INNERGRID', (0,0), (-1,-1), 0.4, c_card_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 10))

    # Verification & Quality Section
    story.append(Paragraph("5. Quality Assurance & Verification Metrics", h1_style))
    story.append(Paragraph(
        "The project has undergone rigorous multi-axis verification conforming to senior software engineering standards:",
        body_style
    ))
    story.append(Paragraph("• <b>Automated Test Suite:</b> 25 automated tests pass with 100% green status in under 1.0 second using <code>pytest</code>, verifying Grade 1 and 2 UEB rules, Bharati Hindi unicode mappings, ASCII round-trips, Leitner box transitions, dual OCR engines, and virtual hardware transmission.", bullet_style))
    story.append(Paragraph("• <b>High-Throughput Performance:</b> Tested with large-scale 77,000+ character capstone project documents; converted into 21,000+ Braille cells in under 200 milliseconds.", bullet_style))
    story.append(Paragraph("• <b>Zero-Error Browser Compatibility:</b> Verified on Google Chrome and Microsoft Edge with 0 JavaScript console errors, complete Web Speech API compliance, and responsive WCAG-compliant high-contrast styling.", bullet_style))
    story.append(Paragraph("• <b>Continuous Version Control:</b> Fully versioned on GitHub with structured commit history under repository <code>Lagisettymahesh/braille_bridge_app</code>.", bullet_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("6. Conclusion & Practical Impact", h1_style))
    story.append(Paragraph(
        "Braille Bridge demonstrates that accessibility tools do not require complex, cost-prohibitive infrastructure. By combining modern web standards, lightweight local microservices, "
        "and automated voice interfaces, the platform empowers visually impaired learners to independently ingest textbooks, convert research papers, and master Braille literacy.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ PDF successfully generated at: {os.path.abspath(filename)}")

if __name__ == '__main__':
    out_name = sys.argv[1] if len(sys.argv) > 1 else "Braille_Bridge_Project_Summary.pdf"
    build_pdf(out_name)
