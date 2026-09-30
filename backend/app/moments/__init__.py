"""The moments engine: signals -> moments -> arbitration.

Design: `docs/design/moments-engine.md`. Every layer is a pure function of its input, which is
what keeps it testable, cheap to run for millions of customers, and explainable per suggestion.
"""
