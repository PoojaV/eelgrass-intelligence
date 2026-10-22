# Architecture

This document describes the planned system in terms of four conceptual
layers. It intentionally stops at the conceptual level — no specific
technologies, schemas, or model architectures are committed to here beyond
what has already been decided, and nothing below assumes facts about CERI's
dataset that have not yet been confirmed (see `data_questions_for_ceri.md`).

## Layer 1 — Data

CERI's raw eelgrass and seafloor imagery, and whatever labels accompany it.

CERI has shared **preliminary, unconfirmed** information about label
volume and format: roughly 6,000 photos labelled at least once, and
another 20,000–30,000+ unlabelled photos; existing labels reportedly
include an estimated eelgrass percentage-cover value and/or a category
such as rocky, sandy, algae, or unclear; many photos have been assessed by
at least three student reviewers. These figures inform scale and format
expectations only — they are not a confirmed dataset schema, and the exact
label structure (e.g. whether categories are mutually exclusive, how
multi-reviewer disagreement is resolved) is still open (see
`data_questions_for_ceri.md`).

The product direction also includes accepting **underwater survey video**
as a source of imagery, not just individual photos: frames are extracted
from uploaded video at approximately one frame per second. The source
video and each extracted frame's timestamp (its position in the original
footage) are both retained, so any frame can always be traced back to the
exact moment it came from.

Principles for this layer:

- Raw data is treated as immutable once received. It is never edited in
  place. This includes uploaded survey video: frame extraction must be a
  regenerable derivation from the video, never a destructive edit of it.
- Anything derived from raw data (validated subsets, splits, features,
  extracted frames) must be regenerable from it — the raw data is the
  single source of truth.
- What counts as a single "sample," and what label formats exist, are
  facts to be obtained from CERI, not assumptions made here.
- Geographic and survey metadata (e.g. location, survey date or
  identifier) should be associated with ingested data when available, but
  CERI's exact metadata schema is not yet confirmed.

## Layer 2 — Data processing / validation

The layer between raw data and anything that trains, evaluates, or runs
inference with a model.

Responsibilities:

- Check that incoming data matches an explicit, agreed schema (once that
  schema is defined with CERI) — file integrity, expected fields, expected
  label formats.
- For video input specifically: extract frames at approximately one frame
  per second, and validate that every extracted frame carries a timestamp
  linking it back to its exact position in the source video, and that the
  source video itself remains intact and traceable.
- Fail loudly and early when data doesn't match expectations, rather than
  letting bad data silently propagate into training, evaluation, or
  inference.
- Produce a clean, well-defined interface (e.g. a dataset abstraction) that
  every later layer relies on instead of re-parsing raw files itself.

This layer cannot be meaningfully built until the open questions in
`data_questions_for_ceri.md` are answered. Frame extraction and timestamp
handling, however, do not depend on CERI's label schema, so that part can
be developed and tested independently (including against synthetic or
openly-licensed video), without waiting for CERI's answers.

**Implemented:** `src/eelgrass_intelligence/video_frames.py` extracts
frames from a local video file at a configurable interval (default: one
per second), using each decoded frame's own reported timestamp rather
than assuming a constant frame rate — see that module's docstring for the
reasoning and for its documented timestamp-accuracy limitation on
variable-frame-rate video. Each run produces a JSON manifest recording
the source video's filename, size, and SHA-256 checksum; the interval
used; and every extracted frame's index, filename, and timestamp (in
both seconds and milliseconds). The manifest never includes survey
identifiers, coordinates, dates, labels, or other environmental
metadata — those are out of scope for this ingestion step and must come
from a separately validated interface if and when they exist. This has
been tested only against small, synthetic videos generated locally; it
has not yet been run against any real CERI or community-submitted video.

## Layer 3 — ML

Training, evaluation, and experiment tracking for the three research tasks:

1. Eelgrass presence/absence detection
2. Percentage cover estimation
3. Cover-type classification

**No single modeling approach is confirmed or assumed as primary.** CERI's
known, preliminary label information points toward **image-level**
labels — an estimated percentage-cover value and/or a category per photo —
not confirmed pixel-level annotations. Candidate approaches to evaluate
once real labelled data is available, in rough order of how directly they
match what CERI has reportedly already produced:

- **Percentage-cover regression** — predicting the numeric cover estimate
  directly from an image, matching the reported label type most closely.
- **Image-level classification** — predicting presence/absence, or a
  category such as rocky/sandy/algae/unclear, directly from an image.
  This depends on confirming the real label schema (e.g. whether
  categories are mutually exclusive) with CERI first.
- **Semantic segmentation** — predicting a class per pixel. This remains a
  reversible, provisional *development scaffold* (see
  `docs/decisions/0001-segmentation-as-provisional-working-hypothesis.md`)
  because it is a convenient structure for prototyping presence/cover
  logic, but it must be adopted as a real modeling approach only if
  suitable pixel-level annotations exist, or a defensible plan to produce
  them is agreed with CERI. It is a candidate, not the assumed method.

Principles for this layer:

- Each task's problem formulation depends on facts about CERI's labels
  that are not yet known, and must not be guessed. The candidate list
  above is a set of options to evaluate, not a decision.
- Every experiment should be defined by an explicit, versioned configuration
  rather than ad hoc code changes, so results are reproducible and
  comparable.
- Evaluation must use a held-out test set that is not used to make modeling
  decisions, with splitting strategy chosen to avoid data leakage. In
  particular, splits must be constructed by independent survey group,
  transect, or site wherever that metadata is available — never by
  randomly splitting individual images or video frames. Frames extracted
  roughly one second apart from the same video are often highly similar,
  so a random image-level split can place near-duplicate frames on both
  sides of a split, producing a misleadingly optimistic performance
  estimate.

## Layer 4 — Serving / product

The layer researchers and community surveyors actually interact with. The
product goal is an open-access, easy-to-use tool for community eelgrass
surveys, built around this workflow:

1. Upload an underwater survey video.
2. Extract frames at roughly one per second (Layer 2), keeping the source
   video and each frame's timestamp.
3. Run automated analysis on frames, once a validated model exists
   (Layer 3) — never claimed before that point.
4. Let a person review and correct the automated results.
5. Associate results with geographic and survey metadata, when available.
6. Produce a heatmap and exportable results.

Principles for this layer:

- This layer should stay as simple as possible until the layers beneath it
  are stable — building a polished interface around an unvalidated model or
  an unconfirmed data schema risks having to redo it.
- The interface must never claim to perform real eelgrass detection or
  cover estimation unless backed by a model validated per Layer 3's
  evaluation principles. Any synthetic or placeholder demonstration must
  be clearly and persistently labeled as such, never presented as
  evidence of real detection performance (see
  `docs/decisions/0001-segmentation-as-provisional-working-hypothesis.md`).
- Human review results, and any future model-generated results, must be
  distinguishably recorded (method and source), so the two can never be
  confused with each other once exported or displayed.
- A heatmap and exported results are downstream presentations of
  whatever per-frame results exist (human-reviewed and/or
  model-generated) — they must inherit the same traceability and
  source-labeling, not bypass it.
- Reliability and observability (knowing when and why a prediction request
  failed, or when model behavior may be drifting) are product requirements,
  not afterthoughts, once this layer exists.

## Status

As of Step 1, only the repository structure existed; no functional code was
written yet. Since then:

- A class registry and segmentation-mask representation (Layer 3
  scaffolding, provisional — see
  `docs/decisions/0001-segmentation-as-provisional-working-hypothesis.md`)
  have been implemented and tested.
- Video frame extraction (Layer 1/2, see above) has been implemented and
  tested against small, locally generated synthetic videos only.

**No eelgrass classification or percentage-cover prediction model has
been implemented, trained, or validated.** Segmentation remains
provisional scaffolding, not an adopted modeling approach. No CERI
dataset has been integrated. Layer 1 cannot be finalized until CERI's
dataset, label schema, and survey metadata are understood. Location-aware
heatmaps and a user-facing upload interface (Layer 4) remain future,
unbuilt capabilities. No model, API, frontend, or database exists yet.
