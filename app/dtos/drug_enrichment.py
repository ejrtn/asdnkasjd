from pydantic import BaseModel, Field


class DrugEnrichmentData(BaseModel):
    """
    LLM이 생성한 의약품 추가 정보 DTO
    """

    efcy_qesitm: str = Field(..., description="이 약의 효능은 무엇입니까?")
    use_method_qesitm: str = Field(..., description="이 약은 어떻게 사용합니까?")
    atpn_warn_qesitm: str | None = Field(None, description="이 약을 사용하기 전에 반드시 알아야 할 내용은 무엇입니까?")
    atpn_qesitm: str = Field(..., description="이 약을 사용할 때 주의해야 할 사항은 무엇입니까?")
    intrc_qesitm: str | None = Field(None, description="이 약을 사용하는 동안 주의해야 할 약물이나 음식은 무엇입니까?")
    se_qesitm: str | None = Field(None, description="이 약의 부작용은 무엇입니까?")
    deposit_method_qesitm: str = Field(..., description="이 약은 어떻게 보관해야 합니까?")
