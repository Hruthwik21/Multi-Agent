You MUST output your final answer as a JSON object matching this schema:

{
  "claims": [
    {
      "issue": "string, ≤500 chars, imperative description",
      "file": "relative/path/to/file.py",
      "line": 42,
      "severity": "critical|high|medium|low|nit",
      "category": "bug|security|perf|style|test|docs",
      "evidence": "code excerpt or reasoning",
      "suggested_fix": "optional corrected code",
      "confidence": 0.0-1.0
    }
  ]
}

RULES:
- Output ONLY the JSON. No prose, no markdown fences.
- If you find nothing, output {"claims": []}.
- Every claim MUST have a file and line within the diff.
- Do NOT invent line numbers. Use the provided diff.
- Confidence < 0.4 -> omit the claim.
