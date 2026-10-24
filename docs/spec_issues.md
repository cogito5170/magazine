# Specification issues and resolutions

The mathematical definitions were kept. Where the specification was contradictory or incomplete, the
issue and the chosen resolution are listed here (spec instruction §0).

| # | Item | Issue | Resolution in code |
|---|---|---|---|
| 1 | C16, D3, D4 | Named "symmetry" but defined as a "normalised difference" between original and mirror. D5 "asymmetry = complement of symmetry" would then equal 1 − difference, i.e. symmetry again. | Value = symmetry S = 1 − d; d is kept in `details`; D5 = d (= 1 − S). |
| 2 | E feature vector `x_p = [D_image, D_text, D_white, B_p, H_p, …]` | `H_p` also denotes page height in §2. | Interpreted as an entropy feature: saliency entropy D15. |
| 3 | B10 letter spacing | "horizontal distance between adjacent glyphs" can mean ink-to-ink or advance-box distance. | Value = tight (ink) gap / size; advance-box (tracking + kerning) variant in `details`. |
| 4 | B12 leading ratio | Dividing the baseline distance of *every* line by the body size s_b makes headline leading meaningless. | Computed on body-text blocks (size within 5 % of s_b). |
| 5 | B5 stroke contrast | `w_max / w_min` of a raster stroke-width distribution is dominated by terminals and anti-aliasing. | Configured quantiles (q90 / q10). |
| 6 | A3 alignment error | `x_i` is undefined for multi-edge objects. | Left edges vs all vertical grid lines (column starts and ends); right-edge variant in `details`. |
| 7 | A2 grid | `W = m_l + m_r + n c + (n-1) g` has more unknowns than one page can determine; larger n always fits better. | n chosen by the minimum binomial tail probability of edge inliers under uniformly random edges (no complexity weight). Holds the identity by construction. |
| 8 | C17 crop retention | The "original source" is usually unavailable; the embedded image may already be cropped. | Ratio w.r.t. the embedded XObject, with a note; raster pages: `not_computable`. |
| 9 | D1 visual weight | The spec requires a weight model but defines none. | w = area · luminance contrast · relative saliency, fixed and labelled `learned: False`. |
| 10 | F02 input `D_decoration` | No measurement exists for "decoration". | Omitted from the model input list until a measurement is defined. |
| 11 | §9 objective L | λ weights have no validated values. | Configurable, default 1, always reported with `validated: false`; not used as quality. |
| 12 | Technical target "image resolution" | No verified source for a ppi threshold was found. | Measured and reported; proposals demoted to observations (`is_actionable`). |
| 13 | WCAG contrast for print | WCAG is normative for web content, not print. | Used as a legibility reference with its scope recorded; source verification `partially_verified`. |
