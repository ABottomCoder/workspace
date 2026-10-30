"""US macro days on which Tidewatch does not enter at all (checked by premarket and both entries).

Three event types only: FOMC rate decisions (statement day), CPI releases and non-farm payrolls.
Nothing else is listed (Fed officials' speeches, FOMC minutes, testimony, PPI, retail sales, ...),
so those days trade normally.

Maintained by hand from the agencies' published schedules.
"""
from datetime import date

FOMC_DECISIONS_2026 = [
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
    date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
]

CPI_2026_H2 = [
    date(2026, 7, 14), date(2026, 8, 12), date(2026, 9, 11), date(2026, 10, 14),
    date(2026, 11, 13), date(2026, 12, 10),
]

NFP_2026_H2 = [
    date(2026, 7, 2), date(2026, 8, 7), date(2026, 9, 4), date(2026, 10, 2),
    date(2026, 11, 6), date(2026, 12, 4),
]


def macro_event(d: date):
    for days, name in ((FOMC_DECISIONS_2026, "FOMC decision"), (CPI_2026_H2, "CPI"), (NFP_2026_H2, "NFP")):
        if d in days:
            return name
    return None
