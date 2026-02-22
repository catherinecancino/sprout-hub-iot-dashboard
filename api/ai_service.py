# api/ai_service.py
import os
import json
import re
from config.firebase import db
from .rag_service import RAGService

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: openai not installed. Run: pip install openai")
    OPENAI_AVAILABLE = False

# Initialize OpenAI client
openai_client = None
if OPENAI_AVAILABLE:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        openai_client = OpenAI(api_key=api_key)
    else:
        print("Warning: OPENAI_API_KEY not found in environment variables")


class AIChatService:
    OPENAI_MODEL = "gpt-4o-mini"

    # ─────────────────────── THRESHOLD MANAGEMENT ───────────────────────

    @staticmethod
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
                 'farm', 'lupa', 'tanim', 'nitrogen', 'temperature', 'halaman']
        return any(t in answer.lower() for t in terms)

    # ─────────────────────── MAIN CHATBOT ───────────────────────

    @staticmethod
    def ask_agronomist(user_question):
        """
        RAG-enhanced AI chatbot with STRICT agricultural focus.
        Uses OpenAI GPT-4o-mini as the LLM backend.
        """
        if not OPENAI_AVAILABLE or openai_client is None:
            return (
                "AI service not available. Please install the OpenAI library "
                "and set your OPENAI_API_KEY in the .env file."
            )

        # 1. Scope Guard
        if not AIChatService._is_agricultural_question(user_question):
            filipino_indicators = ['ano', 'paano', 'saan', 'kailan', 'bakit',
                                   'kumusta', 'kamusta', 'pano', 'yung', 'mga',
                                   'ba', 'po', 'ko', 'mo']
            is_filipino = any(ind in user_question.lower() for ind in filipino_indicators)

            if is_filipino:
                return (
                    "Pasensya na po, tumutulong lang ako sa mga tanong tungkol sa "
                    "agrikultura at pamamahala ng lupa. "
                    "Magtanong po kayo tungkol sa mga pananim, kondisyon ng lupa, "
                    "o mga teknik sa pagsasaka. 🌱"
                )
            else:
                return (
                    "I'm sorry, I can only help with agricultural and soil management questions. "
                    "Please ask me about crops, soil conditions, or farming practices. 🌾"
                )

        # 2. Build Sensor Context with Comparison
        nodes_ref = db.collection("nodes").stream()
        nodes_context = []

        for node_doc in nodes_ref:
            node = node_doc.to_dict()
            latest = node.get("latest_readings", {})
            crop = node.get("crop_type", "default")

            thresholds, source = AIChatService.get_thresholds(crop)

            def safe_float(val, default=0.0):
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default

            m_act  = safe_float(latest.get('moisture'))
            ph_act = safe_float(latest.get('ph'))
            t_act  = safe_float(latest.get('temperature'))

            m_status  = "✓ OK" if thresholds['moisture_min'] <= m_act  <= thresholds['moisture_max'] else "⚠ OUT OF RANGE"
            ph_status = "✓ OK" if thresholds['ph_min']       <= ph_act <= thresholds['ph_max']       else "⚠ OUT OF RANGE"
            t_status  = "✓ OK" if thresholds['temp_min']     <= t_act  <= thresholds['temp_max']     else "⚠ OUT OF RANGE"

            node_info = f"""
### Node: {node.get('node_name', 'Unknown')} ###
**Crop:** {crop.title()}
**Reference Source:** {source}

**CURRENT vs TARGET:**
- Moisture: {m_act:.1f}% | Target: {thresholds['moisture_min']}-{thresholds['moisture_max']}% | {m_status}
- pH: {ph_act:.1f} | Target: {thresholds['ph_min']}-{thresholds['ph_max']} | {ph_status}
- Soil Temp: {t_act:.1f}°C | Target: {thresholds['temp_min']}-{thresholds['temp_max']}°C | {t_status}
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
                doc_name  = res['metadata'].get('document_name', 'Unknown')
                crop_tag  = res['metadata'].get('crop_type', '')
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
        language_instruction = """
**LANGUAGE:**
- If the user asks in Filipino/Tagalog, respond in Filipino
- If the user asks in English, respond in English
- Use PLAIN TEXT only - no markdown symbols (**, ###, -, etc.)
""" if is_filipino else """
**LANGUAGE:**
- Respond in English only
- Use PLAIN TEXT - no markdown formatting
"""
        
        system_prompt = f"""You are a professional Agricultural AI Assistant for farmers.

{language_instruction}

**YOUR ROLE:**
- You help with farming, crops, soil, and agriculture topics ONLY
- You speak BOTH English and Filipino
- Match the user's language: if they ask in Filipino, respond in Filipino. If English, respond in English.
- Use clear, professional language — not overly casual or too formal

**FILIPINO STYLE GUIDE:**
✓ GOOD: "Ang moisture ng iyong lupa ay mababa. Kailangan ng dagdag na tubig para sa tamang paglaki ng tanim."
✓ GOOD: "Ang pH level ay 5.2, mas mababa sa ideal na 6.0-6.8 para sa kamatis. Maglapat ng lime upang itaas ang pH."
❌ AVOID (too casual): "Uy pre, kulang yung lupa mo!"
❌ AVOID (random English mixing): "Kailangan mo ng more water para sa soil."

**RESPONSE STYLE:**
English example: "Both nodes are in good condition. Soil Node 01 has moisture at 62.6% and pH at 7.0, both within optimal range. Soil Node 02 shows similar healthy readings. Continue regular monitoring."
Filipino example: "Ang dalawang soil node ay nasa mabuting kondisyon. Ang Soil Node 01 ay may moisture na 62.6% at pH na 7.0, pareho ay nasa tamang range. Ang Soil Node 02 ay katulad din. Magpatuloy sa regular na monitoring."

**STRICT RULES:**
1. If the question is NOT about farming/agriculture → Politely refuse in the user's language
2. ALWAYS check the "CURRENT vs TARGET" comparison below
3. If you see "⚠ OUT OF RANGE" → Give a specific action to fix it
4. Cite documents when available
5. If no document exists for a crop → Suggest uploading one in Settings
6. Keep responses concise (2–4 sentences) unless a detailed explanation is needed
7. Be helpful and professional

**OUTPUT FORMAT RULES (CRITICAL):**
1. Use PLAIN TEXT ONLY - no markdown symbols like **, ###, ---, -, etc.
2. Use simple line breaks and spacing for readability
3. Keep responses SHORT (2-4 sentences maximum)
4. Be direct and specific
5. If multiple nodes, summarize briefly - don't repeat all data

**YOUR TASK:**
Answer the farmer's question based on the sensor data below. Be concise and helpful.

**CURRENT SENSOR DATA vs REFERENCE:**
{sensor_context}

**ACTIVE ALERTS:**
{alerts_str}

{rag_context}

**FARMER'S QUESTION:**
{user_question}

**REMEMBER:**
- Match the farmer's language exactly (English = English, Filipino = Filipino)
- Use professional, clear Filipino (not conversational Taglish)
- Be direct and practical
- Cite specific numbers from the sensor data
- Plain text only, 2-4 sentences, be specific and helpful."""

        try:
            response = openai_client.chat.completions.create(
                model=AIChatService.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_question},
                ],
                max_tokens=200,
                temperature=0.3,
            )

            answer = response.choices[0].message.content
            
            # Clean up any remaining markdown symbols
            answer = answer.replace('**', '').replace('###', '').replace('---', '')
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
        if not OPENAI_AVAILABLE or openai_client is None:
            return "AI comparison not available (OpenAI not configured)."

        nodes_ref = db.collection("nodes").stream()
        nodes_data = []

        for node_doc in nodes_ref:
            node   = node_doc.to_dict()
            latest = node.get("latest_readings", {})
            crop   = node.get("crop_type", "default")
            thresholds, source = AIChatService.get_thresholds(crop)

            nodes_data.append({
                "name":             node.get('node_name', node.get('node_id')),
                "crop":             crop,
                "moisture":         latest.get('moisture'),
                "ph":               latest.get('ph'),
                "temp":             latest.get('temperature'),
                "moisture_target":  f"{thresholds['moisture_min']}-{thresholds['moisture_max']}%",
                "ph_target":        f"{thresholds['ph_min']}-{thresholds['ph_max']}",
                "source":           source,
            })

        if len(nodes_data) < 2:
            return "Need at least 2 nodes to compare. / Kailangan ng at least 2 nodes para i-compare."

        try:
            response = openai_client.chat.completions.create(
                model=AIChatService.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Compare these soil sensor nodes. Which one needs attention first? "
                        f"Be concise — 2–3 sentences max.\n\n{json.dumps(nodes_data, indent=2)}"
                    ),
                }],
                max_tokens=150,
                temperature=0.4,
            )
            return response.choices[0].message.content

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

        if openai_client is None:
            return {
                "available": False,
                "message": "OPENAI_API_KEY not set. Add it to your .env file.",
            }

        try:
            openai_client.chat.completions.create(
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