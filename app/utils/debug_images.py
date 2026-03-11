import logging
import os
import uuid
from datetime import datetime

from app.core.config import config

logger = logging.getLogger(__name__)


def save_debug_image(image_bytes: bytes, prefix: str = "ocr_debug") -> str | None:
    """
    전처리된 이미지를 디버깅 목적으로 로컬 디렉토리에 저장합니다.
    환경 변수 DEBUG_SAVE_PREPROCESSED_IMAGES가 True일 때만 동작합니다.
    """
    print(f"DEBUG_SAVE_PREPROCESSED_IMAGES 설정값: {config.DEBUG_SAVE_PREPROCESSED_IMAGES}")

    if not config.DEBUG_SAVE_PREPROCESSED_IMAGES:
        return None

    try:
        # 디버그용 이미지 저장 디렉토리 설정
        debug_dir = os.path.join(os.getcwd(), "debug_uploads")
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # 파일명 생성 (타임스탬프 + UUID)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        filename = f"{prefix}_{timestamp}_{unique_id}.png"
        file_path = os.path.join(debug_dir, filename)

        # 이미지 데이터 저장
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"디버그 이미지 저장 완료: {file_path}")
        return file_path

    except Exception as e:
        # 에러 내용을 터미널에 확실히 출력!
        print(f"!!! 디버그 이미지 저장 오류 발생: {e}")
        logger.error(f"디버그 이미지 저장 중 오류 발생: {e}")
        return None
