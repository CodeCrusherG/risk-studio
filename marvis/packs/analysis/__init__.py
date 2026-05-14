"""S3 Group Analysis Package(portfolio analysis pack).

Deterministic bucket-flow / migration / segment-profile / expected-loss / trend
tools over a performance (Show time.) snapshot table, plus a portfolio report
assembler. All metrics are deterministic (INV-1); trend tools reuse the same
compute_psi/bin_distribution kernel as modeling monitor_run.
"""

from marvis.packs.analysis.errors import AnalysisError

__all__ = ["AnalysisError"]
