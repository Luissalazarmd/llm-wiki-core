# Projection details

Read-only helpers require existing Python/PyYAML. Existing mode reads explicitly
selected foreign files/folders; metadata stays unknown. Strict mode scans only
known Raw/Wiki collections. Limits: existing 200 notes, strict 2,000; 256 KiB/file,
16 MiB total. Empty strict scope needs explicit opt-in. Symlinks/unsafe paths fail.

## Native relation grammar

Targets require explicit catalog paths, optionally an exact unique plain ATX
heading. Basenames, traversal, encoded paths, unsupported blocks/slugs and ambiguous
headings fail. link-prefix explicitly handles a subfolder root without expanding
scope. Code/comments create no declarations. Current source/declaration hashes
are provenance, not historical approval. Legacy evidence retains required
source/hash/locator bindings; stale hashes fail.

Legacy roles normalize to note and developing to synthesis only in output. IDs
remain authoritative. Reference-derived IDs incorporate optional Version; unchanged
unversioned references retain their identity. Duplicate known versions fail;
legacy distinct explicit IDs without Version remain readable without inferred editions.

Focus is one hop, default eight/max fifty neighbors, 16 KiB output. Views are
disposable. Proposals bind existing bytes or absent destinations, complete nonempty
draft and explicit Markdown evidence. They grant no approval/write or atomic snapshot.
