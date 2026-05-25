#!/usr/bin/env python3
"""
Generate SSDI 5-Day INFORM Letter Kit PDF
9 pages: Letter template + Procedural explainer + Deadline calendar + Provider tracker + Legal resources
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib import colors

# Output path
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "downloads", "ssdi-5day-inform-letter")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "SSDI-5-Day-INFORM-Letter-Kit.pdf")

# Colors
NAVY = HexColor("#0a2540")
GREEN = HexColor("#00875a")
GRAY = HexColor("#4a4a4a")
LIGHT_GRAY = HexColor("#f0f0f0")
BORDER_GRAY = HexColor("#cccccc")

# Styles
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name='KitTitle',
    fontName='Helvetica-Bold',
    fontSize=22,
    leading=28,
    textColor=NAVY,
    alignment=TA_CENTER,
    spaceAfter=6,
))

styles.add(ParagraphStyle(
    name='KitSubtitle',
    fontName='Helvetica',
    fontSize=11,
    leading=15,
    textColor=GRAY,
    alignment=TA_CENTER,
    spaceAfter=20,
))

styles.add(ParagraphStyle(
    name='SectionTitle',
    fontName='Helvetica-Bold',
    fontSize=14,
    leading=18,
    textColor=NAVY,
    spaceBefore=16,
    spaceAfter=8,
))

styles.add(ParagraphStyle(
    name='SubsectionTitle',
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=14,
    textColor=NAVY,
    spaceBefore=12,
    spaceAfter=6,
))

styles.add(ParagraphStyle(
    name='BodyText2',
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=GRAY,
    alignment=TA_JUSTIFY,
    spaceAfter=8,
))

styles.add(ParagraphStyle(
    name='SmallText',
    fontName='Helvetica',
    fontSize=8.5,
    leading=11,
    textColor=GRAY,
    spaceAfter=4,
))

styles.add(ParagraphStyle(
    name='Citation',
    fontName='Helvetica-Oblique',
    fontSize=9,
    leading=12,
    textColor=HexColor("#555555"),
    leftIndent=20,
    rightIndent=20,
    spaceBefore=8,
    spaceAfter=8,
))

styles.add(ParagraphStyle(
    name='FieldLabel',
    fontName='Helvetica-Bold',
    fontSize=10,
    leading=13,
    textColor=NAVY,
    spaceBefore=10,
    spaceAfter=2,
))

styles.add(ParagraphStyle(
    name='FieldLine',
    fontName='Courier',
    fontSize=10,
    leading=18,
    textColor=GRAY,
    spaceAfter=4,
))

styles.add(ParagraphStyle(
    name='Footer',
    fontName='Helvetica',
    fontSize=7.5,
    leading=10,
    textColor=HexColor("#999999"),
    alignment=TA_CENTER,
))

styles.add(ParagraphStyle(
    name='PageLabel',
    fontName='Helvetica',
    fontSize=8,
    leading=10,
    textColor=HexColor("#999999"),
    alignment=TA_LEFT,
))

styles.add(ParagraphStyle(
    name='BulletBody',
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=GRAY,
    leftIndent=20,
    spaceAfter=4,
))


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )

    story = []

    # ==========================================
    # PAGE 1: INFORM LETTER TEMPLATE
    # ==========================================
    story.append(Paragraph("SSDI 5-Day INFORM Letter Kit", styles['KitTitle']))
    story.append(Paragraph("Customizable template citing 20 CFR § 404.935(a) and HALLEX I-2-5-13", styles['KitSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))

    story.append(Paragraph("INFORM LETTER TEMPLATE", styles['SectionTitle']))
    story.append(Paragraph(
        "Complete the bracketed fields below. Fax or mail to your local hearing office "
        "at least 5 business days before your scheduled hearing date.",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 12))

    # Letter header fields
    story.append(Paragraph("Your Name:", styles['FieldLabel']))
    story.append(Paragraph("[_________________________________]", styles['FieldLine']))
    story.append(Paragraph("Social Security Number (last 4):", styles['FieldLabel']))
    story.append(Paragraph("XXX-XX-[____]", styles['FieldLine']))
    story.append(Paragraph("Hearing Date:", styles['FieldLabel']))
    story.append(Paragraph("[____/____/________]", styles['FieldLine']))
    story.append(Paragraph("Administrative Law Judge:", styles['FieldLabel']))
    story.append(Paragraph("Hon. [_________________________________]", styles['FieldLine']))
    story.append(Paragraph("Hearing Office Address:", styles['FieldLabel']))
    story.append(Paragraph("[_________________________________]", styles['FieldLine']))
    story.append(Paragraph("[_________________________________]", styles['FieldLine']))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceAfter=12))

    # Letter body
    story.append(Paragraph(
        "Dear Judge [____________________],",
        styles['BodyText2']
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Pursuant to <b>20 CFR § 404.935(a)</b>, I am writing to <b>inform</b> "
        "the hearing office that the following evidence exists, is relevant to my claim, "
        "and has been requested but not yet received. I understand that under "
        "<b>HALLEX I-2-5-13</b>, properly informing the hearing office of outstanding "
        "evidence creates a duty to address it in the hearing decision.",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("EVIDENCE IDENTIFICATION (per 20 CFR § 404.935 specificity requirements):", styles['SubsectionTitle']))

    # The 5 specificity elements
    elements_data = [
        ["Element", "Details"],
        ["1. Provider Name & Address", "[Dr./Facility: ________________________]\n[Address: ____________________________]"],
        ["2. Date Range of Treatment", "[From: ____/____/____  To: ____/____/____]"],
        ["3. Type of Evidence", "[  ] Medical records  [  ] Imaging/labs\n[  ] Therapy notes  [  ] Other: ________"],
        ["4. Relevance to Disability\n(SSR 17-4p categories)", "[  ] Medical condition  [  ] Work activity\n[  ] Job history  [  ] Medical treatment\n[  ] Other disability issue: __________"],
        ["5. Status Statement", "Records requested on [____/____/____].\nNot yet received as of this letter date."],
    ]

    t = Table(elements_data, colWidths=[2.2*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEADING', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "(Duplicate the table above for each additional provider with outstanding records.)",
        styles['SmallText']
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "I respectfully request that the hearing office note this INFORM submission "
        "in the record and address the identified evidence per HALLEX I-2-5-13 procedures, "
        "regardless of whether the actual records arrive before the hearing date.",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Sincerely,", styles['BodyText2']))
    story.append(Paragraph("[Your Signature]", styles['FieldLine']))
    story.append(Paragraph("[Your Printed Name]", styles['FieldLine']))
    story.append(Paragraph("[Date: ____/____/________]", styles['FieldLine']))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 1 of 9 · "
        "Not legal advice. For case-specific guidance, consult a disability attorney.",
        styles['Footer']
    ))

    # ==========================================
    # PAGE 2-6: PROCEDURAL EXPLAINER
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("PROCEDURAL EXPLAINER", styles['KitTitle']))
    story.append(Paragraph("Understanding the INFORM vs. SUBMIT Distinction Under the 5-Day Rule", styles['KitSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))

    story.append(Paragraph("What Is the 5-Day Rule?", styles['SectionTitle']))
    story.append(Paragraph(
        "Under <b>20 CFR § 404.935(a)</b>, you must either submit evidence or inform the "
        "hearing office about evidence no later than <b>5 business days before the hearing date</b>. "
        "This rule was implemented in 2017 to prevent hearing-day document dumps that delay decisions.",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        "Most claimants and even some attorneys only focus on submitting evidence before the deadline. "
        "But the regulation provides a critical second path: <b>informing</b>.",
        styles['BodyText2']
    ))

    story.append(Paragraph("The INFORM vs. SUBMIT Asymmetry", styles['SectionTitle']))
    story.append(Paragraph(
        "The 5-day rule creates two distinct obligations — only one of which requires "
        "you to actually have the documents in hand:",
        styles['BodyText2']
    ))

    compare_data = [
        ["", "SUBMIT", "INFORM"],
        ["What it means", "Send the actual evidence documents to the hearing office", "Notify the hearing office that specific evidence exists and has been requested"],
        ["What you need", "The actual records in hand", "Knowledge of what records exist and where they are"],
        ["When to use", "You have the records and can send them before the deadline", "Records are in transit, delayed by provider, or requested but not received"],
        ["ALJ obligation", "Must consider the evidence", "Under HALLEX I-2-5-13, must address the identified evidence in the decision"],
        ["Legal basis", "20 CFR § 404.935(a) — \"submit\"", "20 CFR § 404.935(a) — \"inform\""],
    ]

    t2 = Table(compare_data, colWidths=[1.5*inch, 2.7*inch, 2.7*inch])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('LEADING', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)

    story.append(Paragraph("Why This Matters for Pro Se Claimants", styles['SectionTitle']))
    story.append(Paragraph(
        "If you are representing yourself (pro se), the INFORM path is critical because:",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        "• Medical providers routinely take 2–6 weeks to process records requests",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• You may not receive records before the 5-day deadline through no fault of your own",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• An ALJ can exclude evidence submitted after the deadline without a proper INFORM on file",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• A valid INFORM letter preserves your right to have the evidence considered even if it arrives late",
        styles['BulletBody']
    ))

    story.append(Paragraph(
        '"If the individual does not provide us with information specific enough to allow us '
        'to identify and request the evidence, we are unable to develop or obtain it." '
        '— 20 CFR § 404.935 implementation guidance',
        styles['Citation']
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 2 of 9",
        styles['Footer']
    ))

    # PAGE 3
    story.append(PageBreak())
    story.append(Paragraph("The 5 Specificity Elements", styles['SectionTitle']))
    story.append(Paragraph(
        "For your INFORM letter to be valid under 20 CFR § 404.935, it must contain "
        "information <b>specific enough</b> to allow the hearing office to identify and request "
        "the evidence. Based on the regulation and SSR 17-4p, these are the 5 elements your "
        "letter must address:",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 8))

    spec_data = [
        ["#", "Element", "What to Include", "Example"],
        ["1", "Provider Name\n& Address", "Full name of the doctor, hospital, clinic, or facility. Include street address, city, state, ZIP.", "Dr. Sarah Chen\n1234 Medical Pkwy\nAustin, TX 78701"],
        ["2", "Date Range\nof Treatment", "The period during which you received treatment or the dates the records cover.", "March 2024 – Present\n(ongoing treatment)"],
        ["3", "Type of\nEvidence", "Specify what kind: medical records, lab results, imaging (MRI, X-ray), therapy notes, psychological evaluations, etc.", "MRI imaging results\nand radiology reports"],
        ["4", "Relevance to\nDisability", "SSR 17-4p requires you to state how it relates to:\n• Medical condition\n• Work activity\n• Job history\n• Medical treatment\n• Other disability issue", "Documents ongoing\nlumbar radiculopathy\nthat prevents standing\n> 15 minutes (medical\ncondition + work activity)"],
        ["5", "Status\nStatement", "State that records have been requested but not yet received. Include the date you requested them.", "Requested via fax on\n04/15/2026. Provider\nconfirmed 2-3 week\nprocessing time."],
    ]

    t3 = Table(spec_data, colWidths=[0.3*inch, 1.2*inch, 2.5*inch, 2.5*inch])
    t3.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('LEADING', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Important:</b> If your letter is missing any of these elements, the ALJ is not "
        "obligated to treat it as a valid INFORM under the regulation. A vague statement like "
        "\"I have more medical records coming\" does NOT satisfy the specificity requirement.",
        styles['BodyText2']
    ))

    story.append(Paragraph("SSR 17-4p Relevance Categories Explained", styles['SectionTitle']))
    story.append(Paragraph(
        "Social Security Ruling 17-4p expands the \"relevance\" requirement from a generic "
        "free-text statement to 5 named categories. Your INFORM letter should identify which "
        "of these categories the evidence addresses:",
        styles['BodyText2']
    ))

    story.append(Paragraph(
        "<b>1. Medical condition</b> — Evidence documenting the severity, duration, or "
        "functional impact of your impairment(s).",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "<b>2. Work activity</b> — Evidence showing how your condition affects your ability "
        "to perform work-related activities (lifting, standing, concentrating, etc.).",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "<b>3. Job history</b> — Evidence related to your past relevant work and whether "
        "you can return to previous jobs.",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "<b>4. Medical treatment</b> — Evidence of treatment received, treatment response, "
        "medication effects, and ongoing care plans.",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "<b>5. Other issues relevant to disability/blindness</b> — Evidence related to "
        "daily activities, pain levels, side effects, or any other factor bearing on the "
        "disability determination.",
        styles['BulletBody']
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 3 of 9",
        styles['Footer']
    ))

    # PAGE 4
    story.append(PageBreak())
    story.append(Paragraph("HALLEX I-2-5-13: The ALJ's Duty After INFORM", styles['SectionTitle']))
    story.append(Paragraph(
        "HALLEX (Hearings, Appeals and Litigation Law Manual) I-2-5-13 establishes that when "
        "a claimant properly informs the hearing office about evidence before the deadline, "
        "the Administrative Law Judge has a procedural duty to:",
        styles['BodyText2']
    ))

    story.append(Paragraph("• Acknowledge receipt of the INFORM notification in the record", styles['BulletBody']))
    story.append(Paragraph("• Make reasonable efforts to obtain the identified evidence", styles['BulletBody']))
    story.append(Paragraph("• Address the evidence (or its absence) in the hearing decision", styles['BulletBody']))
    story.append(Paragraph("• Explain the weight given to the evidence if obtained, or explain why it could not be obtained", styles['BulletBody']))

    story.append(Paragraph(
        "This is what makes INFORM powerful: it shifts procedural burden to the hearing office. "
        "Without an INFORM on file, the ALJ can simply exclude late evidence. "
        "With a valid INFORM, the ALJ must address it.",
        styles['BodyText2']
    ))

    story.append(Paragraph("HALLEX I-2-6-58: Evidence Received After the 5-Day Deadline", styles['SectionTitle']))
    story.append(Paragraph(
        "Even with a valid INFORM letter on file, evidence may arrive after the hearing. "
        "HALLEX I-2-6-58 provides guidance on how late-arriving evidence is handled:",
        styles['BodyText2']
    ))
    story.append(Paragraph("• If the evidence arrives before the decision is issued, the ALJ generally must consider it", styles['BulletBody']))
    story.append(Paragraph("• If the evidence arrives after the decision, it may be grounds for Appeals Council review", styles['BulletBody']))
    story.append(Paragraph("• A valid INFORM letter strengthens the argument that late evidence should be considered", styles['BulletBody']))

    story.append(Paragraph("When to Use the INFORM Letter", styles['SectionTitle']))
    story.append(Paragraph("<b>USE the INFORM letter when:</b>", styles['BodyText2']))
    story.append(Paragraph("• You've requested records from a provider and they haven't arrived yet", styles['BulletBody']))
    story.append(Paragraph("• Your hearing is approaching and the 5-day deadline is imminent", styles['BulletBody']))
    story.append(Paragraph("• A provider has confirmed records exist but needs processing time", styles['BulletBody']))
    story.append(Paragraph("• You have multiple providers with outstanding records", styles['BulletBody']))

    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>DO NOT use the INFORM letter when:</b>", styles['BodyText2']))
    story.append(Paragraph("• You already have the records in hand (submit them directly instead)", styles['BulletBody']))
    story.append(Paragraph("• You're speculating about evidence that might exist somewhere", styles['BulletBody']))
    story.append(Paragraph("• You haven't actually requested the records from the provider", styles['BulletBody']))
    story.append(Paragraph("• You're trying to delay the hearing (the INFORM doesn't postpone hearings)", styles['BulletBody']))

    story.append(Paragraph("How to Deliver the INFORM Letter", styles['SectionTitle']))
    story.append(Paragraph("<b>Fax (preferred)</b> — Provides date/time stamp proof of delivery. Keep the fax confirmation page.", styles['BulletBody']))
    story.append(Paragraph("<b>Certified mail</b> — Provides tracking and delivery confirmation. Allow 3-5 days for delivery.", styles['BulletBody']))
    story.append(Paragraph("<b>Electronic filing (ERE)</b> — If available in your jurisdiction, upload through your my Social Security account.", styles['BulletBody']))
    story.append(Paragraph(
        "<b>Important:</b> Count the 5-business-day deadline from the hearing date, NOT from "
        "the date you send the letter. If your hearing is on a Monday, the deadline is the "
        "prior Monday (skipping weekends and federal holidays).",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 4 of 9",
        styles['Footer']
    ))

    # PAGE 5
    story.append(PageBreak())
    story.append(Paragraph("SSDI Appeal Timeline", styles['SectionTitle']))
    story.append(Paragraph(
        "Understanding where the 5-day rule fits in the broader SSDI appeals process:",
        styles['BodyText2']
    ))

    timeline_data = [
        ["Stage", "What Happens", "Timeline"],
        ["1. Initial Application", "Apply for SSDI benefits", "3–6 months for decision"],
        ["2. Reconsideration", "Request review of denial", "3–5 months"],
        ["3. ALJ Hearing\n(5-DAY RULE APPLIES HERE)", "Hearing before Administrative\nLaw Judge. This is where your\nINFORM letter is relevant.", "12–18 months wait.\n5 business days before\nhearing = evidence deadline"],
        ["4. Appeals Council", "Review of ALJ decision", "6–12+ months"],
        ["5. Federal Court", "File in U.S. District Court", "Varies"],
    ]

    t4 = Table(timeline_data, colWidths=[2*inch, 2.7*inch, 2*inch])
    t4.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEADING', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('BACKGROUND', (0, 3), (-1, 3), HexColor("#e8f5e8")),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t4)

    story.append(Paragraph("Good Faith Exception (20 CFR § 404.935(b))", styles['SectionTitle']))
    story.append(Paragraph(
        "The regulation includes a \"good cause\" exception for evidence submitted after the "
        "5-day deadline. The ALJ may accept late evidence if:",
        styles['BodyText2']
    ))
    story.append(Paragraph("• The claimant was misled by SSA action", styles['BulletBody']))
    story.append(Paragraph("• The claimant had a physical, mental, educational, or linguistic limitation", styles['BulletBody']))
    story.append(Paragraph("• Some other unusual, unexpected, or unavoidable circumstance prevented timely submission", styles['BulletBody']))

    story.append(Paragraph(
        "<b>The INFORM letter is stronger than relying on good cause.</b> Good cause is "
        "discretionary — the ALJ decides whether to accept the excuse. An INFORM letter "
        "creates a procedural obligation. Use the INFORM letter as your primary strategy; "
        "good cause is a backup argument.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Statistics: Why This Matters", styles['SectionTitle']))
    story.append(Paragraph(
        "• Approximately <b>2 in 3 initial SSDI applications are denied</b>",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• The ALJ hearing is where most successful claimants win their benefits",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• Evidence quality at the hearing stage is the single biggest factor in outcomes",
        styles['BulletBody']
    ))
    story.append(Paragraph(
        "• Pro se claimants (without attorneys) win at roughly half the rate of represented claimants — "
        "often because they don't know procedural tools like the INFORM path",
        styles['BulletBody']
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 5 of 9",
        styles['Footer']
    ))

    # PAGE 6
    story.append(PageBreak())
    story.append(Paragraph("Frequently Asked Questions", styles['SectionTitle']))

    faqs = [
        ("Does INFORM apply to SSI (Title XVI) claims too?",
         "Yes. The 5-day evidence rule applies to both SSDI (Title II) and SSI (Title XVI) "
         "claims that proceed to an ALJ hearing. The regulation covers all hearings under "
         "20 CFR § 404.935 and its parallel at 20 CFR § 416.1435."),
        ("Can the ALJ refuse to consider my INFORM letter?",
         "If your INFORM letter meets the specificity requirements, the ALJ cannot simply "
         "ignore it. Under HALLEX I-2-5-13, there is a procedural duty to address properly "
         "identified evidence. However, if your letter is too vague (missing one of the 5 elements), "
         "the ALJ may determine it does not qualify as a valid INFORM."),
        ("What if my records never arrive?",
         "Your INFORM letter still serves a purpose. The ALJ must address the identified evidence "
         "in the decision — either by noting efforts to obtain it or explaining why its absence "
         "doesn't change the outcome. This creates a record for potential Appeals Council review."),
        ("Can I send multiple INFORM letters for different providers?",
         "Yes. If you have records outstanding from multiple providers, you can send one letter "
         "listing all providers (using the table on page 1 duplicated for each), or separate "
         "letters for each provider. One consolidated letter is generally cleaner."),
        ("Does the INFORM letter delay or postpone my hearing?",
         "No. The INFORM letter does not postpone your hearing date. Your hearing will proceed "
         "as scheduled. The INFORM creates a procedural record that the evidence was identified "
         "before the deadline, regardless of when it actually arrives."),
    ]

    for q, a in faqs:
        story.append(Paragraph(f"<b>Q: {q}</b>", styles['BodyText2']))
        story.append(Paragraph(f"A: {a}", styles['BodyText2']))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 6 of 9",
        styles['Footer']
    ))

    # ==========================================
    # PAGE 7: DEADLINE CALENDAR WORKSHEET
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("60-DAY DEADLINE CALENDAR WORKSHEET", styles['KitTitle']))
    story.append(Paragraph("Calculate your INFORM deadline and track evidence status", styles['KitSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))

    story.append(Paragraph("Step 1: Calculate Your Deadline", styles['SectionTitle']))

    calc_data = [
        ["Field", "Your Information"],
        ["Hearing Date:", "[____/____/________]  (Day of week: __________)"],
        ["Minus 5 business days:", "Count backwards, skip weekends + federal holidays"],
        ["Your INFORM Deadline:", "[____/____/________]  ← SEND LETTER BY THIS DATE"],
        ["Minus 3 days (mail buffer):", "[____/____/________]  ← MAIL BY THIS DATE if using postal"],
    ]

    t5 = Table(calc_data, colWidths=[2.2*inch, 4.8*inch])
    t5.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('LEADING', (0, 0), (-1, -1), 14),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t5)

    story.append(Paragraph("Step 2: Track Your Records Requests", styles['SectionTitle']))
    story.append(Paragraph(
        "Use this table to track when you requested records and when they arrive. "
        "If records are still outstanding when the deadline approaches, use the INFORM letter.",
        styles['BodyText2']
    ))

    track_data = [
        ["Provider", "Requested\nDate", "Expected\nReturn", "Received?", "INFORM\nSent?"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
        ["", "", "", "[  ] Yes [  ] No", "[  ] Yes [  ] No"],
    ]

    t6 = Table(track_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.3*inch, 1.3*inch])
    t6.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEADING', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t6)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Step 3: INFORM Letter Delivery Confirmation", styles['SectionTitle']))

    delivery_data = [
        ["Delivery Method", "Date Sent", "Confirmation #"],
        ["[  ] Fax", "", "Fax confirmation page: [  ] Saved"],
        ["[  ] Certified Mail", "", "Tracking #: ____________________"],
        ["[  ] ERE Upload", "", "Confirmation screen: [  ] Saved"],
    ]

    t7 = Table(delivery_data, colWidths=[2*inch, 1.8*inch, 3*inch])
    t7.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('LEADING', (0, 0), (-1, -1), 13),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t7)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 7 of 9",
        styles['Footer']
    ))

    # ==========================================
    # PAGE 8: PROVIDER TRACKING TABLE
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("PROVIDER TRACKING TABLE", styles['KitTitle']))
    story.append(Paragraph("Track records requested, received, and INFORM letters sent per provider", styles['KitSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))

    story.append(Paragraph(
        "Use one row per provider. Duplicate this page if you have more than 5 providers.",
        styles['BodyText2']
    ))

    for i in range(1, 6):
        story.append(Paragraph(f"Provider #{i}", styles['SubsectionTitle']))
        prov_data = [
            ["Provider Name:", ""],
            ["Address:", ""],
            ["Phone / Fax:", ""],
            ["Records Requested (date):", ""],
            ["Records Cover (date range):", ""],
            ["Type of Evidence:", "[  ] Medical records  [  ] Labs  [  ] Imaging  [  ] Therapy  [  ] Other: ____"],
            ["SSR 17-4p Relevance:", "[  ] Medical condition  [  ] Work activity  [  ] Job history\n[  ] Medical treatment  [  ] Other: ____"],
            ["Records Received?", "[  ] Yes (date: __/__/____)  [  ] No — INFORM letter needed"],
            ["INFORM Sent?", "[  ] Yes (date: __/__/____)  [  ] No"],
        ]

        tp = Table(prov_data, colWidths=[2.2*inch, 4.8*inch])
        tp.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('LEADING', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), GRAY),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(tp)
        story.append(Spacer(1, 8))

    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 8 of 9",
        styles['Footer']
    ))

    # ==========================================
    # PAGE 9: LEGAL RESOURCES
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("LEGAL RESOURCES", styles['KitTitle']))
    story.append(Paragraph("Official sources, organizations, and next steps", styles['KitSubtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))

    story.append(Paragraph("Official Federal Sources", styles['SectionTitle']))
    story.append(Paragraph("• <b>20 CFR § 404.935</b> — Evidence at a hearing before an ALJ (Cornell LII: law.cornell.edu/cfr/text/20/404.935)", styles['BulletBody']))
    story.append(Paragraph("• <b>20 CFR § 416.1435</b> — Parallel regulation for SSI claims", styles['BulletBody']))
    story.append(Paragraph("• <b>HALLEX I-2-5-13</b> — Duties regarding evidence identified before hearing (ssa.gov/OP_Home/hallex/)", styles['BulletBody']))
    story.append(Paragraph("• <b>HALLEX I-2-6-58</b> — Evidence received after hearing (ssa.gov/OP_Home/hallex/)", styles['BulletBody']))
    story.append(Paragraph("• <b>SSR 17-4p</b> — Responsibility for Developing Written Evidence (federalregister.gov)", styles['BulletBody']))

    story.append(Paragraph("Disability Rights Organizations", styles['SectionTitle']))
    story.append(Paragraph("• <b>National Organization of Social Security Claimants' Representatives (NOSSCR)</b> — nosscr.org — Attorney referral directory", styles['BulletBody']))
    story.append(Paragraph("• <b>Disability Rights (your state)</b> — ndrn.org/about/ndrn-member-agencies/ — Free advocacy in every state", styles['BulletBody']))
    story.append(Paragraph("• <b>Legal Aid (your area)</b> — lawhelp.org — Free legal services for eligible individuals", styles['BulletBody']))
    story.append(Paragraph("• <b>Empire Justice Center</b> — empirejustice.org — SSR 17-4p analysis and practice guidance", styles['BulletBody']))

    story.append(Paragraph("Finding a Contingency-Fee Disability Attorney", styles['SectionTitle']))
    story.append(Paragraph(
        "Most SSDI attorneys work on contingency — they only get paid if you win. "
        "The fee is capped by law at 25% of back pay or $7,200 (whichever is less, as of 2026). "
        "This means there is no upfront cost to you.",
        styles['BodyText2']
    ))
    story.append(Paragraph("• NOSSCR attorney directory: nosscr.org", styles['BulletBody']))
    story.append(Paragraph("• American Bar Association lawyer referral: americanbar.org/groups/legal_services/", styles['BulletBody']))
    story.append(Paragraph("• Your local bar association's referral service", styles['BulletBody']))

    story.append(Paragraph("Important Disclaimers", styles['SectionTitle']))
    story.append(Paragraph(
        "This kit aggregates publicly available federal regulations and SSA procedural "
        "guidance into a structured, actionable format. It is provided for educational and "
        "informational purposes only.",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        "<b>This is not legal advice.</b> This kit does not create an attorney-client relationship. "
        "For case-specific guidance, consult a qualified disability attorney or your state's "
        "Disability Rights organization.",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        "Regulations and procedures may change. This kit is current as of May 2026. "
        "Always verify current regulations at ssa.gov or law.cornell.edu before relying "
        "on any specific citation.",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=12))
    story.append(Paragraph(
        "OEFR Digital · SSDI 5-Day INFORM Letter Kit v1.0 · Page 9 of 9",
        styles['Footer']
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Questions or feedback? Email info@oefrenterprise.com",
        styles['Footer']
    ))
    story.append(Paragraph(
        "© 2026 OEFR Digital. All rights reserved. oefrenterprise.com",
        styles['Footer']
    ))

    doc.build(story)
    print(f"PDF generated: {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH):,} bytes")


if __name__ == "__main__":
    build_pdf()
