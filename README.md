# ARGUS

**Autonomous Reasoning & Graph-based Understanding System**

ARGUS is an AI-powered security auditing agent that autonomously discovers vulnerabilities in AWS cloud infrastructure. Unlike traditional scanners that check static rules, ARGUS thinks — it forms security hypotheses, investigates them through a reasoning loop, and correlates findings across layers to surface composite attack chains that no single finding would reveal.

Built on LangGraph and Claude ARGUS self-discovers all in-scope resources, runs multi-step investigations via AWS APIs and SSH, builds attack graphs linking findings across IAM, network, compute, data, and monitoring layers, and generates a full security report with reasoning chains and remediation guidance.

**Tech Stack:** Terraform (IaC) · FastAPI (backend) · LangGraph (agent workflow) · Claude Sonnet + Opus (LLM) · Next.js (dashboard) · SSE (real-time streaming)
