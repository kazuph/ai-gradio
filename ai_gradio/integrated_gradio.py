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

# 定数: 各provider:モデル名のリスト (OpenAIは gpt-4o, gpt-4o-mini, o3-mini のみ)
INTEGRATED_MODELS = [
    "openai:o3-mini",
    "openai:gpt-4o-mini", 
    "openai:gpt-4o", 
    "anthropic:claude-3-5-sonnet-20241022", 
    "gemini:gemini-2.0-flash-exp",
    "gemini:gemini-exp-1206",
    "gemini:gemini-2.0-flash-thinking-exp",
    "gemini:gemini-1.5-pro", 
    "deepseek:deepseek-r1",
]

# 各provider毎のLLM生成関数の実装を更新
def generate_openai(query, model):
    try:
        logger.info(f"Starting OpenAI generation with model {model}")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        client = OpenAI(api_key=api_key)
        
        system_prompt = """You are an expert web developer. When asked to create a web application:
1. Always respond with HTML code wrapped in ```html code blocks
2. Include necessary CSS within <style> tags
3. Include necessary JavaScript within <script> tags
4. Ensure the code is complete and self-contained
5. Add helpful comments explaining key parts of the code
6. Focus on creating a functional and visually appealing result"""
        
        # 基本パラメータ（すべてのモデルで共通）
        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a web application that: {query}"}
            ],
            "stream": False
        }
        
        # o3-mini以外のモデルの場合は追加パラメータを設定
        if not model.startswith("o3-"):
            params.update({
                "max_tokens": 2048,
                "temperature": 0.7
            })
        
        response = client.chat.completions.create(**params)
        
        response_text = response.choices[0].message.content
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        logger.info(f"Successfully completed OpenAI generation with {model}")
        return code, preview
    except Exception as e:
        logger.error(f"Error in OpenAI generation: {str(e)}")
        err = f"Error in OpenAI: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_anthropic(query, model):
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        # システムプロンプトを改善
        system_prompt = """You are an expert web developer. Please follow these guidelines:
1. Always wrap your HTML code in ```html code blocks
2. Include all necessary CSS and JavaScript within the HTML file
3. Write clean, modern, and responsive code
4. Add clear comments explaining the implementation
5. Focus on creating a functional and visually appealing result
6. Test that all interactive elements work properly"""
        
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"{system_prompt}\n\nCreate a web application that: {query}"
            }]
        )
        
        response_text = response.content[0].text
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        return code, preview
    except Exception as e:
        err = f"Error in Anthropic: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_gemini(query, model):
    try:
        load_dotenv()  # .envファイルを読み込み
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(model_name=model)
        
        # システムプロンプトを改善
        system_prompt = """As an expert web developer, please follow these rules:
1. Generate complete HTML code wrapped in ```html blocks
2. Include all CSS and JavaScript within the HTML file
3. Write modern, responsive, and well-structured code
4. Add descriptive comments for maintainability
5. Ensure all interactive features are properly implemented
6. Focus on both functionality and visual appeal"""
        
        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": "I understand and will follow these guidelines."}]},
                {"role": "user", "parts": [{"text": f"Create a web application that: {query}"}]}
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

def generate_deepseek(query, model):
    try:
        # DeepSeek APIキーの取得
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        # DeepSeek API 呼び出し
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert programmer. Write clean, efficient code."},
                {"role": "user", "content": query}
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
            style="width:100%;height:400px;border:none;border-radius:4px;"
            sandbox="allow-scripts allow-same-origin"
        ></iframe>
    '''

# 既存のimportに追加
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 非同期のLLM生成関数を更新
async def async_generate_openai(query, model):
    try:
        # 同期的な generate_openai を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_openai, query, model)
    except Exception as e:
        logger.error(f"Error in async OpenAI generation: {str(e)}")
        return (f"Error in OpenAI: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in OpenAI: {str(e)}</div>")

async def async_generate_anthropic(query, model):
    try:
        # 同期的な generate_anthropic を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_anthropic, query, model)
    except Exception as e:
        logger.error(f"Error in async Anthropic generation: {str(e)}")
        return (f"Error in Anthropic: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in Anthropic: {str(e)}</div>")

async def async_generate_gemini(query, model):
    try:
        # 同期的な generate_gemini を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_gemini, query, model)
    except Exception as e:
        logger.error(f"Error in async Gemini generation: {str(e)}")
        return (f"Error in Gemini: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in Gemini: {str(e)}</div>")

async def async_generate_deepseek(query, model):
    try:
        # 同期的な generate_deepseek を asyncio.to_thread で実行し、並列化
        return await asyncio.to_thread(generate_deepseek, query, model)
    except Exception as e:
        logger.error(f"Error in async DeepSeek generation: {str(e)}")
        return (f"Error in DeepSeek: {str(e)}",
                f"<div style='padding: 8px;color:red;'>Error in DeepSeek: {str(e)}</div>")

# 統合生成関数を非同期処理に更新
def generate_parallel(query, selected_models):
    # リクエストのログ出力
    logger.info(f"Received generation request - Query: {query}")
    logger.info(f"Selected models: {selected_models}")
    
    async def run_parallel():
        tasks = []
        for full_model in selected_models:
            try:
                provider, model = full_model.split(":")
                logger.info(f"Preparing task for {full_model}")
                
                if provider == "openai":
                    task = async_generate_openai(query, model)
                elif provider == "anthropic":
                    task = async_generate_anthropic(query, model)
                elif provider == "gemini":
                    task = async_generate_gemini(query, model)
                elif provider == "deepseek":
                    task = async_generate_deepseek(query, model)
                else:
                    logger.error(f"Unknown provider: {full_model}")
                    continue
                
                tasks.append((full_model, task))
                
            except Exception as e:
                logger.error(f"Error preparing task for {full_model}: {str(e)}")
                continue
        
        # 並列実行
        results = []
        if tasks:
            # 非同期タスクを同時実行
            completed_tasks = await asyncio.gather(*(task for _, task in tasks))
            # 結果を整理
            for (full_model, _), (code, preview) in zip(tasks, completed_tasks):
                results.append((full_model, code, preview))
        
        return results

    # asyncioのイベントループを取得または作成
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # 非同期処理を実行
    results = loop.run_until_complete(run_parallel())
    
    # 更新: 生成結果のグリッドHTMLの開始部分
    grid_html = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-markup.min.js"></script>
    <style>
        .results-container {
            width: 100%;
            padding: 20px;
            overflow-x: auto;
            display: flex;
            gap: 24px;
        }
        .results-grid {
            display: flex;
            gap: 24px;
            flex-wrap: nowrap;
        }
        .code-section {
            display: none;
            background: var(--code-bg, #1e1e1e);
            color: var(--code-color, #d4d4d4);
            padding: 16px;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
        }
        .preview-container {
            position: relative;
            width: 100%;
            padding-bottom: 75%; /* 4:3のアスペクト比 */
            height: 0;
            overflow: hidden;
            max-height: 600px;
        }
        .preview-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 4px;
            background: white;
        }
        .button-icon {
            width: 32px;
            height: 32px;
            padding: 6px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            cursor: pointer;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        .button-icon:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
        }
        .button-icon svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
        }
        .result-card {
            width: 800px;
            min-width: 800px;
            border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
            border-radius: 8px;
            overflow: hidden;
            background: var(--card-bg, #2d2d2d);
            color: var(--text-color, #fff);
            height: fit-content;
        }
        .card-header {
            background: var(--header-bg, #333);
            color: var(--header-color, #fff);
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-title {
            font-size: 1.2em;
        }
        .header-buttons {
            display: flex;
            gap: 8px;
        }
        .button-container {
            position: absolute;
            top: 8px;
            right: 8px;
            display: flex;
            gap: 8px;
            z-index: 10;
            background: rgba(0, 0, 0, 0.3);
            padding: 4px;
            border-radius: 20px;
            backdrop-filter: blur(4px);
        }
        pre {
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --card-bg: #2d2d2d;
                --header-bg: #333;
                --code-bg: #1e1e1e;
                --text-color: #fff;
                --border-color: rgba(255, 255, 255, 0.1);
            }
        }
        @media (prefers-color-scheme: light) {
            :root {
                --card-bg: #fff;
                --header-bg: #f5f5f5;
                --code-bg: #f8f8f8;
                --text-color: #333;
                --border-color: rgba(0, 0, 0, 0.1);
            }
        }
        .code-preview {
            position: relative;
            background: var(--code-bg);
            border-radius: 4px;
            margin: 16px 0;
        }
        .code-preview iframe {
            width: 100%;
            height: 400px;
            border: none;
            background: white;
        }
        .code-content {
            position: relative;
            padding: 16px;
            background: var(--code-bg);
            border-radius: 4px;
            overflow-x: auto;
        }
        .code-content pre {
            margin: 0;
            padding: 16px;
            background: transparent;
            font-family: 'Fira Code', monospace;
            font-size: 14px;
            line-height: 1.5;
        }
    </style>
    <div class='results-container'>
        <div class='results-grid'>
    """

    # 結果カード生成部分で、ボタンの onclick をインラインで実装
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
    
    logger.info(f"Completed parallel generation request for {len(results)} models")
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
                    value=[INTEGRATED_MODELS[0], INTEGRATED_MODELS[1]],
                    multiselect=True,
                    label="使用するモデルを選択",
                    info="複数のモデルを選択できます"
                )
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
        
        generate_btn.click(
            fn=generate_parallel,
            inputs=[query_input, model_select],
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