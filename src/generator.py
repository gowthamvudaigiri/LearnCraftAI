from __future__ import annotations
import random, re
from src.models import *

REFERENCE_COUNTS = [3,4,4,4,3,4,3]

def _unique_prompt(prompt: str, used_prompts: set[str], item_number: int) -> str:
    """Keep generated papers valid even when random operands or manual tasks repeat."""
    candidate = prompt
    variation = 2
    while candidate.casefold().strip() in used_prompts:
        candidate = f"{prompt} (Practice variation {variation})"
        variation += 1
    used_prompts.add(candidate.casefold().strip())
    return candidate

def _operation_for_concept(concept: str, item_index: int) -> str:
    words = concept.casefold()
    has_addition = any(word in words for word in ("addition", "add", "plus", "sum"))
    has_subtraction = any(word in words for word in ("subtraction", "subtract", "minus", "difference"))
    if has_addition and has_subtraction:
        return "addition" if item_index % 2 == 0 else "subtraction"
    if has_subtraction:
        return "subtraction"
    return "addition"

def _numeric_options(answer: int, likely_errors: list[int], rng: random.Random) -> list[str]:
    candidates = [answer, *likely_errors, answer + 1, answer - 1, answer + 10, max(0, answer - 10)]
    unique = []
    for value in candidates:
        text = str(value)
        if text not in unique:
            unique.append(text)
        if len(unique) == 4:
            break
    while len(unique) < 4:
        value = str(answer + len(unique) + 2)
        if value not in unique:
            unique.append(value)
    rng.shuffle(unique)
    return unique

def _math_question(concept: str, item_index: int, grade: int, qtype: QuestionType, rng: random.Random):
    operation = _operation_for_concept(concept, item_index)
    limit = 20 if grade <= 2 else 100 if grade <= 4 else 1000
    if operation == "subtraction":
        left = rng.randint(1, limit)
        right = rng.randint(0, left)
        answer = left - right
        symbol = "-"
        likely_errors = [left + right, right, left]
        explanation = f"Start with {left} and take away {right}. The difference is {answer}."
    else:
        left = rng.randint(0, limit)
        right = rng.randint(0, limit)
        if left == right == 0:
            right = 1
        answer = left + right
        symbol = "+"
        likely_errors = [abs(left - right), left, right]
        explanation = f"Combine {left} and {right}. Their sum is {answer}."
    prompt = f"Use {operation} to solve: {left} {symbol} {right} = ?"
    options = _numeric_options(answer, likely_errors, rng) if qtype == QuestionType.MCQ else []
    verification = {"eligible": True, "operation": operation, "operands": [left, right], "computed_answer": answer}
    return prompt, str(answer), options, explanation, verification

def analyze(request: GenerationRequest, sources: list[dict] | None = None) -> SourceAnalysis:
    source_text = " ".join(s.get("text", "") for s in (sources or []))
    concepts = request.concepts or [x.strip() for x in re.split(r"[,;\n]", source_text[:1000]) if 2 < len(x.strip()) < 80][:8]
    if not concepts: concepts = ["Core ideas from the uploaded material"]
    objectives = request.learning_goals or [f"Explain and apply {c}." for c in concepts]
    patterns = build_sections(request, concepts)
    evidence = [SourceEvidence(source_id=s["source_id"], filename=s["filename"], short_excerpt=s.get("text", "")[:180], confidence=.85) for s in (sources or []) if s.get("text")]
    return SourceAnalysis(detected_title=f"Grade {request.grade_level} {request.subject}", detected_subject=request.subject, detected_grade=request.grade_level, detected_curriculum=request.curriculum, concepts=concepts, learning_objectives=objectives, prerequisites=["Recall earlier related ideas"], vocabulary=concepts[:8], common_misconceptions=["Rushing without checking each step"], worked_example_patterns=["Explain, model, then try"], question_patterns=patterns, evidence=evidence, ambiguities=[] if source_text or request.concepts else ["No readable source text"], overall_confidence=.95 if request.concepts else .65)

def build_sections(req: GenerationRequest, concepts: list[str]) -> list[SectionPattern]:
    counts = [req.question_count // len(concepts)] * len(concepts)
    for i in range(req.question_count % len(concepts)): counts[i] += 1
    marks = [req.total_marks // len(concepts)] * len(concepts)
    for i in range(req.total_marks % len(concepts)): marks[i] += 1
    return [SectionPattern(section_id=f"S{i+1}", title=c.title(), concepts_covered=[c], permitted_question_types=req.preferred_question_types, question_count=max(1, counts[i]), section_marks=max(1, marks[i]), difficulty=req.difficulty) for i,c in enumerate(concepts) if counts[i]]

def lesson_for(req: GenerationRequest, analysis: SourceAnalysis) -> LessonPlan:
    sections=[]
    for i,c in enumerate(analysis.concepts):
        obj=analysis.learning_objectives[min(i,len(analysis.learning_objectives)-1)]
        sections.append(LessonSection(title=c.title(), objective=obj, explanation=f"{c.title()} becomes easier when we look for the important parts and take one small step at a time.", worked_examples=[f"Example: identify what the {c} question gives you, choose a rule, and check the result."], visual=f"Make a small table or drawing to show {c}.", common_mistake="A common mistake is answering before checking what the question asks.", guided_practice=f"Try one simple {c} example and explain your first step.", quick_check=f"In one sentence, what is the key idea in {c}?", hint="Use the rule and example above.", answer=f"A correct response clearly explains the main rule for {c}."))
    return LessonPlan(title=f"Grade {req.grade_level} {req.subject} Concept Lesson", sections=sections)

def questions_for(req: GenerationRequest, analysis: SourceAnalysis) -> tuple[QuizBlueprint,list[Question]]:
    rng=random.Random(req.random_seed); questions=[]; qno=1; used_prompts=set()
    for si,section in enumerate(analysis.question_patterns):
        base, extra = divmod(section.section_marks, section.question_count)
        for j in range(section.question_count):
            marks=base+(1 if j<extra else 0); concept=section.concepts_covered[0]
            qtype=section.permitted_question_types[j % len(section.permitted_question_types)]
            n=rng.randint(10,99); verification={"eligible":True}; explanation=f"This checks the main idea of {concept}."
            if req.subject.lower()=="mathematics":
                prompt,answer,options,explanation,verification=_math_question(concept,j,req.grade_level,qtype,rng)
            else:
                prompt=f"Which statement best shows your understanding of {concept}?"
                answer=f"A clear, accurate explanation of {concept}"
                options=[answer,f"An unrelated fact about {n}","Skip the evidence","Guess without checking"] if qtype==QuestionType.MCQ else []
            manual=qtype in {QuestionType.DRAWING,QuestionType.LONG,QuestionType.SHORT}
            if qtype==QuestionType.DRAWING:
                drawing_stems = [
                    "Draw and label an example that demonstrates",
                    "Create a different picture or diagram that shows",
                    "Sketch an example and mark the important parts of",
                    "Use shapes, symbols, or labels to represent",
                ]
                prompt=f"{drawing_stems[j % len(drawing_stems)]} {concept}."; answer="Parent/Teacher Review"; verification={"eligible":False}; explanation=f"A parent or teacher checks whether the drawing accurately shows {concept}."
            prompt=_unique_prompt(prompt,used_prompts,qno)
            verification["eligible"] = not manual
            questions.append(Question(question_id=f"Q{qno}",section_id=section.section_id,objective_ids=[f"O{si+1}"],question_type=qtype,prompt=prompt,options=options,canonical_answer=answer,marks=marks,difficulty=req.difficulty,hint="Read the question and show one step.",explanation=explanation,manual_review_required=manual,verification=verification))
            qno+=1
    bp=QuizBlueprint(title=f"Grade {req.grade_level} {req.subject} Practice Paper",instructions="Answer every question. Drawing and longer responses are checked by a parent or teacher.",grade=req.grade_level,subject=req.subject,duration_minutes=req.duration_minutes,total_marks=req.total_marks,sections=analysis.question_patterns,objective_coverage=[ObjectiveCoverage(objective_id=f"O{i+1}",section_ids=[s.section_id]) for i,s in enumerate(analysis.question_patterns)],random_seed=req.random_seed)
    return bp,questions
