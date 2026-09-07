from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="inspector", nullable=False)  # inspector, admin, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    inspections = relationship("Inspection", back_populates="inspector")


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    product_name = Column(String(150), nullable=False)
    brand = Column(String(100), nullable=False)
    image_path = Column(String(300), nullable=False)
    cropped_image_path = Column(String(300), nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    validated_ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True, default=0.0)
    ocr_retry_count = Column(Integer, nullable=True, default=0)
    quality_score = Column(Float, nullable=True, default=0.0)
    quality_assessment = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    compliance_score = Column(Float, nullable=False, default=0.0)
    overall_status = Column(String(50), nullable=False, default="Pending")  # Compliant, Non-Compliant
    created_at = Column(DateTime, default=datetime.utcnow)

    inspector = relationship("User", back_populates="inspections")
    violations = relationship("Violation", back_populates="inspection", cascade="all, delete-orphan")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    rule_code = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # Major, Minor
    status = Column(String(20), nullable=False)    # Pass, Fail

    inspection = relationship("Inspection", back_populates="violations")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # Major, Minor
