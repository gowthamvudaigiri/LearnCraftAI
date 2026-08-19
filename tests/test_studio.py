from uuid import uuid4
import io,zipfile,json
import fitz
import pytest
from src.models import *
from src.generator import analyze,lesson_for,questions_for
from src.validators import normalize_answer,validate_content
from src.renderers import *
from src.parsers import validate_uploads,extract_file

@pytest.fixture
def generation_request():
    return GenerationRequest(concepts=["place value and face value","draw the lines","numbers and number names","identification of shapes","expanded and standard form","odd one out","even and odd numbers"],question_count=25,total_marks=25,preferred_question_types=[QuestionType.MCQ,QuestionType.NUMERIC,QuestionType.DRAWING],random_seed=42)

def test_models_reject_empty_concepts():
    with pytest.raises(ValueError): GenerationRequest(concepts=[])

def test_reference_blueprint_and_seed(generation_request):
    an=analyze(generation_request);bp,q1=questions_for(generation_request,an);_,q2=questions_for(generation_request,an)
    assert len(q1)==25 and sum(q.marks for q in q1)==25
    assert [q.model_dump() for q in q1]==[q.model_dump() for q in q2]
    assert validate_content(generation_request,an,bp,q1).passed

def test_normalization(): assert normalize_answer(" Forty-two. ")==normalize_answer("forty two")

def test_html_is_self_contained_and_escaped(generation_request):
    an=analyze(generation_request);lesson=lesson_for(generation_request,an);bp,qs=questions_for(generation_request,an)
    lesson.sections[0].explanation="<script>alert(1)</script>"
    html=render_lesson_html(lesson,"abc").decode(); quiz=render_quiz_html(bp,qs,"abc").decode()
    assert "&lt;script&gt;" in html and "https://" not in html and "@media print" in quiz
    assert "canonical_answer" in quiz and "window.print" in quiz

def test_visual_aids_render_in_lesson_quiz_and_pdf(generation_request):
    an=analyze(generation_request);lesson=lesson_for(generation_request,an);bp,qs=questions_for(generation_request,an)
    lesson.sections[0].visual="0 -- 1 -- 2 -- 3"
    qs[0].visual="[o] [o] + [o] = ?"
    lesson_html=render_lesson_html(lesson,"abc").decode();quiz_html=render_quiz_html(bp,qs,"abc").decode()
    assert "Visual aid" in lesson_html and "0 -- 1 -- 2 -- 3" in lesson_html
    assert "Use this visual" in quiz_html and "[o] [o] + [o] = ?" in quiz_html
    student,_=render_quiz_pdfs(bp,qs,"abc")
    student_text="".join(p.get_text() for p in fitz.open(stream=student,filetype="pdf"))
    assert "Visual:" in student_text

def test_seed_is_not_exposed_in_pdf_footer(generation_request):
    an=analyze(generation_request);bp,qs=questions_for(generation_request,an)
    student,_=render_quiz_pdfs(bp,qs,"abc")
    text="".join(p.get_text() for p in fitz.open(stream=student,filetype="pdf"))
    assert "seed" not in text.casefold()

def test_pdf_answer_separation(generation_request):
    an=analyze(generation_request);bp,qs=questions_for(generation_request,an);student,key=render_quiz_pdfs(bp,qs,"abc")
    assert student.startswith(b"%PDF") and key.startswith(b"%PDF")
    student_text="".join(p.get_text() for p in fitz.open(stream=student,filetype="pdf"))
    key_text="".join(p.get_text() for p in fitz.open(stream=key,filetype="pdf"))
    assert "Answer:" not in student_text and "Answer:" in key_text and "Q25" in key_text

def test_zip_manifest(generation_request):
    blob=package_artifacts({"lesson.html":b"ok"},{"seed":42})
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert z.read("lesson.html")==b"ok" and json.loads(z.read("manifest.json"))["seed"]==42

def test_file_validation_and_extraction():
    with pytest.raises(ValueError): validate_uploads([("bad.exe",b"x")])
    result=extract_file("notes.txt",b"fractions and halves")
    assert "fractions" in result["text"] and result["status"]=="read"

def test_scanned_pdf_is_prepared_for_model_vision():
    doc=fitz.open();doc.new_page()
    pdf=doc.tobytes();doc.close()
    result=extract_file("scan.pdf",pdf)
    assert result["text"]==""
    assert result["status"]=="vision ready"
    assert result["mime_type"]=="application/pdf"
    assert result["analysis_data"].startswith(b"%PDF")

def test_source_analysis_rejects_empty_concepts(generation_request):
    analysis=analyze(generation_request)
    payload=analysis.model_dump()
    payload["concepts"]=[]
    with pytest.raises(ValueError): SourceAnalysis.model_validate(payload)

def test_provider_builds_pdf_file_input_block():
    from src.providers.openai_provider import _source_content_blocks
    blocks=_source_content_blocks([{
        "filename":"scan.pdf",
        "mime_type":"application/pdf",
        "analysis_data":b"%PDF-test",
    }])
    assert blocks==[{
        "type":"file",
        "source_type":"base64",
        "mime_type":"application/pdf",
        "data":"JVBERi10ZXN0",
        "filename":"scan.pdf",
    }]

def test_graph_compiles():
    from src.graph import build_graph
    assert build_graph() is not None

def test_repeated_manual_questions_receive_unique_prompts():
    req=GenerationRequest(
        concepts=["lines and shapes"],
        question_count=25,
        total_marks=25,
        preferred_question_types=[QuestionType.DRAWING],
        random_seed=2025,
    )
    an=analyze(req);bp,questions=questions_for(req,an)
    assert len({normalize_answer(q.prompt) for q in questions})==25
    assert validate_content(req,an,bp,questions).passed

def test_addition_and_subtraction_use_correct_operations():
    req=GenerationRequest(
        concepts=["Addition", "Subtraction"],
        question_count=20,
        total_marks=20,
        preferred_question_types=[QuestionType.MCQ],
        random_seed=2025,
    )
    an=analyze(req);bp,questions=questions_for(req,an)
    addition=[q for q in questions if q.section_id=="S1"]
    subtraction=[q for q in questions if q.section_id=="S2"]
    assert all(" + " in q.prompt and q.verification.operation=="addition" for q in addition)
    assert all(" - " in q.prompt and " + " not in q.prompt and q.verification.operation=="subtraction" for q in subtraction)
    assert all(int(q.canonical_answer)==q.verification.operands[0]-q.verification.operands[1] for q in subtraction)
    assert validate_content(req,an,bp,questions).passed

def test_combined_addition_and_subtraction_alternates():
    req=GenerationRequest(concepts=["Addition and subtraction"],question_count=6,total_marks=6,preferred_question_types=[QuestionType.NUMERIC])
    an=analyze(req);bp,questions=questions_for(req,an)
    assert [q.verification.operation for q in questions]==["addition","subtraction"]*3
    questions[1].canonical_answer="999"
    report=validate_content(req,an,bp,questions)
    assert not report.passed and report.issues[-1].object_id=="Q2"

def test_byok_provider_uses_structured_contracts():
    from src.providers.openai_provider import OpenAIContentProvider

    req=GenerationRequest(concepts=["Addition"],question_count=1,total_marks=1,preferred_question_types=[QuestionType.MCQ])
    analysis=analyze(req);lesson=lesson_for(req,analysis);blueprint,questions=questions_for(req,analysis)
    fixtures={SourceAnalysis:analysis,LessonPlan:lesson,GeneratedQuiz:GeneratedQuiz(blueprint=blueprint,questions=questions)}

    class FakeRunnable:
        def __init__(self,value): self.value=value
        def invoke(self,messages):
            assert messages[0][0]=="system" and messages[1][0]=="human"
            return self.value
    class FakeClient:
        def with_structured_output(self,schema,method):
            assert method=="json_schema"
            return FakeRunnable(fixtures[schema])

    provider=OpenAIContentProvider("sk-test","test-model",client=FakeClient())
    assert provider.analyze(req,[]).concepts==["Addition"]
    assert provider.generate_lesson(req,analysis).sections
    assert provider.generate_quiz(req,analysis).questions[0].question_id=="Q1"

def test_gpt_56_provider_uses_responses_without_reasoning_tools():
    from src.providers.openai_provider import OpenAIContentProvider
    provider=OpenAIContentProvider("sk-test","gpt-5.6-luna")
    assert provider.client.use_responses_api is True
    assert provider.client.reasoning=={"effort":"none"}
    assert provider.client.reasoning_effort is None

def test_generated_quiz_schema_closes_every_object():
    from openai.lib._pydantic import to_strict_json_schema

    def assert_closed(value):
        if isinstance(value,dict):
            if value.get("type")=="object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                assert_closed(child)
        elif isinstance(value,list):
            for child in value:
                assert_closed(child)

    assert_closed(GeneratedQuiz.model_json_schema())
    assert_closed(to_strict_json_schema(GeneratedQuiz))

def test_server_settings_and_admin_credentials():
    from src.settings import credentials_match,load_settings

    settings=load_settings({
        "OPENAI_API_KEY":"sk-server",
        "OPENAI_MODEL":"gpt-5.6-terra",
        "LEARNCRAFT_ADMIN_USER":"admin",
        "LEARNCRAFT_ADMIN_PASSWORD":"long-secret-password",
    })
    assert not settings.missing_required
    assert settings.openai_model=="gpt-5.6-terra"
    assert credentials_match("admin","long-secret-password",settings)
    assert not credentials_match("admin","wrong",settings)
    assert not credentials_match("wrong","long-secret-password",settings)

def test_server_settings_fail_closed_when_required_values_are_missing():
    from src.settings import load_settings

    settings=load_settings({})
    assert settings.openai_model=="gpt-5.6-luna"
    assert settings.missing_required==(
        "OPENAI_API_KEY",
        "LEARNCRAFT_ADMIN_USER",
        "LEARNCRAFT_ADMIN_PASSWORD",
    )

def test_server_settings_load_dotenv_without_overriding_environment(tmp_path,monkeypatch):
    from src.settings import load_settings

    env_file=tmp_path/".env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-from-file\n"
        "OPENAI_MODEL=gpt-5.6-luna\n"
        "LEARNCRAFT_ADMIN_USER=file-admin\n"
        "LEARNCRAFT_ADMIN_PASSWORD=file-password\n",
        encoding="utf-8",
    )
    for name in ("OPENAI_API_KEY","OPENAI_MODEL","LEARNCRAFT_ADMIN_USER","LEARNCRAFT_ADMIN_PASSWORD"):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv("LEARNCRAFT_ADMIN_USER","shell-admin")

    settings=load_settings(env_file=env_file)

    assert settings.openai_api_key=="sk-from-file"
    assert settings.admin_user_id=="shell-admin"
    assert settings.admin_password=="file-password"
