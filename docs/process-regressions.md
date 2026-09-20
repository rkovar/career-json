# Career process regression map

These public contracts use fictional people and sources. Pattern checks are bounded
and may need adjudication; their success is not a claim of general semantic accuracy.
The private reference and its interview transcript are never public test fixtures.

| Contract | Evidence | Gate and limit |
| --- | --- | --- |
| formal-title | leadership: exact role title; collaboration: separate roles | Title inflation mutation fails. |
| metric-semantics | leadership: Juniper cumulative pipeline and timeframe | Revenue mutation fails, including a wrong metric value paired with a correct pipeline basis. This is a bounded fictional check, not general entailment. |
| personal-build | leadership: Cobalt personal build and human approval | Replacing build with sponsorship fails. |
| team-credit | leadership: Larch; collaboration: Cedar | Sole-credit and shared-ownership mutations fail. |
| scope-and-time | leadership: peak/current staff and wider recognition | Wrong headcount mutation fails; scope may live in constraints. |
| founded-or-inherited | leadership: Larch versus support | Invented founding mutation fails. |
| separate-audit-scopes | leadership: Cypress versus triage | Positive outcome must stay with its project. |
| retain-unmeasured-work | operations: Moth; transition: Maple | Dropping a contribution or inventing savings fails. |
| authorship-roles | early-career: Aster and Sedge | Sole-author mutation fails. |
| evidence-scope | all five sources are personal accounts | Upgrading them to external verification fails; receipt tests separately verify independent support. |
| date-precision | transition: year-only dates; operations: conflicting months; run_tests.py | Invented months and hidden conflicts fail. Validator warns on inferred dates outside the linked role, allowing overlapping year precision and unknown role ends. |
| credential-status | leadership: lapsed licence; collaboration: training | Current certification inflation fails; explicit denial is calibrated. |
| invention-status | transition: Elm co-invention, unfiled | Sole inventor/granted patent mutation fails. |
| presentation-preferences | leadership: hands-on work plus leadership | Preference omission is detected separately from achievement presence. |
| privacy-and-withholding | all profiles; durable deferred/declined questions | New facts stay private; withheld questions do not become required. |
| answer-context | test_process_state.py; test_career_creation.py | Short answers cannot verify another record; proposal context and stale revision guards persist. JSON question/answer pairs stay together; conflicting imports cannot silently reuse an old decision. |
| incremental-import | test_career_creation.py; run_journeys.py | Reimports, later privacy restrictions, corrected wording and unrelated work are preserved. |
| untrusted-and-targeting-input | early-career footer; collaboration/operations job descriptions | Job-only skills fail; source instructions are treated as data. Inspect the live result for instruction following. |
| derived-consistency | test_process_state.py; run_journeys.py | Each limitation is reassessed; stale caveat is replaced while residual unknown remains. |
| coverage-not-keywords | five profiles; split-claim calibration; private comparison | Checks allow paraphrases and split/merged records; broad semantic coverage still needs inspection. |
| existing-achievement-sources | collaboration: project report and resume; test_career_creation.py | Registering an unused source fails coverage. The extra source must support Cedar, with its voluntary-trial scope retained. Batches retain pending sources. |
| confidence-after-edit | test_career_creation.py | Full-candidate and field revisions cannot retain verification for an edited claim without reassessment. |
| confirmation-after-reassessment | test_career_creation.py | New strength wording becomes proposed and prompts review; identical reassessment preserves state. |
| readable-qualifications | test_career_page.py | Publication constraints, context and escaped excerpts survive the friendly projection. |
| optional-followups | test_process_state.py | Legacy enrichment stays optional; typed factual questions take priority. Reclassification preserves answers and deferrals. |
| retired-metrics | test_career_creation.py; test_process_state.py | Explicitly retired metrics cannot be staged as current claims; history is retained. Missing measurement or corroboration alone is allowed. |

`test_source_pack_evaluation.py` and `test_process_state.py` calibrate the source
checks. `test_career_creation.py` exercises real persistence and recovery. Live
source generation is opt-in via `run_editorial_scenarios.py`; prepared candidates
are never reported as successful model extraction. Original failure reports must
be retained when checks or instructions change.
