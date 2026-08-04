# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.utils.password import get_decrypted_password


def get_secret(var_name, default=None):
	"""
	Retrieves an environment variable or secret key safely.
	First checks 'Env Variable' DocType with Password field decryption.
	Fallback to system os.environ.
	"""
	if frappe.db.exists("Env Variable", var_name):
		try:
			val = get_decrypted_password("Env Variable", var_name, fieldname="value")
			if val:
				return val
		except Exception:
			pass
		# Fallback to direct field value if not encrypted as password
		val = frappe.db.get_value("Env Variable", var_name, "value")
		if val:
			return val

	return os.environ.get(var_name, default)


def get_llm_config():
	"""
	Detects configured LLM provider and credentials.
	Checks Marketing Settings user-selected Env Variable links first,
	then falls back to standard names (APIM Gateway, OpenAI, Gemini, Anthropic).
	"""
	try:
		settings = frappe.get_single("Marketing Settings")
		provider = getattr(settings, "ai_provider", None) or "APIM Gateway"

		key_var_name = getattr(settings, "ai_api_key_var", None)
		api_key = get_secret(key_var_name) if key_var_name else None

		endpoint_var_name = getattr(settings, "ai_endpoint_var", None)
		endpoint = get_secret(endpoint_var_name) if endpoint_var_name else None

		model_name = getattr(settings, "ai_model_name", None) or "gpt-4o"

		if api_key:
			return {
				"provider": provider,
				"endpoint": endpoint or "https://api.openai.com/v1",
				"api_key": api_key,
				"model": model_name
			}
	except Exception:
		pass

	# Fallback to standard convention names if Marketing Settings fields are not configured
	apim_url = get_secret("APIM_GATEWAY_URL")
	apim_key = get_secret("APIM_SUBSCRIPTION_KEY") or get_secret("APIM_API_KEY")

	if apim_url and apim_key:
		return {
			"provider": "APIM Gateway",
			"endpoint": apim_url,
			"api_key": apim_key,
			"model": get_secret("APIM_MODEL_NAME", "gpt-4o")
		}

	openai_key = get_secret("OPENAI_API_KEY")
	if openai_key:
		return {
			"provider": "OpenAI",
			"endpoint": get_secret("OPENAI_BASE_URL", "https://api.openai.com/v1"),
			"api_key": openai_key,
			"model": get_secret("OPENAI_MODEL_NAME", "gpt-4o")
		}

	gemini_key = get_secret("GEMINI_API_KEY")
	if gemini_key:
		return {
			"provider": "Google Gemini",
			"endpoint": "https://generativelanguage.googleapis.com/v1beta",
			"api_key": gemini_key,
			"model": get_secret("GEMINI_MODEL_NAME", "gemini-1.5-pro")
		}

	claude_key = get_secret("ANTHROPIC_API_KEY")
	if claude_key:
		return {
			"provider": "Anthropic",
			"endpoint": "https://api.anthropic.com/v1",
			"api_key": claude_key,
			"model": get_secret("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20240620")
		}

	# Return mock/fallback config for test environment
	return {
		"provider": "Mock Agent",
		"endpoint": "local",
		"api_key": "mock-key",
		"model": "mock-v1"
	}
