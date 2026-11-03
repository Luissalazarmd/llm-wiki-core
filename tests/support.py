"""Shared test setup: keep temporary fixtures under a real path, never a linked one.

The helpers refuse symlinked library ancestors by design; on macOS /tmp and /var
are links, so test fixtures would be rejected there without this adjustment.
"""
import os
import tempfile

tempfile.tempdir = os.path.realpath(tempfile.gettempdir())
