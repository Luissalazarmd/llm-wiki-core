---
name: capture-source
description: "Capture sources once with provenance and library rules."
version: 0.1.0
author: Luis Fernando Salazar Hortua, Hermes Agent
---

# Capture a source

## When to Use

Retain a supplied original, with optional attachments, through the capture writer or
existing permitted create-only tools. Retire one only as the owner's exception.

## Procedure

1. Read [AGENTS](../../AGENTS.md), actual library rules and [admission](../../docs/raw-admission.md).
2. Identify provenance/version/rights and search authorized sources for duplicates.
3. Prepare preserved content/reference and its persistent useful connection, drafted
   from the stated purpose; a simple reference needs no strategy discussion. Where the
   library has source templates, fill one: shape, not approval.
4. Bind it with `capture_write.py prepare`. Show the exact wrapper and each attachment
   name, size and sha256; follow [review](../../docs/review-contract.md) and library
   custody. The decision is for this packet only.
5. `capture_write.py save` rechecks inputs, creates without overwrite as independent
   copies, reads back and verifies. Report any `capture_partial` exactly. Without
   plain-file permission, use the host's create-only tool and `capture_check.py`.
6. Retire a capture only when the owner asks in this conversation: name the create-only
   rule being excepted, show the `retire` plan and its linking notes, then run it.
7. Create or change a source template only on the owner's request, through
   `template_write.py` [prepare → show the exact template → save](../../docs/raw-admission.md#templates).

## Pitfalls

Core supplies no downloader. Unknown versions need reconciliation. Approval of an
earlier capture, retired or deleted, never covers a new one: prepare and show it again,
and never rewrite a recorded decision. Do not write your own capture, removal or
template script, and never replace an owner's template without its current hash.
Retirement never edits the notes that link to the source; tell the owner about them.

## Verification

Report captured versus proposed, duplicate-search scope and extraction limits.
Structural checks certify neither meaning nor K-Plex integration.
