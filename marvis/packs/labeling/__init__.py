"""Labeling pack: From repayment/DPD Long Table Construct 0/1 Bad Tag+ cohort Amagnitude check+ Recommendations on calibration(C1).

The label structure is the most important precursor to credit-control modelling:"Loans×Period"The long overdue schedule, as per business
Observation period/Performance period/Overdue threshold, set to a belt 0/1 Target derivative dataset with bad calibre metadata
(In.T3 Accompaniment.cohort I'm not gonna be silent.
"""

from marvis.data.label_construction import (
    BadDefinition,
    BadDefinitionSuggestion,
    CohortMaturity,
    LabelConstruction,
    MaturityReport,
    check_cohort_maturity,
    construct_label,
    suggest_bad_definition,
)
from marvis.packs.labeling.contracts import (
    LabelingContractError,
    LabelingProposal,
    LabelingRequest,
    build_labeling_proposal,
)

__all__ = [
    "BadDefinition",
    "BadDefinitionSuggestion",
    "CohortMaturity",
    "LabelConstruction",
    "LabelingContractError",
    "LabelingProposal",
    "LabelingRequest",
    "MaturityReport",
    "check_cohort_maturity",
    "build_labeling_proposal",
    "construct_label",
    "suggest_bad_definition",
]
