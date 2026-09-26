# Open Questions for CERI

This document tracks information we need from CERI before making any
decisions about data pipelines, label schemas, or model formulation. Nothing
in this project should assume answers to these questions — they should be
confirmed directly with CERI and this document updated accordingly.

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

## About intended use

- Will researchers use this on new imagery immediately after a survey, or
  on batches of archived imagery, or both?
- Are there existing baselines, heuristics, or prior analyses CERI has
  already tried that we should be aware of?

## Status

All of the above are currently **unanswered**. No part of this project
should proceed as if any of these questions has a known answer.
