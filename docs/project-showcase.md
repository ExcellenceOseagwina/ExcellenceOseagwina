# Featured Project Showcase

This document provides a technical overview of selected repositories linked from the GitHub profile. It describes the systems at a portfolio level; it is not a substitute for reviewing each implementation or independently testing its deployment.

## 1. Wellspring University Inventory System

**Role:** Final-year project  
**Repository:** [wellspring-inventory](https://github.com/ExcellenceOseagwina/wellspring-inventory)  
**Live application:** [wellspring-inventory.vercel.app](https://wellspring-inventory.vercel.app)

### Problem and purpose

A web application for digitising departmental equipment records. It supports inventory management, equipment-condition tracking, media uploads, activity history, dashboard summaries, and printable reports.

### Architecture and stack

- **Frontend:** HTML, CSS, vanilla JavaScript
- **Application/API:** Node.js and Express
- **Identity:** Supabase Auth
- **Persistence:** Supabase Postgres
- **Media:** Supabase Storage and Multer-based upload handling
- **Deployment:** Vercel

### Engineering topics demonstrated

- Authentication and protected API routes
- REST API design and frontend/backend separation
- Relational data modelling and SQL migrations
- File-upload workflows and object storage
- Activity history, dashboard aggregation, and report generation
- Environment-based configuration and deployment

### Security review points

For a production deployment, verify server-side authorization on every record operation, ownership and department-level access rules, Supabase Row Level Security policies, upload size/type/content validation, safe file naming, and secret handling. A frontend route guard is not an authorization boundary. Never expose a Supabase service-role key in browser code.

### Further improvements

- Document the role/permission matrix and enforce it server-side.
- Add integration tests for authorization and inventory CRUD operations.
- Add upload limits, content inspection, and explicit storage policies.
- Add database backup/restore guidance and operational monitoring.

---

## 2. WellBot — Wellspring University Student Assistant

**Repository:** [WellBot](https://github.com/ExcellenceOseagwina/WellBot)  
**Live application:** [wellbot-seven.vercel.app](https://wellbot-seven.vercel.app)

### Problem and purpose

A student-support web application that answers university-related questions using a curated knowledge base and an NLP-style question-matching engine. It includes student authentication, email verification, password recovery, and conversation history.

### Architecture and stack

- **Frontend:** HTML, CSS, vanilla JavaScript
- **Application/API:** Node.js and Express
- **Data:** Supabase-backed persistence
- **Identity/session:** JWT-related token utilities and email verification flows
- **Knowledge source:** JSON university knowledge base
- **Email:** SMTP-based delivery for verification and recovery flows

### Engineering topics demonstrated

- Authentication and account lifecycle flows
- Knowledge-base-driven conversational matching
- Conversation persistence
- Email integration and password recovery
- Separation of frontend, API, chatbot engine, and data

### Security and reliability review points

Treat user messages as untrusted input. Verify JWT signatures, issuer/audience where applicable, expiration, and token revocation strategy. Rate-limit authentication and chatbot endpoints, protect password-reset tokens, avoid logging credentials or sensitive conversation content, and ensure users can only access their own conversation history. Keep university answers tied to verified source material and provide a fallback when the knowledge base cannot answer confidently.

### Further improvements

- Add evaluation examples for matching accuracy, false matches, and fallback behavior.
- Track knowledge-base provenance and last-reviewed dates.
- Add per-user authorization tests for conversation history.
- Add abuse controls, request limits, and privacy/retention documentation.

---

## 3. SmartFarm — Fuzzy-Logic Farm Monitoring

**Repository:** [smart-farm](https://github.com/ExcellenceOseagwina/smart-farm)  
**Live application:** [smart-farm-six-rho.vercel.app](https://smart-farm-six-rho.vercel.app)  
**Attribution:** Forked repository. The repository's fork status should remain visible when presenting this work.

### Problem and purpose

A farm-monitoring decision-support application. Users record soil-moisture, temperature, and humidity readings; a fuzzy-logic engine classifies conditions and returns a human-readable status and recommendation. Readings are stored for later review.

### Architecture and stack

- **Frontend:** HTML, CSS, vanilla JavaScript
- **Application/API:** Node.js and Express 5
- **Identity and persistence:** Supabase Auth and Postgres
- **Decision logic:** Fuzzy-logic classification and recommendation rules
- **Hosting:** Node-compatible hosting

### Engineering topics demonstrated

- Translating continuous sensor-like measurements into fuzzy categories
- Rule-based decision support
- Authenticated data persistence
- Historical monitoring and dashboard presentation

### Security and data-integrity review points

The server must derive the authenticated user identity from a verified session rather than trusting a client-supplied `userId`. Enforce row ownership with Row Level Security and server-side authorization. Validate numeric ranges, reject non-finite values, and document units and sensor assumptions. Recommendations should be presented as decision support, not as guaranteed agronomic advice.

### Further improvements

- Add tests for membership boundaries, rule combinations, and invalid inputs.
- Document the membership functions and rule base with examples.
- Add data provenance, units, and sensor calibration notes.
- Preserve clear attribution to the upstream project and distinguish personal modifications.

---

## 4. CSC-423 — Machine Learning Coursework

**Repository:** [CSC-423](https://github.com/ExcellenceOseagwina/CSC-423)  
**Coursework site:** [csc-423.vercel.app](https://csc-423.vercel.app)

### Scope

A coursework collection covering supervised and unsupervised learning, including house-price regression, fraud/anomaly exploration with Gaussian Mixture Models, K-Means clustering, customer segmentation, PCA, digit analysis, visualisation, and model evaluation.

### Technologies

Python, Jupyter Notebook, NumPy, pandas, Matplotlib, and scikit-learn.

### Engineering and analytical topics demonstrated

- Data exploration and preprocessing
- Regression and clustering workflows
- Dimensionality reduction
- Model evaluation and visualisation
- Communicating experiments in reproducible notebooks

### Further improvements

- Provide a dependency file and dataset acquisition instructions.
- Record random seeds, evaluation metrics, and train/test methodology.
- Separate exploratory notebooks from reusable application code.
- Document dataset sources, licensing, and any limitations of fraud/anomaly labels.

---

## Evidence to add before calling these production-ready

For each project, add genuine screenshots or a short demo, a clear local setup guide, a deployment status note, and tests that can be run by another developer. Do not publish screenshots containing real user data, credentials, private URLs, or personal information.

The live links above are included as project destinations, not as a claim that uptime, security, or current functionality has been independently verified.
