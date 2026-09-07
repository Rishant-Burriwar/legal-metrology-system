from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "inspector"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None


class RuleResponse(BaseModel):
    id: int
    rule_code: str
    description: str
    severity: str
    model_config = ConfigDict(from_attributes=True)


class ViolationResponse(BaseModel):
    id: Optional[int] = None
    rule_code: str
    description: str
    severity: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class ExtractedField(BaseModel):
    value: Optional[str] = None
    status: str  # found, not_found, low_confidence
    raw_snippet: Optional[str] = None


class InspectionResponse(BaseModel):
    id: int
    inspector_id: Optional[int] = None
    product_name: str
    brand: str
    image_path: str
    cropped_image_path: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    validated_ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = 0.0
    ocr_retry_count: Optional[int] = 0
    quality_score: Optional[float] = 0.0
    quality_assessment: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    compliance_score: float
    overall_status: str
    created_at: datetime
    violations: List[ViolationResponse] = []
    model_config = ConfigDict(from_attributes=True)


class InspectionSummary(BaseModel):
    id: int
    product_name: str
    brand: str
    compliance_score: float
    quality_score: Optional[float] = 0.0
    ocr_confidence: Optional[float] = 0.0
    overall_status: str
    created_at: datetime
    inspector_name: Optional[str] = None
    image_path: str
    model_config = ConfigDict(from_attributes=True)


class ViolationBreakdown(BaseModel):
    rule_code: str
    description: str
    fail_count: int
    pass_count: int


class DashboardStats(BaseModel):
    total_inspections: int
    compliant_count: int
    non_compliant_count: int
    compliance_rate: float
    violations_by_type: List[ViolationBreakdown]
    recent_trend: List[Dict[str, Any]]
