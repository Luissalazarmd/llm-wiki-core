# Reproducible acceptance

All product tests use synthetic local files, Python and PyYAML; no private engine, accounts, clinical data or vendor source input. Run `python3 -m unittest discover -s tests -v` in an authorized environment, with bytecode writes disabled if desired. Report actual pass/fail/skip counts; do not count a removed vendor test as a successful test.

## Deterministic cases

- Existing library with foreign/no YAML: explicit scoped discovery and mapping, no migration, no out-of-scope file content, original hashes/mtimes unchanged.
- Applicable nested AGENTS paths reported; root compatibility field does not hide nested rules. Agent reads actual rules before content.
- Bounded files/context, safe paths, symlinks/special files and YAML/JSON ambiguity rejected; duplicates reconcile rather than overwrite.
- Role/maturity/review independent; YAML accepted state cannot authorize a write. Factual strict relations bind source/version/locator; semantic support still needs source reading.
- Personal config separately loaded: authorized paths and language checked, optional organization/objectives/initiative do not create migrations or background services.
- Proposal binds base/draft/evidence; changed inputs produce a different packet. Plain writer recomputes displayed diff and rejects even a rehashed misleading packet.
- Plain save requires explicit policy and existing private recovery directory; immutable configured sources/instructions and known managed markers (including broken symlinks) block editing.
- Stale target/evidence refused without overwrite; changed packet refused. Quiet single-writer saving and readback exercised, previous bytes persisted before replacement.
- Restore returns exact previous bytes, including CRLF, and refuses to overwrite subsequent edits; injected replacement failure leaves original and recovery bytes intact.
- AGENTS links three portable skills; valid frontmatter/relative links. Native host registration is not inferred.
- Product contains no obsolete vendor installer/adapter/manifest or test suite requiring private inputs. The independently reproducible demo copies only essential helpers into a disposable checkout.

## Human/host cases — separate evidence

Use [demo](../tests/demo_existing_library.py) for tool-level map/navigation/proposal and the actual host for a small user-guided task. Explain fictional sources and affected files before requesting decisions. Exercise reading → proposal → actual confirmation → save/readback → correction → revised confirmation. Do not manufacture user events to make a test pass.

Capture follows the host's verified retrieval/create-only tools or library writer; Core has no bundled capture runtime. Test duplicate reuse/provenance and source preservation separately when evaluating a particular host. Do not infer working PDF/network capture from synthetic prepared inputs.

Recovery is a separate human permission; automated restore tests do not prove a user requested it. Actual Obsidian/K-Plex rendering, voice, concurrent writers, authenticated managed apply, stronger crash guarantees and host portability need their own explicit scope and verification. They are not baseline private-engine milestones and must not become new infrastructure by default.

## Invariants

No self-approval or source-driven tool execution. Real user interaction and tool permissions are host responsibilities, not content-hash properties. Actual library rules prevail; unknown writer means proposal-only. Preserve exact quotations/identifiers, label translations, default output language Spanish if unspecified. Note approval never permits external tasks, messages, uploads, account changes or Git publication. Local filesystem scope is not provider-transmission permission. No personal memory mirrored into bibliography; no per-article parallel library or compulsory maps.
