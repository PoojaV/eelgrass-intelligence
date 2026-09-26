# Architecture

This document describes the planned system in terms of four conceptual
layers. It intentionally stops at the conceptual level — no specific
technologies, schemas, or model architectures are committed to here beyond
what has already been decided, and nothing below assumes facts about CERI's
dataset that have not yet been confirmed (see `data_questions_for_ceri.md`).

## Layer 1 — Data

CERI's raw eelgrass and seafloor imagery, and whatever labels accompany it.

Principles for this layer:

- Raw data is treated as immutable once received. It is never edited in
  place.
- Anything derived from raw data (validated subsets, splits, features) must
  be regenerable from it — the raw data is the single source of truth.
- What counts as a single "sample," and what label formats exist, are
  facts to be obtained from CERI, not assumptions made here.

## Layer 2 — Data processing / validation

The layer between raw data and anything that trains or evaluates a model.

Responsibilities:

- Check that incoming data matches an explicit, agreed schema (once that
  schema is defined with CERI) — file integrity, expected fields, expected
  label formats.
- Fail loudly and early when data doesn't match expectations, rather than
  letting bad data silently propagate into training or evaluation.
- Produce a clean, well-defined interface (e.g. a dataset abstraction) that
  every later layer relies on instead of re-parsing raw files itself.

This layer cannot be meaningfully built until the open questions in
`data_questions_for_ceri.md` are answered.

## Layer 3 — ML

Training, evaluation, and experiment tracking for the three research tasks:

1. Eelgrass presence/absence detection
2. Percentage cover estimation
3. Cover-type classification

Principles for this layer:

- Each task's problem formulation (classification vs. regression vs.
  segmentation-derived, etc.) depends on facts about CERI's labels that are
  not yet known, and must not be guessed.
- Every experiment should be defined by an explicit, versioned configuration
  rather than ad hoc code changes, so results are reproducible and
  comparable.
- Evaluation must use a held-out test set that is not used to make modeling
  decisions, with splitting strategy chosen to avoid data leakage (e.g.
  across images from the same site or survey date).

## Layer 4 — Serving / product

The layer researchers actually interact with:

- An API that exposes trained models for inference on new imagery.
- A researcher-facing interface for submitting images and viewing results,
  designed to be usable without any ML or coding knowledge.

Principles for this layer:

- This layer should stay as simple as possible until the layers beneath it
  are stable — building a polished interface around an unvalidated model or
  an unconfirmed data schema risks having to redo it.
- Reliability and observability (knowing when and why a prediction request
  failed, or when model behavior may be drifting) are product requirements,
  not afterthoughts, once this layer exists.

## Status

As of Step 1, only the repository structure exists. None of the four layers
have functional code yet. Layer 1 cannot be finalized until CERI's dataset
and label schema are understood; layers 2–4 depend on Layer 1.
