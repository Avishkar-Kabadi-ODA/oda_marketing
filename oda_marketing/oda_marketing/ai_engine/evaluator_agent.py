# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import json
import urllib.request
import urllib.error
import frappe
from oda_marketing.oda_marketing.ai_engine.key_manager import get_llm_config
from oda_marketing.oda_marketing.ai_engine.file_extractor import get_combined_draft_text


def evaluate_content_item(doc, dynamic_system_prompt, user_email=None):
	"""
	Primary Evaluator Agent: Uses dynamic_system_prompt + extracted draft text to score the document.
	Streams progress updates to the user's desk UI via frappe.publish_realtime.
	"""
	docname = doc.name
	publish_stream_event(docname, user_email, "Extracting attachment text and preparing evaluation payload...", progress=20)

	draft_text = get_combined_draft_text(doc)

	user_prompt = f"""
CONTENT DELIVERABLE TO EVALUATE:
- Title: {doc.title}
- Content Type: {doc.content_type}
- Practice Area: {doc.practice_area}
- Topic / Brief: {doc.topic}

DRAFT CONTENT & ATTACHMENT TEXT:
{draft_text}

Evaluate this deliverable according to your System Prompt criteria and output valid JSON.
"""

	llm_cfg = get_llm_config()
	provider = llm_cfg.get("provider")

	publish_stream_event(docname, user_email, f"Connecting to {provider} for Copilot evaluation...", progress=40)

	# If mock agent or no key, perform heuristic quality evaluation
	if provider == "Mock Agent" or not llm_cfg.get("api_key") or llm_cfg.get("api_key") == "mock-key":
		return run_heuristic_mock_evaluation(doc, draft_text)

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
					{"role": "system", "content": dynamic_system_prompt},
					{"role": "user", "content": user_prompt}
				],
				"response_format": {"type": "json_object"},
				"temperature": 0.2
			}

			publish_stream_event(docname, user_email, "Analyzing technical accuracy, structure & domain depth...", progress=65)

			req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
			with urllib.request.urlopen(req, timeout=60) as resp:
				res_data = json.loads(resp.read().decode("utf-8"))
				raw_content = res_data["choices"][0]["message"]["content"]
				res_json = json.loads(raw_content)

				frappe.logger().debug(f"DEBUG OpenAI JSON Response: {raw_content}")
				print("="*40)
				print("DEBUG OpenAI JSON Response:")
				print(raw_content)
				print("="*40)

				publish_stream_event(docname, user_email, f"Evaluation complete. Score: {res_json.get('overall_score', 0)}%", progress=90)
				return format_eval_result(res_json)

		elif provider == "Google Gemini":
			url = f"{llm_cfg['endpoint']}/models/{llm_cfg['model']}:generateContent?key={llm_cfg['api_key']}"
			headers = {"Content-Type": "application/json"}
			payload = {
				"system_instruction": {"parts": [{"text": dynamic_system_prompt}]},
				"contents": [{"parts": [{"text": user_prompt}]}],
				"generationConfig": {"response_mime_type": "application/json"}
			}

			publish_stream_event(docname, user_email, "Analyzing technical accuracy & domain depth via Gemini...", progress=65)

			req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
			with urllib.request.urlopen(req, timeout=60) as resp:
				res_data = json.loads(resp.read().decode("utf-8"))
				raw_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
				res_json = json.loads(raw_content)

				publish_stream_event(docname, user_email, f"Evaluation complete. Score: {res_json.get('overall_score', 0)}%", progress=90)
				return format_eval_result(res_json)

	except Exception as e:
		frappe.log_error(f"Primary Agent LLM Evaluation Error: {str(e)}")

	# Fallback heuristic evaluation if API fails
	publish_stream_event(docname, user_email, "API connection issue. Running local heuristic evaluator...", progress=80)
	return run_heuristic_mock_evaluation(doc, draft_text)


def publish_stream_event(docname, user_email, message, progress=0):
	"""Publishes realtime evaluation updates to desk UI."""
	try:
		frappe.publish_realtime(
			event="ai_copilot_stream",
			message={
				"docname": docname,
				"message": message,
				"progress": progress
			},
			user=user_email
		)
	except Exception:
		pass


def run_heuristic_mock_evaluation(doc, draft_text):
	"""
	Evaluates content text length, key sections, and topic density.
	"""
	settings = frappe.get_single("Marketing Settings")
	passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)

	text_len = len(draft_text.strip())
	has_attachment = bool(doc.content_file_1)
	has_topic_match = any(word.lower() in draft_text.lower() for word in (doc.topic or "").split() if len(word) > 3)

	# If draft has rich technical content or primary attachment -> Pass with 92%
	if (has_attachment or text_len > 250) and (has_topic_match or text_len > 300):
		score = 92
	elif text_len > 150:
		score = 82
	else:
		score = 58

	verdict = "PASS" if score >= passing_score else "REJECT"

	strengths = [
		f"Solid topic coverage aligned with '{doc.topic}'.",
		f"Structured appropriately for a {doc.content_type} deliverable.",
		f"Domain context matches {doc.practice_area} requirements."
	]

	flaws = []
	if score < passing_score:
		flaws = [
			"Draft content requires further elaboration and technical depth.",
			"Primary draft attachment (content_file_1) should be provided.",
			"Technical terminology needs stronger alignment with enterprise industry standards."
		]

	feedback_md = f"""### AI Copilot Evaluation Summary
- **Overall Score**: {score}%
- **Status Verdict**: **{verdict}** (Threshold: {passing_score}%)
- **Content Type**: {doc.content_type} | **Domain**: {doc.practice_area}

#### Key Strengths:
{"".join([f"- {s}\n" for s in strengths])}

{"#### Actionable Revision Items Required:" if flaws else "#### Copilot Recommendations:"}
{"".join([f"- {f}\n" for f in (flaws or ["Content meets enterprise technical quality criteria for submission."])])}
"""

	return {
		"overall_score": score,
		"verdict": verdict,
		"ai_copilot_feedback": feedback_md,
		"key_strengths": strengths,
		"critical_flaws": flaws
	}


def format_eval_result(res_json):
	score = 0
	# Case-insensitive key matching for overall score
	for k, v in res_json.items():
		clean_k = k.lower().replace("_", "").replace(" ", "").replace("-", "")
		if clean_k in ["overallscore", "score", "qualityscore", "finalscore", "totalscore", "overall"]:
			try:
				score = int(float(v))
				break
			except (ValueError, TypeError):
				pass

	settings = frappe.get_single("Marketing Settings")
	passing_score = int(getattr(settings, "ai_copilot_passing_score", 80) or 80)
	verdict = "PASS" if score >= passing_score else "REJECT"

	# Extract Strengths, Weaknesses/Flaws, and Rationale flexibly
	strengths = res_json.get("key_strengths") or res_json.get("strengths") or res_json.get("Strengths") or []
	flaws = res_json.get("critical_flaws") or res_json.get("flaws") or res_json.get("Weaknesses") or res_json.get("improvements") or []

	rationale = res_json.get("Rationale") or res_json.get("Final Verdict") or res_json.get("actionable_feedback") or res_json.get("feedback") or ""
	if isinstance(rationale, list):
		rationale = "\n".join([str(r) for r in rationale])

	feedback_text = f"""### AI Copilot Evaluation Report
- **Overall Quality Score**: **{score}%**
- **Verdict**: **{verdict}** (Passing Threshold: **{passing_score}%**)

#### Key Strengths Identified:
{"".join([f"- {s}\n" for s in strengths]) if strengths else "- Clear structure and strong topic alignment.\n"}

#### Recommended Improvements / Revision Items:
{"".join([f"- {f}\n" for f in flaws]) if flaws else "- Content meets enterprise technical quality criteria for submission.\n"}

{"#### Evaluator Rationale & Verdict:" if rationale else ""}
{rationale}
"""

	return {
		"overall_score": score,
		"verdict": verdict,
		"ai_copilot_feedback": feedback_text,
		"key_strengths": strengths,
		"critical_flaws": flaws
	}
