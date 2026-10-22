# Eelgrass Intelligence

## 1. What this is

Eelgrass Intelligence is an applied machine learning project developed around a
real research use case from the Coastal Ecology and Restoration Institute
(CERI). CERI has a large collection of labelled and unlabelled eelgrass and
seafloor imagery and wants to explore machine learning to help automate parts
of their analysis workflow.

The long-term goal is a tool that is technically rigorous enough to hold up to
scientific scrutiny, while being simple enough for a non-ML researcher to
actually use.

## 2. The scientific problem

Eelgrass (*Zostera marina* and related species) is a foundational coastal
habitat that supports biodiversity, stabilizes sediment, and stores carbon.
Monitoring eelgrass health typically involves manually reviewing large volumes
of underwater/seafloor imagery to answer questions such as:

- Is eelgrass present in this image?
- What percentage of the area shown is covered by eelgrass?
- What type(s) of cover are present (e.g. eelgrass vs. other substrate/vegetation)?

This manual review does not scale well to large image archives. Eelgrass
Intelligence exists to investigate whether machine learning can assist with
these three tasks, so that CERI researchers can spend more time on ecological
analysis and less time on manual image review.

## 3. Current project status

**Step 1 — repository scaffolding** is complete: directory structure,
package layout, and baseline developer tooling (`pytest`, `ruff`, `mypy`).

Since then, two early ingestion/scaffolding capabilities have been built
and are tested:

- A configurable class registry and segmentation-mask representation
  (`src/eelgrass_intelligence/classes.py`, `masks.py`) — provisional
  development scaffolding, not a confirmed modeling approach. See
  `docs/decisions/0001-segmentation-as-provisional-working-hypothesis.md`.
- Video frame extraction (`src/eelgrass_intelligence/video_frames.py`): a
  reusable function and command-line tool that extracts still frames from
  a local video file at a configurable interval (default: one per
  second), with a traceability manifest. See "Extracting frames from a
  video," below.

**No eelgrass classification, percentage-cover prediction, or trained
model of any kind exists or is validated yet.** No API, frontend,
database, or deployment configuration exists. No CERI dataset has been
received or integrated — frame extraction has only been built and tested
against small, synthetic videos generated locally. See
`docs/data_questions_for_ceri.md` for the list of open questions that must
be answered before any real data pipeline or model work begins.

### Extracting frames from a video

```bash
extract-frames path/to/survey_video.mp4 --output data/interim/my_survey_frames
```

This writes one image per extracted interval (default: 1 per second) plus
a `manifest.json` recording exactly how they were produced — see
`docs/architecture.md`, Layer 1/2, for details and current limitations.
Run `extract-frames --help` for all options.

## 4. Principle: no assumptions about CERI's data or label schema

This project intentionally avoids guessing about:

- What a single labelled "sample" is (a full image, a quadrat photo, a
  transect frame, etc.)
- Whether annotations are image-level tags, bounding boxes, polygons, or
  segmentation masks
- Whether percentage cover is already labelled, and if so, how it was derived
- What "cover type" means, or what the class list is
- Class balance, label quality, or annotation tooling used by CERI

Every one of these must be confirmed directly with CERI before the
corresponding part of the system is designed. Building against an assumed
schema risks producing a pipeline and model that don't match the real data,
and would undermine the scientific rigor this project is meant to have.

## 5. Planned high-level architecture

The system is planned around four conceptual layers (see
`docs/architecture.md` for detail):

1. **Data** — CERI's raw imagery and labels, versioned and kept immutable.
2. **Data processing / validation** — turns raw data into a validated,
   schema-checked form that later stages can trust.
3. **ML** — training, evaluation, and experiment tracking for the
   presence/absence, percentage cover, and cover-type tasks.
4. **Serving / product** — an API and a researcher-facing interface for
   getting predictions on new imagery.

Each layer is only built once the layer beneath it is well understood — see
`docs/architecture.md` and `docs/data_questions_for_ceri.md` for what is
still outstanding.
