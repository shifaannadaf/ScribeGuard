"""
Seed the database with mock encounter data.
Usage:  python seed.py
"""
from datetime import datetime, timezone
from app.db.database import engine, Base, SessionLocal
import app.models.models  # noqa: registers all models
from app.models.models import Encounter, Medication, Allergy, Diagnosis, AuditLog, EncounterStatus

ENCOUNTERS = [
    {
        "id": "enc-00001",
        "patient_name": "John Doe",
        "patient_id": "P-00123",
        "duration": "4m 32s",
        "status": EncounterStatus.pending,
        "created_at": datetime(2026, 4, 25, 9, 14, tzinfo=timezone.utc),
        "transcript": (
            "Doctor: Good morning, what brings you in today?\n\n"
            "Patient: I have had this headache for about three days now. It won't go away.\n\n"
            "Doctor: Is the pain throbbing or constant?\n\n"
            "Patient: Throbbing, mostly behind my eyes. And I feel a bit nauseous.\n\n"
            "Doctor: Any fever, stiff neck, or sensitivity to light?\n\n"
            "Patient: No fever. Light does bother me a little.\n\n"
            "Doctor: Any recent illness or stress? Have you been sleeping okay?\n\n"
            "Patient: Work has been stressful. Sleep is probably four to five hours a night.\n\n"
            "Doctor: Have you taken anything for the pain?\n\n"
            "Patient: Ibuprofen, it helps a bit but comes back after a few hours."
        ),
        "medications": [
            {"name": "Ibuprofen", "dose": "400mg", "route": "Oral", "frequency": "As needed", "start_date": "2026-04-25"},
        ],
        "allergies": [
            {"allergen": "Penicillin", "reaction": "Rash", "severity": "Moderate"},
        ],
        "diagnoses": [
            {"icd10_code": "G43.909", "description": "Migraine, unspecified", "status": "Presumed"},
        ],
    },
    {
        "id": "enc-00002",
        "patient_name": "Sarah Miller",
        "patient_id": "P-00089",
        "duration": "6m 10s",
        "status": EncounterStatus.approved,
        "created_at": datetime(2026, 4, 25, 11, 2, tzinfo=timezone.utc),
        "transcript": (
            "Doctor: Hi Sarah, how have you been feeling since your last visit?\n\n"
            "Patient: Pretty good overall. My energy is better.\n\n"
            "Doctor: Your latest A1C came back at 6.8, which is within our target range.\n\n"
            "Patient: That's a relief. I have been watching what I eat more carefully.\n\n"
            "Doctor: Are you still on metformin 500mg twice a day?\n\n"
            "Patient: Yes, no issues with it. The stomach upset I had is gone.\n\n"
            "Doctor: Good. Let's keep the current dose and recheck in three months."
        ),
        "medications": [
            {"name": "Metformin", "dose": "500mg", "route": "Oral", "frequency": "Twice daily", "start_date": "2026-01-10"},
        ],
        "allergies": [],
        "diagnoses": [
            {"icd10_code": "E11.9", "description": "Type 2 Diabetes Mellitus", "status": "Confirmed"},
        ],
    },
    {
        "id": "enc-00003",
        "patient_name": "Robert Chen",
        "patient_id": "P-00210",
        "duration": "3m 55s",
        "status": EncounterStatus.pushed,
        "created_at": datetime(2026, 4, 24, 15, 45, tzinfo=timezone.utc),
        "transcript": (
            "Doctor: Robert, you are here for your annual physical today, correct?\n\n"
            "Patient: Yes, no specific complaints. Just the regular check.\n\n"
            "Doctor: Blood pressure is 122 over 78, heart rate 68. Looks excellent.\n\n"
            "Patient: Good to hear. I have been exercising more regularly.\n\n"
            "Doctor: Lungs are clear, abdomen soft, no abnormalities on exam.\n\n"
            "Patient: Do I need any bloodwork?\n\n"
            "Doctor: We will run a standard metabolic panel and lipid profile."
        ),
        "medications": [],
        "allergies": [],
        "diagnoses": [
            {"icd10_code": "Z00.00", "description": "Annual physical exam, no complaints", "status": "Confirmed"},
        ],
    },
    {
        "id": "enc-00004",
        "patient_name": "Priya Nair",
        "patient_id": "P-00314",
        "duration": "5m 20s",
        "status": EncounterStatus.approved,
        "created_at": datetime(2026, 4, 23, 14, 10, tzinfo=timezone.utc),
        "transcript": (
            "Doctor: Priya, you mentioned chest tightness on the intake form?\n\n"
            "Patient: Yes, it happens when I climb stairs or walk fast. Goes away when I stop.\n\n"
            "Doctor: Any pain at rest, palpitations, or shortness of breath?\n\n"
            "Patient: No pain at rest. Mild shortness of breath with the tightness.\n\n"
            "Doctor: How long has this been going on?\n\n"
            "Patient: About two weeks. It is getting a little more frequent.\n\n"
            "Doctor: I want to get an ECG today and refer you for a stress test.\n\n"
            "Patient: Okay, should I be worried?\n\n"
            "Doctor: Let's not jump ahead. The tests will give us a clearer picture."
        ),
        "medications": [],
        "allergies": [
            {"allergen": "Sulfonamides", "reaction": "Anaphylaxis", "severity": "Severe"},
        ],
        "diagnoses": [
            {"icd10_code": "R07.9", "description": "Chest pain, unspecified", "status": "Presumed"},
        ],
    },
    {
        "id": "enc-00005",
        "patient_name": "Marcus Webb",
        "patient_id": "P-00401",
        "duration": "7m 01s",
        "status": EncounterStatus.pushed,
        "created_at": datetime(2026, 4, 22, 10, 30, tzinfo=timezone.utc),
        "transcript": (
            "Doctor: Marcus, it has been two weeks since your appendectomy. How are you feeling?\n\n"
            "Patient: Much better. The soreness is almost gone.\n\n"
            "Doctor: All three incision sites look clean, no sign of infection, healing nicely.\n\n"
            "Patient: When can I get back to the gym?\n\n"
            "Doctor: Light activity is fine now. Hold off on heavy lifting for another two weeks.\n\n"
            "Patient: What about diet? Any restrictions still?\n\n"
            "Doctor: No restrictions at this point. Eat normally, stay hydrated."
        ),
        "medications": [],
        "allergies": [],
        "diagnoses": [
            {"icd10_code": "Z09", "description": "Post-op follow-up, laparoscopic appendectomy", "status": "Confirmed"},
        ],
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for data in ENCOUNTERS:
            if db.get(Encounter, data["id"]):
                print(f"  ⚠  {data['patient_name']} already exists, skipping")
                continue

            enc = Encounter(
                id=data["id"],
                patient_name=data["patient_name"],
                patient_id=data["patient_id"],
                duration=data["duration"],
                status=data["status"],
                transcript=data["transcript"],
                created_at=data["created_at"],
                updated_at=data["created_at"],
            )
            db.add(enc)

            for m in data["medications"]:
                db.add(Medication(encounter_id=enc.id, **m))
            for a in data["allergies"]:
                db.add(Allergy(encounter_id=enc.id, **a))
            for d in data["diagnoses"]:
                db.add(Diagnosis(encounter_id=enc.id, **d))

            db.add(AuditLog(encounter_id=enc.id, action="created", actor="seed"))
            print(f"  ✓  {data['patient_name']} ({data['id']})")

        db.commit()
        print("\nSeeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database...\n")
    seed()
