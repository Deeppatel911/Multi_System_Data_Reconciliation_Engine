from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class ConfidenceScore(BaseModel):
    score: float = Field(..., description="A float between 0.0 and 1.0 representing merge confidence.")
    reasoning: str = Field(..., description="Explanation of why this confidence score was given by the LLM.")


class ConflictingValues(BaseModel):
    salesforce: Optional[str] = None
    stripe: Optional[str] = None
    app_db: Optional[str] = None


class DiscrepancyReport(BaseModel):
    field_name: str = Field(..., description="The name of the conflicting field (e.g., 'company_name').")
    # source_a_value: str = Field(..., description="The value from the first data source.")
    # source_b_value: str = Field(..., description="The value from the second data source.")
    conflicting_values: ConflictingValues
    conflict_description: str = Field(..., description="Short explanation of why these values conflict.")


class UnifiedCustomerProfile(BaseModel):
    canonical_id: str = Field(..., description="A newly generated unique ID for the merged profile.")
    company_name: str = Field(..., description="The resolved, canonical company name.")
    domain: str = Field(..., description="The primary web domain.")
    billing_email: Optional[str] = Field(None, description="The resolved billing email contact.")
    crm_tier: Optional[str] = Field(None, description="The customer tier from the CRM.")
    is_active: bool = Field(..., description="Boolean indicating if the account is currently active.")
    confidence_metrics: ConfidenceScore
    discrepancies: List[DiscrepancyReport] = Field(default_factory=list, description="List of unresolved discrepancies.")