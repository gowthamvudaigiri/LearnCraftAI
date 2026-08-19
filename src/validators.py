import re
from src.models import *

def normalize_answer(value: str) -> str:
    return re.sub(r"[\s,.-]+", "", str(value).casefold())

def validate_content(req: GenerationRequest, analysis: SourceAnalysis, bp: QuizBlueprint, questions: list[Question]) -> ValidationReport:
    issues=[]
    if not analysis.concepts: issues.append(ValidationIssue(severity="error",message="No concepts approved."))
    if len(questions)!=req.question_count: issues.append(ValidationIssue(severity="error",message="Question total mismatch."))
    if sum(q.marks for q in questions)!=req.total_marks: issues.append(ValidationIssue(severity="error",message="Marks total mismatch."))
    prompts=[normalize_answer(q.prompt) for q in questions]
    duplicate_ids=[questions[i].question_id for i,p in enumerate(prompts) if p in prompts[:i]]
    if duplicate_ids: issues.append(ValidationIssue(severity="error",message=f"Duplicate questions found: {', '.join(duplicate_ids)}."))
    for q in questions:
        if not q.objective_ids: issues.append(ValidationIssue(severity="error",message="Question has no objective.",object_id=q.question_id))
        if q.question_type==QuestionType.MCQ and (len(set(q.options))<4 or q.options.count(q.canonical_answer)!=1): issues.append(ValidationIssue(severity="error",message="Invalid MCQ options.",object_id=q.question_id))
        operation=q.verification.operation
        operands=q.verification.operands
        if operation in {"addition","subtraction"} and len(operands)==2:
            computed=operands[0]+operands[1] if operation=="addition" else operands[0]-operands[1]
            if q.canonical_answer != str(computed) or q.verification.computed_answer != computed:
                issues.append(ValidationIssue(severity="error",message="Arithmetic answer does not match its operands.",object_id=q.question_id))
    return ValidationReport(passed=not issues,issues=issues,model_metadata={"provider":"deterministic-local"})
