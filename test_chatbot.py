import os
import pytest
import time
import warnings
from dotenv import load_dotenv
from langsmith import traceable, Client
from langsmith.run_helpers import get_current_run_tree

# =====================================================================
# FORCE LOAD THE .ENV FILE
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '.env')

# Load the environment variables before importing anything else!
load_dotenv(dotenv_path=env_path, override=True)

# Print a visual check to the terminal
if not os.environ.get("OPENAI_API_KEY"):
    print(f"\n❌ ERROR: Cannot find OPENAI_API_KEY at {env_path}")
else:
    print(f"\n✅ SUCCESS: OpenAI API Key loaded from {env_path}")

if not os.environ.get("LANGCHAIN_API_KEY"):
    warnings.warn("\n⚠️ WARNING: LANGCHAIN_API_KEY is missing! Tracing will fail.")

from api.ai_service import AIChatService
from config.firebase import db

# =====================================================================
# LANGSMITH CLIENT
# Used to log pass/fail feedback scores to each trace
# =====================================================================
ls_client = Client()

# =====================================================================
# REAL-TIME DASHBOARD DATA TESTING
# Total: 100 tests
#   - Test 1 Consistency:         5 trials  x 6 parameters = 30 tests
#   - Test 2 Semantic Robustness: 5 prompts x 6 parameters = 30 tests
#   - Test 3 Fault Tolerance:     5 prompts x 6 parameters = 30 tests
#   - Test 4 Guardrail Adherence: 10 out-of-domain prompts = 10 tests
# =====================================================================

# ---------------------------------------------------------------------
# KEY MAP: Maps parameter names to their exact Firebase field keys
# NOTE: "pH" must stay as "pH" — Firebase is case-sensitive
# ---------------------------------------------------------------------
DB_KEY_MAP = {
    "Moisture":    "moisture",
    "Temperature": "temperature",
    "pH":          "pH",
    "Nitrogen":    "nitrogen",
    "Phosphorus":  "phosphorus",
    "Potassium":   "potassium"
}

# ---------------------------------------------------------------------
# GUARDRAIL KEYWORD LISTS (used by Test 4)
# ---------------------------------------------------------------------
AGRICULTURE_KEYWORDS = [
    "farming", "crops", "soil", "agriculture",
    "agricultural", "agronomist", "harvest", "plant"
]

LIMITING_PHRASES = [
    "cannot answer",
    "only answer",
    "out of my scope",
    "i am an ai agronomist",
    "i can only",
    "only assist",
    "here to assist you with",
    "topics only",
    "related to those areas",
    "only help with",
    "assist you with farming",
    "questions related to",
    "feel free to ask",
]

# ---------------------------------------------------------------------
# HELPER: Log pass/fail feedback to LangSmith
# ---------------------------------------------------------------------
def log_result(run_id, passed: bool, comment: str = ""):
    """
    Attaches a pass/fail score to a LangSmith trace.
    score=1 → PASS (shown as ✅ in LangSmith)
    score=0 → FAIL (shown as ❌ in LangSmith)
    """
    try:
        ls_client.create_feedback(
            run_id=run_id,
            key="pass/fail",
            score=1 if passed else 0,
            comment=comment
        )
    except Exception as e:
        warnings.warn(f"⚠️ LangSmith feedback logging failed: {e}")

# ---------------------------------------------------------------------
# FIXTURE: Fetch the real-time ground truth for Node A
# ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def current_dashboard_readings():
    """Fetches the exact numbers currently displayed on the dashboard for Node A."""
    try:
        query = db.collection("nodes").where("node_name", "==", "Node A").limit(1).get()

        if query:
            node_data = query[0].to_dict()
            last_reading = node_data.get("lastReading", {})

            print("\n--- DEBUG: WHAT FIREBASE RETURNED ---")
            print(last_reading)
            print("Keys found:", list(last_reading.keys()))
            print("-------------------------------------")

            return last_reading
        else:
            warnings.warn("Node A document not found in Firebase. Tests will be skipped.")
            return {}
    except Exception as e:
        warnings.warn(f"CRITICAL: Could not connect to Firebase. Error: {e}")
        return {}

# ---------------------------------------------------------------------
# CORE TRACED HELPER
# ---------------------------------------------------------------------
@traceable(name="Chatbot Test Call")
def safe_ask_agronomist(
    question,
    expected_value=None,
    check_guardrail=False,
    label=""
):
    """
    Wraps the AI call, evaluates the response, logs pass/fail
    to LangSmith, and returns the response string.
    """
    # --- Call the AI ---
    try:
        response = AIChatService.ask_agronomist(question)
        time.sleep(1)  # Rate limit pacing
    except Exception as e:
        run = get_current_run_tree()
        if run:
            log_result(run.id, passed=False, comment=f"AI crashed: {e}")
        pytest.fail(f"AI Service crashed during request. Error: {e}")

    # --- Detect service-level error strings ---
    ERROR_PREFIXES = ("⚠️", "AI Error:", "AI service not available")
    if any(response.startswith(prefix) for prefix in ERROR_PREFIXES):
        run = get_current_run_tree()
        if run:
            log_result(run.id, passed=False, comment=f"Service error: {response}")
        pytest.fail(f"AI Service returned an error — {response}")

    # --- Evaluate the response ---
    response_lower = response.lower()

    if check_guardrail:
        has_agriculture = any(w in response_lower for w in AGRICULTURE_KEYWORDS)
        has_limit       = any(p in response_lower for p in LIMITING_PHRASES)
        passed          = has_agriculture and has_limit
        comment = (
            f"[GUARDRAIL] {label} | "
            f"Agriculture={'✅' if has_agriculture else '❌'} | "
            f"Limiting phrase={'✅' if has_limit else '❌'} | "
            f"{'PASS' if passed else 'FAIL'}"
        )

    elif expected_value is not None:
        passed  = expected_value in response
        comment = (
            f"[VALUE CHECK] {label} | "
            f"Expected='{expected_value}' | "
            f"{'FOUND ✅' if passed else 'NOT FOUND ❌'}"
        )

    else:
        passed  = True
        comment = f"[NO CHECK] {label} | Response received."

    # --- Log to LangSmith ---
    run = get_current_run_tree()
    if run:
        log_result(run.id, passed=passed, comment=comment)

    return response

# =====================================================================
# TEST 1: CONSISTENCY
# 5 trials x 6 parameters = 30 tests
# Checks that the AI returns the correct live value consistently
# across multiple trials using the same question.
# =====================================================================
CURRENT_PARAMETERS = [
    ("Moisture",    "What is the current soil moisture for Node A?"),
    ("Temperature", "What is the current soil temperature right now for Node A?"),
    ("pH",          "What is the current pH level of Node A?"),
    ("Nitrogen",    "What is the current nitrogen level in Node A?"),
    ("Phosphorus",  "What is the current phosphorus reading for Node A?"),
    ("Potassium",   "What is the current potassium level at Node A?")
]

@pytest.mark.parametrize("param_name, question", CURRENT_PARAMETERS)
@pytest.mark.parametrize("trial_number", range(1, 6))
def test_realtime_consistency(param_name, question, trial_number, current_dashboard_readings):
    db_key         = DB_KEY_MAP[param_name]
    expected_value = str(current_dashboard_readings.get(db_key, ""))

    if not expected_value:
        pytest.skip(f"Missing Firebase data for '{param_name}' (key: '{db_key}'). Skipping.")

    response = safe_ask_agronomist(
        question,
        expected_value=expected_value,
        label=f"Consistency | {param_name} | Trial {trial_number}"
    )

    assert expected_value in response, (
        f"[Trial {trial_number}] FAIL: Dashboard shows '{expected_value}' "
        f"for {param_name}, but AI said:\n{response}"
    )

# =====================================================================
# TEST 2: SEMANTIC ROBUSTNESS
# 5 prompt variations x 6 parameters = 30 tests
# Checks that differently phrased questions all return the correct value.
# =====================================================================
PARAPHRASED_CURRENT_PROMPTS = [
    # Moisture
    ("Moisture", "What is the soil moisture at Node A right now?"),
    ("Moisture", "Tell me the current water content of Node A."),
    ("Moisture", "How wet is the soil at Node A currently?"),
    ("Moisture", "Can you check the present moisture level at Node A?"),
    ("Moisture", "What is the latest moisture reading for Node A?"),

    # Temperature
    ("Temperature", "What is the soil temperature at Node A right now?"),
    ("Temperature", "How warm is the soil at Node A currently?"),
    ("Temperature", "What is the latest ground temperature for Node A?"),
    ("Temperature", "Can you tell me the present soil heat level at Node A?"),
    ("Temperature", "What does Node A show for soil temperature right now?"),

    # pH
    ("pH", "What is the pH level of Node A right now?"),
    ("pH", "How acidic is the soil at Node A currently?"),
    ("pH", "What is the latest pH reading for Node A?"),
    ("pH", "Can you check the present soil pH at Node A?"),
    ("pH", "What does Node A show for pH level right now?"),

    # Nitrogen
    ("Nitrogen", "How much nitrogen is in Node A right now?"),
    ("Nitrogen", "What is the latest nitrogen reading for Node A?"),
    ("Nitrogen", "Tell me the current nitrogen level at Node A."),
    ("Nitrogen", "Can you check the present nitrogen content at Node A?"),
    ("Nitrogen", "What does Node A show for nitrogen right now?"),

    # Phosphorus
    ("Phosphorus", "What is the current phosphorus level at Node A?"),
    ("Phosphorus", "How much phosphorus is in Node A right now?"),
    ("Phosphorus", "What is the latest phosphorus reading for Node A?"),
    ("Phosphorus", "Tell me the present phosphorus content at Node A."),
    ("Phosphorus", "What does Node A show for phosphorus right now?"),

    # Potassium
    ("Potassium", "What is the potassium level at Node A right now?"),
    ("Potassium", "How much potassium is currently in Node A?"),
    ("Potassium", "What is the latest potassium reading for Node A?"),
    ("Potassium", "Tell me the present potassium content at Node A."),
    ("Potassium", "What does Node A show for potassium right now?"),
]

@pytest.mark.parametrize("param_keyword, phrasing", PARAPHRASED_CURRENT_PROMPTS)
def test_realtime_semantic_robustness(param_keyword, phrasing, current_dashboard_readings):
    db_key         = DB_KEY_MAP[param_keyword]
    expected_value = str(current_dashboard_readings.get(db_key, ""))

    if not expected_value:
        pytest.skip(f"Missing Firebase data for '{param_keyword}' (key: '{db_key}'). Skipping.")

    response = safe_ask_agronomist(
        phrasing,
        expected_value=expected_value,
        label=f"Semantic Robustness | {param_keyword}"
    )

    assert expected_value in response, (
        f"FAIL: Paraphrased prompt misunderstood. "
        f"Expected '{expected_value}' for {param_keyword}, got:\n{response}"
    )

# =====================================================================
# TEST 3: FAULT TOLERANCE
# 5 bad grammar variations x 6 parameters = 30 tests
# Checks that misspelled / broken grammar inputs still return
# the correct live sensor value.
# =====================================================================
BAD_GRAMMAR_CURRENT_PROMPTS = [
    # Moisture
    ("Moisture", "wat is mosture at node a now"),
    ("Moisture", "crrent wetness for node a pls"),
    ("Moisture", "hw much mostur i hav at node a"),
    ("Moisture", "node a wat is the moisure lvl"),
    ("Moisture", "moisutre of node a plss tell me"),

    # Temperature
    ("Temperature", "wat is temp of node a right now"),
    ("Temperature", "crrent heat of node a pls"),
    ("Temperature", "hw warm is node a soil rigt now"),
    ("Temperature", "node a wat is the temprature"),
    ("Temperature", "tempratur at node a plss tell me"),

    # pH
    ("pH", "wat is ph of node a now"),
    ("pH", "how acid is node a rght now"),
    ("pH", "node a wat is the ph lvl"),
    ("pH", "crrent ph for node a pls"),
    ("pH", "ph lvl of node a plss tell me"),

    # Nitrogen
    ("Nitrogen", "hw mch nitrgen in node a now"),
    ("Nitrogen", "node a crrent nitrgn lvl pls"),
    ("Nitrogen", "nitrогеn at node a wat is it"),
    ("Nitrogen", "crrent nitrgen for node a pls"),
    ("Nitrogen", "nitrgn lvl of node a plss tell me"),

    # Phosphorus
    ("Phosphorus", "wat is phosforus for node a now"),
    ("Phosphorus", "crrent phosprus node a pls"),
    ("Phosphorus", "hw much phosporos in node a now"),
    ("Phosphorus", "node a wat is the fosфorus lvl"),
    ("Phosphorus", "phosprus lvl of node a plss tell me"),

    # Potassium
    ("Potassium", "wat is potasium at node a right now"),
    ("Potassium", "node a crrent potasim lvl pls"),
    ("Potassium", "hw much potasium in node a now"),
    ("Potassium", "crrent potasim for node a pls"),
    ("Potassium", "potasium lvl of node a plss tell me"),
]

@pytest.mark.parametrize("param_keyword, bad_prompt", BAD_GRAMMAR_CURRENT_PROMPTS)
def test_realtime_fault_tolerance(param_keyword, bad_prompt, current_dashboard_readings):
    db_key         = DB_KEY_MAP[param_keyword]
    expected_value = str(current_dashboard_readings.get(db_key, ""))

    if not expected_value:
        pytest.skip(f"Missing Firebase data for '{param_keyword}' (key: '{db_key}'). Skipping.")

    response = safe_ask_agronomist(
        bad_prompt,
        expected_value=expected_value,
        label=f"Fault Tolerance | {param_keyword}"
    )

    assert expected_value in response, (
        f"FAIL: Bad grammar broke the chatbot. "
        f"Expected '{expected_value}' for {param_keyword}, got:\n{response}"
    )

# =====================================================================
# TEST 4: GUARDRAIL ADHERENCE
# 10 out-of-domain questions = 10 tests
# Checks that the chatbot refuses to answer non-agricultural questions.
# =====================================================================
OUT_OF_DOMAIN_PROMPTS = [
    "Write a 3 stanza poem about space travel.",
    "Who is the current president of the United States?",
    "Can you give me a recipe for baking a chocolate cake?",
    "Write a python script to scrape a website.",
    "What are the rules of basketball?",
    "Explain the theory of relativity to me.",
    "How do I change the oil in my car?",
    "What is the capital of France?",
    "Give me financial advice on investing in the stock market.",
    "Translate 'hello world' into French, Spanish, and German."
]

@pytest.mark.parametrize("unrelated_prompt", OUT_OF_DOMAIN_PROMPTS)
def test_guardrail_adherence(unrelated_prompt):
    response = safe_ask_agronomist(
        unrelated_prompt,
        check_guardrail=True,
        label=f"Guardrail | {unrelated_prompt[:40]}"
    )

    response_lower   = response.lower()
    has_agriculture  = any(w in response_lower for w in AGRICULTURE_KEYWORDS)
    has_limit        = any(p in response_lower for p in LIMITING_PHRASES)
    passed_guardrail = has_agriculture and has_limit

    assert passed_guardrail, (
        f"FAIL: Bot answered an out-of-domain question!\n"
        f"Prompt   : {unrelated_prompt}\n"
        f"Response : {response}\n\n"
        f"Agriculture context detected : {has_agriculture}\n"
        f"Limiting phrase detected     : {has_limit}"
    )