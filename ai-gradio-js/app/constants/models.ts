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
    "gemini:gemini-2.5-pro-exp-03-25",
    "gemini:gemini-2.0-pro-exp-02-05",
    "gemini:gemini-2.0-flash",
    "gemini:gemini-2.0-flash-lite-preview-02-05",
    "gemini:gemini-2.0-flash-thinking-exp-01-21",
  ],
  DeepSeek: [
    "deepseek:deepseek-reasoner",
    "deepseek:deepseek-chat",
    "deepseek:deepseek-coder",
  ],
};

// より防御的な実装
export const INTEGRATED_MODELS = (() => {
  try {
    // Object.valuesの結果が配列であることを確認
    const categoryValues = Object.values(MODEL_CATEGORIES);
    if (!Array.isArray(categoryValues)) {
      console.error('MODEL_CATEGORIES values is not an array');
      return [];
    }
    
    // 各カテゴリの値が配列であることを確認
    const validArrays = categoryValues.filter(arr => Array.isArray(arr));
    
    // 配列をフラット化
    return validArrays.flatMap(arr => arr) as readonly string[];
  } catch (error) {
    console.error('Error processing MODEL_CATEGORIES:', error);
    return [] as readonly string[];
  }
})();

export const DEFAULT_WEBAPP_SYSTEM_PROMPT = `You are an expert web developer. When asked to create a web application:
1. Always respond with HTML code wrapped in \`\`\`html code blocks.
2. Include necessary CSS within <style> tags.
3. Include necessary JavaScript within <script> tags.
4. Ensure the code is complete and self-contained.
5. Add helpful comments explaining key parts of the code.
6. Focus on creating a functional and visually appealing result.
7. Note: This is an application running inside an iframe.
8. IMPORTANT: DO NOT use localStorage or sessionStorage as they won't work properly in the iframe environment.
9. Additionally, an internal LLM API is available at POST /api/llm.
   - To use this API, send a JSON object with:
     * 'prompt' field containing your textual prompt
     * 'format_type' field set to either "text" or "json"
   - Example request for JSON response:
     fetch('/api/llm', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         prompt: 'Convert 42 to Roman numerals and return as JSON',
         format_type: 'json'
       })
     })
   - When format_type is "json", ensure your prompt asks for JSON format.
   - Example JSON response format:
     {
       "number": 42,
       "roman": "XLII"
     }
   - Note: Even with format_type="json", the response might be wrapped in \`\`\`json code blocks.
     The API will automatically handle this and extract the JSON content.
   - For text responses, omit format_type or set it to "text"
   - The default model is gemini-2.0-flash
   - Ensure you include proper error handling when invoking this API.`;

export const DEFAULT_TEXT_SYSTEM_PROMPT = `You are a helpful assistant. Provide concise and informative answers to user queries.`;
