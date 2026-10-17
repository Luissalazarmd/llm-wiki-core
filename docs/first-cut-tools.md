# Optional tools

Use existing permitted host tools or these helpers; no automatic installation.
[Private settings](../config/personal.example.json) restrict operations, never grant
permission. Declare actual library_root, authorized_paths and optional source/draft/
knowledge layers. Defaults are read-only; configuration stays private.

```sh
python3 scripts/knowledge.py --root /library --mode existing --scope Reading
python3 scripts/library.py --config /private.json map --scope Reading
python3 scripts/library.py --config /private.json proposal --create --target Notes/new.md --evidence Sources/a.md < /draft.md
python3 scripts/capture_check.py --config /private.json --target Sources/new.md < /capture.md
python3 scripts/note_write.py --config /private.json check --packet /proposal.json
```

Save uses save instead of check; recovery uses restore --record. Capture recheck
uses --expected-sha256; readback adds --saved. Follow [review](review-contract.md),
[capture](raw-admission.md), [plain saving](plain-saving.md) and [projection](projection-reference.md).
Mapping bounds inventory to 500 entries and reads attachment metadata, never binary content.
