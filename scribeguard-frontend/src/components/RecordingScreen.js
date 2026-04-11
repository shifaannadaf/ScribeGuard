import { useState, useRef } from "react";

function RecordingScreen({ onNoteGenerated }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorderRef.current = new MediaRecorder(stream);
    chunksRef.current = [];

    mediaRecorderRef.current.ondataavailable = (e) => {
      chunksRef.current.push(e.data);
    };

    mediaRecorderRef.current.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const file = new File([blob], "recording.webm", { type: "audio/webm" });
      setAudioFile(file);
    };

    mediaRecorderRef.current.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const handleFileUpload = (e) => {
    setAudioFile(e.target.files[0]);
  };

  const handleSubmit = async () => {
    if (!audioFile) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("audio", audioFile);

      const response = await fetch("http://127.0.0.1:8000/process-audio", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      onNoteGenerated(data);
    } catch (err) {
      setError("Something went wrong. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "50px auto", fontFamily: "Arial" }}>
      <h1>ScribeGuard</h1>
      <h2>Record or Upload Audio</h2>

      <div style={{ marginBottom: "20px" }}>
        {!isRecording ? (
          <button onClick={startRecording} style={buttonStyle("green")}>
            🎙️ Start Recording
          </button>
        ) : (
          <button onClick={stopRecording} style={buttonStyle("red")}>
            ⏹️ Stop Recording
          </button>
        )}
      </div>

      <div style={{ marginBottom: "20px" }}>
        <p>Or upload an audio file:</p>
        <input type="file" accept="audio/*" onChange={handleFileUpload} />
      </div>

      {audioFile && (
        <p style={{ color: "green" }}>✅ Audio ready: {audioFile.name}</p>
      )}

      {error && <p style={{ color: "red" }}>{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={!audioFile || loading}
        style={buttonStyle("blue")}
      >
        {loading ? "Processing..." : "Generate SOAP Note"}
      </button>
    </div>
  );
}

const buttonStyle = (color) => ({
  backgroundColor: color,
  color: "white",
  padding: "10px 20px",
  border: "none",
  borderRadius: "5px",
  cursor: "pointer",
  fontSize: "16px",
  marginRight: "10px",
});

export default RecordingScreen;