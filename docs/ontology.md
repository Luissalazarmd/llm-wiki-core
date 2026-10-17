# Three roles, connected notes

[Version 2](../config/ontology.json): source preserves an original; note authors
an explanation, question, entity, project or diagram; map authors a reading route.
Only notes have [maturity](knowledge-workflow.md#idea-emergence), independent of review.

## Declare a connection once

Keep role, optional maturity and optional up in frontmatter. Up is one explicit
map wikilink; derive children. Preserve existing IDs/titles/authorship. In original
note bodies, put typed declarations beside their arguments:

```markdown
Evidence:: [[Raw/report#Results]]
Contrasts:: [[Wiki/alternative]]
BuildsOn:: [[Wiki/question]]
```

Related:: provides useful reading; avoid generic redundancy while retaining distinct
meanings. Optional sources lists need not duplicate Evidence. Plain links navigate;
K-Plex position alone cannot show every meaning. Inspect arguments/details.

[Projection](projection-reference.md) retains legacy roles/developing/review/relations
without rewriting files. Review declarations are data, never approval. Notes/maps
without IDs get temporary path locators.

## One declaration, derived views

See Declare a connection once above.
