# TagGen
MP3ファイルを解析・タグ付け と 検索API アプリを コンテナ 環境

## 概要
1. musicフォルダ内のMP3ファイルが保存されると解析して、タグ情報を取得 DBに保存する
2. DBから検索APIで検索

## 構成
- FastAPI
- SQLite
- Gemini API

## 実行方法
```bash
podman compose up --build
```

### 検索API 実行例
```bash
# "街の道路" を検索
curl "http://localhost:9000/search?q=街の道路"

# 全件検索（"mp3"などを含むもの）
curl "http://localhost:9000/search?q=mp3"
```

### 検索API レスポンス仕様

**エンドポイント:** `GET /search`

**パラメータ:**
- `q`: 検索クエリ (自然言語対応)

**レスポンス例:**

```json
{
  "results": [
    {
      "id": 1,
      "filename": "example.mp3",
      "title": "Quiet Morning",
      "artist": "Nature",
      "album": "Soundscapes",
      "genre": "Ambient",
      "year": "2024",
      "comment": "A peaceful morning sound with birds chirping.",
      "playback_url": "http://localhost:9000/music/example.mp3"
    }
  ]
}
```

- `playback_url`: 音声ファイルを再生するための直リンク (フルパス)
