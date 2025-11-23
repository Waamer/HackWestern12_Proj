import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Mic, PhoneOff, Phone } from "lucide-react";
import { Messages } from "./Messages";
import { Visualizer } from "react-sound-visualizer";

interface Message {
  text: string;
  from: string;
  id: number;
  hasAnimated?: boolean;
  emotions?: { [key: string]: number };
}

type Props = {
  onResponse: (data: any) => void;
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

export default function Recorder({ onResponse }: Props) {
  const [isCallActive, setIsCallActive] = useState(false);
  const [recording, setRecording] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [responseProcessing, setResponseProcessing] = useState(false);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [transcripts, setTranscripts] = useState<Message[]>([]);
  const [AIResponses, setAIResponses] = useState<Message[]>([
    {
      text: "Oh, hey.",
      from: "Assistant",
      id: 0,
      hasAnimated: true,
    },
  ]);
  
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const buffersRef = useRef<Float32Array[]>([]);
  const messageCountRef = useRef<number>(1);
  
  // Speech recognition
  const [transcript, setTranscript] = useState("");
  const transcriptRef = useRef("");
  const recognitionRef = useRef<any>(null);
  const recognitionPromiseResolver = useRef<((value: unknown) => void) | null>(null);
  const isRecordingRef = useRef(false);

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
      alert("Speech recognition not supported. Please use Chrome or Edge. Your audio will still be analyzed for emotions.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

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
        console.log("Final transcript:", finalTranscript);
      }
      const fullTranscript = transcriptRef.current + " " + interimTranscript;
      console.log("Current transcript:", fullTranscript);
      setTranscript(fullTranscript);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === 'aborted' || event.error === 'not-allowed') {
        return;
      }
      if (isRecordingRef.current && recognitionRef.current) {
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
      if (isRecordingRef.current && !recognitionPromiseResolver.current) {
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
        recognitionPromiseResolver.current(true);
        recognitionPromiseResolver.current = null;
      }
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
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
      setAudioStream(stream);
    
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

    startSpeechRecognition();

    setRecording(true);
    setIsRecording(true);
    } catch (err) {
      console.error("Error starting recording:", err);
      isRecordingRef.current = false;
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setRecording(false);
    setIsRecording(false);
    setResponseProcessing(true);
    isRecordingRef.current = false;

    // Stop speech recognition
    if (recognitionRef.current) {
      const stopPromise = new Promise((resolve) => {
        recognitionPromiseResolver.current = resolve;
      });
      recognitionRef.current.stop();
      const timeoutPromise = new Promise(resolve => setTimeout(resolve, 1000));
      await Promise.race([stopPromise, timeoutPromise]);
      recognitionRef.current = null;
    }

    // Stop audio stream
    if (audioStream) {
      audioStream.getTracks().forEach((track) => track.stop());
      setAudioStream(null);
    }

    const processor = processorRef.current;
    const source = sourceRef.current;
    const audioCtx = audioCtxRef.current;

    if (processor && source && audioCtx) {
      processor.disconnect();
      source.disconnect();
      try {
        processor.onaudioprocess = null;
      } catch (e) {}
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

    await transcribeAudio(wavBlob);

    // close audio context
    if (audioCtx) {
      try {
        await audioCtx.close();
      } catch (e) {}
    }
    audioCtxRef.current = null;
    sourceRef.current = null;
    processorRef.current = null;
    buffersRef.current = [];
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      const currentMessageCount = messageCountRef.current;

      // Add loading message for user
      setTranscripts((prev) => [
        ...prev.filter((t) => t.from !== "Human" || t.hasAnimated),
        { text: "Loading", from: "Human", id: currentMessageCount },
      ]);

      messageCountRef.current += 1;

      const fd = new FormData();
      fd.append("audio", audioBlob, "clip.wav");
      fd.append("do_chat", "true");
      
      let textToSend = transcriptRef.current.trim();
      console.log("Captured transcript:", textToSend);
      
      // If no speech was captured, use a default message
      if (!textToSend) {
        textToSend = "Hello, how are you?";
        console.log("No speech detected, using default:", textToSend);
      }
      
      fd.append("transcript", textToSend);

      const res = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        throw new Error("Error analyzing audio");
      }

      const data = await res.json();
      console.log("Backend response:", data);
      onResponse(data);

      // Update user message with actual transcript and emotions
      const displayText = data.transcript || textToSend;
      console.log("Displaying user message:", displayText);
      updateMessage(displayText, "Human", currentMessageCount, data.emotions);

      // Generate AI response from backend
      if (data.reply_text) {
        await generateAIResponse(data.reply_text, data.reply_audio_path);
      } else {
        setResponseProcessing(false);
      }
    } catch (error) {
      console.error("Error transcribing audio:", error);
      setResponseProcessing(false);
    }
  };

  const generateAIResponse = async (responseText: string, audioPath?: string) => {
    try {
      const currentMessageCount = messageCountRef.current;
      
      // Add loading message for AI
      setAIResponses((prev) => [
        ...prev,
        { text: "Loading", from: "Assistant", id: currentMessageCount },
      ]);

      messageCountRef.current += 1;

      // Small delay for UX
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Update with actual backend response
      updateMessage(responseText, "Assistant", currentMessageCount);
      
      // Play audio if available
      if (audioPath) {
        const audio = new Audio(`http://localhost:5000/api/tts-file/${audioPath}`);
        audio.play().catch(e => console.error("Audio playback error:", e));
      }
      
      setResponseProcessing(false);
    } catch (error) {
      console.error("Error generating AI response:", error);
      setResponseProcessing(false);
    }
  };

  const updateMessage = (
    newText: string,
    from: string,
    id: number,
    emotions?: { [key: string]: number }
  ) => {
    if (from === "Human") {
      setTranscripts((prev) =>
        prev.map((transcript) =>
          transcript.id === id
            ? { ...transcript, text: newText, hasAnimated: true, emotions }
            : transcript
        )
      );
    } else if (from === "Assistant") {
      setAIResponses((prev) =>
        prev.map((response) =>
          response.id === id
            ? { ...response, text: newText, hasAnimated: true, emotions }
            : response
        )
      );
    }
  };

  const handleToggleRecording = () => {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
  };

  const startCall = () => {
    setIsCallActive(true);
  };

  const endCall = () => {
    // Stop recording if active
    if (audioStream) {
      audioStream.getTracks().forEach((track) => track.stop());
      setAudioStream(null);
    }
    
    // Reset all state
    setIsCallActive(false);
    setRecording(false);
    setIsRecording(false);
    setResponseProcessing(false);
    setTranscripts([]);
    setAIResponses([
      {
        text: "Oh, hey.",
        from: "Assistant",
        id: 0,
        hasAnimated: true,
      },
    ]);
    messageCountRef.current = 1;
    
    // Clean up audio context
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch (e) {}
    }
    audioCtxRef.current = null;
    sourceRef.current = null;
    processorRef.current = null;
    buffersRef.current = [];
  };

  return (
    <AnimatePresence mode="wait">
      {!isCallActive ? (
        // Landing Screen
        <motion.div
          key="landing"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center justify-center h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50"
        >
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="max-w-2xl px-6"
          >
            <div className="mb-4">
              <h1 className="text-6xl font-bold mb-1">
                Echoes
              </h1>
              <p className="text-xl text-gray-600 leading-relaxed">
                Experience emotion-aware conversations. Speak naturally and watch as
                Echoes understands not just your words, but your feelings.
              </p>
            </div>

            <motion.button
              onClick={startCall}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 md:mx-auto rounded-lg bg-black text-white transition-all shadow-lg flex items-center gap-3 mr-auto text-lg font-semibold"
            >
              <Phone className="w-6 h-6" />
              Start Call
            </motion.button>
          </motion.div>
        </motion.div>
      ) : (
        // Call Screen
        <motion.div
          key="call"
          initial={{ opacity: 0, scale: 1.05 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col h-screen bg-gray-50"
        >
          {/* Header */}
          <div className="bg-white border-b border-gray-200 p-4">
            <div className="max-w-3xl mx-auto flex items-center gap-3">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold text-gray-900">Echoes</h1>
              </div>
            </div>
          </div>

          {/* Messages */}
          <Messages humanMessages={transcripts} AIMessages={AIResponses} />

          {/* Footer with recording controls */}
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="max-w-xl mx-auto">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleToggleRecording}
                  disabled={responseProcessing}
                  className="p-3 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Mic className={`w-5 h-5 ${isRecording ? "text-red-600" : "text-gray-700"}`} />
                </button>

                {/* Visualizer or Transcript */}
                <div className="flex-1 h-12 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden px-3">
                  {isRecording && transcript ? (
                    <span className="text-sm text-gray-700 truncate">
                      {transcript}
                    </span>
                  ) : isRecording && audioStream ? (
                    <Visualizer
                      audio={audioStream}
                      mode="continuous"
                      slices={40}
                      strokeColor="#4B5563"
                      autoStart={true}
                    >
                      {({ canvasRef }) => (
                        <canvas
                          ref={canvasRef}
                          height={48}
                          className="w-full h-full"
                        />
                      )}
                    </Visualizer>
                  ) : (
                    <span className="text-sm text-gray-400">
                      {responseProcessing ? "Processing..." : "Click mic to start recording"}
                    </span>
                  )}
                </div>

                <button
                  onClick={endCall}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2"
                >
                  <PhoneOff className="w-4 h-4" />
                  End Call
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
