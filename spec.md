# 東証上場 ETP 一覧サイト 仕様

東証上場 ETF のカテゴリ別一覧を GitHub Pages で公開し、GitHub Actions で定期自動更新する静的サイト。構成は `/home/masasikatano/project/dsbd/` をテンプレートにする。

## 決定事項（grilling による合意）

1. **データソース**
   - JPX の ETFデータベース xlsx を正（master）とする。GitHub Actions で定期ダウンロードし差し替える。
   - xlsx の href はページ依存（例: `/equities/products/etfs/investors/tvdivq0000005cdd-att/nlsgeu000000vx9t.xlsx`）のため、更新時は `https://www.jpx.co.jp/equities/products/etfs/investors/index.html` を取得して `.xlsx` の href を動的に抽出する。ハードコードしない。
   - xlsx は原則年1回（年末時点）＋新規上場/上場廃止時に随時更新。`最終更新日` が変わったら即差し替え。
   - **価格は Yahoo Finance（主）と J-Quants（フォールバック）**。
     - Yahoo: `query1.finance.yahoo.com/v8/finance/chart/{4桁コード}.T?interval=1d&range=5d`。終値・前日比は close 配列の最後の2点から `(P_n/P_{n-1}-1)*100` で自前計算する（`meta.regularMarketChangePercent` は使わない）。
     - J-Quants: Yahoo で取得失敗した銘柄のみ、日次バーのウィンドウ（Free 版は「12週間前〜17週間前」）の最後の2営業日の close で同様に算出して埋める。日次バー全体は latest.json に保持しない。

2. **更新スケジュール**
   - 日次。平日の固定時刻に Actions を回し、(a) Yahoo Finance から価格取得（J-Quants フォールバック）、(b) xlsx の差分チェック＆差し替え。
   - `[skip ci]` 付きで main に push（dsbd 同様）。時刻は JST 夕方〜夜を推奨。

3. **詳細ページ**
   - **詳細ページは削除する**（2026-10 決定）。一覧テーブルのみ。xlsx の全列は `fields` として latest.json に保持するが表示はしない（将来の復活に備えデータは残す）。

4. **データファイル構成**
   - 単一 `docs/data/latest.json`。銘柄マスタ（xlsx 全列）＋ 各銘柄の価格 `{ close, change_pct, as_of }` の最小形。日次バーは含めない。

5. **一覧ページ機能**
   - カテゴリタブ（12カテゴリ）のみのシンプル一覧。検索・ソートはつけない。

6. **構成・技術**
   - dsbd 同型の独立リポジトリ（etp/ を git init）。
   - Pages: branch `main` の `/docs`。バニラ JS（index.html / common.js。detail.html は削除済み）、Python パイプライン（`python -m src.update`）、pytest、run_local.sh、AGENTS.md、requirements.txt、`.github/workflows/update.yml`。
   - カテゴリ（xlsx「カテゴリー」列、計454銘柄）: 外国株110 / 日本株（テーマ別）86 / 外国債券61 / 日本株（市場別）36 / 不動産（REIT)36 / レバレッジ型・インバース型36 / 国内債券20 / 商品(外国投資法人債券)19 / 日本株（業種別）18 / 商品・商品指数17 / エンハンスト型12 / 日本株（規模別）3

7. **価格データソースの扱い（重要）**
   - Yahoo Finance を主とし、取得失敗した銘柄は J-Quants でフォールバックする。それも失敗・未対象銘柄は行を残し「データなし」表示（dsbd 同方針）。
   - Yahoo は銘柄コードに `.T` を付与（例: 1306 → 1306.T）。銘柄ごとの除外が必要な場合は `src/yahoo.py` の `YAHOO_EXCLUDE` で管理する。
   - 終値・前日比はいずれのソースでも close の最後の2点から自前計算する（前日比% = (P_n/P_{n-1}-1)*100）。Yahoo の `meta.regularMarketChangePercent` は使わない。
   - 出来高は終値と同じ基準日のものを使う（Yahoo は `indicators.quote.volume` の最終ポイント、J-Quants は最終営業日の `Volume`）。取得できなければ `volume: null` で表示は「—」。
   - 表示はサイトの免責表現として「参考値（YYYY-MM-DD時点）」と必ず明記する（Yahoo の最新終値も含めて）。
   - J-Quants の code は5桁（例: 86970）、xlsx は4桁（8697）→ 先頭4桁で突合。
   - J-Quants APIキーはリポジトリ secret（`JQUANTS_API_KEY`）か `.env`。ログ・JSON に出さない。未設定でもジョブは成功（その場合フォールバックは「データなし」）。
   - J-Quants Free版の取得ウィンドウは「12週間前〜17週間前」の固定オフセット。フォールバックで埋めた銘柄はこの期間の過去値になる。

## 残リスク・注意

- Yahoo Finance のレート制限・レスポンス変更（リトライ＋リクエスト間隔で対処。除外銘柄は `YAHOO_EXCLUDE`）。
- J-Quants Free版のレート制限（フォールバックは Yahoo の失敗銘柄のみに絞るため従来よりリクエストは減る。リトライ＋バックオフ）。
- xlsx 列構成が JPX 側で変わった場合の検知（列名マッピングのテストで防ぐ）。
- 有料プランに戻した場合は `src/jquants.py` のウィンドウ計算を差し替えるだけで最新値表示に切替可能な構造にする。
