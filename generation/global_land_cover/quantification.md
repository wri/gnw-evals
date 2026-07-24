# Global land cover x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure that the ground-truth composition or
change table can verify: hectares of one land-cover class (2024 snapshot),
of agricultural land (2024 snapshot, combined classes), or of a
class-to-class transition (2015 to 2024). No wording names a year; the
product fixes the periods.

Subtype notes:

- `class_area`: ask how much of the AOI is a single named class in the
  current land cover data. The expected headline is that class's area_ha in
  the 2024 composition. Keep the land-cover framing (shared rule 3),
  especially for the tree cover class.
- `agriculture_combined`: ask about agricultural land generically without
  naming classes (shared rule 7). The expected figure is cropland +
  cultivated grasslands combined from the 2024 composition.
- `change_area`: ask how much land changed from the row's start class to its
  end class (both listed in `land_cover_classes` as `start;end`), or out of
  a single class where only one is listed. The expected figure comes from
  the change table (land_cover_class_start, land_cover_class_end, area_ha).
  Say "changed", never "lost" or "converted".

Judge expectations (for context, not for the wording): the headline figure
must match ground truth within 5% in any reasonable unit; composition
answers are expected to present a pie/breakdown of the 2024 classes, change
answers a table of start-class x end-class transitions; caveats that this
is land cover change rather than land use change (and that only start- and
end-states are represented, not intra-annual changes) are correct and must
not be penalised.
