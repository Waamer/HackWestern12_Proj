import React, { useEffect, useRef, useState } from "react";

type Props = {
  onResponse: (data: any) => void;
  history: Array<{ id: string; role: string; text: string }>; // last messages from App
};

function floatTo16BitPCM(float32Array: Float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return view;
}

function encodeWAV(samples: Float32Array, sampleRate: number) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  /* RIFF identifier */ writeString(view, 0, "RIFF");
  /* file length */ view.setUint32(4, 36 + samples.length * 2, true);
  /* RIFF type */ writeString(view, 8, "WAVE");
  /* format chunk identifier */ writeString(view, 12, "fmt ");
  /* format chunk length */ view.setUint32(16, 16, true);
  /* sample format (raw) */ view.setUint16(20, 1, true);
  /* channel count */ view.setUint16(22, 1, true);
  /* sample rate */ view.setUint32(24, sampleRate, true);
  /* byte rate (sampleRate * blockAlign) */ view.setUint32(28, sampleRate * 2, true);
  /* block align (channel count * bytes per sample) */ view.setUint16(32, 2, true);
  /* bits per sample */ view.setUint16(34, 16, true);
  /* data chunk identifier */ writeString(view, 36, "data");
  /* data chunk length */ view.setUint32(40, samples.length * 2, true);

  const pcmView = floatTo16BitPCM(samples);
  // copy pcm data
  for (let i = 0; i < pcmView.byteLength; i++) {
    view.setUint8(44 + i, pcmView.getUint8(i));
  }

  return new Blob([view], { type: "audio/wav" });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

export default function Recorder({ onResponse, history }: Props) {
  const [recording, setRecording] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const buffersRef = useRef<Float32Array[]>([]);

  const [transcript, setTranscript] = useState("");
  const transcriptRef = useRef("");
  const recognitionRef = useRef<any>(null);
  const recognitionPromiseResolver = useRef<((value: unknown) => void) | null>(null);
  const isRecordingRef = useRef(false); // Track recording state for auto-restart

  useEffect(() => {
    return () => {
      stopRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startSpeechRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Web Speech API not supported in this browser.");
      alert("Web Speech API not supported. Please use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (finalTranscript) {
        transcriptRef.current += " " + finalTranscript;
      }
      // Update UI with current total + interim
      setTranscript(transcriptRef.current + " " + interimTranscript);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      // Don't restart on aborted (user stopped) or not-allowed (permissions)
      if (event.error === 'aborted' || event.error === 'not-allowed') {
        return;
      }
      // Auto-restart on other errors if still recording
      if (isRecordingRef.current && recognitionRef.current) {
        console.log("Auto-restarting speech recognition...");
        setTimeout(() => {
          if (isRecordingRef.current) {
            try {
              recognitionRef.current?.start();
            } catch (e) {
              console.error("Failed to restart recognition:", e);
            }
          }
        }, 100);
      }
    };

    recognition.onend = () => {
      console.log("Speech recognition ended");
      // Auto-restart if we're still recording
      if (isRecordingRef.current && !recognitionPromiseResolver.current) {
        console.log("Auto-restarting speech recognition (ended unexpectedly)...");
        setTimeout(() => {
          if (isRecordingRef.current) {
            try {
              recognitionRef.current?.start();
            } catch (e) {
              console.error("Failed to restart recognition:", e);
            }
          }
        }, 100);
      } else if (recognitionPromiseResolver.current) {
        // User intentionally stopped
        recognitionPromiseResolver.current(true);
        recognitionPromiseResolver.current = null;
      }
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      console.log("Speech recognition started");
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
    }
  };

  const startRecording = async () => {
    setTranscript("");
    transcriptRef.current = "";
    buffersRef.current = [];
    isRecordingRef.current = true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioContextClass();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e: AudioProcessingEvent) => {
        const input = e.inputBuffer.getChannelData(0);
        buffersRef.current.push(new Float32Array(input));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      // Start Speech Recognition with auto-restart capability
      startSpeechRecognition();

      setRecording(true);
    } catch (err) {
      console.error("Error starting recording:", err);
      alert("Could not access microphone. Please allow permissions.");
      isRecordingRef.current = false;
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setRecording(false);
    isRecordingRef.current = false;

    // Stop Speech Recognition and wait for it to finish
    if (recognitionRef.current) {
      const stopPromise = new Promise((resolve) => {
        recognitionPromiseResolver.current = resolve;
      });
      recognitionRef.current.stop();

      // Wait a bit for the final result to process, but not too long
      const timeoutPromise = new Promise(resolve => setTimeout(resolve, 1000));
      await Promise.race([stopPromise, timeoutPromise]);

      recognitionRef.current = null;
    }

    const processor = processorRef.current;
    const source = sourceRef.current;
    const audioCtx = audioCtxRef.current;

    if (processor && source && audioCtx) {
      processor.disconnect();
      source.disconnect();
      try {
        processor.onaudioprocess = null;
      } catch (e) { }
    }

    // concat buffers
    const totalLength = buffersRef.current.reduce((acc, b) => acc + b.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const b of buffersRef.current) {
      merged.set(b, offset);
      offset += b.length;
    }

    const sampleRate = audioCtx ? audioCtx.sampleRate : 48000;
    const wavBlob = encodeWAV(merged, sampleRate);

    const fd = new FormData();
    fd.append("audio", wavBlob, "clip.wav");
    fd.append("do_chat", "true");

    const textToSend = transcriptRef.current.trim();
    console.log("Sending transcript:", textToSend);
    fd.append("transcript", textToSend);
    // Attach recent history to help LM keep context (JSON string)
    try {
      const hist = (history || []).slice(-20).map((m) => ({ role: m.role, content: m.text }));
      fd.append("history", JSON.stringify(hist));
    } catch (e) {
      console.error("Failed to attach history:", e);
    }

    // Immediately notify the app with the transcript so it can show a speech
    // bubble while the server computes emotions (this is the "speech bubble" step).
    try {
      onResponse({ transcript: textToSend, emotions: null, pending: true });
    } catch (e) {
      console.error("onResponse callback error (pre-send):", e);
    }

    try {
      const controller = new AbortController();
      // Save controller so unload/stop can abort
      (window as any)._currentAbort = controller;

      const res = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        body: fd,
        signal: controller.signal,
      });
      const data = await res.json();
      console.log("Server response:", data);
      // Server returns emotions and optionally reply_text; forward to app
      onResponse(data);
    } catch (err) {
      console.error("Upload error", err);
    }

    // close audio context
    try {
      if (audioCtx) {
        await audioCtx.close();
      }
    } catch (e) { }
    audioCtxRef.current = null;
    sourceRef.current = null;
    processorRef.current = null;
    buffersRef.current = [];
  };

  return (
    <div className="recorder">
      <button onClick={startRecording} disabled={recording}>
        Start
      </button>
      <button onClick={stopRecording} disabled={!recording}>
        Stop
      </button>
      <p>{recording ? "Recording... (Speak now)" : "Idle"}</p>
      {recording && (
        <div style={{ marginTop: 10, padding: 10, border: "1px solid #ccc" }}>
          <strong>Live Transcript:</strong>
          <p>{transcript || "(Listening...)"}</p>
        </div>
      )}
    </div>
  );
}
