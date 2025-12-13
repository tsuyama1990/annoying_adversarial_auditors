# Autonomous Development Template

AIネイティブ開発へようこそ。このテンプレートは、`uv` による高速なパッケージ管理と、`Jules CLI` によるAI自律開発フローを統合したPythonプロジェクトの雛形です。

## 前提条件 (Prerequisites)

- **Python**: 3.12以上
- **uv**: パッケージマネージャー (https://github.com/astral-sh/uv)
- **Jules CLI**: AIエージェントインターフェース (`@google/jules`)
  - `jules login` で認証済みであること。

## セットアップ (Setup)

依存関係のインストール:
```bash
uv sync
```

## ワークフロー (Workflow)

### 1. 契約駆動開発 (Contract-Driven Development)
`contracts/schemas.py` がこのプロジェクトの Single Source of Truth です。
データ構造を変更する場合は、まずこのファイルを修正してください。

### 2. テストの自動生成
スキーマを定義したら、AIにテストを生成させます。

```bash
./scripts/ai_gen_test.sh
```
これにより、`tests/property/` 配下にHypothesisを使用したプロパティベーステストが生成されます。

### 3. 実装と修正の自律ループ
テストを実行し、失敗した場合はAIに自動修正を依頼できます。

通常実行:
```bash
uv run pytest
```

自動修正ループ (AI Auto-fix):
```bash
./scripts/ai_fix.sh
```
このスクリプトは、テストの失敗ログをJulesに送信し、修正案の適用を試みます。

## ディレクトリ構造

- **contracts/**: Pydanticモデル定義。
- **documents/**: AIへのコンテキスト提供用ドキュメント (PRD, ADR, 規約)。
- **scripts/**: AI連携用自動化スクリプト。
- **tests/property/**: 自動生成されるプロパティベーステスト。

Happy Coding with AI Agents!
