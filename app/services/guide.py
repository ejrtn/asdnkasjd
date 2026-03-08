import json
import os
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.user import User


class GuideService:
    def load_rag_docs(self) -> list[dict[str, str]]:
        """
        [RAG] 로컬 문서 로드.
        app/data/docs/ 아래의 모든 .txt 파일을 읽어와
        파일명과 본문을 함께 반환합니다.
        """
        docs_dir = Path("app/data/docs")
        docs: list[dict[str, str]] = []

        if not docs_dir.exists():
            return docs

        for path in docs_dir.glob("*.txt"):
            text = path.read_text(encoding="utf-8")
            docs.append({"filename": path.name, "text": text})

        return docs

    def _score_document(self, doc_text: str, doc_filename: str, keywords: list[str]) -> int:
        score = 0
        doc_filename_lower = doc_filename.lower()

        mapping = {
            "고혈압": "hypertension",
            "당뇨병": "diabetes",
            "복용": "medication",
            "저염식": "low_salt",
            "운동": "exercise",
        }

        for keyword in keywords:
            if not keyword:
                continue

            if keyword in doc_text:
                score += 1

            keyword_lower = keyword.lower()
            if keyword_lower in doc_filename_lower:
                score += 2

            if keyword in mapping and mapping[keyword] in doc_filename_lower:
                score += 2

        return score

    def select_relevant_docs(
        self,
        rag_docs: list[dict[str, str]],
        disease_list: list[str],
        med_list: list[str],
    ) -> list[dict[str, str]]:
        keywords = []
        keywords.extend(disease_list)
        keywords.extend(med_list)
        keywords.extend(["운동", "복용", "저염식", "혈압", "혈당"])

        scored_docs = []
        for doc in rag_docs:
            score = self._score_document(doc["text"], doc["filename"], keywords)
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        selected_docs = [doc for score, doc in scored_docs if score > 0]

        return selected_docs[:3] if selected_docs else rag_docs[:3]

    # ==========================================
    # 필수 1: LLM 기반 안내 가이드 생성
    # ==========================================
    async def generate_guide(self, user: User | None = None) -> dict:
        """
        [GUIDE] 맞춤 가이드 생성(RAG 핵심).
        실제 사용자의 기저질환, 알러지, 복용약을 바탕으로 OpenAI를 통해 구조화된 가이드를 생성합니다.
        (DB 연결 실패 시 기본값으로 대체)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # If API key is missing, return a dummy JSON directly to show the UI
            return {
                "id": 1,
                "guide_data": {
                    "section1": {
                        "title": "복약 안전성 및 주의사항",
                        "status": "주의 필요",
                        "content": "API 키가 설정되지 않아 예시 데이터를 표시합니다. 평소 드시는 약과 알레르기 반응을 주의하세요.",
                        "general_cautions": ["권장 용량을 준수하세요.", "불편함이 느껴지면 즉시 복용을 중단하세요."],
                    },
                    "section2": {
                        "title": "질환 기반 생활습관 가이드",
                        "disease_guides": [
                            {
                                "name": "내 기저질환",
                                "tips": ["충분한 수분을 섭취하세요.", "규칙적인 식습관이 중요합니다."],
                            }
                        ],
                        "integrated_point": "균형 잡힌 생활 패턴 유지를 권장합니다.",
                    },
                    "section3": {
                        "title": "오늘의 실행 플랜",
                        "checklist": ["물 2L 마시기", "가벼운 스트레칭", "제시간에 약 복용"],
                    },
                    "section4": {
                        "title": "왜 이런 가이드가 생성되었나요?",
                        "reason": "사용자의 건강 정보를 종합적으로 분석하여 생성되었습니다.",
                    },
                    "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다.",
                },
                "created_at": "2026-03-01T20:00:00",
            }

        # 1. 실제 사용자 데이터 조회 (연결 실패 시 빈 데이터 처리)
        try:
            if user is None:
                # Try to get first user but don't fail if DB is down
                try:
                    user = await User.first()
                except Exception:
                    user = None

            if user:
                diseases = await ChronicDisease.filter(user=user).all()
                allergies = await Allergy.filter(user=user).all()
                meds = await CurrentMed.filter(user=user).all()

                # 최근 혈압, 혈당 데이터
                bp_records = await BloodPressureRecord.filter(user=user).limit(5)
                bs_records = await BloodSugarRecord.filter(user=user).limit(5)

                bp_list = [f"{r.systolic}/{r.diastolic} mmHg" for r in bp_records]
                bs_list = [f"{r.glucose_mg_dl} mg/dL ({r.measure_type})" for r in bs_records]

                disease_list = [d.disease_name for d in diseases]
                allergy_list = [a.allergy_name for a in allergies]
                med_list = [m.medication_name for m in meds]

            else:
                disease_list, allergy_list, med_list = ["고혈압"], ["땅콩"], ["타이레놀"]
                bp_list = ["120/80 mmHg"]
                bs_list = ["95 mg/dL (FASTING)"]
        except Exception:
            # DB connection error or other DB issues
            disease_list, allergy_list, med_list = ["고혈압"], ["땅콩"], ["타이레놀"]
            bp_list = ["120/80 mmHg"]
            bs_list = ["95 mg/dL (FASTING)"]

        rag_docs = self.load_rag_docs()
        selected_docs = self.select_relevant_docs(rag_docs, disease_list, med_list)
        rag_context = "\n\n".join(docs["text"] for docs in selected_docs) if selected_docs else "참고 문서 없음"

        client = AsyncOpenAI(api_key=api_key)

        prompt = f"""
    신중하고 전문적인 의료 도우미로서, 아래 환자의 건강 상태를 바탕으로 '생활 안내 가이드'를 작성해줘.

    [환자 상태]
    - 만성 질환: {", ".join(disease_list) if disease_list else "없음"}
    - 알레르기: {", ".join(allergy_list) if allergy_list else "없음"}
    - 현재 복용 약: {", ".join(med_list) if med_list else "없음"}
    - 최근 혈압 기록: {", ".join(bp_list) if bp_list else "없음"}
    - 최근 혈당 기록: {", ".join(bs_list) if bs_list else "없음"}

    [참고 문서]
    {rag_context}

    [작성 가이드라인]
    1. 과한 확정 진단(예: ~병입니다)은 피하고, '권장합니다', '주의가 필요합니다' 등의 조언 톤을 유지할 것.
    2. 약물 상호작용 및 알레르기 성분을 최우선으로 체크할 것.
    3. 반드시 아래의 JSON 구조로 응답할 것.
    4. 만성 질환이 2개 이상이면 disease_guides를 질환 개수만큼 반드시 생성할 것(누락 금지).
    5. disease_guides의 name은 입력된 만성 질환명(disease_list)에 있는 문자열을 그대로 사용할 것.
    6. 참고 문서의 내용을 우선 반영하여 생활습관 및 복약 안내를 작성할 것.

    [응답 JSON 구조]
    {{
    "section1": {{
        "title": "복약 안전성 및 주의사항",
        "status": "상호작용 없음 | 주의 필요 | 위험 가능성",
        "content": "상태에 따른 상세 설명 문구",
        "general_cautions": ["주의사항 1", "주의사항 2"]
    }},
    "section2": {{
        "title": "질환 기반 생활습관 가이드",
        "disease_guides": [
        {{ "name": "질환명", "tips": ["가이드 1", "가이드 2"] }}
        ],
        "integrated_point": "종합 관리 포인트 문구"
    }},
    "section3": {{
        "title": "오늘의 실행 플랜",
        "checklist": ["체크리스트 1", "체크리스트 2", "체크리스트 3"]
    }},
    "section4": {{
        "title": "왜 이런 가이드가 생성되었나요?",
        "reason": "입력된 정보(질환, 약물 등)가 가이드에 어떻게 반영되었는지에 대한 설명"
    }},
    "disclaimer": "본 서비스는 의료 진단이나 처방을 제공하지 않으며, 참고용 안내입니다."
    }}
    """.strip()

        try:
            res = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "너는 꼼꼼한 간호사 출신 건강 안내 도우미다. JSON 형식으로만 답변한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )

            content_json = json.loads(res.choices[0].message.content or "{}")
            # ✅ 질환 누락 보정: disease_list에 있는 질환은 모두 disease_guides에 포함되도록 강제
            try:
                sec2 = content_json.get("section2") or {}
                guides = sec2.get("disease_guides") or []
                guide_names = {g.get("name") for g in guides if isinstance(g, dict)}

                for dname in disease_list:
                    if dname not in guide_names:
                        guides.append(
                            {
                                "name": dname,
                                "tips": ["(추가 입력 시 더 정확한 맞춤 가이드를 제공할 수 있어요.)"],
                            }
                        )

                sec2["disease_guides"] = guides
                content_json["section2"] = sec2
            except Exception:
                pass

            return {
                "id": 1,
                "guide_data": content_json,
                "created_at": datetime.now().isoformat(),
                "rag_docs_used": [f"{doc['filename']}: {doc['text'][:120]}..." for doc in selected_docs],
            }
        except Exception as e:
            print(f"OpenAI Error: {e}")
            # Return fallback dummy even if OpenAI fails
            return {
                "id": 1,
                "guide_data": {
                    "section1": {
                        "title": "오류 안내",
                        "status": "데이터 확인 불가",
                        "content": "네트워크 연결 불안정으로 기본 정보를 제공합니다.",
                        "general_cautions": ["약물 오남용 주의"],
                    },
                    "section2": {
                        "title": "일반 관리",
                        "disease_guides": [{"name": "일반", "tips": ["건강한 수면 취하기"]}],
                        "integrated_point": "병원 방문을 권장합니다.",
                    },
                    "section3": {"title": "실행 플랜", "checklist": ["규칙적 식사", "수분 섭취"]},
                    "section4": {"title": "출처", "reason": "시스템 연결 문제로 기본 가이드가 생성되었습니다."},
                    "disclaimer": "본 정보는 참고용입니다.",
                },
                "created_at": "2026-03-01T20:00:00",
            }
