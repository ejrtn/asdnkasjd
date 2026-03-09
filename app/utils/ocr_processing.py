import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(image_bytes: bytes) -> bytes:
    """
    OpenCV를 사용하여 이미지를 전처리하여 OCR 인식률을 높입니다.
    (Grayscale -> GaussianBlur -> Adaptive Thresholding)
    """
    try:
        # bytes를 numpy array로 변환
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("이미지 디코딩 실패. 원본 데이터를 반환합니다.")
            return image_bytes

        # 1. Grayscale 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. 노이즈 제거 (GaussianBlur)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # 3. 이진화 (Adaptive Thresholding)
        # 밝기 차이가 심한 문서를 위해 적응형 이진화 사용
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # 처리된 이미지를 다시 bytes로 변환 (PNG 형식 권장)
        _, encoded_img = cv2.imencode(".png", thresh)
        return encoded_img.tobytes()  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(f"이미지 전처리 중 오류 발생: {e}. 원본 데이터를 사용합니다.")
        return image_bytes
