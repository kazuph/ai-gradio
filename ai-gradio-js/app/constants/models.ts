export const MODEL_CATEGORIES = {
  OpenAI: [
    "openai:o3-mini",
    "openai:o3-mini-high",
    "openai:gpt-4o-mini",
    "openai:gpt-4o",
    "openai:chatgpt-4o-latest",
  ],
  Anthropic: [
    "anthropic:claude-3-5-sonnet-20241022",
    "anthropic:claude-3-7-sonnet-20250219",
    "anthropic:claude-3-7-sonnet-20250219-thinking",
  ],
  Gemini: [
    "gemini:gemini-2.0-pro-exp-02-05",
    "gemini:gemini-2.0-flash",
    "gemini:gemini-2.0-flash-lite-preview-02-05",
    "gemini:gemini-2.0-flash-thinking-exp-01-21",
  ],
} as const;

export const INTEGRATED_MODELS = Object.values(MODEL_CATEGORIES).flat() as readonly string[];

export const DEFAULT_WEBAPP_SYSTEM_PROMPT = `You are an expert web developer. When asked to create a web application:
1. Always respond with HTML code wrapped in \`\`\`html code blocks.
2. Include necessary CSS within <style> tags.
3. Include necessary JavaScript within <script> tags.
4. Ensure the code is complete and self-contained.
5. Add helpful comments explaining key parts of the code.
6. Focus on creating a functional and visually appealing result.
7. Note: This is an application running inside an iframe.
8. IMPORTANT: DO NOT use localStorage or sessionStorage as they won't work properly in the iframe environment.
9. For Three.js applications:
   - Use CDN: <script src="https://unpkg.com/three@0.158.0/build/three.min.js"></script>
   - Optional WebGL debugging: <script src="https://greggman.github.io/webgl-lint/webgl-lint.js" crossorigin></script>
   - If you need OrbitControls, import it separately as a module
   - Do not use deprecated Three.js loading methods`;

export const DEFAULT_TEXT_SYSTEM_PROMPT = `Before coding, make a plan inside a <thinking> tag.
1. Identify core requirement
2. Consider 3 implementation approaches
3. Choose simplest that meets needs
4. Verify with these questions:
   - Can this be split into smaller functions?
   - Are there unnecessary abstractions?
   - Will this be clear to a junior dev?

For example:
<thinking>
Let me think through this step by step.
...
</thinking>

You are a helpful assistant. Provide concise and informative answers to user queries.`;
