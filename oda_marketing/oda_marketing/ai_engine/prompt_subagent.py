# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import time

import frappe
from pydantic_ai import Agent

from oda_marketing.oda_marketing.ai_engine.agent_factory import build_model, build_model_settings
from oda_marketing.oda_marketing.ai_engine.ai_log import log_llm_event
from oda_marketing.oda_marketing.ai_engine.key_manager import get_llm_config

STAGE = "prompt_generator"
SUBAGENT_SYSTEM_PROMPT = "You are a prompt generator subagent."
MAX_OUTPUT_TOKENS = 2048
MIN_PROMPT_CHARS = 50
OUTPUT_RETRIES = 1

SUBAGENT_META_PROMPT = """You are a constructive AI Copilot & Enterprise Marketing Auditor for Optimum Data Analytics (ODA).
Your task is to analyze deliverable metadata and create a practical, fair System Prompt for evaluating the document.

INPUT METADATA:
- Deliverable Title: {title}
- Content Type / Format: {content_type}
- Format Expectations: {format_description}
- Description / Brief: {topic}
- Industry Domain / Practice Area: {practice_area}
- Domain Context & Guidelines: {domain_description}
- Minimum Passing Threshold: {passing_score}%

INSTRUCTIONS FOR GENERATING THE SYSTEM PROMPT:
Construct a System Prompt instructing the Evaluator Agent to:
1. Praise strong structure, clear domain terminology, engaging enterprise tone, and alignment with "{topic}".
2. Evaluate technical relevance for Industry Domain "{practice_area}" ({domain_description}) and format expectations for "{content_type}" ({format_description}).
3. Score each criterion based on evidence in the draft; do not assume or target a particular score.
4. Apply the configured passing threshold without changing workflow state or treating the score as an approval.
5. Request revisions for any material factual, technical, structural, or brief-alignment gaps.

Return raw System Prompt text only.
"""


def _format_kwargs(title, content_type, topic, practice_area, format_description, domain_description, passing_score=80):
    format_text = format_description or "Standard deliverable format structure"
    domain_text = domain_description or "Enterprise domain best practices"
    return {
        "title": title,
        "content_type": content_type,
        "format": content_type,
        "topic": topic,
        "description": topic,
        "practice_area": practice_area,
        "industry_domain": practice_area,
        "format_description": format_text,
        "domain_description": domain_text,
        "practice_area_description": domain_text,
        "option_description": format_text,
        "passing_score": passing_score,
    }


def build_meta_prompt(meta_template, format_kwargs, reviewer_instructions=None):
    """Fill the meta template (falls back to the built-in one if the custom one is invalid)."""
    format_kwargs = {**format_kwargs, "passing_score": format_kwargs.get("passing_score", 80)}
    try:
        meta_prompt = (meta_template or SUBAGENT_META_PROMPT).format(**format_kwargs)
    except Exception:
        meta_prompt = SUBAGENT_META_PROMPT.format(**format_kwargs)

    if reviewer_instructions and reviewer_instructions.strip():
        meta_prompt += f"\n\nADDITIONAL REVIEWER INSTRUCTIONS:\n{reviewer_instructions.strip()}"
    return meta_prompt


def generate_dynamic_system_prompt(doc, reviewer_instructions=None):
    """
    Subagent execution: analyzes Content Item metadata, Format descriptions, and Domain descriptions,
    and returns a dynamic, custom System Prompt for evaluation.
    Uses customizable subagent_meta_prompt from Marketing Settings if configured.
    Any LLM or configuration failure falls back to build_fallback_dynamic_prompt, which only
    builds a prompt and never produces a score.
    """
    title = getattr(doc, "title", "Untitled Marketing Deliverable")
    content_type = getattr(doc, "content_type", "Blog")
    topic = getattr(doc, "description", None) or getattr(doc, "topic", "General Enterprise Analytics")
    practice_area = getattr(doc, "industry_domain", None) or getattr(doc, "practice_area", "Cross-domain")

    format_description = ""
    if content_type and frappe.db.exists("Content Item Option", content_type):
        format_description = (
            frappe.db.get_value("Content Item Option", content_type, "option_description") or ""
        )

    domain_description = ""
    if practice_area and frappe.db.exists("Content Item Option", practice_area):
        domain_description = (
            frappe.db.get_value("Content Item Option", practice_area, "option_description") or ""
        )

    settings = frappe.get_single("Marketing Settings")
    passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)
    format_kwargs = _format_kwargs(
        title, content_type, topic, practice_area, format_description, domain_description, passing_score
    )
    meta_template = getattr(settings, "subagent_meta_prompt", None)
    if not (meta_template and meta_template.strip()):
        meta_template = SUBAGENT_META_PROMPT

    meta_prompt = build_meta_prompt(meta_template, format_kwargs, reviewer_instructions)

    llm_cfg = get_llm_config()
    provider = llm_cfg.get("provider")
    model_name = llm_cfg.get("model")
    started = time.monotonic()

    try:
        agent = Agent(
            build_model(llm_cfg),
            instructions=SUBAGENT_SYSTEM_PROMPT,
            model_settings=build_model_settings(temperature=0.3, max_tokens=MAX_OUTPUT_TOKENS),
            retries=OUTPUT_RETRIES,
        )
        generated = (agent.run_sync(meta_prompt).output or "").strip()
        if len(generated) < MIN_PROMPT_CHARS:
            raise ValueError("generated prompt is empty or too short")
        log_llm_event(
            STAGE, provider, model_name, doc.name, "ok",
            duration_ms=(time.monotonic() - started) * 1000,
        )
        return generated
    except Exception as exc:
        log_llm_event(
            STAGE, provider, model_name, doc.name, "fallback",
            duration_ms=(time.monotonic() - started) * 1000, error=exc,
        )

    return build_fallback_dynamic_prompt(
        title, content_type, topic, practice_area, format_description, domain_description,
        reviewer_instructions=reviewer_instructions, passing_score=passing_score,
    )


def build_fallback_dynamic_prompt(
    title,
    content_type,
    topic,
    practice_area,
    format_description="",
    domain_description="",
    reviewer_instructions=None,
    passing_score=None,
):
    """
    Generates a dynamic system prompt using Marketing Settings evaluator_default_prompt if configured.
    Optionally appends reviewer-specific instructions.
    """
    settings = frappe.get_single("Marketing Settings")
    passing_score = passing_score or int(getattr(settings, "ai_copilot_passing_score", 80) or 80)
    tmpl = getattr(settings, "evaluator_default_prompt", None)
    format_kwargs = _format_kwargs(
        title, content_type, topic, practice_area, format_description, domain_description, passing_score
    )

    if tmpl and tmpl.strip():
        try:
            base_prompt = tmpl.format(**format_kwargs)
            reviewer_section = ""
            if reviewer_instructions and reviewer_instructions.strip():
                reviewer_section = f"\n\nADDITIONAL REVIEWER INSTRUCTIONS:\n{reviewer_instructions.strip()}"
            return base_prompt + reviewer_section + """

You must respond in valid JSON with:
{
  "overall_score": <number 0-100>,
  "technical_accuracy_score": <number 0-100>,
  "clarity_score": <number 0-100>,
  "structure_score": <number 0-100>,
  "verdict": "<PASS or REJECT>",
  "key_strengths": ["list of strengths"],
  "critical_flaws": ["list of issues"],
  "actionable_feedback": "Detailed formatted markdown advice for the Content Writer on how to improve this deliverable."
}
"""
        except Exception:
            pass

    domain_info = f"{practice_area} ({domain_description})" if domain_description else practice_area
    format_info = f"{content_type} ({format_description})" if format_description else content_type

    return f"""You are an encouraging AI Copilot & Technical Reviewer for Optimum Data Analytics (ODA).
You are evaluating the {format_info} titled "{title}" in the domain of {domain_info}.

EVALUATION GUIDELINES FOR THIS DELIVERABLE:
1. Praise strong structure, clear domain terminology ({practice_area}), and alignment with "{topic}".
2. Evaluate technical depth for {domain_info} and layout compliance for {format_info}.
3. Score each criterion based on evidence in the draft; do not assume or target a particular score.
4. Passing threshold is {passing_score}%. The score is informational and must not approve or route the item.

You must respond in valid JSON with:
{{
  "overall_score": <number 0-100>,
  "technical_accuracy_score": <number 0-100>,
  "clarity_score": <number 0-100>,
  "structure_score": <number 0-100>,
  "verdict": "<PASS or REJECT>",
  "key_strengths": ["list of key strengths"],
  "critical_flaws": ["list of revision items if any"],
  "actionable_feedback": "Constructive, supportive feedback report for the Content Writer."
}}
"""