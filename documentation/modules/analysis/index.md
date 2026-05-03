# Analysis

<span class="cs-kicker">collection_swarm/analysis/</span>

The read-side of the system. Four small files that turn the contents
of `runs` into rankings, exclusions, objection counts, and the
Markdown Playbook.

| File                                | Public surface                                                |
| ----------------------------------- | -------------------------------------------------------------- |
| [`statistics.py`](statistics.md)    | `StrategyRanking`, `compare_strategies(profile_id, store)`     |
| [`compliance.py`](compliance.md)    | `ComplianceExclusion`, `check_exclusions(...)`                 |
| [`objections.py`](objections.md)    | `ObjectionReport`, `extract_objections(transcripts, taxonomy)` |
| [`playbook.py`](playbook.md)        | `generate_playbook(rankings, exclusions, store)`               |

The `analyze` CLI command and the dashboard's `GET /api/playbook`
endpoint both compose the four together. There's no caching layer;
everything is recomputed on demand from the SQLite store.
