from marvis.error_kinds import ErrorKind


class StrategyError(ValueError):
    pass


class StrategyNotAdoptedError(StrategyError):
    """S5: raised when strategy monitoring is requested for a strategy that is not
    locally adopted. A draft/validated/retired asset is not the local champion.
    Local adoption is deliberately not represented as production deployment.
    Carries ``to_detail()`` so the subprocess boundary tags the tool
    result with error_kind='strategy_not_adopted' (structured, never parsed from
    free text -- the NanLabelNotConfirmedError precedent)."""

    def __init__(
        self,
        *,
        strategy_id: str,
        status: str | None = None,
        asset_status: str | None = None,
    ) -> None:
        self.strategy_id = str(strategy_id)
        self.status = str(status) if status else None
        self.asset_status = str(asset_status) if asset_status else None
        current = self.asset_status or self.status
        detail = f"(Current asset status{current})" if current else ""
        super().__init__(
            f"The only way to monitor the strategy that has been adopted is to monitor it.{self.strategy_id} Not in place"
            f" adopted_local{detail}.Locally accepted, not representing production on line."
        )

    def to_detail(self) -> dict:
        return {
            "kind": ErrorKind.STRATEGY_NOT_ADOPTED,
            "strategy_id": self.strategy_id,
            "status": self.status,
            "asset_status": self.asset_status,
        }


class StrategyPoolLegacyDraftNeedsRebuildError(StrategyError):
    """A v1 draft was archived and cannot be interpreted as a v2 Pool."""

    def __init__(self, archive: dict) -> None:
        self.archive = dict(archive)
        super().__init__(
            "archived Strategy Pool v1 draft requires an explicit v2 rebuild"
        )

    def to_detail(self) -> dict:
        return {
            "kind": ErrorKind.LEGACY_POOL_DRAFT_NEEDS_REBUILD,
            "archive": self.archive,
        }


class StrategySampleDesignV2NativeSourceUnsupportedError(StrategyError):
    """A consumer that still requires V1 development lineage saw native V2 evidence."""

    code = "strategy_sample_design_v2_native_source_unsupported"

    def __init__(
        self,
        *,
        consumer: str,
        source_mode: str = "native_active_dataset",
    ) -> None:
        self.consumer = str(consumer)
        self.source_mode = str(source_mode)
        super().__init__(
            f"{self.consumer} requires legacy_development capability; "
            f"sample-design V2 source_mode {self.source_mode} is unsupported"
        )

    def to_detail(self) -> dict:
        return {
            "kind": (
                ErrorKind.STRATEGY_SAMPLE_DESIGN_V2_NATIVE_SOURCE_UNSUPPORTED
            ),
            "consumer": self.consumer,
            "source_mode": self.source_mode,
        }


class StrategySampleDesignScopeIneligibleError(StrategyError):
    """Authenticated sample evidence is not eligible for development execution."""

    code = "strategy_sample_design_scope_ineligible"

    def __init__(
        self,
        *,
        scope: str,
        required_scope: str = "strategy_development",
    ) -> None:
        self.scope = str(scope)
        self.required_scope = str(required_scope)
        super().__init__(
            "strategy sample-design scope "
            f"{self.scope} is not eligible for {self.required_scope} execution"
        )


__all__ = [
    "StrategyError",
    "StrategyNotAdoptedError",
    "StrategyPoolLegacyDraftNeedsRebuildError",
    "StrategySampleDesignScopeIneligibleError",
    "StrategySampleDesignV2NativeSourceUnsupportedError",
]
