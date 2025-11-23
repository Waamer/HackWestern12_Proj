import { motion, AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";

interface Message {
  text: string;
  from: string;
  id: number;
  hasAnimated?: boolean;
  emotions?: { [key: string]: number };
}

interface MessagesProps {
  humanMessages: Message[];
  AIMessages: Message[];
}

export function Messages({ humanMessages, AIMessages }: MessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Combine human and AI messages
  const combinedMessages = [...humanMessages, ...AIMessages];

  // Sort messages by id (chronological order)
  combinedMessages.sort((a, b) => a.id - b.id);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [combinedMessages]);

  // Helper function to get top 3 emotions
  const getTopEmotions = (emotions?: { [key: string]: number }) => {
    if (!emotions) return [];
    return Object.entries(emotions)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([emotion, score]) => ({
        emotion: emotion.charAt(0).toUpperCase() + emotion.slice(1),
        score: score.toFixed(2),
      }));
  };

  // Emotion color mapping (based on Whisper emotion model labels)
  const emotionColors: { [key: string]: string } = {
    // Whisper model emotions (exact labels)
    angry: "bg-red-600",
    disgust: "bg-green-600",
    fearful: "bg-purple-600",
    happy: "bg-yellow-400",
    neutral: "bg-gray-400",
    sad: "bg-blue-500",
    surprised: "bg-cyan-400",
    // Variations/aliases
    anger: "bg-red-600",
    disgusted: "bg-green-600",
    fear: "bg-purple-600",
    sadness: "bg-blue-500",
    happiness: "bg-yellow-400",
    joy: "bg-yellow-400",
    surprise: "bg-cyan-400",
  };

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto p-4 flex justify-center mb-2">
      <div className="w-full max-w-3xl space-y-4">
        <AnimatePresence>
          {combinedMessages.map(({ text, from, id, hasAnimated = false, emotions }) => {
            const topEmotions = getTopEmotions(emotions);
            const isUser = from === "Human";

            return (
              <motion.div
                key={id}
                initial={hasAnimated ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ease: "easeInOut", duration: 0.3 }}
                className={`${isUser ? "ml-auto max-w-2xl" : "mr-auto max-w-2xl"}`}
              >
              <div className={`bg-white min-w-md max-w-2xl rounded-lg border border-gray-200 shadow-sm p-4 ${isUser ? "sm:ml-8 md:ml-16 lg:ml-32" : "sm:mr-8 md:mr-16 lg:mr-32"}`}>
                <div className="text-sm text-gray-500 text-md font-semibold leading-none">{from}</div>
                {text === "Loading" ? (
                  <Loader2 className="animate-spin mt-2 size-5 text-gray-400" />
                ) : (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    className="text-gray-900 text-lg font-semibold"
                  >
                    {text}
                  </motion.p>
                )}

                {/* Only show emotions for user messages */}
                {isUser && topEmotions.length > 0 && text !== "Loading" && (
                  <div className="pt-2 mt-2 border-t border-gray-200 flex flex-col gap-2 md:flex-row md:space-x-2 w-full">
                    {topEmotions.map(({ emotion, score }) => {
                      const emotionKey = emotion.toLowerCase();
                      const colorClass = emotionColors[emotionKey] || "bg-gray-400";
                      const percentage = parseFloat(score) * 100;

                      return (
                        <div key={emotion} className="space-y-1 w-full">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-semibold text-gray-700">{emotion}</span>
                            <span className="font-semibold text-gray-500">{score}</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-sm h-2 overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percentage}%` }}
                              transition={{ duration: 0.5, ease: "easeOut" }}
                              className={`h-full ${colorClass} rounded-sm`}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {/* Invisible element to scroll to */}
      <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
