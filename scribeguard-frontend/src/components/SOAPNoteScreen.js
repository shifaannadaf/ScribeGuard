import { useState } from "react";
function SOAPNoteScreen({ note, onBack }) {
    const [editedNote, setEditedNote] = useState({ ...note });
  
    const handleChange = (field, value) => {
      setEditedNote((prev) => ({ ...prev, [field]: value }));
    };
  
    return (
      <div style={{ maxWidth: "700px", margin: "50px auto", fontFamily: "Arial" }}>
        <div style={{ backgroundColor: "#fff3cd", padding: "10px", borderRadius: "5px", marginBottom: "20px" }}>
          <strong>⚠️ AI-Generated — Pending Review</strong>
        </div>
  
        <h1>SOAP Note</h1>
  
        {["subjective", "objective", "assessment", "plan"].map((section) => (
          <div key={section} style={{ marginBottom: "20px" }}>
            <h3>{section.toUpperCase()}</h3>
            <textarea
              value={editedNote[section]}
              onChange={(e) => handleChange(section, e.target.value)}
              style={{ width: "100%", height: "100px", padding: "10px", fontSize: "14px" }}
            />
          </div>
        ))}
  
        <div style={{ marginBottom: "20px" }}>
          <h3>MEDICATIONS</h3>
          {editedNote.medications && editedNote.medications.length > 0 ? (
            <ul>
              {editedNote.medications.map((med, i) => (
                <li key={i}>{med}</li>
              ))}
            </ul>
          ) : (
            <p>No medications found.</p>
          )}
        </div>
  
        <button
          style={{ backgroundColor: "blue", color: "white", padding: "10px 20px", border: "none", borderRadius: "5px", cursor: "pointer", fontSize: "16px", marginRight: "10px" }}
        >
          ✅ Approve & Submit
        </button>
  
        <button
          onClick={onBack}
          style={{ backgroundColor: "gray", color: "white", padding: "10px 20px", border: "none", borderRadius: "5px", cursor: "pointer", fontSize: "16px" }}
        >
          ← Back
        </button>
      </div>
    );
  }
  
  export default SOAPNoteScreen;