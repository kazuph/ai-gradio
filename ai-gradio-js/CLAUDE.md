# AI-Gradio-JS Development Guide

## Commands
- `pnpm run dev` - Start development server
- `pnpm run build` - Build for production
- `pnpm run start` - Run with Wrangler
- `pnpm run deploy` - Deploy to Cloudflare
- `pnpm run lint` - Run Biome linter
- `pnpm run format` - Check code formatting with Prettier
- `pnpm run typecheck` - Run TypeScript type checking
- `pnpm run validate` - Run all checks (lint, format, typecheck)

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

## Architecture
React Router v7 + Cloudflare Workers, supports multiple LLM providers (OpenAI, Anthropic, Google)