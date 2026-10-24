# Implementation status (verified vs. not implemented)

Test suite: `python -m unittest discover -s tests -t .` — 43 tests, all passing in the build environment
(Python 3.13, pypdfium2 5.13, NumPy 2.5, Pillow 12, reportlab 5).

## Implemented and tested

| Area | What | Verification |
|---|---|---|
| Schema | p_i = (D,U,F,N,T,E,C,V), output schema §14, null for unmeasured values, NaN→null, raster→`estimated` | unit tests |
| PDF engine | PDFium extraction of glyphs (tight/loose boxes, origins, effective size), fonts (embedded flag, outlines), images (clip, ppi, crop), vectors, forms; CropBox/Rotate → top-left points | synthetic ground truth, rotated page test |
| Raster fallback | blank / flattened (image-only) documents → segmentation estimates | tests |
| A Layout A01–A20 | grid fit, alignment, margins, occupancies (exact union), distances, IoU, NN clustering, whitespace matrix, complexity, grid consistency | ground truth tests (grid n, c, g, margins, occupancy) |
| B Typography B01–B20 | sizes, ratios, glyph geometry from outlines, spacing, leading, families, entropy, shape similarity, consistency, WCAG contrast; B19/B20 null without OCR/reference | tests |
| BK bilingual BK01–BK13 | script classes, font identification status, Hangul 6-type stratified geometry, Latin classes, visual size, baseline, harmony vector h, spacing by script, hierarchy, ink vs. complexity, installed alternatives with licence fields | tests (visual size ≠ point size; complexity relation computed) |
| Typeface dimensions TA/TB/TC/TE/TX | morphology z_f, consistency, optical spacing, overshoot, size dependence, separation report; aesthetic outputs null without data | AesthetNova-type regression on a stand-in title |
| Counterfactual Experiments A/B | same-rasteriser stimuli, equal cap height, page redraw with text removed, manifests | tests |
| Preference learning | judgment schema (5 typeface criteria + bilingual criteria), BT with Davidson ties, hierarchical (rater deviations), feature model, bootstrap, OOD; agreement (Krippendorff α), page/project-grouped CV, calibration, rater differences, aesthetic–readability association | simulation tests |
| A/B interface | self-contained HTML, hidden fonts, randomised sides, tie / cannot judge, JSON export → `prefs-import` | browser smoke test (no JS errors) |
| C Photography C01–C20 | luminance, contrast, saturation, entropies, sharpness, edges, saliency subject, horizon, symmetry, crop, CIEDE2000, style consistency | pipeline runs |
| D Composition D01–D16 | weight model, centre deviation, symmetry, size contrast/entropy, alignment consistency, graph clustering, repetition, saliency entropy, focal points | pipeline runs |
| E Rhythm E01–E14 | transitions, standardised Δ_p, autocorrelation, period candidates (flagged), cosine similarity, colour/type transitions, state entropy, sign changes | pipeline runs |
| F Aesthetics F01–F16 | input schemas; F13 consistency; F14/F15 with a reference profile; others null (`no_model`) | tests (null without data) |
| Reference profiles | quantile targets, robust τ, bootstrap CI, comparison and errors | pipeline runs |
| Evaluation | Q_technical constraints with evidence status; Q_perceptual/Q_functional null; L with `validated:false` | tests |
| Governance | evidence records with registered sources only, actionability rule, approval gate, protected pages, regression comparison | tests |
| Exports | JSON, CSV, HTML (overlays, saliency, rhythm charts), PDF report, spec registry, CLI | smoke tests |

## Not implemented / not verified

| Item | Reason |
|---|---|
| Analysis of `PORTFOLIO 5.pdf` (all §17 outputs) | File not available in the repository or environment. |
| Real page 2 regression and page 3 `AesthetNova-Bold` experiments | Need the original PDF. |
| Web reference search (Openverse / Brave / Google CSE providers, galleries, re-ranking, dataset) | Not built yet. Researched: Openverse reachable without a key (20/min, 200/day anonymous); Brave and Google endpoints blocked in this environment; Google CSE closed to new customers (ends 2027-01-01); Bing Search APIs retired 2025-08-11. |
| Streamlit dashboard | Streamlit/Plotly not installable here (package index blocked); HTML report is the dashboard substitute. |
| Semantic image embeddings (C19), OCR legibility (B19), learned visual font embeddings | No model weights or OCR engine available offline. |
| CFF-flavoured OpenType candidates (e.g. Inter .otf) | Outline route unsupported; reported as `not_measured`, never approximated. |
| Kerning from GPOS in counterfactual specimens | Specimens use nominal advances (recorded); as-set spacing of the original is reproduced separately. |
| Mood/sensory module | Requested last; design questions open (see README). |
