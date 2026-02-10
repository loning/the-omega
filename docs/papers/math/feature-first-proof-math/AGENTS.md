# Feature First Proof Math: Working Protocol

This directory is for solving 10 problems from `questions.tex` and building one consolidated paper.

## Workflow

1. The user submits one problem solution at a time (Q1 to Q10).
2. The assistant reviews only:
   - Mathematical correctness.
   - Logical dependency and internal consistency.
3. If correct:
   - Accept the solution and write a polished section into the consolidated paper.
4. If incorrect or incomplete:
   - Report only content-level blocking issues and direct fixes.

## Review Contract (mandatory)

1. Conversation language with the user is Chinese.
2. Every review result must include a version id.
3. Review files must contain only directly relevant content issues:
   - Wrong implication or invalid inference.
   - Missing hypothesis or undefined objects.
   - Unjustified use of external theorem/lemma.
   - Contradiction with earlier established statements.
4. Do not include review comments that are only about publication style.
5. Style polishing is handled by the assistant during accepted-writeup, not as blocking review feedback.

## Review Output Format

Use this minimal structure in each review note:

- Problem: `Qk`
- Review Version: `Qk-Rn`
- Verdict: `PASS` or `FAIL`
- Blocking Issues:
  - only correctness/logic blockers
- Required Fixes:
  - only fixes mapped to blockers

## Writing Rules for Accepted Sections

- Paper default language: English (unless user changes it).
- Use standard theorem environments and explicit assumptions.
- Keep Omega/HPA interpretation separate from the core standard proof.

## Paths

- `questions.tex`: source problems.
- `reviews/`: versioned review notes.
- `paper/`: consolidated paper project (sections added after each PASS).
