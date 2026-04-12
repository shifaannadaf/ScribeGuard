"""
SOAP Note Prompt Engineering — Test Runner
==========================================
Runs each transcript against the system prompt via OpenAI GPT-4 and saves
the structured JSON output plus a markdown summary.

Usage:
    export OPENAI_API_KEY=sk-...
    python test/test_prompt.py --version v1
    python test/test_prompt.py --version v2

Requirements:
    pip install openai
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
TEST_DIR     = Path(__file__).parent
PROMPT_DIR   = TEST_DIR / "prompts"
TRANSCRIPT_DIR = TEST_DIR / "transcripts"
RESULTS_DIR  = TEST_DIR / "results"

PROMPTS = {
    "v1": PROMPT_DIR / "system_prompt_v1.md",
    "v2": PROMPT_DIR / "system_prompt_v2.md",
}

TRANSCRIPTS = sorted(TRANSCRIPT_DIR.glob("transcript_*.txt"))

# ── Load system prompt ─────────────────────────────────────────────────────────

def load_system_prompt(version: str) -> str:
    path = PROMPTS.get(version)
    if not path or not path.exists():
        raise FileNotFoundError(f"Prompt file not found for version '{version}': {path}")
    text = path.read_text()
    # Extract the raw prompt text (everything after the second --- frontmatter block)
    # The .md files have a "## Prompt Text" section followed by the actual prompt
    marker = "## Prompt Text"
    if marker in text:
        text = text.split(marker, 1)[1].strip()
    return text

# ── Call GPT-4 ─────────────────────────────────────────────────────────────────

def generate_soap_note(client: OpenAI, system_prompt: str, transcript: str, model: str = "gpt-4o") -> dict:
    """
    Send transcript to GPT-4 with system prompt, return parsed JSON.
    Returns dict with keys: raw_response, parsed, error
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"Please convert the following clinical transcript into a SOAP note:\n\n{transcript}"},
            ],
            temperature=0.2,   # low temperature for clinical consistency
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if model wrapped output anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0].strip()

        parsed = json.loads(raw)
        return {"raw_response": raw, "parsed": parsed, "error": None}

    except json.JSONDecodeError as e:
        return {"raw_response": raw if "raw" in dir() else "", "parsed": None, "error": f"JSON parse error: {e}"}
    except Exception as e:
        return {"raw_response": "", "parsed": None, "error": str(e)}

# ── Validate output ────────────────────────────────────────────────────────────

REQUIRED_KEYS = {"subjective", "objective", "assessment", "plan", "medications"}

def validate_output(parsed: dict | None) -> dict:
    if parsed is None:
        return {"valid": False, "issues": ["No parsed output (JSON error)"]}

    issues = []
    missing = REQUIRED_KEYS - set(parsed.keys())
    if missing:
        issues.append(f"Missing keys: {missing}")

    for key in REQUIRED_KEYS - {"medications"}:
        val = parsed.get(key, "")
        if not isinstance(val, str):
            issues.append(f"'{key}' must be a string, got {type(val).__name__}")

    meds = parsed.get("medications", [])
    if not isinstance(meds, list):
        issues.append(f"'medications' must be a list, got {type(meds).__name__}")

    # Warn on suspiciously short sections (may indicate hallucination or failure)
    for key in ("subjective", "objective", "assessment", "plan"):
        val = parsed.get(key, "")
        if isinstance(val, str) and 0 < len(val) < 20:
            issues.append(f"'{key}' is suspiciously short ({len(val)} chars): '{val}'")

    return {"valid": len(issues) == 0, "issues": issues}

# ── Main test loop ─────────────────────────────────────────────────────────────

def run_tests(version: str, model: str = "gpt-4o"):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    system_prompt = load_system_prompt(version)
    output_dir = TEST_DIR / "outputs" / version
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SOAP Prompt Test — {version.upper()}   model={model}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    summary_rows = []

    for tx_path in TRANSCRIPTS:
        transcript_text = tx_path.read_text()

        # Extract metadata comment lines at the top
        meta_lines = [l.lstrip("# ").strip() for l in transcript_text.splitlines() if l.startswith("#")]
        label = meta_lines[0] if meta_lines else tx_path.stem

        print(f"▶  {label}")

        result = generate_soap_note(client, system_prompt, transcript_text, model=model)
        validation = validate_output(result["parsed"])

        status = "✓ PASS" if (result["error"] is None and validation["valid"]) else "✗ FAIL"
        print(f"   Status : {status}")
        if result["error"]:
            print(f"   Error  : {result['error']}")
        if validation["issues"]:
            for issue in validation["issues"]:
                print(f"   Issue  : {issue}")
        if result["parsed"]:
            meds = result["parsed"].get("medications", [])
            print(f"   Meds   : {meds}")

        # Save output JSON
        out_file = output_dir / (tx_path.stem + "_output.json")
        with open(out_file, "w") as f:
            json.dump({
                "transcript_file": tx_path.name,
                "prompt_version":  version,
                "model":           model,
                "timestamp":       datetime.now().isoformat(),
                "result":          result,
                "validation":      validation,
            }, f, indent=2)

        summary_rows.append({
            "file":   tx_path.name,
            "label":  label,
            "status": status,
            "error":  result["error"],
            "issues": validation["issues"],
            "meds":   result["parsed"].get("medications", []) if result["parsed"] else [],
        })

        print()
        time.sleep(1)  # rate-limit courtesy pause

    # Write markdown summary
    write_summary(version, model, summary_rows)

    total = len(summary_rows)
    passed = sum(1 for r in summary_rows if "PASS" in r["status"])
    print(f"\nResults: {passed}/{total} passed")
    print(f"Outputs saved to: {output_dir}")
    print(f"Summary saved to: {RESULTS_DIR / f'test_results_{version}.md'}\n")

# ── Write markdown summary ─────────────────────────────────────────────────────

def write_summary(version: str, model: str, rows: list):
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"test_results_{version}.md"
    total = len(rows)
    passed = sum(1 for r in rows if "PASS" in r["status"])

    lines = [
        f"# Test Results — Prompt {version.upper()}",
        f"",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Model:** {model}  ",
        f"**Pass rate:** {passed}/{total}",
        f"",
        f"---",
        f"",
    ]

    for r in rows:
        lines.append(f"## {r['label']}")
        lines.append(f"**File:** `{r['file']}`  ")
        lines.append(f"**Status:** {r['status']}  ")
        if r["error"]:
            lines.append(f"**Error:** {r['error']}  ")
        if r["issues"]:
            lines.append(f"**Validation issues:**")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
        if r["meds"]:
            lines.append(f"**Extracted medications:**")
            for m in r["meds"]:
                lines.append(f"- {m}")
        lines.append("")

    out.write_text("\n".join(lines))

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test SOAP note system prompt against transcripts")
    parser.add_argument("--version", choices=["v1", "v2"], default="v1", help="Prompt version to test")
    parser.add_argument("--model",   default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    args = parser.parse_args()

    run_tests(version=args.version, model=args.model)
