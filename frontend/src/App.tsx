import React, { useState, useEffect } from "react";
import Recorder from "./components/Recorder";

type Message = {
  text: string;
  from: string;
  id: number;
  hasAnimated?: boolean;
  emotions?: { [key: string]: number };
};

export default function App() {
  const STORAGE_KEY = "realtime_emotion_chat_v1";
  const [chatHistory, setChatHistory] = useState<Message[]>([]);

  // Load chat history from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setChatHistory(JSON.parse(raw));
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  }, []);

  // Persist chat history to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
    } catch (e) {
      console.error("Failed to persist chat history:", e);
    }
  }, [chatHistory]);

  const handleResponse = (data: any) => {
    // Optionally update chat history with responses
    console.log("Emotion data:", data);
  };

  return <Recorder onResponse={handleResponse} history={chatHistory} />;
}
