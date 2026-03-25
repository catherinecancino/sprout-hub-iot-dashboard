# api/management/commands/run_ragas_eval.py

from django.core.management.base import BaseCommand
from api.evaluation.ragas_eval import SOIL_TEST_CASES, retrieve_context
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI
import os


class Command(BaseCommand):
    help = "Run RAGAS + LangSmith evaluation for Sprout Hub RAG chatbot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            default="all",
            help=(
                "Which model to evaluate: "
                "'gpt-4o-mini', 'claude-sonnet-4-6', 'gemini-3-flash-preview', "
                "or 'all' (default)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Test your config without calling any LLM or spending any credits",
        )

    def handle(self, **options):
        self.stdout.write(self.style.NOTICE(
            "\n🌱 Sprout Hub — RAGAS Evaluation\n"
            "   Same prompt used for all models (fair comparison)\n"
            "   Traces → https://smith.langchain.com\n"
        ))

        # ── DRY RUN MODE ──────────────────────────────────────────────
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                "⚡ DRY RUN MODE — No LLM calls, no credits used\n"
            ))

            # 1. Check environment variables
            self.stdout.write("Checking environment variables...")
            env_vars = {
                "OPENAI_API_KEY":    os.environ.get("OPENAI_API_KEY"),
                "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
                "GOOGLE_API_KEY":    os.environ.get("GOOGLE_API_KEY"),
                "LANGCHAIN_API_KEY": os.environ.get("LANGCHAIN_API_KEY"),
            }
            all_good = True
            for key, val in env_vars.items():
                if val:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {key} — found"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {key} — MISSING"))
                    all_good = False

            # 2. Check test questions loaded correctly
            self.stdout.write(f"\nChecking test questions...")
            try:
                for case in SOIL_TEST_CASES:
                    q = case["inputs"]["question"]
                    g = case["outputs"]["ground_truth"]
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ {len(SOIL_TEST_CASES)} test questions loaded correctly"
                ))
            except KeyError as e:
                self.stdout.write(self.style.ERROR(
                    f"  ❌ Test case structure error: missing key {e}"
                ))
                all_good = False

            # 3. Check ChromaDB retrieval works
            self.stdout.write(f"\nChecking ChromaDB retrieval...")
            try:
                test_q = SOIL_TEST_CASES[0]["inputs"]["question"]
                results = retrieve_context(test_q)
                if results:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✅ ChromaDB returned {len(results)} chunks for test question"
                    ))
                    self.stdout.write(f"     Sample: \"{results[0][:80]}...\"")
                else:
                    self.stdout.write(self.style.WARNING(
                        "  ⚠️  ChromaDB returned 0 chunks — make sure you uploaded documents in Settings"
                    ))
                    all_good = False
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ ChromaDB error: {e}"))
                all_good = False

            # 4. Check models that will be tested
            model_choice = options["model"]
            models = (
                ["gpt-4o-mini", "claude-sonnet-4-6", "gemini-3-flash-preview"]
                if model_choice == "all"
                else [model_choice]
            )
            self.stdout.write(f"\nModels to evaluate:")
            for m in models:
                self.stdout.write(f"  → {m}")

            # 5. Cost estimate
            n_questions = len(SOIL_TEST_CASES)
            self.stdout.write(f"\nCost estimate:")
            self.stdout.write(f"  {n_questions} questions × {len(models)} models = {n_questions * len(models)} LLM calls")
            self.stdout.write(f"  + {n_questions * len(models)} RAGAS evaluator calls (GPT-4o)")
            self.stdout.write(f"  Estimated cost: ~${n_questions * len(models) * 0.002:.2f} total")

            # 6. Final verdict
            self.stdout.write("")
            if all_good:
                self.stdout.write(self.style.SUCCESS(
                    "✅ All checks passed — safe to run:\n"
                    "   python manage.py run_ragas_eval"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    "❌ Fix the issues above before running the full evaluation"
                ))
            return

        # ── FULL EVAL MODE ────────────────────────────────────────────
        from api.evaluation.ragas_eval import run_evaluation, evaluate_model
        model_choice = options["model"]

        if model_choice == "all":
            run_evaluation()
        else:
            evaluator_llm = LangchainLLMWrapper(
                ChatOpenAI(
                    model="gpt-4o",
                    temperature=0,
                    api_key=os.environ["OPENAI_API_KEY"],
                )
            )
            scores = evaluate_model(model_choice, evaluator_llm)
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Done. Overall score: {scores['overall']}")
            )