## Summary

<!-- Required. What changes and why. The PR title and this body become the squash commit on main. -->

## Related issue

<!-- Optional. e.g. "Closes #12". Leave empty if there is none. -->

## Testing

<!-- Required. How you checked it: commands run, tests added, what you could not test. -->

## Ground rules

<!-- Tick what applies; leave unticked lines that don't apply. See AGENTS.md. -->

- [ ] No look-ahead: strategy, allocator and overlay code reads data only through the data window (ADR 0003)
- [ ] Raw prices for fills, as-of adjusted history for strategies (ADR 0002)
- [ ] Point-in-time universe: no tickers filtered with knowledge of the future (ADR 0001)
- [ ] No market data, run recordings, keys or `.env` committed (ADR 0007)
- [ ] Deterministic: no unseeded randomness or wall-clock dependence
- [ ] Names follow the glossary in `CONTEXT.md`
- [ ] New or changed decisions recorded as an ADR
