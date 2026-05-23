from pydantic import BaseModel, field_validator
from typing import Optional


class FieldExtraction(BaseModel):
    value: Optional[str] = None
    confidence: float  # 0.0–1.0
    source_region: Optional[str] = None

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ExtractionResult(BaseModel):
    job_id: str
    doc_type: str  # 'BoL' | 'CommercialInvoice' | 'PackingList' | 'CertificateOfOrigin'

    consignee_name: FieldExtraction
    hs_code: FieldExtraction
    port_of_loading: FieldExtraction
    port_of_discharge: FieldExtraction
    incoterms: FieldExtraction
    description_goods: FieldExtraction
    gross_weight: FieldExtraction
    invoice_number: FieldExtraction

    avg_confidence: float = 0.0

    def compute_avg_confidence(self) -> float:
        fields = [
            self.consignee_name,
            self.hs_code,
            self.port_of_loading,
            self.port_of_discharge,
            self.incoterms,
            self.description_goods,
            self.gross_weight,
            self.invoice_number,
        ]
        return round(sum(f.confidence for f in fields) / len(fields), 4)
