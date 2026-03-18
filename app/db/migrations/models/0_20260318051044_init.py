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
    `provider` VARCHAR(20) NOT NULL DEFAULT 'local',
    `social_id` VARCHAR(100),
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
    CONSTRAINT `fk_allergie_users_cc13c577` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_allergies_user_id_6131ad` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 보유한 알러지 성분 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `chronic_diseases` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `disease_name` VARCHAR(100) NOT NULL,
    `when_to_diagnose` VARCHAR(10) NOT NULL,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_chronic__users_a03285c9` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_chronic_dis_user_id_05eec3` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 앓고 있는 기저 질환(고혈압, 당뇨 등) 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `llm_life_guides` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_current_status` LONGTEXT NOT NULL,
    `medication_guide` JSON,
    `disease_guide` JSON,
    `profile_guide` JSON,
    `activity_medication` BOOL NOT NULL DEFAULT 0,
    `activity_disease` BOOL NOT NULL DEFAULT 0,
    `activity_profile` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_llm_life_users_9bda261a` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_llm_life_gu_user_id_8b1575` (`user_id`)
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
    CONSTRAINT `fk_chat_mes_users_91f55345` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_chat_messag_user_id_baf261` (`user_id`)
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
    CONSTRAINT `fk_uploads_users_5a3e4278` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_uploads_user_id_0a970b` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 업로드한 원본 파일 정보(처방전, 약품 사진 등)를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `pill_recognitions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `model_version` VARCHAR(50),
    `pill_name` VARCHAR(255) NOT NULL,
    `pill_description` LONGTEXT,
    `confidence` DOUBLE NOT NULL,
    `raw_result` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `back_upload_id` INT,
    `front_upload_id` INT,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_pill_rec_uploads_796ec903` FOREIGN KEY (`back_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_uploads_461a6fb8` FOREIGN KEY (`front_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pill_rec_users_2e103417` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_pill_recogn_user_id_6afcef` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='AI 모델을 통한 알약 외형 이미지 분석 이력을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `current_meds` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `medication_name` VARCHAR(255) NOT NULL,
    `one_dose_amount` VARCHAR(255),
    `one_dose_count` VARCHAR(255),
    `total_days` VARCHAR(255),
    `instructions` LONGTEXT,
    `user_id` VARCHAR(100) NOT NULL,
    `pill_recognition_id` INT UNIQUE,
    CONSTRAINT `fk_current__users_425eb8b1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_current__pill_rec_9a5f78e7` FOREIGN KEY (`pill_recognition_id`) REFERENCES `pill_recognitions` (`id`) ON DELETE CASCADE,
    KEY `idx_current_med_user_id_bc1b2b` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 현재 실제로 복용 중인 약물 목록을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `alarms` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `alarm_type` VARCHAR(20) NOT NULL DEFAULT 'MED',
    `alarm_time` TIME(6) NOT NULL,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `repeat_days` VARCHAR(32),
    `current_med_id` INT,
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_alarms_current__65ab2c31` FOREIGN KEY (`current_med_id`) REFERENCES `current_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_alarms_users_00f32162` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_alarms_user_id_b8517f` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 설정한 알람 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `alarm_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `sent_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `delivered_at` DATETIME(6),
    `read_at` DATETIME(6),
    `is_confirmed` BOOL NOT NULL DEFAULT 0,
    `snoozed_until` DATETIME(6),
    `snooze_count` INT NOT NULL DEFAULT 0,
    `alarm_id` INT NOT NULL,
    CONSTRAINT `fk_alarm_hi_alarms_9f73e320` FOREIGN KEY (`alarm_id`) REFERENCES `alarms` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='알람 발송 내역과 사용자의 확인 여부를 기록하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `ocr_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `raw_text` LONGTEXT NOT NULL,
    `is_valid` BOOL NOT NULL DEFAULT 0,
    `inference_metadata` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    `back_upload_id` INT UNIQUE,
    `front_upload_id` INT NOT NULL UNIQUE,
    CONSTRAINT `fk_ocr_hist_users_de674177` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ocr_hist_uploads_1cf26d91` FOREIGN KEY (`back_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ocr_hist_uploads_2ee6bf89` FOREIGN KEY (`front_upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    KEY `idx_ocr_history_user_id_4cf1ec` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='이미지 내 텍스트 추출(OCR) 엔진의 분석 원본 이력을 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `prescriptions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hospital_name` VARCHAR(255),
    `prescribed_date` DATE,
    `drug_list_raw` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    `upload_id` INT NOT NULL UNIQUE,
    `ocr_history_id` INT UNIQUE,
    CONSTRAINT `fk_prescrip_users_75d98828` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prescrip_uploads_02e6e99e` FOREIGN KEY (`upload_id`) REFERENCES `uploads` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prescrip_ocr_hist_0b5733ff` FOREIGN KEY (`ocr_history_id`) REFERENCES `ocr_history` (`id`) ON DELETE CASCADE,
    KEY `idx_prescriptio_user_id_5c50a3` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자가 업로드한 처방전의 분석 결과를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `prescription_drugs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `standard_drug_name` VARCHAR(255) NOT NULL,
    `dosage_amount` DOUBLE,
    `daily_frequency` INT,
    `duration_days` INT,
    `is_linked_to_meds` BOOL NOT NULL DEFAULT 0,
    `current_med_id` INT,
    `prescription_id` INT NOT NULL,
    CONSTRAINT `fk_prescrip_current__39f1e88e` FOREIGN KEY (`current_med_id`) REFERENCES `current_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prescrip_prescrip_c35d9dcd` FOREIGN KEY (`prescription_id`) REFERENCES `prescriptions` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방전에 포함된 개별 약품 상세 정보를 관리하는 모델입니다.';
CREATE TABLE IF NOT EXISTS `blood_pressure_records` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `systolic` INT NOT NULL COMMENT '수축기(mmHg)',
    `diastolic` INT NOT NULL COMMENT '이완기(mmHg)',
    `measure_type` VARCHAR(2) NOT NULL COMMENT '측정 상황',
    `created_at` DATETIME(6) NOT NULL COMMENT '서버 저장 시각' DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL COMMENT '사용자',
    CONSTRAINT `fk_blood_pr_users_67a78557` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_blood_press_user_id_b74caa` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='혈압 기록(수축기/이완기)';
CREATE TABLE IF NOT EXISTS `blood_sugar_records` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `glucose_mg_dl` DOUBLE NOT NULL COMMENT '혈당(mg/dL)',
    `measure_type` VARCHAR(6) NOT NULL COMMENT '측정 상황(공복/식후 2시간/취침전/임의)',
    `created_at` DATETIME(6) NOT NULL COMMENT '서버 저장 시각' DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL COMMENT '사용자',
    CONSTRAINT `fk_blood_su_users_6db13992` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_blood_sugar_user_id_4f1146` (`user_id`)
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
    CONSTRAINT `fk_health_p_users_35ba10a2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_health_prof_user_id_46c128` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='사용자 건강 프로필(정적/준정적 정보)';
CREATE TABLE IF NOT EXISTS `plan_check_list` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `content` VARCHAR(255) NOT NULL,
    `plan_type` VARCHAR(20) NOT NULL DEFAULT 'self',
    `is_completed` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` VARCHAR(100) NOT NULL,
    CONSTRAINT `fk_plan_che_users_e7d8e98d` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_plan_check__user_id_fe269f` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='오늘 계획 체크 리스트';
CREATE TABLE IF NOT EXISTS `drug_masters` (
    `item_seq` VARCHAR(20) NOT NULL PRIMARY KEY,
    `item_name` VARCHAR(255) NOT NULL,
    `entp_name` VARCHAR(255) NOT NULL,
    `chart` LONGTEXT,
    `item_image` VARCHAR(500),
    `print_front` VARCHAR(100),
    `print_back` VARCHAR(100),
    `drug_shape` VARCHAR(50),
    `color_class1` VARCHAR(50),
    `color_class2` VARCHAR(50),
    `line_front` VARCHAR(50),
    `line_back` VARCHAR(50),
    `form_code_name` VARCHAR(100),
    `etc_otc_name` VARCHAR(50),
    `class_name` VARCHAR(100),
    `efcy_qesitm` LONGTEXT,
    `use_method_qesitm` LONGTEXT,
    `atpn_warn_qesitm` LONGTEXT,
    `atpn_qesitm` LONGTEXT,
    `intrc_qesitm` LONGTEXT,
    `se_qesitm` LONGTEXT,
    `deposit_method_qesitm` LONGTEXT,
    `source` VARCHAR(20) DEFAULT 'MFDS',
    `mfds_update_date` VARCHAR(20),
    `last_enriched_mfds_date` VARCHAR(20),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_master_item_na_0a4b40` (`item_name`),
    KEY `idx_drug_master_entp_na_2830c9` (`entp_name`)
) CHARACTER SET utf8mb4 COMMENT='공공데이터포털(식약처) API에서 가져온 의약품 통합 마스터 정보 모델입니다.';
CREATE TABLE IF NOT EXISTS `drug_masters_tmp` (
    `item_seq` VARCHAR(20) NOT NULL PRIMARY KEY,
    `item_name` VARCHAR(255) NOT NULL,
    `entp_name` VARCHAR(255) NOT NULL,
    `chart` LONGTEXT,
    `item_image` VARCHAR(500),
    `print_front` VARCHAR(100),
    `print_back` VARCHAR(100),
    `drug_shape` VARCHAR(50),
    `color_class1` VARCHAR(50),
    `color_class2` VARCHAR(50),
    `line_front` VARCHAR(50),
    `line_back` VARCHAR(50),
    `form_code_name` VARCHAR(100),
    `etc_otc_name` VARCHAR(50),
    `class_name` VARCHAR(100),
    `efcy_qesitm` LONGTEXT,
    `use_method_qesitm` LONGTEXT,
    `atpn_warn_qesitm` LONGTEXT,
    `atpn_qesitm` LONGTEXT,
    `intrc_qesitm` LONGTEXT,
    `se_qesitm` LONGTEXT,
    `deposit_method_qesitm` LONGTEXT,
    `source` VARCHAR(20) DEFAULT 'MFDS',
    `mfds_update_date` VARCHAR(20),
    `last_enriched_mfds_date` VARCHAR(20),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_master_item_na_ef4cbc` (`item_name`),
    KEY `idx_drug_master_entp_na_4dff6a` (`entp_name`)
) CHARACTER SET utf8mb4 COMMENT='의약품 정보 동기화 및 LLM 보충을 위한 임시 스테이징 테이블입니다.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "=="
)
