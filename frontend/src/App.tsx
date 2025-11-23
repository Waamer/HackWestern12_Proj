import React, { useEffect, useState } from "react";
import Recorder from "./components/Recorder";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  audio?: string | null; // basename for assistant audio
  emotions?: Record<string, number> | null;
  pending?: boolean;
};

export default function App() {
  const STORAGE_KEY = "realtime_emotion_chat_v1";

  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    // Load persisted chat from localStorage
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setMessages(JSON.parse(raw));
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  }, []);

  useEffect(() => {
    // Persist chat to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
      console.error("Failed to persist chat history:", e);
    }
  }, [messages]);

  const handleResponse = (data: any) => {
    // data may be pending transcript or final server response
    if (data && data.pending && data.transcript) {
      // Add a pending user message
      const msg: ChatMessage = {
        id: `m_${Date.now()}`,
        role: "user",
        text: data.transcript,
        emotions: null,
        pending: true,
      };
      setMessages((m) => [...m, msg]);
      return;
    }

    if (data && data.transcript && data.emotions) {
      // Replace the last pending user message (if any) and add assistant reply
      setMessages((m) => {
        const copy = [...m];
        // find last pending user
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].role === "user" && copy[i].pending) {
            copy[i] = { ...copy[i], pending: false, emotions: data.emotions };
            break;
          }
        }
        // add assistant message
        const assistant: ChatMessage = {
          id: `m_${Date.now()}_a`,
          role: "assistant",
          text: data.reply_text || "",
          audio: data.reply_audio_path || null,
          pending: false,
        };
        copy.push(assistant);
        return copy;
      });
      return;
    }

    // If arbitrary data without emotions, just append as assistant
    if (data && data.reply_text) {
      const assistant: ChatMessage = {
        id: `m_${Date.now()}_a`,
        role: "assistant",
        text: data.reply_text || "",
        audio: data.reply_audio_path || null,
        pending: false,
      };
      setMessages((m) => [...m, assistant]);
    }
  };

  return (
    <div className="app">
      <h1>Realtime Emotion + Chat</h1>
      <Recorder onResponse={handleResponse} history={messages} />

      <div className="chat">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-${msg.role}`}>
            <strong>{msg.role === "user" ? "You" : "Assistant"}:</strong>
            <p>{msg.text}</p>
            {msg.emotions && (
              <pre>{JSON.stringify(msg.emotions, null, 2)}</pre>
            )}
            {msg.audio && (
              <audio controls src={`http://localhost:5000/api/tts-file/${msg.audio}`} />
            )}
            {msg.pending && <em>Processing...</em>}
          </div>
        ))}
      </div>
    </div>
  );
}
