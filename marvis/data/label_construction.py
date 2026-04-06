"""Determination 0/1 Bad tab to construct kernel(C1 Tab Structure and Maturity Tool).

The most important precursor to the credit wind modeling: from one"Loans×Period"Repayment of the/DPD Long watch, according to business.
**Observation period/ Performance period/ - It's a bad caliber.** Construct a 0/1 Target (bad)=1).This module is a pure core of functions
(No touch.IO,No touch subprocesses), output of the same input for which the same input is required (in the case of the same output)INV-1 (c) Determination).

Enter long table ()DPD The contract - follow-up``marvis.data.performance`` Existing"Show time."Columns
Promise. One line.= A loan in one of the places.MOB(month-on-book)Overdue status:

- ``id_col``:Loan only key.
- ``mob_col``:AgeingMOB(non-negative integers; 0=The government has also been making a financial contribution to the government.
- Overdue strength is two-to-one:
  - ``dpd_col``:Number of days overdue (indays past due);Caliber threshold``threshold_dpd`` It's days.
  - ``status_col`` + ``states``:Dispersed overdue drums (e.g.,C/M1/M2/M3+),A barrel."From the good to the bad."
    Semantic order is passed by the caller``states`` Visible (machine does not guess, withperformance/roll_rate (a) Unanimously;
    Caliber threshold``threshold_status`` Yes.``states`` One of the barrels, hit.=Reaching or breaking the barrel.
- ``cohort_col``(Optional, maturity check: Loanvintage(YYYY-MM),Determines whether the performance period is closed.

Stereotype (%2)bad definition)Three elements:

- Observation period``observation_window``:Watch the end of the windowMOB.The characteristics are known at this point; the label is only after this point.
- Performance period``performance_window``:How many more do you see back after the observation point?MOB Deciding whether it's bad.
- Overdue threshold:``threshold_dpd``(Like 30/60/90 Days) or``threshold_status``(Like"M2");
  Optional``at_mob`` Which one is specified?MOB (e.g.,"90+@mob6"),Default=Show the end end.

Label for a loan: in the performance window``(observation_window, at_mob]`` Internal**Once.**Reaching the bad threshold
→ 1;Not a full trip.→ 0;Unobserved complete performance period (lack of sufficient in-window)MOB (Observations)→ It's not bad.
Tag asNaN(Not quietly as a good customer; downstream.NaN The label door determines to discard or supplement data.

Output Carrie**Stereometric metadata** ``BadDefinition``,In.T3 Blood (Legitimate)NumberProvenance It's...params).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from marvis.validation.vintage import _cohort_key


@dataclass(frozen=True)
class BadDefinition:
    """Stereometric metadata (advanced)T3 Blood.params Part;certainty recalculated)."""

    #: Overdue strength caliber:"dpd"(days) or"status"(- Dispersed buckets.
    threshold_kind: str
    #: Threshold:dpd (a) Values of serialization of the caliber of the number of days;status Cal. barrel name (Cyber)states The government has been monitoring the situation.
    threshold: float | str
    #: Watch the end of the windowMOB(Characteristics are known; labels are only seen after.
    observation_window: int
    #: Length of performance period (after observation point)MOB I'm not sure.
    performance_window: int
    #: DecisionMOB(Like 90+@mob6 6th session= observation_window + performance_window.
    at_mob: int
    #: Impact definition:"ever"(The performance window has been corrupted; the only currently supported calibre.
    hit_rule: str = "ever"

    def to_dict(self) -> dict:
        return {
            "threshold_kind": self.threshold_kind,
            "threshold": self.threshold,
            "observation_window": self.observation_window,
            "performance_window": self.performance_window,
            "at_mob": self.at_mob,
            "hit_rule": self.hit_rule,
            "label": self.label_expression(),
        }

    def label_expression(self) -> str:
        """Readable bad calibre expressions, such as``90+@mob6 (obs=0, perf=6)``."""
        if self.threshold_kind == "dpd":
            head = f"DPD{int(self.threshold)}+@mob{self.at_mob}"
        else:
            head = f"{self.threshold}+@mob{self.at_mob}"
        return f"{head} (obs={self.observation_window}, perf={self.performance_window})"


@dataclass(frozen=True)
class LabelConstruction:
    """Label construction result: 0 per line of loans/1(orNaN)Objective+ Caliber metadata+ Count."""

    #: Line one loans:id_col + cohort((if so)+ target Column (0)/1/NaN).
    frame: pd.DataFrame
    #: target Listed.
    target_col: str
    definition: BadDefinition
    n_loans: int
    n_bad: int
    n_good: int
    #: Number of loans with unconstructed performance periods that cannot be determined (%)target=NaN).
    n_unmatured: int


def _resolve_threshold_kind(
    *,
    dpd_col: str | None,
    status_col: str | None,
    threshold_dpd,
    threshold_status,
    states,
) -> tuple[str, str | None, tuple[str, ...]]:
    """Identification of late strength caliber, return``(kind, resolved_col, state_order)``."""
    has_dpd = dpd_col is not None and threshold_dpd is not None
    has_status = status_col is not None and threshold_status is not None
    if has_dpd and has_status:
        raise ValueError(
            "I'm also giving you a deal.dpd caliber(dpd_col+threshold_dpd) andstatus caliber"
            "(status_col+threshold_status);There's only one choice."
        )
    if not has_dpd and not has_status:
        raise ValueError(
            "Lack of late-intensity calibre: pleasedpd_col+threshold_dpd(Number of days)"
            "orstatus_col+threshold_status+states(- Dispersed buckets."
        )
    if has_dpd:
        return "dpd", str(dpd_col), ()
    state_order = tuple(str(state) for state in (states or ()))
    if not state_order:
        raise ValueError("status The calibre must be providedstates(The barrel's in good to bad order.")
    if len(set(state_order)) != len(state_order):
        raise ValueError("states Contains a duplicate barrel withdrawal value; only once per barrel can occur.")
    if str(threshold_status) not in state_order:
        raise ValueError(
            f"threshold_status={threshold_status!r} No, I'm not.states={list(state_order)} Inside."
        )
    return "status", str(status_col), state_order


def _hit_mask_dpd(values: pd.Series, threshold: float) -> np.ndarray:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    # NaN DPD(This issue is not counted; it is hit by a number of days that the threshold is reached or exceeded.
    return np.where(np.isfinite(numeric), numeric >= float(threshold), False)


def _hit_mask_status(
    values: pd.Series, threshold: str, state_order: tuple[str, ...]
) -> np.ndarray:
    # Hit.= Battery is worse than or equal to the threshold drum (in thestates Index in the good to bad order>= threshold index).
    rank = {state: index for index, state in enumerate(state_order)}
    threshold_rank = rank[str(threshold)]
    observed = values.map(lambda v: rank.get(str(v)) if pd.notna(v) else None)
    return np.array(
        [False if r is None else (r >= threshold_rank) for r in observed.tolist()],
        dtype=bool,
    )


def construct_label(
    df: pd.DataFrame,
    *,
    id_col: str,
    mob_col: str,
    observation_window: int,
    performance_window: int,
    dpd_col: str | None = None,
    threshold_dpd: float | None = None,
    status_col: str | None = None,
    threshold_status: str | None = None,
    states: list[str] | tuple[str, ...] | None = None,
    at_mob: int | None = None,
    cohort_col: str | None = None,
    target_col: str = "target",
) -> LabelConstruction:
    """FromDPD Long Table Construct 0/1 Bad label (see module)docstring The #GazaAs are the most popular in the world.

    Determination: same given``df`` Results consistent with the same calibre parameters, outputs by category.
    """
    if observation_window < 0:
        raise ValueError("observation_window must be non-negative")
    if performance_window < 1:
        raise ValueError("performance_window must be >= 1")
    resolved_at_mob = observation_window + performance_window if at_mob is None else int(at_mob)
    if resolved_at_mob <= observation_window:
        raise ValueError("at_mob must be greater than observation_window")

    kind, value_col, state_order = _resolve_threshold_kind(
        dpd_col=dpd_col,
        status_col=status_col,
        threshold_dpd=threshold_dpd,
        threshold_status=threshold_status,
        states=states,
    )
    required = [id_col, mob_col, value_col]
    if cohort_col:
        required.append(cohort_col)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")

    work = df[required].copy()
    work["_marvis_mob"] = pd.to_numeric(work[mob_col], errors="coerce")
    finite_mob = work["_marvis_mob"].dropna()
    if ((finite_mob < 0) | (finite_mob % 1 != 0)).any():
        raise ValueError("MOB must be non-negative integers")
    work = work[work["_marvis_mob"].notna()].copy()
    work["_marvis_mob"] = work["_marvis_mob"].astype(int)

    if kind == "dpd":
        work["_marvis_hit"] = _hit_mask_dpd(work[value_col], float(threshold_dpd))
    else:
        work["_marvis_hit"] = _hit_mask_status(work[value_col], str(threshold_status), state_order)

    # Performance window= Watchpoint and final.MOB:(observation_window, at_mob].
    in_window = (work["_marvis_mob"] > observation_window) & (work["_marvis_mob"] <= resolved_at_mob)
    window = work[in_window]

    # Each loan: a hit in the performance window-> Bad; seen to judgeMOB Or far away and never hit.-> Okay;
    # No determination observedMOB((Insisting period)-> It's not bad.(NaN).
    # Hit test only for the performance window(observation_window, at_mob] (a) Lines within;
    # The maturity test is used for theloan **Full**(Notat_mob The biggest observations on the top line.MOB —— I've seen it.
    # at_mob Or grow up after that, not becauseat_mob The issue coincided with the absence of a business (a common absence of monthly service documents) and the miscalculation was premature.
    ids = pd.Index(pd.unique(work[id_col]))
    ever_hit = window.groupby(id_col)["_marvis_hit"].any()
    max_mob_observed = work.groupby(id_col)["_marvis_mob"].max()

    target_values: list[float] = []
    n_bad = n_good = n_unmatured = 0
    for loan_id in ids:
        hit = bool(ever_hit.get(loan_id, False))
        matured = int(max_mob_observed.get(loan_id, -1)) >= resolved_at_mob
        if hit:
            target_values.append(1.0)
            n_bad += 1
        elif matured:
            target_values.append(0.0)
            n_good += 1
        else:
            target_values.append(float("nan"))
            n_unmatured += 1

    out = pd.DataFrame({id_col: list(ids)})
    if cohort_col:
        cohort_by_id = work.drop_duplicates(subset=[id_col]).set_index(id_col)[cohort_col]
        out[cohort_col] = out[id_col].map(cohort_by_id)
    out[target_col] = target_values

    definition = BadDefinition(
        threshold_kind=kind,
        threshold=float(threshold_dpd) if kind == "dpd" else str(threshold_status),
        observation_window=int(observation_window),
        performance_window=int(performance_window),
        at_mob=int(resolved_at_mob),
    )
    return LabelConstruction(
        frame=out,
        target_col=target_col,
        definition=definition,
        n_loans=int(len(ids)),
        n_bad=int(n_bad),
        n_good=int(n_good),
        n_unmatured=int(n_unmatured),
    )


@dataclass(frozen=True)
class CohortMaturity:
    """Single Loanscohort The maturity of the performance period is determined."""

    cohort: str
    n_loans: int
    #: Thecohort The biggest observed in the house.MOB(Cross that.cohort All loans).
    max_observed_mob: int
    #: It's what you need.MOB(= at_mob).
    required_mob: int
    matured: bool


@dataclass(frozen=True)
class MaturityReport:
    """Presscohort in which countries:cohort Performance period is not closed."""

    required_mob: int
    cohorts: tuple[CohortMaturity, ...]
    immature_cohorts: tuple[str, ...]

    @property
    def all_matured(self) -> bool:
        return len(self.immature_cohorts) == 0


def check_cohort_maturity(
    df: pd.DataFrame,
    *,
    id_col: str,
    mob_col: str,
    cohort_col: str,
    required_mob: int,
) -> MaturityReport:
    """Pressvintage cohort (b) Determine whether the performance period is closed enough to be bad enough.

    One.cohort Grown up.= The biggest thing they've ever seen on their loans.MOB >= ``required_mob``(- It's a bad decision point.
    Immortalcohort Bad labels underestimate the rate (to be taken as good before it is broken) and must be passed through the confirmation door and included in silence.
    Determination: Same output required for the same inputreport.
    """
    required = [id_col, mob_col, cohort_col]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    work = df[required].copy()
    work["_marvis_mob"] = pd.to_numeric(work[mob_col], errors="coerce")
    work = work[work["_marvis_mob"].notna()].copy()
    work["_marvis_mob"] = work["_marvis_mob"].astype(int)
    work["_marvis_cohort"] = work[cohort_col].map(_cohort_key)

    cohorts: list[CohortMaturity] = []
    immature: list[str] = []
    for cohort, group in work.groupby("_marvis_cohort", sort=True):
        max_mob = int(group["_marvis_mob"].max())
        n_loans = int(group[id_col].nunique())
        matured = max_mob >= int(required_mob)
        cohorts.append(
            CohortMaturity(
                cohort=str(cohort),
                n_loans=n_loans,
                max_observed_mob=max_mob,
                required_mob=int(required_mob),
                matured=matured,
            )
        )
        if not matured:
            immature.append(str(cohort))
    return MaturityReport(
        required_mob=int(required_mob),
        cohorts=tuple(cohorts),
        immature_cohorts=tuple(immature),
    )


@dataclass(frozen=True)
class BadDefinitionSuggestion:
    """Fromroll_rate The matrix presents a bad-calibre proposal (see below).tool_define_label . The default recommended."""

    threshold_status: str
    at_mob: int
    #: The bucket is recommending.MOB Scrollback Rate After (roll-back To better status as a percentage.
    roll_back_rate: float
    rationale: str

    def to_dict(self) -> dict:
        return {
            "threshold_status": self.threshold_status,
            "at_mob": self.at_mob,
            "roll_back_rate": self.roll_back_rate,
            "rationale": self.rationale,
        }


#: Rollback rate below this threshold= The past-due barrel basic"I can't go back.",It's a bad thing.
_STABLE_ROLL_BACK_THRESHOLD = 0.10


def suggest_bad_definition(
    *,
    states: list[str] | tuple[str, ...],
    matrix: list[list[float]] | tuple[tuple[float, ...], ...],
    at_mob: int,
    roll_back_threshold: float = _STABLE_ROLL_BACK_THRESHOLD,
) -> BadDefinitionSuggestion | None:
    """From the beginning.roll_rate_matrix Output generates a bad calibre proposal.

    Bridge logic:``states`` It's a good to bad sort of barrel.``matrix[i][j]`` Fromstates[i] Transfer
    states[j] % of each past due barrel."Okay."- I'm counting it."Rollback Rate"= Move to any**Better.**
    The share of the barrel is the sum of the drums.< The threshold) means that when you enter the barrel, you will hardly be able to recover — a steady and bad point.
    Selecting rollback below threshold**Top (lightest)**The last time I saw a barrel, I was told that the last barrel was a long time ago (the sooner I decided to break it, the more I could expand it).
    Like"60+ Yes.mob6 Backscrolling Rate<10% → Recommendation 60+@mob6".Return of UnsatisfactoryNone.

    Determination: Pure function, given as a givenmatrix The outputs will be the same as the recommendations.
    """
    state_order = tuple(str(state) for state in states)
    n = len(state_order)
    if n < 2:
        return None
    rows = [tuple(float(value) for value in row) for row in matrix]
    if len(rows) != n or any(len(row) != n for row in rows):
        raise ValueError("matrix shape must match states length")

    # Overdue barrels= Index>= 1(Index 0 is the best."Current/Normal"(breathing heavily)
    for index in range(1, n):
        roll_back = sum(rows[index][j] for j in range(0, index))
        if roll_back < float(roll_back_threshold):
            return BadDefinitionSuggestion(
                threshold_status=state_order[index],
                at_mob=int(at_mob),
                roll_back_rate=float(roll_back),
                rationale=(
                    f"{state_order[index]} Yes.mob{at_mob} Backscrolling Rate"
                    f"{roll_back * 100:.1f}% < {roll_back_threshold * 100:.0f}%,"
                    f"It's almost no good to go into the barrel.{state_order[index]}@mob{at_mob} It's bad."
                ),
            )
    return None


__all__ = [
    "BadDefinition",
    "BadDefinitionSuggestion",
    "CohortMaturity",
    "LabelConstruction",
    "MaturityReport",
    "check_cohort_maturity",
    "construct_label",
    "suggest_bad_definition",
]
