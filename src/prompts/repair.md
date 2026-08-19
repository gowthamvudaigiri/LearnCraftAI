# Targeted quiz repair v2

Repair only the fields and question IDs named in `validation_issues`. Preserve valid original questions, approved concepts, objectives, section IDs, section counts, total count, marks, difficulty, and seed. Recompute arithmetic from stored operands. Ensure MCQ options are distinct and contain the canonical answer exactly once. Remove duplicate prompts without adding meaningless suffixes. Return the full corrected GeneratedQuiz tool output and no hidden reasoning.
