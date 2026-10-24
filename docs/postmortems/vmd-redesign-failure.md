# Post-mortem: VMD portfolio redesign failure

- Date recorded: 2026-10-25 (handoff received 2026-10-24 UTC during development)
- Status: **failure case. The previous redesign was not approved.**
- Source of this record: the user's handoff message. The redesign, its evaluation and the rejected PDF
  were produced **outside this repository and session**. None of those files (the 12-page VMD portfolio,
  `PORTFOLIO 5.pdf`, or the rejected redesign) is available here, so nothing in this document was
  re-measured. Statements below are the user's account, not reproduced results.

## 1. Summary

A 12-page VMD portfolio was evaluated and redesigned as a new PDF. The user's verdict:
- the original page 2 was good, and the revision damaged it;
- the fundamental problems of the remaining pages were not solved.

The user requires every design judgment to rest on official documents and verified evidence.

## 2. Confirmed failures

| Failure | What happened |
|---|---|
| Preservation failure | Original page 2, which the user liked, was modified without sufficient grounds. |
| Proxy-metric misuse | Low saturation, few fonts and wide margins were used as proxies for sophistication. The causal link was never verified. |
| Evaluation-target confusion | Page 3 `AesthetNova-Bold` was rated positively for 61 pt size, contrast and hierarchy. The typeface's own aesthetic suitability was never tested. |
| Uniform style imposition | One preferred style was applied to different pages, losing each page's own strengths and purpose. |
| No verification | "Improvement" was claimed without a controlled original-vs-revision comparison, user approval, preference data or an evidence trail. |
| Weak evidence labelling | Measurable properties, the scope of official standards, research findings and subjective judgment were not separated. |

## 3. Forbidden inferences

- low saturation → sophisticated
- few fonts → good design
- wide margins → luxurious
- large, legible title → beautiful typeface
- geometrically balanced glyphs → aesthetically superior
- similar to a famous brand or typeface → appropriate
- the model's taste → a verified design defect
- one negative user judgment → a universal aesthetic truth

These are listed in code at `edas/modules/typeface.py::FORBIDDEN_INFERENCES` and checked by tests
(`tests/test_typography.py::TestAestheticGuard`, `tests/test_preference_governance.py`).

## 4. What changed in this codebase because of this failure

| Requirement | Implementation | Status |
|---|---|---|
| Evidence record for every proposal | `edas/governance/evidence.py` (`ChangeProposal`, `Evidence`, `ClaimType`, registered `SOURCES`) with every field from §4 of the handoff (`flat()`) | implemented, tested |
| No invented sources | `Evidence.source()` refuses any source id not in `SOURCES`; each source carries its own verification status and note | implemented, tested |
| Aesthetic claims need preference tests | `ChangeProposal.verification_status` is `unverified` for an aesthetic purpose without a verified `controlled_preference_test` record | implemented, tested |
| No proposal without a verified normative basis | `is_actionable()` moves such items to `observations_without_verified_basis` (e.g. the 300 ppi print convention, which has no verified source here) | implemented, tested |
| Approval gate | `edas/governance/gate.py::assert_finalizable` refuses final output with unapproved changes or changes to protected pages | implemented, tested |
| Page 2 preservation | `RunOptions.protected_pages` / CLI `--protect 2` suppresses proposals; `compare_documents()` regression check (text, fonts, embedding, images, colour histogram, appearance, page order) must report no difference on protected pages | implemented, tested on synthetic PDFs; **not run on the real portfolio (file unavailable)** |
| Page 3 typeface separation | `TX01` keeps size, contrast and role apart from the aesthetic verdict (null without validated preference data); `TA*`/`TB*` describe glyph morphology and spacing; `TE01`/`TE02` hold preference models per criterion; Experiment A/B stimuli via `edas typo-experiment` | implemented, tested on a stand-in title; **the real `AesthetNova-Bold` case needs the PDF** |
| No final portfolio before approval | No code path writes a redesigned PDF. Proposals are recommendations only. | by construction |

## 5. Audit of existing evaluation rules (proxy metrics)

| Location | Rule | Classification | Action |
|---|---|---|---|
| `default_config.yaml: objective.lambda / default_lambda` | λ = 1 for every error term | unvalidated weight | `validated: false` is printed with L everywhere. L is never called quality. |
| `technical_targets.effective_ppi_min` (300 ppi) | print-resolution threshold | convention without a verified source | reported as a measurement; proposals demoted to observations |
| `technical_targets.text_contrast_min` (WCAG 4.5:1 / 3:1) | contrast threshold | official standard (web scope), partially verified | kept; applicability to print stated in the source record |
| `modules/composition.py` visual weight model | w = area · contrast · saliency | fixed modelling choice, not learned | labelled `learned: False`; D01/D02 are measurements, not quality |
| `modules/aesthetics.py::INPUTS` | candidate inputs of F01–F16 | hypotheses about relevant features | no direction or weight; outputs null without trained models |
| `modules/bilingual.py` role rule (title ≥ 1.5 × body) | role labelling | labelling heuristic | `estimated`; never used as a quality criterion |
| Anywhere: "fewer fonts", "low saturation", "wide margins", "symmetric", "centred" as good | — | forbidden | none present; aesthetic outputs are null without preference models (tests assert this) |

## 6. Redesign protocol (to apply when the PDF is supplied)

1. Freeze the original: analyse an in-memory copy and never write the source file.
2. Write a per-page purpose specification (information purpose, visual strengths, required elements, user-identified defects) before any proposal.
3. Collect evidence only from sources that were actually checked, and record each one's scope.
4. Judge functional defects and aesthetic preferences separately.
5. Contested typefaces (page 3) get Experiment A and Experiment B stimuli with all other factors controlled.
6. Approval gate: show the original and A/B variants of each target page and collect the user's choice.
7. Minimal intervention: apply only verified problems with approved changes. Otherwise keep the original.
8. Regression check: `compare_documents` with `--protect 2`.
9. Post-evaluation: compare original and revision under identical conditions and label each result measured, preference-tested or unverified.

## 7. Open items

- Supply `PORTFOLIO 5.pdf` (and, if wanted, the rejected redesign) so that the page 2 regression test and the page 3 `AesthetNova-Bold` experiments can run on the real file.
- No preference data exist yet. All preference outputs report `insufficient_data` until judgments are collected.
