from __future__ import annotations
import random,re
import streamlit as st
from pydantic import ValidationError
from src.models import *
from src.parsers import validate_uploads,extract_file
from src.validators import validate_content
from src.renderers import *
from src.providers.openai_provider import OpenAIContentProvider,friendly_llm_error
from src.settings import credentials_match,load_settings

st.set_page_config(page_title="Kids Learning & Quiz Studio",page_icon="🌟",layout="wide")
SETTINGS=load_settings()
st.markdown("""
<style>
  :root{--ink:#172033;--muted:#677189;--line:#e3e7f0;--accent:#5b4cc4;--accent-soft:#f1efff}
  .stApp{background:linear-gradient(180deg,#f7f8fc 0,#fbfbfd 34rem)}
  [data-testid="stMainBlockContainer"]{width:100%;max-width:1180px;box-sizing:border-box;padding-top:1.6rem;padding-bottom:5rem}
  [data-testid="stSidebar"]{border-right:1px solid var(--line);background:#fff}
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.7rem}
  .app-header{display:flex;align-items:center;justify-content:space-between;gap:1.5rem;padding:1.35rem 1.5rem;border:1px solid var(--line);border-radius:20px;background:#fff;box-shadow:0 10px 30px rgba(39,46,78,.06);margin-bottom:1.35rem}
  .app-header>div{min-width:0;flex:1}
  .app-header h1{color:var(--ink);font-size:2rem;line-height:1.1;margin:.18rem 0 .35rem;letter-spacing:-.035em}
  .app-header p{color:var(--muted);margin:0;font-size:.98rem}
  .eyebrow{color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}
  .model-chip{white-space:nowrap;background:var(--accent-soft);color:#4c3eac;border-radius:999px;padding:.5rem .8rem;font-size:.8rem;font-weight:750}
  .section-heading{display:flex;align-items:center;gap:.75rem;margin:1.7rem 0 .7rem}
  .section-number{display:inline-grid;place-items:center;width:2rem;height:2rem;border-radius:10px;background:var(--accent);color:white;font-weight:800}
  .section-heading h2{font-size:1.15rem;color:var(--ink);margin:0}
  .section-heading p{font-size:.84rem;color:var(--muted);margin:.1rem 0 0}
  .sidebar-brand{padding:.25rem 0 .55rem}.sidebar-brand strong{font-size:1.15rem;color:var(--ink)}.sidebar-brand p{margin:.2rem 0 0;color:var(--muted);font-size:.82rem}
  .progress-step{display:flex;gap:.65rem;align-items:center;padding:.38rem .45rem;border-radius:10px;color:#7a8397;font-size:.86rem}
  .progress-step.active{background:var(--accent-soft);color:#493ba8;font-weight:750}
  .progress-step.done{color:#2c7a59}.progress-dot{display:inline-grid;place-items:center;width:1.45rem;height:1.45rem;border-radius:999px;background:#eef0f5;font-size:.72rem;font-weight:800}.active .progress-dot{background:var(--accent);color:#fff}.done .progress-dot{background:#e4f6ec;color:#21734f}
  div[data-testid="stForm"],div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:16px!important}
  .stButton>button,.stDownloadButton>button{border-radius:11px;font-weight:700;min-height:2.65rem}
  [data-testid="stAlert"]{border-radius:12px}
  @media(max-width:760px){.app-header{align-items:flex-start;flex-direction:column}.app-header h1{font-size:1.65rem}.model-chip{display:none}[data-testid="stMainBlockContainer"]{padding-top:1rem}}
</style>
""",unsafe_allow_html=True)

st.session_state.setdefault("authenticated",False)
st.session_state.setdefault("login_failed",False)

def authenticate_admin():
    authenticated=credentials_match(
        st.session_state.get("admin_user_id",""),
        st.session_state.get("admin_password",""),
        SETTINGS,
    )
    st.session_state.authenticated=authenticated
    st.session_state.login_failed=not authenticated
    st.session_state.admin_password=""

def logout_admin():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.authenticated=False

if SETTINGS.missing_required:
    st.title("Kids Learning & Quiz Studio")
    st.error("Server configuration is incomplete. Set the required environment variables and restart the app.")
    st.code("\n".join(SETTINGS.missing_required),language="text")
    st.stop()

if not st.session_state.authenticated:
    st.markdown('<div class="app-header"><div><span class="eyebrow">LearnCraft AI</span><h1>Kids learning & quiz studio</h1><p>Sign in to create lessons, quizzes, and printable learning packs.</p></div><span class="model-chip">Secure admin access</span></div>',unsafe_allow_html=True)
    left,login_column,right=st.columns([1.15,1,1.15])
    with login_column:
        with st.container(border=True):
            st.subheader("Welcome back",anchor=False)
            st.caption("Use the administrator credentials configured on this server.")
            with st.form("admin_login"):
                st.text_input("User ID",key="admin_user_id",autocomplete="username")
                st.text_input("Password",type="password",key="admin_password",autocomplete="current-password")
                st.form_submit_button("Sign in",type="primary",width="stretch",icon=":material/login:",on_click=authenticate_admin)
            if st.session_state.login_failed:
                st.error("Invalid user ID or password.")
    st.stop()

PREVIEW_COMPONENT = st.components.v2.component(
    "safe_artifact_preview",
    html="<div id='preview-root'></div>",
    js="""
export default function ({ data, parentElement }) {
  const root = parentElement.querySelector('#preview-root')
  if (!root) return
  let frame = root.querySelector('iframe')
  if (!frame) {
    frame = document.createElement('iframe')
    frame.setAttribute('sandbox', 'allow-scripts')
    frame.style.cssText = 'width:100%;height:100%;border:1px solid #dbe3f2;border-radius:16px;background:white'
    root.style.height = `${data.height || 620}px`
    root.appendChild(frame)
  }
  if (frame.srcdoc !== data.html) frame.srcdoc = data.html
}
""",
)
st.markdown(f'<div class="app-header"><div><span class="eyebrow">LearnCraft AI</span><h1>Learning pack studio</h1><p>Build a focused lesson and an original quiz from concepts or reference material.</p></div><span class="model-chip">{SETTINGS.openai_model}</span></div>',unsafe_allow_html=True)

for key,default in {"analysis":None,"approved":False,"artifacts":None,"sources":[],"request":None,"llm_model_used":None}.items(): st.session_state.setdefault(key,default)
if st.session_state.pop("config_saved_notice",False): st.toast("Configuration saved",icon=":material/check_circle:")
if st.session_state.pop("source_approved_notice",False): st.toast("Source plan approved",icon=":material/check_circle:")

def section_heading(number:int,title:str,description:str):
    st.markdown(f'<div class="section-heading"><span class="section-number">{number}</span><div><h2>{title}</h2><p>{description}</p></div></div>',unsafe_allow_html=True)

def invalidate_pack():
    for key in ["analysis","approved","artifacts","sources","request"]:
        st.session_state[key]=[] if key=="sources" else None if key!="approved" else False

with st.sidebar:
    st.markdown('<div class="sidebar-brand"><strong>Learning pack</strong><p>Follow the steps to create and export.</p></div>',unsafe_allow_html=True)
    current_step=5 if st.session_state.artifacts else 4 if st.session_state.approved else 3 if st.session_state.analysis else 2 if st.session_state.request else 1
    progress_labels=["Configure","Add material","Review","Generate","Download"]
    for step_number,step_label in enumerate(progress_labels,1):
        state="done" if step_number<current_step else "active" if step_number==current_step else ""
        marker="✓" if step_number<current_step else str(step_number)
        st.markdown(f'<div class="progress-step {state}"><span class="progress-dot">{marker}</span><span>{step_label}</span></div>',unsafe_allow_html=True)
    st.space("small")
    if st.button("Start over",width="stretch",icon=":material/refresh:"):
        for k in ["analysis","approved","artifacts","sources","request"]: st.session_state[k]=None if k!="sources" else []
        st.rerun()
    st.caption(f"Signed in · {SETTINGS.openai_model}")
    st.button("Sign out",width="stretch",icon=":material/logout:",on_click=logout_admin)

section_heading(1,"Configure","Choose the learner, subject, and content source.")
with st.expander("Configuration details" if st.session_state.request is None else "Edit configuration",expanded=st.session_state.request is None,icon=":material/settings:"):
    source_labels={"Concepts":InputMode.CONCEPTS.value,"Attachments":InputMode.ATTACHMENTS.value,"Both":InputMode.BOTH.value}
    source_choice=st.segmented_control(
        "Content source",
        list(source_labels),
        default="Concepts",
        key="input_mode_selector",
        on_change=invalidate_pack,
        width="content",
    )
    mode=source_labels[source_choice]
    st.caption("Use concepts, attached reference material, or both together.")
    with st.form("configuration",border=False):
        c1,c2,c3=st.columns([.8,1.2,1.2])
        grade=c1.selectbox("Grade / class",range(1,9),index=1)
        subject=c2.selectbox("Subject",["Mathematics","Science","English","Social Studies"],accept_new_options=True)
        curriculum=c3.selectbox("Curriculum / board",["Not specified","CBSE","ICSE","State Board"],accept_new_options=True)
        if mode!=InputMode.ATTACHMENTS.value:
            concepts_text=st.text_area(
                "Concepts",
                "Place value and face value\nLines and shapes\nNumber names\nExpanded and standard form\nEven and odd numbers",
                key="concepts_input",
                help="Enter one concept per line or separate concepts with commas.",
            )
        else:
            concepts_text=""
            st.caption("Concepts will be identified from the material you attach in the next step.")
        with st.expander("Assessment settings",icon=":material/tune:"):
            a,b,c,d=st.columns(4)
            difficulty=a.selectbox("Difficulty",[x.value for x in Difficulty],index=1)
            duration=b.number_input("Minutes",5,240,40)
            count=c.number_input("Questions",1,100,25)
            marks=d.number_input("Total marks",1,500,25)
            qtypes=st.multiselect("Question types",[x.value for x in QuestionType],default=[QuestionType.MCQ.value,QuestionType.FILL.value,QuestionType.NUMERIC.value,QuestionType.DRAWING.value])
            outputs=st.pills("Create",["lesson","quiz"],default=["lesson","quiz"],selection_mode="multi")
            e,f,g=st.columns(3)
            hints=e.checkbox("Include hints",True)
            examples=f.checkbox("Worked examples",True)
            explanations=g.checkbox("Answer explanations",True)
        with st.expander("Optional guidance",icon=":material/edit_note:"):
            goals=st.text_area("Learning goals",placeholder="One goal per line")
            special=st.text_area("Teacher instructions",placeholder="For example: use everyday objects and avoid negative numbers")
        saved=st.form_submit_button("Save and continue",type="primary",width="stretch",icon=":material/arrow_forward:")
if saved:
    concepts=[x.strip() for x in re.split(r"[,;\n]",concepts_text) if x.strip()]
    internal_seed=(
        st.session_state.request.random_seed
        if st.session_state.request is not None
        else random.SystemRandom().randint(1,2_147_483_647)
    )
    try:
        st.session_state.request=GenerationRequest(input_mode=mode,grade_level=grade,subject=subject,curriculum=curriculum,concepts=concepts,learning_goals=[x.strip() for x in goals.splitlines() if x.strip()],special_instructions=special or None,difficulty=difficulty,duration_minutes=duration,question_count=count,total_marks=marks,preferred_question_types=qtypes or [QuestionType.MCQ],include_hints=hints,include_worked_examples=examples,include_explanations=explanations,random_seed=internal_seed,requested_outputs=outputs or ["lesson"])
        st.session_state.config_saved_notice=True
        st.rerun()
    except ValidationError as e: st.error(e.errors()[0]["msg"])

uploaded=[]
if st.session_state.request is not None:
    section_heading(2,"Add material and analyze","Attach references when needed, then let the model prepare a source review.")
    with st.container(border=True):
        req_summary=st.session_state.request
        st.markdown(f":violet-badge[Grade {req_summary.grade_level}] :blue-badge[{req_summary.subject}] :gray-badge[{req_summary.question_count} questions] :gray-badge[{req_summary.total_marks} marks]")
        if mode==InputMode.CONCEPTS.value:
            st.caption("Your entered concepts are ready. Supporting material is not required for this mode.")
        else:
            uploaded=st.file_uploader("Supporting material",type=["pdf","png","jpg","jpeg","webp","html","htm","txt","md"],accept_multiple_files=True,help="Text and scanned PDFs, images, HTML, TXT, and Markdown are analyzed. Scanned pages use the configured model's vision capability.")
            if uploaded:
                st.dataframe([{"File":f.name,"Size":f"{f.size/1024:.1f} KB"} for f in uploaded],hide_index=True,width="stretch")
        analyze_clicked=st.button("Analyze source",type="primary",width="stretch",icon=":material/auto_awesome:")
else:
    st.caption("Save the configuration to continue to source analysis.")
    analyze_clicked=False

if analyze_clicked:
    if st.session_state.request.input_mode == InputMode.ATTACHMENTS and not uploaded:
        st.error("Upload at least one readable file in Attachments only mode, or switch to a concepts mode.")
        st.stop()
    try:
        pairs=[(f.name,f.getvalue()) for f in (uploaded or [])];validate_uploads(pairs);st.session_state.sources=[extract_file(*x) for x in pairs]
        provider=OpenAIContentProvider(SETTINGS.openai_api_key,SETTINGS.openai_model)
        with st.status("Analyzing curriculum and paper pattern…",expanded=True) as status:
            vision_sources=[s for s in st.session_state.sources if "vision" in s.get("status","")]
            if vision_sources:
                st.write(f"Reading {len(vision_sources)} scanned PDF/image source(s) with model vision")
            st.write(f"Sending the approved inputs to {SETTINGS.openai_model}")
            st.session_state.analysis=provider.analyze(st.session_state.request,st.session_state.sources)
            st.session_state.llm_model_used=SETTINGS.openai_model
            st.write("Validating the structured source analysis and paper pattern");status.update(label="Source review is ready",state="complete")
        st.session_state.approved=False;st.session_state.artifacts=None
    except Exception as e: st.error(f"LLM analysis failed: {friendly_llm_error(e)}")

if st.session_state.analysis:
    section_heading(3,"Review the source plan","Confirm the concepts and paper structure before generation.")
    an=st.session_state.analysis
    if st.session_state.approved:
        st.success("Source plan approved. Generation controls are ready below.",icon=":material/check_circle:")
    with st.expander(
        "Source plan details",
        expanded=not st.session_state.approved,
        icon=":material/fact_check:",
    ):
        st.markdown(f":blue-badge[{an.detected_subject or 'Subject'}] :violet-badge[Grade {an.detected_grade or '—'}] :green-badge[{an.overall_confidence:.0%} confidence]")
        st.caption("Your edits are authoritative and will be passed to the lesson and quiz writers.")
        review_left,review_right=st.columns(2)
        edited_concepts=review_left.text_area("Approved concepts","\n".join(an.concepts),key="review_concepts",height=160)
        edited_goals=review_right.text_area("Approved objectives","\n".join(an.learning_objectives),key="review_goals",height=160)
        rows=[{"Section":s.title,"Questions":s.question_count,"Marks":s.section_marks,"Type":s.permitted_question_types[0].value,"Difficulty":s.difficulty.value} for s in an.question_patterns]
        changed=st.data_editor(rows,num_rows="dynamic",width="stretch",key="pattern_editor")
        tq=sum(int(r["Questions"]) for r in changed);tm=sum(int(r["Marks"]) for r in changed)
        st.caption(f"Paper total: {tq} questions · {tm} marks")
        if an.evidence:
            with st.container(border=True):
                st.markdown("**Source evidence**")
                for e in an.evidence: st.write(f"**{e.filename}** — {e.short_excerpt}")
        if st.button("Approve source plan",type="primary",width="stretch",icon=":material/check_circle:"):
            if tq!=st.session_state.request.question_count or tm!=st.session_state.request.total_marks: st.error("Section totals must match the configured questions and marks.")
            else:
                an.concepts=[x.strip() for x in edited_concepts.splitlines() if x.strip()];an.learning_objectives=[x.strip() for x in edited_goals.splitlines() if x.strip()]
                an.question_patterns=[SectionPattern(section_id=f"S{i+1}",title=r["Section"],concepts_covered=[an.concepts[min(i,len(an.concepts)-1)]],permitted_question_types=[r["Type"]],question_count=int(r["Questions"]),section_marks=int(r["Marks"]),difficulty=r["Difficulty"],manual_review_required=r["Type"] in [QuestionType.DRAWING.value,QuestionType.LONG.value]) for i,r in enumerate(changed)]
                st.session_state.approved=True;st.session_state.source_approved_notice=True;st.rerun()

if st.session_state.approved:
    section_heading(4,"Generate and preview","Create the approved lesson and quiz, then inspect the results.")
    with st.container(border=True):
        st.caption(f"Powered by {SETTINGS.openai_model}. Visual aids are included when they improve understanding.")
        with st.container(horizontal=True):
            generate=st.button("Generate learning pack",type="primary",icon=":material/auto_awesome:")
            new_paper=st.button("Create another variation",icon=":material/shuffle:")
        if new_paper: st.session_state.request.random_seed=random.SystemRandom().randint(1,2_147_483_647);st.session_state.artifacts=None;st.rerun()
    if generate:
        req=st.session_state.request;an=st.session_state.analysis
        try:
            provider=OpenAIContentProvider(SETTINGS.openai_api_key,SETTINGS.openai_model)
            with st.status("Creating your LLM-authored learning pack…",expanded=True) as status:
                lesson=None;bp=None;qs=[]
                if "lesson" in req.requested_outputs:
                    st.write(f"Writing the concept lesson with {SETTINGS.openai_model}")
                    lesson=provider.generate_lesson(req,an)
                if "quiz" in req.requested_outputs:
                    st.write(f"Writing original quiz questions with {SETTINGS.openai_model}")
                    quiz=provider.generate_quiz(req,an);bp=quiz.blueprint;qs=quiz.questions
                    st.write("Checking counts, marks, answer consistency, and originality")
                    report=validate_content(req,an,bp,qs)
                    for repair_count in range(2):
                        if report.passed: break
                        st.write(f"Repairing {len(report.issues)} validation issue(s) with the LLM")
                        quiz=provider.repair_quiz(req,an,quiz,report);bp=quiz.blueprint;qs=quiz.questions
                        report=validate_content(req,an,bp,qs);report.repair_count=repair_count+1
                else:
                    report=ValidationReport(passed=bool(lesson),model_metadata={"provider":"openai","model":SETTINGS.openai_model})
                report.model_metadata={"provider":"openai","model":SETTINGS.openai_model}
                if not report.passed:
                    status.update(label="Validation needs attention",state="error");st.error("; ".join(i.message for i in report.issues))
                else:
                    gid=str(req.request_id)[:8];slug=f"grade-{req.grade_level}-{req.subject.lower().replace(' ','-')}";arts={}
                    if lesson is not None: arts[f"{slug}-concept-lesson.html"]=render_lesson_html(lesson,gid);arts[f"{slug}-concept-lesson.pdf"]=render_lesson_pdf(lesson,gid,req.random_seed)
                    if bp is not None: arts[f"{slug}-quiz.html"]=render_quiz_html(bp,qs,gid);student,key=render_quiz_pdfs(bp,qs,gid);arts[f"{slug}-quiz-student.pdf"]=student;arts[f"{slug}-answer-key.pdf"]=key
                    arts[f"{slug}-learning-pack.zip"]=package_artifacts(arts,{"generation_id":gid,"grade":req.grade_level,"subject":req.subject,"question_count":len(qs),"total_marks":sum(q.marks for q in qs),"validation":"passed","provider":"openai","model":SETTINGS.openai_model})
                    st.session_state.artifacts={"files":arts,"lesson":lesson,"blueprint":bp,"questions":qs,"report":report};st.session_state.llm_model_used=SETTINGS.openai_model;status.update(label="Learning pack ready",state="complete")
        except Exception as e:
            st.error(f"LLM generation failed: {friendly_llm_error(e)}")
    if st.session_state.artifacts:
        data=st.session_state.artifacts
        st.success(f"Generation with {data['report'].model_metadata.get('model')} passed content validation.",icon=":material/check_circle:")
        tab1,tab2=st.tabs([":material/menu_book: Lesson preview",":material/quiz: Quiz preview"])
        with tab1:
            if data["lesson"] is not None: PREVIEW_COMPONENT(data={"html":render_lesson_html(data["lesson"],str(st.session_state.request.request_id)[:8]).decode(),"height":620},height=640,key="lesson-preview")
        with tab2:
            if data["blueprint"] is not None: PREVIEW_COMPONENT(data={"html":render_quiz_html(data["blueprint"],data["questions"],str(st.session_state.request.request_id)[:8]).decode(),"height":720},height=740,key="quiz-preview")
        section_heading(5,"Download","Save the complete pack or individual lesson and quiz files.")
        with st.container(border=True):
            cols=st.columns(2)
            for i,(name,blob) in enumerate(data["files"].items()): cols[i%2].download_button(name,blob,file_name=name,mime="application/zip" if name.endswith(".zip") else "application/pdf" if name.endswith(".pdf") else "text/html",width="stretch",icon=":material/download:")
