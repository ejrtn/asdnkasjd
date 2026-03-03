import asyncio

from tortoise import Tortoise

from app.db.databases import TORTOISE_APP_MODELS
from app.models.allergy import Allergy
from app.models.blood_pressure_record import BloodPressureRecord
from app.models.blood_sugar_record import BloodSugarRecord
from app.models.chronic_disease import ChronicDisease
from app.models.current_med import CurrentMed
from app.models.health_profile import HealthProfile
from app.utils.default_data import DefaultData


async def run_verification():
    # 1. Initialize Tortoise with SQLite in-memory
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS})
    await Tortoise.generate_schemas()

    print("--- Starting Data Population ---")
    # 2. Run default data creation
    default_data = DefaultData()
    await default_data.create_default_data()
    print("--- Data Population Completed ---\n")

    # 3. Verify records
    print("--- Verifying Records ---")

    # Allergies
    allergies = await Allergy.all()
    print(f"Allergies count: {len(allergies)}")
    for a in allergies:
        print(f" - {a.pill_allergy}, {a.food_allergy}, {a.any_allergy}, {a.symptom}")
    assert len(allergies) > 0

    # Chronic Diseases
    diseases = await ChronicDisease.all()
    print(f"Chronic Diseases count: {len(diseases)}")
    for d in diseases:
        print(f" - {d.disease_name} (Diagnosed: {d.when_to_Diagnose})")
    assert len(diseases) >= 2

    # Current Meds
    meds = await CurrentMed.all()
    print(f"Current Meds count: {len(meds)}")
    for m in meds:
        print(f" - {m.medication_name}: {m.one_dose}, {m.daily_dose_count}, {m.one_dose_count}, {m.dose_time}")
    assert len(meds) >= 2

    # Health Profile
    profile = await HealthProfile.first()
    print(f"Health Profile found: {profile is not None}")
    if profile:
        print(f" - Weight Change: {profile.weight_change}")
        print(f" - Exercise: {profile.exercise_frequency}")
    assert profile is not None

    # Blood Pressure
    bp_records = await BloodPressureRecord.all()
    print(f"Blood Pressure records: {len(bp_records)}")
    assert len(bp_records) >= 6

    # Blood Sugar
    bs_records = await BloodSugarRecord.all()
    print(f"Blood Sugar records: {len(bs_records)}")
    assert len(bs_records) >= 6

    print("\n--- Verification Successful! ---")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_verification())
