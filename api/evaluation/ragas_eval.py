# api/evaluation/ragas_eval.py
"""
RAGAS + LangSmith evaluation for Sprout Hub's RAG chatbot.
 
Tests 3 models against the same ChromaDB knowledge base:
  - GPT-4o-mini      (current model)
  - Claude Sonnet 4.6 (comparison)
  - Gemini 3 Flash Preview (comparison)
 
Run with:
    python manage.py run_ragas_eval
"""

import os
import sys
import django
import time
import pandas as pd
import json
from pathlib import Path


# ── Django setup ──────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ── Dependencies ───────────────────────────────────────────────────────────
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    LLMContextRecall,
    LLMContextPrecisionWithReference,
)
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langsmith import traceable

# ── Your existing services ─────────────────────────────────────────────────
from api.rag_service import RAGService

# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — TEST QUESTIONS
# Written based on the documents you actually uploaded to ChromaDB.
# Ground truth = the correct answer based on your crop knowledge documents.
# ══════════════════════════════════════════════════════════════════════════
SOIL_TEST_CASES = [
    # --- CALAMANSI TEST CASES ---
        {
        "inputs": {"question": "Why are waterlogged areas not suitable for cultivating calamansi?"},
        "outputs": {"ground_truth": "Waterlogged areas are not suitable for cultivation because calamansi plants cannot tolerate too much moisture."}
    },
    
    {
        "inputs": {"question": "What is the ideal temperature range for calamansi to thrive?"},
        "outputs": {"ground_truth": "Calamansi is an evergreen tree that thrives in warm climates (65°F–77°F), or in places where it can tolerate drought as it is more tolerant than most citrus. Calamansi can also thrive in cool climates that are frostfree."}
    },
    
    {
        "inputs": {"question": "When will calamansi start to bear fruit?"},
        "outputs": {"ground_truth": "Calamansi trees will start to bear fruit one or two years after planting."},
    },

    # --- STRAWBERRY TEST CASES ---
    {
        "inputs": {"question": "What specific soil types and pH range are best suited for strawberry production?"},
        "outputs": {"ground_truth": "Strawberries grows best in well-drained, clay-loam and loamy soils with pH ranging from 5.5 to 6.5."}
    },
   
    {
        "inputs": {"question": "Which specific previous crops should be avoided when selecting a site for strawberries, and what disease do they leave behind?"},
        "outputs": {"ground_truth": "Avoid planting sites that are previously used for Solanaceous crops (tomato, potato, pepper, eggplant) unless they can be fumigated. Soils previously planted to Solanaceous crops may contain Verticillium wilt, a persistent fungal organism in the soil."}
    },
    
    {
        "inputs": {"question": "What are the specific plant and row spacing dimensions when using the matted row or spaced-matted row system for strawberries?"},
        "outputs": {"ground_truth": "In both the matted row and spaced-matted row systems, the original mother plants are planted 18 to 36 inches apart in rows 36 to 48 inches apart."}
    }
]

# ── One universal prompt for ALL models ───────────────────────────────────
# Same prompt is used for GPT, Claude, and Gemini.
# This ensures a fair comparison — the only variable is the model itself.
SYSTEM_PROMPT = """You are an agricultural assistant for Sprout Hub, an IoT soil monitoring system.
If the context does not have enough information, say "I don't have enough information in the knowledge base to answer that."
Be concise and mention specific values when available."""

# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — RAG PIPELINE
# Same retrieval for all models (ChromaDB).
# Only the LLM call changes per model.
# ══════════════════════════════════════════════════════════════════════════
 
@traceable(name="sprouthub-retrieve")
def retrieve_context(question: str) -> list[str]:
    """Retrieves relevant chunks from your ChromaDB knowledge base."""
    results = RAGService.search_knowledge(question, n_results=4)
    
    #----- Debug
    print(f"  DEBUG results type: {type(results)}")
    if results:
        print(f"  DEBUG first result type: {type(results[0])}")
        print(f"  DEBUG first result value: {results[0]}")
        
        
    return [r["text"] for r in results] if results else []
 
 
@traceable(name="sprouthub-generate")
def generate_answer(question: str, context_texts: list[str], model_name: str) -> str:
    """
    Sends the retrieved context + question to the specified LLM.
    Same prompt is used for all models — only the API call differs.
    """
    context_str = "\n\n".join(context_texts) if context_texts else "No documents found."
 
    # One universal prompt for all models
    full_prompt = f"""{SYSTEM_PROMPT}
 
Context:
{context_str}
 
Question: {question}"""
 
    # ── GPT-4o-mini ───────────────────────────────────────────────────
    if "gpt" in model_name:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content
 
    # ── Claude Sonnet 4.6 ─────────────────────────────────────────────
    elif "claude" in model_name:
        from anthropic import Anthropic, InternalServerError
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        
        for attempt in range (3):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=300,
                    messages=[{"role": "user", "content": full_prompt}],
                )
                return response.content[0].text
            except InternalServerError:
                if attempt < 2:
                    print(f"  ⚠️  Claude API error, retrying... (attempt {attempt + 1}/3)")
                    time.sleep(5)  # wait before retrying
                else:
                    raise Exception("Claude API failed after 3 attempts.")
 
    # ── Gemini 3 Flash Preview ──────────────────────────────────────────────
    elif "gemini" in model_name:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(full_prompt)
        return response.text
 
    else:
        raise ValueError(f"Unknown model: {model_name}")
 
 
@traceable(name="sprouthub-rag-pipeline")
def run_rag_pipeline(question: str, model_name: str) -> dict:
    """Full pipeline: retrieve from ChromaDB → generate with LLM."""
    contexts = retrieve_context(question)
    answer = generate_answer(question, contexts, model_name)
    return {"answer": answer, "contexts": contexts}


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 — RAGAS EVALUATION
# Builds the dataset and scores it with all 4 metrics.
# ══════════════════════════════════════════════════════════════════════════

def build_eval_dataset(model_name: str) -> Dataset:
    rows = []
    for i, case in enumerate(SOIL_TEST_CASES):
        question     = case["inputs"]["question"]
        ground_truth = case["outputs"]["ground_truth"]
        print(f"  → [{i+1}/{len(SOIL_TEST_CASES)}] {question[:60]}...")
        
        try:
            result = run_rag_pipeline(question, model_name)
            row = {
                "user_input":         question,
                "response":           result["answer"],
                "retrieved_contexts": result["contexts"],
                "reference":          ground_truth,
            }
        except Exception as e:
            print(f" Failed: {e}")
            row = {
                "user_input":   question,
                "response":     "ERROR: LLM call failed.",
                "retrieved_contexts": [],
                "reference":    ground_truth,
            }
            
        rows.append(row)
        
        safe_name = model_name.replace("/", "-").replace(":", "-")
        Path(f"raw_responses_{safe_name}.json").write_text(
            json.dumps(rows, indent=2)
        )
    return Dataset.from_list(rows)
 
 
def evaluate_model(model_name: str, evaluator_llm) -> dict:
    """Scores one model using all 4 RAGAS metrics."""
    print(f"\n{'='*55}")
    print(f"  Evaluating: {model_name}")
    print(f"{'='*55}")

    dataset = build_eval_dataset(model_name)
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            AnswerRelevancy(),
            LLMContextRecall(),
            LLMContextPrecisionWithReference(),
        ],
        llm=evaluator_llm,
    )

    # Convert result to pandas first — works with all RAGAS versions
    df = result.to_pandas()
    
    print(f" DEBUG Columns:   {df.columns.tolist()}")

    def safe_score(col):
        """Handles both old (float) and new (list) RAGAS return formats."""
        if col not in df.columns:
            return 0.0
        val = df[col].dropna().mean()  # average across all test questions
        if pd.isna(val): 
            return 0.0
        return round(float(val), 4)

    scores = {
        "model":               model_name,
        "faithfulness":        safe_score("faithfulness"),
        "answer_relevancy":    safe_score("answer_relevancy"),
        "context_recall":      safe_score("context_recall"),
        "context_precision":   safe_score("llm_context_precision_with_reference"),
    }
    scores["overall"] = round(
        (scores["faithfulness"] + scores["answer_relevancy"] +
         scores["context_recall"] + scores["context_precision"]) / 4, 4
    )

    print(f"\n  Faithfulness:        {scores['faithfulness']}")
    print(f"  Answer Relevancy:    {scores['answer_relevancy']}")
    print(f"  Context Recall:      {scores['context_recall']}")
    print(f"  Context Precision:   {scores['context_precision']}")
    print(f"  {'─'*35}")
    print(f"  Overall:             {scores['overall']}")

    return scores


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 — MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════

def run_evaluation():
    evaluator_llm = LangchainLLMWrapper(
        ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.environ["OPENAI_API_KEY"],
        )
    )

    models_to_test = ["gpt-4o-mini", "claude-sonnet-4-6", "gemini-3-flash-preview"]
    results = []

    for model in models_to_test:
        try:
            scores = evaluate_model(model, evaluator_llm)
            results.append(scores)

            
            Path("eval_results.json").write_text(json.dumps(results, indent=2))
            print(f"  💾 Progress saved → eval_results.json")

        except Exception as e:
            print(f"\n  ❌ {model} failed: {e}")
            print(f"  Skipping to next model...\n")
            continue
        
    if not results:
        print("\n❌ No models completed successfully.")
        return results
    
# ── Print comparison table ─────────────────────────────────────

    metrics = [
        "faithfulness",
        "answer_relevancy",
        "context_recall",
        "context_precision",
        "overall",
    ]

    col_w = 16
    print(f"\n{'='*80}")
    print("  SPROUT HUB — RAGAS MODEL COMPARISON")
    print(f"{'='*85}")
    print(f"  {'Metric':<25}", end="")
    for r in results:
        print(f"{r['model']:>{col_w}}", end="")
    print(f"{'Winner':>{col_w}}")
    print(f"  {'-'*80}")

    for m in metrics:
        scores = [r[m] for r in results]
        best = max(scores)
        winner_idx = scores.index(best)
        winner_name = results[winner_idx]["model"].split("-")[0].upper()
        label = m.replace("_", " ").title()
        print(f"  {label:<25}", end="")
        for s in scores:
            marker = " ✓" if s == best else "  "
            print(f"{str(s)+marker:>{col_w}}", end="")
        print(f"{winner_name:>{col_w}}")

    print(f"{'='*85}")

    # ── PLACE 2: Final save with all results ──────────────────────
    output_path = Path("eval_results.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n  ✅ Final results saved to: {output_path.resolve()}")
    print(f"  🔍 Traces at: https://smith.langchain.com\n")

    return results
 
 
if __name__ == "__main__":
    run_evaluation()