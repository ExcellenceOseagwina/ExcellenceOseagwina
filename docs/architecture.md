# Project Architecture

These diagrams are high-level logical views based on each project's documented components. They are not generated from runtime traces and should be updated when implementation details change.

## Wellspring Inventory System

```mermaid
flowchart TD
    U[Authenticated user] --> UI[Browser frontend]
    UI --> API[Express API]
    UI --> AUTH[Supabase Auth]
    API --> MW[Authentication middleware]
    MW --> CTRL[Inventory controllers]
    CTRL --> DB[(Supabase Postgres)]
    CTRL --> STORE[Supabase Storage]
    CTRL --> ACT[Activity history]
    DB --> DASH[Dashboard and reports]
    STORE --> MEDIA[Media gallery]
```

**Trust boundaries:** the browser is untrusted; API authorization must be enforced server-side. Storage policies and database policies must independently protect user and departmental data. Service-role credentials must remain server-side.

## WellBot

```mermaid
flowchart TD
    STUDENT[Student] --> WEB[Browser application]
    WEB --> API[Express API]
    WEB --> AUTH[Authentication and verification]
    API --> TOKEN[Token verification]
    TOKEN --> ROUTES[Protected API routes]
    ROUTES --> ENGINE[Chatbot question matcher]
    ENGINE --> KB[(University knowledge base)]
    ROUTES --> DB[(Supabase persistence)]
    API --> EMAIL[SMTP email service]
```

**Trust boundaries:** authenticate and authorize each request; do not trust student identifiers supplied in request bodies. Conversation history must be scoped to the authenticated student. Knowledge-base answers should be reviewed against authoritative university information.

## SmartFarm

```mermaid
flowchart TD
    FARMER[Farmer] --> WEB[Browser dashboard]
    WEB --> AUTH[Supabase Auth]
    WEB --> API[Express API]
    API --> VERIFY[Verify authenticated identity]
    VERIFY --> VALIDATE[Validate readings and units]
    VALIDATE --> FUZZY[Fuzzy-logic engine]
    FUZZY --> RESULT[Status and recommendation]
    VERIFY --> DB[(Supabase Postgres)]
    RESULT --> DB
    DB --> HISTORY[User monitoring history]
```

**Trust boundaries:** derive user identity from a verified token, validate every measurement server-side, and enforce row ownership in database policies. Do not treat client-provided `userId` values as proof of identity.

## CSC-423 coursework

```mermaid
flowchart TD
    DATA[Dataset] --> PREP[Exploration and preprocessing]
    PREP --> SPLIT[Train/test or evaluation strategy]
    SPLIT --> MODEL[Regression, clustering, GMM, PCA]
    MODEL --> EVAL[Metrics and diagnostics]
    EVAL --> VIS[Plots and notebook explanations]
```

**Reproducibility:** record dataset sources, dependency versions, random seeds, preprocessing steps, and evaluation methodology. Keep test data out of model fitting and preprocessing statistics.
