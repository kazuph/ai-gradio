# AI Gradio

A dual-language AI web application generator built with React Router v7 and Cloudflare Workers.

## Overview

This project provides a web interface for generating applications using multiple LLM providers (OpenAI, Anthropic, Gemini, DeepSeek). It supports both JavaScript/TypeScript and Python implementations.

### JavaScript Implementation (Current)
- **Framework**: React Router v7 + Cloudflare Workers
- **LLM Providers**: OpenAI, Anthropic, Gemini, DeepSeek
- **Features**: Streaming responses, multiple model support, web app generation

### Python Implementation (Archived)
- **Framework**: Gradio
- **Location**: `old/ai-gradio-py/`

## Development

Run the dev server:

```sh
pnpm run dev
```

To run Wrangler for local Cloudflare Workers testing:

```sh
pnpm run build
pnpm run start
```

## Available Commands

- `pnpm run dev` - Start development server
- `pnpm run build` - Build for production  
- `pnpm run start` - Run with Wrangler for local testing
- `pnpm run deploy` - Deploy to Cloudflare Workers
- `pnpm run lint` - Run Biome linter
- `pnpm run format` - Check code formatting with Prettier
- `pnpm run typecheck` - Run TypeScript type checking
- `pnpm run validate` - Run all checks (lint, format, typecheck)
- `pnpm run typegen` - Generate Cloudflare Workers types

## Project Structure

### Core Components
- **LLM Providers**: `app/lib/llm/` - Abstracted providers for different AI services
- **Model Configuration**: `app/constants/models.ts` - Centralized model definitions
- **API Routes**: 
  - `/api/generate` - Main generation endpoint (streaming)
  - `/api/llm` - Simple LLM endpoint for generated apps
- **Components**: `app/components/` - Modular React components

### Environment Setup

You'll need to configure API keys for the LLM providers you want to use:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY` 
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`

## Deployment

First, create a [Cloudflare account](https://dash.cloudflare.com/sign-up) and set up your free custom Cloudflare Workers subdomain.

Then deploy:

```sh
pnpm run deploy
```

## Typegen

Generate types for your Cloudflare bindings in `wrangler.toml`:

```sh
pnpm run typegen
```

You will need to rerun typegen whenever you make changes to `wrangler.toml`.

## Styling

This project uses [Tailwind CSS](https://tailwindcss.com/) with custom CSS variables for theming. See the [Vite docs on css](https://vitejs.dev/guide/features.html#css) for more information.