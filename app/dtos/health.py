from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.health_profile import (
    DietType,
    DrinkingStatus,
    ExerciseFrequency,
    FamilyHistory,
    SleepChange,
    SmokingStatus,
    WeightChange,
)


class ChronicDiseaseResponse(BaseModel):
    id: int
    disease_name: str
    when_to_diagnose: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChronicDiseaseListResponse(BaseModel):
    items: list[ChronicDiseaseResponse]


class ChronicDiseaseSaveRequest(BaseModel):
    name: str
    when_to_diagnose: str


class AllergyResponse(BaseModel):
    id: int
    allergy_name: str | None = None
    symptom: str | None = None
    allergy_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AllergyListResponse(BaseModel):
    items: list[AllergyResponse]


class AllergySaveRequest(BaseModel):
    allergy_type: str  # 필수
    allergy_name: str  # 필수
    symptom: str | None = None  # 선택


class BloodPressureRecordResponse(BaseModel):
    id: int
    systolic: int
    diastolic: int
    pulse: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BloodSugarRecordResponse(BaseModel):
    id: int
    glucose_mg_dl: float
    measure_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentMedResponse(BaseModel):
    id: int
    medication_name: str
    one_dose: str | None = None
    one_dose_count: str | None = None
    dose_time: str | None = None
    added_from: str | None = None
    start_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CurrentMedSaveRequest(BaseModel):
    medication_name: str  # 필수
    dose_time: str  # 필수
    one_dose: str | None = None
    one_dose_count: str | None = None
    added_from: str | None = None
    start_date: str | None = None


class HealthProfileDetailResponse(BaseModel):
    id: int

    family_history: FamilyHistory
    family_history_note: str | None = None

    height_cm: float
    weight_kg: float
    weight_change: WeightChange

    sleep_hours: float | None = None
    sleep_change: SleepChange

    smoking_status: SmokingStatus
    smoking_years: int | None = None
    smoking_per_week: float | None = None

    drinking_status: DrinkingStatus
    drinking_years: int | None = None
    drinking_per_week: float | None = None

    exercise_frequency: ExerciseFrequency
    diet_type: DietType

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthProfileResponse(BaseModel):
    health_profile: HealthProfileDetailResponse | None = None
    chronic_diseases: list[ChronicDiseaseResponse]
    allergies: list[AllergyResponse]
    current_meds: list[CurrentMedResponse]
    blood_pressure_records: list[BloodPressureRecordResponse]
    blood_sugar_records: list[BloodSugarRecordResponse]


class BloodSugarRequest(BaseModel):
    glucose_mg_dl: float
    measure_type: str


class BloodPressureRequest(BaseModel):
    systolic: str
    diastolic: str
    measure_type: str


class FullHealthProfileSaveRequest(BaseModel):
    # 기본 건강 정보
    family_history: str
    family_history_note: str | None = None

    height_cm: float | None = None
    weight_kg: float | None = None
    weight_change: str

    sleep_hours: float | None = None
    sleep_change: str

    smoking_status: str
    smoking_years: int | None = None
    smoking_per_week: float | None = None

    drinking_status: str
    drinking_years: int | None = None
    drinking_per_week: float | None = None

    exercise_frequency: str
    diet_type: str

    allergies: list[AllergySaveRequest] = Field(default_factory=list)
    chronic_diseases: list[ChronicDiseaseSaveRequest] = Field(default_factory=list)
    medications: list[CurrentMedSaveRequest] = Field(default_factory=list)
