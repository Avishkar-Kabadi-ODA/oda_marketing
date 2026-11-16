# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import os
import frappe
from oda_marketing.oda_marketing.file_security import resolve_site_file

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def resolve_disk_path(file_relative_path, doc=None):
	"""Resolves the absolute filesystem path for a Frappe file attachment."""
	if not file_relative_path:
		return None

	attached_to = ("Content Item", doc.name) if doc else None
	file_doc, abs_path = resolve_site_file(
		file_relative_path,
		max_bytes=MAX_ATTACHMENT_BYTES,
		attached_to=attached_to,
	)
	return abs_path if file_doc and abs_path and os.path.isfile(abs_path) else None


def has_markdown_attachment(doc):
	"""
	Checks if any of the document's attached files (content_file_1, content_file_2, content_file_3)
	is a valid Markdown file (.md or .markdown).
	"""
	attachment_fields = ["content_file_1", "content_file_2", "content_file_3"]
	for field in attachment_fields:
		val = getattr(doc, field, None)
		if val and str(val).strip():
			clean_path = str(val).strip().split("?")[0]
			if not clean_path.startswith(("/files/", "/private/files/")):
				continue
			ext = os.path.splitext(clean_path)[1].lower()
			if ext in MARKDOWN_EXTENSIONS:
				return True
	return False


def extract_file_content(file_relative_path, doc=None):
	"""
	Extracts readable plain text from a given Frappe file attachment path.
	Supports .md, .markdown, .txt, .html, .docx, .pdf files.
	Image attachments are noted as visual assets without bloating token consumption.
	"""
	if not file_relative_path:
		return ""

	clean_path = str(file_relative_path).strip().split("?")[0]
	ext = os.path.splitext(clean_path)[1].lower()
	abs_path = resolve_disk_path(file_relative_path, doc=doc)

	if ext in IMAGE_EXTENSIONS:
		return f"[Image Attachment: {os.path.basename(clean_path)}]"

	if not abs_path:
		return f"[Attachment: {os.path.basename(clean_path)} (file record unavailable)]"

	try:
		if ext == ".docx":
			import zipfile
			import xml.etree.ElementTree as ET
			try:
				with zipfile.ZipFile(abs_path) as z:
					xml_content = z.read("word/document.xml")
					tree = ET.fromstring(xml_content)
					paragraphs = []
					for p in tree.iter():
						if p.tag.endswith("}p"):
							p_text = "".join(t.text for t in p.iter() if t.tag.endswith("}t") and t.text)
							if p_text.strip():
								paragraphs.append(p_text.strip())
					if paragraphs:
						return "\n\n".join(paragraphs)
			except Exception as de:
				frappe.log_error(f"DOCX stdlib parsing fallback error: {str(de)}")

		elif ext == ".pdf":
			try:
				import pypdf
				reader = pypdf.PdfReader(abs_path)
				text_parts = [page.extract_text() for page in reader.pages if page.extract_text()]
				if text_parts:
					return "\n\n".join(text_parts)
			except Exception:
				pass

			# PDF Stream Regex Extraction Fallback
			import re
			try:
				with open(abs_path, "rb") as f:
					raw_pdf = f.read().decode("latin-1", errors="ignore")
					matches = re.findall(r'\((.*?)\)\s*Tj', raw_pdf)
					if matches:
						return " ".join(matches)
			except Exception:
				pass

		elif ext in [".pptx", ".odt", ".ods", ".odp"]:
			import zipfile
			import xml.etree.ElementTree as ET
			try:
				with zipfile.ZipFile(abs_path) as z:
					text_parts = []
					for fname in z.namelist():
						if fname.startswith("ppt/slides/slide") or fname == "content.xml":
							xml_data = z.read(fname)
							tree = ET.fromstring(xml_data)
							for elem in tree.iter():
								if elem.text and elem.text.strip():
									text_parts.append(elem.text.strip())
					if text_parts:
						return "\n".join(text_parts)
			except Exception:
				pass

		elif ext in [".html", ".htm", ".xhtml", ".xml"]:
			with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
				html_content = f.read()
				import re
				clean_text = re.sub(r'<[^>]+>', ' ', html_content)
				return clean_text.strip()

		# Universal Text & Markdown File Reader (.md, .markdown, .txt, .csv, .json, .log, .yaml, .rtf, etc.)
		with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
			content_str = f.read()
			if content_str and len(content_str.strip()) > 0:
				return content_str

	except Exception as e:
		frappe.log_error(f"Error extracting content from {file_relative_path}: {str(e)}")

	return f"[Attachment: {os.path.basename(file_relative_path)}]"


def get_combined_draft_text(doc):
	"""
	Extracts and combines text from all draft attachments and working notes for a Content Item document.
	"""
	parts = []

	# Include Notes & Working Draft Copy if present
	if doc.notes:
		import re
		clean_notes = re.sub(r'<[^>]+>', ' ', doc.notes)
		if clean_notes.strip():
			parts.append(f"=== WORKING NOTES / DRAFT COPY ===\n{clean_notes.strip()}")

	# Extract Primary Attachment (content_file_1)
	if doc.content_file_1:
		t1 = extract_file_content(doc.content_file_1, doc=doc)
		parts.append(f"=== PRIMARY DRAFT ATTACHMENT ({os.path.basename(doc.content_file_1)}) ===\n{t1}")

	# Extract Supporting File 1 (content_file_2)
	if doc.content_file_2:
		t2 = extract_file_content(doc.content_file_2, doc=doc)
		parts.append(f"=== SUPPORTING ATTACHMENT 1 ({os.path.basename(doc.content_file_2)}) ===\n{t2}")

	# Extract Supporting File 2 (content_file_3)
	if doc.content_file_3:
		t3 = extract_file_content(doc.content_file_3, doc=doc)
		parts.append(f"=== SUPPORTING ATTACHMENT 2 ({os.path.basename(doc.content_file_3)}) ===\n{t3}")

	return "\n\n".join(parts) if parts else "[No draft attachment text or notes found. Evaluation based on title and topic.]"
