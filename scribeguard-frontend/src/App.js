import { useState } from "react";
import RecordingScreen from "./components/RecordingScreen";
import SOAPNoteScreen from "./components/SOAPNoteScreen";

function App() {
  const [soapNote, setSoapNote] = useState(null);

  return (
    <div>
      {soapNote ? (
        <SOAPNoteScreen note={soapNote} onBack={() => setSoapNote(null)} />
      ) : (
        <RecordingScreen onNoteGenerated={setSoapNote} />
      )}
    </div>
  );
}

export default App;