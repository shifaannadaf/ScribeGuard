export type RecordStatus = 'pending' | 'approved' | 'pushed'

export interface PatientRecord {
  id: string
  patientName: string
  patientId: string
  date: string
  time: string
  duration: string
  status: RecordStatus
  snippet: string
  transcription: { speaker: 'Doctor' | 'Patient'; text: string }[]
}

export const MOCK_RECORDS: PatientRecord[] = [
  {
    id: '1',
    patientName: 'John Doe',
    patientId: 'P-00123',
    date: '2026-04-25',
    time: '09:14 AM',
    duration: '4m 32s',
    status: 'pending',
    snippet: 'Patient complains of persistent headache for 3 days, mild nausea, no fever…',
    transcription: [
      { speaker: 'Doctor',  text: "Good morning John, what brings you in today?" },
      { speaker: 'Patient', text: "I have had this headache for about three days now. It won't go away." },
      { speaker: 'Doctor',  text: "Is the pain throbbing or constant?" },
      { speaker: 'Patient', text: "Throbbing, mostly behind my eyes. And I feel a bit nauseous." },
      { speaker: 'Doctor',  text: "Any fever, stiff neck, or sensitivity to light?" },
      { speaker: 'Patient', text: "No fever. Light does bother me a little." },
      { speaker: 'Doctor',  text: "Any recent illness or stress? Have you been sleeping okay?" },
      { speaker: 'Patient', text: "Work has been stressful. Sleep is probably four to five hours a night." },
      { speaker: 'Doctor',  text: "Have you taken anything for the pain?" },
      { speaker: 'Patient', text: "Ibuprofen, it helps a bit but comes back after a few hours." },
    ],
  },
  {
    id: '2',
    patientName: 'Sarah Miller',
    patientId: 'P-00089',
    date: '2026-04-25',
    time: '11:02 AM',
    duration: '6m 10s',
    status: 'approved',
    snippet: 'Follow-up for Type 2 diabetes. Blood glucose stable on metformin 500mg…',
    transcription: [
      { speaker: 'Doctor',  text: "Hi Sarah, how have you been feeling since your last visit?" },
      { speaker: 'Patient', text: "Pretty good overall. My energy is better." },
      { speaker: 'Doctor',  text: "Your latest A1C came back at 6.8, which is within our target range." },
      { speaker: 'Patient', text: "That's a relief. I have been watching what I eat more carefully." },
      { speaker: 'Doctor',  text: "Are you still on metformin 500mg twice a day?" },
      { speaker: 'Patient', text: "Yes, no issues with it. The stomach upset I had is gone." },
      { speaker: 'Doctor',  text: "Good. Let's keep the current dose and recheck in three months." },
    ],
  },
  {
    id: '3',
    patientName: 'Robert Chen',
    patientId: 'P-00210',
    date: '2026-04-24',
    time: '03:45 PM',
    duration: '3m 55s',
    status: 'pushed',
    snippet: 'Annual physical. No acute complaints. BP 122/78, HR 68…',
    transcription: [
      { speaker: 'Doctor',  text: "Robert, you are here for your annual physical today, correct?" },
      { speaker: 'Patient', text: "Yes, no specific complaints. Just the regular check." },
      { speaker: 'Doctor',  text: "Blood pressure is 122 over 78, heart rate 68. Looks excellent." },
      { speaker: 'Patient', text: "Good to hear. I have been exercising more regularly." },
      { speaker: 'Doctor',  text: "Lungs are clear, abdomen soft, no abnormalities on exam." },
      { speaker: 'Patient', text: "Do I need any bloodwork?" },
      { speaker: 'Doctor',  text: "We will run a standard metabolic panel and lipid profile. I'll send the order in." },
    ],
  },
  {
    id: '4',
    patientName: 'Priya Nair',
    patientId: 'P-00314',
    date: '2026-04-23',
    time: '02:10 PM',
    duration: '5m 20s',
    status: 'approved',
    snippet: 'Chest tightness on exertion. Denies rest pain. ECG ordered…',
    transcription: [
      { speaker: 'Doctor',  text: "Priya, you mentioned chest tightness on the intake form?" },
      { speaker: 'Patient', text: "Yes, it happens when I climb stairs or walk fast. Goes away when I stop." },
      { speaker: 'Doctor',  text: "Any pain at rest, palpitations, or shortness of breath?" },
      { speaker: 'Patient', text: "No pain at rest. Mild shortness of breath with the tightness." },
      { speaker: 'Doctor',  text: "How long has this been going on?" },
      { speaker: 'Patient', text: "About two weeks. It is getting a little more frequent." },
      { speaker: 'Doctor',  text: "I want to get an ECG today and refer you for a stress test." },
      { speaker: 'Patient', text: "Okay, should I be worried?" },
      { speaker: 'Doctor',  text: "Let's not jump ahead. The tests will give us a clearer picture." },
    ],
  },
  {
    id: '5',
    patientName: 'Marcus Webb',
    patientId: 'P-00401',
    date: '2026-04-22',
    time: '10:30 AM',
    duration: '7m 01s',
    status: 'pushed',
    snippet: 'Post-op follow-up, laparoscopic appendectomy. Wound healing well…',
    transcription: [
      { speaker: 'Doctor',  text: "Marcus, it has been two weeks since your appendectomy. How are you feeling?" },
      { speaker: 'Patient', text: "Much better. The soreness is almost gone." },
      { speaker: 'Doctor',  text: "Let me take a look at the incision sites." },
      { speaker: 'Patient', text: "Sure. The small one on the right was itchy for a while." },
      { speaker: 'Doctor',  text: "All three sites look clean, no sign of infection, healing nicely." },
      { speaker: 'Patient', text: "When can I get back to the gym?" },
      { speaker: 'Doctor',  text: "Light activity is fine now. Hold off on heavy lifting for another two weeks." },
      { speaker: 'Patient', text: "What about diet? Any restrictions still?" },
      { speaker: 'Doctor',  text: "No restrictions at this point. Eat normally, stay hydrated." },
    ],
  },
]
