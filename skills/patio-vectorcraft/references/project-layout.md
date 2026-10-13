# Project layout

```
<project>/                 read root
  brief/                   the request: dimensions, material, quantities, deadline, photos
  sources/                 files received, copied in (never linked)
  out/                     write root; everything the agent produces
    S01_long-shelf_1450x170mm_revA.vectorcraft
    S01_long-shelf_1450x170mm_revA.svg
    S01_long-shelf_1450x170mm_revA_review.pdf
    README.md              hand-off note
  project-record.md        from templates/project-record.md, filled by the studio
```

Naming: `S<two digits>_<part-slug>_<W>x<H>mm_rev<letter>`. Parts in one job share the S number and get their own slug. Artboards use the same names. Revision letters only move forward; keep earlier revisions in `out/`.
