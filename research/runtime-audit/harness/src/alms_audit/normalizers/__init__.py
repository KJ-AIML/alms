"""Runtime-specific normalizers.

A normalizer converts serialized raw evidence (plain JSON, never SDK objects) into the
candidate audit vocabulary (DevSpec Section 43). Normalizers live in the harness and must
NOT import any provider SDK; they read only the raw JSON a probe wrote. They preserve raw
references and emit provider_extension events for semantics that do not fit the vocabulary.
"""
