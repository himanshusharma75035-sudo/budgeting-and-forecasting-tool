"""Variance analysis domain (DESIGN.md 4).

Pure, dependency-free FP&A variance logic: sign/polarity conventions, budget-vs-actual,
the flexible-budget hierarchy, standard-costing cost variances, sales price/volume/
mix/quantity variances, materiality thresholding and waterfall bridges. All money math
is exact via :class:`decimal.Decimal`; favorable/unfavorable polarity is always derived
from the account type (DESIGN.md 4.2), never from the raw sign alone.
"""

from __future__ import annotations

from app.domain.variance.bridge import (
    Bridge,
    BridgeStep,
    build_bridge,
    price_volume_decomposition,
)
from app.domain.variance.budget_actual import BudgetActualVariance, budget_vs_actual
from app.domain.variance.cost_variances import (
    cost_variance_status,
    fixed_oh_spending_variance,
    fixed_oh_volume_variance,
    labor_efficiency_variance,
    labor_rate_variance,
    material_price_variance,
    material_quantity_variance,
    voh_efficiency_variance,
    voh_spending_variance,
)
from app.domain.variance.flexible_budget import (
    VarianceHierarchy,
    flexible_budget,
    variance_hierarchy,
)
from app.domain.variance.insights import (
    InsightDriver,
    VarianceInsight,
    VarianceItem,
    build_insights,
    compose_narrative,
)
from app.domain.variance.materiality import MaterialityThreshold, is_material
from app.domain.variance.sales_variances import (
    MixQtyResult,
    ProductSales,
    sales_mix_quantity,
    sales_price_variance,
    sales_volume_variance,
)
from app.domain.variance.sign import favorable_variance, is_favorable, status

__all__ = [
    # sign
    "is_favorable",
    "favorable_variance",
    "status",
    # budget vs actual
    "BudgetActualVariance",
    "budget_vs_actual",
    # flexible budget hierarchy
    "VarianceHierarchy",
    "flexible_budget",
    "variance_hierarchy",
    # cost variances
    "material_price_variance",
    "material_quantity_variance",
    "labor_rate_variance",
    "labor_efficiency_variance",
    "voh_spending_variance",
    "voh_efficiency_variance",
    "fixed_oh_spending_variance",
    "fixed_oh_volume_variance",
    "cost_variance_status",
    # sales variances
    "sales_price_variance",
    "sales_volume_variance",
    "ProductSales",
    "MixQtyResult",
    "sales_mix_quantity",
    # materiality
    "MaterialityThreshold",
    "is_material",
    # bridge
    "BridgeStep",
    "Bridge",
    "build_bridge",
    "price_volume_decomposition",
    # insights / narrative
    "VarianceItem",
    "InsightDriver",
    "VarianceInsight",
    "build_insights",
    "compose_narrative",
]
