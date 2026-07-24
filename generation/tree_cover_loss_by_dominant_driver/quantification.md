# TCL by dominant driver x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks about the driver breakdown of tree cover loss over the whole
2001-2025 record: which driver dominates, what share a named driver or
grouping contributed. Any figure is an area (ha) - or emissions (MgCO2e) -
per driver class over the full period.

Subtype notes:

- `dominant_driver`: ask what the leading/dominant driver of tree cover loss
  is over the whole record. The expected headline is the top driver class
  (with its share/area).
- `driver_share`: ask what share or area a single named driver contributed
  (the row's `notes` records which class, e.g. permanent agriculture). Name
  that one class in the prompt.
- `driver_grouping`: ask about a grouping (the row's `notes` says which -
  drivers of deforestation, temporary disturbances, or all agriculture). The
  expected headline is the combined share/area for that grouping.
- `canopy_threshold`: name the row's threshold explicitly (50% or 75%). The
  question is otherwise a plain driver breakdown.

Judge expectations (for context, not for the wording): the driver taxonomy
and any grouping arithmetic must be correct; the answer covers the whole
2001-2025 record (not a year or range); Unknown is excluded; presentation is
a pie chart or table; the raw loss is called "tree cover loss", not
"deforestation"; volunteered figures within a reasonable tolerance. Model
accuracy is 90.5%, so a caveat is acceptable.
