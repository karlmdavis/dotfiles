# Documentation

This directory contains all project documentation, organized by type.

## Directory Structure

- `design-product/` - Product design specifications (features, user needs, business value)
- `design-engineering/` - Engineering design specifications (architecture, tech stack, infrastructure)
- `implementation-plans/` - Technical implementation plans
- `analysis/` - Analysis documents and research
- `notes/` - General project notes and meeting notes

**Typical document flow:** Analysis → Product Design + Engineering Design → Implementation Plans → Code

## Naming Conventions

### Single-File Documents

Format: `YYYY-MM-DD-short-name.md`

Examples:
- `2025-01-15-initial-feature-set.md`
- `2025-01-20-focus-tracking-impl.md`
- `2025-02-01-user-research-findings.md`

### Multi-File Documents

For documents that require multiple files (e.g., phased implementation plans, analysis with supporting materials):

Format: `YYYY-MM-DD-short-name/` directory containing:
- `README.md` - Main document
- Additional supporting files as needed

Examples:
```
2025-01-25-onboarding-flow/
  README.md
  user-journey-map.md
  wireframes.png

2025-02-10-backend-architecture/
  README.md
  phase-1-mvp.md
  phase-2-scaling.md
  database-schema.sql
```

## Style Guide

- Use kebab-case for all file and directory names (compatible with both Rust and Swift projects)
- Dates always in ISO 8601 format: YYYY-MM-DD
- Keep short names descriptive but concise (3-5 words max)
- All documents should be in Markdown format unless a different format is specifically required
