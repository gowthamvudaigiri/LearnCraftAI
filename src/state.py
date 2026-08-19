from typing import TypedDict, Any
class StudioState(TypedDict,total=False):
    request: Any
    sources: list[dict]
    analysis: Any
    approved: bool
    lesson: Any
    blueprint: Any
    questions: list[Any]
    report: Any
    artifacts: dict[str,bytes]
