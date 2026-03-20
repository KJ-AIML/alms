# System Design

> **Last Updated:** March 20, 2026  
> **Version:** 0.1.0  
> **Status:** ✅ Active

## Overview

FastAPI Agentic Starter is a production-ready boilerplate designed for building robust, AI-powered backends. Built with an **AI-First** philosophy, it combines the performance of FastAPI with **ALMS** (Agentic Layer for Microservices) - a pragmatic layered architecture that treats LLM interactions as first-class citizens.

Whether you're building autonomous agents, RAG pipelines, or intelligent APIs, this starter kit provides the scalability and clean code structure you need to move fast without over-engineering.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│         (Web Apps, Mobile Apps, External Services)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                    (src/api/main.py)                             │
├─────────────────────────────────────────────────────────────────┤
│  • CORS Middleware          • Security Headers                  │
│  • Request Logging          • Error Handling                    │
│  • API Key Authentication   • Scalar Documentation              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ALMS Architecture Layers                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ API Layer (src/api/)                                       │  │
│  │ HTTP handling, routing, middleware, validation             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Execution Layer (src/execution/)                           │  │
│  │ Business logic, use cases, action orchestration            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Agent Layer (src/agents/)                                  │  │
│  │ AI logic, prompts, tools, workflows (LangChain/LangGraph) │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Infrastructure Layers                                      │  │
│  │ • Providers (src/providers/) - External integrations       │  │
│  │ • Database (src/database/) - PostgreSQL/SQLAlchemy         │  │
│  │ • Core (src/core/) - Shared utilities                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     External Services                            │
├─────────────────────────────────────────────────────────────────┤
│  • OpenAI/Gemini API    • PostgreSQL    • Redis                 │
│  • Vector Databases     • Third-party APIs                       │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Typical Request Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│  API Endpoint   │  ← src/api/endpoints/v1/*.py
│  (Validation)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Usecase      │  ← src/execution/usecases/*.py
│  (Orchestrate)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Action      │  ← src/execution/actions/*.py
│   (Execute)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Agent       │  ← src/agents/agent_manager/*.py
│  (AI Logic)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Provider     │  ← src/providers/*/*.py
│ (External API)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Response     │  ← Standardized AppResponse
│   (JSON/API)    │
└─────────────────┘
```

### Agent-First Data Flow

For AI-centric operations, the flow emphasizes the Agent layer:

```
User Query/Request
        │
        ▼
┌──────────────────┐
│   API Endpoint   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Usecase      │
│  (Pre-process)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│      Agent       │
│  (LangChain/     │
│   LangGraph)     │
│                  │
│  ┌────────────┐  │
│  │  Prompts   │  │  ← src/agents/prompts/*.py
│  └────────────┘  │
│  ┌────────────┐  │
│  │   Tools    │  │  ← src/agents/tools/*.py
│  └────────────┘  │
│  ┌────────────┐  │
│  │ Workflows  │  │  ← src/agents/workflows/*.py
│  └────────────┘  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Action       │
│ (Post-process)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Response     │
└──────────────────┘
```

## Layer Communication Rules

### ✅ Correct Flow

```python
# Flow through all layers
API Endpoint → Usecase → Action → Provider

# Example: src/api/endpoints/v1/sample_agent.py
@router.post("/agent")
async def agent_endpoint(request: QueryRequest):
    usecase = SampleUsecase()      # Execution Layer
    result = await usecase.execute(request.query)
    return AppResponse(success=True, data=result)

# Example: src/execution/usecases/sample_usecase.py
class SampleUsecase:
    async def execute(self, query: str):
        action = SampleAction()     # Action Layer
        return await action.run(query)

# Example: src/execution/actions/sample_action.py
class SampleAction:
    async def run(self, query: str):
        agent = SampleAgent()       # Agent Layer
        return await agent.process(query)
```

### ❌ Anti-Patterns (Never Do)

```python
# Never skip layers
API Endpoint → Provider     # Don't bypass execution layer
Usecase → Database          # Use repository pattern
Action → External API       # Go through provider layer
```

## Microservice Scalability

ALMS makes it easy to extract layers into microservices:

```
Monolith                    →    Microservices
┌──────────┐                     ┌──────────────┐
│ API      │ ─────────────────→  │ API Gateway  │
├──────────┤                     ├──────────────┤
│ Execution│ ─────────────────→  │ Logic Svc    │
├──────────┤                     ├──────────────┤
│ Agent    │ ─────────────────→  │ Agent Svc    │
├──────────┤                     ├──────────────┤
│ DB       │ ─────────────────→  │ Data Svc     │
└──────────┘                     └──────────────┘
```

Each layer is already isolated - just add HTTP/gRPC clients between them!

## Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    API Layer (src/api/)                       │
├──────────────────────────────────────────────────────────────┤
│  main.py          │ FastAPI app factory                      │
│  router/routers.py│ API router aggregation                   │
│  endpoints/v1/    │ Versioned endpoints                      │
│  middlewares/     │ Security, logging, error handling        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Execution Layer (src/execution/)                 │
├──────────────────────────────────────────────────────────────┤
│  usecases/        │ Business flow orchestration              │
│  actions/         │ Discrete operations                      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                 Agent Layer (src/agents/)                     │
├──────────────────────────────────────────────────────────────┤
│  agent_manager/   │ Agent definitions (LangChain)            │
│  prompts/         │ LLM prompt templates                     │
│  tools/           │ Agent tools                              │
│  workflows/       │ LangGraph workflows                      │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Infrastructure Layers (src/*)                    │
├──────────────────────────────────────────────────────────────┤
│  providers/       │ External service integrations            │
│  database/        │ Repositories, migrations (Alembic)       │
│  config/          │ Settings (Pydantic), logging             │
│  core/            │ Exceptions, base classes                 │
│  models/          │ Domain models                            │
└──────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **ALMS over Hexagonal** | Simpler, AI-native, microservice-ready |
| **Layer Isolation** | Clear separation, testable, scalable |
| **Repository Pattern** | Database abstraction, testability |
| **Provider Pattern** | External service encapsulation |
| **Pydantic v2** | Modern validation, FastAPI integration |
| **Async-First** | Performance for I/O-bound operations |
| **LangChain/LangGraph** | Industry standard for agent workflows |

## Related Documentation

- [02-Design-Patterns.md](./02-Design-Patterns.md) - Detailed pattern documentation
- [04-Tech-Stack.md](./04-Tech-Stack.md) - Technology choices
- [05-Project-Structure.md](./05-Project-Structure.md) - Directory organization
