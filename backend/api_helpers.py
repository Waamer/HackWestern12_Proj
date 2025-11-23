import os
import tempfile
import requests
from typing import Optional

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "api_default")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Allow overriding model name via env; default to a known OpenRouter preview model
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")
# Debug: Print what was loaded
print(f"[DEBUG api_helpers] GEMINI_API_KEY: {'SET' if GEMINI_API_KEY else 'NOT SET'}")
print(f"[DEBUG api_helpers] ELEVENLABS_API_KEY: {'SET' if ELEVEN_API_KEY else 'NOT SET'}")
print(f"[DEBUG api_helpers] OPENROUTER_MODEL: {OPENROUTER_MODEL}")


def _is_advice_request(transcript: str) -> bool:
    """Detect if the user is asking for advice."""
    advice_keywords = [
        "what should i do", "what do i do", "should i", "advice", "suggest",
        "recommend", "help me decide", "what would you do", "how do i",
        "how should i", "any tips", "any suggestions", "what's the best",
        "guide me", "need help with", "stuck on", "not sure what to"
    ]
    lower = transcript.lower()
    return any(kw in lower for kw in advice_keywords)

def _synthesize_local_reply(transcript: str, emotions: dict | None, history: list | None = None) -> str:
    """Create a short empathetic reply locally when the model returns only reasoning.

    This avoids exposing the model's chain-of-thought to the user and guarantees
    the frontend receives a caring response.
    """
    # Check if this is an advice request
    is_advice = _is_advice_request(transcript)
    
    # Choose dominant emotion if available
    dominant = None
    if emotions:
        try:
            dominant = max(emotions.items(), key=lambda kv: kv[1])[0]
        except Exception:
            dominant = None

    # PRIORITY: Analyze the actual transcript content first
    lower = transcript.lower()
    
    # Detect clear positive sentiment in words
    positive_words = ["great", "good", "happy", "excited", "wonderful", "amazing", "fantastic", "love", "enjoy"]
    negative_words = ["hard", "difficult", "sad", "upset", "hurt", "pain", "struggle", "tough", "bad", "awful", "terrible"]
    
    has_positive = any(word in lower for word in positive_words)
    has_negative = any(word in lower for word in negative_words)
    
    # Check for emotion-content mismatch
    emotion_content_mismatch = False
    if has_positive and dominant in ["sad", "fearful", "angry", "disgust"]:
        emotion_content_mismatch = True
        return "I hear you saying things are going well, though I'm picking up some other signals. How are you really feeling about everything?"
    elif has_negative and dominant in ["happy", "surprised"]:
        emotion_content_mismatch = True
        return "That sounds like it's been really difficult for you. I'm here to listen - what's been hardest about it?"
    
    # If it's an advice request, provide structured guidance
    if is_advice:
        lower = transcript.lower()
        
        # Detailed situation analysis with specific advice
        if "confident" in lower and ("school" in lower or "study" in lower or "class" in lower):
            return "Building academic confidence takes intentional practice. Start by identifying one subject where you feel even slightly capable—build momentum there first. Prepare questions before class so you can participate actively; speaking up builds confidence faster than silent mastery. Study in short, focused 25-minute blocks rather than marathon sessions—this proves to yourself you can concentrate. Finally, reframe mistakes as data: each wrong answer tells you exactly what to study next. Confidence comes from evidence you're capable, and you create that evidence through small, repeated wins."
        
        elif "stress" in lower and ("school" in lower or "study" in lower or "exam" in lower or "test" in lower):
            return "Academic stress often comes from feeling overwhelmed by everything at once. Try this: write down every task you're worried about, then sort them by actual deadline, not emotional urgency. Focus only on what's due in the next 48 hours—everything else goes on a 'later' list. Schedule specific blocks for studying (e.g., 'Chemistry 4-6pm Monday') rather than vague 'I should study more.' Take real breaks—15 minutes of movement or fresh air between sessions. If you're losing sleep or appetite, talk to a counselor; that's a sign you need support beyond study strategies."
        
        elif "stress" in lower and ("work" in lower or "job" in lower):
            return "Work stress usually signals a boundary issue or capacity problem. First, track exactly how you spend your work hours for 2-3 days—you might find time drains you can eliminate. Second, identify one task you could delegate, automate, or simply stop doing. Third, practice a firm end-of-workday ritual (close laptop, change clothes, etc.) to create mental separation. If you feel anxious on Sunday nights or dread going in, that's worth discussing with a manager or therapist—chronic stress damages your health and that matters more than any job."
        
        elif "relationship" in lower or "partner" in lower or "spouse" in lower or "girlfriend" in lower or "boyfriend" in lower:
            return "Relationship challenges need both honesty and compassion. Start by clarifying what you actually need (not what you think you should want). Then, share that need clearly and specifically: 'I need us to spend one evening a week without phones' works better than 'you never listen.' Listen to understand their perspective, not just to respond. If the same argument keeps happening, that's a sign you're solving the wrong problem—dig deeper to find the real issue. If you feel unsafe, dismissed, or consistently worse after interactions, that's a red flag worth discussing with someone you trust."
        
        elif "friend" in lower or "friendship" in lower:
            return "Friendship issues sting because we often don't have clear ways to address them. If someone hurt you, decide whether you want to repair or release the friendship—both are valid. For repair: express how you felt without attacking their character ('I felt left out when...' not 'you always...'). For release: it's okay to let friendships naturally fade without drama. If you're feeling lonely, invest in activities where you'll see the same people repeatedly (clubs, classes, volunteering)—familiarity breeds connection. Quality matters more than quantity."
        
        elif "anxious" in lower or "anxiety" in lower or "panic" in lower or "worry" in lower:
            return "Anxiety thrives on uncertainty and catastrophizing. When you notice worry spiraling, try this: name five things you can see, four you can hear, three you can touch. This grounds you in the present instead of feared futures. Write down your worst-case scenario, then list three ways you'd cope even if it happened—this often reveals you're more resilient than anxiety suggests. If physical symptoms (racing heart, shortness of breath) are frequent, learn box breathing: in for 4, hold for 4, out for 4, hold for 4. For persistent anxiety, therapy—especially CBT—is remarkably effective."
        
        elif "sad" in lower or "depressed" in lower or "depression" in lower or "down" in lower:
            return "Persistent sadness deserves attention and care. Start with the basics your brain needs: aim for 7-8 hours of sleep, eat regularly even if you're not hungry, and get 15 minutes of daylight daily. Movement helps—even a 10-minute walk can shift your neurochemistry slightly. Reach out to one person, even just to say 'I'm struggling.' If you've felt this way for more than two weeks, or if you're having thoughts of self-harm, please contact a counselor or therapist. Depression is a medical condition, not a character flaw, and it responds to treatment."
        
        elif "decision" in lower or "choose" in lower or "choice" in lower:
            return "For tough decisions, try this framework: First, set a decision deadline—open-ended deliberation increases anxiety. Second, write out the realistic best and worst outcomes for each option (not catastrophic fantasies). Third, imagine you chose option A—how do you feel? Then imagine choosing B. Your gut often knows before your brain. Fourth, ask 'which option leaves me with the most future flexibility?' Finally, remember that most decisions aren't permanent—you can adjust course later. Perfectionism is the enemy of good-enough choices."
        
        elif "sleep" in lower or "insomnia" in lower or "tired" in lower:
            return "Sleep issues often reflect stress, but they also worsen everything else. Try these: keep a consistent wake time even on weekends (this matters more than bedtime). Move your body during the day—tired bodies sleep better. Dim lights 1-2 hours before bed and avoid screens if possible. If your mind races at night, keep a notepad by your bed to dump worries onto paper. If you're awake more than 20 minutes, get up and do something boring in dim light until you feel sleepy again. If this persists for weeks, talk to a doctor—sleep disorders are treatable."
        
        else:
            # Specific general fallback based on emotional tone
            if dominant == "happy":
                return "I'm glad you're approaching this from a positive place. Channel that energy: write down what success looks like for this specific situation, then identify the very first small step you could take today. Break bigger goals into weekly milestones so you can track progress. Share your goal with someone who'll check in on you—accountability helps follow-through. And remember, motivation fades, so build habits and systems that work even when you don't feel inspired."
            else:
                return "Here's a tailored approach: First, define the specific outcome you want—'feel better' is too vague, but 'have one honest conversation' or 'finish the project by Friday' gives you a target. Second, identify what's blocking you (fear? time? information?) and tackle that obstacle first. Third, find one person who's successfully handled something similar and ask them what worked. Fourth, commit to trying one new strategy for one week, then assess honestly whether it's helping. You deserve specific solutions, not generic platitudes."
        
        return reply[:600]

    # Choose template based on emotion, but also consider content
    # For normal conversation (non-advice), respond to what they said
    if has_positive:
        # They're expressing something positive
        reply = (
            "That's great to hear! It sounds like things are going well. "
            "What's been the best part of your day?"
        )
    elif has_negative:
        # They're expressing something difficult
        reply = (
            "That sounds really hard to go through, and I'm here to listen. "
            "What's been the most difficult part for you? Sometimes talking it through can help."
        )
    elif "day" in lower and not has_positive and not has_negative:
        # Talking about their day but sentiment unclear
        reply = (
            "Thanks for sharing about your day. I'm listening. "
            "How are you feeling about everything right now?"
        )
    else:
        # Use emotion-based template as final fallback
        # Therapist-style templates keyed by emotion. They validate what was said,
        # offer constructive support, and invite productive follow-up.
        templates = {
        "angry": (
            "I hear the frustration in what you're sharing - that sounds really difficult. "
            "What do you think would help most right now? I'm here to listen and support you."
        ),
        "disgust": (
            "That sounds really upsetting and unfair. "
            "How has this been affecting you? Let's talk through what you need."
        ),
        "fearful": (
            "That sounds concerning and stressful. Are you okay right now? "
            "What would be most helpful to talk about, or is there something specific you need support with?"
        ),
        "happy": (
            "I hear what you're sharing. "
            "How are you actually feeling about everything that's going on? I want to make sure I understand."
        ),
        "neutral": (
            "Thanks for sharing that with me - I'm listening. "
            "What's the most important thing on your mind about this right now?"
        ),
        "sad": (
            "That sounds really hard to go through, and I'm here to listen. "
            "What's been the most difficult part for you? Sometimes talking it through can help."
        ),
        "surprised": (
            "That sounds like a lot to process and take in. "
            "How are you making sense of this? I'm here if you need to work through it."
        ),
    }

        # Choose template for dominant emotion, fallback to a neutral supportive line
        reply = templates.get(dominant)
        if not reply:
            reply = (
                "Thank you for sharing that with me - I'm listening. "
                "What's the most important thing on your mind right now?"
            )

    # If no dominant emotion but a transcript suggests immediate risk,
    # include a brief safety-check (best-effort heuristic)
    lower = (transcript or "").lower()
    if any(w in lower for w in ("hurt myself", "kill myself", "want to die", "not want to live", "suicide")):
        return (
            "I'm really sorry you're feeling that way. If you're in immediate danger, please contact local emergency services or a crisis line. "
            "If you'd like, tell me what's going on and I'll listen."
        )

    # Try to answer memory questions from conversation history
    if history and isinstance(history, list):
        try:
            tl = (transcript or "").lower()
            mem_triggers = ["do you remember", "what was", "where was", "where did", "what did i", "recall"]
            
            if any(mt in tl for mt in mem_triggers):
                # Extract what they're asking about
                search_terms = []
                if "setting" in tl or "where" in tl:
                    search_terms = ["at", "in", "on", "location", "place", "setting"]
                elif "doing" in tl or "what" in tl:
                    search_terms = ["doing", "did", "was", "am", "activity"]
                
                # Search history for relevant information
                relevant_info = []
                for h in reversed(history):
                    if not isinstance(h, dict):
                        continue
                    role = h.get("role", "user")
                    content = (h.get("content") or "").strip()
                    
                    if role == "user" and content and content.lower() != tl:
                        # Look for specific information based on the question
                        content_lower = content.lower()
                        
                        # If asking about setting/location
                        if any(term in tl for term in ["setting", "where", "location", "place"]):
                            # Look for location indicators
                            location_words = ["public lecture", "at work", "at school", "at home", "in class", 
                                            "in the office", "at the gym", "in the hospital", "at the store",
                                            "presentation", "meeting", "conference", "auditorium", "classroom"]
                            for loc in location_words:
                                if loc in content_lower:
                                    relevant_info.append(f"You mentioned you did a {loc}")
                                    break
                        
                        # If asking what they were doing
                        if "doing" in tl or "what was i" in tl:
                            # Return the relevant sentence
                            if len(content) < 150:
                                relevant_info.append(f"You told me: '{content}'")
                            else:
                                relevant_info.append(f"You were talking about: {content[:100]}...")
                    
                    if relevant_info:
                        break
                
                if relevant_info:
                    return relevant_info[0]
                else:
                    # Fallback: return most relevant past user message
                    for h in reversed(history):
                        if not isinstance(h, dict):
                            continue
                        role = h.get("role", "user")
                        content = (h.get("content") or "").strip()
                        if role == "user" and content and content.lower() != tl:
                            return f"Looking back at our conversation, you mentioned: '{content}'. Is that what you're referring to?"
        except Exception as e:
            print(f"[DEBUG] Memory search error: {e}")
            pass

    return reply[:400]

def generate_response_with_gemini(
    transcript: str,
    emotions: dict | None = None,
    history: list | None = None,
    max_tokens: int = 256,
) -> str:
    """Generates an empathetic response using OpenRouter (Gemini).

    Accepts `transcript`, optional `emotions` mapping (label -> score), and an
    optional `history` (list of {role, content}). The history is included so
    the model keeps conversational context (we cap to recent messages).
    The system prompt instructs the model to treat emotion estimates as
    probabilistic and to NOT reveal internal chain-of-thought.
    """
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set.")
        return "I'm sorry, I can't think right now. (Missing API Key)"

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    # Build emotion lines in a consistent, sorted order (top-first)
    emotion_lines = ""
    if emotions:
        try:
            # Sort emotions by score desc and include top 5
            items = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)[:5]
            emotion_lines = "\nEmotion estimates (probabilistic):\n" + "\n".join([
                f"- {k}: {v:.3f}" for k, v in items
            ])
        except Exception:
            emotion_lines = "\nEmotion estimates: (unavailable)"

    # Detect if this is an advice request
    is_advice_request = _is_advice_request(transcript)
    
    # Detect if this is a memory question
    is_memory_question = any(trigger in transcript.lower() for trigger in 
                             ["do you remember", "what did i", "where did i", "what was i", 
                              "where was i", "recall", "you said", "i told you", "i mentioned"])
    
    print(f"[DEBUG] Advice request: {is_advice_request}, Memory question: {is_memory_question} for: '{transcript[:50]}...'")
    
    # User-visible content: transcript + emotion estimates (explicitly framed)
    if is_memory_question:
        user_content = (
            f"Transcript: {transcript}\n\n"
            f"The user is asking you to recall information from earlier in the conversation. "
            f"Review the conversation history carefully and provide the specific information they're asking about. "
            f"If you find it, quote or reference it clearly. If you don't find it in the history, say so honestly."
            + emotion_lines
        )
    elif is_advice_request:
        user_content = (
            f"Transcript: {transcript}\n\n"
            f"The user is asking for advice. Provide specific, actionable guidance tailored to their unique situation. "
            f"Include 2-4 concrete steps or strategies they can implement. Be practical and empathetic."
            + emotion_lines
        )
    else:
        user_content = (
            f"Transcript: {transcript}\n\n"
            f"Respond primarily to what the user is SAYING in the transcript above. "
            f"The emotion analysis below is supplementary context only - it may not be accurate. "
            f"If the words and emotions don't match (e.g., saying something sad with 'happy' detected), "
            f"trust the words and gently check in: 'I hear what you're saying, how are you actually feeling about this?'\n"
            f"Keep responses empathetic, relevant to their actual words, and concise (2-3 sentences)."
            + emotion_lines
        )

    # System prompt: explicitly instruct about chain-of-thought and emotion handling
    if is_memory_question:
        system_prompt = (
            "You are a helpful and empathetic therapist with perfect memory of this conversation. "
            "When the user asks you to remember something:\n"
            "1. Carefully review the conversation history provided\n"
            "2. Find the specific information they're asking about\n"
            "3. Quote or reference it directly and clearly\n"
            "4. If the information isn't in the history, honestly say you don't recall that being mentioned\n"
            "Be accurate and helpful. The conversation history is your only source of truth."
        )
    elif is_advice_request:
        system_prompt = (
            "You are an experienced therapist and life coach. When giving advice:\n"
            "1. Acknowledge their emotions and situation\n"
            "2. Provide 2-4 specific, actionable steps tailored to their unique circumstances\n"
            "3. Consider their emotional state from the voice analysis\n"
            "4. Be practical, compassionate, and non-judgmental\n"
            "5. If the situation is serious (safety, health, legal), recommend professional help\n"
            "Do NOT reveal internal reasoning. Keep advice clear, structured, and around 4-6 sentences."
        )
    else:
        system_prompt = (
            "You are a helpful and empathetic therapist who is constructive and action-oriented. Your PRIMARY focus is what the user says (their words). "
            "Emotion estimates are PROVIDED FOR CONTEXT ONLY - they are probabilistic and may be inaccurate. \n\n"
            "Rules:\n"
            "1. Respond to the CONTENT of what they're saying, not just the detected emotion\n"
            "2. Be constructive: validate what happened, then move toward what would help or what they need\n"
            "3. If words and emotions mismatch (e.g., describing something sad but emotion shows 'happy'), acknowledge what they SAID and gently ask how they're feeling\n"
            "4. If words and emotions align, validate both and ask what would be helpful\n"
            "5. Never assert emotions as facts ('you sound happy') - instead reflect their words ('that sounds difficult')\n"
            "6. Keep responses empathetic but forward-moving: validate + helpful question (2-3 sentences)\n"
            "7. Do NOT reveal internal reasoning or emotion analysis to the user\n\n"
            "Your style: Warm validation + constructive next step. Example: 'That sounds really stressful. Are you okay? What would help most right now?'"
        )

    # Start building messages: include system prompt, then recent history (if any), then the current user content
    messages = [{"role": "system", "content": system_prompt}]
    if history and isinstance(history, list):
        try:
            # Include the full session history supplied by the client.
            # For safety, limit to a large number of most recent entries (e.g. 500)
            cap = 500
            for h in history[-cap:]:
                if not isinstance(h, dict):
                    continue
                role = h.get("role", "user")
                # Normalize roles: only allow 'user' or 'assistant'
                if role not in ("user", "assistant"):
                    role = "user"
                content = h.get("content", "")
                # Append history messages in chronological order
                messages.append({"role": role, "content": content})
        except Exception:
            pass

    messages.append({"role": "user", "content": user_content})

    # Increase token limits to ensure actual content is generated (not just reasoning)
    # Gemini-3-pro-preview uses reasoning tokens, so we need higher limits
    if is_memory_question:
        token_limit = 800
    elif is_advice_request:
        token_limit = 1200
    else:
        # Normal conversation - MUST be high enough for reasoning + content
        token_limit = 800
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": token_limit,
        "temperature": 0.7  # Add some creativity for varied responses
    }

    r = None
    try:
        print(f"[DEBUG] Sending request to OpenRouter - Advice mode: {is_advice_request}")
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"[DEBUG] OpenRouter response received, checking for content...")
        print(f"[DEBUG] Full response: {data}")
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            # Try several common locations for returned assistant text
            text = None
            # 1) OpenRouter normalized shape: choice['message']['content'] may be string or dict
            msg = choice.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                    print(f"[DEBUG] Got response text (string): {text[:100] if text else '(empty)'}...")
                elif isinstance(content, dict):
                    # nested forms: try common keys
                    text = content.get("text") or content.get("content")
                    if text:
                        print(f"[DEBUG] Got response text (from dict): {text[:100]}...")
                
                # If content is empty but reasoning exists, synthesize a response locally
                # to avoid exposing chain-of-thought
                if not text or text.strip() == "":
                    reasoning = msg.get("reasoning")
                    if reasoning:
                        print("[DEBUG] Content empty but reasoning present - using local synthesis")
                        return _synthesize_local_reply(transcript, emotions, history=history)
            # 2) Older OpenAI-like shape: choice.get('text')
            if not text:
                text = choice.get("text")
                if text:
                    print(f"[DEBUG] Got response text (older shape): {text[:100]}...")
            # 3) Some providers include 'message' as a plain string
            if not text and isinstance(msg, str):
                text = msg
                print(f"[DEBUG] Got response text (message string): {text[:100]}...")

            # If we have text, return it immediately
            if text:
                return text.strip()
            
            # If still no text, do a safe follow-up request asking for a concise
            # empathetic reply based only on the transcript+emotions. Do NOT
            # expose or return the model's internal chain-of-thought or reasoning.
            print("[DEBUG] No text found in initial response, trying follow-up request...")
            if not text:
                try:
                    follow_payload = {
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a helpful and empathetic therapist. Do NOT reveal your internal chain-of-thought or reasoning. Provide a concise, caring reply in 1-3 sentences."},
                            {"role": "user", "content": user_content},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    }
                    r2 = requests.post(url, json=follow_payload, headers=headers, timeout=20)
                    r2.raise_for_status()
                    d2 = r2.json()
                    if "choices" in d2 and len(d2["choices"]) > 0:
                        choice2 = d2["choices"][0]
                        msg2 = choice2.get("message")
                        # Try to extract text from the follow-up response
                        if isinstance(msg2, dict):
                            content2 = msg2.get("content")
                            if isinstance(content2, str) and content2.strip():
                                return content2.strip()
                            if isinstance(content2, dict):
                                text2 = content2.get("text") or content2.get("content")
                                if text2:
                                    return str(text2).strip()
                        # Fallback to older shape
                        if choice2.get("text"):
                            return str(choice2.get("text")).strip()
                    # If follow-up didn't produce text, try to extract reasoning and
                    # synthesize a safe local reply so we don't expose chain-of-thought.
                    reasoning_text = None
                    try:
                        if isinstance(choice2.get("message"), dict):
                            reasoning_text = choice2["message"].get("reasoning")
                        if not reasoning_text:
                            rd = choice2.get("message", {}).get("reasoning_details") or choice2.get("reasoning_details")
                            if rd and isinstance(rd, list) and len(rd) > 0:
                                first = rd[0]
                                if isinstance(first, dict):
                                    reasoning_text = first.get("text") or first.get("content")
                                elif isinstance(first, str):
                                    reasoning_text = first
                    except Exception:
                        reasoning_text = None

                    if reasoning_text:
                        # Use local synthesizer based on original transcript+emotions
                        return _synthesize_local_reply(transcript, emotions)

                    # As a last resort, log both responses for debugging and return empty
                    print("OpenRouter initial response (no assistant text):")
                    print(data)
                    print("OpenRouter follow-up response:")
                    try:
                        print(d2)
                    except Exception:
                        pass
                    return ""
                except Exception as e:
                    print(f"Error doing follow-up OpenRouter request: {e}")
                    print("Initial response was:")
                    print(data)
                    return ""

            final_text = (text or "").strip()
            print(f"[DEBUG] Returning final text: {final_text[:100]}...")
            return final_text
        else:
            print(f"[DEBUG] OpenRouter Error (no choices): {data}")
            return "I'm having trouble understanding that."
    except requests.HTTPError as e:
        # If OpenRouter returned a 400, include the body for diagnosis
        body = None
        try:
            body = r.text if r is not None else None
        except Exception:
            body = None
        print(f"[DEBUG] HTTP Error calling OpenRouter: {e}; response body: {body}")
        return "I'm sorry, I'm having connection issues. (HTTP Error)"
    except Exception as e:
        print(f"[DEBUG] Exception calling OpenRouter: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return "I'm sorry, I'm having connection issues. (Exception)"

def tts_elevenlabs(text: str, out_path: Optional[str] = None) -> Optional[str]:
    """Simple ElevenLabs TTS stream-to-file. Returns path or None if key missing."""
    if not ELEVEN_API_KEY:
        print("Warning: ELEVENLABS_API_KEY not set.")
        return None
    # Save TTS output into the project root so the frontend can request it by basename.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(project_root, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(suffix=".wav", dir=project_root)
    os.close(fd)

    # Use the voice ID from env or default
    voice_id = ELEVEN_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"  # Default Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
        # Return only the basename so the frontend can request `/api/tts-file/<basename>`.
        return os.path.basename(tmp_path)
    except Exception as e:
        print(f"Error calling ElevenLabs: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return None
