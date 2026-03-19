from tortoise import fields, models


class DrugMaster(models.Model):
    """
    공공데이터포털(식약처) API에서 가져온 의약품 통합 마스터 정보 모델입니다.
    의약품 개요정보(e약은요)와 낱알식별 정보를 통합하여 관리합니다.
    """

    item_seq = fields.CharField(max_length=20, pk=True)  # 품목일련번호
    item_name = fields.CharField(max_length=500)  # 품목명
    entp_name = fields.CharField(max_length=255)  # 업소명

    # 낱알식별 정보 관련 필드
    chart = fields.TextField(null=True)  # 성상(성상/색상/모양 정보 포함)
    item_image = fields.CharField(max_length=500, null=True)  # 큰제품이미지 URL
    print_front = fields.CharField(max_length=100, null=True)  # 표시앞
    print_back = fields.CharField(max_length=100, null=True)  # 표시뒤
    drug_shape = fields.CharField(max_length=50, null=True)  # 의약품모양
    color_class1 = fields.CharField(max_length=50, null=True)  # 색상앞
    color_class2 = fields.CharField(max_length=50, null=True)  # 색상뒤
    line_front = fields.CharField(max_length=50, null=True)  # 분할선앞
    line_back = fields.CharField(max_length=50, null=True)  # 분할선뒤
    form_code_name = fields.CharField(max_length=100, null=True)  # 제형코드명
    etc_otc_name = fields.CharField(max_length=50, null=True)  # 전문/일반
    class_name = fields.CharField(max_length=100, null=True)  # 분류명

    # e약은요 개요정보 관련 필드
    efcy_qesitm = fields.TextField(null=True)  # 효능
    use_method_qesitm = fields.TextField(null=True)  # 사용법
    atpn_warn_qesitm = fields.TextField(null=True)  # 주의사항 경고
    atpn_qesitm = fields.TextField(null=True)  # 주의사항
    intrc_qesitm = fields.TextField(null=True)  # 상호작용
    se_qesitm = fields.TextField(null=True)  # 부작용
    deposit_method_qesitm = fields.TextField(null=True)  # 보관법
    source = fields.CharField(max_length=20, default="MFDS", null=True)  # 데이터 출처 (MFDS, AI 등)
    mfds_update_date = fields.CharField(max_length=20, null=True)  # 식약처 데이터 최종 변경/등록 일자
    last_enriched_mfds_date = fields.CharField(max_length=20, null=True)  # 마지막 AI 보충 시점의 식약처 변경 일자

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "drug_masters"
        indexes = [
            ("item_name",),
            ("entp_name",),
        ]
