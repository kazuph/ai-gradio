import os
import base64
import gradio as gr
import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms
import re
import requests
import zlib

# 追加：OpenAI API を利用するためのimport（必要に応じて環境変数などでapi_keyを設定してください）
import openai
from openai import OpenAI

# 既存のインポートに追加
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_gradio.logging_config import setup_logging

# ロガーの初期化
logger = setup_logging()
import asyncio
generation_lock = asyncio.Lock()  # 生成処理の重複実行を防ぐためのグローバルロック

# 既存のインポートに追加
from dotenv import load_dotenv
load_dotenv()  # 追加: .envファイルから環境変数をグローバルに読み込みます

# 既存のimportの直後に追加
BASE_URL = os.environ.get("BASE_URL", "http://localhost:7860")

# 定数: 各provider:モデル名のリスト
INTEGRATED_MODELS = [
    "openai:o3-mini",
    "openai:o3-mini-high",
    "openai:gpt-4o-mini",
    "openai:gpt-4o",
    "openai:chatgpt-4o-latest",
    "anthropic:claude-3-5-sonnet-20241022",
    "anthropic:claude-3-7-sonnet-20250219",
    "anthropic:claude-3-7-sonnet-20250219-thinking",
    "gemini:gemini-2.0-pro-exp-02-05",
    "gemini:gemini-2.0-flash",
    "gemini:gemini-2.0-flash-lite-preview-02-05",
    "gemini:gemini-2.0-flash-thinking-exp-01-21",
    # "gemini:gemini-exp-1206",
    # "gemini:gemini-1.5-pro",
    # "deepseek:deepseek-r1",
]

# デフォルトのシステムプロンプト（Webアプリ生成用）を更新
DEFAULT_WEBAPP_SYSTEM_PROMPT = """You are an expert web developer. When asked to create a web application:
1. Always respond with HTML code wrapped in ```html code blocks.
2. Include necessary CSS within <style> tags.
3. Include necessary JavaScript within <script> tags.
4. Ensure the code is complete and self-contained.
5. Add helpful comments explaining key parts of the code.
6. Focus on creating a functional and visually appealing result.
7. Additionally, an internal LLM API is available at POST /api/llm.
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
   - Note: Even with format_type="json", the response might be wrapped in ```json code blocks.
     The API will automatically handle this and extract the JSON content.
   - For text responses, omit format_type or set it to "text"
   - The default model is gemini-2.0-flash
   - Ensure you include proper error handling when invoking this API."""

# 通常テキスト応答用のシステムプロンプト
DEFAULT_TEXT_SYSTEM_PROMPT = """Before coding, make a plan inside a <thinking> tag.
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

You are a helpful assistant. Provide concise and informative answers to user queries."""

# Excalidraw図用のシステムプロンプト
DEFAULT_EXCALIDRAW_SYSTEM_PROMPT = """You are an expert diagram creator using Excalidraw format. When asked to create a diagram:
1. Always respond with ONLY valid Excalidraw JSON format wrapped in ```json code blocks.
2. Follow the Excalidraw JSON schema with required fields: type, version, source, elements.
3. Each element should have appropriate properties like type, x, y, width, height, etc.
4. Do not include any explanations or text outside the JSON code block.
5. Focus on creating clear, visually effective diagrams.
6. The diagram will be rendered using kroki.io's Excalidraw renderer.

Example of valid Excalidraw JSON format:
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "version": 175,
      "versionNonce": 279344008,
      "isDeleted": false,
      "id": "2ZYh24ed28FJ0yE-S3YNY",
      "fillStyle": "hachure",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "angle": 0,
      "x": 580,
      "y": 140,
      "strokeColor": "#000000",
      "backgroundColor": "#15aabf",
      "width": 80,
      "height": 20,
      "seed": 521916552,
      "groupIds": [],
      "strokeSharpness": "sharp",
      "boundElementIds": []
    }
  ]
}
```"""

# GraphViz図用のシステムプロンプト
DEFAULT_GRAPHVIZ_SYSTEM_PROMPT = """You are an expert diagram creator using GraphViz DOT language. When asked to create a diagram:
1. Always respond with ONLY valid GraphViz DOT code wrapped in ```graphviz code blocks.
2. Use appropriate node shapes, colors, and edge styles to create clear visualizations.
3. Do not include any explanations or text outside the code block.
4. Focus on creating clear, visually effective diagrams.
5. The diagram will be rendered using kroki.io's GraphViz renderer.

Example of valid GraphViz DOT code:
```graphviz
digraph G {
  rankdir=LR;
  node [shape=box, style=filled, fillcolor=lightblue];
  
  A [label="Start"];
  B [label="Process"];
  C [label="Decision", shape=diamond, fillcolor=lightyellow];
  D [label="End"];
  
  A -> B;
  B -> C;
  C -> D [label="Yes"];
  C -> B [label="No"];
}
```"""

# Mermaid図用のシステムプロンプト
DEFAULT_MERMAID_SYSTEM_PROMPT = """You are an expert diagram creator using Mermaid syntax. When asked to create a diagram:
1. Always respond with ONLY valid Mermaid code wrapped in ```mermaid code blocks.
2. Use appropriate Mermaid diagram types: flowchart, sequence, class, state, entity-relationship, gantt, pie, etc.
3. Do not include any explanations or text outside the code block.
4. Focus on creating clear, visually effective diagrams.
5. The diagram will be rendered using kroki.io's Mermaid renderer.

Example of valid Mermaid code:
```mermaid
graph TD
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    C --> D[Rethink]
    D --> B
    B ---->|No| E[End]
```

Or for a sequence diagram:
```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>John: Hello John, how are you?
    loop Healthcheck
        John->>John: Fight against hypochondria
    end
    Note right of John: Rational thoughts <br/>prevail!
    John-->>Alice: Great!
    John->>Bob: How about you?
    Bob-->>John: Jolly good!
```"""

# 各provider毎のLLM生成関数の実装を更新
def generate_openai(query, model, system_prompt, prompt_type):
    try:
        logger.info(f"Starting OpenAI generation with model {model}")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        client = OpenAI(api_key=api_key)

        # system_prompt を使用 (引数として受け取る)

        # モデル名とパラメータの処理
        if model in ("openai:o3-mini-high", "o3-mini-high"):
            actual_model = "o3-mini"
        else:
            actual_model = model.replace("openai:", "")

        # prompt_type に応じて user メッセージを設定する
        if prompt_type == "Web App":
            user_msg = f"Create a web application that: {query}"
        else:
            user_msg = query

        # 基本パラメータ（すべてのモデルで共通）
        params = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            "stream": False
        }

        # o3-mini-highの場合はreasoning_effortを設定
        if model in ("openai:o3-mini-high", "o3-mini-high"):
            params["reasoning_effort"] = "high"
        # o3系以外のモデルの場合は追加パラメータを設定
        elif not actual_model.startswith("o3-"):
            params.update({
                "max_tokens": 2048,
                "temperature": 0.7
            })

        response = client.chat.completions.create(**params)

        response_text = response.choices[0].message.content
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        logger.info(f"Successfully completed OpenAI generation with {model} ({actual_model})")
        return code, preview
    except Exception as e:
        logger.error(f"Error in OpenAI generation: {str(e)}")
        err = f"Error in OpenAI: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_anthropic(query, model, system_prompt, prompt_type):
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        # システムプロンプトを改善 (引数を使用)

        if prompt_type == "Web App":
            content = f"{system_prompt}\n\nCreate a web application that: {query}"
        else:
            content = f"{system_prompt}\n\n{query}"
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": content
            }]
        )

        response_text = response.content[0].text
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        return code, preview
    except Exception as e:
        err = f"Error in Anthropic: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_gemini(query, model, system_prompt, prompt_type):
    try:
        load_dotenv()

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(model_name=model)

        # システムプロンプト (引数を使用)

        if prompt_type == "Web App":
            last_message = f"Create a web application that: {query}"
        else:
            last_message = query
        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": "I understand and will follow these guidelines."}]},
                {"role": "user", "parts": [{"text": last_message}]}
            ],
            stream=False
        )

        response_text = response.text
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        return code, preview
    except Exception as e:
        err = f"Error in Gemini: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_deepseek(query, model, system_prompt, prompt_type):
    try:
        # DeepSeek APIキーの取得
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

        # DeepSeek API 呼び出し (system_promptを使用)
        if prompt_type == "Web App":
            user_msg = f"Create a web application that: {query}"
        else:
            user_msg = query
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=2048,
            stream=False
        )

        response_text = response.choices[0].message.content
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        return code, preview
    except Exception as e:
        err = f"Error in DeepSeek: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

# ユーティリティ関数の追加
def remove_code_block(text):
    """コードブロックから実際のコードを抽出する"""
    pattern = r'```(?:html)?\n(.+?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# send_to_preview関数を更新
def send_to_preview(code, iframe_id=""):
    """
    HTMLプレビューを生成する関数です。
    生成されたコードに <base> タグを追加し、iframe 内での相対 URL の解決を保証します。
    """
    clean_code = code.replace("```html", "").replace("```", "").strip()

    # 既にHTML文書でなければ、<base>タグ付きのHTMLテンプレートでラップ
    if "<html" not in clean_code.lower():
        wrapped_code = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <base href="{BASE_URL}/">
  </head>
  <body>
    {clean_code}
  </body>
</html>"""
    else:
        # 既存のHTMLドキュメントの場合は<head>タグ内に<base>タグを追加
        if "<head>" in clean_code.lower():
            wrapped_code = clean_code.replace(
                "<head>",
                f'<head>\n    <base href="{BASE_URL}/">'
            )
        else:
            # <head>タグがない場合は追加
            wrapped_code = clean_code.replace(
                "<html>",
                f'<html>\n  <head>\n    <base href="{BASE_URL}/">\n  </head>'
            )

    encoded_html = base64.b64encode(wrapped_code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"

    id_attribute = f' id="{iframe_id}"' if iframe_id else ""
    return f'''
        <iframe{id_attribute}
            src="{data_uri}"
            style="width:100%;border:none;border-radius:4px;"
            sandbox="allow-scripts allow-same-origin"
        ></iframe>
    '''

# 既存のsend_to_preview関数はそのままとして、以下に新しい関数 send_to_preview_react を追加

def send_to_preview_react(react_code, container_id=""):
    """
    LLM が生成した React コンポーネントのコードを使ってプレビューを生成する関数です。

    ※ この実装は試作用であり、セキュリティ対策は最小限です。

    生成されたコードは、Reactコンポーネント（例: GeneratedComponent）が定義されている前提です。
    Babel を利用して JSX をランタイムにコンパイルし、ReactDOM でレンダリングします。
    """
    if not container_id:
        container_id = "react_preview"
    html_react = f"""
    <div id="{container_id}"></div>
    <!-- React と ReactDOM の読み込み（開発用版） -->
    <script crossorigin src="https://unpkg.com/react@17/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
    <!-- Babel の読み込み（JSXをランタイムコンパイルするため） -->
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <!-- 生成された React コンポーネントのコードを含むスクリプト -->
    <script type="text/babel">
    {react_code}
    // 例: LLM により生成されたコード内で GeneratedComponent が定義されていると仮定
    ReactDOM.render(<GeneratedComponent />, document.getElementById("{container_id}"));
    </script>
    """
    return html_react

# 既存のimportに追加
from concurrent.futures import ThreadPoolExecutor

# 非同期のLLM生成関数を更新
async def async_generate_openai(query, model, system_prompt, prompt_type):
    try:
        # 同期的な generate_openai を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_openai, query, model, system_prompt, prompt_type)
    except Exception as e:
        logger.error(f"Error in async OpenAI generation: {str(e)}")
        return (f"Error in OpenAI: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in OpenAI: {str(e)}</div>")

async def async_generate_anthropic(query, model, system_prompt, prompt_type):
    try:
        # 同期的な generate_anthropic を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_anthropic, query, model, system_prompt, prompt_type)
    except Exception as e:
        logger.error(f"Error in async Anthropic generation: {str(e)}")
        return (f"Error in Anthropic: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in Anthropic: {str(e)}</div>")

async def async_generate_gemini(query, model, system_prompt, prompt_type):
    try:
        # 同期的な generate_gemini を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_gemini, query, model, system_prompt, prompt_type)
    except Exception as e:
        logger.error(f"Error in async Gemini generation: {str(e)}")
        return (f"Error in Gemini: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in Gemini: {str(e)}</div>")

async def async_generate_deepseek(query, model, system_prompt, prompt_type):
    try:
        # 同期的な generate_deepseek を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_deepseek, query, model, system_prompt, prompt_type)
    except Exception as e:
        logger.error(f"Error in async DeepSeek generation: {str(e)}")
        return (f"Error in DeepSeek: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in DeepSeek: {str(e)}</div>")

# 統合生成関数を簡素化
async def get_implementation_plan(query, prompt_type):
    """o3-miniを使用して実装計画を生成する"""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        client = OpenAI(api_key=api_key)

        planning_prompt = """あなたは優秀なソフトウェアアーキテクトです。
以下の要件に対する実装計画を作成してください。

1. 要件の分析
2. 必要な機能の洗い出し
3. 実装手順の詳細化
4. 注意点やベストプラクティス

回答は以下のフォーマットで行ってください：

<実装計画>
[ここに計画の詳細を記載]
</実装計画>"""

        if prompt_type == "Web App":
            user_msg = f"以下のWebアプリケーションの実装計画を作成してください：{query}"
        else:
            user_msg = f"以下の機能の実装計画を作成してください：{query}"

        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": planning_prompt},
                {"role": "user", "content": user_msg}
            ],
            stream=False
        )

        plan = response.choices[0].message.content
        return plan
    except Exception as e:
        logger.error(f"Error in implementation planning: {str(e)}")
        return f"Error in planning: {str(e)}"

async def generate_parallel(query, selected_models, system_prompt, prompt_type, use_planning=False):
    logger.info(f"Received generation request - Query: {query}")
    logger.info(f"Selected models: {selected_models}")

    implementation_plan = ""
    if use_planning:
        implementation_plan = await get_implementation_plan(query, prompt_type)
        # 実装計画をシステムプロンプトに追加
        system_prompt = f"{system_prompt}\n\n実装計画：\n{implementation_plan}"

    # 同時実行数を制御するセマフォを作成（必要に応じて数値を調整）
    semaphore = asyncio.Semaphore(5)  # 同時に5つまで実行可能

    async def run_with_semaphore(full_model, task):
        async with semaphore:
            return await task

    tasks = []
    for full_model in selected_models:
        try:
            provider, model = full_model.split(":")
            logger.info(f"Preparing task for {full_model}")

            if provider == "openai":
                task = async_generate_openai(query, model, system_prompt, prompt_type)
            elif provider == "anthropic":
                task = async_generate_anthropic(query, model, system_prompt, prompt_type)
            elif provider == "gemini":
                task = async_generate_gemini(query, model, system_prompt, prompt_type)
            elif provider == "deepseek":
                task = async_generate_deepseek(query, model, system_prompt, prompt_type)
            else:
                logger.error(f"Unknown provider: {full_model}")
                continue

            tasks.append((full_model, run_with_semaphore(full_model, task)))

        except Exception as e:
            logger.error(f"Error preparing task for {full_model}: {str(e)}")
            continue

    results = []
    if tasks:
        completed_tasks = await asyncio.gather(*(task for _, task in tasks))
        for (full_model, _), result in zip(tasks, completed_tasks):
            # await で結果を取り出してからリストに追加
            code, preview = result
            results.append((full_model, code, preview))

    # HTMLの生成（plan_htmlを削除）
    grid_html = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-coy.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-markup.min.js"></script>
    <div class='results-container'>
        <div class='results-grid'>
    """

    # 結果カードの生成
    for full_model, code, preview in results:
        provider, model_name = full_model.split(":")
        model_id = f"model_{provider}_{model_name}".replace("-", "_")

        preview_iframe = send_to_preview(code, iframe_id=f"{model_id}_preview")
        escaped_code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        grid_html += f"""
            <div class='result-card'>
                <div class='card-header'>
                    <div class='header-title'>
                        <strong>{provider.upper()}</strong> - {model_name}
                    </div>
                    <div class='header-buttons'>
                        <button class="button-icon" onclick="(function(){{
                            var codeEl = document.getElementById('{model_id}_code');
                            if (codeEl){{
                                codeEl.style.display = (codeEl.style.display === 'none' ? 'block' : 'none');
                                if (codeEl.style.display === 'block' && window.Prism){{ Prism.highlightAll(); }}
                            }}
                        }})()" title="コードを表示/非表示">
                            <svg viewBox="0 0 24 24">
                                <path fill="currentColor" d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
                            </svg>
                        </button>
                        <button class="button-icon" onclick="(function(){{ 
                            var iframe = document.getElementById('{model_id}_preview');
                            if (iframe){{
                                var currentSrc = iframe.src;
                                iframe.src = 'about:blank';
                                setTimeout(function() {{
                                    iframe.src = currentSrc;
                                }}, 100);
                            }}
                        }})()" title="プレビューを更新">
                            <svg viewBox="0 0 24 24">
                                <path fill="currentColor" d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div style='position: relative;'>
                    <div class='preview-container'>
                        {preview_iframe}
                    </div>
                    <div id='{model_id}_code' class='code-content' style='display:none;'>
                        <pre><code class="language-html">{escaped_code}</code></pre>
                    </div>
                </div>
            </div>
        """

    grid_html += """
        </div>
    </div>
    """

    logger.info("Completed generating HTML grid")
    return grid_html

# Kroki.ioを使ってSVGを取得する関数
def get_kroki_svg(diagram_source, diagram_type):
    """
    Kroki.ioを使って図のSVGを取得する
    
    Args:
        diagram_source (str): 図のソースコード
        diagram_type (str): 図のタイプ (excalidraw, graphviz, mermaid)
        
    Returns:
        str: SVG形式の図、エラーの場合はエラーメッセージ
    """
    try:
        # POSTリクエストを使用する方法
        url = f"https://kroki.io/{diagram_type}/svg"
        headers = {
            "Content-Type": "text/plain"
        }
        response = requests.post(url, headers=headers, data=diagram_source)
        
        if response.status_code == 200:
            return response.text
        else:
            # エラーの場合はエラーメッセージを返す
            return f"<div class='error'>Error: {response.status_code} - {response.text}</div>"
    except Exception as e:
        logger.error(f"Error getting SVG from Kroki.io: {str(e)}")
        return f"<div class='error'>Error: {str(e)}</div>"

# 図のプレビューを表示する関数
def send_to_diagram_preview(diagram_source, diagram_type):
    """
    図のソースコードからSVGを取得してプレビューを表示する
    
    Args:
        diagram_source (str): 図のソースコード
        diagram_type (str): 図のタイプ (excalidraw, graphviz, mermaid)
        
    Returns:
        str: HTMLコンテンツ
    """
    # コードブロックから図のソースコードを抽出
    pattern = r"```(?:" + diagram_type + r")?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, diagram_source, re.IGNORECASE)
    
    if match:
        source_code = match.group(1).strip()
        svg_content = get_kroki_svg(source_code, diagram_type)
        
        html_content = f"""
        <div class="result-card">
            <div class="card-header" style="display: flex; justify-content: space-between; padding: 8px 16px; align-items: center;">
                <div class="header-title">
                    <strong>{diagram_type.capitalize()} Diagram</strong>
                </div>
            </div>
            <div class="diagram-preview" style="padding: 16px; overflow: auto;">
                {svg_content}
            </div>
            <div class="code-content">
                <pre><code>{source_code}</code></pre>
            </div>
        </div>
        """
        return html_content
    else:
        return f"<div class='error'>Error: No {diagram_type} code block found in the response.</div>"

# 統合Gradioインターフェースの定義
def build_interface():
    custom_css = """
    :root {
        --card-bg: #ffffff;
        --header-bg: #f5f5f5;
        --border-color: #e0e0e0;
        --text-color: #333333;
        --icon-color: #333333;
        --button-hover-bg: rgba(0, 0, 0, 0.1);
        --code-bg: #f5f5f5;
        --code-text: #333333;
        --preview-bg: #ffffff;
        --preview-border: #e0e0e0;
    }
    * {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    }

    /* 結果出力エリアのスタイル */
    .result-output {
        min-height: 600px !important;
        margin-bottom: 2rem;
    }

    /* プログレスバーのコンテナ */
    .progress-container {
        background: var(--neutral-100);
        padding: 1rem;
        border-radius: 8px;
        min-height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* プログレスバーのスタイル */
    .progress-bar {
        height: 4px;
        background: var(--primary-500);
        border-radius: 2px;
        animation: progress 2s infinite;
    }

    @keyframes progress {
        0% { width: 0%; }
        50% { width: 70%; }
        100% { width: 100%; }
    }

    /* 実装計画セクションのスタイル */
    .implementation-plan {
        margin: 20px 0;
        padding: 20px;
        border-radius: 8px;
        background: var(--neutral-50);
    }

    /* 結果カードのスタイル更新 */
    .result-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 32px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        color: var(--text-color);
    }

    /* カードヘッダーのスタイルの修正 */
    .card-header {
        background: var(--header-bg, #f5f5f5);
        border-bottom: 1px solid var(--border-color, #e0e0e0);
        color: var(--text-color, #333333);
    }

    /* ヘッダー内の強調テキストの修正 */
    .header-title strong {
        color: var(--text-color, #333333);
        margin-right: 4px;
    }

    /* ヘッダーボタンのスタイル */
    .header-buttons {
        display: flex;
        gap: 8px;
    }

    .button-icon {
        background: none;
        border: 1px solid var(--border-color, #404040);
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        transition: all 0.2s;
        color: var(--icon-color, #333333);
    }

    .button-icon:hover {
        background-color: var(--button-hover-bg, rgba(0, 0, 0, 0.1));
        border-color: var(--icon-color, #333333);
    }

    .button-icon svg {
        width: 20px;
        height: 20px;
        color: var(--icon-color, #333333);
    }

    .preview-container {
        width: 100%;
        min-height: 600px !important;  /* 最小高さを設定 */
        height: 800px;  /* デフォルトの高さを設定 */
        position: relative;
        background: var(--preview-bg);
        border: 1px solid var(--preview-border);
        border-radius: 4px;
        margin: 16px;
        overflow: auto;  /* スクロール可能に */
    }

    .preview-container iframe {
        width: 100%;
        height: 100%;
        min-height: 600px !important;  /* iframeの最小高さも設定 */
        border: none;
        background: var(--preview-bg);
    }

    /* コードブロックのスタイル */
    .code-content {
        background: var(--code-bg, #1e1e1e);
        color: var(--code-text, #d4d4d4);
        padding: 16px;
        margin: 16px;
        border-radius: 4px;
        overflow-x: auto;
        max-height: 800px;
        overflow-y: auto;
        border: 1px solid var(--border-color);
    }

    .code-content pre {
        margin: 0;
        padding: 0;
        background: transparent;
    }

    .code-content code {
        font-family: 'Consolas', 'Monaco', 'Andale Mono', monospace;
        font-size: 14px;
        line-height: 1.5;
        color: inherit;
    }

    /* 図のプレビュー用スタイル */
    .diagram-preview {
        padding: 16px;
        background: white;
        border-radius: 4px;
        overflow: auto;
        text-align: center;
    }

    .diagram-preview svg {
        max-width: 100%;
        height: auto;
    }

    .error {
        color: red;
        padding: 16px;
        background: #ffeeee;
        border-radius: 4px;
        margin: 16px;
    }
    """
    with gr.Blocks(
        css=custom_css,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=["system-ui", "-apple-system", "sans-serif"]
        ).set(
            background_fill_primary="#ffffff",
            background_fill_secondary="#f5f5f5",
            border_color_primary="#e0e0e0"
        )
    ) as demo:
        gr.Markdown("# 🎨 AI Gradio Code Generator")

        # 入力セクション
        gr.Markdown("## 入力")
        with gr.Row():
            # 左側のカラム
            with gr.Column(scale=1):
                # テキスト入力エリア
                query_input = gr.Textbox(
                    placeholder="作成したいWebアプリや図の仕様を記載してください",
                    label="Request",
                    lines=8
                )
                # マルチセレクト: 統合対象のモデル一覧
                model_select = gr.Dropdown(
                    choices=INTEGRATED_MODELS,
                    value=[
                       # INTEGRATED_MODELS[4],
                        # INTEGRATED_MODELS[5],
                        # INTEGRATED_MODELS[6],
                        INTEGRATED_MODELS[7],
                        # INTEGRATED_MODELS[8],
                    ],
                    multiselect=True,
                    label="使用するモデルを選択",
                    info="複数のモデルを選択できます"
                )

                # 実装計画オプションをここに移動
                use_planning = gr.Radio(
                    choices=["はい", "いいえ"],
                    label="o3-miniによる実装計画を利用しますか？",
                    value="いいえ",
                    info="o3-miniが実装計画を作成し、その計画に基づいて各モデルが実装を行います。"
                )

            # 右側のカラム
            with gr.Column(scale=1):
                # システムプロンプト選択ラジオボタン
                prompt_type = gr.Radio(
                    ["Web App", "Text", "Excalidraw", "GraphViz", "Mermaid"],
                    label="Prompt Type",
                    value="Web App",
                    interactive=True
                )

                # システムプロンプト入力欄 (Web App 用, Text用, Excalidraw用, GraphViz用, Mermaid用)
                system_prompt_webapp_textbox = gr.Textbox(
                    placeholder="Enter system prompt for web app generation...",
                    label="System Prompt (Web App)",
                    lines=5,
                    value=DEFAULT_WEBAPP_SYSTEM_PROMPT,
                    visible=True
                )
                system_prompt_text_textbox = gr.Textbox(
                    placeholder="Enter system prompt for text generation...",
                    label="System Prompt (Text)",
                    lines=5,
                    value=DEFAULT_TEXT_SYSTEM_PROMPT,
                    visible=False
                )
                system_prompt_excalidraw_textbox = gr.Textbox(
                    placeholder="Enter system prompt for Excalidraw diagram generation...",
                    label="System Prompt (Excalidraw)",
                    lines=5,
                    value=DEFAULT_EXCALIDRAW_SYSTEM_PROMPT,
                    visible=False
                )
                system_prompt_graphviz_textbox = gr.Textbox(
                    placeholder="Enter system prompt for GraphViz diagram generation...",
                    label="System Prompt (GraphViz)",
                    lines=5,
                    value=DEFAULT_GRAPHVIZ_SYSTEM_PROMPT,
                    visible=False
                )
                system_prompt_mermaid_textbox = gr.Textbox(
                    placeholder="Enter system prompt for Mermaid diagram generation...",
                    label="System Prompt (Mermaid)",
                    lines=5,
                    value=DEFAULT_MERMAID_SYSTEM_PROMPT,
                    visible=False
                )

        # 実装計画セクション（結果の前に配置）
        plan_output = gr.Markdown(
            visible=False,
            elem_classes="implementation-plan"
        )

        # Generate ボタン
        generate_btn = gr.Button(
            "Generate",
            variant="primary",
            size="lg"
        )

        # 結果セクション
        gr.Markdown("## 結果")
        output_html = gr.HTML(
            container=True,
            show_label=True,
            elem_classes="result-output"
        )

        # プロンプトタイプに応じて system_prompt を決定する関数
        def get_system_prompt(prompt_type, webapp_prompt, text_prompt, excalidraw_prompt, graphviz_prompt, mermaid_prompt):
            if prompt_type == "Web App":
                return webapp_prompt
            elif prompt_type == "Text":
                return text_prompt
            elif prompt_type == "Excalidraw":
                return excalidraw_prompt
            elif prompt_type == "GraphViz":
                return graphviz_prompt
            elif prompt_type == "Mermaid":
                return mermaid_prompt
            else:
                return webapp_prompt  # デフォルト

        # プロンプトタイプの変更に応じてシステムプロンプト入力欄の表示/非表示を切り替える
        def update_system_prompt_visibility(prompt_type):
            return {
                system_prompt_webapp_textbox: prompt_type == "Web App",
                system_prompt_text_textbox: prompt_type == "Text",
                system_prompt_excalidraw_textbox: prompt_type == "Excalidraw",
                system_prompt_graphviz_textbox: prompt_type == "GraphViz",
                system_prompt_mermaid_textbox: prompt_type == "Mermaid"
            }

        # プロンプトタイプの変更イベントを設定
        prompt_type.change(
            fn=update_system_prompt_visibility,
            inputs=[prompt_type],
            outputs=[
                system_prompt_webapp_textbox,
                system_prompt_text_textbox,
                system_prompt_excalidraw_textbox,
                system_prompt_graphviz_textbox,
                system_prompt_mermaid_textbox
            ]
        )

        # ボタンクリック時の処理を更新
        async def run_generate(q, m, pt, wp, tp, ep, gp, mp, up):
            try:
                # 非ブロッキングでのロック取得を試みる（タイムアウトを短く設定）
                await asyncio.wait_for(generation_lock.acquire(), timeout=0.001)
            except asyncio.TimeoutError:
                logger.info("Generation is already in progress. Ignoring duplicate request.")
                return [plan_output, "<div style='padding: 8px;color:red;'>Process already in progress. Please wait...</div>"]
            try:
                use_plan = (up == "はい")
                if use_plan:
                    implementation_plan = await get_implementation_plan(q, pt)
                    logger.info("Implementation Plan:")
                    logger.info(implementation_plan)
                    plan_output.visible = True
                    plan_output.value = f"## 実装計画 (o3-mini)\n\n{implementation_plan}"
                else:
                    plan_output.visible = False
                    implementation_plan = ""

                result = await generate_parallel(
                    q, m,
                    get_system_prompt(pt, wp, tp, ep, gp, mp),
                    pt,
                    use_planning=use_plan
                )

                # 図の場合はKroki.ioを使ってプレビューを表示
                if pt in ["Excalidraw", "GraphViz", "Mermaid"]:
                    diagram_type = pt.lower()
                    diagram_preview = send_to_diagram_preview(result, diagram_type)
                    return [plan_output, diagram_preview]
                
                return [plan_output, result]
            finally:
                generation_lock.release()


        generate_btn.click(
            fn=run_generate,
            inputs=[
                query_input,
                model_select,
                prompt_type,
                system_prompt_webapp_textbox,
                system_prompt_text_textbox,
                system_prompt_excalidraw_textbox,
                system_prompt_graphviz_textbox,
                system_prompt_mermaid_textbox,
                use_planning
            ],
            outputs=[plan_output, output_html]
        )
    return demo

if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    ) 
