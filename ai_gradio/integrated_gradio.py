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
        # OpenAI APIキーの取得
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        client = OpenAI(api_key=api_key)
        
        # OpenAI API 呼び出し
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes code."},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=512,
            stream=False
        )
        
        response_text = response.choices[0].message.content
        code = remove_code_block(response_text)
        preview = send_to_preview(code)
        logger.info("Successfully completed OpenAI generation")
        return code, preview
    except Exception as e:
        logger.error(f"Error in OpenAI generation: {str(e)}")
        err = f"Error in OpenAI: {str(e)}"
        return err, f"<div style='padding: 8px;color:red;'>{err}</div>"

def generate_anthropic(query, model):
    try:
        # Anthropic APIキーの取得
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        # Anthropic API 呼び出し
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"Please write code for: {query}"
            }],
            system="You are an expert programmer. Write clean, efficient code."
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
        # Google API キーの取得
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Geminiモデルの初期化
        model = genai.GenerativeModel(model_name=model)
        
        # プロンプトの設定と生成
        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": "You are an expert programmer. Write clean, efficient code."}]},
                {"role": "model", "parts": [{"text": "I understand. I will help you write clean, efficient code."}]},
                {"role": "user", "parts": [{"text": query}]}
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
    encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    return f'<iframe src="{data_uri}" width="100%" height="480px"></iframe>'

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
    grid_html = "<div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;'>"
    for full_model, code, preview in results:
        grid_html += (
            "<div style='border: 1px solid #ccc; border-radius: 4px; overflow: hidden;'>"
            "  <div style='background: #f5f5f5; padding: 8px; text-align: center;'>"
            f"    <strong>{full_model}</strong>"
            "  </div>"
            "  <div style='display: flex;'>"
            "    <div style='flex: 1; border-right: 1px dashed #aaa; padding: 8px; overflow: auto;'>"
            f"      <pre style='margin:0;'>{code}</pre>"
            "    </div>"
            "    <div style='flex: 1; padding: 8px; overflow: auto;'>"
            f"      {preview}"
            "    </div>"
            "  </div>"
            "</div>"
        )
    grid_html += "</div>"
    
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
                    value=[INTEGRATED_MODELS[0]],
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