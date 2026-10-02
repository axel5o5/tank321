"""Shared, deterministic cohort definitions for output tables and headlines."""


def bottom_by_total(projections, n=8):
    """Lowest market totals, breaking cutoff ties alphabetically by team code.

    Projection CSVs are ordered by their estimated incentive. That output order
    must not decide which tied team enters a market-total-defined cohort.
    """
    return projections.sort_values(['win_total', 'team'], kind='stable').head(n)
