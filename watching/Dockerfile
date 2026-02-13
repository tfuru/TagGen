FROM python:3.11-slim

WORKDIR /app

# 依存ライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
# COPY ./app /app

# アプリケーションの起動
CMD ["python", "main.py"]