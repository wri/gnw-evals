# TCL by dominant driver x comparison

Read `_shared.md` first; those rules always apply.

The prompt asks how two countries' driver profiles differ over the whole
2001-2025 record: which country's dominant driver is which, or which country
lost more tree cover to a given driver. The verifiable core is the
comparative claim's direction or the per-country dominant-class
identification; any volunteered figures (ha) must match ground truth.

Subtype notes:

- `two_country`: the row's `aoi_ids` has both countries (e.g. `BRA;IDN`).
  Two shapes, chosen by the row's `notes`:
  - "which country's dominant driver": ask what each country's dominant
    driver of tree cover loss is, or to compare their dominant drivers.
  - "driver focus: <class>": ask which of the two countries lost more tree
    cover to that named driver over the whole record.
  Both countries must appear in the prompt; the whole-record basis applies to
  both. Where a row sets a canopy threshold, it applies to both.
- Near-zero rows (CRI, GBR): wording is normal; the small magnitudes are the
  test - the dominant-class identification or direction must still be correct.

There are no trend or period-split rows: the dataset is a single whole-record
aggregate and cannot be split into comparable sub-periods.

Judge expectations: the dominant-class identification or comparative
direction must be correct; the answer covers the whole 2001-2025 record;
Unknown is excluded; the raw loss is called "tree cover loss", not
"deforestation"; cited figures within tolerance.
