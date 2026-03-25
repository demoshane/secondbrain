---
created: 2026-03-16T15:36:11.646Z
title: Add tests for LLM adapters
area: testing
files:
  - engine/adapters/base.py
  - engine/adapters/claude_adapter.py
  - engine/adapters/ollama_adapter.py
---

## Problem

The three LLM adapter modules have zero test coverage. Adapter selection and routing logic is mission-critical for the AI layer but completely unprotected against regression.

## Solution

Add unit tests mocking Claude API and Ollama HTTP calls. Test adapter instantiation, request/response mapping, error handling, and the base class contract.
