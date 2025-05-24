# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- `pnpm run dev` - Start development server
- `pnpm run build` - Build for production  
- `pnpm run start` - Run with Wrangler for local Cloudflare Workers testing
- `pnpm run deploy` - Deploy to Cloudflare Workers
- `pnpm run lint` - Run Biome linter
- `pnpm run format` - Check code formatting with Prettier
- `pnpm run typecheck` - Run TypeScript type checking
- `pnpm run validate` - Run all checks (lint, format, typecheck)
- `pnpm run typegen` - Generate Cloudflare Workers types from wrangler.toml

## Project Structure

This is a dual-language AI web application generator:

### ai-gradio-js/
React Router v7 + Cloudflare Workers application that generates web apps using multiple LLM providers.

**Key Architecture:**
- **LLM Providers**: Abstracted in `app/lib/llm/` with providers for OpenAI, Anthropic, Gemini, and DeepSeek
- **Model Configuration**: Centralized in `app/constants/models.ts` with categorized model lists
- **API Routes**: 
  - `/api/generate` - Main generation endpoint (streaming)
  - `/api/llm` - Simple LLM endpoint for generated apps to call
- **Components**: Modular React components in `app/components/`
- **Environment**: Cloudflare Workers runtime with environment variables for API keys

**LLM Provider Pattern:**
Each provider in `app/lib/llm/` follows the same interface:
```typescript
async function generate(query: string, model: ModelType, systemPrompt: string, env: Env): Promise<LLMResponse>
```

### ai-gradio-py/
Python Gradio application that provides a UI for the same functionality.

**Key Components:**
- **Main Interface**: `ai_gradio/integrated_gradio.py` - Gradio interface
- **LLM Integration**: `ai_gradio/api_llm.py` - API client for various providers
- **Entry Point**: Can be run with `uv run start` or `uv run python ai_gradio`

## Code Style
- **Formatting**: No semicolons, single quotes, 80 char line length  
- **Imports**: Use organize-imports plugin, explicit imports
- **Types**: Use TypeScript interfaces for objects, type for unions/aliases
- **Components**: Functional components with explicit type annotations
- **Error Handling**: Use try/catch blocks with instanceof Error checks
- **State Management**: Use React hooks (useState, useEffect)
- **Naming**: camelCase for variables/functions, PascalCase for components/types
- **CSS**: Use Tailwind with custom CSS variables (--color-*)
- **APIs**: Centralize in lib/ directory, handle errors consistently

## LLM Integration Notes
- Models are configured with provider prefixes (e.g., "openai:gpt-4o", "anthropic:claude-3-5-sonnet")
- System prompts are specialized for different output types (web apps, text, diagrams)
- The generate function supports concurrent execution across multiple models
- Environment variables for API keys are injected via Cloudflare Workers environment