# 0001 — Segmentation as a provisional working hypothesis

## Status

Accepted as a **provisional, reversible development hypothesis**. Not an
answer about CERI's real label structure. Must be revisited once CERI's
actual data, labels, and annotation workflow are known (see
`docs/data_questions_for_ceri.md`).

## Context

`docs/architecture.md` (Layer 3) states that each research task's problem
formulation — "classification vs. regression vs. segmentation-derived,
etc." — depends on facts about CERI's labels that are not yet known, and
"must not be guessed." That principle stands and is not changed by this
decision.

At the same time, the project needs *something concrete* to build and test
an end-to-end pipeline against while CERI's data and label schema are still
unknown. Without a working hypothesis, no pipeline code can be written or
tested at all.

This ADR records semantic segmentation (predicting a class for every pixel
in an image) as that working hypothesis — chosen for development purposes
only, not as a claim about how CERI's real labels are structured.

**Update:** CERI has since shared preliminary, unconfirmed information
indicating their existing labels are **image-level** (an estimated
percentage-cover value and/or a category such as rocky/sandy/algae/
unclear per photo), not confirmed pixel-level annotations.
`docs/architecture.md` (Layer 3) now lists percentage-cover regression and
image-level classification as candidate approaches that match this
reported label type more directly, alongside segmentation. This ADR's
scope is unchanged by that update: segmentation remains a reversible,
pipeline-testing scaffold here, not an assumed primary ML method for real
CERI data. It should be adopted as an actual modeling approach only if
suitable pixel-level annotations exist, or a defensible plan to produce
them is agreed with CERI.

## Decision

1. **Segmentation is a development-time scaffold, not a confirmed
   requirement.** The core pipeline will be built around a "mask" concept —
   one class-id per pixel — because it is a convenient, general structure
   from which both presence/absence and percentage cover can be derived.
   This choice is explicitly **reversible**: if CERI's real labels turn out
   to be image-level tags, point counts, bounding boxes, or anything else,
   the mask-producing step can be swapped out without changing how
   presence/absence or cover are computed *from* a mask, since those
   consumers only depend on the mask structure, not on how it was produced.

2. **The synthetic, color-matching segmenter is strictly a pipeline-testing
   tool.** It exists only to prove that mask → presence/cover → annotation
   → export works end-to-end, using synthetic images whose "correct" answer
   is already known by construction. It must never be presented, labeled,
   or logged as an eelgrass detector or as a real model prediction. Every
   output it produces must carry a method/source label (see Decision 4)
   that makes this unambiguous wherever the output is displayed, stored, or
   exported.

3. **Presence/absence must be computed by an explicit, documented,
   configurable rule — never assumed.** It must not be hardcoded as "any
   nonzero count of an eelgrass-like class pixel means present." Whatever
   rule is used (e.g. a minimum pixel count, a minimum percentage of the
   valid-pixel area, or something else) must be:
   - stated in code and in configuration, not implied,
   - adjustable without code changes, since the correct rule for CERI's
     real imagery is unknown,
   - recorded alongside each presence/absence result, so a reader can see
     exactly which rule produced it.

4. **Cover outputs must be transparent about what they counted.** Every
   percentage-cover result must report, alongside the percentage(s):
   - the count of valid classified pixels (pixels confidently assigned to a
     real class),
   - the count of unclassified pixels (valid image data, no confident
     class),
   - the count of invalid pixels (should not count at all — e.g. corrupted
     or out-of-frame data),
   - the exact denominator used for each percentage calculation (e.g.
     "percentage of valid pixels," explicitly excluding invalid pixels, and
     explicitly stating whether unclassified pixels are included in the
     denominator or reported separately).
   A percentage with no visible denominator or pixel-count breakdown is not
   acceptable output from this pipeline.

5. **Every result must record its method and source**, so synthetic,
   human-reviewed, and (future) model-generated outputs can never be
   confused with one another. At minimum, every stored or exported result
   must carry:
   - a `source` value (e.g. `"synthetic_placeholder_segmenter"`,
     `"human_review"` — `"trained_model"` does not exist as a valid value
     yet, because no trained model exists),
   - a `method` or description of how the result was produced,
   - a `schema_version`, so the recording format itself can evolve
     traceably.
   This labeling must survive export (CSV/JSON) — a file viewed outside the
   application must still make the distinction obvious, not just the UI.

6. **This decision stays reversible.** Nothing built under this ADR may
   assume CERI's real data will use segmentation masks, nor may it block
   adopting a different label structure later. If CERI's answers (see
   `docs/data_questions_for_ceri.md`) indicate a different formulation is
   correct, this ADR should be superseded by a new decision record, and the
   mask-producing step replaced — the presence/cover/annotation/export
   logic built on top should not need to change, by design.

## Consequences

- Enables M1 onward (class registry, mask structure, presence/cover logic,
  placeholder segmenter, annotations, export) to proceed without waiting
  for CERI, while staying honest about what has and hasn't been confirmed.
- Adds ongoing discipline: every new output type must be checked against
  Decision 4 and 5 (pixel-count transparency, method/source labeling)
  before it's considered done.
- Prevents a likely failure mode: a visually polished UI quietly implying
  real detection capability. The method/source and pixel-count
  requirements are deliberately mechanical (testable), not just a tone
  guideline.
- Means some early code (the mask abstraction, the placeholder segmenter)
  may be discarded or substantially reworked once CERI's real label
  structure is known. This is an accepted, intentional cost of having a
  working pipeline sooner — not a sign the approach failed.

## Related

- `docs/architecture.md`, Layer 3 — the "must not be guessed" principle
  this ADR operates under.
- `docs/project_workflow.md`, Stage 6 — notes that task formulation depends
  on unknown label structure.
- `docs/data_questions_for_ceri.md` — the open questions that, once
  answered, may require superseding this ADR.
