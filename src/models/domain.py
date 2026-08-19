from __future__ import annotations
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StructuredOutputModel(BaseModel):
    """Base for schemas sent to OpenAI Structured Outputs."""

    model_config = ConfigDict(extra="forbid")

class InputMode(StrEnum):
    CONCEPTS = "Concepts only"
    ATTACHMENTS = "Attachments only"
    BOTH = "Concepts + attachments"

class Difficulty(StrEnum):
    EASY = "easy"
    STANDARD = "standard"
    CHALLENGING = "challenging"
    MIXED = "mixed"

class QuestionType(StrEnum):
    MCQ = "multiple choice"
    TRUE_FALSE = "true/false"
    FILL = "fill in the blank"
    SHORT = "short answer"
    NUMERIC = "numeric answer"
    DRAWING = "drawing/manual activity"
    LONG = "long answer/manual review"

class GenerationRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    input_mode: InputMode = InputMode.CONCEPTS
    grade_level: int = Field(default=2, ge=1, le=8)
    subject: str = "Mathematics"
    curriculum: str = "Not specified"
    language: str = "English"
    concepts: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    special_instructions: str | None = None
    difficulty: Difficulty = Difficulty.STANDARD
    duration_minutes: int = Field(default=40, ge=5, le=240)
    question_count: int = Field(default=25, ge=1, le=100)
    total_marks: int = Field(default=25, ge=1, le=500)
    preferred_question_types: list[QuestionType] = Field(default_factory=lambda: [QuestionType.MCQ, QuestionType.FILL, QuestionType.NUMERIC])
    include_hints: bool = True
    include_worked_examples: bool = True
    include_explanations: bool = True
    preserve_source_pattern: bool = True
    random_seed: int = 2025
    requested_outputs: list[str] = Field(default_factory=lambda: ["lesson", "quiz"])
    attachment_descriptors: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def has_input(self):
        if self.input_mode == InputMode.CONCEPTS and not self.concepts:
            raise ValueError("Enter at least one concept.")
        return self

class SourceEvidence(StructuredOutputModel):
    source_id: str
    filename: str
    page_number: int | None = None
    short_excerpt: str = ""
    evidence_type: str = "text"
    confidence: float = Field(default=1.0, ge=0, le=1)

class SectionPattern(StructuredOutputModel):
    section_id: str
    title: str
    instructions: str = "Answer all questions."
    concepts_covered: list[str] = Field(default_factory=list)
    permitted_question_types: list[QuestionType] = Field(default_factory=lambda: [QuestionType.MCQ])
    question_count: int = Field(ge=1)
    section_marks: int = Field(ge=1)
    difficulty: Difficulty = Difficulty.STANDARD
    manual_review_required: bool = False

class SourceAnalysis(StructuredOutputModel):
    detected_title: str = "Learning Pack"
    detected_subject: str = ""
    detected_grade: int | None = None
    detected_curriculum: str = "Not specified"
    concepts: list[str]
    learning_objectives: list[str]
    prerequisites: list[str] = Field(default_factory=list)
    vocabulary: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    worked_example_patterns: list[str] = Field(default_factory=list)
    question_patterns: list[SectionPattern]
    evidence: list[SourceEvidence] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=.9, ge=0, le=1)

class LessonSection(StructuredOutputModel):
    title: str
    objective: str
    explanation: str
    worked_examples: list[str]
    visual: str = ""
    common_mistake: str
    guided_practice: str
    quick_check: str
    hint: str = ""
    answer: str

class LessonPlan(StructuredOutputModel):
    title: str
    sections: list[LessonSection]

class ObjectiveCoverage(StructuredOutputModel):
    objective_id: str
    section_ids: list[str]


class VerificationMetadata(StructuredOutputModel):
    eligible: bool = True
    operation: str | None = None
    operands: list[int | float] = Field(default_factory=list)
    computed_answer: int | float | str | None = None
    units: str | None = None
    tolerance: float | None = None


class QuizBlueprint(StructuredOutputModel):
    title: str
    instructions: str
    grade: int
    subject: str
    duration_minutes: int
    total_marks: int
    sections: list[SectionPattern]
    objective_coverage: list[ObjectiveCoverage]
    random_seed: int

class Question(StructuredOutputModel):
    question_id: str
    section_id: str
    objective_ids: list[str]
    question_type: QuestionType
    prompt: str
    options: list[str] = Field(default_factory=list)
    canonical_answer: str
    alternate_answers: list[str] = Field(default_factory=list)
    marks: int = 1
    difficulty: Difficulty = Difficulty.STANDARD
    hint: str = ""
    explanation: str = ""
    manual_review_required: bool = False
    verification: VerificationMetadata = Field(default_factory=VerificationMetadata)

class GeneratedQuiz(StructuredOutputModel):
    blueprint: QuizBlueprint
    questions: list[Question]

class ValidationIssue(BaseModel):
    severity: str
    message: str
    object_id: str | None = None

class ValidationReport(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    repair_count: int = 0
    model_metadata: dict[str, str] = Field(default_factory=dict)
