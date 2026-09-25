# ORDER EXCHANGE TIME-VALUE TRANSACTION DESIGN NOTES 3

## 本メモの位置づけ

- 本ファイルは `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md` の継続版。詳細設計メモ第3巻。
- 第1巻・第2巻は削除、移動、置換しない。旧メモは歴史的記録として維持する。
- 2026-09-26以降の詳細設計と実装結果は、原則として本ファイルへ追記する。新しいチャットでは本ファイルを先に読む。
- 最新現在地は `ORDER_EXCHANGE_PROGRESS_2.md` で確認する。過去経緯は旧設計メモの該当箇所を検索する。旧設計メモ全文を毎回同時に読み込ませない。
- 実装済み事実は実コードとテストを最終確認対象とする。最新正本として明記された新しい節を、矛盾する古い未実装記録より優先する。

## 文書保守方針

- 過去の設計判断・実装状態・未解決事項・当時の再開地点は原則削除しない。古い記録と最新が異なる場合は更新注記と最新参照先で整理する。
- 歴史的記録を推測で復元・書換えしない。実装前仕様と実装結果を区別する。Cursorの報告だけで実装完了と確定しない。
- 実コード、専用テスト、回帰、差分、Git状態、独立確認を根拠にする。各節目で詳細設計メモと最新進捗メモへの反映要否を確認する。
- Git操作は利用者がTerminalで行う。commitとpushを分ける。メモを含むコミット名には `document` を含める。
- `diagnostics/order_control.zip` は対象外。文献調査とコーディング進捗を混同しない。

## 旧詳細設計メモとの関係

- 第1巻: `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`
- 第2巻: `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`
- 第3巻: 本ファイル

第1巻・第2巻は第3巻開始前の詳細設計・実装履歴。第3巻は2026-09-26以降の詳細設計・実装結果の最新本流。旧メモ本文を第3巻へ移動しない。旧メモへ同じ実装結果を大量重複追記しない。最新仕様は第3巻を先に読む。今回は旧設計メモへ移行注記を追加しない（独立確認後に別作業で検討）。

## 第3巻開始時のGit状態

- 作成日: 2026-09-26。作業ブランチ: `feature/intersection-order-control`
- 最新保存済み・push済み: `5cde1aa` — document pre-implementation specification for TVT-MP candidate selection。HEADと `origin/feature/intersection-order-control` は一致。
- `ORDER_EXCHANGE_PROGRESS.md` に第2巻への短い移行注記が未コミットで追加済み。`ORDER_EXCHANGE_PROGRESS_2.md` は新規未追跡。
- 候補選択: `uxsim/order_control_tvt_mp_candidate_selection.py`、`tests_order_control_tvt_mp_candidate_selection.py` は新規未追跡。`diagnostics/order_control.zip` は既存未追跡。
- 第3巻作成時点で git add、commit、push は未実行。

## 第3巻開始時の現在地

**主対象:** TVT-MP、複数ネットワーク・OD需要、右左折あり、単車線、時間価値取引型交差点管理。

**重要原則:** Case III不使用。strategy-proofness未証明。正しいVOT申告を前提。不参加は `participates_in_order_exchange=False`。VOT=0は合法で不参加の代理にしない。TVT-MP一般形を直接実装。非参加Visitあり・なしを一般形で扱う。成立候補選択は surplus 最大 → surplus同値なら buyer 数最大 → 最終同値のみ局所RNG。traffic RNGと order-control 再訪RNGを候補選択で消費しない。

**実装済み主処理（列挙のみ）:** candidate Visit整理、inlink別snapshot物理順、具体的買い手候補集合、一般形順位再構成、FIFO検査接続、局所拘束順位列、候補別局所仮想計算、全候補局所仮想計算集合、経済性評価、成立候補選択。

## 旧メモの主要参照索引

| 主題 | 参照先 |
| --- | --- |
| TVT-MP一般形、非参加Visit、prefix、trade_scope、一般形順位再構成 | `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md` |
| FIFO検査接続、局所拘束順位列、候補別局所仮想計算 | 同上 |
| 経済性評価、VOT=0、G_b、R_s、G、R、surplus | 同上 |
| 成立候補選択の完全実装前仕様 | 同上（commit `5cde1aa`） |
| 最新進捗要約 | `ORDER_EXCHANGE_PROGRESS_2.md` |
| 切替前の詳細進捗履歴 | `ORDER_EXCHANGE_PROGRESS.md` |

# TVT-MP成立候補選択部品・実装結果

**記録日: 2026-09-26**

## 位置づけ

保存済み実装前仕様: commit `5cde1aa`、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md` の「TVT-MP成立候補選択部品・完全実装前仕様」。経済性評価結果の feasible 候補から Node ごとに最大1件を選ぶ。payment・compensation・最終順位・実World反映は対象外。

## 新規ファイルと公開要素

| 区分 | パス |
| --- | --- |
| 本番 | `uxsim/order_control_tvt_mp_candidate_selection.py` |
| 専用テスト | `tests_order_control_tvt_mp_candidate_selection.py` |

**Enum** `OrderControlTvtMpCandidateSelectionStatus`: `SELECTED` = `"selected"`、`NO_ECONOMICALLY_FEASIBLE_CANDIDATE` = `"no_economically_feasible_candidate"`。

**Node結果** `OrderControlTvtNodeMpCandidateSelectionResult`（frozen）— `node_name`、`selection_status`、`selected_candidate_economic_result`、`rng_was_used`。

**全体結果** `OrderControlTvtMpCandidateSelectionSetResult`（frozen）— `economic_evaluation_set_result`、`node_candidate_selection_results`（tuple）。

**API** `select_tvt_mp_candidates(economic_evaluation_set_result, real_W)` — 位置引数2つ、全Node一括、公開関数はこれのみ。入力 economic set と selected は同一object参照。selected flag の後書きなし。

## 選択単位と正式選択順

Nodeごとに最大1候補（全Node横断1件ではない）。入力Node順を維持し、公開候補列を再ソートしない。

1. `economically_feasible is True` のみ
2. 保存済み surplus 最大
3. 同値なら `len(buyer_economic_records)` 最大
4. surplus と buyer 数が同じ候補が2件以上なら局所一時RNGで1件

## feasible候補の抽出と整合確認

入力順の明示的forループ。economic evaluation再実行なし。unresolved・FIFO Falseは入力に無く選択しない。infeasibleも基本自己整合を確認（strict bool、reasons tuple、surplus有限かつ `G-R` 一致、buyers_sortedとVisitKey集合一致・重複なし）。feasibleは reason 空、buyer≥1、全 `G_b>0`、`G>=R`。

## surplus比較

保存済み surplus の完全比較。再計算・丸め・tolerance・Decimalなし。明示ループで最大値と完全一致候補を集める。

## buyer数比較

正本 `len(buyer_economic_records)`。surplus最大が複数のときのみ第二比較。seller数・当事者総数・trade scope等は使わない。buyer件数と `buyers_sorted` 件数一致を確認。

## candidate identity

`(node_name, buyers_sorted)`。VisitKeyは `(vehicle_name, visit_id)`。id・列挙index・`hash()`・曖昧連結は使わない。同一Node内重複は `RuntimeError`（重複除去継続しない）。`candidate_id` field は追加しない。

## 最終同値候補の決定論的整列

同値2件以上のみ。identityとcandidate objectの組をidentityで整列。同一object参照を維持。RNG母集団のみ使用。公開結果・入力列は変更しない。

## 選択専用局所RNG

`numpy.random.SeedSequence` と `default_rng`。最終同値2件以上のみ関数内構築。`real_W.rng`・`order_control_rng`・第三永続RNG・state保存復元は使わない。結果へ保存しない。

## seed材料

存在フラグ付き `random_seed`（None時はフラグのみ）、`T`、Node名、同値件数、整列済みidentity（候補件数・buyer件数・UTF-8長さ付きbytes・`visit_id` int）。整数列を `SeedSequence(entropy=...)` に渡す。負整数の暗黙unsigned変換なし。`hash()`・id・単純連結・pickle・外部hash・新規依存なし。

## RNG使用条件と非使用条件

**使用:** surplusとbuyer数が同じ最終同値が2件以上 → `rng_was_used=True`。

**非使用:** feasible 0/1件、surplusまたはbuyer数で単独最大、Node空、全infeasible。選択あり単独最大は `SELECTED`・`rng_was_used=False`。候補なしは `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`・selected `None`・`rng_was_used=False`（正常、例外でない）。

## RNG不変性

`rng`・`order_control_rng`（各bit generator state）、`random_seed`、`T`、`TIME`、交通・Vehicle・payment台帳・経済・局所・FIFO・collector・rank stateを変更しない。既存RNGを参照・使用しない。

## 候補列挙順およびNode処理順からの独立性

同値候補をidentity整列後にRNG母集団化。入力候補列順を変えても同じidentity。Nodeごとに局所RNG（seedにNode名）。Node列順を変えても各Nodeの当選identityは変わらない。

## selection statusと候補なし

`SELECTED`: selected非None、入力同一object、`rng_was_used` strict bool。`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`: selected `None`、`rng_was_used=False`。status矛盾は `RuntimeError`。

## 重大不整合と部分結果

外部入力不正: `ValueError`（型、`random_seed`、`T`）。保存済み矛盾: `RuntimeError`（Node/候補型・feasible/reason・surplus・buyer集合・identity重複・RNG index・status矛盾等）。正常な候補なしは `RuntimeError` にしない。1Node不整合で全体停止、後続Node未処理、部分overallなし、rollbackなし、入力・実World・RNG不変。

## 責務境界

未実装: payment、compensation、P_b配分、seller実補償、payment台帳更新、最終順位列、baseline fallback、情報未解決確定、formal route、順位台帳、確定ブロック接続、実World反映、actual、utility/welfare、上位driver、strategy-proofness。結果に payment・compensation・final rank・actual field なし。

## 可読性

正しさ最優先。明示的Node/candidateループ、feasible・maximum surplus・maximum buyerの明示list/走査、小さなprivate helper、seed符号化の分離。多段max one-liner、generator、`hash()`、id、World RNG、並列・キャッシュ、payment/final rank 混入なし。

## 専用テスト・回帰・静的確認

専用35件（直接35 passed、pytest 35/35 collected、TESTS 35、重複・漏れ・未定義参照なし）。py_compile 新規2ファイル成功。関係回帰: 指定7ファイル **366 passed**、baseline driver/downstream boundary **121 passed**（区分記録）。静的: 経済評価・局所計算・FIFO再実行なし、`hash()`/id/World RNG/RNG state保存復元なし、payment/compensation/final rank/actual/実World書込みなし。独立確認: 仕様整合、追加修正不要。全pytest・GUI・性能テストは未実行。

## 独立確認結果

新規本番と専用テストを確認。surplus→buyer数→最終同値RNG、局所RNGのみ、RNG不変、identity・列挙順/Node順独立、候補なし正常、同一object参照、責務外未実装を確認。**追加修正不要**。

## 実装完了範囲

selection status、Node/全体frozen結果、一括API、feasible抽出、surplus・buyer数最大抽出、identity・重複検出、deterministic整列、seed材料、局所RNG、最終同値選択、RNG非使用、候補なし正常、RNG不変性、順序独立、重大不整合・部分結果なし、専用テスト、関係回帰、独立確認。

## 未実装範囲

payment、compensation、配分・台帳更新、最終確定各種、formal route、順位台帳、実World・actual、utility/welfare、上位driver、strategy-proofness、文献移植。API・型・配分規則・処理順は本節で新規確定しない。

## 次の再開地点

1. 候補選択コード、専用テスト、進捗第1巻の移行注記、進捗第2巻、詳細設計第2巻の移行注記、本第3巻を同一保存単位でcommitする。
2. commit結果、最新コミット、残存変更を確認する。
3. 別の指示でpushし、push後の状態を確認する。
4. 保存後に最新進捗と最新設計を再確認する。
5. 未実装領域から次の設計対象を選ぶ。

payment、compensation、最終順位確定は未実装として残る。今回の文書更新だけで、次の設計対象は確定しない。
