"""Read-only autonomous delivery lineage projection."""

CONTRACT = "autonomous-delivery-lineage-v1"

from app.platform.delivery_lineage.service import build_delivery_lineage, build_lineage_summary

__all__ = ["CONTRACT", "build_delivery_lineage", "build_lineage_summary"]
