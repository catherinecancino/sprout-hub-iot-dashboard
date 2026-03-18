# api/ai_service.py
import os
import json
import re
from config.firebase import db
from .rag_service import RAGService
from langsmith import traceable

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: openai not installed. Run: pip install openai")
    OPENAI_AVAILABLE = False

# Initialize OpenAI client
openai_client = None
def _get_openai_client():
    """Always reads the key fresh from environment."""
    global openai_client
    if openai_client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            openai_client = OpenAI(api_key=api_key)
    return openai_client

def _safe_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

class AIChatService:
    OPENAI_MODEL = "gpt-4o-mini"

    # ─────────────────────── THRESHOLD MANAGEMENT ───────────────────────

    @staticmethod
    @traceable(name="AI Agronomist")
    def get_thresholds(crop_type=None):
        """
        Combined threshold retrieval logic with Knowledge Library priority.
        Priority:
        1. crop_profiles/{crop_type} (Knowledge Library - permanent storage)
        2. crop_config/{crop_type} (Extracted thresholds cache)
        3. Hardcoded defaults (last resort)
        """
        try:
            if crop_type and crop_type != "default":
                crop_id = crop_type.lower().replace(" ", "_")

                # PRIORITY 1: Check crop_profiles (Knowledge Library)
                profile_doc = db.collection("crop_profiles").document(crop_id).get()
                if profile_doc.exists:
                    profile = profile_doc.to_dict()
                    if profile.get('thresholds'):
                        return profile['thresholds'], f"crop_profiles/{crop_id}"

                # PRIORITY 2: Check crop_config (legacy/cache)
                config_doc = db.collection("crop_config").document(crop_id).get()
                if config_doc.exists:
                    return config_doc.to_dict(), f"crop_config/{crop_id}"

            # Try "default" config in Firebase
            doc = db.collection("crop_config").document("default").get()
            if doc.exists:
                return doc.to_dict(), "crop_config/default"

        except Exception as e:
            print(f"Error fetching thresholds: {e}")

        # Last resort: hardcoded fallback
        return {
            "moisture_min": 30.0, "moisture_max": 80.0,
            "ph_min": 5.5, "ph_max": 7.5,
            "temp_min": 15.0, "temp_max": 35.0,
        }, "hardcoded_fallback"

    # ─────────────────────── SCOPE FILTERS ───────────────────────

    @staticmethod
    def _is_agricultural_question(question):
        """Pre-filter to check if question is agriculture-related (EN & PH)"""
        agricultural_keywords = [
            # English
            'crop', 'soil', 'plant', 'grow', 'farm', 'agriculture', 'seed',
            'fertilizer', 'irrigation', 'harvest', 'pest', 'weed', 'compost',
            'nitrogen', 'phosphorus', 'potassium', 'npk', 'ph', 'moisture',
            'tomato', 'lettuce', 'rice', 'corn', 'wheat', 'vegetable',
            'fruit', 'garden', 'cultivation', 'organic', 'yield', 'nutrient',
            # Filipino/Taglish
            'lupa', 'halaman', 'palay', 'tanim', 'pananim', 'pataba',
            'tubig', 'ulan', 'ani', 'sakahan', 'magsasaka', 'halumigmig',
            'kamatis', 'gulay', 'prutas', 'binhi', 'pesteng', 'damo'
        ]
        q_lower = question.lower()
        return any(k in q_lower for k in agricultural_keywords)

    @staticmethod
    def _is_agricultural_answer(answer):
        """Safety check on the AI's output"""
        terms = ['crop', 'soil', 'plant', 'fertilizer', 'moisture', 'ph',
                 'farm', 'lupa', 'tanim', 'nitrogen', 'temperature', 'halaman',
                 'potassium', 'phosphorus', 'npk', 'nutrient',
                 'node', 'reading', 'level', 'sensor', 'mg/kg', 'current']
        return any(t in answer.lower() for t in terms)

    # ─────────────────────── MAIN CHATBOT ───────────────────────

    @staticmethod
    def ask_agronomist(user_question, language="en"):
        """
        RAG-enhanced AI chatbot with STRICT agricultural focus.
        Uses OpenAI GPT-4o-mini as the LLM backend.
        """
        # FIX: renamed from 'client' to 'oai_client' to avoid any shadowing
        oai_client = _get_openai_client()
        if not OPENAI_AVAILABLE or oai_client is None:
            return (
                "AI service not available. Please install the OpenAI library "
                "and set your OPENAI_API_KEY in the .env file."
            )

        # Strict language instruction
        lang_instruction = "You MUST respond in Tagalog/Filipino." if language == 'fil' else "You MUST respond in English."

        # 2. Build Sensor Context with Comparison
        nodes_ref = db.collection("nodes").stream()
        nodes_context = []

        for node_doc in nodes_ref:
            node = node_doc.to_dict()
            latest = node.get("latest_readings") or node.get("lastReading") or node

            crop = node.get("crop_type", "default")
            thresholds, source = AIChatService.get_thresholds(crop)

            def get_target(min_key, max_key, unit=""):
                if thresholds.get(min_key) is not None and thresholds.get(max_key) is not None:
                    return f"{thresholds[min_key]}-{thresholds[max_key]}{unit}"
                return "Not specified in profile"

            def get_status(actual_val, min_key, max_key):
                if actual_val is None:
                    return "Unknown"
                if thresholds.get(min_key) is not None and thresholds.get(max_key) is not None:
                    return "✓ OK" if float(thresholds[min_key]) <= actual_val <= float(thresholds[max_key]) else "⚠ OUT OF RANGE"
                return "Target Not Specified"

            # Grab the actual values safely
            m_act  = _safe_float(latest.get('moisture'))
            ph_act = _safe_float(latest.get('pH') or latest.get('ph'))
            t_act  = _safe_float(latest.get('temperature'))

            # Format numbers safely for display
            fmt_m  = f"{m_act:.1f}"  if m_act  is not None else "N/A"
            fmt_ph = f"{ph_act:.1f}" if ph_act is not None else "N/A"
            fmt_t  = f"{t_act:.1f}"  if t_act  is not None else "N/A"

            node_info = f"""
### Node: {node.get('node_name', 'Unknown')} ###
**Crop:** {crop.title()}
**Reference Source:** {source}

**CURRENT vs TARGET:**
- Moisture: {fmt_m}% | Target: {get_target('moisture_min', 'moisture_max', '%')} | {get_status(m_act, 'moisture_min', 'moisture_max')}
- pH: {fmt_ph} | Target: {get_target('ph_min', 'ph_max')} | {get_status(ph_act, 'ph_min', 'ph_max')}
- Soil Temp: {fmt_t}°C | Target: {get_target('temp_min', 'temp_max', '°C')} | {get_status(t_act, 'temp_min', 'temp_max')}
- NPK: N={latest.get('nitrogen','N/A')}, P={latest.get('phosphorus','N/A')}, K={latest.get('potassium','N/A')} mg/kg
- Air: {latest.get('air_temperature','N/A')}°C, Humidity: {latest.get('humidity','N/A')}%
"""
            nodes_context.append(node_info)

        sensor_context = "\n".join(nodes_context) if nodes_context else "No sensor data available."

        # 3. RAG Context from uploaded documents
        rag_results = RAGService.search_knowledge(user_question, n_results=4)
        rag_context = ""

        if rag_results:
            rag_context = "\n**KNOWLEDGE FROM UPLOADED DOCUMENTS:**\n"
            for res in rag_results:
                doc_name   = res['metadata'].get('document_name', 'Unknown')
                crop_tag   = res['metadata'].get('crop_type', '')
                crop_label = f" [{crop_tag.upper()}]" if crop_tag else ""
                rag_context += f"\n📄 Source: {doc_name}{crop_label}\n{res['text']}\n"
        else:
            rag_context = (
                "\n**NOTE:** No documents found in Knowledge Library. "
                "Upload crop-specific documents in Settings for better advice.\n"
            )

        # 4. Active Alerts
        alerts_ref = (
            db.collection("alerts")
            .where("status", "==", "active")
            .limit(5)
            .stream()
        )
        alerts_list = [a.to_dict().get('message') for a in alerts_ref]
        alerts_str  = "\n".join([f"⚠️ {msg}" for msg in alerts_list]) if alerts_list else "No active alerts."

        # 5. System Prompt
        system_prompt = f"""You are a professional Agricultural AI Assistant for farmers.

**YOUR ROLE:**
- You help with farming, crops, soil, and agriculture topics ONLY
- You speak BOTH English and Filipino
- If the user asks in English, reply in English. If they ask in Filipino, reply in Filipino. Match the language of the user's question.
- Use PLAIN TEXT ONLY. No asterisks (**), hashtags (#), or dashes.
- Use ALL CAPS for headers and ENSURE a double line break before starting your points.

**FILIPINO STYLE GUIDE:**
✓ GOOD: "Ang moisture ng iyong lupa ay mababa. Kailangan ng dagdag na tubig para sa tamang paglaki ng tanim."
✓ GOOD: "Ang pH level ay 5.2, mas mababa sa ideal na 6.0-6.8 para sa kamatis. Maglapat ng lime upang itaas ang pH."
❌ AVOID (too casual): "Uy pre, kulang yung lupa mo!"
❌ AVOID (random English mixing): "Kailangan mo ng more water para sa soil."

**STRICT RULES:**
1. If the question is "how is my soil" or general, summarize the status of ALL nodes provided in the data.
2. ASSUME CONTEXT: If the user asks vague questions like "how are my conditions?", "what should I do?", or "is it okay?", ASSUME they are talking about the provided Sensor Data. Do NOT refuse these questions.
3. If a reading is "⚠ OUT OF RANGE", explain why and give one clear action.
4. If a target is "Not specified", use your general knowledge for that crop.
5. BE EXTREMELY CONCISE. Maximum 3 sentences total.
6. CITE sensor values directly.

**FORMATTING & TONE RULES:**
1. Write in a natural, friendly, and conversational tone.
2. NEVER use ALL CAPS for your sentences. Use standard capitalization.
3. DO NOT use rigid headers like "Observation:", "Action:", or "Summary:".
4. Just provide a brief, easy-to-read paragraph explaining the current conditions. If something is out of range, gently suggest what the user might need to do.
5. Always bold key numbers, metrics, and units (e.g., **27.8%**, **23.0°C**, **5.5 pH**) so they are easy to read.
6. {lang_instruction}

**CURRENT SENSOR DATA vs REFERENCE:**
{sensor_context}

**ACTIVE ALERTS:**
{alerts_str}

{rag_context}

**REMEMBER:**
- Match the farmer's language exactly (English = English, Filipino = Filipino)
- Use professional, clear Filipino (not conversational Taglish)
- Be direct and practical
- Cite specific numbers from the sensor data"""

        try:
            # FIX: using oai_client instead of client
            response = oai_client.chat.completions.create(
                model=AIChatService.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_question},
                ],
                max_tokens=300,
                temperature=0.3,
            )

            answer = response.choices[0].message.content

            # Clean up markdown formatting
            answer = answer.replace('###', '').replace('##', '').replace('#', '')

            # Normalize spacing
            answer = re.sub(r'\n{3,}', '\n\n', answer)
            answer = answer.strip()

            # Safety check on output
            if not AIChatService._is_agricultural_answer(answer):
                filipino_indicators = ['ano', 'paano', 'yung', 'mga', 'ba', 'po']
                is_filipino = any(ind in user_question.lower() for ind in filipino_indicators)
                if is_filipino:
                    return (
                        "Pasensya na po, tumutulong lang ako sa mga tanong tungkol sa agrikultura. "
                        "Magtanong po tungkol sa mga pananim, lupa, o pagsasaka. 🌱"
                    )
                return (
                    "I'm sorry, I can only help with agricultural questions. "
                    "Please ask me about crops, soil, or farming practices. 🌾"
                )

            return answer

        except Exception as e:
            error_msg = str(e).lower()
            if "api_key" in error_msg or "authentication" in error_msg or "invalid" in error_msg:
                return "⚠️ Invalid OpenAI API key. Please check your OPENAI_API_KEY in the .env file."
            elif "rate_limit" in error_msg:
                return "⚠️ OpenAI rate limit reached. Please wait a moment and try again."
            elif "insufficient_quota" in error_msg or "quota" in error_msg:
                return "⚠️ OpenAI quota exceeded. Please check your billing at platform.openai.com."
            return f"AI Error: {str(e)}"

    # ─────────────────────── NODE COMPARISON ───────────────────────

    @staticmethod
    def get_node_comparison():
        """Generate AI comparison between multiple nodes using GPT-4o-mini"""
        oai_client = _get_openai_client()
        if not OPENAI_AVAILABLE or oai_client is None:
            return "AI comparison not available (OpenAI not configured)."

        nodes_ref  = db.collection("nodes").stream()
        nodes_data = []

        for node_doc in nodes_ref:
            node   = node_doc.to_dict()
            latest = node.get("latest_readings", {}) or node.get("lastReading", {}) or node
            crop   = node.get("crop_type", "default")
            thresholds, source = AIChatService.get_thresholds(crop)

            def get_target(min_key, max_key, unit=""):
                if thresholds.get(min_key) is not None and thresholds.get(max_key) is not None:
                    return f"{thresholds[min_key]}-{thresholds[max_key]}{unit}"
                return "Not specified in profile"

            nodes_data.append({
                "name":            node.get('node_name', node.get('node_id')),
                "crop":            crop,
                "moisture":        latest.get('moisture'),
                "ph":              latest.get('pH') or latest.get('ph'),
                "temp":            latest.get('temperature'),
                "moisture_target": get_target('moisture_min', 'moisture_max', '%'),
                "ph_target":       get_target('ph_min', 'ph_max'),
                "source":          source,
            })

        if len(nodes_data) < 2:
            return "Need at least 2 nodes to compare. / Kailangan ng at least 2 nodes para i-compare."

        try:
            response = oai_client.chat.completions.create(
                model=AIChatService.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Compare these soil sensor nodes. Which one needs attention first? "
                        f"If a target is 'Not specified in profile', use your general agricultural knowledge for that crop to assess it. "
                        f"Be concise and direct. 1-2 sentences ONLY. Use plain text, no markdown.\n\n"
                        f"{json.dumps(nodes_data, indent=2)}"
                    ),
                }],
                max_tokens=100,
                temperature=0.4,
            )

            answer = response.choices[0].message.content
            answer = answer.replace('**', '').replace('###', '').replace('---', '').strip()
            return answer

        except Exception as e:
            return f"Comparison unavailable: {str(e)}"

    # ─────────────────────── STATUS CHECK ───────────────────────

    @staticmethod
    def check_openai_status():
        """Check if OpenAI API key is valid and reachable"""
        if not OPENAI_AVAILABLE:
            return {
                "available": False,
                "message": "OpenAI Python package not installed. Run: pip install openai",
            }

        oai_client = _get_openai_client()
        if oai_client is None:
            return {
                "available": False,
                "message": "OPENAI_API_KEY not set. Add it to your .env file.",
            }

        try:
            oai_client.chat.completions.create(
                model=AIChatService.OPENAI_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return {
                "available": True,
                "running":   True,
                "model":     AIChatService.OPENAI_MODEL,
                "provider":  "OpenAI",
            }
        except Exception as e:
            return {
                "available": True,
                "running":   False,
                "message":   f"OpenAI API error: {str(e)}",
            }

    # Backward-compatible alias
    @staticmethod
    def check_ollama_status():
        return AIChatService.check_openai_status()