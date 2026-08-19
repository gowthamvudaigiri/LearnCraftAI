from __future__ import annotations
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.models import *

ENV=Environment(loader=FileSystemLoader(Path(__file__).parents[1]/"templates"),autoescape=True)

def _safe_json(value) -> str:
    return json.dumps(value,ensure_ascii=False).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")

def render_lesson_html(lesson: LessonPlan, document_id: str) -> bytes:
    return ENV.get_template("lesson.html.j2").render(lesson=lesson,document_id=document_id).encode()

def render_quiz_html(bp: QuizBlueprint, questions: list[Question], document_id: str) -> bytes:
    public=[q.model_dump(mode="json") for q in questions]
    return ENV.get_template("quiz.html.j2").render(blueprint=bp,questions=questions,question_json=_safe_json(public),document_id=document_id).encode()
