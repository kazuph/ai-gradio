import os
import base64
import gradio as gr
import modelscope_studio.components.antd as antd
import modelscope_studio.components.base as ms
import re

# 追加：OpenAI API を利用するためのimport（必要に応じて環境変数などでapi_keyを設定してください）
import openai
from openai import OpenAI

# 既存のインポートに追加
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_gradio.logging_config import setup_logging

# ロガーの初期化
logger = setup_logging()

# 既存のインポートに追加
from dotenv import load_dotenv
load_dotenv()  # 追加: .envファイルから環境変数をグローバルに読み込みます

# 定数: 各provider:モデル名のリスト
INTEGRATED_MODELS = [
    "openai:o3-mini",
    "openai:o3-mini-high",
    "openai:gpt-4o-mini", 
    "openai:gpt-4o", 
    "anthropic:claude-3-5-sonnet-20241022", 
    "gemini:gemini-2.0-flash",
    "gemini:gemini-2.0-flash-lite-preview-02-05",
    "gemini:gemini-2.0-pro-exp-02-05",
    "gemini:gemini-2.0-flash-thinking-exp-01-21",
    # "gemini:gemini-exp-1206",
    # "gemini:gemini-1.5-pro", 
    # "deepseek:deepseek-r1",
]

# デフォルトのシステムプロンプト（Webアプリ生成用）
DEFAULT_WEBAPP_SYSTEM_PROMPT = """You are an expert web developer. When asked to create a web application:
1. Always respond with HTML code wrapped in ```html code blocks
2. Include necessary CSS within <style> tags
3. Include necessary JavaScript within <script> tags
4. Ensure the code is complete and self-contained
5. Add helpful comments explaining key parts of the code
6. Focus on creating a functional and visually appealing result"""

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

def send_to_preview(code, iframe_id=""):
    """HTMLプレビューを生成する"""
    # Clean the code and create base64 encoded data URI
    clean_code = code.replace("```html", "").replace("```", "").strip()
    encoded_html = base64.b64encode(clean_code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    
    id_attribute = f' id="{iframe_id}"' if iframe_id else ""
    return f'''
        <iframe{id_attribute}
            src="{data_uri}"
            style="width:100%;border:none;border-radius:4px;"
            sandbox="allow-scripts allow-same-origin"
        ></iframe>
    '''

# 既存のimportに追加
import asyncio
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
async def generate_parallel(query, selected_models, system_prompt, prompt_type):
    logger.info(f"Received generation request - Query: {query}")
    logger.info(f"Selected models: {selected_models}")
    
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

    # HTMLの生成
    grid_html = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-markup.min.js"></script>
    <style>
        :root {
            --card-bg: #ffffff;
            --border-color: #e0e0e0;
            --header-bg: #f5f5f5;
            --code-bg: #1e1e1e;
            --text-color: #333333;
            --preview-bg: #ffffff;
            --preview-border: #e0e0e0;
            --button-bg: rgba(0, 0, 0, 0.1);
            --button-hover: rgba(0, 0, 0, 0.2);
            --button-color: #333333;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --card-bg: #2d2d2d;
                --border-color: #444444;
                --header-bg: #1a1a1a;
                --code-bg: #1e1e1e;
                --text-color: #e0e0e0;
                --preview-bg: #ffffff;
                --preview-border: #444444;
                --button-bg: rgba(255, 255, 255, 0.1);
                --button-hover: rgba(255, 255, 255, 0.2);
                --button-color: #ffffff;
            }
        }

        .results-container {
            width: 100%;
            padding: 20px;
            overflow-x: auto;
            background-color: var(--card-bg);
            color: var(--text-color);
        }

        .results-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            justify-content: center;
        }

        .result-card {
            width: 800px;
            min-width: 800px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 24px;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: var(--header-bg);
            border-bottom: 1px solid var(--border-color);
            color: var(--text-color);
        }

        .preview-container {
            width: 100%;
            aspect-ratio: 1;
            position: relative;
            background: var(--preview-bg);
            border: 1px solid var(--preview-border);
            border-radius: 4px;
            margin: 16px;
        }

        .preview-container iframe {
            width: 100%;
            height: 100%;
            border: none;
            background: var(--preview-bg);
        }

        .code-content {
            display: none;
            padding: 16px;
            background: var(--code-bg);
            max-height: 400px;
            overflow-y: auto;
            margin: 16px;
            border-radius: 4px;
        }

        .code-content pre {
            margin: 0;
        }

        .code-content code {
            color: #e0e0e0;
        }

        .header-buttons {
            display: flex;
            gap: 8px;
        }

        .button-icon {
            width: 32px;
            height: 32px;
            padding: 6px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            background: var(--button-bg);
            color: var(--button-color);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .button-icon:hover {
            background: var(--button-hover);
        }

        .button-icon svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
        }

        @media (max-width: 768px) {
            .results-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
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
                                if (codeEl.style.display === 'block' && window.Prism){{{{ Prism.highlightAll(); }}}} 
                            }} 
                        }})()" title="コードを表示/非表示">
                            <svg viewBox="0 0 24 24">
                                <path fill="currentColor" d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
                            </svg>
                        </button>
                        <button class="button-icon" onclick="(function(){{ 
                            var iframe = document.getElementById('{model_id}_preview');
                            if (iframe && iframe.contentWindow){{ 
                                iframe.contentWindow.location.reload();
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

# 統合Gradioインターフェースの定義
def build_interface():
    with gr.Blocks(title="統合AI Code Generator", theme=gr.themes.Soft()) as interface:
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 入力")
                # テキスト入力エリア
                query_input = gr.Textbox(
                    placeholder="作成したいWebアプリの仕様を記載してください",
                    label="Request",
                    lines=3
                )
                # マルチセレクト: 統合対象のモデル一覧
                model_select = gr.Dropdown(
                    choices=INTEGRATED_MODELS,
                    value=[
                        INTEGRATED_MODELS[0], 
                        INTEGRATED_MODELS[4],
                        INTEGRATED_MODELS[7],
                    ],
                    multiselect=True,
                    label="使用するモデルを選択",
                    info="複数のモデルを選択できます"
                )

                # システムプロンプト選択ラジオボタン
                prompt_type = gr.Radio(
                    ["Web App", "Text"],  # 選択肢
                    label="Prompt Type",
                    value="Web App",  # デフォルト値を "Web App" に設定
                    interactive=True
                )

                # システムプロンプト入力欄 (Web App 用, Text用)
                system_prompt_webapp_textbox = gr.Textbox(
                    placeholder="Enter system prompt for web app generation...",
                    label="System Prompt (Web App)",
                    lines=5,
                    value=DEFAULT_WEBAPP_SYSTEM_PROMPT,  # デフォルトのプロンプトを設定
                    visible=True  # 最初は表示
                )
                system_prompt_text_textbox = gr.Textbox(
                    placeholder="Enter system prompt for text generation...",
                    label="System Prompt (Text)",
                    lines=5,
                    value=DEFAULT_TEXT_SYSTEM_PROMPT,  # デフォルトのプロンプトを設定
                    visible=False  # 最初は非表示
                )
                
                # system_prompt_webapp_textbox が変更されたときに prompt_type も "Web App" に設定
                system_prompt_webapp_textbox.change(lambda: "Web App", inputs=[], outputs=[prompt_type])
                # system_prompt_text_textbox が変更されたときに prompt_type も "Text" に設定
                system_prompt_text_textbox.change(lambda: "Text", inputs=[], outputs=[prompt_type])

                # プロンプトタイプに基づいて表示を切り替える関数
                def switch_prompt_visibility(prompt_type):
                    if prompt_type == "Web App":
                        return gr.update(visible=True), gr.update(visible=False)  # Web App 用を表示、Text用を非表示
                    else:
                        return gr.update(visible=False), gr.update(visible=True) # Web App 用を非表示、Text用を表示

                # ラジオボタンが変更されたときのイベントハンドラ
                prompt_type.change(
                    switch_prompt_visibility,
                    inputs=[prompt_type],
                    outputs=[system_prompt_webapp_textbox, system_prompt_text_textbox])

                generate_btn = gr.Button(
                    "Generate",
                    variant="primary",
                    size="lg"
                )
            with gr.Column(scale=2):
                gr.Markdown("## 結果")
                # 結果出力用のHTMLコンポーネント
                output_html = gr.HTML(
                    container=True,
                    show_label=True
                )

        # プロンプトタイプに応じて system_prompt を決定する関数
        def get_system_prompt(prompt_type, webapp_prompt, text_prompt):
            if prompt_type == "Web App":
                return webapp_prompt  # 編集された、またはデフォルトのWeb App用プロンプト
            else:
                return text_prompt  # 編集された、またはデフォルトのText用プロンプト

        # ボタンクリック時の処理
        async def run_generate(q, m, pt, wp, tp):
            # get_system_promptでシステムプロンプトを取得し、prompt_type(pt)も渡す
            return await generate_parallel(q, m, get_system_prompt(pt, wp, tp), pt)

        generate_btn.click(
            fn=run_generate,
            inputs=[query_input, model_select, prompt_type, system_prompt_webapp_textbox, system_prompt_text_textbox],
            outputs=output_html
        )
    return interface

if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    ) 