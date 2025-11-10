# Engineering Design Documents

This directory contains engineering and technical design specifications for the Happy Focus project.

## Purpose

Engineering design documents capture technical implementation decisions including:
- Technology stack choices (frameworks, libraries, tools).
- Architecture patterns and system design.
- Infrastructure setup and deployment configuration.
- Development tooling and workflow design.
- Technical constraints and trade-offs.

These documents focus on **how** we build the system and **what technologies** we use, complementing
  product design documents which focus on **what features** to build and **why**.

## When to Create an Engineering Design Document

Create an engineering design document when:
- Making significant technology stack decisions (choosing between frameworks, databases, etc.).
- Designing system architecture or major architectural changes.
- Establishing infrastructure patterns (CI/CD, deployment, monitoring).
- Defining development workflows and tooling standards.
- Making cross-cutting technical decisions that affect the entire codebase.

## Design Process

Engineering design decisions should generally be preceded by analysis:

1. **Analysis phase** (`docs/analysis/`):
   - Research available options and alternatives.
   - Evaluate trade-offs between different approaches.
   - Document findings and recommendations.
   - Example: "Analysis: PostgreSQL ORM Options (Diesel vs SQLx vs SeaORM)".

2. **Design phase** (this directory):
   - Make concrete technology choices based on analysis.
   - Specify architecture patterns and implementation approach.
   - Define configuration and setup details.
   - Document rationale linking back to analysis.

3. **Implementation phase** (`docs/implementation-plans/`):
   - Break design into concrete implementation tasks.
   - Specify exact file changes and code structure.
   - Create step-by-step implementation guide.

Not all engineering decisions require formal analysis documents (especially straightforward choices), but
  significant decisions with multiple viable options should be analyzed before design.

## File Naming Convention

Engineering design documents follow the same naming convention as other dated documents:

```
YYYY-MM-DD-descriptive-topic-name.md
```

Examples:
- `2025-11-01-project-structure-hello-world.md`
- `2025-11-15-observability-and-monitoring.md`
- `2025-12-01-production-deployment-architecture.md`

## Document Structure

Engineering design documents typically include:

1. **Overview**: What technical problem or need is being addressed.
2. **Technology choices**: Selected frameworks, libraries, and tools with rationale.
3. **Architecture**: System design, component structure, data flow.
4. **Configuration**: Specific settings, parameters, and deployment details.
5. **Trade-offs**: What was gained and what was sacrificed with chosen approach.
6. **Success criteria**: How to validate the technical implementation works.

## Relationship to Other Document Types

- **Product Design** (`docs/design-product/`): Defines features and user-facing capabilities.
- **Engineering Design** (this directory): Defines technical implementation approach.
- **Analysis** (`docs/analysis/`): Evaluates options to inform design decisions.
- **Implementation Plans** (`docs/implementation-plans/`): Breaks designs into actionable tasks.
- **Notes** (`docs/notes/`): Exploratory thinking and broader technical concepts.

The typical flow: Analysis → Product Design + Engineering Design → Implementation Plans → Code.
