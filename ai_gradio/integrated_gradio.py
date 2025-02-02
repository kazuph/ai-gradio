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

def generate_gemini(query, model, code=None):
    try:
        load_dotenv()
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(model_name=model)
        
        if code:  # コード解説モード
            system_prompt = """あなたは優秀なプログラマーです。
提供されたHTMLコードを分析し、以下の点について日本語で解説してください：
1. コードの全体的な構造と目的
2. 使用されている主要な技術（HTML/CSS/JavaScript）
3. 実装の特徴や工夫している点
4. 改善できる点があれば指摘
簡潔かつ分かりやすく説明してください。"""
            
            response = model.generate_content(
                [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\nコード:\n{code}"}]}
                ],
                stream=False
            )
            
            return response.text

        # 通常のコード生成モード（既存のコード）
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
            style="width:100%;border:none;border-radius:4px;"
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
async def generate_parallel(query, selected_models):
    logger.info(f"Received generation request - Query: {query}")
    logger.info(f"Selected models: {selected_models}")
    
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
    
    results = []
    if tasks:
        # コード生成タスクを実行
        completed_tasks = await asyncio.gather(*(task for _, task in tasks))
        
        # 解説生成タスクを準備
        explanation_tasks = []
        for (full_model, _), (code, preview) in zip(tasks, completed_tasks):
            if code and not code.startswith("Error"):
                # 解説生成を非同期タスクとして追加
                explanation_task = asyncio.create_task(asyncio.to_thread(
                    generate_gemini,
                    None,
                    "gemini-exp-1206",
                    code
                ))
                explanation_tasks.append((full_model, explanation_task))
            else:
                explanation_tasks.append((full_model, None))
        
        # 解説生成タスクを実行
        explanations = []
        results = []
        for i, (full_model, task) in enumerate(explanation_tasks):
            if task:
                try:
                    explanation = await task
                except Exception as e:
                    logger.error(f"Error generating explanation for {full_model}: {str(e)}")
                    explanation = "解説の生成に失敗しました。"
            else:
                explanation = "コード生成に失敗したため、解説を生成できません。"
            explanations.append(explanation)
            code, preview = completed_tasks[i]
            results.append((full_model, code, preview, explanation))
        
        # 総合解説の生成（2つ以上の結果がある場合のみ）
        if len(explanations) > 1:
            try:
                analysis = await asyncio.to_thread(
                    generate_gemini,
                    None,
                    "gemini-exp-1206",
                    "以下の各モデルによる実装の解説を比較分析し、最も優れた実装はどれか考察してください:\n\n" + 
                    "\n\n".join(explanations)
                )
                results.append(("analysis", "", "", analysis))
            except Exception as e:
                logger.error(f"Error generating analysis: {str(e)}")
                results.append(("analysis", "", "", "総合解説の生成に失敗しました。"))

    # HTMLの生成
    grid_html = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-markup.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .results-container {
            width: 100%;
            padding: 20px;
            overflow-x: auto;
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
            background: var(--card-bg, #ffffff);
            border: 1px solid var(--border-color, #e0e0e0);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 24px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: var(--header-bg, #f5f5f5);
            border-bottom: 1px solid var(--border-color, #e0e0e0);
        }
        .preview-container {
            width: 100%;
            aspect-ratio: 1;
            position: relative;
            background: white;
        }
        .preview-container iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .code-content {
            display: none;
            padding: 16px;
            background: var(--code-bg, #1e1e1e);
            max-height: 400px;
            overflow-y: auto;
        }
        .explanation {
            padding: 16px;
            border-top: 1px solid var(--border-color, #e0e0e0);
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
        @media (max-width: 768px) {
            .results-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* マークダウンスタイルを追加 */
        .markdown-body {
            color: var(--text-color, #333);
            line-height: 1.6;
            word-wrap: break-word;
        }
        .markdown-body h1,
        .markdown-body h2,
        .markdown-body h3,
        .markdown-body h4 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        .markdown-body code {
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: var(--code-bg-inline, rgba(27,31,35,0.05));
            border-radius: 3px;
            font-family: monospace;
        }
        .markdown-body pre code {
            padding: 0;
            background-color: transparent;
        }
        .markdown-body ul,
        .markdown-body ol {
            padding-left: 2em;
            margin-top: 0;
            margin-bottom: 16px;
        }
        .markdown-body blockquote {
            padding: 0 1em;
            color: var(--quote-color, #6a737d);
            border-left: 0.25em solid var(--quote-border, #dfe2e5);
            margin: 0 0 16px 0;
        }
    </style>
    <script>
        function initializeMarkdown() {
            // マークダウンの設定
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false
            });
            
            // 修正: data-markdown 属性があればその値を利用し、なければ内包テキストを使用する
            document.querySelectorAll('.markdown-body').forEach(function(element) {
                const rawMarkdown = element.getAttribute('data-markdown') || element.textContent;
                if (rawMarkdown) {
                    try {
                        element.innerHTML = marked.parse(rawMarkdown);
                    } catch (e) {
                        console.error('Markdown parsing error:', e);
                    }
                }
            });
            
            // シンタックスハイライトを適用
            if (window.Prism) {
                Prism.highlightAll();
            }
        }

        // DOMContentLoadedとload両方で初期化を試みる
        document.addEventListener('DOMContentLoaded', initializeMarkdown);
        window.addEventListener('load', initializeMarkdown);
        
        // 1秒後にも実行（非同期コンテンツ対策）
        setTimeout(initializeMarkdown, 1000);
    </script>
    <div class='results-container'>
        <div class='results-grid'>
    """

    # デバッグログを追加
    logger.info(f"Processing {len(results)} results")
    
    # 結果カードの生成
    for full_model, code, preview, explanation in results:
        logger.info(f"Generating card for model: {full_model}")
        
        if full_model == "analysis":
            grid_html += f"""
                <div class='result-card analysis-card'>
                    <div class='card-header'>
                        <div class='header-title'>実装の比較分析</div>
                    </div>
                    <div class='explanation'>
                        <div class='markdown-body' data-markdown="{explanation.replace('"', '&quot;')}">
                            {explanation}
                        </div>
                    </div>
                </div>
            """
        else:
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
                    <div class='explanation'>
                        <h4>コードの解説:</h4>
                        <div class='markdown-body' data-markdown="{explanation.replace('"', '&quot;')}">
                            {explanation}
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