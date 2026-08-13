# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import json
import urllib.request
import urllib.error
import frappe
from oda_marketing.oda_marketing.ai_engine.key_manager import get_llm_config


SUBAGENT_META_PROMPT = """You are a constructive AI Copilot & Enterprise Marketing Auditor for Optimum Data Analytics (ODA).
Your task is to analyze deliverable metadata and create a practical, fair System Prompt for evaluating the document.

INPUT METADATA:
- Deliverable Title: {title}
- Content Type: {content_type} (Blog, Poll, Flowchart, Carousel)
- Topic / Brief: {topic}
- Practice Area / Domain: {practice_area}
- Minimum Passing Threshold: 80%

INSTRUCTIONS FOR GENERATING THE SYSTEM PROMPT:
Construct a System Prompt instructing the Evaluator Agent to:
1. Praise strong structure, clear domain terminology, engaging enterprise tone, and alignment with "{topic}".
2. Evaluate technical relevance for {practice_area} and structure for {content_type}.
3. Award high passing scores (85%–98%) for complete, well-written enterprise deliverables.
4. Only request revisions if content is missing, blank, or severely incomplete.

Return raw System Prompt text only.
"""


def generate_dynamic_system_prompt(doc, reviewer_instructions=None):
	"""
	Subagent execution: Analyzes Content Item metadata and returns a dynamic, custom System Prompt for evaluation.
	Uses customizable subagent_meta_prompt from Marketing Settings if configured.
	Optionally incorporates reviewer-specific instructions when triggered by a Reviewer.
	"""
	title = getattr(doc, "title", "Untitled Marketing Deliverable")
	content_type = getattr(doc, "content_type", "Blog")
	topic = getattr(doc, "topic", "General Enterprise Analytics")
	practice_area = getattr(doc, "practice_area", "Cross-domain")

	settings = frappe.get_single("Marketing Settings")
	meta_template = getattr(settings, "subagent_meta_prompt", None)
	if not (meta_template and meta_template.strip()):
		meta_template = SUBAGENT_META_PROMPT

	llm_cfg = get_llm_config()
	provider = llm_cfg.get("provider")

	try:
		meta_prompt = meta_template.format(
			title=title,
			content_type=content_type,
			topic=topic,
			practice_area=practice_area
		)
	except Exception:
		meta_prompt = SUBAGENT_META_PROMPT.format(
			title=title,
			content_type=content_type,
			topic=topic,
			practice_area=practice_area
		)

	# Append reviewer instructions to meta prompt if provided
	if reviewer_instructions and reviewer_instructions.strip():
		meta_prompt += f"\n\nADDITIONAL REVIEWER INSTRUCTIONS:\n{reviewer_instructions.strip()}"

	# If no live API key is configured or mock provider, return structured dynamic template fallback
	if provider == "Mock Agent" or not llm_cfg.get("api_key") or llm_cfg.get("api_key") == "mock-key":
		return build_fallback_dynamic_prompt(title, content_type, topic, practice_area, reviewer_instructions=reviewer_instructions)

	try:
		if provider in ["APIM Gateway", "OpenAI"]:
			url = f"{llm_cfg['endpoint'].rstrip('/')}/chat/completions"
			headers = {
				"Content-Type": "application/json",
				"api-key": llm_cfg["api_key"]
			} if provider == "APIM Gateway" else {
				"Content-Type": "application/json",
				"Authorization": f"Bearer {llm_cfg['api_key']}"
			}

			payload = {
				"model": llm_cfg["model"],
				"messages": [
					{"role": "system", "content": "You are a prompt generator subagent."},
					{"role": "user", "content": meta_prompt}
				],
				"temperature": 0.3
			}

			req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
			with urllib.request.urlopen(req, timeout=30) as resp:
				res_data = json.loads(resp.read().decode("utf-8"))
				generated_prompt = res_data["choices"][0]["message"]["content"].strip()
				return generated_prompt

		elif provider == "Google Gemini":
			url = f"{llm_cfg['endpoint']}/models/{llm_cfg['model']}:generateContent?key={llm_cfg['api_key']}"
			headers = {"Content-Type": "application/json"}
			payload = {
				"contents": [{"parts": [{"text": meta_prompt}]}]
			}
			req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
			with urllib.request.urlopen(req, timeout=30) as resp:
				res_data = json.loads(resp.read().decode("utf-8"))
				generated_prompt = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
				return generated_prompt

	except Exception as e:
		frappe.log_error(f"Subagent prompt generation API call failed: {str(e)}")

	# Fallback to local prompt builder
	return build_fallback_dynamic_prompt(title, content_type, topic, practice_area, reviewer_instructions=reviewer_instructions)


def build_fallback_dynamic_prompt(title, content_type, topic, practice_area, reviewer_instructions=None):
	"""
	Generates a dynamic system prompt using Marketing Settings evaluator_default_prompt if configured.
	Optionally appends reviewer-specific instructions.
	"""
	settings = frappe.get_single("Marketing Settings")
	tmpl = getattr(settings, "evaluator_default_prompt", None)
	if tmpl and tmpl.strip():
		try:
			base_prompt = tmpl.format(
				title=title,
				content_type=content_type,
				topic=topic,
				practice_area=practice_area
			)
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

	return f"""You are an encouraging AI Copilot & Technical Reviewer for Optimum Data Analytics (ODA).
You are evaluating the {content_type} titled "{title}" in the domain of {practice_area}.

EVALUATION GUIDELINES FOR THIS DELIVERABLE:
1. Praise strong structure, clear domain terminology ({practice_area}), and alignment with "{topic}".
2. Award high passing scores (85%–98%) for complete, well-written, publishable enterprise content.
3. Passing threshold is 80%.

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
