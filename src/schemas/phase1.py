"""Phase 1 schema compatibility re-exports."""

from .common import (
    ConfirmationBiasLevel,
    Entity,
    EntityCategory,
    EntityExtractionOutput,
    OpinionSpreader,
    Relation,
)

__all__ = [
    "EntityCategory",
    "Entity",
    "OpinionSpreader",
    "Relation",
    "EntityExtractionOutput",
    "ConfirmationBiasLevel",
]
