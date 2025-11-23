import React, { useState } from "react";
import Recorder from "./components/Recorder";

export default function App() {
  const [result, setResult] = useState<any>(null);

  const handleResponse = (data: any) => {
    setResult(data);
    console.log("Emotion data:", data);
  };

  return <Recorder onResponse={handleResponse} />;
}
