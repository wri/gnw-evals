# SBTN Natural Lands Map x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks which of two countries has more natural land (or a higher
natural share). The verifiable core is the comparative claim's direction;
volunteered figures must match ground truth. No wording names a year; the
map is a fixed 2020 baseline. Two-period comparisons do not exist for this
dataset: there is only one snapshot, so `two_country` is the only subtype.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;IDN`).
  Both must appear in the prompt. The row's judge_note says which axis is
  compared:
  - **absolute extent** rows ask which country has more natural land (or
    more non-natural land, where the judge_note says so): the Natural (or
    Non-natural) row's area_ha per country.
  - **share** rows ask which country is more natural *proportionally*
    ("which has the higher share of natural land"): Natural / (Natural +
    Non-natural) per country. The wording must make the proportional
    framing explicit so it cannot be read as an absolute-area question.

Judge expectations (for context, not for the wording): direction must be
correct; cited figures within 5%; figure-free but directionally correct
answers pass with unquantified=true; the known overestimation caveat is
acceptable and must not be penalised.
