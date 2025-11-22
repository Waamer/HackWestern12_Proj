import React, { useEffect, useRef, useState } from "react";

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
  const [recording, setRecording] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const buffersRef = useRef<Float32Array[]>([]);

  useEffect(() => {
    return () => {
      stopRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startRecording = async () => {
    buffersRef.current = [];
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
    processor.connect(audioCtx.destination); // needed in some browsers

    setRecording(true);
  };

  const stopRecording = async () => {
    if (!recording) return;
    setRecording(false);

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

    const fd = new FormData();
    fd.append("audio", wavBlob, "clip.wav");
    fd.append("do_chat", "true");

    try {
      const res = await fetch("http://localhost:5000/api/analyze", {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      onResponse(data);
    } catch (err) {
      console.error("Upload error", err);
    }

    // close audio context
    try {
      await audioCtx.close();
    } catch (e) {}
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
      <p>{recording ? "Recording..." : "Idle"}</p>
    </div>
  );
}
