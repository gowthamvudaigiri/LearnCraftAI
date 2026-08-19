from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from src.state import StudioState
from src.generator import analyze, lesson_for, questions_for
from src.validators import validate_content

def validate_request(state:StudioState): state["request"].model_dump(); return {}
def extract_sources(state:StudioState): return {"sources":state.get("sources",[])}
def analyze_curriculum(state:StudioState): return {"analysis":analyze(state["request"],state.get("sources",[]))}
def await_source_review(state:StudioState): return {"approved":state.get("approved",False)}
def plan_documents(state:StudioState):
    bp,qs=questions_for(state["request"],state["analysis"]); return {"blueprint":bp,"questions":qs}
def generate_lesson(state:StudioState): return {"lesson":lesson_for(state["request"],state["analysis"])}
def verify_answers(state:StudioState): return {}
def quality_review(state:StudioState): return {"report":validate_content(state["request"],state["analysis"],state["blueprint"],state["questions"])}
def route_outputs(state): return "lesson" if "lesson" in state["request"].requested_outputs else "verify"

def build_graph():
    g=StateGraph(StudioState)
    for name,fn in [("validate_request",validate_request),("extract_sources",extract_sources),("analyze_curriculum",analyze_curriculum),("await_source_review",await_source_review),("plan_documents",plan_documents),("generate_lesson",generate_lesson),("verify_answers",verify_answers),("quality_review",quality_review)]: g.add_node(name,fn)
    g.add_edge(START,"validate_request");g.add_edge("validate_request","extract_sources");g.add_edge("extract_sources","analyze_curriculum");g.add_edge("analyze_curriculum","await_source_review");g.add_edge("await_source_review","plan_documents")
    g.add_conditional_edges("plan_documents",route_outputs,{"lesson":"generate_lesson","verify":"verify_answers"});g.add_edge("generate_lesson","verify_answers");g.add_edge("verify_answers","quality_review");g.add_edge("quality_review",END)
    return g.compile()
