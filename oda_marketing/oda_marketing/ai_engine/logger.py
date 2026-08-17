# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import sys
import json
import frappe


def log_raw_llm_request(stage_name, provider, url, headers, payload, docname=None):
	"""Prints full raw HTTP request payload and metadata to terminal stdout."""
	border = "=" * 80
	print(f"\n{border}", flush=True)
	print(f"🚀 [RAW LLM HTTP REQUEST] {stage_name.upper()}", flush=True)
	print(f"📄 Deliverable: {docname or 'N/A'} | Provider: {provider}", flush=True)
	print(f"🌐 Target URL: {url}", flush=True)
	print(f"{'-' * 80}", flush=True)
	print("📋 [HTTP HEADERS]:", flush=True)
	safe_headers = {}
	for k, v in (headers or {}).items():
		if k.lower() in ["authorization", "api-key", "x-api-key"] and len(str(v)) > 8:
			safe_headers[k] = f"{str(v)[:6]}...{str(v)[-4:]}"
		else:
			safe_headers[k] = v
	print(json.dumps(safe_headers, indent=2), flush=True)

	print(f"{'-' * 80}", flush=True)
	print("📦 [RAW REQUEST BODY / JSON PAYLOAD]:", flush=True)
	if isinstance(payload, (dict, list)):
		print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
	elif isinstance(payload, str):
		try:
			parsed = json.loads(payload)
			print(json.dumps(parsed, indent=2, ensure_ascii=False), flush=True)
		except Exception:
			print(payload, flush=True)
	else:
		print(str(payload), flush=True)
	print(f"{border}\n", flush=True)
	sys.stdout.flush()


def log_raw_llm_response(stage_name, provider, status_code, raw_response_text, parsed_json=None, docname=None):
	"""Prints full raw HTTP response body to terminal stdout."""
	border = "=" * 80
	print(f"\n{border}", flush=True)
	print(f"📥 [RAW LLM HTTP RESPONSE] {stage_name.upper()} | Status: {status_code}", flush=True)
	print(f"📄 Deliverable: {docname or 'N/A'} | Provider: {provider}", flush=True)
	print(f"{'-' * 80}", flush=True)
	print("📦 [RAW RESPONSE BODY]:", flush=True)
	if parsed_json is not None:
		print(json.dumps(parsed_json, indent=2, ensure_ascii=False), flush=True)
	elif raw_response_text:
		try:
			parsed = json.loads(raw_response_text)
			print(json.dumps(parsed, indent=2, ensure_ascii=False), flush=True)
		except Exception:
			print(str(raw_response_text), flush=True)
	else:
		print("<Empty Response>", flush=True)
	print(f"{border}\n", flush=True)
	sys.stdout.flush()


def log_raw_llm_error(stage_name, provider, url, error_obj, docname=None):
	"""Prints raw HTTP error details and body from the LLM provider to terminal stdout."""
	border = "=" * 80
	print(f"\n{border}", flush=True)
	print(f"❌ [RAW LLM HTTP ERROR] {stage_name.upper()}", flush=True)
	print(f"📄 Deliverable: {docname or 'N/A'} | Provider: {provider}", flush=True)
	print(f"🌐 Target URL: {url}", flush=True)
	print(f"{'-' * 80}", flush=True)

	error_body = ""
	status_code = "N/A"
	if hasattr(error_obj, "code"):
		status_code = error_obj.code
	if hasattr(error_obj, "read"):
		try:
			error_body = error_obj.read().decode("utf-8")
		except Exception:
			pass

	print(f"Status Code: {status_code}", flush=True)
	print(f"Error Message: {str(error_obj)}", flush=True)
	if error_body:
		print(f"{'-' * 80}", flush=True)
		print("📦 [RAW ERROR RESPONSE BODY FROM PROVIDER]:", flush=True)
		try:
			parsed = json.loads(error_body)
			print(json.dumps(parsed, indent=2, ensure_ascii=False), flush=True)
		except Exception:
			print(error_body, flush=True)

	print(f"{border}\n", flush=True)
	sys.stdout.flush()
