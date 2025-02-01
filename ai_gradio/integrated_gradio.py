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

# 定数: 各provider:モデル名のリスト (OpenAIは gpt-4o, gpt-4o-mini, o3-mini のみ)
INTEGRATED_MODELS = [
    "openai:o3-mini",
    "openai:gpt-4o-mini", 
    "openai:gpt-4o", 
    "anthropic:claude-3-5-sonnet-20241022", 
    "anthropic:claude-3-opus-20240229",
    "gemini:gemini-1.5-pro", 
    "gemini:gemini-2.0-flash-exp",
    "gemini:gemini-2.0-exp",
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

def send_to_preview(code):
    """HTMLプレビューを生成する"""
    # Clean the code and escape special characters for HTML
    clean_code = code.replace("```html", "").replace("```", "").strip()
    escaped_code = clean_code.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    return f'''
        <iframe 
            srcdoc="<!DOCTYPE html><html><body>{escaped_code}</body></html>"
            width="100%" 
            height="920px"
            sandbox="allow-scripts allow-same-origin"
        ></iframe>
    '''

# 統合生成関数（並列実行の疑似実装）
def generate_parallel(query, selected_models):
    # リクエストのログ出力
    logger.info(f"Received generation request - Query: {query}")
    logger.info(f"Selected models: {selected_models}")
    
    # 各モデルの生成結果を格納
    results = []
    for full_model in selected_models:
        try:
            provider, model = full_model.split(":")
            logger.info(f"Generating code with {full_model}")
            
            if provider == "openai":
                code, preview = generate_openai(query, model)
            elif provider == "anthropic":
                code, preview = generate_anthropic(query, model)
            elif provider == "gemini":
                code, preview = generate_gemini(query, model)
            elif provider == "deepseek":
                code, preview = generate_deepseek(query, model)
            elif provider == "mistral":
                logger.warning(f"Mistral implementation pending for {full_model}")
                code, preview = f"// Mistral: API implementation pending for {full_model}", f"<div>Unknown provider for {full_model}</div>"
            else:
                logger.error(f"Unknown provider: {full_model}")
                code, preview = f"// Unknown provider: {full_model}", f"<div>Unknown provider for {full_model}</div>"
            
            results.append((full_model, code, preview))
            logger.info(f"Successfully generated code with {full_model}")
            
        except Exception as e:
            logger.error(f"Error generating code with {full_model}: {str(e)}")
            continue
    
    # 生成結果のグリッドHTMLを作成
    grid_html = """
    <style>
        .code-section {
            display: none;
        }
        .code-toggle {
            cursor: pointer;
            padding: 4px 8px;
            background: #eee;
            border: 1px solid #ddd;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.9em;
        }
        .code-toggle:hover {
            background: #e0e0e0;
        }
        .code-icon {
            width: 16px;
            height: 16px;
            display: inline-block;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z'/%3E%3C/svg%3E");
            filter: invert(1);
        }
    </style>
    <div style='height: 100vh; overflow-y: auto; padding: 20px;'>
        <div style='display: grid; grid-template-columns: repeat(1, 1fr); gap: 24px;'>
    """
    
    for full_model, code, preview in results:
        provider, model_name = full_model.split(":")
        model_id = f"model_{provider}_{model_name}".replace("-", "_")
        
        grid_html += f"""
            <div style='border: 1px solid #ccc; border-radius: 8px; overflow: hidden;'>
                <div style='background: #333; color: #fff; padding: 12px; border-bottom: 1px solid #ccc;'>
                    <div style='font-size: 1.2em; margin-bottom: 4px;'>
                        <strong>Provider:</strong> {provider.upper()}
                    </div>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <strong>Model:</strong> {model_name}
                        </div>
                        <button class="code-toggle" onclick="(function(el, id){{ var cs = document.getElementById(id + '_code'); if(cs.style.display === 'none' || cs.style.display === '') {{ cs.style.display = 'block'; el.innerHTML = '<span class=&quot;code-icon&quot;></span>Hide Code'; }} else {{ cs.style.display = 'none'; el.innerHTML = '<span class=&quot;code-icon&quot;></span>Show Code'; }} }})(this, '{model_id}')">
                            <span class="code-icon"></span>Show Code
                        </button>
                    </div>
                </div>
                <div style='display: flex; flex-direction: column;'>
                    <div id='{model_id}_code' class='code-section' style='flex: 1; padding: 16px; border-bottom: 1px solid #eee;'>
                        <div style='font-weight: bold; margin-bottom: 8px;'>Generated Code:</div>
                        <pre style='margin:0; background: #f8f8f8; padding: 12px; border-radius: 4px; overflow-x: auto;'>{code}</pre>
                    </div>
                    <div style='flex: 1; padding: 16px;'>
                        <div style='font-weight: bold; margin-bottom: 8px;'>生成LLM: {full_model}</div>
                        <div style='font-weight: bold; margin-bottom: 8px;'>Preview:</div>
                        <div style='overflow-x:auto;'>{preview}</div>
                    </div>
                </div>
            </div>
        """
    
    grid_html += """
        </div>
    </div>
    """
    
    logger.info(f"Completed generation request for {len(results)} models")
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