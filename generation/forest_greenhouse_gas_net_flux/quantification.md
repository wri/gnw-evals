# Forest GHG net flux x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for the single whole-period net GHG flux total (MgCO2e) that
the ground-truth table can verify, or whether the country's forests are a net
sink or net source over the record.

Subtype notes:

- `net_flux`: ask for the total net greenhouse gas flux from the country's
  forests over the whole model period. The expected headline is the net flux
  total in MgCO2e (a single figure, emissions minus removals).
- `net_sink_source`: ask whether the country's forests are a net carbon sink
  or a net source (and, optionally, by how much). The answer is determined by
  the sign of the net flux total: net-negative = net sink, net-positive =
  net source.
- `canopy_threshold`: name the row's threshold explicitly (50% or 75%). The
  question is otherwise a plain net-flux quantification.

Judge expectations (for context, not for the wording): the headline figure
is the whole-period net flux total in MgCO2e (or an honest conversion) and
must match ground truth within a reasonable tolerance; no annualising (no
divide-by-25); net sink/source language must follow the sign; a split-bar
presentation (emissions positive, removals negative) is expected.
