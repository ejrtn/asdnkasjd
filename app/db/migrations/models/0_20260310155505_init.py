from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `users` (
    `id` VARCHAR(100) NOT NULL PRIMARY KEY COMMENT '사용자 ID (이메일 주소)',
    `nickname` VARCHAR(40) NOT NULL,
    `name` VARCHAR(20) NOT NULL,
    `password` VARCHAR(128) NOT NULL,
    `phone_number` VARCHAR(11) NOT NULL,
    `birthday` VARCHAR(10) NOT NULL,
    `gender` VARCHAR(10) NOT NULL,
    `alarm_tf` BOOL NOT NULL,
    `fcm_token` VARCHAR(255),
    `is_terms_agreed` BOOL NOT NULL DEFAULT 0,
    `is_privacy_agreed` BOOL NOT NULL DEFAULT 0,
    `is_marketing_agreed` BOOL NOT NULL DEFAULT 0,
    `is_alarm_agreed` BOOL NOT NULL DEFAULT 0
) CHARACTER SET utf8mb4 COMMENT='서비스의 사용자 계정 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `allergies` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `allergy_type` VARCHAR(100),
    `allergy_name` VARCHAR(100),
    `symptom` VARCHAR(100),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_allergie_users_cc13c577` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 보유한 알러지 성분 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `chronic_diseases` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `disease_name` VARCHAR(100) NOT NULL,
    `when_to_diagnose` VARCHAR(10) NOT NULL,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_chronic__users_a03285c9` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 앓고 있는 기저 질환(고혈압, 당뇨 등) 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `current_meds` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `medication_name` VARCHAR(255) NOT NULL,
    `one_dose` VARCHAR(255),
    `daily_dose_count` VARCHAR(255),
    `one_dose_count` VARCHAR(255),
    `dose_time` VARCHAR(4) NOT NULL COMMENT '복용 시간',
    `added_from` VARCHAR(5) NOT NULL COMMENT '복용 시간',
    `start_date` VARCHAR(255),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_current__users_425eb8b1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 현재 실제로 복용 중인 약물 목록을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `alarms` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `alarm_type` VARCHAR(20) NOT NULL DEFAULT 'MED',
    `alarm_time` TIME(6) NOT NULL,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `current_med_id` INT,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_alarms_current__65ab2c31` FOREIGN KEY (`current_med_id`) REFERENCES `current_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_alarms_users_00f32162` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 설정한 알람 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `alarm_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `sent_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `delivered_at` DATETIME(6),
    `read_at` DATETIME(6),
    `is_confirmed` BOOL NOT NULL DEFAULT 0,
    `alarm_id` INT NOT NULL,
    CONSTRAINT `fk_alarm_hi_alarms_9f73e320` FOREIGN KEY (`alarm_id`) REFERENCES `alarms` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='알람 발송 내역과 사용자의 확인 여부를 기록하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `llm_life_guides` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_current_status` LONGTEXT NOT NULL,
    `generated_content` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_llm_life_users_9bda261a` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='AI가 생성한 환자 맞춤형 복약 및 생활 가이드 전문을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `session_id` VARCHAR(100) NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    `message` LONGTEXT NOT NULL,
    `is_deleted` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `reference_guide_id` INT,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_chat_mes_llm_life_f5df1902` FOREIGN KEY (`reference_guide_id`) REFERENCES `llm_life_guides` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_chat_mes_users_91f55345` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자와 챗봇 간의 대화 메시지 이력을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `multimodal_assets` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `source_table` VARCHAR(50) NOT NULL,
    `source_id` INT NOT NULL,
    `asset_type` VARCHAR(20) NOT NULL,
    `asset_url` VARCHAR(512) NOT NULL
) CHARACTER SET utf8mb4 COMMENT='텍스트 기반 가이드를 바탕으로 생성된 시각/청각 에셋 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `system_logs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `api_path` VARCHAR(255) NOT NULL,
    `method` VARCHAR(10) NOT NULL,
    `response_ms` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4 COMMENT='서비스 API의 성능 및 에러 여부를 모니터링하기 위한 로그 모델입니다.';
CREATE TABLE IF NOT EXISTS `uploads` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `file_path` VARCHAR(512) NOT NULL,
    `original_name` VARCHAR(255),
    `file_type` VARCHAR(20) NOT NULL,
    `category` VARCHAR(50),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_uploads_users_5a3e4278` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 업로드한 원본 파일 정보(처방전, 약품 사진 등)를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `prescriptions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hospital_name` VARCHAR(255),
    `prescribed_date` DATE,
    `drug_list_raw` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    `upload_id` INT NOT NULL UNIQUE,
    CONSTRAINT `fk_prescrip_users_75d98828` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prescrip_uploads_02e6e99e` FOREIGN KEY (`upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자가 업로드한 처방전의 분석 결과를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `prescription_drugs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `standard_drug_name` VARCHAR(255) NOT NULL,
    `dosage_amount` DOUBLE,
    `daily_frequency` INT,
    `duration_days` INT,
    `is_linked_to_meds` BOOL NOT NULL DEFAULT 0,
    `prescription_id` INT NOT NULL,
    CONSTRAINT `fk_prescrip_prescrip_c35d9dcd` FOREIGN KEY (`prescription_id`) REFERENCES `prescriptions` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방전에 포함된 개별 약품 상세 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `ocr_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `raw_text` LONGTEXT NOT NULL,
    `is_valid` BOOL NOT NULL DEFAULT 0,
    `inference_metadata` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    `front_upload_id` INT NOT NULL UNIQUE,
    `back_upload_id` INT UNIQUE,
    CONSTRAINT `fk_ocr_hist_users_de674177` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ocr_hist_uploads_2ee6bf89` FOREIGN KEY (`front_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ocr_hist_uploads_1cf26d91` FOREIGN KEY (`back_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='이미지 내 텍스트 추출(OCR) 엔진의 분석 원본 이력을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `cnn_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `model_version` VARCHAR(50),
    `confidence` DOUBLE NOT NULL,
    `raw_result` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    `front_upload_id` INT NOT NULL UNIQUE,
    `back_upload_id` INT NOT NULL UNIQUE,
    CONSTRAINT `fk_cnn_hist_users_e8d4fc04` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cnn_hist_uploads_cf0f5d83` FOREIGN KEY (`front_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cnn_hist_uploads_ff92f8c2` FOREIGN KEY (`back_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='AI 모델을 통한 알약 외형 이미지 분석 이력을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `pill_recognitions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pill_name` VARCHAR(255) NOT NULL,
    `pill_description` LONGTEXT NOT NULL,
    `is_linked_to_meds` BOOL NOT NULL DEFAULT 0,
    `cnn_history_id` INT NOT NULL,
    `ocr_history_id` INT NOT NULL,
    `user_id` VARCHAR(100) NOT NULL,
    `front_upload_id` INT NOT NULL UNIQUE,
    `back_upload_id` INT NOT NULL UNIQUE,
    CONSTRAINT `fk_pill_rec_cnn_hist_f16067ca` FOREIGN KEY (`cnn_history_id`) REFERENCES `cnn_history` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_ocr_hist_6d4cdf0a` FOREIGN KEY (`ocr_history_id`) REFERENCES `ocr_history` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_users_2e103417` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_uploads_461a6fb8` FOREIGN KEY (`front_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_uploads_796ec903` FOREIGN KEY (`back_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='CNN 및 OCR 분석 결과를 조합하여 최종적으로 식별된 알약 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `blood_pressure_records` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `systolic` INT NOT NULL COMMENT '수축기(mmHg)',
    `diastolic` INT NOT NULL COMMENT '이완기(mmHg)',
    `measure_type` VARCHAR(2) NOT NULL COMMENT '측정 상황',
    `created_at` DATETIME(6) NOT NULL COMMENT '서버 저장 시각' DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL COMMENT '사용자',
    CONSTRAINT `fk_blood_pr_users_67a78557` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='혈압 기록(수축기/이완기/맥박)';
CREATE TABLE IF NOT EXISTS `blood_sugar_records` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `glucose_mg_dl` DOUBLE NOT NULL COMMENT '혈당(mg/dL)',
    `measure_type` VARCHAR(8) NOT NULL COMMENT '측정 상황(공복/식후 2시간/취침전/임의)',
    `created_at` DATETIME(6) NOT NULL COMMENT '서버 저장 시각' DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL COMMENT '사용자',
    CONSTRAINT `fk_blood_su_users_6db13992` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='혈당 기록(mg/dL + 측정상황)';
CREATE TABLE IF NOT EXISTS `health_profiles` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `family_history` VARCHAR(5) NOT NULL COMMENT '가족력',
    `family_history_note` LONGTEXT COMMENT '사용자 입력 텍스트',
    `height_cm` DOUBLE NOT NULL COMMENT '신장(cm)',
    `weight_kg` DOUBLE NOT NULL COMMENT '체중(kg)',
    `weight_change` VARCHAR(4) NOT NULL COMMENT '최근 체중 변화',
    `sleep_hours` DOUBLE COMMENT '수면 시간(시간)',
    `sleep_change` VARCHAR(4) NOT NULL COMMENT '최근 수면 변화',
    `smoking_status` VARCHAR(5) NOT NULL COMMENT '흡연 상태',
    `smoking_years` INT COMMENT '흡연 기간(년)',
    `smoking_per_week` DOUBLE COMMENT '주 평균 흡연량(팀 기준 단위 통일)',
    `drinking_status` VARCHAR(5) NOT NULL COMMENT '음주 상태',
    `drinking_years` INT COMMENT '음주 기간(년)',
    `drinking_per_week` DOUBLE COMMENT '주 평균 음주량(팀 기준 단위 통일)',
    `exercise_frequency` VARCHAR(7) NOT NULL COMMENT '운동 빈도',
    `diet_type` VARCHAR(5) NOT NULL COMMENT '식습관 유형',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '사용자',
    CONSTRAINT `fk_health_p_users_35ba10a2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='사용자 건강 프로필(정적/준정적 정보)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
