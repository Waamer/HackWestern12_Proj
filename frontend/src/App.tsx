import React, { useState } from "react";
import Recorder from "./components/Recorder";
import axios from "axios";

export default function App() {
  const [result, setResult] = useState<any>(null);

  const handleResponse = (data: any) => {
    setResult(data);
  };

  return (
    <div className="app">
      <h1>Realtime Emotion + Chat</h1>
      <Recorder onResponse={handleResponse} />

      {result && (
        <div className="results">
          <h2>Emotions</h2>
          <pre>{JSON.stringify(result.emotions, null, 2)}</pre>
          {result.transcript && (
            <>
              <h3>Transcript</h3>
              <p>{result.transcript}</p>
            </>
          )}
          {result.reply_text && (
            <>
              <h3>Assistant</h3>
              <p>{result.reply_text}</p>
            </>
          )}
          {result.reply_audio_path && (
            <audio
              controls
              autoPlay
              src={`http://localhost:5000/api/tts-file/${result.reply_audio_path}`}
            />
          )}
        </div>
      )}
    </div>
  );
}
