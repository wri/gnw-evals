# Tree cover gain x quantification

Read `_shared.md` first; those rules always apply.

The prompt asks for a single figure that the ground-truth table can verify:
hectares of cumulative tree cover gain for one of the four fixed periods.

Subtype notes:

- `gain_total`: ask "how much/how many hectares of tree cover gain" over the
  full cumulative 2000-2020 period. The expected headline is the cumulative
  gain area (ha) for 2000-2020.
- `period_gain`: ask about cumulative gain for one of the three shorter fixed
  windows (2005-2020, 2010-2020 or 2015-2020 - the row's `start_year`/
  `end_year`). Ask for the cumulative total to 2020; never ask to decompose
  the window into sub-intervals.

Judge expectations (for context, not for the wording): the headline area
must match ground truth within a reasonable tolerance in any sensible unit;
the answer must use "tree cover gain" and must not call it "restoration";
if the wording anywhere brushes net change, the agent must refuse to combine
gain with loss.
