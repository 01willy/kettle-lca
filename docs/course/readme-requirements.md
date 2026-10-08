# Required README.md fields

Use Codex to create README.md from your actual code, inputs, choices and results. Include all ten sections below. Give a short substantive summary in the README and link detailed tables, logs and figures by relative path. Use “unknown”, “not calculated” or “not applicable”, with an explanation, when appropriate. Do not invent missing values or present placeholders as results.

Names and emails are collected privately in the course submission form; they are not required in the public README. Do not include course codes, API keys, passwords, private messages or restricted data dumps.

## 1. Study identity and purpose

- Study title, public student/group alias, repository URL, run identifier, study date, study goal and intended comparison.
- Identify the independent or revised run and any Git tag. Submit the final 40-character commit SHA in the form after committing; do not try to embed a README’s own future commit hash. Full name and email belong in the submission form, not this public file.

## 2. Product, declared unit and system boundary

- One manufactured and packaged BC1 1 L plastic electric kettle at the factory gate. State the product specifications, BOM source/date and local file path; check 723 g product plus 137.8 g packaging.
- List included stages/processes, exclusions and cut-offs, geography and reference year. Separate any use-phase or end-of-life extension from the common factory-gate result.

## 3. Foreground inventory and quantitative assumptions

- A table of parameter/input, value, unit, evidence/source and status (sourced, estimated or assumed). Cover material quantities, losses/yields, conversion services, assembly electricity, transport, scrap and prices where applicable.
- Explain finished-mass-to-purchase conversions, reference-flow normalization and unit conversions. Identify which conversion/energy burdens are already included in background data to avoid double counting.

## 4. Background data and matching decisions

- For every input: database, release, dataset name, UUID and version, geography, year, reference flow/amount/unit, source URL, retrieval date and file hash where available. Link the complete mapping table and data manifest.
- Record search queries, alternatives, selection rationale and proxies. Distinguish unit-process inventory, cumulative factors and monetary estimates; record supplier links and external dependencies. For monetary proxies state sector, currency, price year, purchaser/basic-price basis, quantity and price.

## 5. Calculation and impact-assessment methods

- Explain the equations or algorithm (A s = f; g = B s; h = C g, or the actual equivalent), software/solver, process scaling and provider-linking approach.
- State allocation/system model, recycling/scrap treatment, credits, characterization method/version/source, time horizon, biogenic-carbon treatment and flow matching. Report missing upstream providers and uncharacterized flows; do not silently assign zero.

## 6. How to reproduce the analysis

- Repository file map; operating system/runtime and dependency versions; exact installation, data-retrieval and execution commands; expected input/output paths. Include how to open the generated report or tool.
- Document account/API requirements, configuration variable names without values, data permissions, retrieval/caching and seeds. Supply permitted inputs or precise retrieval instructions. State any remaining manual steps or inaccessible dependencies.

## 7. Results, checks and interpretation

- Calculation status; GWP100 total in kg CO2-eq per packaged kettle; complete contribution breakdown (with units), top three contributors, output files and figures. Label baseline/scenario and database/method differences.
- Report unit, mass/balance, supplier-closure, contribution-sum and double-counting checks, including failures. Explain drivers, unsupported conclusions, omitted contributions and limitations. A failed calculation or missing input is not a numerical zero.

## 8. Uncertainty and sensitivity

- State whether uncertainty was calculated. If yes: parameters, distributions/ranges, evidence, correlations/dependence, simulation method, draw count, seed and convergence check.
- Report mean, median and P05/P95 when available; identify the central 90% interval as conditional on the model and assumed distributions. Separate parameter uncertainty, provider/method scenarios and variability between repeated AI runs. If not calculated, state this and why.

## 9. Codex and human decisions

- Codex model/version as displayed, run dates, available settings, consequential prompts and revisions, and links to a curated prompt/decision log. Mark unavailable settings as unknown.
- Identify decisions made by the student, accepted/rejected matches, manual edits, error corrections, assistance received and independently checked outputs. Omit private messages, contact details and credentials.

## 10. Independent and revised runs

- Identify preserved independent outputs and their Git tag or, in a later version, commit SHA. Do not overwrite the original results after seeing classmates’ answers.
- For a revision: prior commit, one changed decision, predicted effect, original and revised numerical results, absolute/percentage difference and explanation. Distinguish corrected errors from defensible modeling alternatives; use not applicable if no revision was made.
