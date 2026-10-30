# Scientific citations and metadata closure

Objective: close the general citation/metadata documentation and its authorized Git delivery, without new runtime behavior or library operations.

## Tasks

- Review — done. Reviewed both inherited documentation diffs against current contracts. Vancouver applies to new scientific derived notes unless local rules differ; full references, available verified DOI links and actual consulted scope belong in the human preview. Identity, authorship, provenance and local writer rules remain protected; no bulk conversion.
- Documentation — done. Retained the inherited changes in `docs/knowledge-workflow.md` and `skills/review-save/SKILL.md`; clarified that DOI links are included when available. This tracker records the bounded closure without rewriting earlier delivery history.
- Validation — done. On 2026-10-30, 192 unit tests passed; the synthetic existing-library demo passed with unchanged inputs and no apply. Four JSON files and one Canvas parsed; 111 local Markdown links, including 20 heading references, resolved. Whitespace passed. These checks do not establish scientific correctness, actual human library approval or native rendering. Browser/native and independent-agent demo acceptance were not run.
- Git delivery — prepared. Canonical destination verified as public `Luissalazarmd/llm-wiki-core`, default branch `main`, with no branch protection or rulesets and no required PR/CI workflow. The owner explicitly authorized integrating the four previously published implementation commits as well as this documentation. Preserve their commits and the historical trackers; use a non-force fast-forward delivery after final publication review. Final remote hashes and delivery outcome belong in project operational memory.

## Continuity and boundaries

Starting branch: `feat/living-synthesis-numbering` at `b81fbf7`; local/remote `main` at `f18c15a`. Only the two inherited citation-policy documents were modified; no untracked files existed. The previous [implementation delivery](living-synthesis-implementation.md) was branch-only under its earlier authorization; today's explicit integration authorization extends that delivery without changing its historical record.

No private library, personal bibliography, configuration, recovery data or cross-project memory was accessed or imported. No runtime, test, schema or integration changes are part of the new documentation commit. Rollback unit: the citation-policy section, its review/save pointer and this tracker; previous implementation commits remain separate. Runtime harness: not applicable to the prose-only delta; the full synthetic suite covers the implementation being integrated.
