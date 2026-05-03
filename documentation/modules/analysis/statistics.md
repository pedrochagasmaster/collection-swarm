# `analysis/statistics.py` — strategy ranking

<span class="cs-kicker">collection_swarm/analysis/statistics.py</span>

A tiny module — one frozen dataclass and one function — that turns the
output of `SimulationStore.get_strategy_comparison(profile_id)` into a
typed ranking object.

<dl class="cs-summary">
  <dt>Imports</dt><dd>dataclasses, domain models, the store</dd>
  <dt>Side effects</dt><dd>None (delegates the SQL to the store)</dd>
</dl>

## `StrategyRanking`

```python
@dataclass(frozen=True)
class StrategyRanking:
    profile_id: str
    strategies: list[StrategyStats]

    @property
    def recommended_strategy_id(self) -> str | None:
        return self.strategies[0].strategy_id if self.strategies else None
```

`strategies` is sorted by `mean_payment_probability` descending — the
order is set in the `get_strategy_comparison` SQL. The
`recommended_strategy_id` property is just shorthand for "the top of
the list, or None if the list is empty".

## `compare_strategies(profile_id, store)`

```python
def compare_strategies(profile_id: str, store: SimulationStore) -> StrategyRanking:
    return StrategyRanking(profile_id=profile_id, strategies=store.get_strategy_comparison(profile_id))
```

The function's only job is to wrap the store result in a typed object so
callers don't have to remember which sorted order the SQL returns.

## How the Playbook uses it

```python
rankings = [compare_strategies(profile_id, store) for profile_id in config.profiles]
exclusions = check_exclusions(...)
output_path.write_text(generate_playbook(rankings, exclusions, store), ...)
```

One ranking per Profile. The Playbook walks every ranking and emits a
"Recommended Strategy" section with the table of strategies plus the
best transcript and the objection report.

If a Profile has no completed Simulations,
`StrategyRanking.strategies` is an empty list and the Playbook writes
"No completed simulations." rather than crashing.

## Why mean payment probability

The default ranking metric. The argument:

- It captures the headline outcome the system is supposed to optimize.
- Compliance is enforced separately by the exclusion gate, so a
  high-`payment_probability` strategy that fails compliance is filtered
  out before ranking.
- Simple, transparent, and easy to explain to non-technical
  stakeholders.

If you want to rank by a different metric, swap the `ORDER BY` in
`SimulationStore.get_strategy_comparison` and update the property.
