import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging():
    """ロギングの設定を行う"""
    # ログディレクトリの作成
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ログファイル名の設定（日付を含む）
    log_file = os.path.join(log_dir, f"ai_code_generator_{datetime.now().strftime('%Y%m%d')}.log")
    
    # ロガーの設定
    logger = logging.getLogger('ai_code_generator')
    logger.setLevel(logging.INFO)
    
    # ファイルハンドラーの設定（ローテーション付き）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # フォーマッターの設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # ハンドラーの追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 