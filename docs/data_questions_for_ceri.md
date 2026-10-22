# Open Questions for CERI

This document tracks information we need from CERI before making any
decisions about data pipelines, label schemas, or model formulation. Nothing
in this project should assume answers to these questions — they should be
confirmed directly with CERI and this document updated accordingly.

**Note (preliminary information received):** CERI has reported roughly
6,000 photos labelled at least once, and 20,000–30,000+ unlabelled photos;
that existing labels reportedly include an estimated eelgrass percentage
cover and/or a category such as rocky, sandy, algae, or unclear; and that
many photos have assessments from at least three student reviewers. These
are preliminary figures, not a confirmed dataset schema — most of the
specific questions below (exact sample definition, label format, whether
categories are mutually exclusive, how multi-reviewer disagreement is
resolved, grouping/metadata structure) remain open and are not answered by
this note.

## About the imagery

- What is a single labelled "sample"? (a full image, a quadrat photo, a
  transect frame, a video frame extraction, etc.)
- What is the capture protocol? (diver-operated camera, fixed rig, drop
  camera, quadrat-based, etc.)
- What is the typical image resolution, format, and file size?
- What metadata is available per image? (site, date/season, depth, GPS,
  camera/sensor type, lighting/turbidity conditions)
- How many labelled images exist in total, and how many per task (if
  different)? How many unlabelled images exist?
- Can imagery leave CERI's own systems/storage? Are there data-sharing,
  privacy, or sensitive-location constraints (e.g. protected habitat
  coordinates that must be redacted)?

## About presence/absence labels

- Are presence/absence labels image-level tags, or derived from something
  richer (e.g. bounding boxes or masks)?
- How was presence/absence determined — by a human reviewer, and if so,
  by how many, and with what agreement?

## About percentage cover

- Does a percentage cover value already exist per image/sample?
- If so, how was it derived? (e.g. expert visual estimate, point-intercept
  transect method, computed from a segmentation mask)
- If not, would CERI need to produce new segmentation-style labels for this,
  or is percentage cover out of scope until such labels exist?

## About cover-type

- What is the actual list of cover types CERI cares about? (e.g. species-
  level, functional-group level, substrate-level — this is not something we
  should define ourselves)
- Are cover types mutually exclusive per sample, or can multiple types
  co-occur in one image?
- Is there an existing taxonomy or labelling guide CERI already uses?

## About label format and tooling

- What annotation tool(s) were used, if any? (e.g. CVAT, Labelbox, VIAME,
  spreadsheets, GIS shapefiles)
- In what file format are labels stored, and how are they linked to image
  files?
- Was there any quality control or inter-annotator agreement process?

## About structure and evaluation

- Are multiple images taken from the same site, transect, or day? (This
  affects how train/validation/test splits must be constructed to avoid
  leakage.)
- What is the class balance for each task, roughly? (e.g. how rare is
  eelgrass presence, how rare are minority cover types)
- Were any of CERI's existing photos extracted from video? If so, at what
  interval, and is there a way to identify which photos came from the same
  video/survey, so splits can group them rather than split them apart (see
  the adjacent-frame leakage risk noted in `docs/project_workflow.md`,
  Stage 5)?

## About survey and geographic metadata (community-survey direction)

- What geographic/location metadata, if any, should be captured per
  survey or per video upload (e.g. coordinates, site name), and are there
  sensitive-location constraints on storing or displaying it (see "About
  the imagery" above)?
- What constitutes a single "survey" for grouping purposes — one video
  upload, one outing, one site visit? This affects both leakage-aware
  splitting (Stage 5) and how results are grouped for review/export
  (Stage 9).
- Does CERI have requirements for how community-submitted surveys (as
  opposed to CERI's own labelled photos) should be handled, reviewed, or
  trusted differently?

## About intended use

- Will researchers use this on new imagery immediately after a survey, or
  on batches of archived imagery, or both?
- Are there existing baselines, heuristics, or prior analyses CERI has
  already tried that we should be aware of?

## Status

All of the above are currently **unanswered**. No part of this project
should proceed as if any of these questions has a known answer.
