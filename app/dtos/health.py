from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ChronicDiseaseResponse(BaseModel):
    id: int
    disease_name: str

    model_config = ConfigDict(from_attributes=True)


class ChronicDiseaseListResponse(BaseModel):
    items: list[ChronicDiseaseResponse]


class ChronicDiseaseCreateRequest(BaseModel):
    disease_name: str


class AllergyResponse(BaseModel):
    id: int
    any_allergy: str

    model_config = ConfigDict(from_attributes=True)


class AllergyListResponse(BaseModel):
    items: list[AllergyResponse]


class AllergyCreateRequest(BaseModel):
    allergy_name: str


class BloodPressureRecordResponse(BaseModel):
    id: int
    systolic: int
    diastolic: int
    pulse: int | None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BloodSugarRecordResponse(BaseModel):
    id: int
    glucose_mg_dl: float
    measure_type: str
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentMedResponse(BaseModel):
    id: int
    medication_name: str
    start_date: date | None

    model_config = ConfigDict(from_attributes=True)


class HealthProfileDetailResponse(BaseModel):
    id: int
    family_history: bool
    family_history_father_note: str | None
    family_history_mother_note: str | None
    height_cm: float | None
    weight_kg: float | None
    weight_change: str
    job: str | None
    smoking_status: str
    smoking_years: int | None
    smoking_per_week: float | None
    drinking_status: str
    drinking_years: int | None
    drinking_per_week: float | None
    exercise_frequency: str
    diet_type: str

    model_config = ConfigDict(from_attributes=True)


class HealthProfileResponse(BaseModel):
    health_profile: HealthProfileDetailResponse | None
    chronic_diseases: list[ChronicDiseaseResponse]
    allergies: list[AllergyResponse]
    current_meds: list[CurrentMedResponse]
    blood_pressure_records: list[BloodPressureRecordResponse]
    blood_sugar_records: list[BloodSugarRecordResponse]
