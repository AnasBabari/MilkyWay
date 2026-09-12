# Frozen engine versions

- `mw_0_1/` and `mw_0_2/`: historical baselines used by measurement tools and tests.
- `final_packaged/`: byte-exact extraction of the last documented TM ZIP. Its
  manifest records every original member hash. It includes the required compact
  value model omitted from the old loose experiment tree.

The compiled snapshot is historical evidence and is excluded from maintained-source
Ruff checks; it is not reformatted to erase its recorded typing/style limitations.
Do not edit it to alter an archived result. The root Python engine remains a
separate implementation. See [provenance](../docs/BUILD_PROVENANCE.md).
