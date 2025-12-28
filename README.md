# Intelligent Framework for ERP Systems

This repository contains the project deliverables for an "Intelligent framework for ERP Systems" thesis. The solution combines an Odoo Community Edition ERP stack with automation (n8n), AI-assisted operations via MCP, and a Streamlit front-end (ERPGenie) for natural-language interaction and data visualization.

Highlights
- Modular ERP stack split across VMs: Odoo app, PostgreSQL DB, automation/AI layer.
- n8n workflows for AI chatbot routing, DB chat, health checks, and CRM lead capture automation.
- Streamlit UI (ERPGenie) that talks to n8n webhooks and adds charts/tables.

Repo layout
- `streamlit-app/` Streamlit UI (`app.py`) and theme config.
- `n8n-workflows/` Exported n8n workflow JSON files.
- `docs/thesis/` Thesis documents (DOCX and TXT).

Prerequisites
- Python 3.10+ for the Streamlit UI.
- n8n (Docker or local install).
- Odoo Community Edition and PostgreSQL (not included).
- MCP server for controlled ERP/DB access (not included).

Quick start (Streamlit UI)
1. `pip install -r requirements.txt`
2. Edit `streamlit-app/app.py` and set `WEBHOOK_URL` to your n8n webhook.
3. Run `streamlit run streamlit-app/app.py`

Using the n8n workflows
1. Import workflows from `n8n-workflows/*.json` into n8n.
2. Configure credentials for OpenAI/Anthropic, Postgres, IMAP/SMTP as needed.
3. Update URLs in the workflow nodes for your local IPs/ports (Odoo health, MCP endpoint, etc.).

Notes
- Workflow exports include credential references by ID; replace them with your own in n8n.
- Cloudflare Tunnel and VM configuration are documented in the thesis, not included in this repo.

License
- No license specified yet. Add one if you plan to distribute or reuse this code.
