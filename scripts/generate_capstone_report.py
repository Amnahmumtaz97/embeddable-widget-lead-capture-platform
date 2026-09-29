from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "pdf" / "lead-capture-platform-capstone-report.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 18 * mm

INK = colors.HexColor("#102A2A")
DEEP = colors.HexColor("#0B3B35")
TEAL = colors.HexColor("#0F766E")
MINT = colors.HexColor("#DDF5EC")
GREEN = colors.HexColor("#20A77B")
PALE = colors.HexColor("#F3F8F6")
SLATE = colors.HexColor("#52666A")
LINE = colors.HexColor("#C9D9D4")
WHITE = colors.white
AMBER = colors.HexColor("#C27A0A")


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverEyebrow", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=MINT, spaceAfter=8, tracking=1.2))
styles.add(ParagraphStyle(name="CoverTitle", fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=WHITE, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName="Helvetica", fontSize=12, leading=18, textColor=colors.HexColor("#D7E8E3"), spaceAfter=8))
styles.add(ParagraphStyle(name="H1x", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=DEEP, spaceBefore=0, spaceAfter=11))
styles.add(ParagraphStyle(name="H2x", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle(name="Bodyx", fontName="Helvetica", fontSize=9.2, leading=13.2, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", fontName="Helvetica", fontSize=7.6, leading=10.5, textColor=SLATE, spaceAfter=3))
styles.add(ParagraphStyle(name="Tinyx", fontName="Helvetica", fontSize=6.8, leading=9, textColor=SLATE))
styles.add(ParagraphStyle(name="Callout", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=DEEP, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="TableHead", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=WHITE))
styles.add(ParagraphStyle(name="TableCell", fontName="Helvetica", fontSize=7.2, leading=9, textColor=INK))
styles.add(ParagraphStyle(name="TableCellSmall", fontName="Helvetica", fontSize=6.5, leading=8, textColor=INK))
styles.add(ParagraphStyle(name="ReportCode", fontName="Courier", fontSize=7.2, leading=10, textColor=DEEP, backColor=PALE, borderColor=LINE, borderWidth=0.5, borderPadding=7, spaceAfter=7))
styles.add(ParagraphStyle(name="CenterSmall", fontName="Helvetica", fontSize=8, leading=11, textColor=SLATE, alignment=TA_CENTER))


def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def section_title(number, title, kicker=None):
    items = [p(f"{number}. {title}", "H1x")]
    if kicker:
        items.append(p(kicker, "Bodyx"))
    return items


def badge(text, bg=MINT, fg=DEEP):
    table = Table([[Paragraph(text, ParagraphStyle(name=f"badge-{text}", parent=styles["Smallx"], fontName="Helvetica-Bold", textColor=fg, alignment=TA_CENTER))]], colWidths=[39 * mm], rowHeights=[8 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, fg), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return table


def metric(value, label, note=""):
    content = [Paragraph(value, ParagraphStyle(name=f"metric-{value}", fontName="Helvetica-Bold", fontSize=20, leading=22, textColor=TEAL, alignment=TA_CENTER)), p(label, "Callout")]
    if note:
        content.append(p(note, "CenterSmall"))
    table = Table([[content]], colWidths=[52 * mm], rowHeights=[31 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return table


def architecture_drawing():
    d = Drawing(500, 260)
    boxes = [
        (10, 180, 110, 58, "Widget owner", "Authenticated API"),
        (195, 180, 110, 58, "FastAPI", "Routes + services"),
        (380, 180, 110, 58, "Supabase", "TLS + migrations"),
        (10, 55, 110, 58, "Customer site", "Different origin"),
        (195, 55, 110, 58, "Public path", "Validate + protect"),
        (380, 55, 110, 58, "Outbox worker", "Retry + alert"),
    ]
    for x, y, w, h, title, sub in boxes:
        d.add(Rect(x, y, w, h, rx=8, ry=8, fillColor=PALE, strokeColor=TEAL, strokeWidth=1.2))
        d.add(String(x + w / 2, y + 34, title, fontName="Helvetica-Bold", fontSize=10, fillColor=DEEP, textAnchor="middle"))
        d.add(String(x + w / 2, y + 17, sub, fontName="Helvetica", fontSize=7.5, fillColor=SLATE, textAnchor="middle"))
    arrows = [
        (120, 209, 195, 209, "CRUD + dashboard"),
        (305, 209, 380, 209, "tenant SQL"),
        (120, 84, 195, 84, "config + submit"),
        (305, 84, 380, 84, "durable job"),
        (250, 180, 250, 113, "CORS boundary"),
    ]
    for x1, y1, x2, y2, label in arrows:
        d.add(Line(x1, y1, x2, y2, strokeColor=GREEN, strokeWidth=1.5))
        if x1 == x2:
            d.add(String(x1 + 7, (y1 + y2) / 2, label, fontName="Helvetica", fontSize=6.5, fillColor=SLATE))
        else:
            d.add(String((x1 + x2) / 2, y1 + 7, label, fontName="Helvetica", fontSize=6.5, fillColor=SLATE, textAnchor="middle"))
    d.add(String(250, 15, "Three paths stay separate: owner administration, public delivery, and visitor submission.", fontName="Helvetica-Oblique", fontSize=8, fillColor=SLATE, textAnchor="middle"))
    return d


def resilience_drawing():
    d = Drawing(500, 205)
    steps = [
        (6, 120, 79, 48, "REQUEST", "CORS + size"),
        (108, 120, 79, 48, "VALIDATE", "schema + fields"),
        (210, 120, 79, 48, "PROTECT", "rate + spam"),
        (312, 120, 79, 48, "ENRICH", "A -> B -> none"),
        (414, 120, 79, 48, "COMMIT", "lead + job"),
    ]
    for i, (x, y, w, h, title, sub) in enumerate(steps):
        fill = MINT if i < 4 else colors.HexColor("#C8F0DE")
        d.add(Rect(x, y, w, h, rx=7, ry=7, fillColor=fill, strokeColor=TEAL, strokeWidth=1))
        d.add(String(x + w / 2, y + 29, title, fontName="Helvetica-Bold", fontSize=8.5, fillColor=DEEP, textAnchor="middle"))
        d.add(String(x + w / 2, y + 14, sub, fontName="Helvetica", fontSize=6.5, fillColor=SLATE, textAnchor="middle"))
        if i < len(steps) - 1:
            d.add(Line(x + w, y + h / 2, steps[i + 1][0], y + h / 2, strokeColor=GREEN, strokeWidth=1.5))
    d.add(Rect(120, 28, 120, 46, rx=7, ry=7, fillColor=PALE, strokeColor=AMBER, strokeWidth=1))
    d.add(String(180, 55, "UPSTREAM FAILURE", fontName="Helvetica-Bold", fontSize=8, fillColor=AMBER, textAnchor="middle"))
    d.add(String(180, 40, "store without geo", fontName="Helvetica", fontSize=7, fillColor=SLATE, textAnchor="middle"))
    d.add(Rect(300, 28, 120, 46, rx=7, ry=7, fillColor=PALE, strokeColor=AMBER, strokeWidth=1))
    d.add(String(360, 55, "NOTIFY FAILURE", fontName="Helvetica-Bold", fontSize=8, fillColor=AMBER, textAnchor="middle"))
    d.add(String(360, 40, "retry, then alert", fontName="Helvetica", fontSize=7, fillColor=SLATE, textAnchor="middle"))
    d.add(Line(350, 120, 180, 74, strokeColor=AMBER, strokeWidth=1))
    d.add(Line(454, 120, 360, 74, strokeColor=AMBER, strokeWidth=1))
    return d


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SLATE)
    canvas.drawRightString(PAGE_W - MARGIN_X, 9 * mm, f"Page {doc.page}")
    canvas.drawString(MARGIN_X, 9 * mm, "Implementation report | 29 September 2026")
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.circle(PAGE_W - 25 * mm, PAGE_H - 30 * mm, 52 * mm, fill=1, stroke=0)
    canvas.setFillColor(GREEN)
    canvas.circle(PAGE_W - 15 * mm, 15 * mm, 42 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#8DDCC0"))
    canvas.setLineWidth(1)
    for offset in range(0, 120, 16):
        canvas.line(15 * mm, 32 * mm + offset, PAGE_W - 15 * mm, 32 * mm + offset)
    canvas.restoreState()


def build_story():
    story = []
    story.extend([
        Spacer(1, 36 * mm),
        p("BACKEND TRACK - CAPSTONE REPORT", "CoverEyebrow"),
        p("Embeddable Widget &<br/>Lead-Capture Platform", "CoverTitle"),
        p("A hardened, multi-tenant FastAPI platform with Supabase persistence, cross-origin delivery, resilient enrichment, and verifiable acceptance evidence.", "CoverSub"),
        Spacer(1, 18 * mm),
        Table([[badge("LIVE ON SUPABASE", colors.HexColor("#133F38"), colors.HexColor("#8DE2C1")), badge("9 TESTS PASSING", colors.HexColor("#133F38"), colors.HexColor("#8DE2C1")), badge("$0 RUNTIME AI", colors.HexColor("#133F38"), colors.HexColor("#8DE2C1"))]], colWidths=[45 * mm] * 3, hAlign="LEFT", style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]),
        Spacer(1, 67 * mm),
        p("Prepared from the implemented repository, deterministic test evidence, and live Supabase smoke verification.", "CoverSub"),
        p("Report date: 29 September 2026", "CoverEyebrow"),
        PageBreak(),
    ])

    story.extend(section_title("1", "Executive summary", "The system turns one widget definition into a safe public acquisition path and a tenant-isolated owner view."))
    story.append(Table([[metric("6", "product capabilities", "CRUD, embed, delivery, capture, resilience, analytics"), metric("15/15", "core requirements", "mapped to deterministic proof"), metric("9/9", "automated tests", "acceptance + resilience")]], colWidths=[55 * mm] * 3, hAlign="CENTER", style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("<b>Outcome.</b> The repository now implements authenticated widget management, versioned delivery, a public CORS submission boundary, abuse controls, two-provider geolocation fallback, a durable notification outbox, and owner analytics. PostgreSQL is provided by Supabase through an SSL-required Session pooler connection; the browser receives no database credential."))
    story.append(p("<b>Verification.</b> Nine deterministic tests pass. A live smoke test returned 200 for config and the second-origin demo, stored an idempotent lead in Supabase, and exposed it through the authenticated dashboard with correct short-cache headers."))
    story.append(p("<b>Engineering posture.</b> The implementation favors clear failure boundaries over feature volume: untrusted input receives clean 4xx responses, non-critical providers may fail without losing leads, and repeated submissions do not duplicate storage or side effects."))
    story.append(p("Delivered scope", "H2x"))
    delivered = [
        ["Area", "Delivered behavior", "Primary concern"],
        ["Owner API", "Tenant-scoped CRUD, snippet generation, lead list, aggregate stats", "Authorization"],
        ["Widget delivery", "Versioned JS, short-lived config cache, Shadow DOM rendering", "Performance"],
        ["Public capture", "CORS, preflight, size/schema checks, dynamic field validation", "Boundary safety"],
        ["Resilience", "Rate limit, honeypot, geo fallback, durable notification retry", "Graceful degradation"],
        ["Persistence", "Supabase migrations, indexes, transactions, idempotency key", "Correctness"],
    ]
    story.append(styled_table(delivered, [33 * mm, 95 * mm, 38 * mm]))
    story.append(PageBreak())

    story.extend(section_title("2", "Architecture and request paths", "The code and runtime keep authenticated administration separate from public delivery and visitor submission."))
    story.append(architecture_drawing())
    story.append(p("Layer boundaries", "H2x"))
    layers = [
        ["Layer", "Responsibility", "Representative modules"],
        ["HTTP", "Routes, middleware, status codes, CORS, response headers", "app/api.py"],
        ["Business", "Validation, rate limiting, enrichment, job processing", "app/services/*"],
        ["Data", "Tenant-scoped SQL, migrations, analytics, outbox transaction", "app/repositories.py"],
        ["Client", "Config fetch, Shadow DOM form, idempotent submission wiring", "assets/widget.v1.js"],
        ["Operations", "Container runtime, Supabase TLS, DNS, seed and proof commands", "docker-compose.yml"],
    ]
    story.append(styled_table(layers, [27 * mm, 86 * mm, 53 * mm]))
    story.append(p("The Supabase connection stays server-side. This preserves multi-statement transactions, partial unique indexes, and <font name='Courier'>FOR UPDATE SKIP LOCKED</font> for the worker while avoiding exposure of secret or database credentials to the widget."))
    story.append(PageBreak())

    story.extend(section_title("3", "Data model and tenant isolation", "Ownership is explicit in every persistent record and every authenticated query."))
    model = [
        ["Table", "Key fields", "Integrity and access rule"],
        ["tenants", "id, name, api_key_hash", "Only SHA-256 key hashes are stored; raw keys remain environment/user input."],
        ["widgets", "tenant_id, type, form_fields, display_options", "Every owner read/write filters tenant_id; public reads require active=true."],
        ["submissions", "tenant_id, widget_id, data, geo, idempotency_key", "Tenant is copied from the widget; partial unique index prevents retry duplicates."],
        ["side_effect_jobs", "submission_id, status, attempts, next_attempt_at", "Created in the same transaction as the lead; claimed with row locking."],
        ["ai_usage", "provider, model, tokens, cost_usd", "Reserved for attributed usage; current runtime AI cost is zero."],
    ]
    story.append(styled_table(model, [28 * mm, 61 * mm, 77 * mm]))
    story.append(p("Isolation proof", "H2x"))
    isolation = [
        ["Control", "Proof"],
        ["Authentication required", "Requests without a valid API key return 401."],
        ["Opaque cross-tenant behavior", "Tenant B receives 404 for tenant A widget reads and updates."],
        ["Submission ownership", "Tenant identity is derived from the selected widget, never trusted from the public payload."],
        ["Dashboard scope", "Tenant B receives an empty lead list after a tenant A submission."],
        ["Secret hygiene", ".env is ignored; browser-safe configuration never contains the database URL."],
    ]
    story.append(styled_table(isolation, [48 * mm, 118 * mm]))
    story.append(p("The API accepts <font name='Courier'>X-API-Key</font> or a bearer key. Authentication returns only tenant identity and all repository methods require that identity as an explicit argument, reducing the chance of an unscoped query."))
    story.append(PageBreak())

    story.extend(section_title("4", "Hardened submission path", "Every public request crosses explicit validation, abuse, enrichment, and persistence boundaries."))
    story.append(resilience_drawing())
    controls = [
        ["Stage", "Successful path", "Failure behavior"],
        ["Transport", "CORS preflight accepted from external origins", "Unsupported or oversized input returns JSON 4xx"],
        ["Validation", "Configured fields normalized and type checked", "Unexpected, missing, invalid email, or overlong fields return 422"],
        ["Abuse", "Per-IP and per-widget windows admit normal traffic", "Burst returns 429 + Retry-After; honeypot returns quiet 202 and stores nothing"],
        ["Enrichment", "Provider A, then provider B", "Both providers down: continue without geo"],
        ["Persistence", "Lead and outbox job commit atomically", "Idempotency conflict returns original lead"],
        ["Notification", "Worker completes console notification", "Exponential retry; final attempt emits alert"],
    ]
    story.append(styled_table(controls, [29 * mm, 69 * mm, 68 * mm]))
    story.append(p("The main success invariant is simple: if validation and abuse checks pass, an optional dependency cannot turn the submission into a 500 or erase a stored lead."))
    story.append(PageBreak())

    story.extend(section_title("5", "API and delivery contract", "A small surface area supports the three actors without mixing responsibilities."))
    api_rows = [
        ["Method", "Path", "Auth", "Contract"],
        ["GET", "/health", "No", "Service health"],
        ["POST", "/api/widgets", "Yes", "Create widget"],
        ["GET", "/api/widgets", "Yes", "List tenant widgets"],
        ["GET/PUT/DELETE", "/api/widgets/{id}", "Yes", "Tenant-scoped CRUD"],
        ["GET", "/api/widgets/{id}/snippet", "Yes", "One-line versioned embed"],
        ["GET", "/assets/widget.v1.js", "No", "One-year immutable cache"],
        ["GET", "/widgets/{id}/config", "No", "60-second public config cache"],
        ["POST", "/submissions", "No", "Protected public capture"],
        ["GET", "/api/submissions", "Yes", "Tenant lead table"],
        ["GET", "/api/dashboard/stats", "Yes", "Time, widget, and geo aggregates"],
    ]
    story.append(styled_table(api_rows, [23 * mm, 59 * mm, 20 * mm, 64 * mm]))
    story.append(p("Embed contract", "H2x"))
    story.append(p("&lt;script async src=\"http://localhost:8000/assets/widget.v1.js?id={widget-id}\"&gt;&lt;/script&gt;", "ReportCode"))
    story.append(p("Caching strategy", "H2x"))
    cache_rows = [
        ["Asset", "Header", "Reason"],
        ["widget.v1.js", "public, max-age=31536000, immutable", "Filename changes on release; safe long cache."],
        ["widget config", "public, max-age=60, stale-while-revalidate=300", "Owner edits become visible quickly without a fetch on every view."],
    ]
    story.append(styled_table(cache_rows, [35 * mm, 70 * mm, 61 * mm]))
    story.append(p("The demo page runs on port 5500 while the API runs on 8000, proving that delivery and submission operate across different browser origins."))
    story.append(PageBreak())

    story.extend(section_title("6", "Verification and acceptance evidence", "Automated and live checks cover the full contract, including failure paths."))
    story.append(Table([[metric("9", "automated tests", "all passing"), metric("200", "live config + demo", "Supabase smoke"), metric("1", "idempotent lead", "visible in dashboard")]], colWidths=[55 * mm] * 3, hAlign="CENTER", style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 7 * mm))
    tests = [
        ["Test area", "Verified behavior"],
        ["CRUD and isolation", "Auth rejection, full CRUD, cross-tenant 404 behavior"],
        ["Delivery", "Versioned snippet, immutable bundle, config cache, different-origin wiring"],
        ["CORS", "OPTIONS preflight and allowed request headers"],
        ["Boundary validation", "Malformed JSON, invalid models, dynamic fields, 413 payload limit"],
        ["Abuse and idempotency", "429 with Retry-After, honeypot drop, replay without duplicate"],
        ["Geo resilience", "Provider A down -> B; both down -> submission continues"],
        ["Notification resilience", "Forced failure keeps lead and marks job for retry"],
        ["Supabase configuration", "URL precedence, missing config failure, forced TLS"],
    ]
    story.append(styled_table(tests, [50 * mm, 116 * mm]))
    story.append(p("Live Supabase transcript", "H2x"))
    story.append(p("ConfigStatus=200<br/>ConfigCache=public, max-age=60, stale-while-revalidate=300<br/>SubmissionAccepted=true<br/>SubmissionReplayed=false<br/>DashboardTotal=1<br/>DemoStatus=200", "ReportCode"))
    story.append(p("The smoke test uses a stable idempotency key, so repeating it cannot create duplicate leads."))
    story.append(PageBreak())

    story.extend(section_title("7", "Operations, setup, and limitations", "The runtime is deliberately small: one API container, one static demo container, and Supabase."))
    story.append(p("Operator runbook", "H2x"))
    runbook = [
        ["Step", "Command or action", "Expected result"],
        ["1", "Set SUPABASE_DATABASE_URL to Session pooler URI", "PostgreSQL URI, port 5432, password URL-encoded"],
        ["2", "docker compose up --build", "API and demo containers start; migration runs"],
        ["3", "docker compose exec app python seed.py", "Two demo tenants and fixed demo widget created"],
        ["4", "docker compose exec app pytest -q", "9 tests pass"],
        ["5", "Open localhost:8000/docs and localhost:5500", "API docs and cross-origin demo available"],
    ]
    story.append(styled_table(runbook, [12 * mm, 90 * mm, 64 * mm]))
    story.append(p("Operational notes", "H2x"))
    notes = [
        "TLS is required for every database connection.",
        "Docker Compose pins public DNS resolvers because Docker Desktop's embedded resolver failed on this host.",
        "The old local database container was removed after Supabase verification; its Docker volume was retained for recovery.",
        "The notification side effect is a console implementation by design; reliability behavior, not email delivery, is the evaluated concern.",
    ]
    story.append(bullet_table(notes))
    story.append(p("Known limitations", "H2x"))
    limitations = [
        "Rate-limit state is process-local; multi-replica deployment should use a shared store such as Redis.",
        "CORS defaults to all origins for embeddability; production should support an owner-configured allowlist where appropriate.",
        "Geo enrichment is best effort and private/test IPs may produce no location.",
        "The dashboard is a proof interface, not a production identity or session system.",
    ]
    story.append(bullet_table(limitations, amber=True))
    story.append(PageBreak())

    story.extend(section_title("8", "Conclusion and references", "The capstone meets its core contract and demonstrates production-oriented backend reasoning."))
    story.append(p("The implemented platform is intentionally compact but complete. It proves the hard parts of an embeddable lead product: multi-tenant ownership, public-browser compatibility, attacker-aware boundaries, failure isolation, durable side effects, observable evidence, and a real managed database."))
    story.append(p("The strongest interview narrative is not the widget's CSS. It is the submission invariant: validate early, reject abuse predictably, degrade optional dependencies, commit the business record once, and move secondary work behind a durable boundary."))
    story.append(p("Final status", "H2x"))
    final_rows = [
        ["Category", "Status"],
        ["Section 6 core requirements", "PASS - all 15 mapped to proof"],
        ["Shared backend requirements", "PASS - architecture, validation, jobs, persistence, idempotency, secrets, cost"],
        ["Automated verification", "PASS - 9 tests"],
        ["Live managed persistence", "PASS - Supabase migration, seed, submit, dashboard"],
        ["Second-origin delivery", "PASS - demo page on port 5500"],
    ]
    story.append(styled_table(final_rows, [64 * mm, 102 * mm]))
    story.append(p("References", "H2x"))
    refs = [
        "FlyRank Internship Backend Track - Embeddable Widget & Lead-Capture Platform capstone brief.",
        "Repository README.md, DESIGN.md, EVIDENCE.md, BUILDLOG.md, capstone.yaml, and source modules.",
        "Supabase documentation: Connect to Postgres and API key security guidance.",
        "Docker documentation: Docker Desktop with the WSL 2 backend on Windows.",
    ]
    story.append(bullet_table(refs))
    story.append(Spacer(1, 12 * mm))
    story.append(p("Prepared as a portfolio-ready implementation report. No secrets, passwords, or private connection strings are included.", "CenterSmall"))
    return story


def styled_table(rows, widths):
    converted = []
    for row_index, row in enumerate(rows):
        converted.append([p(str(cell), "TableHead" if row_index == 0 else "TableCell") for cell in row])
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), DEEP),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for idx in range(1, len(rows)):
        commands.append(("BACKGROUND", (0, idx), (-1, idx), WHITE if idx % 2 else PALE))
    table.setStyle(TableStyle(commands))
    return table


def bullet_table(items, amber=False):
    rows = []
    dot_color = AMBER if amber else GREEN
    for item in items:
        rows.append([Paragraph("-", ParagraphStyle(name=f"dot-{len(rows)}-{amber}", fontName="Helvetica-Bold", fontSize=10, textColor=dot_color)), p(item, "Bodyx")])
    table = Table(rows, colWidths=[6 * mm, 160 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return table


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Embeddable Widget & Lead-Capture Platform - Capstone Report",
        author="FlyRank Backend Track Capstone",
        subject="Implementation, architecture, security, resilience, and verification report",
    )
    cover_frame = Frame(MARGIN_X, MARGIN_BOTTOM, PAGE_W - 2 * MARGIN_X, PAGE_H - MARGIN_BOTTOM - 18 * mm, id="cover")
    body_frame = Frame(MARGIN_X, MARGIN_BOTTOM, PAGE_W - 2 * MARGIN_X, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM, id="body")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=cover, autoNextPageTemplate="Body"),
        PageTemplate(id="Body", frames=[body_frame], onPageEnd=on_page),
    ])
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
