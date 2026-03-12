from pydantic import BaseModel, Field


# ==========================================
# [추가된 기능] 필수 3 & 선택 2: OCR 및 약품 이미지 분석
# ==========================================
class DrugInfo(BaseModel):
    drug_name: str = Field(..., description="약품명")
    dosage: str = Field(..., description="1회 복용량 (mg/ml 등 정규화)")
    frequency: str = Field(..., description="1일 복용 횟수")
    duration: str = Field(..., description="복용 기간 (일)")


class OCRExtractResponse(BaseModel):
    hospital_name: str | None = Field(None, description="병원명")
    prescribed_date: str | None = Field(None, description="처방일 (YYYY-MM-DD)")
    drugs: list[DrugInfo] = Field(default_factory=list, description="추출된 약품 상세 정보")
    extracted_text: str = Field(..., description="전체 텍스트 본문")
    confidence: float = Field(..., description="OCR 전체 신뢰도")
    multimodal_assets: list[dict] | None = Field(None, description="카드뉴스/음성 등 변환 에셋")


class PillCandidate(BaseModel):
    pill_name: str
    confidence: float
    medication_info: str = ""
    image_url: str | None = None
    item_seq: str | None = None
    color: str | None = None
    shape: str | None = None
    marking_front: str | None = None
    marking_back: str | None = None


class PillAnalyzeResponse(BaseModel):
    candidates: list[PillCandidate] = Field(..., description="CNN 분석 상위 3개 후보")
    top_candidate: PillCandidate = Field(..., description="가장 신뢰도 높은 약품")
    suggestion: str | None = Field(None, description="신뢰도가 낮을 경우(60% 미만) 안내 문구")
    multimodal_assets: list[dict] | None = Field(None, description="이미지/음성 등 변환 에셋")


class OCRVerificationRequest(BaseModel):
    hospital_name: str | None = None
    prescribed_date: str | None = None  # YYYY-MM-DD
    drugs: list[DrugInfo] | None = None  # 수동 수정된 약품 목록
    is_verified: bool = True
