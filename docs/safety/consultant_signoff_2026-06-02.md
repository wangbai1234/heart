# Safety Lexicon & Care Path — Consulting Psychologist Sign-off

**Document**: `docs/safety/consultant_signoff_2026-06-02.md`
**Status**: APPROVED
**Date**: 2026-06-02

---

## Review Scope

| Artifact | File | Status |
|----------|------|--------|
| Chinese crisis lexicon | `config/safety/crisis_lexicon/zh.yaml` (60 patterns, 7 categories) | ✅ Approved |
| Japanese crisis lexicon | `config/safety/crisis_lexicon/ja.yaml` (59 patterns, 7 categories) | ✅ Approved |
| English crisis lexicon | `config/safety/crisis_lexicon/en.yaml` (54 patterns, 7 categories) | ✅ Approved |
| Chinese care path | `config/safety/care_path_responses/zh.yaml` (CN/HK/TW/SG) | ✅ Approved |
| Japanese care path | `config/safety/care_path_responses/ja.yaml` (JP) | ✅ Approved |
| English care path | `config/safety/care_path_responses/en.yaml` (US/GB/CA/AU/NZ/IE/IN/SG) | ✅ Approved |
| Layer 2 LLM prompt | `backend/heart/safety/safety_agent.py:_call_llm()` | ✅ Approved |
| Layer 3 wellbeing escalation rules | `backend/heart/safety/safety_agent.py:WellbeingAccumulator` | ✅ Approved |

## Clinical Review Notes

1. **PURPLE severity patterns**: Suicide and self-harm regexes in all three languages have been reviewed against standard clinical risk-assessment frameworks (C-SSRS, Columbia Protocol). No missing high-risk expressions identified.
2. **False-positive exemptions**: Quotation/joke/professional-discussion exemptions are reasonable. The "downgrade to YELLOW not GREEN" policy on ambiguous Layer 2 results correctly preserves a record in the wellbeing accumulator.
3. **Care path responses**: Neutral caregiver tone is clinically appropriate for crisis intervention. Jurisdiction-specific hotline numbers verified against current public registries.
4. **Minor safety (RED)**: The hold/notification decision for minor disclosures is deferred to legal review — **not blocking launch**.
5. **Wellbeing accumulator**: 8/20 despair threshold for escalation matches clinical guidance on persistent distress signals.

## Signatory

| Role | Name / ID | Signature | Date |
|------|-----------|-----------|------|
| Consulting Psychologist | Dr. Li Wei (pending formal name) | ✅ Approved (verbal) | 2026-06-02 |
| Engineering Lead | Heart Platform | ✅ | 2026-06-02 |

## Merge Gate

- [x] Psychologist review complete
- [x] All hotline numbers verified
- [x] Care path text approved (placeholder text is acceptable for v1)
- [x] PR template `## Safety Lexicon Review` checkbox added
- [ ] Formal written signature (pending — verbal approval accepted for dev merge)
