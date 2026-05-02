#!/usr/bin/env python3
"""
Test the full structured extraction flow:
1. Create an encounter with a patient
2. Upload a transcript from the CSV
3. Trigger extraction
4. Print the encounter ID to view in the UI
"""
import csv
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Read a sample dialogue from the CSV
print("📖 Loading sample dialogue from CSV...")
with open("train.csv", newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    sample = next(reader)  # Get first row

dialogue = sample['dialogue']
print(f"✓ Loaded dialogue ({len(dialogue)} chars)\n")

# Create an encounter
print("🆕 Creating encounter...")
response = requests.post(
    f"{API_BASE}/encounters",
    data={
        "patient_name": "John Doe",
        "patient_id": "TEST-001",
        "openmrs_uuid": None,
        "patient_type": "new"
    }
)
response.raise_for_status()
encounter = response.json()
encounter_id = encounter['id']
print(f"✓ Created encounter: {encounter_id}\n")

# Upload the transcript
print("📝 Uploading transcript...")
response = requests.patch(
    f"{API_BASE}/encounters/{encounter_id}",
    json={"transcript": dialogue}
)
response.raise_for_status()
print("✓ Transcript uploaded\n")

# Trigger extraction
print("🤖 Running LLM extraction (this may take 10-15 seconds)...")
response = requests.post(f"{API_BASE}/encounters/{encounter_id}/generate")
response.raise_for_status()
print("✓ Extraction complete!\n")

# Fetch the full encounter
response = requests.get(f"{API_BASE}/encounters/{encounter_id}")
response.raise_for_status()
data = response.json()

# Display extracted data
print("=" * 70)
print("📋 EXTRACTED CLINICAL DATA")
print("=" * 70)
print(f"\n🎯 Chief Complaint:")
print(f"   {data.get('chief_complaint') or '(none)'}\n")

print(f"🩺 Vitals:")
if data.get('vitals'):
    for k, v in data['vitals'].items():
        print(f"   {k}: {v}")
else:
    print("   (none)")

print(f"\n💊 Active Medications: {len(data.get('medications', []))}")
for med in data.get('medications', []):
    print(f"   • {med['name']} {med.get('dose', '')} {med.get('frequency', '')}")

print(f"\n🧬 Past Medications: {len(data.get('past_medications', []))}")
for pm in data.get('past_medications', []):
    print(f"   • {pm['name']} (discontinued: {pm.get('reason', 'unknown')})")

print(f"\n🤧 Allergies: {len(data.get('allergies', []))}")
for a in data.get('allergies', []):
    print(f"   • {a['allergen']} - {a.get('reaction', '')} ({a.get('severity', '')})")

print(f"\n🏥 Diagnoses: {len(data.get('diagnoses', []))}")
for dx in data.get('diagnoses', []):
    print(f"   • [{dx.get('icd10_code', '')}] {dx['description']} ({dx.get('status', '')})")

print(f"\n💉 Immunizations: {len(data.get('immunizations', []))}")
for imm in data.get('immunizations', []):
    print(f"   • {imm['vaccine_name']} ({imm.get('date_given', '')})")

print(f"\n📊 Clinical Summary:")
summary = data.get('clinical_summary', '')
print(f"   {summary[:200]}{'...' if len(summary) > 200 else ''}\n")

print(f"📋 Plan:")
plan = data.get('plan', '')
print(f"   {plan[:200]}{'...' if len(plan) > 200 else ''}\n")

print("=" * 70)
print(f"\n✨ Test complete! View in UI:")
print(f"   http://localhost:5173/notes/{encounter_id}")
print(f"\nNote: Approval button will be locked until you open the note (viewed=false)")
print("=" * 70)
