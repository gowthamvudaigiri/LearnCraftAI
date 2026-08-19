from __future__ import annotations
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak
from src.models import *

def _doc(title, generation_id):
    out=BytesIO(); styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name="StudioTitle",parent=styles["Title"],textColor=colors.HexColor("#5146B8"),alignment=TA_CENTER))
    def footer(canvas,doc): canvas.saveState(); canvas.setFont("Helvetica",8); canvas.drawString(36,20,f"Generation {generation_id}"); canvas.drawRightString(A4[0]-36,20,f"Page {doc.page}"); canvas.restoreState()
    return out, SimpleDocTemplate(out,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=34,title=title), styles, footer

def render_lesson_pdf(lesson: LessonPlan,generation_id:str,seed:int)->bytes:
    out,doc,s,footer=_doc(lesson.title,generation_id); story=[Paragraph(lesson.title,s["StudioTitle"]),Spacer(1,14)]
    for sec in lesson.sections:
        parts=[Paragraph(sec.title,s["Heading2"]),Paragraph(f"<b>What you will learn:</b> {sec.objective}",s["BodyText"]),Spacer(1,6),Paragraph(sec.explanation,s["BodyText"])]
        for e in sec.worked_examples: parts.append(Paragraph(f"<b>Worked example:</b> {e}",s["BodyText"]))
        if sec.visual: parts.append(Paragraph(f"<b>Visual aid:</b> {escape(sec.visual).replace(chr(10), '<br/>')}",s["BodyText"]))
        parts.extend([Paragraph(f"<b>Common mistake:</b> {sec.common_mistake}",s["BodyText"]),Paragraph(f"<b>Try it:</b> {sec.guided_practice}",s["BodyText"]),Spacer(1,28),Paragraph(f"<b>Quick check:</b> {sec.quick_check}",s["BodyText"]),Spacer(1,24)])
        story.append(KeepTogether(parts))
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return out.getvalue()

def render_quiz_pdfs(bp:QuizBlueprint,questions:list[Question],generation_id:str)->tuple[bytes,bytes]:
    def build(key:bool):
        out,doc,s,footer=_doc(bp.title+(" — Answer Key" if key else ""),generation_id); story=[Paragraph(bp.title+(" — Answer Key" if key else ""),s["StudioTitle"]),Paragraph(f"Grade {bp.grade} • {bp.subject} • {bp.duration_minutes} minutes • {bp.total_marks} marks",s["BodyText"]),Spacer(1,8)]
        if not key: story.extend([Paragraph("Name: ____________________  Date: __________  Class: __________",s["BodyText"]),Spacer(1,12)])
        for sec in bp.sections:
            story.append(Paragraph(f"{sec.title} — {sec.section_marks} marks",s["Heading2"]))
            for q in [x for x in questions if x.section_id==sec.section_id]:
                p=[Paragraph(f"<b>{q.question_id}.</b> {q.prompt} ({q.marks})",s["BodyText"])]
                if q.visual: p.append(Paragraph(f"<b>Visual:</b> {escape(q.visual).replace(chr(10), '<br/>')}",s["BodyText"]))
                if q.options: p.append(Paragraph(" &nbsp;&nbsp; ".join(f"{chr(65+i)}. {o}" for i,o in enumerate(q.options)),s["BodyText"]))
                if key: p.extend([Paragraph(f"<b>Answer:</b> {q.canonical_answer}",s["BodyText"]),Paragraph(f"<b>Explanation:</b> {q.explanation}"+(" <b>Parent/Teacher Review.</b>" if q.manual_review_required else ""),s["BodyText"])])
                else: p.append(Spacer(1,48 if q.manual_review_required else 22))
                story.append(KeepTogether(p)); story.append(Spacer(1,8))
        doc.build(story,onFirstPage=footer,onLaterPages=footer); return out.getvalue()
    return build(False),build(True)
