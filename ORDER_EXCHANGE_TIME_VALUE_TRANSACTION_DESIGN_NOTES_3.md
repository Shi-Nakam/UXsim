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

# TVT-MP payment・compensation計算部品・完全実装前仕様

**記録日: 2026-09-26**

本節は完全実装前仕様である。Python実装と専用テストは未着手である。Cursorの報告だけで実装完了としない。実装後は実コード、専用テスト、差分、Git状態、独立確認を根拠にする。

成立候補選択部品はcommit `2e67ae0` で実装・検証・保存済みである。本部品は、Nodeごとに選択された最大1件の候補について、buyer支払額とseller補償額を計算する純計算部品である。Vehicle金銭台帳、final rank、実World反映は対象外である。

新しい制度判断は追加しない。次の制度原則は再検討または未確定へ戻さない。

## 1. 位置づけと予定ファイル

本部品は candidate selection の直後に置く。入力は選択結果だけである。出力は新しいfrozen結果だけである。

| 区分 | パス |
| --- | --- |
| 新規本番予定 | `uxsim/order_control_tvt_mp_payment_and_compensation.py` |
| 新規専用テスト予定 | `tests_order_control_tvt_mp_payment_and_compensation.py` |

既存の経済性評価モジュール、候補選択モジュール、それらの専用テスト、既存結果型は変更しない。

## 2. 制度原則

- buyer支払総額は、seller側必要補償総額 `R` である。
- 各buyer `b` の支払額は `P_b = R * G_b / G` である。
- 各seller `s` の補償額は、上流経済性評価で計算済みの `R_s` である。
- seller補償総額は `R` である。制度上、buyer支払総額とseller補償総額はともに `R` である。
- sellerへ追加的な金銭surplusを配らない。
- `surplus = G - R` は制度主体が保持する金銭残高ではない。
- paymentとcompensationは予測値に基づいて事前確定する。
- actual passage結果に基づく事後精算は行わない。
- strategy-proofnessは未証明である。

sellerの予想通過時刻がbaselineと同じ、または早い場合:

- `compensation_amount` は 0 である。
- seller自身の支払額も 0 である。
- sellerのroleを維持する。
- buyerへ変更しない。
- sellerの時間短縮価値を `G` へ加えない。
- 早期通過sellerは、支払いなしで時間短縮の交通上の便益を得る。

これらの帰結は、上流経済性評価が `expected_waiting_increase = max(raw_diff, 0)` により `R_s = 0` を保存済みであることに依る。本部品は `compensation_amount = R_s` とするだけで、seller roleを変更しない。

## 3. 数値契約

- 各 `payment_P_b` は `P_b = R * G_b / G` で個別計算する。
- floatを使用する。
- 内部で丸めない。
- toleranceを使わない。
- Decimalを使わない。
- 最後のbuyerへ残差を割り当てない。
- buyer順を金額補正へ利用しない。
- `sum(P_b)` と `R` のbit単位一致を重大不整合条件にしない。
- `payment_P_b` と `G_b` のごく小さなfloat差を直ちに重大不整合にしない。
- 数値表現上の実問題が確認された場合だけ、Tolerance、Decimal、または別の残差方式を再検討する。
- 経済的成立判定 `G >= R` は上流の既存契約である。本部品はそれを再定義しない。

上流から受け取った保存値については、本部品が直接利用する材料として次を確認する。

- 保存済み `G` と、buyerの `G_b` を明示的forループで加算した値が完全一致する。
- 保存済み `R` と、sellerの `R_s` を明示的forループで加算した値が完全一致する。

経済性評価や候補選択を再実行しない。

成立候補では全 `G_b > 0` のため `G > 0` である。したがって `P_b` のゼロ除算は発生しない。`R = 0` なら全 `payment_P_b = 0` となる。`G = R` なら式上 `P_b = G_b` である。`G > R` なら式上 `P_b < G_b` である。これらをbit単位の公開不変条件にはしない。

## 4. 実装境界と入力

入力は次だけである。

- `OrderControlTvtMpCandidateSelectionSetResult`

`real_W` は受け取らない。Vehicle検索は行わない。選択結果から次へ到達できる。

- `G_b`
- `R_s`
- `G`
- `R`
- buyerとsellerのVisitKey
- `vehicle_name`
- selected candidate
- Node名
- economic evaluation set result

VisitKeyは `(vehicle_name, visit_id)` である。identity保持に `real_W` は不要である。

本部品は純計算だけを行い、新しいfrozen結果を返す。

変更しない:

- selection result
- economic evaluation result
- local result
- FIFO result
- collector
- rank state
- Vehicle
- `Vehicle.payment_paid`
- `Vehicle.payment_received`
- `Vehicle.order_exchange_log`
- real World
- RNG

既存の `OrderControlTvtMpBuyerEconomicRecord`、`OrderControlTvtMpSellerEconomicRecord`、`OrderControlTvtMpCandidateEconomicEvaluationResult`、候補選択結果型へ payment / compensation field を追加しない。economic resultへselected flagを後書きしない。

## 5. 公開Enum

`OrderControlTvtMpPaymentAndCompensationStatus`

- `CALCULATED = "calculated"`
- `NO_SELECTED_CANDIDATE = "no_selected_candidate"`

`SETTLED` / `NO_SETTLEMENT` は使わない。実Worldへの金銭反映と誤読されるためである。selection statusを本部品のNode結果へ複写しない。候補なしの詳細原因は、入力selection resultの参照連鎖から確認する。

## 6. 公開frozen型

すべて `dataclass(frozen=True)`。公開の順序付き列は `tuple`。入力resultとselected candidateは同一object参照を維持する。live World、Vehicle、Node、Link、RNG、mutable list、mutable dict を保持しない。件数fieldを置かない。

### 6.1 buyer record

`OrderControlTvtMpBuyerPaymentRecord` — field順:

1. `visit_key`
2. `vehicle_name`
3. `payment_P_b`

`payment_P_b` は本部品の計算結果である。`G_b` は入力経済recordから取得し、本recordへ複写しない。

### 6.2 seller record

`OrderControlTvtMpSellerCompensationRecord` — field順:

1. `visit_key`
2. `vehicle_name`
3. `compensation_amount`

`compensation_amount` は、選択された経済結果に保存された `required_compensation_R_s` と同額とする。これは本部品が確定する実補償額であり、経済評価の留保額 `required_compensation_R_s` とはfield名を分ける。`actual_compensation` というfield名は使わない。actual passageに基づく事後値と誤読されるためである。`R_s` 自体は本recordへ複写しない。

### 6.3 Node結果

`OrderControlTvtNodeMpPaymentAndCompensationResult` — field順:

1. `node_name`
2. `payment_and_compensation_status`
3. `selected_candidate_economic_result`
4. `buyer_payment_records`
5. `seller_compensation_records`

Nodeごとにselected candidateは最大1件である。`selected_candidate_economic_result` は、入力Node選択結果のselectedと同一objectとする。候補なしでは `None` とする。

### 6.4 全体結果

`OrderControlTvtMpPaymentAndCompensationSetResult` — field順:

1. `candidate_selection_set_result`
2. `node_payment_and_compensation_results`

`candidate_selection_set_result` は入力と同一object参照である。`node_payment_and_compensation_results` は入力selectionのNode順を維持するtupleである。

## 7. 公開API

```python
def calculate_tvt_mp_payments_and_compensations(
    candidate_selection_set_result,
) -> OrderControlTvtMpPaymentAndCompensationSetResult:
```

- 位置引数1つ
- `real_W` なし
- 全Node一括
- Node単位公開APIなし
- buyer、seller単位公開APIなし
- tolerance、Decimal、rounding、外部rule引数なし
- mutable stateなし
- 部分的overall resultを返さない

関数名に `settle` を使わない。純計算であり、実Worldへ金銭を反映する処理ではない。

## 8. 候補なしNode

selected candidateがない場合は正常結果であり、例外ではない。

- `payment_and_compensation_status` は `NO_SELECTED_CANDIDATE`
- `selected_candidate_economic_result` は `None`
- `buyer_payment_records` は空tuple
- `seller_compensation_records` は空tuple
- 0額recordを作らない
- Node結果は省略しない。全体結果から当該Nodeを落とさない

入力の `selection_status` が `NO_ECONOMICALLY_FEASIBLE_CANDIDATE` であることと、selectedが `None` であることを対応確認する。候補なしを重大不整合へ変換しない。

## 9. 保存する値

- buyerの `visit_key`
- buyerの `vehicle_name`
- `payment_P_b`
- sellerの `visit_key`
- sellerの `vehicle_name`
- `compensation_amount`
- Node status
- selected economic resultの同一参照
- input selection setの同一参照

## 10. 保存しない値

- `G_b` の複写
- `R_s` の複写
- `payment_share`
- `expected_net_benefit`
- buyerまたはsellerのutility
- 早期通過flag
- `total_buyer_payment`
- `total_seller_compensation`
- `institutional_balance`
- `sum(P_b)` の診断値
- rounding情報
- tolerance
- Decimal
- final rank
- actual passage
- Vehicle台帳
- live World
- RNG
- mutable listまたはdict

`sum(P_b)` と制度上の総額 `R` の関係、`G = R` 近傍の `P_b` と `G_b` の関係は、公開結果へ診断fieldを増やさず専用テストで確認する。

## 11. 処理順

明示的なNode、buyer、sellerのforループを使う。iterator、generator、並列実行は使わない。候補列、buyer列、seller列を不要に再ソートしない。buyerまたはsellerの順序を金額補正に使わない。

1. selection setの型を確認する
2. selection Node結果列とeconomic Node結果列の対応を確認する
3. Node順とNode名を確認する
4. selection statusとselected candidateの対応を確認する
5. selected candidateが当該Nodeの経済候補tuple内の同一objectであることを確認する
6. 候補なしなら `NO_SELECTED_CANDIDATE` 結果を作る
7. selected candidateがある場合は `G`、`R`、buyer records、seller recordsを確認する
8. buyer recordsを保存順に明示的forループで走査する
9. `payment_P_b = R * G_b / G` を個別計算する
10. seller recordsを保存順に明示的forループで走査する
11. `compensation_amount = R_s` とする
12. `CALCULATED` のNode結果を作る
13. 全Node完了後に全体結果を作る

seller空は合法である。seller record tupleが空、保存済み `R = 0`、全 `payment_P_b = 0`、seller compensation recordsは空tupleとする。

## 12. 重大不整合

外部入力型不正は `ValueError`。例: 公開入力が `OrderControlTvtMpCandidateSelectionSetResult` でない。

保存済み結果間または内部の重大不整合は `RuntimeError`。

主な確認対象:

- Node結果列の型
- Node件数、Node順、Node名
- statusとselected candidateの矛盾
- selected candidateの同一object契約
- selected candidateが `economically_feasible is True` であること
- `G` が正かつ有限
- `R` が非負かつ有限
- `G >= R`
- buyer recordsがtupleで1件以上
- seller recordsがtuple（空は合法）
- 各 `G_b` が正かつ有限
- 各 `R_s` が非負かつ有限
- 保存済み `G` と明示加算した `G_b` 合計の完全一致
- 保存済み `R` と明示加算した `R_s` 合計の完全一致
- 新しく計算した `payment_P_b` が有限かつ非負
- `compensation_amount` が有限かつ非負
- statusとrecord列の矛盾（`CALCULATED` なのにrecords空かつselectedなし、`NO_SELECTED_CANDIDATE` なのにrecords非空 など）

確認しない:

- `sum(P_b)` と `R` のbit単位一致
- `payment_P_b <= G_b` のbit単位完全比較
- toleranceによる補正
- Decimalによる再計算
- 残差配分
- 経済性評価の再実行
- 候補選択の再実行
- Vehicle欠落検査
- actual passageとの照合

1 Nodeの重大不整合で全体停止する。後続Nodeを処理しない。部分的overall resultを返さない。rollbackしない。入力selection result、経済結果、実Worldを変更しない。正常なcandidateなしを `RuntimeError` にしない。

## 13. 過剰検証を避ける方針

候補選択が比較材料として確認済みの事項を、同じ深さで全部やり直さない。本部品が直接利用する材料だけを確認する。

直接利用する材料: selection set型、Node対応、statusとselectedの対応、selectedの同一object、成立候補であること、`G`、`R`、各 `G_b`、各 `R_s`、保存済み合計と明示加算合計の一致、計算した `payment_P_b` と `compensation_amount` の有限かつ非負。

やり直さない例: surplus最大の再選択、buyer数比較、局所RNG、経済価値の再計算、VOT再読取、通過timestepの再計算。

## 14. final rankと実適用の境界

推奨処理順:

1. candidate selection
2. pure payment/compensation calculation
3. final rank construction
4. final consistency validation
5. rank stateとVehicle金銭台帳へのatomic application

金額計算はfinal rank前に行ってよい。計算結果はfrozenであり、後続のfinal rankが重大不整合で停止しても破棄できる。

`Vehicle.payment_paid`、`Vehicle.payment_received`、`Vehicle.order_exchange_log` の更新は、final rankと全体整合確認の成功後まで行わない。final rank確定前に不可逆な金銭反映を行わない。

`payment_paid` と `payment_received` は累積属性である。`order_exchange_log` は `list` である。これらの更新方法は後続のapply部品で定める。本部品は読取も書込もしない。

## 15. 責務外

今回の計算部品では実装しない。

- Vehicle金銭台帳更新
- `order_exchange_log` 更新
- final rank
- baseline fallback
- information unresolved時の最終確定
- formal route
- 順位台帳
- atomic apply
- 実World反映
- actual passage
- expectedとactualの比較
- prediction error
- realized utility
- ex-post welfare
- 上位TVT driver
- strategy-proofness検証
- 文献制度の移植

## 16. 可読性

正しさを最優先する。明示的forループ、意味のある中間変数、小さなprivate helper。責務を少なくとも次へ分ける。公開入力検証、Node対応確認、statusとselected確認、候補なし結果構築、成立候補の材料確認、`G_b`/`R_s` 明示加算、buyer payment計算、seller compensation転写、Node結果構築、overall結果構築。

避ける: 長い内包表記、複雑なgenerator、残差を最後のbuyerへ付けるone-liner、tolerance、Decimal、`hash()`、object id、並列、キャッシュ、入力変更、World参照、Vehicle台帳更新、final rankの混入。

## 17. 専用テスト契約

新規専用テストは `tests_order_control_tvt_mp_payment_and_compensation.py`。最低限次を固定する。

公開型: Enum memberとvalue、buyer/seller/Node/overall frozen、field順、公開列tuple、入力selection setと同一object、selectedと入力candidateの同一object、live object/RNG非保持、禁止fieldなし。

公開API: 正式関数名、位置引数1つ、`real_W` なし、Node単位・一候補・一台公開APIなし、mutable stateなし。

候補なし: status `NO_SELECTED_CANDIDATE`、selected `None`、両records空tuple、例外なし、0額recordなし。

計算: `P_b = R * G_b / G`、`compensation_amount = R_s`、buyer/seller保存順維持、再ソートなし、順序を補正に使わない。

数値: `R = 0` なら全 `P_b = 0`、seller空なら `R = 0`、内部丸めなし、toleranceなし、Decimalなし、最後のbuyerへ残差なし、`sum(P_b)` と `R` のbit一致を重大不整合にしない。

seller: 遅延では `compensation_amount = R_s` とする。同時刻・早期では `compensation_amount = 0` とする。sellerのroleは変更せず、早期通過flagも追加しない。遅延sellerでも、申告VOTが0であるため保存済み `R_s` が0の場合、`compensation_amount` は0とし、人工的に正値へ補正しない。

不変性: selection result、economic result、local result、FIFO、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、実World、RNG。

重大不整合: 入力型不正は `ValueError`。status矛盾、同一object違反、infeasible selected、`G <= 0`、非有限、`G < R`、buyer空、`G_b`/`R_s` 不正、保存済み合計と明示加算の不一致、1Node不整合で全体停止、partialなし、後続Node未処理。正常な候補なしは `RuntimeError` にしない。

責務外: Vehicle台帳更新なし、final rankなし、actualなし、strategy-proofness主張なし。

## 18. 実装範囲と実装対象外

実装範囲: 全Node一括の純計算API、Enum、buyer/seller/Node/overall frozen結果、候補なし正常結果、`P_b` 個別計算、`compensation_amount = R_s`、明示加算による `G`/`R` 材料確認、重大不整合時の全体停止、専用テスト。

実装対象外: Vehicle台帳更新、final rank、baseline fallback、formal route、順位台帳、atomic apply、実World交通反映、actual記録・比較、realized utility、ex-post welfare、上位TVT driver、strategy-proofness検証、文献制度の移植。

## 19. 反証して採用しない事項

- buyerから `G` 全額を徴収する
- buyerからsurplusを徴収する
- buyer数で均等割りする
- seller数で均等補償する
- sellerへ追加surplusを配る
- 早期通過sellerをbuyerへ変更する
- 早期通過sellerの価値を `G` へ加える
- 早期通過sellerへ支払義務を課す
- 最後のbuyerへfloat残差を押し付ける
- buyer順序でpaymentが変わる
- toleranceで支払額を補正する
- Decimalを導入する
- `sum(P_b)` と `R` のbit一致を重大不整合にする
- expected settlementをactual passageで事後精算する
- 計算時にVehicle台帳を更新する
- final rank確定前に不可逆な金銭反映を行う
- payment、compensation、final rank、applyを巨大関数へ混入する
- strategy-proofnessを証明済みとする
- 既存経済評価型または選択型へpayment fieldを追加する
- `real_W` を本APIへ追加する

## 20. 次の再開地点

1. 詳細設計第3巻と進捗第2巻を同一保存単位でcommitする。
2. commit結果、最新コミット、残存変更を確認する。
3. 別の指示でpushし、push後の状態を確認する。
4. 保存後に、本節へ従い新規本番 `uxsim/order_control_tvt_mp_payment_and_compensation.py` と専用テスト `tests_order_control_tvt_mp_payment_and_compensation.py` だけを実装する。
5. 実装後に独立確認する。

本節は完全実装前仕様である。Pythonと専用テストは未着手である。Vehicle台帳更新とfinal rankは実装しない。

## 21. 実装・検証結果（2026-09-26）

**記録日: 2026-09-26**

保存済み完全実装前仕様（本節 §1–§20、commit `1cc579f`）に従って実装・検証した。上記 §1–§20 は歴史的な実装前仕様として残す。最新の実装完了事実は本節 §21 を参照する。

### 21.1 新規ファイルと公開要素

| 区分 | パス |
| --- | --- |
| 本番 | `uxsim/order_control_tvt_mp_payment_and_compensation.py` |
| 専用テスト | `tests_order_control_tvt_mp_payment_and_compensation.py` |

**Enum** `OrderControlTvtMpPaymentAndCompensationStatus`: `CALCULATED` = `"calculated"`、`NO_SELECTED_CANDIDATE` = `"no_selected_candidate"`。

**buyer record** `OrderControlTvtMpBuyerPaymentRecord`（frozen）— field順: `visit_key`、`vehicle_name`、`payment_P_b`。

**seller record** `OrderControlTvtMpSellerCompensationRecord`（frozen）— field順: `visit_key`、`vehicle_name`、`compensation_amount`。

**Node結果** `OrderControlTvtNodeMpPaymentAndCompensationResult`（frozen）— `node_name`、`payment_and_compensation_status`、`selected_candidate_economic_result`、`buyer_payment_records`、`seller_compensation_records`（いずれもtuple）。

**全体結果** `OrderControlTvtMpPaymentAndCompensationSetResult`（frozen）— `candidate_selection_set_result`、`node_payment_and_compensation_results`（tuple）。

**API** `calculate_tvt_mp_payments_and_compensations(candidate_selection_set_result)` — 位置引数1つ、`real_W` なし、全Node一括、公開計算APIはこれのみ。入力 selection set と selected candidate は同一object参照。部分的overall resultを返さない。

### 21.2 buyer paymentとseller compensation

**buyer:** 各buyer `b` の `payment_P_b = R * G_b / G`。buyerごとに式どおり個別計算。buyer順による金額補正なし。最後のbuyerへの残差割当なし。

**seller:** 各seller `s` の `compensation_amount = required_compensation_R_s`（上流経済性評価の保存済み `R_s` を写す）。VOTや通過時刻から再計算しない。`actual_compensation` field は使わない。早期通過flagは追加しない。

**制度:** sellerへ追加的な金銭surplusを配らない。`surplus = G - R` は制度主体の金銭残高ではない。paymentとcompensationは予測値に基づく事前確定。actual passageによる事後精算なし。strategy-proofnessは未証明。

### 21.3 遅延seller

candidate passageがbaselineより遅いため、上流経済性評価で正の予想待ち増加が保存されている。その結果 `required_compensation_R_s`（`R_s`）が正となる場合、本部品は `compensation_amount = R_s` とする。VOTや通過時刻から再計算しない。

### 21.4 申告VOTが0の遅延seller

**原因:** 申告VOTが0であるため、予想待ち増加の秒数にかけても留保額は金銭0となる。上流経済性評価は `R_s = expected_waiting_increase_seconds * declared_vot_per_second` により、遅延があっても保存済み `R_s` を0とする。

**結果:** `compensation_amount` は0。人工的に正値へ補正しない。入力異常にしない。非参加へ変更しない。buyerへ変更しない。sellerのroleを維持する。

### 21.5 同時刻seller

**原因:** candidate passageとbaseline passageが同じため、予想遅延は0。上流で `expected_waiting_increase = 0`、保存済み `R_s = 0`。

**結果:** `compensation_amount` は0。seller自身の支払額も0。sellerのroleを維持する。

### 21.6 早期通過seller

**原因:** candidate passageがbaselineより早いため、補償対象となる予想遅延はない。上流で waiting increase を0にclipし、保存済み `R_s = 0`。

**結果:** `compensation_amount` は0。seller自身の支払額も0。sellerのroleを維持する。buyerへ変更しない。時間短縮価値を `G` へ加えない。支払いなしで時間短縮の交通上の便益を得る。早期通過flagは追加しない。

### 21.7 候補なしNode

selected candidateがない場合は正常結果。`payment_and_compensation_status` は `NO_SELECTED_CANDIDATE`。`selected_candidate_economic_result` は `None`。`buyer_payment_records` と `seller_compensation_records` は空tuple。例外にしない。0額recordを作らない。Node結果を省略しない。

### 21.8 数値契約

float。内部丸めなし。toleranceなし。Decimalなし。残差補正なし。最後のbuyerへの差額割当なし。buyer順による補正なし。保存済み `G` と buyerの `G_b` を明示forループで加算した値の完全一致、保存済み `R` と sellerの `R_s` を明示forループで加算した値の完全一致を確認する。`sum(P_b)` と `R` のbit単位一致を重大不整合にしない。`payment_P_b <= G_b` のbit単位完全比較を重大不整合にしない。数値表現上の実問題が確認された場合だけ代替方式を再検討する。

### 21.9 不変性

変更しない: candidate selection result、economic evaluation result、local virtual calculation result、FIFO result、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、real World、RNG、`vot_declared`、`vot_true`、`participates_in_order_exchange`。新しいfrozen結果だけを返す。

### 21.10 責務境界（今回未実装）

Vehicle金銭台帳更新、`order_exchange_log` 更新、final rank、baseline fallback、information unresolved時の最終確定、formal route、順位台帳、atomic apply、実World交通反映、actual passage、expectedとactualの比較、prediction error、realized utility、ex-post welfare、上位TVT driver、strategy-proofness検証、文献制度の移植。

金額計算はfinal rank前に行ってよい。Vehicle台帳更新とatomic applyは、final rankと全体整合確認の設計後に扱う。

### 21.11 独立確認で修正した専用テスト

初回専用テスト `test_three_equal_buyers_do_not_require_sum_of_payments_to_match_r_in_bits` に `assert summed_payments != 1.0 or summed_payments == 1.0` があった。値に関係なく常に成功するため、独立確認で問題として検出した。

**修正:** 常時成功条件を削除。テスト名を `test_three_equal_buyers_each_use_formula_without_residual_or_sum_bit_check` に変更。3人のbuyerについて各 `payment_P_b` が `R * G_b / G` であることを確認。最後のbuyerも同じ式を使い残差を割り当てないことを確認。本番が支払総額のbit単位一致を要求しないことを確認。floatの加算結果が1.0になるかに依存しない。

修正後、専用テスト36件は再検証済み。**追加修正不要**。

### 21.12 専用テスト・回帰・py_compile

| 項目 | 結果 |
| --- | --- |
| 専用テスト件数 | 36 |
| 直接実行 | 36 tests passed |
| pytest | 36 passed |
| pytest収集 | 36 collected |
| 定義済みtest関数 | 36 |
| TESTS登録 | 36（重複なし、登録漏れなし、未定義参照なし） |
| py_compile | 新規本番・新規専用テストとも成功 |

**TVT-MP関係回帰**（同一実行で8ファイル）: **437 passed**

- 新規専用テスト: 36
- その他のTVT-MP関係テスト: 401

対象: `tests_order_control_tvt_mp_payment_and_compensation.py`、`tests_order_control_tvt_mp_economic_evaluation.py`、`tests_order_control_tvt_mp_candidate_selection.py`、`tests_order_control_tvt_mp_local_virtual_calculation_set.py`、`tests_order_control_tvt_mp_candidate_local_virtual_calculation.py`、`tests_order_control_tvt_mp_fifo_inspection.py`、`tests_order_control_tvt_mp_general_trade_rank.py`、`tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`。

**baseline関係回帰:** `tests_order_control_baseline_driver.py` と `tests_order_control_baseline_downstream_boundary.py` — **121 passed**（437と合算値だけへまとめない）。

全pytest、GUI、デモ、長時間性能テストは実行していない。

### 21.13 独立確認結果

保存済み完全実装前仕様と整合。純計算、`real_W` なし、式どおりのbuyer payment、保存済み `R_s` のseller compensation、申告VOT=0遅延seller・同時刻・早期通過の因果、候補なし正常、float契約、不変性、Vehicle台帳非更新、専用テスト修正を確認。**追加修正不要**。

### 21.14 実装完了範囲

Enum、buyer/seller/Node/全体frozen結果、一括公開API、候補なし正常、`P_b` 個別計算、`compensation_amount = R_s`、保存済み `G`/`R` と明示加算合計の確認、重大不整合時の全体停止・部分結果なし、専用テスト、TVT-MP関係回帰、baseline関係回帰、独立確認。

### 21.15 未実装範囲

Vehicle金銭台帳更新、final rank、baseline fallback、formal route、順位台帳、atomic apply、実World交通反映、actual記録・比較、realized utility、ex-post welfare、上位TVT driver、strategy-proofness検証、文献制度の移植。

### 21.16 次の再開地点

1. 実装コード、専用テスト、詳細設計第3巻、進捗第2巻を同一保存単位でcommitする。
2. commit結果、最新コミット、残存変更を確認する。
3. 別の指示でpushし、push後の状態を確認する。
4. 保存後に、final rank、baseline fallback、formal route、順位台帳接続などの次領域を選ぶ。
5. Vehicle台帳更新とatomic applyは、final rankと全体整合確認の設計後に扱う。

# TVT-MP final rank construction部品・完全実装前仕様

**記録日: 2026-09-26**

本節は完全実装前仕様である。Python実装と専用テストは未着手である。Cursorの報告だけで実装完了としない。実装後は実コード、専用テスト、差分、Git状態、独立確認を根拠にする。

新しい制度判断は追加しない。第1巻 §14.2–§14.4 および第2巻の原因別最終分岐・拘束順位列4区分は再検討または未確定へ戻さない。`TVT検討なし` という一括表現だけで原因別分岐を潰さない。

## 1. 位置づけと予定ファイル

payment・compensation 純計算（commit `634d9e7`）の次に置く。各対象Nodeについて、今回新たに正式確定する Visit 列と、各 Visit の対象Node通過後の正式進路を構築する純計算部品である。新しい frozen 結果だけを返す。

順位台帳への書込み、Vehicle金銭台帳更新、実World反映は対象外である。confirmation という名称は使わない。台帳反映まで完了したと誤読されるためである。construction により純計算と実適用を区別する。正式名称は FinalRank である。

| 区分 | パス |
| --- | --- |
| 新規本番予定 | `uxsim/order_control_tvt_mp_final_rank.py` |
| 新規専用テスト予定 | `tests_order_control_tvt_mp_final_rank.py` |

既存の payment、候補選択、経済性評価、拘束順位列、順位台帳モジュールおよびそれらの専用テスト、既存結果型は変更しない。

## 2. 原因別5分岐

結果だけでなく、その結果になる原因を記録する。5分岐を混同しない。分岐4と分岐5は同じ `NO_VISITS_TO_CONFIRM` となるが、原因は別である。

### 2.1 分岐1: selected candidateがある

**原因:** economically feasible 候補から selected candidate が1件選ばれた。

**結果:** 区分3と区分4をこの順で使う。区分3は selected candidate の `trade_scope` 内にある Visit。区分3は取引後順位で確定する。区分4は `trade_scope` 外にある、今回の意思決定窓内に残る Visit。区分4は baseline 順位で確定する。区分1と区分2はすでに確定済みなので再確定しない。すでに確定済みの順位を上書きしない。すでに確定済みの正式進路を上書きしない。selected candidate の保存済み拘束順位列を再構築しない。経済性評価、候補選択、payment・compensation を再実行しない。`trade_scope` だけを確定し、残る意思決定窓内 Visit を放置してはいけない。

### 2.2 分岐2: 候補検討の結果、採用候補が0件

**原因:** 意思決定窓内 Visit が存在した。候補検討まで進んだ。FIFO False、局所 unresolved、経済的不成立、またはその混在により採用候補が0件となった。

対象例: FIFO False、局所仮想計算 unresolved、required buyer または seller が horizon 内に通過しない、resolved だが経済的不成立、不採用・未解決・経済的不成立の混在、feasible 候補が0件。

**結果:** 先行確定後に残る意思決定窓内 Visit 全体を baseline 順位で確定する。すでに確定済みの Visit は対象に含めない。すでに確定済みの順位を上書きしない。すでに確定済みの正式進路を上書きしない。正常な baseline fallback とする。一部 Visit だけを確定しない。上限 N で切らない。情報不足と経済的不成立を同一原因として記録しない。payment・compensation は候補なし正常結果で records は空。例外にしない。

### 2.3 分岐3: 必要なbaseline情報不足

**原因:** 意思決定窓内 Visit が存在した。しかし候補形成または評価に必要な baseline 情報が不足した。

対象例: `NOT_BUILT_UNRESOLVED_ARRIVALS`、`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`、`UNRESOLVED_CANDIDATE_PASSAGES`。

**結果:** 経済的不成立とは扱わない。unresolved を経済的不成立へ変換しない。部分情報だけで部分的 TVT を形成しない。先行確定後に残る意思決定窓内 Visit 全体を baseline 順位で確定する。すでに確定済みの Visit は対象に含めない。すでに確定済みの順位を上書きしない。すでに確定済みの正式進路を上書きしない。正常な baseline fallback とする。情報不足を任意推定値で補わない。例外にしない。

### 2.4 分岐4: 意思決定窓内Visitが最初から0件

この分岐を、TVT不成立後の baseline fallback として記述しない。

**原因:** `decision_window_visit_keys` が最初から空 tuple。意思決定窓内 Visit が最初から存在しない。

**制度上の意味:** 実質的な TVT候補検討を行わない。候補を形成しない。経済性評価対象を作らない。payment または compensation を計算しない。架空の候補、架空の G、R、payment、compensation を作らない。

**実装上の意味:** 対象Nodeを後段の set result から削除しない。正常な空Node結果を payment set まで伝播させる。架空の候補または金額を作らない。上位driverは対象Node全体について既存の全Node APIを順に呼ぶ。各後段部品は実質的な候補評価や金額計算を行わず、正常な空Node結果を伝播させる。payment Node結果は `NO_SELECTED_CANDIDATE` かつ空recordsとなる。これは payment を計算したという意味ではない。経済条件を検討して不成立になったという意味ではない。

**結果:** `NO_VISITS_TO_CONFIRM`。selected candidate は None。final rank 列は空 tuple。baseline fallback ではない。例外にしない。

「TVT不成立かつ残る意思決定窓内 Visit が0件」を通常の正常分岐として作らない。TVTを実際に検討した結果、採用候補が0件になった場合は分岐2であり、残る意思決定窓内 Visit 全体を baseline 順位で確定する。残る窓が1件以上あるなら `NO_VISITS_TO_CONFIRM` ではない。

### 2.5 分岐5: 意思決定窓内Visitは存在したが、全件が先行確定済み

**原因:** `decision_window_visit_keys` は1件以上。区分2までの先行確定により、その全 Visit がすでに確定された。`remaining_decision_window_visit_keys` が空 tuple となった。final rank construction 部品が追加で確定する Visit はない。

**結果:** `NO_VISITS_TO_CONFIRM`。selected candidate は None。final rank 列は空 tuple。baseline fallback ではない。先行確定済み Visit を final rank 列へ再掲しない。すでに確定済みの順位と正式進路を上書きしない。例外にしない。

**分岐4との違い:** 分岐4は、意思決定窓内 Visit が最初から0件。分岐5は、意思決定窓内 Visit は存在したが、final rank construction 前に全件が先行確定済み。結果 status が同じでも、原因を混同しない。

### 2.6 payment setまでの正常な空Node結果伝播

既存の全Node APIを保存済み処理順に呼んだ場合、次の全Nodeが正常なNode結果として payment set まで伝播する。

- selected candidate あり
- 候補検討後の採用候補なし
- baseline 情報不足
- 意思決定窓内 Visit が最初から0件
- 先行確定により残る意思決定窓が空

空窓や情報不足では候補や金額を作らず、空候補・空recordsの正常結果が伝播する。架空の payment または架空の selected candidate を作るわけではない。Node結果を省略しない。呼出し忘れによる欠落と、正常な空Node結果を同一視しない。

payment set は、金額計算済み候補だけを意味するものではない。payment set 全体には、selected candidate あり、候補なし、情報不足、空窓、全件先行確定済みの Node結果が含まれ得る。selected candidate がない Node では payment records は空である。空recordsは架空の金額ではない。原因は上流参照連鎖から判定する。payment set は5分岐を final rank へ運ぶ一つの不変な入口として使う。

### 2.7 payment statusを原因として使わない

payment status は final rank 分岐の原因ではない。`NO_SELECTED_CANDIDATE` だけを見て baseline fallback を選ばない。`NO_SELECTED_CANDIDATE` だけを見て経済的不成立と判断しない。`NO_SELECTED_CANDIDATE` は、selected candidate がなく payment records が空であるという後段の結果ラベルである。空窓、baseline 情報不足、全候補却下、全件先行確定済みは、payment 上では同じ `NO_SELECTED_CANDIDATE` へ畳み込まれ得る。final rank 部品は、上流の保存済み原因へ遡って正式分岐を決定する。

正式な原因判定材料:

- `decision_window_visit_keys`
- `remaining_decision_window_visit_keys`
- candidate visit set の `build_status`
- FIFO結果
- 局所仮想計算の `resolved`
- 経済性評価結果
- candidate selection status
- selected candidate の有無
- payment status と records

payment status と selection status は整合確認に使うが、それだけで原因別分岐を決めない。

### 2.8 5分岐への到達方法

**分岐1 selected candidate あり:** payment status は `CALCULATED`。selection status は `SELECTED`。selected candidate は入力 economic 候補内の同一 object。保存済み拘束順位列の区分3と区分4を使用する。payment 金額は順位材料に使わない。

**分岐2 候補検討後の採用候補なし:** 意思決定窓内 Visit は1件以上存在した。candidate visit set の `build_status` は `BASELINE_INFORMATION_COMPLETE`。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。FIFO False、局所 unresolved、経済的不成立等の詳細原因は上流結果に残る。final rank は残る意思決定窓内 Visit 全体を baseline fallback する。

**分岐3 baseline 情報不足:** 意思決定窓内 Visit は1件以上存在した。`build_status` は `NOT_BUILT_UNRESOLVED_ARRIVALS`、`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`、`UNRESOLVED_CANDIDATE_PASSAGES` のいずれか。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。経済的不成立とは扱わない。final rank は残る意思決定窓内 Visit 全体を baseline fallback する。残る窓が1件以上あることが前提である。

**分岐4 意思決定窓内 Visit が最初から0件:** `decision_window_visit_keys` が空 tuple。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。候補検討または経済条件評価を実質的に行ったという意味ではない。final rank status は `NO_VISITS_TO_CONFIRM`。final rank 列は空 tuple。baseline fallback ではない。

**分岐5 全件先行確定済み:** `decision_window_visit_keys` は1件以上。`remaining_decision_window_visit_keys` が空 tuple。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。final rank status は `NO_VISITS_TO_CONFIRM`。final rank 列は空 tuple。baseline fallback ではない。分岐4と原因を混同しない。

## 3. selected candidate成立時の確定範囲

保存済み拘束順位列の区分3と区分4を使う。

**区分3** `trade_scope_of_this_candidate_visits`: selected candidate の取引後順位。非参加 Visit の baseline 順位枠は保存済み拘束順位列へすでに反映済み。Visitごとの確定元は `SELECTED_CANDIDATE`。

**区分4** `outside_trade_scope_inside_k_fixed_visits`: `trade_scope` 外だが今回の確定範囲内に含まれる Visit。baseline 順位。Visitごとの確定元は `BASELINE`。`trade_scope` が意思決定窓より小さい場合に、残る意思決定窓内 Visit を放置しないための列である。

正式関係: `k_fixed = max(k_last_buyer, k_decision_window)`。

確認: 区分3と区分4をこの順で連結する。VisitKey 重複なし。Visit 欠落なし。保存済み binding rank と順序が一致する。区分3の各 Visit に区分3と整合する binding partition が保存されている。区分4の各 Visit に区分4と整合する binding partition が保存されている。先行確定済み区分1・2を含めない。対象Node向け正式進路を各 Visit に対応させる。selected candidate の保存済み拘束順位列を再構築しない。

意思決定窓外 Visit: 不成立または情報不足だけを理由に確定しない。候補母集団に入っただけでは確定しない。上限 N 以内であることだけを理由に確定しない。selected candidate 成立時に `k_fixed` へ含まれる場合だけ確定され得る。

## 4. 区分1から区分4

**区分1** `confirmed_before_this_baseline`: 今回 baseline 開始前から確定済みの Visit。通過済み Visit を含み得る。今回の final rank construction では再保存しない。

**区分2** `preconfirmed_by_this_baseline`: 今回 baseline 内で先行確定された Visit。既到着かつ順位未確定 Visit の先行確定と、先頭連続非参加 Visit の先行確定。候補形成前に順位と正式進路を原子的に確定済み。今回の final rank construction では再保存しない。

**区分3・4:** selected candidate 成立時の最終確定対象。baseline fallback 時の最終確定対象は、先行確定後に残る意思決定窓内 Visit 全体であり、区分1・2を再度 final rank 列へ含めない。

重複 VisitKey を自動除外して処理を続行しない。区分1または区分2の Visit が final rank 列へ混入した場合は重大不整合とする。

## 5. baseline fallback

対象: 先行確定後に残る意思決定窓内 Visit 全体。正本列は `remaining_decision_window_visit_keys`。

順位: 正式 baseline 順。上限 N で切らない。一部だけ確定しない。正式 baseline 順から不要に再ソートしない。根拠は到着 timestep、arrival tiebreaker、vehicle_id。既存部品で確定済みの正式順を再利用する。

formal route: 今回 baseline collector に保存された対象Node通過後の `route_next_link_name`。過去に確定済みの正式進路を上書きしない。進路を推測しない。進路欠落を任意値で補わない。空文字を正式進路として扱わない。進路欠落が実在する場合は重大不整合。

先行確定済み Visit は fallback で再確定しない。final rank 列へ再掲しない。重複 VisitKey を自動除外しない。重複混入は重大不整合。

「残る意思決定窓内 Visit」と「意思決定窓内 Visit 全体」を混同しない。selected candidate 成立時の区分4は、`trade_scope` 外に残る Visit。全候補却下または情報不足時の fallback は、先行確定後に残る意思決定窓内 Visit 全体。

## 6. 全候補却下、情報不足、unresolved

全候補却下（分岐2）と baseline 情報不足（分岐3）は、残る窓が1件以上なら同じ Node status `BASELINE_FALLBACK_RANKS` を使う。詳細原因は上流 `build_status`、FIFO、局所 `resolved`、`economically_feasible` の参照連鎖から確認する。新しい status へ原因を重複複写しない。情報不足を経済的不成立へ変換しない。unresolved を重大不整合にしない。部分情報だけで部分的 TVT を形成しない。

## 7. NO_VISITS_TO_CONFIRM（分岐4と分岐5）

`NO_VISITS_TO_CONFIRM` は、処理結果として次を意味する。

- final rank construction 部品が今回追加で確定する Visit がない
- final rank 列は空 tuple
- selected candidate は None
- baseline fallback 列も作らない

分岐4と分岐5は、いずれもこの status となる。ただし、原因は必ず区別する。`NO_VISITS_TO_CONFIRM` を「最初から意思決定窓内 Visit が0件の場合だけ」と限定しない。分岐4と分岐5を同じ原因として記録しない。

### 7.1 分岐4: 意思決定窓内Visitが最初から0件

§2.4 と同じ原因。`decision_window_visit_keys` が最初から空である。実質的な候補検討や金額計算は行わず、正常な空Node結果を後段へ伝播させる。架空の record を作らない。baseline fallback status にしない。経済的不成立と記録しない。「残る窓全体を baseline 確定」と記録しない。例外にしない。

### 7.2 分岐5: 全件先行確定済み

§2.5 と同じ原因。`decision_window_visit_keys` は1件以上。`remaining_decision_window_visit_keys` が空。final rank 部品が追加確定する Visit はない。分岐4と混同しない。先行確定済み Visit を final rank 列へ再掲しない。すでに確定済みの順位と正式進路を上書きしない。例外にしない。

### 7.3 使わない意味

`NO_VISITS_TO_CONFIRM` を次の意味にはしない。

- TVT検討後に候補が不成立となった結果、残窓を放置する
- baseline fallback 対象があるのに空結果にする
- selected candidate があるのに final rank 列を空にする

`remaining_decision_window_visit_keys` が1件以上で selected candidate がない場合は、`BASELINE_FALLBACK_RANKS` であり、`NO_VISITS_TO_CONFIRM` ではない。

## 8. 先行確定済みVisitと意思決定窓外Visit

区分1・2は再保存しない。最終確定対象は成立時は区分3＋区分4、fallback 時は残る窓全体。重複混入は重大不整合。すでに確定済みの順位と正式進路を上書きしない。全件先行確定済みで残る窓が空の場合は、先行確定済み Visit を final rank 列へ再掲せず、`NO_VISITS_TO_CONFIRM` とする。原因は分岐5（§2.5、§7.2）である。

窓外 Visit は、不成立・情報不足・N 外であることだけを理由に確定しない。成立時に `k_fixed` へ含まれる場合だけ確定され得る。

## 9. formal route

formal route は、対象Node通過後の正式 outlink 名である。正式 field 名は `formal_route_next_link_name`。final rank Visit record へ順位と一緒に保存する。

理由: 順位と進路を同じ Visit へ対応付ける。後続 apply が既存の原子的順位・進路確定 API へ渡す。route だけを別部品で保存すると順位と進路がずれる。順位だけ確定し進路が未確定の中途半端な状態を作らない。

採用時: 保存済み `OrderControlTvtMpLocalBindingRankVisit.route_next_link_name` を利用する。`route_origin` の既存契約と整合していることを確認する。route を再推定しない。

fallback 時: 今回 baseline collector の対象Node向け進路を利用する。`remaining_decision_window_visit_keys` の各 Visit へ対応する保存済み進路を取得する。route を Vehicle または World から再探索しない。

本部品では順位台帳へ書き込まない。

## 10. 順位台帳との境界

既存の適用 API は `OrderControlTvtNodeRankState.confirm_visits_and_formal_target_node_routes_atomically`。対象 Visit 全件を先に確認する。VisitKey 重複、既確定の再確定、未登録 Visit、対象Nodeの outlink でない進路を拒否する。候補となる更新後状態を別オブジェクトとして構築し、全体検証後に一括保存する。途中で問題があれば1件も保存しない。空列では no-op 結果を返す。

非技術的な意味: 例えば10台の順位と進路を確定する場合、10台分をすべて先に点検する。問題がなければ10台を一度に登録する。6台目で問題が見つかった場合は、最初の5台を含めて1台も登録しない。

final rank construction 部品はこの API を呼ばない。後続 apply へ渡す純計算結果だけを作る。順位台帳への適用は後続の atomic apply 部品へ分離する。既存順位状態型は変更しない。

## 11. 正式入力

入力は `OrderControlTvtMpPaymentAndCompensationSetResult` だけである。`real_W` は受け取らない。rank state も受け取らない。Vehicle 検索しない。World 検索しない。

次を追加しない。

- selection set の別引数
- candidate visit set の別引数
- optional payment 引数
- common upstream result の新型
- 空窓専用 API
- fallback 専用 API
- selected candidate 専用 API

理由:

- 既存の全Node APIを順に呼んだ場合、5分岐すべての Node が、正常なNode結果として payment set まで伝播する
- 空窓や情報不足では候補や金額を作らず、空候補・空recordsの正常結果が伝播する
- 架空の payment または架空の selected candidate を作るわけではない
- 原因は payment status ではなく、上流の保存済み情報から判定できる
- 新しい入力型、optional 引数、複数公開 API を追加せずに済む
- 原因別5分岐の final rank 判定を一つの部品へ集約できる
- final rank construction を pure calculation に維持できる
- 後続 atomic apply へ payment 結果と final rank 結果を一つの参照連鎖で渡せる

payment set から参照連鎖により到達できる: payment and compensation status、candidate selection status、selected candidate、economic evaluation result、local virtual calculation result、binding rank sequence、FIFO result、general trade rank result、concrete buyer candidate set、candidate visit set、right-of-entry selection result、leading nonparticipating confirmation result、`remaining_decision_window_visit_keys`、`decision_window_visit_keys`、candidate visit set の `build_status`、baseline collector、selected 時の区分3・4、fallback 時の baseline 順と正式進路。

payment 金額は final rank 順序の材料にしない。payment result は、処理順の維持、payment status と selection status の整合確認、上流結果への一つの参照連鎖、後続 atomic apply へ payment 結果と final rank 結果をそろえて渡す、ために入力として保持する。payment set は5分岐を final rank へ運ぶ一つの不変な入口として使う。金額計算済み候補だけを意味するものではない。

### 11.1 長い参照連鎖の集約方針

payment set から baseline collector までは長い参照連鎖になる。情報を新しい入力型へ複写しない。private helper で参照経路を一か所に集約する。final rank 本体へ長い参照取得処理を散在させない。上流 object は同一参照で保持し、複写しない。

## 12. 公開Enum

`OrderControlTvtMpFinalRankStatus`

- `SELECTED_CANDIDATE_RANKS = "selected_candidate_ranks"`
- `BASELINE_FALLBACK_RANKS = "baseline_fallback_ranks"`
- `NO_VISITS_TO_CONFIRM = "no_visits_to_confirm"`

`SELECTED_CANDIDATE_RANKS`: selected candidate が存在する。区分3と区分4から final rank 列を構築する。同じ Node 結果内で、Visitごとの確定元は selected candidate と baseline の両方になり得る。

`BASELINE_FALLBACK_RANKS`: 意思決定窓内 Visit が存在した。TVT検討または必要情報取得を行った。しかし selected candidate がない。先行確定後に残る意思決定窓内 Visit が1件以上ある。その全件を baseline 順位で確定する。全候補却下と情報不足の詳細原因は上流 `build_status` 等から確認する。詳細原因を新しい status へ重複複写しない。

`NO_VISITS_TO_CONFIRM`: final rank construction 部品が今回追加で確定する Visit がない。final rank 列は空 tuple。selected candidate は None。baseline fallback 列も作らない。分岐4（§2.4）または分岐5（§2.5）である。分岐4は `decision_window_visit_keys` が最初から空。分岐5は `decision_window_visit_keys` が1件以上で先行確定により `remaining_decision_window_visit_keys` が空。分岐4と分岐5を同じ原因として記録しない。baseline fallback 後に偶然0件になったという意味ではない。経済条件検討後に不成立になったという意味ではない。残る窓が1件以上あるのに空結果にするという意味ではない。

原因を `TVT検討なし` だけで一括表現しない。

## 13. Visitごとの確定元

同じ Node の selected candidate 成立時でも、区分3は selected candidate 順位、区分4は baseline 順位が混在する。Node status だけではこの違いを表現できない。

`OrderControlTvtMpFinalizationSource`

- `SELECTED_CANDIDATE = "selected_candidate"`
- `BASELINE = "baseline"`

区分3の record は `SELECTED_CANDIDATE`。区分4の record は `BASELINE`。baseline fallback の全 record は `BASELINE`。`NO_VISITS_TO_CONFIRM` では Visit record 自体が存在しない。

## 14. 公開frozen型

すべて `dataclass(frozen=True)`。公開の順序付き列は `tuple`。live World、Vehicle、Node、Link、rank state、RNG、mutable list、mutable dict を保持しない。件数 field を置かない。

### 14.1 Visit record

`OrderControlTvtMpFinalRankVisitRecord` — field順:

1. `visit_key`（既存 `OrderControlTvtVisitKey`）
2. `final_local_rank`（今回構築する final rank 列内の1始まり順位）
3. `formal_route_next_link_name`（対象Node通過後の正式 outlink 名）
4. `finalization_source`

`final_local_rank` 契約: 1始まり、1から連続、final rank tuple の保存順と一致。順位台帳全体の絶対順位ではない。後続 apply では、既存の `k_confirmed` に続く順として台帳へ登録される。

保存しない: `vehicle_name`（VisitKey から取得できる）、vehicle_id、binding rank Visit 全体、trade role、payment 金額、compensation 金額、G、R、surplus、live object、mutable state。

### 14.2 Node結果

`OrderControlTvtNodeMpFinalRankResult` — field順:

1. `node_name`
2. `final_rank_status`
3. `selected_candidate_economic_result`
4. `final_rank_visits`

`final_rank_visits` は tuple。selected candidate がある場合、`selected_candidate_economic_result` は入力と同一 object 参照。fallback と no visits では selected は `None`。final rank 列は VisitKey 重複なし。`final_local_rank` は1から連続。保存順と `final_local_rank` は一致。

`SELECTED_CANDIDATE_RANKS`: selected は None ではない。列は区分3＋区分4。区分3 record は selected source。区分4 record は baseline source。区分3は1件以上。区分4は空でもよい。

`BASELINE_FALLBACK_RANKS`: selected は None。列は1件以上。全 record は baseline source。残る意思決定窓内 Visit 全体と一致。

`NO_VISITS_TO_CONFIRM`: selected は None。列は空 tuple。`remaining_decision_window_visit_keys` は空。分岐4では `decision_window_visit_keys` も空。分岐5では `decision_window_visit_keys` は1件以上。分岐4と分岐5を混同しない。残る窓が1件以上ある場合はこの status にしない。

### 14.3 全体結果

`OrderControlTvtMpFinalRankSetResult` — field順:

1. `payment_and_compensation_set_result`
2. `node_final_rank_results`

payment set は入力と同一 object 参照。Node 結果列は tuple。payment、selection の Node 順を維持する。Node 結果を省略しない。部分的 overall result を返さない。上流結果を複数 field で重複保持しない。payment set 1本から参照連鎖を辿る。

## 15. 公開API

```python
def build_tvt_mp_final_ranks(
    payment_and_compensation_set_result,
) -> OrderControlTvtMpFinalRankSetResult:
```

位置引数1つ。`real_W` なし。rank state 入力なし。全Node一括。公開 API はこの関数1つ。Node単位・Visit単位公開 API なし。空窓専用 API、fallback 専用 API、selected candidate 専用 API なし。mutable state なし。外部 fallback rule 引数なし。route Mapping 引数なし。RNG なし。部分的 overall result なし。optional 引数なし。

## 16. 正常分岐の正式判定

Nodeごとに、上流状態を原因別に確認する。payment status だけを唯一の分岐材料にしない。selection status だけを唯一の分岐材料にしない。`NO_SELECTED_CANDIDATE` だけを見て baseline fallback または経済的不成立と判断しない。

正式判定順:

1. payment set から、Nodeごとの上流参照連鎖を取得する
2. Node件数、順序、Node名、payment status と selection status の整合を確認する
3. `decision_window_visit_keys` と `remaining_decision_window_visit_keys` を確認する
4. `remaining_decision_window_visit_keys` が空の場合:
   - selected candidate が存在しないことを確認する
   - payment status が `NO_SELECTED_CANDIDATE` であることを確認する
   - payment records が空であることを確認する
   - status を `NO_VISITS_TO_CONFIRM` とする
   - final rank 列を空 tuple とする
   - `decision_window_visit_keys` も空なら分岐4
   - `decision_window_visit_keys` が1件以上なら分岐5（全件先行確定済み）
   - 分岐4と分岐5を混同しない
   - baseline fallback とはしない
5. selected candidate がある場合:
   - status を `SELECTED_CANDIDATE_RANKS` とする
   - payment status は `CALCULATED`
   - selection status は `SELECTED`
   - 保存済み区分3と区分4を使用する
   - selected を同一 object 参照で保持する
6. selected candidate がなく、`remaining_decision_window_visit_keys` が1件以上の場合:
   - `build_status` 等から全候補却下と情報不足を区別する
   - status を `BASELINE_FALLBACK_RANKS` とする
   - 残る窓全体を baseline 順位で確定する
   - 全 record の source は `BASELINE`
   - 詳細原因を新しい status へ重複複写しない

selected candidate があるのに remaining decision window が空という状態が、制度上または保存済み拘束列上起こり得るかを、保存済み件数契約で検証する。重大な矛盾であれば fallback または `NO_VISITS_TO_CONFIRM` へ変換せず `RuntimeError` とする。

## 17. 処理順

明示的な Node、区分3、区分4、fallback Visit の for ループを使う。iterator、generator、並列実行は使わない。候補列、拘束列、残る窓列を不要に再ソートしない。

1. payment and compensation set result の外部入力型を確認する
2. payment Node 結果列が tuple であることを確認する
3. selection Node 結果列が tuple であることを確認する
4. economic、local 等の必要な Node 結果列が tuple であることを必要最小限に確認する
5. Node 件数、Node 順、Node 名を確認する
6. payment status と selection status の対応を確認する
7. private helper により、Nodeごとの上流参照連鎖を一か所から取得する
8. `decision_window_visit_keys` と `remaining_decision_window_visit_keys` を確認する
9. 残る意思決定窓が空なら、selected なし・`NO_SELECTED_CANDIDATE`・空recordsを確認し、`NO_VISITS_TO_CONFIRM` 結果を作る
10. `decision_window_visit_keys` も空なら分岐4、1件以上なら分岐5として区別する
11. selected candidate がある場合、入力 economic 候補内の同一 object であることを確認する
12. selected candidate の保存済み binding rank sequence を取得する
13. 区分3を保存順に明示的 for ループで走査する
14. 区分4を保存順に明示的 for ループで走査する
15. 区分3と区分4の VisitKey 重複、件数、binding partition、binding rank、正式進路を確認する
16. 区分3と区分4をこの順で連結する
17. Visitごとに `final_local_rank` を1から順に付ける
18. 区分3の finalization source を `SELECTED_CANDIDATE` とする
19. 区分4の finalization source を `BASELINE` とする
20. `SELECTED_CANDIDATE_RANKS` の Node 結果を作る
21. selected candidate がなく、残る意思決定窓が1件以上なら、`build_status` 等から全候補却下と情報不足を区別し、baseline fallback 材料を取得する
22. 残る意思決定窓内 Visit 全体を正式 baseline 順で明示的 for ループにより走査する
23. 各 Visit の正式進路を baseline collector から取得する
24. Visitごとに `final_local_rank` を1から順に付ける
25. 全 record の finalization source を `BASELINE` とする
26. `BASELINE_FALLBACK_RANKS` の Node 結果を作る
27. 全 Node 完了後に全体結果を作る

再実行しない: 候補形成、一般形順位再構成、FIFO検査、局所仮想計算、経済性評価、候補選択、payment・compensation 計算、VOT 読取、交通シミュレーション。

## 18. 重大不整合

外部入力型不正は `ValueError`。保存済み結果間または内部の重大不整合は `RuntimeError`。

主な重大不整合: payment / selection / 必要な上流 Node 結果列が tuple でない。Node 件数、Node 順、Node 名が一致しない。Node結果が上流 set から欠落しているのに処理を続ける。呼出し忘れによる欠落を正常な空Node結果と同一視する。payment status だけで原因別分岐を決める実装。payment status と selection status が矛盾。payment status が `NO_SELECTED_CANDIDATE` なのに payment records が非空。payment status が `CALCULATED` なのに selected candidate がない。payment status が `CALCULATED` なのに selection status が `SELECTED` でない。payment status が `NO_SELECTED_CANDIDATE` なのに selection status が候補なし status でない。selected candidate が入力 economic 候補内の同一 object でない。selected があるのに binding rank sequence がない。selected candidate status なのに payment status が `NO_SELECTED_CANDIDATE`。selected がないのに payment records が存在する。decision window が空なのに selected candidate が存在する。decision window が空なのに payment status が `CALCULATED`。remaining decision window が空なのに baseline fallback status を作る。remaining decision window が1件以上あるのに `NO_VISITS_TO_CONFIRM` を作る。全件先行確定済みなのに、その Visit を final rank 列へ再掲する。すでに確定済みの順位または正式進路を上書きする。分岐4と分岐5を同じ原因として記録する。情報不足なのに `BASELINE_INFORMATION_COMPLETE` として扱う。`BASELINE_INFORMATION_COMPLETE` なのに情報不足 fallback として扱う。成立時に区分3・4の VisitKey が重複。区分1または区分2の Visit が最終列へ混入。baseline fallback 列に先行確定済み Visit が混入。final rank 対象 Visit が重複または欠落。`k_fixed`、`k_last_buyer`、`k_decision_window` と保存済み列件数が矛盾。区分3または区分4の binding partition が不正。final rank 順と保存済み binding rank 順が矛盾。`final_local_rank` が1から連続しない。formal route が欠落または空文字。route 情報を推測で補う必要がある。`NO_VISITS_TO_CONFIRM` なのに final rank record が存在する。`BASELINE_FALLBACK_RANKS` なのに残る意思決定窓が空。`SELECTED_CANDIDATE_RANKS` なのに selected candidate がない。selected candidate の重大不整合を baseline fallback へ変換する。selected candidate の重大不整合を `NO_VISITS_TO_CONFIRM` へ変換する。情報不足理由を経済的不成立へ変換する。意思決定窓内 Visit が最初から0件なのに baseline fallback へ変換する。

正常な次の状態は `RuntimeError` にしない: 全候補却下（分岐2）、情報不足（分岐3）、FIFO False、局所 unresolved、required buyer または seller の horizon 内未通過、resolved だが経済的不成立、分岐4の `NO_VISITS_TO_CONFIRM`、分岐5の `NO_VISITS_TO_CONFIRM`。

1 Node の重大不整合で全体停止する。後続 Node を処理しない。部分的 overall result を返さない。rollback しない。入力、rank state、Vehicle、World を変更しない。

## 19. 過剰検証を避ける方針

本部品で確認する: 外部入力型、Node 結果列の tuple 契約、Node 対応、payment status と selection status の整合、selected の同一 object、意思決定窓件数、残る意思決定窓件数、candidate visit set の build status、区分3・4、fallback 対象列、VisitKey 重複・欠落、binding partition、binding rank の保存順、final rank 連続性、formal route、保存済み件数関係。

payment status は整合確認に使う。payment status だけで原因別分岐を決めない。`NO_SELECTED_CANDIDATE` を空窓、情報不足、全候補却下の原因として使わない。

再実行しない: candidate formation、general trade rank、FIFO、local virtual calculation、economic evaluation、candidate selection、payment・compensation、VOT 読取、交通シミュレーション。

上流で保証済みの buyer 集合、seller 集合、surplus、payment 式、compensation 式、RNG 選択、経済的成立条件の全詳細を無制限に再検証しない。selected 成立時は保存済み区分3・4を再利用する。fallback 時は保存済み `remaining_decision_window_visit_keys` と baseline 情報を利用する。長い参照連鎖は private helper 一か所で辿り、本体へ散在させない。

## 20. 不変性

変更しない: payment and compensation result、candidate selection result、economic evaluation result、local virtual calculation result、FIFO result、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、real World、World RNG、order-control RNG、`vot_declared`、`vot_true`、`participates_in_order_exchange`。

新しい frozen final rank 結果だけを返す。入力結果へ selected flag、final rank、formal route 確定済み flag 等を後書きしない。

## 21. 処理全体での位置

正式順序:

1. candidate selection
2. payment・compensation pure calculation
3. final rank construction
4. final consistency validation
5. rank state と Vehicle 金銭台帳への atomic application

payment 金額は final rank 順位を変えない。payment 結果は final rank の順位材料として使わない。payment 処理を先に行うのは、上位処理順と後続 atomic apply の入力をそろえるためである。final rank construction が失敗した場合、frozen payment 結果は実適用せず破棄できる。順位台帳と Vehicle 金銭属性への不可逆な更新は atomic apply まで行わない。

### 21.1 将来の上位driverの責務

上位driverは未実装である。将来の上位driverについて、次を実装前仕様として記録する。本部品では実装しない。

- 対象Node全体について、既存の全Node APIを保存済み処理順に呼ぶ
- Nodeごとに空窓または情報不足を理由として処理チェーンから脱落させない
- 空窓Nodeも正常な空Node結果として各 set result に残す
- final rank 部品へ、全Nodeを含む payment set を渡す
- final rank の原因別5分岐を上位driverで再実装しない
- baseline fallback 列を上位driverで構築しない
- 分岐4と分岐5を上位driverで別APIへ分けない

上位driverが payment set を作らず、空窓Nodeを別経路へ送る案は採用しない。

## 22. atomic applyとの境界

本部品は行わない: rank state への書込み、`payment_paid` 更新、`payment_received` 更新、`order_exchange_log` 更新、target Node の outlink 集合検証、複数 Node の実適用、rollback。

後続 atomic apply 部品が行う予定: final rank Visit 列を順位と正式進路の組として Node 順位台帳へ渡す。既存 `confirm_visits_and_formal_target_node_routes_atomically` を利用する。selected candidate が成立した Node について、payment・compensation 結果を Vehicle 金銭台帳へ反映する。final rank と payment・compensation の整合を最終確認する。台帳反映途中の部分更新を防ぐ。

複数 Node 全体をどの単位で atomic にするかは、後続 apply 部品の設計で扱う。本節では新たに確定しない。

## 23. 責務外

rank state への書込み、`Vehicle.payment_paid` 更新、`Vehicle.payment_received` 更新、`order_exchange_log` 更新、atomic apply、target Node outlink 集合の World からの取得、実World交通反映、actual passage 記録、expected と actual の比較、prediction error、realized utility、ex-post welfare、上位 TVT driver、strategy-proofness 検証、文献制度の移植。

## 24. 可読性

正しさを最優先する。Python 初学者が後から追いやすい明示的な実装を前提とする。明示的 Node / 区分3 / 区分4 / fallback Visit の for ループ、意味のある中間変数、小さな private helper、原因と結果が分かるコメント、frozen dataclass、tuple 公開列、明示的な status 分岐。

コメント、docstring、エラーメッセージでは、結果だけでなく原因を明記する。特に次を区別する。意思決定窓内 Visit が最初から0件であるため、実質的な候補検討や金額計算は行わず、正常な空Node結果を後段へ伝播させる。意思決定窓内 Visit は存在したが、全件が先行確定されたため remaining decision window が空となり、final rank 部品が追加確定する Visit はない。baseline 情報が不足しているため候補形成または評価へ進めず、残る意思決定窓内 Visit 全体を baseline fallback する。候補検討まで進んだが採用可能候補が0件となったため、残る意思決定窓内 Visit 全体を baseline fallback する。payment status は原因ではなく、上流結果を final rank へ運ぶ結果ラベルである。

避ける: 長い内包表記、複雑な generator、多段 one-liner、不透明な kind/status 圧縮、原因を `TVT検討なし` だけで一括表現すること、`NO_SELECTED_CANDIDATE` だけで原因を潰すこと、「空窓なので後段へ進まない」と関数呼出し禁止として書くこと、World 検索、Vehicle 検索、rank state 書込み、route 推定、upstream 部品の再実行、final rank と apply の混在、payment との巨大関数化、並列処理、キャッシュ、RNG。

## 25. 専用テスト契約

新規専用テストは `tests_order_control_tvt_mp_final_rank.py`。最低限次を固定する。

公開型: Enum member と value（FinalRankStatus、FinalizationSource）、Visit / Node / overall frozen、field 順、公開列 tuple、入力 payment set と同一 object、selected と入力 candidate の同一 object、live World / Vehicle / rank state / RNG 非保持、禁止 field なし。

公開 API: `build_tvt_mp_final_ranks`、位置引数1つ、`real_W` なし、rank state 引数なし、Node単位・Visit単位公開 API なし、mutable state なし、RNG なし。空窓専用 API、fallback 専用 API、selected 専用 API なし。optional 引数なし。新しい共通入力型なし。

入力経路: payment set だけで5分岐へ到達できる。selection set 等の追加公開引数なし。payment set から上流原因へ同一参照で到達する。private helper で参照連鎖を集約する。

selected candidate: payment status は `CALCULATED`。selected candidate は入力 economic 候補と同一 object。final rank は `SELECTED_CANDIDATE_RANKS`。区分3だけ、区分3＋区分4、区分4空、区分3は selected source、区分4は baseline source、保存済み順維持、binding rank 順維持、formal route 維持、区分1・2を含めない、selected 順位を再構築しない、`trade_scope` だけを確定して残窓を放置しない、窓外 Visit は `k_fixed` へ含まれる場合だけ確定、`final_local_rank` は1から連続。payment 金額を順位材料に使わない。

baseline fallback: 全候補却下、FIFO False 全件、局所 unresolved 全件、経済不成立全件、不採用・未解決・経済不成立の混在、baseline 情報不足、`NOT_BUILT_UNRESOLVED_ARRIVALS`、`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`、`UNRESOLVED_CANDIDATE_PASSAGES`、残る意思決定窓内 Visit 全体、上限 N で切らない、一部だけ確定しない、baseline 順維持、formal route 維持、先行確定済み Visit を含めない、全 record の source は baseline、fallback を例外にしない。

情報不足の正常伝播: `build_status` は情報不足 status。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。remaining decision window は1件以上。final rank は `BASELINE_FALLBACK_RANKS`。経済的不成立として扱わない。残る窓全体を baseline 順位で確定。

全候補却下: `build_status` は `BASELINE_INFORMATION_COMPLETE`。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。remaining decision window は1件以上。final rank は `BASELINE_FALLBACK_RANKS`。FIFO False、局所 unresolved、経済不成立等の上流原因を維持。

分岐4（空窓）の正常伝播: decision window が最初から空。leading confirmation から payment まで Node結果が省略されない。candidate tuple は空。economic candidate tuple は空。selected candidate は None。payment status は `NO_SELECTED_CANDIDATE`。payment records は空。final rank は `NO_VISITS_TO_CONFIRM`。final rank 列は空。架空の候補または金額なし。baseline fallback ではない。分岐5と別原因として固定する。

分岐5（全件先行確定済み）: decision window は1件以上。remaining decision window は空。selected candidate は None。payment records は空。final rank は `NO_VISITS_TO_CONFIRM`。final rank 列は空。分岐4と別原因として固定する。先行確定済み Visit を final rank 列へ再掲しない。すでに確定済みの順位と正式進路を上書きしない。

formal route: selected の保存済み route、fallback の collector 保存済み route、route を順位と同じ record へ保存、欠落は重大不整合、空文字は重大不整合、推測補完なし、World 検索なし、Vehicle 検索なし。

重大不整合: 入力型不正、Node 対応不一致、Node結果の欠落、payment status と selection status の矛盾、selected 同一 object 違反、selected なのに binding sequence なし、区分3・4重複、区分1・2混入、fallback へ先行確定 Visit 混入、Visit 欠落、件数関係矛盾、binding partition 不正、binding rank 順不一致、final rank 非連続、route 欠落、route 空文字、NO_VISITS なのに records あり、fallback なのに残る窓空、remaining window ありなのに NO_VISITS、decision window 空なのに selected あり、decision window 空なのに payment `CALCULATED`、`build_status` と原因分岐の矛盾、意思決定窓内 Visit が最初から0件なのに fallback、selected の重大不整合を fallback 化、selected の重大不整合を空結果へ変換しない、1 Node 不整合で全体停止、partial なし、後続 Node 未処理。

不変性: payment / selection / economic / local / FIFO / collector / rank state / Vehicle / `payment_paid` / `payment_received` / `order_exchange_log` / World / RNG。

責務外: rank state 書込みなし、Vehicle 台帳更新なし、atomic apply なし、actual なし、utility または welfare なし、strategy-proofness 主張なし。

## 26. 反証して採用しない事項

- selected candidate の `trade_scope` だけを確定し、残る意思決定窓内 Visit を放置する
- 意思決定窓外 Visit を無条件に確定する
- fallback で一部 Visit だけを確定する
- 情報不足を経済的不成立へ変換する
- 未解決を重大不整合にする
- 意思決定窓内 Visit が最初から0件なのに TVT不成立 fallback と記録する
- 意思決定窓内 Visit が最初から0件なのに、実質的な経済条件評価まで進んだと記録する
- remaining decision window が1件以上あるのに `NO_VISITS_TO_CONFIRM` とする
- 分岐4と分岐5を同じ原因として記録する
- 分岐5を、最初から空窓だった分岐4と同一視する
- 全件先行確定済み Visit を final rank 列へ再掲する
- すでに確定済みの順位または正式進路を上書きする
- 空窓に架空の final rank record を作る
- 空窓Nodeを payment set から脱落させる
- 空窓だから後段関数を呼ばないと記録する
- `NO_SELECTED_CANDIDATE` だけを見て baseline fallback または経済的不成立と判断する
- payment status だけで原因別分岐を決める
- 空窓Nodeへ架空の `CALCULATED` 結果を作る
- payment 型へ空窓専用 status を追加する
- selection set または candidate visit set を別の公開引数として渡す
- optional payment 引数で正常状態を表現する
- 新しい共通入力型へ上流情報を大量複写する
- 空窓専用 API、fallback 専用 API、selected 専用 API を分ける
- 原因別分岐を上位driverと final rank 部品へ二重実装する
- 呼出し忘れによる欠落を正常な空Node結果と同一視する
- 先行確定済み Visit を重複登録する
- 重複 Visit を自動除外して処理を続ける
- selected 順位と baseline 順位を重複 Visit 付きで連結する
- route 未確定 Visit を確定する
- route を推測で補う
- final rank construction で順位台帳へ書き込む
- final rank construction で Vehicle 金銭台帳へ書き込む
- Nodeごとに部分的な実適用を行う
- payment、final rank、apply を巨大関数へ混入する
- candidate selection または経済性評価を再実行する
- 原因を `TVT検討なし` だけで潰す

## 27. 実装範囲と実装対象外

実装範囲（保存後の次作業）: 全Node一括の純計算 API、2つの Enum、Visit / Node / overall frozen 結果、原因別5分岐、payment set 1本からの参照連鎖、空Node結果の正常伝播、`NO_VISITS_TO_CONFIRM` の分岐4と分岐5の区別、区分3＋区分4の再利用、baseline fallback、formal route の Visit record 保存、重大不整合時の全体停止、専用テスト。

実装対象外: rank state 書込み、Vehicle 金銭台帳、atomic apply、実World交通反映、actual、utility/welfare、上位 TVT driver 本体、strategy-proofness、文献制度の移植。上位driverの責務は §21.1 に記録するが、本部品では実装しない。

## 28. 次の再開地点

1. Terminalで修正後の final rank 完全実装前仕様を直接表示する。
2. 内容を独立確認する。
3. 問題がなければ、進捗第2巻へ本仕様の要約を別作業で追加する。
4. 進捗第2巻の要約も Terminal で直接確認する。
5. 詳細設計第3巻と進捗第2巻を同一保存単位で commit する。
6. commit 結果、最新コミット、残存変更を確認する。
7. 別の指示で push し、push 後の状態を確認する。
8. 保存後に新規本番 `uxsim/order_control_tvt_mp_final_rank.py` と専用テスト `tests_order_control_tvt_mp_final_rank.py` だけを実装する。

本節は完全実装前仕様である。Python と専用テストは未着手である。順位台帳更新、Vehicle 金銭台帳更新、atomic apply は実装しない。

## 29. 実装・検証結果（2026-09-26）

**記録日: 2026-09-26**

保存済み完全実装前仕様（本大見出しの §1–§28、commit `e364238`）に従って実装・検証した。上記 §1–§28 は歴史的な実装前仕様として残す。最新の実装完了事実は本節 §29 を参照する。

既存 Python、既存テスト、既存結果型は変更していない。

### 29.1 新規ファイル

| 区分 | パス |
| --- | --- |
| 本番 | `uxsim/order_control_tvt_mp_final_rank.py` |
| 専用テスト | `tests_order_control_tvt_mp_final_rank.py` |

### 29.2 公開要素

**Enum** `OrderControlTvtMpFinalRankStatus`:

- `SELECTED_CANDIDATE_RANKS` = `"selected_candidate_ranks"`
- `BASELINE_FALLBACK_RANKS` = `"baseline_fallback_ranks"`
- `NO_VISITS_TO_CONFIRM` = `"no_visits_to_confirm"`

**Enum** `OrderControlTvtMpFinalizationSource`:

- `SELECTED_CANDIDATE` = `"selected_candidate"`
- `BASELINE` = `"baseline"`

**Visit record** `OrderControlTvtMpFinalRankVisitRecord`（frozen）— field順: `visit_key`、`final_local_rank`、`formal_route_next_link_name`、`finalization_source`。

**Node結果** `OrderControlTvtNodeMpFinalRankResult`（frozen）— field順: `node_name`、`final_rank_status`、`selected_candidate_economic_result`、`final_rank_visits`（tuple）。

**全体結果** `OrderControlTvtMpFinalRankSetResult`（frozen）— field順: `payment_and_compensation_set_result`、`node_final_rank_results`（tuple）。

**API**

```text
def build_tvt_mp_final_ranks(
    payment_and_compensation_set_result,
) -> OrderControlTvtMpFinalRankSetResult:
```

契約: 位置引数1つ。入力は `OrderControlTvtMpPaymentAndCompensationSetResult` だけ。`real_W` なし。rank state 引数なし。optional 引数なし。全 Node 一括。公開 API はこの関数1つ。部分的 overall result なし。入力 payment set は同一 object 参照で保持する。selected candidate は同一 object 参照で保持する。

### 29.3 入力経路

上流参照連鎖は private helper `_saved_node_columns_from_payment_set` へ集約した。

payment set から、selection、economic、local、FIFO、general trade rank、concrete buyer、inlink、candidate visit set、right-of-entry、leading confirmation、arrived confirmation、alignment fork、baseline collector へ、既存 object の同一参照で到達する。

新しい共通入力型へ情報を複写していない。

payment status は分岐原因として使用しない。payment status は selection status および records との整合確認にだけ使用する。`NO_SELECTED_CANDIDATE` だけを見て、fallback、経済的不成立、`NO_VISITS_TO_CONFIRM` を決めない。

### 29.4 原因別5分岐

#### 分岐1: selected candidateあり

原因: economically feasible 候補から selected candidate が1件選択された。

結果: `SELECTED_CANDIDATE_RANKS`。保存済み区分3と区分4をこの順で使用する。selected candidate は入力と同一 object。payment 金額を順位材料として使用しない。

区分3: `trade_scope_of_this_candidate_visits`。selected candidate の取引後順位。source は `SELECTED_CANDIDATE`。

区分4: `outside_trade_scope_inside_k_fixed_visits`。trade_scope 外で今回の意思決定窓内に残る Visit。baseline 順位。source は `BASELINE`。空でもよい。

区分1・2は再掲しない。

#### 分岐2: 候補検討後、採用候補なし

原因: baseline 情報は揃った。候補検討まで進んだ。FIFO False、局所 unresolved、経済的不成立、またはこれらの混在により採用候補が0件となった。

結果: `BASELINE_FALLBACK_RANKS`。`remaining_decision_window_visit_keys` 全体を baseline 順位で確定する。上限 N で切らない。一部だけ確定しない。全 record の source は `BASELINE`。正常結果であり例外ではない。

#### 分岐3: baseline情報不足

原因: 意思決定窓内 Visit は存在する。候補形成または評価に必要な baseline 情報が不足した。

対象 status: `NOT_BUILT_UNRESOLVED_ARRIVALS`、`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`、`UNRESOLVED_CANDIDATE_PASSAGES`。

結果: `BASELINE_FALLBACK_RANKS`。`remaining_decision_window_visit_keys` 全体を baseline 順位で確定する。経済的不成立へ変換しない。全 record の source は `BASELINE`。正常結果であり例外ではない。

#### 分岐4: 意思決定窓内Visitが最初から0件

原因: `decision_window_visit_keys` が空。`remaining_decision_window_visit_keys` も空。

結果: `NO_VISITS_TO_CONFIRM`。selected candidate は None。final rank 列は空 tuple。baseline fallback ではない。架空の候補または金額を作らない。Node 結果を省略しない。

#### 分岐5: 意思決定窓内Visitは存在したが全件先行確定済み

原因: `decision_window_visit_keys` は1件以上。区分2までの先行確定により全件確定済み。`remaining_decision_window_visit_keys` は空。

結果: `NO_VISITS_TO_CONFIRM`。selected candidate は None。final rank 列は空 tuple。baseline fallback ではない。先行確定済み Visit を再掲しない。既確定順位と正式進路を上書きしない。

分岐4と分岐5は同じ status だが、原因を混同しない。

### 29.5 formal route

selected candidate 成立時: binding Visit の `route_next_link_name` を使用する。

baseline fallback 時: remaining window の各 Visit について、baseline collector の `get_baseline_visit_snapshot` から `route_next_link_name` を取得する。上限 N 外に残る Visit も collector から取得する。

次を行わない: World からの再探索、Vehicle からの再探索、route の推測補完。

欠落、None、空文字は重大不整合。`formal_route_next_link_name` を、順位と同じ Visit record へ保存する。

### 29.6 final_local_rank

各 Node の今回の final rank 列内で1から開始する。1から連続する。tuple の保存順と一致する。順位台帳全体の絶対順位ではない。本部品は rank state を読まない。

### 29.7 既確定Visitとの境界

区分1・2を final rank 列へ含めない。先行確定済み Visit を fallback 列へ含めない。arrived 確定済み Visit を再掲しない。既確定順位を上書きしない。既確定正式進路を上書きしない。重複を自動除外して処理を継続しない。混入または重複は重大不整合。

### 29.8 不変性と責務境界

変更しない: payment result、selection result、economic result、local result、FIFO result、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、World、RNG。

本部品は次を行わない: `confirm_visits_and_formal_target_node_routes_atomically` の呼出し、rank state への書込み、Vehicle 金銭台帳更新、atomic apply、上位 driver、actual 処理、utility または welfare 計算。

新しい frozen final rank 結果だけを返す。

### 29.9 独立確認で修正した専用テスト

初回専用テストに次の常時成功条件があった。

```text
assert "uxsim" not in imported_modules or True
```

問題: `or True` により必ず成功する。何も検証していない。本番モジュールが既存 uxsim 型を import すること自体は正常であり、トップレベル名 `uxsim` の一律禁止も不適切である。

修正: 常時成功 assert を削除した。不要になった `imported_modules` 変数を削除した。`ast.Import` および `ast.ImportFrom` の収集処理を削除した。具体的な責務外処理の禁止確認は維持した。

維持した確認例: `real_W` なし、World 検索なし、Vehicle 検索なし、rank state 書込みなし、atomic apply 呼出しなし、上流工程再実行なし、Vehicle 金銭属性更新なし、actual passage 処理なし、明示的 for ループ、`dataclass(frozen=True)`、baseline route 取得。

修正後、専用テスト43件は成功し、追加修正は不要である。

### 29.10 検証結果

専用テスト: 件数 43。直接実行 `43 tests passed`。pytest `43 passed`。pytest 収集 43。定義済み test 関数 43。`TESTS` 登録 43。定義と登録は一致する。

py_compile: `uxsim/order_control_tvt_mp_final_rank.py` 成功。`tests_order_control_tvt_mp_final_rank.py` 成功。

関係回帰: 新規専用テストを含む指定16ファイルで `772 passed`。内訳は新規専用テスト 43、その他の関係テスト 729。

全 pytest、GUI、デモ、長時間性能テストは実行していない。

### 29.11 実装完了範囲

実装完了: 2つの公開 Enum。Visit、Node、全体 frozen 結果。payment set だけを入力とする公開 API。private helper による上流参照集約。原因別5分岐。selected candidate の区分3＋区分4。baseline fallback。`NO_VISITS_TO_CONFIRM` の2原因。formal route。`final_local_rank`。重大不整合時の全体停止。部分的 overall result なし。専用テスト43件。関係回帰772件。py_compile。独立確認。

### 29.12 未実装範囲

未実装: final consistency validation。rank state への書込み。Vehicle 金銭台帳更新。atomic apply。上位 driver 本体。実 World 反映。actual 比較。utility または welfare。strategy-proofness 検証。文献制度の移植。

### 29.13 次の再開地点

1. Terminal で本実装結果節を直接表示し、独立確認する。
2. 問題がなければ進捗第2巻へ要約を別作業で追加する。
3. 進捗第2巻も Terminal で直接確認する。
4. 新規本番、新規専用テスト、詳細設計第3巻、進捗第2巻を同一保存単位で commit する。
5. commit 結果、最新コミット、残存変更を確認する。
6. 別の指示で push する。
7. 保存後に final consistency validation の設計へ進む。
8. atomic apply と上位 driver は、その後の別設計とする。

# TVT-MP final consistency validation部品・完全実装前仕様

**記録日: 2026-09-26**

本節は完全実装前仕様である。Python 実装と専用テストは未着手である。rank state、Vehicle 金銭台帳、実 World は変更しない。

完成済みの final rank 結果、payment・compensation 結果、およびそれらが参照する上流結果を相互照合する純計算部品である。実適用前に、順位、正式進路、買い手支払記録、売り手補償記録、selected candidate、原因別5分岐が相互に矛盾していないことを一括確認する。順位列の構築、金額の計算、台帳への書込みは行わない。

## 1. 位置づけ

次まで実装・検証・保存済みである。候補形成、一般形順位再構成、FIFO 検査、候補別局所仮想計算、全候補局所仮想計算集合、経済性評価、economically feasible 候補間の最終選択、buyer payment・seller compensation の純計算、final rank construction。

保存済みの正式処理順:

1. candidate selection
2. payment・compensation pure calculation
3. final rank construction
4. final consistency validation
5. rank state と Vehicle 金銭台帳への atomic application

本部品は final rank construction 部品とは別にする。final rank construction は順位列と正式進路を構築する。payment 部品は支払額と補償額を計算する。final consistency validation は両結果を初めて相互照合する。rank state や Vehicle への実書込みは後続 atomic apply が担当する。構築、照合、実適用を分離することで、問題発生箇所と補修箇所を限定する。

## 2. 予定ファイル

| 区分 | パス |
| --- | --- |
| 本番 | `uxsim/order_control_tvt_mp_final_consistency_validation.py` |
| 専用テスト | `tests_order_control_tvt_mp_final_consistency_validation.py` |

既存 Python、既存テスト、既存結果型は変更しない。

## 3. pure validationと実状態検証の境界

本部品は frozen 結果間の純照合だけを行う。

本部品へ入力しないもの: rank state、Vehicle、Vehicle mapping、対象 Node の outlink 集合、`real_W`、Node object、Link object、RNG。

理由: rank state、Vehicle、outlink 集合は validation 成功後から apply までに変化し得る。validation 時点で実状態を確認しても、書込み時点の安全性を保証できない。apply が同じ確認を省略すれば危険であり、apply が再確認するなら不必要な二重検証になる。既存の原子的順位・進路確定 API は書込み直前に実状態を確認できる。Vehicle 金銭台帳も書込み直前に実 Vehicle を確認する。

したがって次は後続 atomic apply で確認する。rank state に Visit が未確定として登録されていること。Visit がすでに確定済みでないこと。formal route が対象 Node の実 outlink 集合に含まれること。Vehicle が実 World に存在すること。`payment_paid`、`payment_received`、`order_exchange_log` が利用可能であること。実適用直前の状態が変更されていないこと。

final consistency validation の成功は、実状態への書込み成功を保証しない。frozen 結果間の相互整合が確認済みであることだけを示す。

## 4. 正式入力

唯一の公開入力は `OrderControlTvtMpFinalRankSetResult` である。

`real_W`、rank state、Vehicle、Vehicle mapping、Node object、対象 Node の outlink 集合、RNG は受け取らない。

final rank set から同一参照の連鎖により、少なくとも次へ到達する。final rank Node 結果、final rank status、final rank Visit records、payment and compensation set result、payment Node 結果、buyer payment records、seller compensation records、candidate selection set result、selection Node 結果、selection status、selected candidate、economic evaluation set result、economic Node 結果、buyer economic records、seller economic records、local virtual calculation result、binding rank sequence、区分1から区分4、binding Visit の trade role、candidate visit set、`build_status`、`decision_window_visit_keys`、`remaining_decision_window_visit_keys`、baseline collector。

新しい共通入力型へ上流情報を複写しない。長い参照連鎖は private helper 一か所へ集約する。照合本体の各所へ長い参照取得処理を散在させない。上流 object は同一参照のまま利用する。

## 5. 正式結果型

`OrderControlTvtMpFinalConsistencyValidationSetResult` は `dataclass(frozen=True)` とする。

field 順:

1. `final_rank_set_result`

契約: `final_rank_set_result` は入力と同一 object 参照である。field は1つだけである。Node 結果列、final rank Visit 列、buyer payment records、seller compensation records、formal route を複写しない。rank state、Vehicle、outlink 集合を保持しない。boolean の承認 token だけを独立保存しない。failed status を保存しない。mutable state を保持しない。

Node 単位の公開 validation result 型は作らない。validation は全 Node 一括で成功または停止する。Node ごとの成功 record を作ると final rank Node 結果列と重複する。Node 単位の問題は `RuntimeError` のメッセージへ Node 名を含める。部分的な承認を後続 apply へ渡さない。

公開 Enum は作らない。`VALIDATED` だけの Enum も作らない。失敗を正常 status として返さない。

## 6. 公開API

```text
def validate_tvt_mp_final_consistency(
    final_rank_set_result,
) -> OrderControlTvtMpFinalConsistencyValidationSetResult:
```

契約: 位置引数1つ。入力は `OrderControlTvtMpFinalRankSetResult` だけ。`real_W` なし。rank state 引数なし。Vehicle 引数なし。Vehicle mapping 引数なし。Node 引数なし。outlink 集合引数なし。RNG なし。optional 引数なし。外部 validation rule 引数なし。全 Node 一括。公開 API はこの関数1つ。Node 単位公開 API なし。Visit 単位公開 API なし。部分的 validation result なし。成功時だけ frozen 全体結果を返す。

## 7. 採用する設計と採用しない設計

採用する設計: final rank set だけを入力とする pure validation。成功時だけ新しい frozen 全体結果を返す。重大不整合では `RuntimeError`。Node 単位の成功 result は作らない。failed status は作らない。公開 Enum は作らない。順位列、金銭列、route 列を結果へ複写しない。rank state、Vehicle、outlink 集合を保持しない。atomic apply は別部品とする。

採用しない設計: final consistency validation へ rank state、Vehicle、Vehicle mapping、対象 Node の outlink 集合、`real_W` を入力すること。validation 時に順位台帳または Vehicle 金銭台帳へ書き込むこと。pure validation と apply を巨大関数へ統合すること。apply 準備用 snapshot を今回新設すること。Node 単位の空の承認 record を作ること。`VALIDATED` だけの公開 Enum を作ること。failure を正常 status として返すこと。validation 済みの順位列または金銭列を複写すること。

## 8. construction内検証との違い

final rank construction は、final rank 列を構築するときに final rank status、Node 順、selected candidate、区分3と区分4、baseline fallback 列、`final_local_rank`、formal route の存在、Visit 重複、先行確定済み Visit の非再掲、原因別5分岐を確認済みである。

payment 部品は、payment status、buyer payment records、seller compensation records、`payment_P_b`、`compensation_amount`、候補なしの空 records を確認済みである。

candidate selection は、selected candidate の同一 object、selected status、候補なし status を確認済みである。

本部品はこれらを再構築または再計算しない。本部品で初めて可能になる部品間照合を行う。例: final rank の selected candidate と payment の selected candidate が同一 object であること。payment buyer records と selected candidate の buyer economic records が対応すること。seller compensation records と seller economic records が対応すること。buyer record が区分3の `BUYER` role と対応すること。seller record が区分3の `SELLER` role と対応すること。非参加 Visit または区分4 Visit に金銭 record がないこと。fallback または `NO_VISITS_TO_CONFIRM` で金銭 record が空であること。原因別5分岐と金銭結果および順位結果が一致すること。

## 9. selected candidateの同一object

分岐1では、次の selected candidate がすべて同一 object でなければならない。

- final rank Node 結果の `selected_candidate_economic_result`
- payment Node 結果の `selected_candidate_economic_result`
- selection Node 結果の `selected_candidate_economic_result`
- 当該 economic Node 結果の candidate tuple 内にある selected candidate

値が等しいだけでは不十分である。`is` による同一 object 契約を確認する。selected candidate の複製を正常として扱わない。

## 10. buyer paymentの対応

selected candidate 成立時:

- buyer economic records は1件以上
- buyer payment records も1件以上
- 件数が一致する
- 保存順が一致する
- 各 index の VisitKey が一致する
- 各 index の `vehicle_name` が一致する
- buyer VisitKey は重複しない
- buyer payment record の各 VisitKey は区分3内に存在する
- 対応する binding Visit の `trade_role` は `BUYER`
- 区分3内で `BUYER` role の VisitKey 集合は buyer payment records の VisitKey 集合と一致する

`payment_P_b` の式は再計算しない。`R * G_b / G`、`G` の再加算、`R` の再加算、payment 式の再評価、tolerance または Decimal による照合は行わない。payment amount の有限性・非負性等は payment 部品で確認済みなので、同じ深さで再検証しない。payment record と経済 record の Visit 対応は本部品で確認する。

## 11. seller compensationの対応

selected candidate 成立時:

- seller economic records は0件でもよい
- seller compensation records は0件でもよい
- 件数が一致する
- 保存順が一致する
- 各 index の VisitKey が一致する
- 各 index の `vehicle_name` が一致する
- seller VisitKey は重複しない
- seller compensation record の各 VisitKey は区分3内に存在する
- 対応する binding Visit の `trade_role` は `SELLER`
- 区分3内で `SELLER` role の VisitKey 集合は seller compensation records の VisitKey 集合と一致する
- `compensation_amount` は保存済み `required_compensation_R_s` と一致する

`required_compensation_R_s` の式は再計算しない。declared VOT の読取、passage difference の計算、expected waiting increase の計算、`R_s` の式、seller role の再判定は行わない。`compensation_amount` と保存済み `required_compensation_R_s` の一致は、計算式の再実行ではなく、上流値が正しく写されたことの対応確認である。

## 12. compensation 0のseller

補償額0の seller record を欠落扱いにしない。次の seller は、いずれも seller compensation record を保持し、`compensation_amount` は0である。

1. 同時刻 seller。candidate passage と baseline passage が同じため予想遅延が0であり、保存済み `R_s` が0であり、`compensation_amount` が0である。
2. 早期通過 seller。candidate passage が baseline passage より早いため補償対象となる予想遅延がなく、waiting increase が0に clip され、保存済み `R_s` が0であり、`compensation_amount` が0である。
3. 申告 VOT が0の遅延 seller。遅延は存在するが申告 VOT が0であるため、予想待ち増加時間に申告 VOT を掛けた保存済み `R_s` が0であり、`compensation_amount` が0である。

これらの seller は role を維持する。buyer へ変更しない。補償額0であることを理由に record を削除しない。validation では、seller economic record と seller compensation record が存在し、VisitKey と role が対応することを確認する。

## 13. buyerとsellerの重複禁止

同一 candidate の trade scope 内で、同一 VisitKey が buyer と seller の両方になることを許可しない。binding Visit の `trade_role` は `BUYER`、`SELLER`、`NONPARTICIPATING` のうち1つである。buyer economic records と seller economic records は役割別の列である。同一 VisitKey を両方へ登録すると、保存済み role 契約と矛盾する。

確認する事項: buyer VisitKey 集合に重複がないこと。seller VisitKey 集合に重複がないこと。buyer VisitKey 集合と seller VisitKey 集合の共通部分が空であること。payment record と compensation record の VisitKey 共通部分が空であること。重複を自動除外しない。重複は `RuntimeError` とする。

## 14. 非参加Visit

selected candidate 成立時、区分3には `NONPARTICIPATING` role の Visit が存在し得る。非参加 Visit は final rank 列に存在し、selected candidate 順位枠内に存在し、finalization source は `SELECTED_CANDIDATE` である。buyer payment record も seller compensation record も持たない。非参加 Visit に金銭 record を要求しない。非参加 Visit に金銭 record が存在する場合は重大不整合である。

## 15. 区分4Visit

区分4は `outside_trade_scope_inside_k_fixed_visits` である。`trade_role` は `OUTSIDE_TRADE_SCOPE` である。finalization source は `BASELINE` である。selected candidate 成立時の final rank 列には存在する。buyer payment record も seller compensation record も持たない。区分4 Visit に金銭 record を要求しない。区分4 Visit に金銭 record が存在する場合は重大不整合である。区分4が空でも正常である。

## 16. final rank全Visitと金銭recordの関係

final rank 全 Visit と金銭 record の Visit 集合は一致しない。金銭 record を持つのは、selected candidate 成立時の区分3のうち `BUYER` role と `SELLER` role だけである。

金銭 record を持たない正常な final rank Visit: 区分3の `NONPARTICIPATING`、区分4の `OUTSIDE_TRADE_SCOPE`、baseline fallback の全 Visit。`NO_VISITS_TO_CONFIRM` では Visit 自体がない。

したがって次を要求しない。final rank 全 Visit が buyer または seller の金銭 record を持つこと。非参加 Visit が金銭 record を持つこと。区分4 Visit が金銭 record を持つこと。baseline fallback Visit が金銭 record を持つこと。

## 17. 原因別5分岐

### 17.1 分岐1: selected candidateあり

必要な対応: final rank status は `SELECTED_CANDIDATE_RANKS`。payment status は `CALCULATED`。selection status は `SELECTED`。selected candidate は同一 object。buyer payment records は1件以上。seller compensation records は0件以上。final rank 列は区分3＋区分4。区分3の `BUYER` と buyer payment records が一致する。区分3の `SELLER` と seller compensation records が一致する。区分3の `NONPARTICIPATING` に金銭 record はない。区分4の `OUTSIDE_TRADE_SCOPE` に金銭 record はない。formal route は全 final rank Visit に存在する。

### 17.2 分岐2: 候補検討後、採用候補なし

必要な対応: final rank status は `BASELINE_FALLBACK_RANKS`。payment status は `NO_SELECTED_CANDIDATE`。selection status は `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected candidate は None。buyer payment records は空。seller compensation records は空。`build_status` は `BASELINE_INFORMATION_COMPLETE`。final rank 列は remaining window 全体。全 finalization source は `BASELINE`。formal route は全 Visit に存在する。

### 17.3 分岐3: baseline情報不足

必要な対応: final rank status は `BASELINE_FALLBACK_RANKS`。payment status は `NO_SELECTED_CANDIDATE`。selection status は `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected candidate は None。buyer payment records は空。seller compensation records は空。`build_status` は `NOT_BUILT_UNRESOLVED_ARRIVALS`、`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`、`UNRESOLVED_CANDIDATE_PASSAGES` のいずれか。final rank 列は remaining window 全体。全 finalization source は `BASELINE`。経済的不成立へ変換しない。formal route は全 Visit に存在する。

### 17.4 分岐4: 意思決定窓内Visitが最初から0件

必要な対応: final rank status は `NO_VISITS_TO_CONFIRM`。payment status は `NO_SELECTED_CANDIDATE`。selection status は `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected candidate は None。buyer payment records は空。seller compensation records は空。final rank 列は空。decision window は空。remaining window は空。`build_status` は `NOT_BUILT_NO_RIGHT_OF_ENTRY`。架空の候補、金銭、順位はない。

### 17.5 分岐5: 意思決定窓内Visitは存在したが全件先行確定済み

必要な対応: final rank status は `NO_VISITS_TO_CONFIRM`。payment status は `NO_SELECTED_CANDIDATE`。selection status は `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected candidate は None。buyer payment records は空。seller compensation records は空。final rank 列は空。decision window は1件以上。remaining window は空。`build_status` は `NOT_BUILT_NO_RIGHT_OF_ENTRY`。先行確定済み Visit を再掲しない。

分岐4と分岐5は同じ status だが、原因を混同しない。

## 18. status対応

正式対応:

- `SELECTED_CANDIDATE_RANKS` は `CALCULATED` および `SELECTED`
- `BASELINE_FALLBACK_RANKS` は `NO_SELECTED_CANDIDATE` および `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`
- `NO_VISITS_TO_CONFIRM` は `NO_SELECTED_CANDIDATE` および `NO_ECONOMICALLY_FEASIBLE_CANDIDATE`

`NO_SELECTED_CANDIDATE` だけでは分岐2、3、4、5を区別しない。原因は `build_status`、`decision_window_visit_keys`、`remaining_decision_window_visit_keys` から判断する。

## 19. formal route照合

本部品で確認する事項: 全 final rank Visit の `formal_route_next_link_name` が str であること。空文字でないこと。selected 時は binding Visit の `route_next_link_name` と一致すること。fallback 時は collector snapshot の `route_next_link_name` と一致すること。VisitKey 対応が一致すること。

本部品で確認しない事項: 実 Node の outlink 集合に含まれること。実 Link object が存在すること。World 上の Node と route が接続していること。route を実 World から再探索すること。実 outlink 妥当性は atomic apply が書込み直前に確認する。

## 20. final rank列の純照合

確認する事項: final rank VisitKey に重複がないこと。`final_local_rank` が1から連続すること。tuple 順と `final_local_rank` が一致すること。finalization source と Node status が一致すること。selected 時の区分3は `SELECTED_CANDIDATE` source であること。selected 時の区分4は `BASELINE` source であること。fallback 時の全 Visit は `BASELINE` source であること。`NO_VISITS_TO_CONFIRM` では final rank 列が空であること。区分1・2を再掲していないこと。先行確定済み Visit を再掲していないこと。arrived 確定済み Visit を再掲していないこと。

final rank 列自体を再構築しない。

## 21. 処理順

1. final rank set の外部入力型を確認する。
2. final rank Node 結果列が tuple であることを確認する。
3. payment Node 結果列が tuple であることを確認する。
4. selection、economic、local 等の必要な Node 結果列が tuple であることを必要最小限に確認する。
5. Node 件数、Node 順、Node 名を確認する。
6. Node を保存順に明示的 for ループで走査する。
7. private helper で当該 Node の上流参照連鎖を取得する。
8. final rank status、payment status、selection status を照合する。
9. selected candidate の同一 object を照合する。
10. 原因別5分岐を判定する。
11. selected 時は buyer records と区分3 `BUYER` role を照合する。
12. selected 時は seller records と区分3 `SELLER` role を照合する。
13. buyer と seller の VisitKey 重複がないことを確認する。
14. `NONPARTICIPATING` と `OUTSIDE_TRADE_SCOPE` に金銭 record がないことを確認する。
15. fallback 時は両金銭 record が空であることを確認する。
16. `NO_VISITS_TO_CONFIRM` 時は両金銭 record と final rank 列が空であることを確認する。
17. final rank VisitKey、`final_local_rank`、source を照合する。
18. formal route を保存済み binding または collector と照合する。
19. 全 Node 完了後に frozen validation set result を作る。

1 Node で重大不整合があれば後続 Node を処理しない。部分的 validation result を返さない。

## 22. ValueError

外部入力が `OrderControlTvtMpFinalRankSetResult` でない場合は `ValueError` とする。公開引数は1つだけなので、外部入力型不正だけを `ValueError` とする。

## 23. RuntimeError

保存済み結果間または内部の重大不整合は `RuntimeError` とする。最低限、次を重大不整合とする。

- Node 結果列が tuple でない
- Node 件数、Node 順、Node 名が一致しない
- Node 結果が上流 set から欠落している
- final rank status と payment status が矛盾する
- final rank status と selection status が矛盾する
- selected candidate が同一 object でない
- selected candidate が economic 候補 tuple 内の同一 object でない
- selected 時に buyer economic records が空である
- buyer economic records と buyer payment records の件数、順序、VisitKey、`vehicle_name` が不一致である
- buyer payment record の Visit が区分3 `BUYER` でない
- 区分3 `BUYER` なのに buyer payment record がない
- seller economic records と seller compensation records の件数、順序、VisitKey、`vehicle_name` が不一致である
- seller compensation record の Visit が区分3 `SELLER` でない
- 区分3 `SELLER` なのに seller compensation record がない
- `compensation_amount` と `required_compensation_R_s` が一致しない
- 補償額0の seller record が欠落している
- buyer VisitKey が重複している
- seller VisitKey が重複している
- buyer と seller の VisitKey が重複している
- `NONPARTICIPATING` に金銭 record が存在する
- `OUTSIDE_TRADE_SCOPE` に金銭 record が存在する
- fallback 時に buyer または seller の金銭 record が存在する
- `NO_VISITS_TO_CONFIRM` 時に buyer または seller の金銭 record が存在する
- fallback 時に selected candidate が存在する
- `NO_VISITS_TO_CONFIRM` 時に selected candidate が存在する
- final rank VisitKey が重複している
- `final_local_rank` が1から連続しない
- tuple 順と `final_local_rank` が一致しない
- finalization source が Node status または binding partition と矛盾する
- 区分1・2が final rank 列へ再掲されている
- 先行確定済み Visit が final rank 列へ再掲されている
- arrived 確定済み Visit が final rank 列へ再掲されている
- formal route が欠落している、None である、または空文字である
- selected 時の formal route が binding Visit の route と不一致である
- fallback 時の formal route が collector snapshot と不一致である
- 分岐2と分岐3の `build_status` を取り違えている
- 分岐4と分岐5の decision window を取り違えている
- 1 Node の不整合後に処理を続ける
- 部分的 validation result を返す

正常な次の状態は `RuntimeError` にしない。分岐2、分岐3、分岐4、分岐5。seller economic records が0件。seller compensation records が0件。同時刻 seller、早期通過 seller、申告 VOT が0であるため保存済み `R_s` が0となる遅延 seller の `compensation_amount` が0。`NONPARTICIPATING` が金銭 record を持たないこと。`OUTSIDE_TRADE_SCOPE` が金銭 record を持たないこと。

## 24. 過剰検証回避

本部品で照合する事項: 外部入力型、Node 列、status 対応、selected 同一 object、原因別5分岐、buyer economic と buyer payment の対応、seller economic と seller compensation の対応、payment または compensation record と binding role の対応、buyer と seller の VisitKey 一意性、非参加と区分4の金銭 record 非存在、fallback と `NO_VISITS_TO_CONFIRM` の空金銭、final rank 列、source、formal route。

再実行しない事項: candidate formation、general trade rank、FIFO、local virtual calculation、economic evaluation、candidate selection、`P_b` の計算式、`R_s` の計算式、`G` または `R` の再加算、surplus 判定、final rank construction、VOT 読取、passage difference 計算、交通シミュレーション。upstream で確認済みの数値有限性等を同じ深さで繰り返さない。

## 25. 不変性

変更しない対象: final rank result、payment result、selection result、economic result、local result、FIFO result、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、World、World RNG、order-control RNG、`vot_declared`、`vot_true`、`participates_in_order_exchange`。

新しい frozen validation set result だけを返す。

## 26. atomic applyとの境界

validation result は、後続 atomic apply の入力の一つとする。atomic apply は validation result が保持する final rank set を読む。apply は validation 成功済みであることだけを理由に、実状態検査を省略しない。

apply が書込み直前に確認する予定: rank state、Visit の未確定登録、既確定 Visit との衝突、対象 Node の outlink 集合、formal route の実 outlink 妥当性、Vehicle の存在、Vehicle 金銭属性、`order_exchange_log`、実適用対象 Node、複数 Node の一括単位。

本部品は次を行わない。`confirm_visits_and_formal_target_node_routes_atomically` の呼出し。rank state 書込み。Vehicle 金銭台帳更新。log 更新。rollback。実 World 反映。

複数 Node の atomic な書込み単位は、後続 apply 設計の未確定事項として残す。本節では新たに確定しない。

## 27. 上位driverとの境界

上位 driver は未実装である。将来の driver は、全 Node を final rank construction まで通し、final rank set を validation へ渡し、validation 成功結果を atomic apply へ渡す。原因別5分岐を再実装しない。buyer・seller 対応を再照合しない。金銭列を再構築しない。Node ごとに validation 直後の部分適用をしない。driver 本体は本部品では実装しない。

## 28. 専用テスト契約

新規予定ファイルは `tests_order_control_tvt_mp_final_consistency_validation.py` である。Python 実装と専用テストは未着手である。

公開型・API で固定する事項: validation set result が frozen であること。field は `final_rank_set_result` だけであること。入力と同一 object 参照であること。公開 Enum がないこと。公開 Node result 型がないこと。関数名は `validate_tvt_mp_final_consistency` であること。位置引数1つで final rank set だけであること。`real_W`、rank state、Vehicle、outlink 集合、optional 引数がないこと。公開 API は1つであること。

正常5分岐: selected candidate、全候補却下 fallback、情報不足 fallback、最初から空窓、全件先行確定済み。

selected 時: selected 同一 object。buyer economic と payment record の件数・順序・VisitKey・`vehicle_name`。seller economic と compensation record の件数・順序・VisitKey・`vehicle_name`。`BUYER` role 対応。`SELLER` role 対応。`NONPARTICIPATING` に金銭 record がないこと。`OUTSIDE_TRADE_SCOPE` に金銭 record がないこと。seller 0件が正常であること。compensation 0 の seller record を維持すること。buyer と seller の VisitKey 重複を拒否すること。

compensation 0: 同時刻 seller、早期通過 seller、申告 VOT が0であるため保存済み `R_s` が0となる遅延 seller。いずれも seller record を保持し、`compensation_amount` は0であり、role は seller である。

fallback: buyer records 空、seller records 空、selected なし、remaining window 全体、source は `BASELINE`、分岐2と分岐3の `build_status` 区別。

`NO_VISITS_TO_CONFIRM`: buyer records 空、seller records 空、selected なし、final rank 列空。分岐4は decision window 空。分岐5は decision window が1件以上。remaining window は空。分岐4と分岐5を混同しない。

formal route: selected 時に binding route と一致すること。fallback 時に collector route と一致すること。欠落、None、空文字を拒否すること。実 outlink 集合の検査は行わないこと。World 検索なし。Vehicle 検索なし。

重大不整合: input 型不正。Node 対応不一致。status 不一致。selected 別 object。buyer record の欠落、余分、順序違い、VisitKey 違い、`vehicle_name` 違い。seller record の欠落、余分、順序違い、VisitKey 違い、`vehicle_name` 違い。buyer role 不一致。seller role 不一致。buyer と seller の VisitKey 重複。非参加に金銭 record。区分4に金銭 record。fallback に金銭 record。`NO_VISITS_TO_CONFIRM` に金銭 record。compensation 0 の seller record 欠落。final rank 重複。`final_local_rank` 非連続。source 矛盾。formal route 不一致。区分1・2の再掲。先行確定の再掲。arrived 確定の再掲。1 Node 不整合で全体停止。partial result なし。後続 Node 未処理。

不変性: final rank、payment、selection、economic、local、FIFO、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、World、RNG を変更しない。

責務外: rank state 書込みなし。Vehicle 台帳更新なし。atomic apply なし。actual なし。utility または welfare なし。strategy-proofness 主張なし。

## 29. 反証して採用しない事項

次は採用しない。final rank construction で検証済みなので validation を省略すること。status だけを確認して Visit 対応を確認しないこと。final rank 全 Visit、非参加 Visit、区分4 Visit へ金銭 record を要求すること。compensation 0 の seller record を欠落扱い、または seller 列から除外すること。申告 VOT が0の遅延 seller を入力異常にすること。buyer と seller の VisitKey 重複を許可すること。selected candidate の同一 object を確認しないこと。fallback または `NO_VISITS_TO_CONFIRM` で金銭 record を許可すること。pure validation が rank state または Vehicle を変更すること。validation 時に atomic apply を行うこと。validation と apply を巨大関数へ統合すること。validation 成功後に実状態検査を省略すること。Node ごとに validation 直後の部分適用を行うこと。1 Node 失敗後に他 Node を適用すること。rollback 前提で部分書込みすること。actual passage を validation へ混入すること。strategy-proofness を validation で検証すること。`VALIDATED` だけの Enum を作ること。Node 単位の空の承認 result を作ること。順位列や金銭列を validation result へ複写すること。

## 30. 実装範囲と未実装範囲

実装範囲（保存後の次作業）: 全 Node 一括の純照合 API、frozen 全体結果1型、final rank set 1本からの参照連鎖、原因別5分岐と金銭結果の相互照合、buyer・seller と区分3 role の対応、補償0 seller record の維持、非参加と区分4の金銭非存在、formal route の保存値照合、重大不整合時の全体停止、専用テスト。

未実装範囲: 本部品の Python と専用テスト。rank state 書込み。Vehicle 金銭台帳更新。atomic apply。上位 driver 本体。実 World 反映。実 outlink 集合の検査。actual 比較。utility または welfare。strategy-proofness 検証。文献制度の移植。複数 Node の atomic 書込み単位の確定。

## 31. 次の再開地点

1. Terminal で本節を直接表示し、内容を独立確認する。
2. 問題がなければ進捗第2巻へ本仕様の要約を別作業で追加する。
3. 進捗第2巻の要約も Terminal で直接確認する。
4. 詳細設計第3巻と進捗第2巻を同一保存単位で commit する。
5. commit 結果、最新コミット、残存変更を確認する。
6. 別の指示で push し、push 後の状態を確認する。
7. 保存後に新規本番 `uxsim/order_control_tvt_mp_final_consistency_validation.py` と専用テスト `tests_order_control_tvt_mp_final_consistency_validation.py` だけを実装する。
8. 実装後に独立確認する。
9. atomic apply と上位 driver は、その後の別設計とする。

本節は完全実装前仕様である。Python 実装と専用テストは未着手である。rank state、Vehicle 金銭台帳、実 World は変更しない。

## 32. 実装・検証結果（2026-09-27）

**記録日: 2026-09-27**

保存済み完全実装前仕様（本大見出しの §1–§31、commit `7effc68`）に従って実装・検証した。上記 §1–§31 は歴史的な実装前仕様として残す。最新の実装完了事実は本節 §32 を参照する。

既存 Python、既存テスト、既存結果型は変更していない。

### 32.1 新規ファイル

| 区分 | パス |
| --- | --- |
| 本番 | `uxsim/order_control_tvt_mp_final_consistency_validation.py` |
| 専用テスト | `tests_order_control_tvt_mp_final_consistency_validation.py` |

### 32.2 公開要素

**全体結果** `OrderControlTvtMpFinalConsistencyValidationSetResult`（frozen）— field 順: `final_rank_set_result` の1つだけ。入力と同一 object 参照。final rank 列、金銭列、formal route を複写しない。rank state、Vehicle、outlink 集合を保持しない。failed status を保持しない。boolean だけの独立承認 token を作らない。mutable state を保持しない。

公開 Enum は作成していない。公開 Node 単位 validation result 型も作成していない。

**API**

```text
def validate_tvt_mp_final_consistency(
    final_rank_set_result,
) -> OrderControlTvtMpFinalConsistencyValidationSetResult:
```

契約: 位置引数1つ。入力は `OrderControlTvtMpFinalRankSetResult` だけ。`real_W` なし。rank state 引数なし。Vehicle 引数なし。Node 引数なし。outlink 集合引数なし。RNG なし。optional 引数なし。全 Node 一括。公開 API はこの関数1つ。成功時だけ frozen 全体結果を返す。部分的 validation result なし。

### 32.3 入力経路

上流参照連鎖は private helper `_saved_node_columns_from_final_rank_set` へ集約した。

final rank set から、payment、selection、economic、local、FIFO、general trade rank、concrete buyer、inlink、candidate visit set、right-of-entry、leading confirmation、arrived confirmation、baseline collector へ、既存 object の同一参照で到達する。

新しい共通入力型へ情報を複写していない。長い参照連鎖を validation 本体へ散在させていない。

### 32.4 pure validationと実状態検証の境界

実装したのは frozen 結果間の純照合だけである。

確認するもの: final rank と payment・compensation の対応。final rank と selection の対応。selected candidate の同一 object。buyer・seller の Visit 対応。buyer・seller と区分3 role の対応。非参加 Visit と区分4 Visit の金銭 record 非存在。原因別5分岐。final rank 列。formal route の保存値。

確認しないもの: rank state 上の未確定または既確定状態。formal route の実 Node outlink 所属。Vehicle の実 World 上の存在。Vehicle 金銭属性の書込み可能性。apply 直前の実状態変化。

validation 成功は、保存済み frozen 結果間の整合だけを保証する。実際の順位・金銭書込み成功は保証しない。実状態は後続 atomic apply が書込み直前に再確認する。

### 32.5 selected candidateの同一object

分岐1では、次を `is` で照合した。final rank Node 結果の selected candidate。payment Node 結果の selected candidate。selection Node 結果の selected candidate。economic 候補 tuple 内の selected candidate。

値が等しい複製は拒否する。selected candidate の重大不整合を fallback または `NO_VISITS_TO_CONFIRM` へ変換しない。

### 32.6 buyer paymentの対応

selected candidate 成立時に、buyer economic records と buyer payment records について次を照合する。1件以上。件数一致。保存順一致。VisitKey 一致。`vehicle_name` 一致。buyer VisitKey 重複なし。payment record の Visit が区分3内に存在。対応する binding Visit の role が `BUYER`。区分3の `BUYER` 集合と payment record 集合が一致。

`payment_P_b` の式は再計算しない。`R * G_b / G`、`G` の再加算、`R` の再加算、tolerance、Decimal、丸め、残差補正は再実行しない。

専用テストでは、保存された payment 額を式から再計算せず、そのまま承認することも固定した。

### 32.7 seller compensationの対応

selected candidate 成立時に、seller economic records と seller compensation records について次を照合する。0件でも正常。件数一致。保存順一致。VisitKey 一致。`vehicle_name` 一致。seller VisitKey 重複なし。compensation record の Visit が区分3内に存在。対応する binding Visit の role が `SELLER`。区分3の `SELLER` 集合と compensation record 集合が一致。`compensation_amount` と保存済み `required_compensation_R_s` が一致。

`required_compensation_R_s` の式は再計算しない。declared VOT、通過時刻差、予想待ち増加、seller role を再判定しない。

### 32.8 補償額0のseller

補償額0の seller も record を維持する。

実装・テストで固定した対象:

1. 同時刻 seller。予想遅延が0であるため保存済み `R_s` が0。`compensation_amount` は0。
2. 早期通過 seller。補償対象となる予想遅延がないため保存済み `R_s` が0。`compensation_amount` は0。
3. 申告 VOT が0の遅延 seller。遅延は存在する。申告 VOT が0であるため保存済み `R_s` が0。`compensation_amount` は0。

これらは seller role を維持する。buyer へ変更しない。補償額0を理由に record を削除しない。存在すべき seller record が欠落していれば `RuntimeError` とする。

### 32.9 buyerとsellerの重複禁止

同じ VisitKey を buyer と seller の両方にしない。buyer VisitKey 内の重複なし。seller VisitKey 内の重複なし。buyer と seller の VisitKey 集合に共通部分なし。payment record と compensation record に共通 VisitKey なし。重複を自動除外しない。重複は `RuntimeError` とする。

### 32.10 非参加Visitと区分4Visit

区分3の `NONPARTICIPATING`: final rank に存在。source は `SELECTED_CANDIDATE`。buyer payment record なし。seller compensation record なし。

区分4の `OUTSIDE_TRADE_SCOPE`: final rank に存在し得る。source は `BASELINE`。buyer payment record なし。seller compensation record なし。空でも正常。

非参加 Visit または区分4 Visit に金銭 record があれば `RuntimeError` とする。final rank 全 Visit へ金銭 record を要求しない。金銭 record を持つのは selected 時の区分3の `BUYER` と `SELLER` だけである。

### 32.11 原因別5分岐

分岐1 selected candidate あり: `SELECTED_CANDIDATE_RANKS`。`CALCULATED`。`SELECTED`。selected 同一 object。buyer records は1件以上。seller records は0件以上。区分3 `BUYER` と buyer records が一致。区分3 `SELLER` と seller records が一致。非参加・区分4に金銭 record なし。

分岐2 候補検討後、採用候補なし: `BASELINE_FALLBACK_RANKS`。`NO_SELECTED_CANDIDATE`。`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected は None。両金銭列は空。`build_status` は `BASELINE_INFORMATION_COMPLETE`。remaining window 全体。source は `BASELINE`。

分岐3 baseline 情報不足: `BASELINE_FALLBACK_RANKS`。`NO_SELECTED_CANDIDATE`。`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`。selected は None。両金銭列は空。`build_status` は情報不足3 status のいずれか。remaining window 全体。source は `BASELINE`。経済的不成立へ変換しない。

分岐4 最初から空窓: `NO_VISITS_TO_CONFIRM`。両金銭列は空。selected は None。final rank 列は空。decision window は空。remaining window は空。`NOT_BUILT_NO_RIGHT_OF_ENTRY`。正常に次の処理へ進む。シミュレーション停止を意味しない。

分岐5 全件先行確定済み: `NO_VISITS_TO_CONFIRM`。両金銭列は空。selected は None。final rank 列は空。decision window は1件以上。remaining window は空。`NOT_BUILT_NO_RIGHT_OF_ENTRY`。先行確定済み Visit を再掲しない。正常に次の処理へ進む。シミュレーション停止を意味しない。

分岐4と分岐5は同じ status だが原因を混同しない。

### 32.12 final rank列とformal route

照合するもの: VisitKey 重複なし。`final_local_rank` が1から連続。tuple 順と `final_local_rank` が一致。finalization source が正しい。selected 時の区分3は `SELECTED_CANDIDATE`。selected 時の区分4は `BASELINE`。fallback 時の全 Visit は `BASELINE`。`NO_VISITS_TO_CONFIRM` は空列。区分1・2を再掲していない。先行確定済み Visit を再掲していない。arrived 確定済み Visit を再掲していない。

formal route: 非空 str。selected 時は binding Visit の保存 route と一致。fallback 時は collector snapshot と一致。欠落、None、空文字は `RuntimeError`。route を推測しない。実 outlink 集合への所属は確認しない。

正常な処理では既確定 Visit が final rank へ混入しない。既確定 Visit の混入確認は、上流結果の破損または実装ミスを検出する安全確認である。混入しても自動除外または上書きしない。

### 32.13 ValueErrorとRuntimeError

`ValueError`: 入力が `OrderControlTvtMpFinalRankSetResult` でない場合だけ。

`RuntimeError`: Node 対応不一致。status 不一致。selected 同一 object 違反。buyer または seller record 不一致。role 不一致。VisitKey 重複。buyer と seller の重複。補償額0 seller record 欠落。非参加または区分4の金銭 record。fallback または `NO_VISITS_TO_CONFIRM` の金銭 record。final rank 重複または順位不整合。source 不整合。formal route 不一致。区分1・2、先行確定、arrived 確定の再掲。分岐2と3の取り違え。分岐4と5の取り違え。1 Node 不整合後の続行。部分的 validation result。

正常扱い: 分岐2から5。seller 0件。同時刻 seller の補償0。早期通過 seller の補償0。申告 VOT が0であるため保存済み `R_s` が0となる遅延 seller の補償0。非参加 Visit に金銭 record なし。区分4 Visit に金銭 record なし。

### 32.14 不変性と責務境界

変更しない: final rank、payment、selection、economic、local、FIFO、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、World、RNG。

本部品は次を行わない。`confirm_visits_and_formal_target_node_routes_atomically` の呼出し。rank state 書込み。Vehicle 金銭台帳更新。log 更新。rollback。実 World 反映。atomic apply。上位 driver。actual 処理。utility または welfare 計算。

新しい frozen validation set result だけを返す。

### 32.15 独立確認

実ファイルを Terminal で直接確認し、少なくとも次を確認した。公開結果型は1種類。公開 API は1関数。入力は final rank set だけ。Node を保存順に明示的に走査。1 Node の不整合で停止。部分承認なし。selected candidate の同一 object 照合。buyer と payment record の対応。seller と compensation record の対応。補償額0 seller record の欠落検出。buyer と seller の重複拒否。非参加と区分4の金銭 record 拒否。selected 時の区分3＋区分4。fallback 時の remaining window 全体。`NO_VISITS_TO_CONFIRM` の分岐4と分岐5。formal route の保存値照合。既確定 Visit 混入時の停止。rank state、Vehicle、World への書込みなし。

追加修正は不要。

### 32.16 検証結果

専用テスト: 件数 58。直接実行 `58 tests passed`。pytest `58 passed`。pytest 収集 58。定義済み test 関数 58。`TESTS` 登録 58。定義と登録は一致する。

py_compile: `uxsim/order_control_tvt_mp_final_consistency_validation.py` 成功。`tests_order_control_tvt_mp_final_consistency_validation.py` 成功。

関係回帰: 新規専用テストを含む指定17ファイルで `830 passed`。内訳は新規専用テスト 58、その他の関係テスト 772。

全 pytest、GUI、デモ、長時間性能テストは実行していない。

### 32.17 実装完了範囲

実装完了: frozen 全体結果1型。final rank set だけを入力とする公開 API。private helper による上流参照集約。selected 同一 object 照合。buyer payment 対応。seller compensation 対応。補償額0 seller record 維持。buyer・seller 重複禁止。非参加と区分4の金銭 record 非存在。原因別5分岐。final rank 列照合。formal route 照合。重大不整合時の全体停止。部分的 validation result なし。専用テスト58件。関係回帰830件。py_compile。独立確認。

### 32.18 未実装範囲

未実装: rank state 書込み。Vehicle 金銭台帳更新。atomic apply。上位 driver。実 World 反映。実 outlink 集合の検査。actual 比較。utility または welfare。strategy-proofness 検証。文献制度の移植。複数 Node の atomic 書込み単位の確定。

### 32.19 次の再開地点

1. Terminal で本実装結果節を直接表示し、独立確認する。
2. 問題がなければ進捗第2巻へ実装結果要約を別作業で追加する。
3. 進捗第2巻も Terminal で直接確認する。
4. 新規本番、新規専用テスト、詳細設計第3巻、進捗第2巻を同一保存単位で commit する。
5. commit 結果、最新コミット、残存変更を確認する。
6. 別の指示で push する。
7. 保存後に atomic apply の設計着手前調査へ進む。
8. 複数 Node の atomic 書込み単位を atomic apply 設計で検討する。
9. 上位 driver は atomic apply 設計後の別設計とする。

# UXsim正式サンプル・TVT-MP atomic apply設計前スモークテスト

**記録日: 2026-09-27**

TVT-MP final consistency validation の実装・検証・文書化・push 完了後、atomic apply の設計着手前に、UXsim の正式サンプルを実行した記録である。

## 1. 実行目的と位置づけ

**目的**

- 現在の研究用改変によって、既存の通常 UXsim 動作が壊れていないか確認する。
- FCFS 開発時から保存されている正式サンプルの既知基準値と比較する。
- atomic apply の設計へ進む前のスモークテストとする。

**本確認が TVT 機能そのものの動作確認ではない理由**

- TVT-MP の上位 driver は未実装である。
- TVT-MP は実 World の通常実行経路へ未接続である。
- atomic apply も未実装である。
- この正式サンプルは通常の UXsim 実行を確認するものである。

**今回確認できたこと**

- 既存 UXsim の通常シミュレーションが異常終了しない。
- 保存済みの主要交通指標が従来基準値から変化していない。
- 現時点で通常 UXsim 動作への回帰は検出されなかった。

**確認していないこと**

- TVT-MP を有効化した実シミュレーション。
- TVT-MP による順位交換。
- payment・compensation の実 Vehicle 反映。
- rank state への実適用。
- TVT-MP の上位 driver。
- expected 値と actual 値の比較。
- realized utility。
- ex-post welfare。

## 2. 実行時コミットと Git 状態

| 項目 | 内容 |
| --- | --- |
| 実行時コミット | `de19603` — Implement, test and document TVT-MP final consistency validation |
| HEAD | `de19603` |
| `origin/feature/intersection-order-control` | `de19603`（HEAD と一致） |
| 未追跡 | `diagnostics/order_control.zip` のみ |
| その他 | 変更なし |

## 3. 実行対象とコマンド

| 項目 | 内容 |
| --- | --- |
| 実行対象 | `demos_and_examples/example_00en_simple.py` |
| 実行コマンド | `python demos_and_examples/example_00en_simple.py` |

**終了状態**

- exit code: 0
- `simulation finished` を表示
- 例外なし
- 異常終了なし

**実行時間（診断情報のみ、回帰判定対象外）**

setup time と simulation 中の computation time は実行環境により変化するため、交通結果の回帰判定対象に含めない。

今回の表示値:

- setup time: 14.76 s
- simulation 中の computation time: 0.03 s

## 4. 保存済み基準値

旧進捗メモに保存されている正式サンプルの既知基準値（今回新規設定した値ではない。FCFS 開発時から繰り返し確認されている保存済み基準値）:

| 指標 | 基準値 |
| --- | --- |
| number of completed trips | 735 / 810 |
| average speed | 11.7 m/s |
| total travel time | 119475.0 s |
| average travel time of trips | 162.6 s |
| average delay of trips | 62.6 s |
| delay ratio | 0.385 |
| total distance traveled | 1632250.0 m |

主な既存参照箇所: `ORDER_EXCHANGE_PROGRESS.md` の「標準挙動維持の確認」、Phase 4-6K 回帰確認、Phase 4-6L 回帰確認、その後の複数の FCFS・BATCH 回帰確認。

## 5. 今回の実行結果と比較

今回の主要交通結果:

| 指標 | 今回の値 |
| --- | --- |
| number of completed trips | 735 / 810 |
| average speed | 11.7 m/s |
| total travel time | 119475.0 s |
| average travel time of trips | 162.6 s |
| average delay of trips | 62.6 s |
| delay ratio | 0.385 |
| total distance traveled | 1632250.0 m |

**7指標の比較結果（すべて保存済み基準値と一致）**

- completed trips: 一致
- average speed: 一致
- total travel time: 一致
- average travel time: 一致
- average delay: 一致
- delay ratio: 一致
- total distance traveled: 一致

**結論**

- 現在の `de19603` 時点で、既存の通常 UXsim 動作を壊す回帰は検出されなかった。
- 正式サンプルは正常終了した。
- atomic apply 設計着手前のスモークテストとして PASS とする。
- この結果だけで TVT-MP の実 World 動作が確認済みとはしない。

## 6. 今後の再実行方針

正式サンプルは今後も次の節目で再実行する。

1. **atomic apply 実装後** — 順位台帳と Vehicle 金銭台帳への反映部品追加後に、通常 UXsim が壊れていないか確認する。
2. **上位 driver 接続後** — TVT を無効にした通常経路で従来基準値が維持されるか確認する。
3. **TVT-MP を実 World 実行経路へ接続後** — 正式サンプルとは別に、TVT 有効の専用シナリオで実機能を確認する。

**正式サンプルで確認するもの:** 通常 UXsim の既存挙動。異常終了の有無。保存済み主要交通指標。

**正式サンプルだけでは確認しないもの:** TVT-MP の順位交換成立。payment・compensation 実反映。actual passage。prediction error。realized utility。ex-post welfare。

## 7. 次の再開地点

1. Terminal で本スモークテスト記録を直接表示し、内容を独立確認する。
2. 問題がなければ進捗第2巻へ同じ結果の要約を別作業で追加する。
3. 進捗第2巻の要約も Terminal で直接確認する。
4. 詳細設計第3巻と進捗第2巻を同一保存単位で commit する。
5. commit 結果、最新コミット、残存変更を確認する。
6. 別の指示で push し、push 後の状態を確認する。
7. 保存後に atomic apply の設計着手前調査へ進む。
8. atomic apply 実装後に正式サンプルを再実行する。
9. 上位 driver 接続後にも正式サンプルを再実行する。

# TVT-MP atomic apply部品・完全実装前仕様

**記録日: 2026-09-27**

本節は完全実装前仕様である。Python 実装と専用テストは未着手である。Cursor の作業だけで実装完了とはしない。

現在地: candidate selection、payment・compensation 純計算、final rank construction、final consistency validation は実装済みである。UXsim 正式サンプルによる atomic apply 設計前スモークテストも実施済みである。atomic apply と上位 driver は未実装である。

本節は、final consistency validation の成功結果を、Node ごとの順位台帳、Visit ごとの正式進路、`Vehicle.payment_paid`、`Vehicle.payment_received`、`Vehicle.order_exchange_log` へ反映する部品の実装前仕様である。設計着手前調査と、実コード・専用テストの確認を前提にする。調査で確定した技術的前提は、実コードと衝突しない限り未確定へ戻さない。

## 1. 位置づけと目的

非技術的には、順位だけ変わって金銭が変わっていない、金銭だけ変わって履歴がない、ある Node だけ反映されて別 Node が未反映、という中途半端な状態を防ぐ部品である。

目的:

- 順位だけ反映され、金銭が未反映になる状態を防ぐ。
- 金銭だけ反映され、順位が未反映になる状態を防ぐ。
- 支払額だけ更新され、受取額または履歴が欠ける状態を防ぐ。
- 一部の Node だけ反映される状態を防ぐ。
- 通常想定される不整合を、最初の実書込みより前にすべて検出する。

保存済みの正式処理順:

1. candidate selection
2. payment・compensation pure calculation
3. final rank construction
4. final consistency validation
5. atomic apply

本部品は 5 の atomic apply だけを担当する。構築と照合は再実行しない。実通過後の評価は後続部品へ残す。

## 2. 予定ファイル

| 区分 | パス |
| --- | --- |
| 新規本番 | `uxsim/order_control_tvt_mp_atomic_apply.py` |
| 新規専用テスト | `tests_order_control_tvt_mp_atomic_apply.py` |
| 既存変更候補 | `uxsim/order_control_tvt_node_rank_state.py` |

既存順位台帳の公開 API 契約は変更しない。validation、final rank、payment、`uxsim.py`、leading confirmation、collector は変更しない。

`uxsim/order_control_tvt_node_rank_state.py` を変更する理由は、1 Node 内の原子的確定を壊さず、複数 Node の候補状態を先に揃えるためである。公開メソッドの入出力、空入力 no-op、拒否条件は維持する。

## 3. atomic applyの一括単位

1回の `OrderControlTvtMpFinalConsistencyValidationSetResult` に含まれる全対象 Node を、1回の apply 単位とする。Node 単位の公開 apply API は作らない。Vehicle 単位の公開 apply API も作らない。

1 Node の不整合では、全 Node の順位、全 Vehicle の累計金額、全 Vehicle の履歴を一切変更しない。

`NO_VISITS_TO_CONFIRM` の Node も点検対象 Node 集合から落とさない。空 Node は正常な no-op である。final rank 列も金銭列も空なので、その Node の台帳と、どの Vehicle の累計・履歴も変えない。空 Node でも `rank_states_by_node_name` からの欠落は拒否する。欠落を正常な空結果と同一視しない。

上位 driver は、全 Node 一括の公開 API を 1 回だけ呼ぶ。

理由:

- 既存の `OrderControlTvtNodeRankState.confirm_visits_and_formal_target_node_routes_atomically` は、1 Node 内では全件検査後に内部状態を一括置換する。複数 Node へ順番に呼ぶと、後続 Node の失敗時に先行 Node だけが残る。
- `confirm_leading_nonparticipating_decision_window_visits` は、この公開 API を target node 順に呼ぶ。`tests_order_control_tvt_leading_nonparticipating_confirmation.py` の `test_mid_failure_preserves_prior_node_and_skips_later_nodes` は、Node B 失敗時に Node A が確定済みで残ることを既存動作として固定している。atomic apply はその部分更新を引き継がない。
- `payment_paid` と `payment_received` は Node 台帳の内部ではなく、Vehicle 上の累計属性である。Node 単位の commit では、後続 Node 失敗後に累計だけを戻す手段が既存 API にない。

## 4. rollbackに依存しない構造

prepare 区間と commit 区間を分離する。rollback を前提にしない。World 全体の copy もしない。順位台帳は World の外にあり、World の複製は通過状態まで複製するためである。

prepare 区間で作るもの:

- 全 Node の更新後順位台帳状態
- 全 Vehicle の更新後 `payment_paid`
- 全 Vehicle の更新後 `payment_received`
- 全 Vehicle の新しい `order_exchange_log`
- 成功結果の候補

prepare 区間では live 状態を変更しない。1件でも問題があれば、この段階で停止する。

commit 区間は、準備済みの値または内部状態を代入するだけである。通常の入力検査を行わない。金額を計算しない。`order_exchange_log` へ `append` しない。上流計算を再実行しない。rollback を行わない。

保証する範囲は、通常の型不正、欠落、重複、既確定、未登録、進路不正、Vehicle 欠落、金銭属性不正、履歴属性不正による部分更新を防ぐことである。Python プロセスの強制終了、OS 障害、`MemoryError` など、commit 中の致命的障害まで完全な transaction にするものではない。本仕様を完全な transaction と読まない。

## 5. 公開入力と公開API

公開 API（正式）:

```text
def apply_tvt_mp_validated_result(
    final_consistency_validation_set_result,
    real_W,
    rank_states_by_node_name,
) -> OrderControlTvtMpAtomicApplySetResult:
```

公開関数名は `apply_tvt_mp_validated_result`、成功結果型名は `OrderControlTvtMpAtomicApplySetResult` として正式確定する。

契約: 位置引数3つ。optional 引数なし。全 Node 一括。Node 単位公開 API なし。Vehicle 単位公開 API なし。RNG なし。外部 transaction rule 引数なし。部分的成功結果なし。成功時だけ frozen 全体結果を返す。

各入力の意味:

- final consistency validation result は、frozen 結果間の整合が確認済みである入口である。live 状態の正しさまでは保証しない。validation は rank state、Vehicle、outlink を見ていない。
- `real_W` は、live な Node、outlink、Vehicle、累計金額、履歴への入口である。
- `rank_states_by_node_name` は、既存の Node 別順位台帳である。先行確定済み順位と未確定集合を既に保持している。

atomic apply 内で rank state を新規作成しない。新規作成すると、先行確定済み順位と未確定集合を失う。mapping は上位 driver が保持しているものを渡す。

意味と引数契約は本節で固定する。正式名称は §30 で確定済みである。

## 6. 時刻一致

`real_W.T` と、保存済み `baseline_timestep_T` の一致を必須とする。

`baseline_timestep_T` は別の仮想時刻ではない。baseline 計算を開始した実 World の時刻 `T` である。この時刻 `T` に TVT 成立を判断した取引として履歴へ記録する。予測を作った後に実 World が次の timestep へ進んでいれば、古い判断を反映せず停止する。

根拠: `confirm_leading_nonparticipating_decision_window_visits` は、順位書込み前に `real_W.T` と `baseline_timestep_T` の一致を既に要求している。apply がこれを省くと、leading confirmation より弱い時刻条件で台帳を更新する。

空 Node だけの結果でも、結果全体の時刻一致を確認する。空だから時刻検査を省かない。

保存済み連鎖の中で fork 結果の `baseline_timestep_T` と、採用候補がある場合の局所結果の `baseline_timestep_T` が異なる場合は、どちらかを採用せず `RuntimeError` とする。

成立時履歴へ保存する成立時刻 field の正式名称は `tvt_decision_timestep` である。

- 値は、上流 frozen 結果の `baseline_timestep_T` と同じ整数である。baseline 計算を開始した実 World の時刻 `T` であり、TVT 成立を判断した実 World の時刻 `T` でもある。仮想計算内の将来通過時刻ではない。
- prepare 時に、保存済み `baseline_timestep_T` を読み、`tvt_decision_timestep` へ写す。
- apply は `real_W.T` と、保存済み `baseline_timestep_T` の一致を確認する。書き込む履歴の `tvt_decision_timestep` も同じ整数である。
- `baseline_timestep_T` は、上流参照連鎖の field 名として引き続き使用する。成立時履歴の field 名だけを `tvt_decision_timestep` とする。`baseline_passage_timestep` との混同を避ける。

## 7. 既存順位台帳APIの内部整理

維持する公開 API は `OrderControlTvtNodeRankState.confirm_visits_and_formal_target_node_routes_atomically` である。

既存公開契約:

- 1 Node 内で全入力を検査する。
- 候補状態を作る。
- 候補状態を検証する。
- 最後に内部4状態を置換する。内部4状態は、確定 Visit 列、順位 dict、formal route dict、未確定集合である。
- 空入力は台帳を変えず no-op 結果を返す。
- 既確定、未登録、重複、対象 Node の outlink でない進路では無変更で拒否する。
- `OrderControlTvtConfirmResult` を返す。`k_confirmed_before`、`k_confirmed_after`、`newly_confirmed_count` を持つ。

内部変更案:

- private prepare helper
- private prepared state
- private commit helper

private prepare が作るもの:

- 新しい confirmed Visit 列
- 新しい rank dict
- 新しい formal route dict
- 新しい undetermined 集合
- `k_confirmed_before`
- `k_confirmed_after`
- `newly_confirmed_count`

private prepare では live な内部4属性を変更しない。絶対順位は、prepare 開始時の `k_confirmed` の次から、入力列の順に振る。`final_local_rank` は受け取らない。

private commit は、準備済みの4参照を代入するだけとする。

既存公開 API は、同一 Node について private prepare の直後に private commit を呼び、既存動作を維持する。外部から見た拒否条件と空列 no-op は変えない。

atomic apply は、全 Node の private prepare を終了した後で、書込み対象 Node だけを private commit する。`NO_VISITS_TO_CONFIRM` は commit リストに入れない。状態オブジェクト自体を触らない。

prepared state を公開型にしない。mutable list や dict を外部へ公開しない。prepare が作った list と dict は、commit 後に台帳の内部状態になる。公開すると外部が台帳の実体を保持する。

private commit は、atomic apply と既存公開 API の内部からのみ呼ぶ。モジュール外の任意の候補状態を受け取って台帳へ書く入口にはしない。不正な外部呼出しで、検査を飛ばした状態を台帳へ入れないためである。

`confirm_visits_in_order` は formal route を `None` にする。apply は使わない。route 付きの公開 API だけを、内部整理の対象にする。

## 8. final rankと順位台帳の接続

final rank 列の保存順を維持する。その順で、VisitKey と `formal_route_next_link_name` の組を順位台帳へ渡す。

`final_local_rank` は、今回追加する final rank 列内の1始まり順位である。順位台帳全体の絶対順位ではない。validation は、この値が1から連続し、tuple 順と一致することを確認済みである。

順位台帳へ登録される絶対順位は、prepare 開始時の `k_confirmed + final_local_rank` である。`k_confirmed` が0のときだけ、絶対順位と `final_local_rank` は同じ数値になる。`final_local_rank` を絶対順位として上書きしない。過去の確定が既にある台帳を、列内順位で拒否しない。

formal route は、final rank record の保存値を使う。World や Vehicle から再推定しない。実 Node の現在の outlink 所属だけを、apply 直前に確認する。

outlink 名の取得:

- `real_W.get_node(node_name)`
- `node.outlinks.values()`
- 各 Link の `name`

`outlinks` の keys だけを正式検査材料にしない。leading confirmation の `_valid_outlink_names_at_target_node` が、keys ではなく values の Link 名を使う。apply は同じ規則の確認を自モジュールに置く。leading confirmation の private helper は公開しない。

## 9. Vehicle金銭属性

開発初期 commit `6a0578d` から、次が確定している。`uxsim.py` の導入時 docstring は Cumulative と明記している。旧進捗第1巻のフェーズ1も、支払累計額・受取累計額・順序交換履歴と記録している。

- `Vehicle.payment_paid` は累計支払額である。
- `Vehicle.payment_received` は累計受取額である。
- `Vehicle.order_exchange_log` は、当該 Vehicle に関する order-exchange event の履歴 list である。1件の正式形式は、本節で成立時 record として初めて定める。導入時には list であることと、event の履歴であることが定義され、項目は未確定だった。

atomic apply では次を行う。

buyer:

- 保存済み `payment_P_b` を `payment_paid` へ加える。
- `payment_received` は増やさない。

seller:

- 保存済み `compensation_amount` を `payment_received` へ加える。
- `payment_paid` は増やさない。

行わないこと: `G`、`R`、`G_b`、`R_s` の再計算。payment 式の再計算。VOT の再読取。passage timetable の再計算。actual passage による事後精算。金額の丸め。tolerance。Decimal。残差補正。

金額0でも累計へ0を加え、個別取引履歴を必ず残す。0を足す経路と、正の金額を足す経路を分けない。

## 10. 同一Vehicleの複数金銭record

現行 baseline collector は、1回の snapshot-fixed baseline run で同一 Vehicle 名を1 Visit だけ登録する。`order_control_baseline_collector.py` は、同一 `vehicle_name` の2件目を snapshot 登録時に拒否する。

現行の正常な上流結果では、1回の validation 結果内で同一 Vehicle に複数の buyer または seller 金銭 record は通常発生しない。複数 Node を1回の apply にまとめる主因は、同一 Vehicle の合算ではない。後続 Node の失敗で先行 Node の順位または金銭が残ることである。

現行 atomic apply では、同一 `vehicle_name` が金銭 record へ複数回現れた場合は `RuntimeError` とする。合算して処理を続けない。現行上流契約違反として扱う。

将来 collector が複数 Visit 対応になった場合、Vehicle 単位集約へ拡張する可能性を禁止しない。「将来も常に1 Vehicle 1 record でなければならない」とは記録しない。

## 11. order_exchange_logの成立時record

1要素は frozen dataclass を採用する。

理由: dict より field 名と型が明確である。tuple より可読性が高い。後日の実績 record と `isinstance` で区別できる。live object を保持せずに済む。

buyer 用と seller 用に型を分けない。共通の成立時 record 型 `OrderControlTvtMpTradeEstablishmentLogRecord` を正式採用する。分けると、順位と時刻の field が二箇所になる。role と両金額を持ち、使わない側は0にする。

live な Vehicle、Node、World、rank state は入れない。

### 11.1 取引識別

各成立時 record は、次の3 field を直接保持し、この組を取引識別材料とする。

- `tvt_decision_timestep`
- `node_name`
- `buyers_sorted`

`OrderControlTvtMpTradeIdentity` などの専用 frozen 識別型は、現段階では作らない。後続 actual outcome record の設計時に、共通 identity 型が本当に必要と判明した場合だけ再検討する。

`visit_key` は、各 Vehicle の個別 record を識別する情報であり、取引全体の identity には入れない。

各 record は、さらに次を持つ。

- `visit_key`
- `vehicle_name`
- `trade_role`（`BUYER` または `SELLER`）

`vehicle_name` は VisitKey の先頭から得られる。既存の buyer payment record と seller compensation record は `vehicle_name` も保持している。履歴だけ VisitKey に縮めると、金銭 record と履歴の対応が読みにくくなる。VisitKey の先頭および金銭 record の `vehicle_name` と一致することを確認した写しを残す。

`id()`、`hash()`、live object 参照は使わない。新しい連番 transaction ID は現段階では作らない。

根拠: candidate selection は、安定した候補識別として Node 名と公式の `buyers_sorted` を既に使っている。1 Node の1回の validation 結果には、採用候補は高々1つである。`tvt_decision_timestep` を足すと、同じ Node の別時刻の取引と分かれる。

`buyers_sorted` を各 buyer および各 seller の成立時 record へ保持する。seller の record だけを見ても、同じ取引の buyer 集合を特定できる。後続の実績記録は、この材料で成立時 record と結び付く。別のヘッダ record を後から探す必要はない。

この識別材料は、二重適用防止の正本にしない。二重適用の拒否は、順位台帳が既確定 Visit の再確定を拒否することである。`order_exchange_log` は研究コードが list を差し替えできる。

### 11.2 順位情報

履歴へ残す順位は次の3種類だけとする。

`baseline_local_rank`:

- 今回の TVT `candidate_visits` 内における正式 baseline 順位である。
- `candidate_visits` の保存順を1始まりで読む。
- 到着時刻、tiebreaker、Vehicle id で apply が再ソートしない。
- 先行確定済み Visit は `candidate_visits` から除外済みである。
- 交差点に関係する全 Vehicle の絶対順位ではない。
- 今回の TVT 候補車両内の比較用順位である。

取得できる理由: general trade rank の `_build_baseline_order_and_ranks` は、保存済み `candidate_visits` の位置を1始まりで読んだ一時 dict を作り、その dict は結果型へ保存しない、と実装コメントにある。並びの再ソートはしていない。apply は同じ定義で位置を読む。上流型へ baseline 順位 field を追加しない。候補集合に無い Visit は `RuntimeError` とし、順位を推定しない。

`post_trade_local_rank`:

- 同じ `candidate_visits` 母集団における取引後順位である。
- selected candidate の general trade rank の `assigned_rank` を利用する。
- `baseline_local_rank` と同じ母集団なので、順位変化の比較に使える。

結び付け: selected 側の `concrete_buyer_candidate_set.buyers_sorted` と、general trade rank 側の `buyers_sorted` が同じ並びである候補だけを使う。別候補の trade rank は使わない。この参照は保存済み連鎖の読取りであり、順位の再構成ではない。

`ledger_assigned_rank`:

- 順位台帳全体に実際に登録される絶対順位である。
- prepare 時の `k_confirmed + final_local_rank` である。
- 先行確定済み Vehicle を含む順位台帳全体の順位である。
- commit 後に台帳を読み返して履歴を埋めない。prepare 時に決まり、成立時 record へ書く。

`rank_change` は `baseline_local_rank - post_trade_local_rank` である。正なら前進、0なら順位不変、負なら後退である。

履歴へ保存しないもの:

- `binding_rank`
- `post_trade_local_rank` と重複する `final_local_rank`
- buyer・seller について常に selected candidate 由来となる `finalization_source`

理由:

- `binding_rank` は、区分1・2を含む局所 binding 列の位置である。`candidate_visits` 内の取引前後順位と同じ母集団ではない。純粋な取引前後の比較には使わない。
- buyer と seller について、`post_trade_local_rank` と今回列の `final_local_rank` は同じ取引後順になる。同じ数を二 field にしない。
- 履歴を作る Visit は selected 時の buyer と seller だけである。source は selected candidate に決まる。fallback の Visit は履歴を作らないため、source を履歴 field にしない。

`final_local_rank` 自体は台帳接続に使う。履歴へ重複保存しないだけである。絶対順位は `ledger_assigned_rank` だけが表す。

### 11.3 正式進路

`formal_route_next_link_name` を残す。final rank record に保存された正式進路を利用する。World や Vehicle から再推定しない。実 Node の outlink 所属だけを apply 直前に確認する。

### 11.4 予想通過時刻

`baseline_passage_timestep` と `candidate_passage_timestep` を残す。

取得元は `OrderControlTvtMpBuyerEconomicRecord` と `OrderControlTvtMpSellerEconomicRecord` の保存済み int である。経済 record は、採用候補についてこの2時刻を int で保持する。局所仮想計算の passage record は `None` を許すため、履歴の取得元にしない。局所仮想計算を再実行しない。live な local World へ戻らない。

### 11.5 今回の正式金額

`payment_paid_in_this_transaction` と `payment_received_in_this_transaction` を残す。

buyer:

- `payment_paid_in_this_transaction` は `payment_P_b`
- `payment_received_in_this_transaction` は 0

seller:

- `payment_paid_in_this_transaction` は 0
- `payment_received_in_this_transaction` は `compensation_amount`

金額0を省略しない。累計属性へ足す値と、履歴に残す今回額は同じ保存済み金額である。

field 名は §30 で正式確定済みである。buyer は支払額だけを累計へ足し、seller は補償額だけを累計へ足す、という対応は §9 で固定する。

### 11.6 申告VOTと真のVOT

成立時 record には、次の両方を float として保存する。

- `declared_vot_per_second` は、その取引の成立判定と正式金額の計算で使われた、取引成立時点の申告 VOT である。
- `true_vot_per_second` は、後続の実績利得と満足・不満足評価で使う、取引成立時点の真の VOT である。

`declared_vot_per_second` の取得元は、対応する `OrderControlTvtMpBuyerEconomicRecord.declared_vot_per_second` または `OrderControlTvtMpSellerEconomicRecord.declared_vot_per_second` である。buyer の履歴は buyer の経済 record、seller の履歴は seller の経済 record と、VisitKey で対応していることを確認する。atomic apply で `Vehicle.vot_declared` を再読取りしない。申告 VOT が0でも正式な値として保存する。補償額0または支払額0を理由に省略しない。

`true_vot_per_second` は、現在の buyer・seller 経済 record には保存されていない。atomic apply の prepare 時に、対応する live Vehicle の `Vehicle.vot_true` を読み取る。これは経済 record からの取得ではなく、成立時点の値を履歴へ固定するための新規読取りである。

読む対象は、正式な金銭 record を持つ buyer または seller だけである。`NONPARTICIPATING`、区分4、baseline fallback、`NO_VISITS_TO_CONFIRM` では成立時 record を作らない。それらの Visit について、今回の履歴材料として `vot_true` も読まない。

`Vehicle.vot_true` を成立判定または正式金額計算に使わない。atomic apply は保存するだけであり、実績利得や満足判定を計算しない。`Vehicle.vot_true` も `Vehicle.vot_declared` も変更しない。

正式な buyer または seller について、取引成立時点の `vot_true` は次を必須とする。bool ではない。Python の int または float である。有限値である。0以上である。成立時 record へ書くときは float とする。

次は、最初の実書込みより前に `RuntimeError` とする。`vot_true` が `None`。bool。int または float でない。NaN。正または負の無限大。負。1台でも不正なら、順位、金銭、履歴を一切変更しない。

`vot_true` が0は有効である。真の VOT が0の Vehicle も研究上の有効な設定として扱う。不参加の表現には使わない。不参加は `participates_in_order_exchange=False` で表す。満足評価に必要な取引時点の真の VOT が保存できない場合、後から個別取引を正確に評価できない。

申告 VOT を履歴へ残す理由は、個別履歴だけから次を確認できるようにするためである。

- 申告 VOT が0であるため seller 補償額が0だったこと。
- 後続の実績ベース参考支払額・参考補償額が、取引時点の申告 VOT を使えること。
- 金額0を、遅延が無い場合と、遅延があっても申告 VOT が0の場合とに分けること。

### 11.7 VOT設定の研究上の前提

基本実験では、統計資料または論文等に基づいて各 Vehicle へ `vot_true` を設定する。基本実験では `vot_declared` を `vot_true` と同じ値に設定する。正しい VOT 申告を前提として TVT-MP を評価する。

将来の虚偽申告研究では、`vot_true` を車両が本当に持つ時間価値として扱う。`vot_declared` を `vot_true` と異なる値に設定する。申告行動、成立候補、支払額、補償額、実績利得、満足度への影響を調べる。車両が複数の申告 VOT を試し、より有利な申告値を探索する発展研究を妨げない。成立時 record は、申告値と真値が違っていても正常とする。

現時点の基本方針では、`vot_true` は Vehicle へ一度設定した後、ネットワーク内を走行中は不変とする。基本実験では `vot_declared` も走行中は不変とする。

将来拡張として、`vot_declared` が走行中に変化する研究を排除しない。`vot_true` が走行中に変化するシナリオも、設計上は完全には排除しない。したがって、後続評価時に Vehicle の現在値を読むだけでは足りない。各取引の成立時点の両 VOT を、成立時 record へ保存する。将来 live Vehicle の VOT が変わっても、既存の成立時 record の保存値は変えない。

### 11.8 申告VOTと真のVOTの役割分担

`declared_vot_per_second` を使うもの: 取引成立判定。buyer 価値 `G_b`。seller 要求補償 `R_s`。正式支払額。正式補償額。実績ベース参考支払額と参考補償額。

`true_vot_per_second` を使うもの: buyer 実績利得。seller 実績利得。満足・不満足の最終判定。1秒当たり支払額・補償額と真の VOT の比較。虚偽申告研究における申告値と真値の差の分析。

atomic apply では、これらの評価計算を実行しない。両 VOT を成立時 record へ保存するだけである。

### 11.9 正式field一覧と順序

`OrderControlTvtMpTradeEstablishmentLogRecord` の field は、次の順序で固定する。

1. `tvt_decision_timestep`
2. `node_name`
3. `buyers_sorted`
4. `visit_key`
5. `vehicle_name`
6. `trade_role`
7. `baseline_local_rank`
8. `post_trade_local_rank`
9. `ledger_assigned_rank`
10. `rank_change`
11. `formal_route_next_link_name`
12. `baseline_passage_timestep`
13. `candidate_passage_timestep`
14. `payment_paid_in_this_transaction`
15. `payment_received_in_this_transaction`
16. `declared_vot_per_second`
17. `true_vot_per_second`

`binding_rank` と `final_local_rank` は成立時履歴へ保存しない。

## 12. order_exchange_logへ記録しないVisit

成立時 record を作るのは、正式な buyer と seller だけである。

作らないもの:

- `NONPARTICIPATING`
- `OUTSIDE_TRADE_SCOPE`
- baseline fallback の Visit
- `NO_VISITS_TO_CONFIRM`
- 候補なし Node

理由: これらは正式な金銭取引当事者ではない。final rank に含まれても、金銭 record は無い。金額0の buyer・seller とは区別する。金額0の buyer・seller は金銭 record が存在し、role が buyer または seller である。非参加と区分4は金銭 record が存在しない。

補償額0の seller は正式な seller なので必ず記録する。apply は原因を再判定しない。原因の再計算もしない。

上流の経済 record に原因は残る。それに加え、成立時 record が `declared_vot_per_second`、`baseline_passage_timestep`、`candidate_passage_timestep` を持つため、個別履歴だけでも次を区別できる。

- `candidate_passage_timestep` と `baseline_passage_timestep` が同じであるため、予想遅延が0である。
- `candidate_passage_timestep` が `baseline_passage_timestep` より早いため、補償対象の予想遅延が0である。
- `candidate_passage_timestep` が `baseline_passage_timestep` より遅いが、`declared_vot_per_second` が0であるため、補償額が0である。

申告 VOT が0の場合も、その0を履歴から落とさない。落とすと、遅延が無かった場合と区別できなくなる。

seller role を buyer へ変更しない。補償0を理由に record を削除しない。

## 13. 成立時recordとactual outcomeの分離

成立時 record へ、次の未確定 field を `None` でも置かない。

- actual passage timestep
- 実績時間節約
- 実績遅延
- 実績ベース参考支払額
- 実績ベース参考補償額
- realized gain
- satisfaction classification

成立時 record を後から書き換えない。未確定値と、record がまだ無いことを混同しないためである。

後続の actual passage・事後評価部品が、別の frozen actual outcome record を `order_exchange_log` へ追加する。同じ取引識別材料により、成立時 record と actual outcome record を結び付ける。list に複数型が入る場合の区別は `isinstance` とする。種別だけの Enum は、2種類目を実装するまで作らない。

actual outcome 型は後続部品の設計で定める。今回の atomic apply 実装対象には含めない。

## 14. 将来の事後評価

今回は実装しない。後続設計のため、確定方針を残す。atomic apply では計算しない。

buyer の予想時間節約は、`baseline_passage_timestep - candidate_passage_timestep` である。

buyer の実績時間節約は、`baseline_passage_timestep - actual_passage_timestep` である。符号の意味は、正が baseline 予想より早い、0が baseline 予想と同じ、負が baseline 予想より遅い、である。

seller の予想遅延は、`candidate_passage_timestep - baseline_passage_timestep` である。

seller の実績遅延は、`actual_passage_timestep - baseline_passage_timestep` である。符号の意味は、正が baseline 予想より遅い、0が baseline 予想と同じ、負が baseline 予想より早い、である。

baseline 予測には、取引による影響と周辺交通の予想が含まれる。baseline 予測に対する実績差は、制度の予想全体がどの程度外れたかを顕在化する評価値とする。取引だけの純粋な因果効果とは断定しない。

buyer の累計は buyer role の取引だけを合計する。seller の累計は seller role の取引だけを合計する。

## 15. 実績ベース参考金額

正式精算を変更しない補足指標である。`payment_paid` と `payment_received` を、実績に合わせて書き換えない。取引参加者全員の実通過結果が揃った後に計算する。Vehicle 単独では計算できない。同じ取引の buyer と seller 全員をまとめて評価する後続部品の責務とする。

事後評価上の不成立条件:

- buyer の1人でも実績時間節約が正でない。
- または、全 buyer の実績節約価値合計が、全 seller の実績要求補償額合計を下回る。

不成立時: 全 buyer の参考支払額を0にする。全 seller の参考補償額を0にする。

事後評価上も成立する場合:

- 各 buyer の参考支払額は、実績ベースの seller 必要補償総額を、各 buyer の実績節約価値の比率で配分する。
- 各 seller の参考補償額は、正の実績遅延に、成立時 record の `declared_vot_per_second` を掛けた額である。後続評価で `Vehicle.vot_declared` を読み直さない。取引時点の申告 VOT を使う。
- seller の参考補償額は負にしない。
- 実績では早く通過した seller を buyer へ変更しない。

## 16. buyer・seller別の累計評価

同一 Vehicle が走行中に buyer にも seller にもなり得る。役割別に集計する。

buyer: 正式支払額累計。予想時間節約累計。実績時間節約累計。buyer 取引回数。予想と実績の差。buyer 実績利得。

seller: 正式補償額累計。予想遅延累計。実績遅延累計。seller 取引回数。予想と実績の差。seller 実績利得。

新しい Vehicle 累計属性は現段階で追加しない。個別履歴から役割別に集計する。成立時 record があれば、正式金額、予想通過時刻の組、`declared_vot_per_second`、`true_vot_per_second`、順位変化、取引回数の元が取れる。実績累計は、後続 record が実通過 timestep を持ってから足す。実績利得に使う真の VOT は、成立時 record の `true_vot_per_second` であり、評価時点の `Vehicle.vot_true` ではない。

## 17. 満足・不満足評価

今回の atomic apply では計算しない。計算に使う true VOT は、成立時 record の `true_vot_per_second` である。評価時点の `Vehicle.vot_true` を読み直さない。

直接的な最終判定:

- buyer 実績利得は、true VOT × 実績時間節約累計 − 正式支払額累計である。
- seller 実績利得は、正式補償額累計 − true VOT × 実績遅延累計である。
- 0以上を満足、0未満を不満足とする。

補助的な区分:

buyer:

- 実績時間節約累計が0以下なら、自明な不満足とする。
- 実績時間節約累計が正で、1秒当たり正式支払額が true VOT を超えるなら、価格面の不満足とする。
- 実績時間節約累計が正で、1秒当たり正式支払額が true VOT 以下なら、価格面でも満足とする。

seller:

- 実績遅延累計が0以下なら、自明な満足とする。
- 実績遅延累計が正で、1秒当たり正式補償額が true VOT 未満なら、補償面の不満足とする。
- 実績遅延累計が正で、1秒当たり正式補償額が true VOT 以上なら、補償面でも満足とする。

実績時間累計が0以下の場合、1秒当たり金額の割り算は行わない。直接的な実績利得で最終判定し、割り算指標で満足・不満足の理由を区分する。

## 18. 全件事前検査

最初の実書込み前に、全 Node と全 Vehicle について確認する。validation の再実行はしない。validation は live 状態を見ていない。再実行しても、書込み直前の台帳と Vehicle のずれは検出できない。

### 18.1 公開入力

- validation result の正式型。
- `real_W` の正式型。`World` であること。
- `rank_states_by_node_name` の Mapping 契約。
- mapping の各値が `OrderControlTvtNodeRankState` であること。
- validation result 内の final rank set を、その結果が保持する同一 object 参照で使用すること。
- upstream 計算を再実行しないこと。

### 18.2 全体

- Node 結果列。
- Node 件数。
- Node 名の重複が無いこと。
- 保存順を維持すること。
- `real_W.T` と保存済み成立時刻 `T` が一致すること。
- baseline 時刻の保存値同士が一致すること。

### 18.3 Node

- `real_W.get_node` で対象 Node が存在すること。
- `rank_states_by_node_name` に全対象 Node が存在すること。
- `rank_state.node_name` が一致すること。
- 空 Node でも mapping 欠落を拒否すること。
- final rank の VisitKey が重複しないこと。
- 対象 Visit が rank state で undetermined として登録済みであること。
- 対象 Visit が既確定でないこと。
- formal route が、現在の実 Node の outlink 名集合に存在すること。
- final rank の保存順を維持すること。
- `final_local_rank` を絶対順位と誤解しないこと。

### 18.4 Vehicle

- buyer と seller の Vehicle が `real_W.VEHICLES` に存在すること。
- VisitKey の `vehicle_name` と record の `vehicle_name` が一致すること。
- `payment_paid` が bool でない有限数であること。
- `payment_received` が bool でない有限数であること。
- 現在値が非負であること。
- 更新後値が有限かつ非負であること。
- `order_exchange_log` が list であること。
- 保存済み金額を使用すること。
- 金額式を再計算しないこと。
- 金額0でも成立時 record を作ること。
- 同一 `vehicle_name` の複数金銭 record を、現行契約では拒否すること。
- 正式な buyer または seller の live Vehicle に `vot_true` があること。
- `vot_true` が bool でない有限の非負数であること。`None`、bool、int または float でない値、NaN、無限大、負は拒否すること。`vot_true` が0は正常であること。
- 保存済み経済 record の `declared_vot_per_second` を成立時 record へ使うこと。
- live な `Vehicle.vot_declared` を再読取りしないこと。
- `true_vot_per_second` は live な `Vehicle.vot_true` から prepare 時に読み、成立時 record へ固定すること。
- `vot_true` とその他の live Vehicle 属性を変更しないこと。
- 1台でも `vot_true` が不正なら、順位、金銭、履歴を一切変更せず `RuntimeError` とすること。

### 18.5 履歴材料

- selected candidate の取引識別材料が取れること。
- `baseline_local_rank` が `candidate_visits` から一意に取得できること。
- `post_trade_local_rank` が、selected の general trade rank から一意に取得できること。
- `ledger_assigned_rank` が prepare 時に一意に決まること。
- baseline passage timestep が economic record に存在すること。
- candidate passage timestep が economic record に存在すること。
- `declared_vot_per_second` が、対応する buyer または seller の経済 record の保存済み値と一致すること。
- `Vehicle.vot_declared` を再読取りしないこと。
- 申告 VOT が0でも成立時 record へ保存すること。
- `true_vot_per_second` が、prepare 時の `Vehicle.vot_true` を float で固定した値であること。
- 非参加、区分4、fallback、`NO_VISITS_TO_CONFIRM` では成立時 record を作らず、その Visit の `vot_true` を履歴材料として読まないこと。
- buyer または seller の role と金銭 record が対応すること。
- formal route が final rank record と対応すること。
- buyer と seller 以外に成立時 record を作らないこと。

## 19. Vehicle prepare

Vehicle ごとに、次の準備済み状態を作る。

- `updated_payment_paid`
- `updated_payment_received`
- `updated_order_exchange_log`

新しい log は、既存 list の copy へ成立時 record を加えた新しい list とする。既存 list へ in-place の `append` をしない。commit 前に、全 Vehicle 分の新しい list を完成させる。

同一 Vehicle が buyer と seller の両方、または複数金銭 record に現れた場合は、現行契約では commit 前に `RuntimeError` とする。既存 log に既に入っている要素の形式は、今回の成立時 record の検査対象にしない。今回追加する要素だけを本仕様の型にする。既存 list が list であることだけを要求する。

## 20. commit順

commit 開始前に、全 Node の順位候補と、全 Vehicle の更新後状態を完成させる。

実 commit 順:

1. 書込み対象の全 Node について、順位台帳の内部4状態を置換する。
2. 全対象 Vehicle の `payment_paid` を、準備済みの値へ置換する。
3. 全対象 Vehicle の `payment_received` を、準備済みの値へ置換する。
4. 全対象 Vehicle の `order_exchange_log` を、新しい list へ置換する。

理由: 順位を先に残すと、commit 途中の致命的終了後に再実行した場合、既確定 Visit として停止できる。金銭を先に書くと、順位が未確定のまま再実行され、累計金額を二重加算する危険がある。金銭の二重加算より、順位だけ確定して停止し、人が不整合を検知する状態を優先する。

この順序でも、順位 commit 後かつ金銭 commit 前の致命的終了による部分状態は自動修復しない。通常の検査失敗による部分更新を防ぐ設計である。完全な transaction ではない。

空 Node と、金銭 record が無い fallback Visit は、2から4の対象に入らない。fallback で final rank 列がある Node は、1の順位 commit の対象である。

## 21. 成功結果型

成功結果型の正式名称は `OrderControlTvtMpAtomicApplySetResult` である。`dataclass(frozen=True)` とする。

field は `final_consistency_validation_set_result` の1つだけとする。入力 validation result と同一 object 参照を保持する。

保持しないもの: live World。live Node。live Vehicle。live rank state。mutable list。mutable dict。Node 別件数。Vehicle 別金額の複写。failed status。boolean だけの承認 token。

Node 別件数と金額は、入力 frozen 結果と適用後の台帳から確認できる。結果へ重複保存しない。

## 22. ValueErrorとRuntimeError

`ValueError` は、公開3引数の外部入力型が正式型でない場合だけである。validation 結果型でない、`World` でない、mapping でない、mapping の値が `OrderControlTvtNodeRankState` でない、が該当する。

`RuntimeError` は、型は正式だが、保存済み結果または live 状態が矛盾する場合である。

主な `RuntimeError`: Node 件数・順序・名前の不一致。Node 名の重複。時刻不一致。対象 Node の欠落。rank state mapping の欠落。`rank_state.node_name` の不一致。Visit 未登録。Visit 既確定。Visit 重複。formal route が実 outlink に無い。Vehicle 欠落。Vehicle 名不一致。金銭属性の型不正。金銭属性が非有限。金銭属性が負。更新後金額が非有限または負。`order_exchange_log` が list でない。同一 Vehicle の複数金銭 record。baseline 順位を一意に取得できない。post-trade 順位を一意に取得できない。passage timestep を取得できない。trade role の不一致。取引識別材料の不一致。正式な buyer または seller の `vot_true` が無いこと。`vot_true` が `None`、bool、int または float でない、NaN、無限大、または負であること。

正常であり `RuntimeError` にしないもの: 分岐2から5。fallback。`NO_VISITS_TO_CONFIRM`。空 Node。seller 0件。補償額0の seller。支払額0の buyer。非参加 Visit に履歴が無いこと。区分4 Visit に履歴が無いこと。`vot_true` が0であること。`declared_vot_per_second` と `true_vot_per_second` が異なること。

## 23. 不変性

失敗時に変更しないもの: validation result。final rank result。payment result。selection result。economic result。local result。FIFO result。collector。全 rank state。全 Vehicle の `payment_paid`。全 Vehicle の `payment_received`。全 Vehicle の `order_exchange_log`。World。Node。Link。RNG。`vot_declared`。`vot_true`。`participates_in_order_exchange`。

成功時に変更するものだけ:

- final rank 列がある Node の rank state。空 Node の rank state は変えない。
- buyer の `payment_paid`。
- seller の `payment_received`。
- buyer と seller の `order_exchange_log`。

成功時も変更しないもの: `vot_true`。`vot_declared`。`participates_in_order_exchange`。成立時 record へ写したあとも、Vehicle 上の値は変えない。

fallback の Node は、final rank 列があるなら rank state だけを変える。累計と履歴は変えない。非対象 Node と非対象 Vehicle は変えない。

## 24. 上位driverとの境界

上位 driver は未実装である。本部品では実装しない。

上位 driver が行うこと:

- `rank_states_by_node_name` を保持する。
- 全 Node の処理チェーンを正式順に呼ぶ。
- final consistency validation を1回呼ぶ。
- 成功した validation result で atomic apply を1回呼ぶ。
- apply の例外を成功扱いにしない。
- apply 成功後だけ次の処理へ進む。

上位 driver が行わないこと:

- Node 単位の部分 apply。
- final rank の再構築。
- 金額の再計算。
- buyer と seller の対応の再照合。
- 履歴 record の構築。
- rollback。
- 原因別5分岐の再実装。
- actual passage の評価。
- 実績参考金額の計算。
- 満足評価。

呼出し境界は、baseline 時刻で driver が明示的に1回呼ぶ側である。`Node.transfer` の途中や `user_function` の途中へ apply を入れない。現在の `Node.transfer` は `fcfs` と `batch` だけを特別扱いし、`time_value` の確定順位は通過順に使っていない。その物理的利用は本部品の外である。

## 25. 責務外

`Node.transfer` による TVT 確定順位の物理的利用。実 World の通過順制御。actual passage record。prediction error。実績時間節約。実績遅延。実績ベース参考支払額。実績ベース参考補償額。realized utility。satisfaction classification。welfare。上位 driver。strategy-proofness。文献制度の移植。

## 26. 可読性

正しさを最優先する。Python 初学者が後から追える明示的な実装にする。明示的な Node ループ。明示的な Vehicle ループ。意味のある中間変数。小さすぎる helper への過剰分割を避ける。長い内包表記を避ける。複雑な generator を避ける。commit 前と commit 後の境界をコード上で明確にする。原因と結果をコメントへ明記する。upstream 計算を再実行しない。live object を履歴へ保存しない。

## 27. 専用テスト契約

新規予定ファイルは `tests_order_control_tvt_mp_atomic_apply.py` である。Python 実装と専用テストは未着手である。

### 27.1 公開型とAPI

公開 API は全 Node 一括の1関数 `apply_tvt_mp_validated_result` である。位置引数3つ。optional なし。成功結果型は `OrderControlTvtMpAtomicApplySetResult` で frozen である。field は `final_consistency_validation_set_result` の1つだけであり、入力 validation result と同一 object 参照を保持する。成立時履歴型は `OrderControlTvtMpTradeEstablishmentLogRecord` である。live object を保持しない。

専用テストは、少なくとも次を正式名称として照合する。

- 公開関数名が `apply_tvt_mp_validated_result` である。
- 成功結果型が `OrderControlTvtMpAtomicApplySetResult` である。
- 成立時履歴型が `OrderControlTvtMpTradeEstablishmentLogRecord` である。
- 成立時刻 field が `tvt_decision_timestep` である。
- `tvt_decision_timestep` が、上流 `baseline_timestep_T` および `real_W.T` と一致する。
- 成立時 record の field 名と field 順が §11.9 の正式契約どおりである。
- 取引識別は、`tvt_decision_timestep`、`node_name`、`buyers_sorted` の平坦な3 field である。
- `OrderControlTvtMpTradeIdentity` 型を現段階では作らない。
- `binding_rank` と `final_local_rank` を成立時履歴へ保存しない。

### 27.2 正常selected

Node 順位と formal route が反映される。buyer の `payment_paid` が増える。seller の `payment_received` が増える。buyer と seller の成立時履歴が増える。金額は保存済み値である。金額式を再計算しない。0円 buyer を記録する。0円 seller を記録する。非参加と区分4に履歴が無い。

### 27.3 順位履歴

`baseline_local_rank` は `candidate_visits` の正式 baseline 順である。`post_trade_local_rank` は selected の general trade rank である。`rank_change` の符号を固定する。`ledger_assigned_rank` は既存 `k_confirmed` を含む絶対順位である。`binding_rank` を履歴に保存しない。`final_local_rank` を履歴へ重複保存しない。先行確定済み Visit が存在する場合も、3順位の意味が崩れない。

### 27.4 passage履歴

buyer と seller の経済 record の baseline passage timestep を使用する。candidate passage timestep を使用する。局所仮想計算を再実行しない。actual field を成立時 record へ置かない。

### 27.4.1 成立時VOT

buyer の成立時 record に `declared_vot_per_second` と `true_vot_per_second` が保存される。seller の成立時 record にも両方が保存される。`declared_vot_per_second` は経済 record の保存値を使い、live な `Vehicle.vot_declared` を再読取りしない。`true_vot_per_second` は apply 時の live な `Vehicle.vot_true` を float で保存する。申告 VOT が0でも保存する。`declared_vot_per_second` と `true_vot_per_second` が異なっていても正常である。`true_vot_per_second` が0でも正常である。`vot_true` が `None`、負、NaN、無限大、bool のいずれかなら、全体を無変更のまま拒否する。非参加 Visit と区分4 Visit には成立時 record を作らない。atomic apply は true VOT を金額計算や成立判定へ使わない。`Vehicle.vot_true` と `Vehicle.vot_declared` を変更しない。将来 live Vehicle の VOT が変わっても、既存の成立時 record の保存値は変わらない。

### 27.5 fallbackと空Node

fallback は順位と formal route だけを反映する。fallback では累計金額と履歴は不変である。`NO_VISITS_TO_CONFIRM` は全台帳が不変である。空 Node も mapping の存在を要求する。Node 結果を脱落させない。

### 27.6 全体atomic性

2 Node 目の不整合で1 Node 目も未変更である。Vehicle 不整合で全 Node が未変更である。outlink 不整合で全 Node と全 Vehicle が未変更である。金銭属性の不整合で全 Node と全 Vehicle が未変更である。log の型不正で全 Node と全 Vehicle が未変更である。同一 Vehicle の複数 record で全体が未変更である。`real_W.T` の不一致で全体が未変更である。`vot_true` の欠落または不正で全体が未変更である。

### 27.7 既存順位API回帰

既存公開 API の正常動作を維持する。空入力 no-op を維持する。既確定拒否を維持する。未登録拒否を維持する。route 不正拒否を維持する。candidate verification 失敗時の無変更を維持する。`tests_order_control_tvt_node_rank_state.py` を回帰対象にする。

### 27.8 不変性

upstream の frozen 結果は不変である。collector は不変である。World RNG は不変である。order-control RNG は不変である。非対象 Vehicle は不変である。非対象 Node は不変である。

## 28. 反証して採用しない事項

採用しないもの:

- Node 単位の公開 apply。
- Node ごとの validation 直後の部分反映。
- 既存公開 Node API の単純な順次呼出し。検査を複製し、1か所でもずれると先行 Node が残る。
- apply での金額再計算。
- apply での順位再構築。
- apply での baseline 再実行。
- apply での局所仮想計算の再実行。
- commit 中の検査。
- commit 中の金額加算の計算。
- commit 中の `log.append`。
- rollback 前提。
- World 全体の copy。
- live object の履歴への保存。
- `order_exchange_log` を二重適用防止の唯一の正本にすること。
- 金額0の buyer または seller の記録を省略すること。
- actual field を成立時 record へ `None` で追加すること。
- 成立時 record を後から変更すること。
- `binding_rank` を順位交換の前後比較に使うこと。
- `final_local_rank` と `post_trade_local_rank` を重複保存すること。
- 非参加または区分4を、0円の取引相手として記録すること。
- actual passage による正式金額の事後精算。
- 同一 Vehicle の複数 record を黙って合算すること。
- 致命的なプロセス終了まで完全な transaction であると主張すること。

## 29. 実装範囲と未実装範囲

実装範囲（保存後の次作業）: 全 Node 一括の公開 API。成功結果型。成立時履歴型。全件 live 検査。全 Node の順位 prepare。全 Vehicle の金銭と履歴の prepare。prepare 完了後の commit。既存順位台帳の内部 prepare と commit の分割。金額0の buyer と seller の履歴。専用テスト。既存順位台帳の回帰。関係回帰。独立確認。

未実装範囲: actual outcome record。physical passage の制御。上位 driver。actual passage の評価。実績参考金額。buyer と seller 別の累計分析。満足評価。welfare。strategy-proofness。文献制度の移植。

本節の記録は実装完了ではない。

## 30. 正式名称とfield構成の確定

本節で固定した意味は、未確定へ戻さない。公開関数名、成功結果型名、成立時履歴型名、成立時刻 field 名、取引識別の持ち方、履歴 field 名、履歴 field 順は、利用者確認と独立確認の後に正式確定した。

既存の命名は、`validate_tvt_mp_final_consistency`、`build_tvt_mp_final_ranks`、`OrderControlTvtMpFinalConsistencyValidationSetResult`、`OrderControlTvtMpBuyerPaymentRecord` のように、処理を表す関数名と、`OrderControlTvtMp` で始まる frozen 型名である。field は snake_case で、既存結果の field 名を重ねられるときは重ねる。

名称候補（判断経緯・歴史的比較）:

| 対象 | 推奨候補 | 理由 | 代替 |
| --- | --- | --- | --- |
| 公開関数 | `apply_tvt_mp_validated_result` | validation 成功結果を live へ反映する、という引数の意味と一致する | 実装前に別名へ変える場合でも、引数3つと全 Node 一括は変えない |
| 成功結果型 | `OrderControlTvtMpAtomicApplySetResult` | 既存の set result 命名と一致する | なしを第一候補とする |
| 成立時履歴型 | `OrderControlTvtMpTradeEstablishmentLogRecord` | 成立時であり、actual outcome ではないことが型名で分かる | 実装前に短縮する場合でも、共通1型であることは変えない |
| 成立時刻 field | `baseline_timestep_T` | 上流 frozen 結果と同じ整数と同じ field 名である。docstring に、実 World の成立判断時刻であり別仮想時刻ではない、と書く | `tvt_decision_timestep`。単独で読むと成立時刻であることが分かりやすい。上流名とは揃わない |
| 取引識別 | record 上の `node_name`、成立時刻、`buyers_sorted` | 新しい識別型を増やさず、seller の1行から取引全体が分かる | ネストした frozen 識別型。情報は増えない。actual record との共有が目的なら後続で切る |
| baseline 順位 | `baseline_local_rank` | `candidate_visits` 内であり、台帳絶対順位ではない | なしを第一候補とする |
| 取引後順位 | `post_trade_local_rank` | 同じ母集団の取引後順位である。`final_local_rank` とは重複保存しない | なしを第一候補とする |
| 台帳絶対順位 | `ledger_assigned_rank` | `k_confirmed + final_local_rank` であり、台帳へ書く順位である | なしを第一候補とする |
| 今回支払・受取 | `payment_paid_in_this_transaction`、`payment_received_in_this_transaction` | 累計の `payment_paid`、`payment_received` と、今回額を名前で分ける | なしを第一候補とする |
| 成立時の申告 VOT | `declared_vot_per_second` | 経済 record の field 名と揃える。取引時点の申告 VOT である | なしを第一候補とする |
| 成立時の真の VOT | `true_vot_per_second` | 申告 VOT と対になる。取引時点の `Vehicle.vot_true` を float で固定する | なしを第一候補とする |

### 30.1 正式採用結果

| 対象 | 正式名称 |
| --- | --- |
| 公開関数 | `apply_tvt_mp_validated_result` |
| 成功結果型 | `OrderControlTvtMpAtomicApplySetResult` |
| 成功結果 field | `final_consistency_validation_set_result`（入力 validation 結果と同一 object 参照） |
| 成立時履歴型 | `OrderControlTvtMpTradeEstablishmentLogRecord` |
| 成立時刻 field | `tvt_decision_timestep`（値は上流 `baseline_timestep_T` と `real_W.T` と同じ整数。prepare 時に上流値を写す） |
| 取引識別 | 平坦な3 field：`tvt_decision_timestep`、`node_name`、`buyers_sorted`。`OrderControlTvtMpTradeIdentity` は現段階では作らない |
| 成立時 record field 順 | §11.9 の17 field（`binding_rank` と `final_local_rank` は含めない） |

`declared_vot_per_second` と `true_vot_per_second` を成立時 record へ保存することは確定済みである。上表の名称判断は解消済みである。`baseline_timestep_T` か `tvt_decision_timestep` か、TradeIdentity 型を作るか、正式な型名・field 名は、未決事項として残さない。

## 31. 次の再開地点

1. 正式名称と field 構成は確定済みである。
2. Terminal で詳細設計第3巻の本節（§5、§6、§11、§21、§27、§30）を限定表示し、内容を独立確認する。
3. 進捗第2巻の要約が本節と一致することを確認する。
4. 両文書の差分を確認する。
5. `git diff --check` を実行する。
6. 文書2ファイルだけが変更されていることを確認する。
7. 利用者の確認後に commit する。
8. commit と push は分ける。
9. メモを含む commit 名には `document` を含める。
10. 保存後に、atomic apply 本番実装と専用テストの実装へ進む。
11. 実装では、新規本番モジュール、新規専用テスト、順位台帳の内部 prepare と commit の分離を扱う。
12. Cursor 実装後は、実コードと専用テストを独立確認する。

本節は完全実装前仕様である。上記 §31 は実装着手前の再開地点の保存である。Python 実装と専用テストは、当時は未着手であった。実装・検証完了後の記録と最新の再開地点は §32 を参照する。

## 32. TVT-MP atomic apply部品・実装検証結果（2026-09-27）

**記録日: 2026-09-27**

保存済み完全実装前仕様（本大見出しの §1–§31）に従って実装・検証した。上記 §1–§31 は歴史的な実装前仕様として残す。最新の実装完了事実は本節 §32 を参照する。

atomic apply による Python 変更は、次の3ファイルだけである。

### 32.1 実装ファイル

| 区分 | パス |
| --- | --- |
| 新規本番 | `uxsim/order_control_tvt_mp_atomic_apply.py` |
| 新規専用テスト | `tests_order_control_tvt_mp_atomic_apply.py` |
| 既存変更 | `uxsim/order_control_tvt_node_rank_state.py` |

### 32.2 公開型と公開API

**公開関数** `apply_tvt_mp_validated_result` — 位置引数3つ（`final_consistency_validation_set_result`、`real_W`、`rank_states_by_node_name`）。optional なし。全 Node 一括。Node 単位・Vehicle 単位の公開 apply なし。

**成功結果型** `OrderControlTvtMpAtomicApplySetResult`（frozen）— field は `final_consistency_validation_set_result` の1つだけ。入力 validation 結果と同一 object 参照。live object、mutable state、Node 別複写、failed status、boolean 承認 token を保持しない。

**成立時履歴型** `OrderControlTvtMpTradeEstablishmentLogRecord`（frozen）— 17 field を §11.9 の順序どおり実装。`binding_rank` と `final_local_rank` は履歴へ保存しない。

**成立時履歴 role 型** `OrderControlTvtMpTradeEstablishmentRole` — `BUYER` と `SELLER` だけ。既存 `OrderControlTvtMpLocalBindingTradeRole` は `NONPARTICIPATING` と `OUTSIDE_TRADE_SCOPE` も含むため、成立時履歴の field 型には使用しなかった。意味は実装前仕様どおりである。

**取引識別** — `OrderControlTvtMpTradeIdentity` は作らない。各成立時 record が平坦に `tvt_decision_timestep`、`node_name`、`buyers_sorted` を保持する。

### 32.3 順位台帳のprepare・commit分離

`OrderControlTvtNodeRankState` 内に、private prepared-state、`_prepare_formal_route_confirmation`、`_commit_prepared_formal_route_confirmation` を実装した。

既存公開 API `confirm_visits_and_formal_target_node_routes_atomically` の公開契約は維持した。同一 Node について prepare 直後に commit する。

空入力では `commit_required=False` とし、live 台帳の内部4参照を置換しない。

atomic apply は、全 Node の prepare 完了後だけ、書込み対象 Node を commit する。

### 32.4 全Node一括prepareとcommit

1回の `OrderControlTvtMpFinalConsistencyValidationSetResult` を1 apply 単位とした。全 Node の更新後順位台帳候補と、全対象 Vehicle の `payment_paid`、`payment_received`、新しい `order_exchange_log` を、最初の実書込み前に準備する。1件でも不整合があれば commit へ進まない。2 Node 目の不整合時も1 Node 目を変更しない。

`NO_VISITS_TO_CONFIRM` は正常な no-op である。空 Node も点検対象から落とさない。空 Node でも `rank_states_by_node_name` の欠落は拒否する。

**commit 順**（全 prepare 成功後のみ）: (1) 全対象 Node の順位台帳内部4状態、(2) 全対象 Vehicle の `payment_paid`、(3) 全対象 Vehicle の `payment_received`、(4) 全対象 Vehicle の新しい `order_exchange_log`（list 代入のみ。commit 中の検査・探索・金額計算・`append` なし）。

### 32.5 順位・正式進路

final rank 列の保存順を維持して順位台帳へ渡す。`formal_route_next_link_name` は final rank record の保存値を使い、World や Vehicle から再推定しない。apply 直前に、実 Node の `outlinks.values()` 上の Link 名集合へ含まれることを確認する。

履歴: `baseline_local_rank` は `candidate_visits` の保存順（1始まり）。`post_trade_local_rank` は selected candidate に対応する general trade rank の `assigned_rank`。`rank_change` は `baseline_local_rank - post_trade_local_rank`。`ledger_assigned_rank` は prepare 開始時の `k_confirmed + final_local_rank`。`binding_rank` は取引前後比較に使わない。`final_local_rank` は `post_trade_local_rank` と重複するため履歴に入れない。

### 32.6 累計金額と成立時履歴

buyer: 保存済み `payment_P_b` を `payment_paid` に加算。今回受取額は0。seller: 保存済み `compensation_amount` を `payment_received` に加算。今回支払額は0。

`G`、`R`、`G_b`、`R_s`、payment 式、compensation 式、VOT、passage difference は再計算しない。金額0でも、正式な buyer または seller なら成立時 record を必ず作る。非参加、区分4、fallback、`NO_VISITS_TO_CONFIRM` には成立時 record を作らない。`order_exchange_log` は prepare 時に新 list を完成させ、commit では属性へ代入するだけである。

### 32.7 VOT

**declared_vot_per_second** — 保存済み buyer または seller economic record から取得。`Vehicle.vot_declared` は再読取りしない。有限の非負値を必須とする。0は正常。

**true_vot_per_second** — prepare 時の live `Vehicle.vot_true` から取得。有限の非負値を必須とする。0は正常。成立時 record へ float で固定する。成立判定・正式金額計算には使わない。

`Vehicle.vot_true` と `Vehicle.vot_declared` は変更しない。

### 32.8 独立確認で発見した問題と修正

独立確認で、保存済み `declared_vot_per_second` について、数値型と有限性は確認していたが、**非負検査が不足**していることを発見した。

- **原因:** `_require_declared_vot` が `value < 0` を拒否していなかった。
- **修正:** 負値を `RuntimeError` とした。0と正の有限値は正常。上流経済性評価の申告 VOT 契約と一致させた。
- **テスト追加:** buyer 側・seller 側の負値 declared VOT で、全 Node 順位・全 Vehicle 累計・全 Vehicle 履歴が完全無変更の `RuntimeError` を専用テストで固定した。

### 32.9 専用テスト

ファイル: `tests_order_control_tvt_mp_atomic_apply.py`

- 定義済み `test_` 関数: **38**
- `TESTS` 登録: **38**
- pytest 収集: **38**
- 重複なし、登録漏れなし、未定義参照なし
- 直接実行: 38件成功
- pytest 専用: 38件成功

公開契約、selected 正常系、履歴 field、fallback・空 Node、全体 atomic 性、commit 境界、入力型の `ValueError`／live 不整合の `RuntimeError` を固定した。

### 32.10 独立確認と回帰結果

**py_compile 成功:** `uxsim/order_control_tvt_mp_atomic_apply.py`、`uxsim/order_control_tvt_node_rank_state.py`、`tests_order_control_tvt_mp_atomic_apply.py`

**独立確認として Terminal で実行した関連 pytest:**

- `tests_order_control_tvt_node_rank_state.py`
- `tests_order_control_tvt_mp_final_consistency_validation.py`
- `tests_order_control_tvt_mp_final_rank.py`
- `tests_order_control_tvt_mp_payment_and_compensation.py`
- `tests_order_control_tvt_mp_atomic_apply.py`

**結果: 246 passed**（約20.11秒）。失敗なし。回帰なし。

Cursor 側の追加回帰では、参照関係の leading confirmation と general trade rank を含む **409 passed** も報告されている。正式記録として独立確認で直接実行した件数は **246** とする。409 は Cursor 実行結果として区別する。

`git diff --check` は問題なし。

### 32.11 可読性確認

実装上確認したもの: 明示的な Node ループ、明示的な buyer・seller ループ、意味のある中間変数、prepare と commit の明確な境界、小さな private helper。長い内包表記や複雑な generator は避けた。短さより、Python 初学者が後から処理順を追える構造を優先した。

正しさと契約検査を優先するため、本番モジュールは長い。長いこと自体を理由に統合・短縮しない。

### 32.12 実装済み範囲

- atomic apply 本番
- 成功結果型
- 成立時履歴型
- role 型
- 全 Node 一括 prepare
- 全 Vehicle 金銭・履歴 prepare
- commit
- 順位台帳内部 prepare・commit 分離
- 0円 buyer・seller 履歴
- VOT 保存
- 専用テスト
- 関係回帰
- 独立確認

### 32.13 未実装範囲

- actual outcome record
- actual passage 評価
- `Node.transfer` による TVT 確定順位の物理通過利用
- 上位 driver
- 実績参考支払額・補償額
- buyer・seller 別累計分析
- 実績利得
- 満足評価
- welfare
- strategy-proofness

### 32.14 次の再開地点

1. 詳細設計第3巻の本節 §32 を Terminal で限定確認する。
2. 進捗第2巻の実装完了要約を Terminal で限定確認する。
3. `git diff --check` を実行する。
4. 変更ファイルを確認する（文書2ファイル、Python3ファイル、専用テスト1ファイル）。
5. 文書と Python・テストをまとめて commit する。
6. commit 名には `document` を含める。
7. commit と push を分ける。
8. push 後に UXsim 正式サンプルのスモークテストを実施するか判断する。
9. その後、次の未実装部品の設計へ進む。

**再開地点の更新（2026-09-27・実装後スモークテスト後）**

- 実装後スモークテストまで完了した。
- 次は結果の限定確認、文書 commit・push である。
- その後、次の未実装部品を検討する。

### 32.15 UXsim正式サンプル・実装後スモークテスト

atomic apply 実装・関連テスト・独立確認・push 後に、UXsim 正式サンプルによるスモークテストを実施した（実行日: 2026-09-27）。

**実行コマンド**

```text
python demos_and_examples/example_00en_simple.py
```

- `demos_and_examples/example_00en_simple.py` は変更せず実行した。

**シミュレーション設定**

- simulation duration: 1200 s
- number of vehicles: 810
- total road length: 3000 m
- timestep size: 5 s
- platoon size: 5 veh
- number of timesteps: 240
- number of platoons: 162
- number of links: 3
- number of nodes: 4

**実行状況**

- 1200 秒まで正常に完走した。
- exception は発生しなかった。
- `simulation finished` を確認した。

**主要交通結果**

- average speed: 11.7 m/s
- completed trips: 735 / 810
- total travel time: 119475.0 s
- average travel time: 162.6 s
- average delay: 62.6 s
- delay ratio: 0.385
- total distance traveled: 1632250.0 m

**確認範囲と限界**

- 本正式サンプルから atomic apply（`apply_tvt_mp_validated_result` 等）は直接呼ばれていない。
- したがって、本スモークテストが確認するのは、atomic apply 関連の新規モジュール追加と順位台帳内部整理が、TVT を使わない従来 UXsim の基本動作を壊していないことである。
- atomic apply 自体の正しさは、専用テスト 38 件と関連テスト 246 件で別途確認済みである。
- 本スモークテストだけで atomic apply の実処理経路を確認したとは記録しない。

# TVT-MP actual passage・事後評価・役割別累計の将来仕様

記録日: 2026-09-27

本節は進捗要約ではない。atomic apply 検討中に確定した actual passage、事後評価、役割別累計の将来仕様を、後日このチャットを参照せずに設計と実装を再開できる詳細設計として記録する。本節は実装完了の記録ではない。上位 driver より後の後続部品の仕様である。既存節を改訂しない。atomic apply の成立時 record 契約を未確定へ戻さない。

## 記録品質

議論で確定した定義、数式、正負と0の意味、計算順序、取引全体で評価する事項、Vehicle 単独で評価できない事項、buyer と seller の違い、正式金額と参考金額の違い、満足・不満足の最終判定、割り算指標による理由分類、分母が0以下の場合、同じ Vehicle が buyer にも seller にもなる場合、成立時 record と actual outcome record の分離、declared VOT と true VOT の役割、将来 VOT が取引ごとに変化する場合、未確定事項、後続実装に必要な処理、再開手順を省略しない。簡潔さを理由に事項を統合または省略しない。同じ結論に至った理由も記録する。結果だけでなく原因を記録する。

## 1. 目的

取引成立時に予想した時間短縮または遅延と、実際の対象 Node 通過結果を比較する。

評価対象は、単なる取引だけの因果効果とは限定しない。

原因: baseline 予測と candidate 予測は、取引による順位変化だけを含むのではない。局所仮想計算で予想した周辺交通の動きも含む。したがって、実績差の原因は、順位交換そのものに限られない。周辺車の動き、下流境界、通過可能時刻の予測誤差も含まれる。

結果として扱う意味: baseline 予測に対する実績差は、制度が事前に行った交通予測全体が、実際にどこまで実現したか、または外れたかを示す値である。「取引によって生じた遅延または短縮の完全な因果効果」とは断定しない。因果効果として断定すると、周辺交通の予測誤差まで取引の効果として帰属させることになる。その帰属は本節では採用しない。

比較の出発点は、atomic apply が成立時 record へ保存した `baseline_passage_timestep` と `candidate_passage_timestep` である。実績側の比較対象は、後続部品が捕捉する `actual_passage_timestep` である。

## 2. atomic applyとの責務境界

atomic apply が既に成立時 record へ保存する情報は、次の17 field である。field 名と順序は atomic apply の正式契約であり、本節で変更しない。

1. `tvt_decision_timestep`
2. `node_name`
3. `buyers_sorted`
4. `visit_key`
5. `vehicle_name`
6. `trade_role`
7. `baseline_local_rank`
8. `post_trade_local_rank`
9. `ledger_assigned_rank`
10. `rank_change`
11. `formal_route_next_link_name`
12. `baseline_passage_timestep`
13. `candidate_passage_timestep`
14. `payment_paid_in_this_transaction`
15. `payment_received_in_this_transaction`
16. `declared_vot_per_second`
17. `true_vot_per_second`

atomic apply は、次を計算しない。

- actual passage
- 実績時間
- 参考金額
- 実績利得
- 満足判定

atomic apply は、正式支払額と正式補償額を、actual passage に基づいて事後精算しない。

理由: 成立時点の正式金額は、成立時点の予測と申告 VOT に基づく制度上の確定額である。実績が予測と異なっても、追加請求、返金、正式額の書換えを行わない。実績との差は、後続の参考指標と利得評価で扱う。成立時 record へ actual 用 field を `None` で予約すると、未通過の取引と通過済みの取引を同じ record 型で混在させ、後から成立時 record を書き換える設計へ entice する。その設計は採用しない。

## 3. 成立時recordとactual outcome recordの分離

### 3.1 成立時record

- 型名は `OrderControlTvtMpTradeEstablishmentLogRecord` である。
- frozen である。
- 後から変更しない。
- actual 用の field を `None` で持たせない。

理由: 成立時点で確定した予測、順位、正式金額、両 VOT を、実績評価の正本として固定するためである。後続評価時に live Vehicle の VOT や通過時刻を読み直して成立時 record を更新すると、その取引が成立した時点の条件が失われる。

### 3.2 後続部品が追加するactual outcome record

- 別の frozen actual outcome record を `order_exchange_log` へ追加する。
- 成立時 record を書き換えない。

理由: 1取引・1 Vehicle について、成立時点の記録と通過後の記録を別 object として残すためである。通過前は成立時 record だけが存在する。通過後は成立時 record に actual outcome record が追加される。同一 record の field を埋める方式は採用しない。

### 3.3 取引単位の対応

同じ取引であることを識別する3項目は、次である。

- `tvt_decision_timestep`
- `node_name`
- `buyers_sorted`

理由: atomic apply は取引識別型 `OrderControlTvtMpTradeIdentity` を現段階では作らない。成立時 record 上の平坦な3 field が取引識別の正本である。actual outcome 側も、同じ3 field で取引へ対応する。新しい識別型が必要かどうかは、actual outcome の後続設計で決める。本節では新しい識別型を確定しない。

### 3.4 Vehicleごとの対応

同じ取引の同じ Visit であることを識別する項目は、次である。

- `tvt_decision_timestep`
- `node_name`
- `buyers_sorted`
- `visit_key`

理由: 1取引には複数の buyer と複数の seller が属する。Vehicle 名だけでは、同一 Vehicle が別 Visit で再訪した場合と区別できない。VisitKey を含めて対応する。

### 3.5 型名とfield名

actual outcome record の正式型名と field 名は、後続設計時に確定する。本節では未確定のまま残す。確定してはいけない理由は、捕捉場所、完了待ちの主体、出力形式が未確定であり、field 構成がそれらに依存するためである。

## 4. buyerの時間評価

buyer は、取引により baseline 予想より早く対象 Node を通過することを予想して支払う側である。時間評価の向きは「節約」である。遅延の符号を buyer に流用しない。

### 4.1 取引ごとの予想時間節約

```text
予想時間節約 = baseline_passage_timestep - candidate_passage_timestep
```

意味: 成立時点で、baseline 予測通過時刻から candidate 予測通過時刻を引いた値である。正なら、取引により早く通過すると予想していた。0なら、通過時刻は変わらないと予想していた。負なら、buyer でありながら candidate の方が遅いと予想していた。後者は通常の成立条件では想定しにくいが、値を0へ切り上げない。保存済み timestep の差をそのまま記録する。

### 4.2 取引ごとの実績時間節約

```text
実績時間節約 = baseline_passage_timestep - actual_passage_timestep
```

意味: 成立時点の baseline 予測通過時刻から、実際の対象 Node 通過時刻を引いた値である。candidate 予測ではなく baseline 予測を減算の出発点にする。理由: 実績が「取引前の予測全体」に対してどれだけ早いか、または遅いかを見るためである。candidate 予測との差は、予想と実績の差として別に保存する。

### 4.3 符号

- 正: baseline 予想より早く通過した。
- 0: baseline 予想と同じ時刻に通過した。
- 負: 時間節約を予想していたが、実際には baseline 予想より遅く通過した。負値は、予想の有無にかかわらず、実績が baseline より遅いことを表す。

負値を0へ切り上げない。マイナスの時間節約として記録し、累積する。

理由: 切り上げると、遅く通過した取引が「節約0」になり、早く通過した取引と区別できなくなる。累計でも、遅れた取引のマイナスが消えると、早く通過した取引のプラスだけが残る。実績の外れを隠すことになるため、切り上げは採用しない。

### 4.4 集計範囲

buyer role の取引だけを集計する。同じ Vehicle の seller 取引の時間を混ぜない。

### 4.5 buyerについて保存・集計する値

- 取引ごとの予想時間節約
- 取引ごとの実績時間節約
- 取引ごとの予想と実績の差
- 予想時間節約累計
- 実績時間節約累計
- buyer 取引回数
- 正式支払額累計
- buyer 実績利得

取引ごとの予想と実績の差は、次である。

```text
予想と実績の差 = 予想時間節約 - 実績時間節約
```

展開すると、次と同一である。

```text
予想と実績の差 = actual_passage_timestep - candidate_passage_timestep
```

【2026-10-02 最新仕様による注記】

- 上記の引き算の向きは、過去のCopilotが利用者の明示確認なしに導入した記述であり、利用者合意済みの確定仕様ではなかった。
- 上記の向きでは、buyerがcandidate予測より早く通過して予測以上の時間節約を得た場合に負となる。
- 新規実装では使用しない。
- 最新仕様では、共通保存値を次とする。

```text
candidate_minus_actual_passage_timesteps
= candidate_passage_timestep - actual_passage_timestep
```

- buyerの最新role別指標は次とする。

```text
predicted_based_actual_saving_timesteps
= candidate_minus_actual_passage_timesteps
```

- 正は、実際の通過がcandidate予測より早く、buyerが予測以上の時間節約を得たことを表す。
- 負は、実際の通過がcandidate予測より遅く、buyerの時間節約が予測を下回ったことを表す。
- 最新の正式参照先は、第4巻末尾
  「TVT-MP actual passage基盤 実装項目1の確定設計・実装・検証結果（2026-10-02）」
  §5および§6である。

正なら、実績通過が candidate 予測より遅い。負なら、実績通過が candidate 予測より早い。0なら、candidate 予測どおりである。この差も切り上げない。

## 5. sellerの時間評価

seller は、取引により baseline 予想より遅く対象 Node を通過することを予想して補償を受け取る側である。時間評価の向きは「遅延」である。buyer の節約式を符号反転しただけの別名として扱わず、seller 専用の式で記録する。理由: 符号の向きを役割ごとに固定し、後続実装で引き算の左右を取り違えないためである。

### 5.1 取引ごとの予想遅延

```text
予想遅延 = candidate_passage_timestep - baseline_passage_timestep
```

意味: 成立時点で、candidate 予測通過時刻から baseline 予測通過時刻を引いた値である。正なら、取引により遅く通過すると予想していた。0なら、通過時刻は変わらないと予想していた。負なら、seller でありながら candidate の方が早いと予想していた。値を0へ切り上げない。

### 5.2 取引ごとの実績遅延

```text
実績遅延 = actual_passage_timestep - baseline_passage_timestep
```

意味: 実際の対象 Node 通過時刻から、成立時点の baseline 予測通過時刻を引いた値である。

### 5.3 符号

- 正: baseline 予想より遅く通過した。
- 0: baseline 予想と同じ時刻に通過した。
- 負: 遅延を予想していたが、実際には baseline 予想より早く通過した。

負値を0へ切り上げない。マイナスの遅延として記録し、累積する。

理由: 早く通過した seller を「遅延0」にすると、補償を受けつつ実際には早く通過した事実が時間累計から消える。参考金額では後述のとおり `max(実績遅延, 0)` を使う。時間評価と参考金額で、負の遅延の扱いを分ける。時間評価では負を残す。参考金額では負を0にする。役割は seller のままである。

### 5.4 集計範囲

seller role の取引だけを集計する。同じ Vehicle の buyer 取引の時間を混ぜない。

### 5.5 sellerについて保存・集計する値

- 取引ごとの予想遅延
- 取引ごとの実績遅延
- 取引ごとの予想と実績の差
- 予想遅延累計
- 実績遅延累計
- seller 取引回数
- 正式補償額累計
- seller 実績利得

取引ごとの予想と実績の差は、次である。

```text
予想と実績の差 = 実績遅延 - 予想遅延
```

展開すると、次と同一である。

```text
予想と実績の差 = actual_passage_timestep - candidate_passage_timestep
```

【2026-10-02 最新仕様による注記】

- 上記の名称と式は、記載当時に利用者が明示確定したものではなかった。
- ただし、2026-10-02に利用者が明示確定したsellerの最新式とは、数値上の向きが一致する。
- 最新仕様では、曖昧な「予想と実績の差」という名称を新規実装へ使用しない。
- 共通保存値を次とする。

```text
candidate_minus_actual_passage_timesteps
= candidate_passage_timestep - actual_passage_timestep
```

- sellerの最新role別指標は次とする。

```text
predicted_based_actual_delay_timesteps
= -candidate_minus_actual_passage_timesteps
```

- したがって、次と同じである。

```text
predicted_based_actual_delay_timesteps
= actual_passage_timestep - candidate_passage_timestep
```

- 正は実績遅延がcandidate予測より大きいこと、負は実績遅延がcandidate予測より小さいことを表す。
- 最新の正式参照先は、第4巻末尾の2026-10-02節§5および§6である。

正なら、実績通過が candidate 予測より遅い。負なら、実績通過が candidate 予測より早い。この差も切り上げない。buyer の差式と展開後は同じ形になるが、役割別の意味は異なる。buyer では節約の外れ、seller では遅延の外れとして読む。集計時に混ぜない。

## 6. buyer・seller別集計

同じ Vehicle は、ネットワーク走行中に buyer にも seller にもなり得る。

原因: ある交差点では早く通りたい側として支払い、別の交差点または別時刻では譲る側として補償を受け取る、という走行があり得る。1台の累計時間や累計金額へ役割を混ぜると、支払った額と受け取った額が相殺され、buyer としての損得と seller としての損得が見えなくなる。

結果として採用する集計方針:

- buyer としての時間、金額、取引回数、利得と、seller としての時間、金額、取引回数、利得を混ぜない。
- 当面は新しい Vehicle 累計属性を多数追加しない。
- 個別の成立時 record と actual outcome record を正本とし、履歴から役割別に集計する。
- 表示または計算速度上の必要性が確認された場合だけ、派生的な累計属性を追加する。
- 派生累計属性を追加しても、個別履歴を再現可能な正本として維持する。

理由: 累計属性だけを正本にすると、過去の取引別内訳が再現できなくなる。将来 true VOT が取引ごとに変わる場合、累計時間へ最新 VOT を一括乗算する誤りが起きやすい。個別履歴を正本にすれば、取引別利得を後から再計算できる。

## 7. 実績ベース参考金額の意味

実績ベース参考支払額と実績ベース参考補償額は、実際の通過結果が取引成立時点で完全に分かっていたと仮定し、現在と同じ経済条件を適用した場合の仮想的な金額である。

制度上の正式金額ではない。

次には使用しない。

- 追加請求
- 返金
- 正式支払額の変更
- 正式補償額の変更

研究上の補足指標とする。

この参考金額は Vehicle 単独では計算できない。

原因: 各 buyer の参考支払額は、全 seller の実績要求補償総額を、全 buyer の実績節約価値で按分する。1人の buyer の actual passage と申告 VOT だけでは、按分の分子と分母が揃わない。seller の参考補償額は、その seller の実績遅延と申告 VOT から決まるが、事後評価上の不成立判定は全参加者の実績に依存する。buyer 側が事後評価上不成立なら、遅延した seller の参考補償額も0になる。したがって、同じ取引に属する全 buyer・全 seller の actual passage が揃った後に、取引全体として計算する。

Vehicle 単独で計算できるものは、その Vehicle の役割別の時間差と、その Vehicle の成立時正式金額である。参考金額と事後成立判定は取引全体の計算である。

## 8. 実時間ベースの事後評価

本節で扱うのは、車両の実通過時刻が判明した後に行う**実時間ベースの事後評価**である。今回の判定は実時間ベースである。事後評価上の成立・不成立は、制度上の正式成立を取り消す判定ではない。取引成立時の予想値に基づく正式支払額・正式補償額は変更しない。本節は事後精算を採用しない。事後評価上不成立の場合は参考金額だけを0にする。

判定は次の順序で行う。順序を入れ替えない。

1. 同じ取引に属する全 buyer・全 seller の actual passage が揃った後に、実時間ベースの事後評価を開始する。

2. 各 buyer について、実時間ベースの実績時間節約を計算する。

```text
実績時間節約
= baseline_passage_timestep - actual_passage_timestep
```

3. 各 buyer について、実時間ベースの実績節約価値を計算する。

```text
実績節約価値
= 実績時間節約 × 成立時recordの declared_vot_per_second
```

4. buyer が1人でも実績節約価値が0以下なら、取引全体を事後評価上不成立とする。

```text
ある buyer について 実績節約価値 <= 0
なら、取引全体を事後評価上不成立とする
```

この場合:

- 全 buyer の実績ベース参考支払額を0とする。
- 全 seller の実績ベース参考補償額を0とする。
- buyer 間の按分を行わない。
- buyer 合計と seller 合計の比較へ進まない。
- 正式支払額・正式補償額は変更しない。

5. 全 buyer の実績節約価値が正の場合だけ、次を計算する（seller 側の式の詳細は §9 も参照）。

- buyer 全体の実績節約価値
- 各 seller の実績要求補償額
- seller 全体の実績要求補償総額

各 seller の実績遅延は次である。

```text
実績遅延 = actual_passage_timestep - baseline_passage_timestep
```

```text
sellerの実績要求補償額
= max(実績遅延, 0) × 成立時recordの declared_vot_per_second
```

6. buyer 全体の実績節約価値が、seller 全体の実績要求補償総額を下回る場合、取引全体を事後評価上不成立とする。

```text
buyer全体の実績節約価値 < seller全体の実績要求補償総額
なら、取引全体を事後評価上不成立とする
```

この場合も:

- 全 buyer の参考支払額を0とする。
- 全 seller の参考補償額を0とする。
- 按分を行わない。
- 正式金額は変更しない。

7. 次の両方を満たす場合だけ、実績ベース参考金額を計算する（§9）。

- 全 buyer の実績節約価値が正である。
- buyer 全体の実績節約価値が、seller 全体の実績要求補償総額以上である。

### 予想ベースとの区別

- 取引成立時の `G_b > 0` は予想ベースの条件である。成立時の TVT では、各 buyer について `gross_time_value_G_b > 0` が必要条件である。

```text
G_b = 予想時間節約 × 取引成立時の declared_vot_per_second
```

- 実時間ベースの実績時間節約は、正、0、負のいずれもあり得る。
- 成立時の `G_b > 0` は、実時間ベースの実績時間節約が正になることを保証しない。
- 手順4では、実績時間節約が0以下であることにより、実績節約価値が0以下となる buyer がいれば、取引全体を事後評価上不成立とする。正式に成立した取引の buyer は予想ベースで `G_b > 0` を満たし、成立時 declared VOT は正であるが、実績節約価値が正になることは実績時間節約が正であることに依存する。

## 9. 実時間ベースの参考金額

§8 の手順7を満たし、事後評価上も成立した取引について、実績ベース参考金額を計算する。`実績時間節約` と `実績遅延` は §8 で計算済みである。使用する VOT は、後続評価時の live `Vehicle.vot_declared` ではない。その取引の成立時 record に保存された `declared_vot_per_second` である。理由: 走行中に申告値が変わっても、その取引が成立した時点の経済条件で参考金額を再現するためである。

### 9.1 各buyerの実時間ベースの実績節約価値

```text
各buyerの実時間ベースの実績節約価値
= 実績時間節約 × 成立時recordの declared_vot_per_second
```

`declared VOT=0` という申告自体は有効である。正式 buyer になるには、取引成立時の予想ベースで `G_b > 0` が必要である。declared VOT=0 なら、予想時間節約が正でも `G_b = 0` である。その Vehicle を buyer に含む候補は経済的に成立しない。正式に成立した取引の buyer の成立時 declared VOT は正である。ただし、実時間ベースの実績時間節約や実時間ベースの実績節約価値が正になることは保証しない。実績節約価値が0以下なら、§8 で事後評価上不成立となり、本節の按分へ進まない。

### 9.2 buyer全体の実時間ベースの実績節約価値

```text
buyer全体の実時間ベースの実績節約価値
= 全buyerの実時間ベースの実績節約価値の合計
```

### 9.3 各sellerの実時間ベースの実績要求補償額

```text
実績遅延 = actual_passage_timestep - baseline_passage_timestep
```

```text
各sellerの実時間ベースの実績要求補償額
= max(実績遅延, 0) × 成立時recordの declared_vot_per_second
```

`declared VOT=0` は有効である。declared VOT=0 でも正式 seller になり得る。実績遅延が正でも、申告 VOT が0であれば要求補償額または参考補償額は0になり得る。seller を buyer へ変更しない。補償額0を理由に seller record を省略しない。

`max(実績遅延, 0)` を使う理由: 実績で早く通過した seller に負の補償を要求しないためである。時間評価では負の実績遅延を残す。要求補償額と参考補償額の計算だけを0にする。早く通過した seller を buyer へ変更しない。buyer 側の実績節約価値へ加えない。

### 9.4 seller全体の実時間ベースの実績要求補償総額

```text
seller全体の実時間ベースの実績要求補償総額
= 全sellerの実時間ベースの実績要求補償額の合計
```

### 9.5 各buyerの実績ベース参考支払額（buyer間按分）

#### 按分へ進む条件

§8 に従い、buyer 間の参考支払額按分は、次の両方を満たす場合だけ行う。

- 全 buyer の実時間ベースの実績節約価値が正である。
- buyer 全体の実時間ベースの実績節約価値が、seller 全体の実時間ベースの実績要求補償総額以上である。

これは §8 手順7と同じである。§8 手順4・手順6で不成立となった取引は、本節の按分を行わない。

全 buyer の実績節約価値が個別に正であることを §8 で確認済みである。その合計である `buyer全体の実時間ベースの実績節約価値` は、按分式の除数として必ず正である。

#### 按分式

```text
各buyerの実績ベース参考支払額
= seller全体の実時間ベースの実績要求補償総額
  × 各buyerの実時間ベースの実績節約価値
  ÷ buyer全体の実時間ベースの実績節約価値
```

### 9.6 各sellerの実績ベース参考補償額

```text
各sellerの実績ベース参考補償額
= max(実績遅延, 0) × 成立時recordの declared_vot_per_second
```

seller の参考補償額を負にしない。`declared_vot_per_second` は成立時 record の保存値である。

§8 手順7を満たす場合、各 seller の参考補償額は §9.3 の実時間ベースの実績要求補償額と同じ式である。取引全体で按分し直さない。理由: seller 側は、自分の非負実績遅延と自分の申告 VOT で決まる額を受け取る。buyer 側だけが、seller 全体の実績要求補償総額を実績節約価値で按分して支払う。

### 9.7 早く通過したseller

実績遅延が負または0の seller について、次を同時に満たす。

- 時間評価では負または0の実績遅延を残す。負値を0へ切り上げない。
- 参考補償額は0である。
- buyer 側の実績節約価値へ加えない。
- buyer へ役割変更しない。

理由: 成立時点の役割は seller である。実績で早く通過しても、その Vehicle を事後に buyer へ組み替えると、取引識別、支払按分、履歴の役割が成立時 record と一致しなくなる。役割は成立時 record の `trade_role` が正本である。

### 9.8 buyer側条件による不成立とseller参考補償

buyer 側の条件で事後評価上不成立なら、実際に遅延した seller についても参考補償額は0とする。

理由: 参考金額は取引全体の仮想再計算である。buyer 側が事後評価上成立しない取引で、seller だけに参考補償を残すと、参考支払と参考補償の合計が取引内で対応しなくなる。正式補償額は変更しない。遅延した seller が制度上受け取った正式補償は残る。参考補償だけが0である。

## 10. 中心的な研究指標

buyer の中心的な対比:

- 正式支払額累計
- 予想時間節約累計
- 実績時間節約累計
- 予想と実績の差

seller の中心的な対比:

- 正式補償額累計
- 予想遅延累計
- 実績遅延累計
- 予想と実績の差

実績ベース参考支払額と参考補償額は、文字どおり参考指標にとどめる。中心指標へ昇格しない。理由: 参考金額は事後の仮想再計算であり、制度が実際に課した額ではない。中心指標を参考金額にすると、事後精算したかのような読み方を招く。

金額と時間を同じ単位として直接比較しない。理由: 秒と金額は単位が異なる。直接比較すると、VOT を経由しないまま大小を論じることになる。利得評価では時間を true VOT で金銭換算する。申告 VOT は参考金額の経済条件に使い、満足判定の最終正本には使わない。理由: 満足は、その車両が本当に持つ時間価値に対する損得である。申告値で満足を判定すると、虚偽申告研究で真の損得が見えなくなる。

## 11. 実績利得

### 11.1 基本実験（true VOTが走行中不変）

true VOT が走行中不変である基本実験では、buyer 累計実績利得は次で表せる。

```text
buyer累計実績利得
= true VOT × 実績時間節約累計 - 正式支払額累計
```

seller 累計実績利得:

```text
seller累計実績利得
= 正式補償額累計 - true VOT × 実績遅延累計
```

ここでの true VOT は、基本実験では走行中不変の値である。成立時 record の `true_vot_per_second` と live `Vehicle.vot_true` は、基本実験では一致する前提である。一致していても、後続評価では成立時 record の保存値を使う。live 値を読み直さない。理由: 将来の拡張で live 値が変わっても、基本実験用の実装経路を分岐させないためである。

実績時間節約累計が負の buyer では、`true VOT × 実績時間節約累計` も0以下である（true VOT が0以上の場合）。その場合、支払額を引く前から利得は正にならない。負値を0へ切り上げてから乗算しない。

実績遅延累計が負の seller では、`- true VOT × 実績遅延累計` は加算になる。早く通過した seller は、時間評価上のマイナス遅延により利得が増える。これに正式補償額が加わる。参考補償額は0でも、正式補償額は残る。この差は、参考指標と正式金額を混ぜない理由でもある。

### 11.2 満足・不満足の最終判定

実績利得:

- 0以上: 満足
- 0未満: 不満足

0は満足である。理由: 損をしていない状態を不満足にしない。最終判定の正本は実績利得である。1秒当たり金額は補助指標であり、最終判定を上書きしない。

buyer と seller の判定は別である。同じ Vehicle が両方の役割を持つ場合、buyer としての満足と seller としての満足を1つの判定へ統合しない。統合の定義は本節では確定しない。未確定である。

### 11.3 将来true VOTが取引ごとに変化する場合

将来 true VOT が取引ごとに変化する可能性を排除しない。

その場合は、各取引について次を計算してから合計する。

buyer 取引別実績利得:

```text
buyer取引別実績利得
= その取引の true_vot_per_second
  × その取引の実績時間節約
  - その取引の正式支払額
```

seller 取引別実績利得:

```text
seller取引別実績利得
= その取引の正式補償額
  - その取引の true_vot_per_second
  × その取引の実績遅延
```

取引ごとの実績利得を合計する。buyer 役割の合計と seller 役割の合計は分けたままにする。

最新または単一の live `Vehicle.vot_true` を、過去の実績時間累計全体へ一括乗算しない。

成立時 record の `true_vot_per_second` を使用する。

理由: 過去の取引の時間差に、今の真の時間価値を掛けると、当時の損得が今の VOT で上書きされる。成立時 record へ true VOT を保存した原因は、この上書きを防ぐためである。基本実験でも取引別式は使える。取引別式の合計は、VOT が不変なら累計式と一致する。実装の正本を取引別式に揃えるかどうかは、後続実装時に決めてよい。本節が禁止するのは、過去累計へ最新 live VOT を一括乗算することだけである。

## 12. 満足・不満足の理由分類

最終判定の正本は実績利得とする。

1秒当たり金額は、判定理由を直感的に区分する補助指標とする。最終判定を変更しない。同じ満足または不満足でも、時間が得られなかったのか、時間は得たが価格または補償が真の時間価値に対して不利だったのかを分けるために使う。

### 12.1 buyer

- 実績時間節約累計が0以下: 自明な不満足。
  理由: 早く通れなかった、または遅くなった。支払額の大小を論じる前に、時間面で得ていない。割り算を行わない。
- 実績時間節約累計が正で、正式支払額累計 ÷ 実績時間節約累計 が true VOT を超える: 価格面の不満足。
  理由: 秒あたりに払った額が、その車両の真の時間価値を超える。時間は得たが、払いすぎである。最終判定の実績利得も0未満になる。
- 実績時間節約累計が正で、1秒当たり正式支払額が true VOT 以下: 価格面でも満足。
  理由: 秒あたりの支払いが真の時間価値以下である。最終判定の実績利得は0以上になる。

### 12.2 seller

- 実績遅延累計が0以下: 自明な満足。
  理由: 遅くなっていない、またはむしろ早く通過した。補償額の多少を論じる前に、時間面で損をしていない。割り算を行わない。正式補償額が0でも、遅延が0以下なら自明な満足である。
- 実績遅延累計が正で、正式補償額累計 ÷ 実績遅延累計 が true VOT 未満: 補償面の不満足。
  理由: 秒あたりに受け取った補償が、真の時間価値を下回る。遅れた分を補償しきれていない。最終判定の実績利得も0未満になる。
- 実績遅延累計が正で、1秒当たり正式補償額が true VOT 以上: 補償面でも満足。
  理由: 秒あたりの補償が真の時間価値以上である。最終判定の実績利得は0以上になる。

### 12.3 分母が0以下の場合

実績時間累計が0以下の場合、割り算を行わない。

buyer では実績時間節約累計が0以下、seller では実績遅延累計が0以下、がこの場合である。0で割らない。負の累計で割って符号が反転した1秒当たり指標も作らない。理由: 分母が0以下のときは、1秒当たり価格または補償という解釈が成立しない。自明な不満足または自明な満足として分類する。

### 12.4 この割り算指標の目的

- 直感的な評価。
- 同じ満足または不満足でも、その理由を区分すること。

割り算指標は最終判定の正本ではない。実績利得と矛盾する分類を採用しない。基本実験で true VOT が走行中不変、かつ役割別累計を使う場合、上記の3区分は実績利得の正負と整合する。

### 12.5 将来true VOTが取引ごとに変わる場合

単一 true VOT との累計割り算比較をそのまま使えない。

原因: 取引ごとに true VOT が違うと、正式支払額累計 ÷ 実績時間節約累計 という1つの商を、どの true VOT と比較すべきかが決まらない。最新 VOT と比較すると過去取引の理由が歪む。算術平均 VOT と比較すると、加重の定義が新しい設計になる。

その場合も、取引別実績利得を合計した最終判定を正本とする。

1秒当たり指標の再定義は後続設計で決める。本節では確定しない。

## 13. VOT方針

### 13.1 declared VOT

- 申告値である。
- 0を不正値として拒否しない。
- declared VOT=0 は有効である。
- 不参加の代理にしない。
- 不参加は `participates_in_order_exchange=False` である。
- 後続評価では、成立時 record に保存された `declared_vot_per_second` を使う。
- 後続評価時の live `Vehicle.vot_declared` を読み直さない。

理由: VOT=0 の車両を不参加とみなすと、参加フラグと申告値の責務が混ざる。参加したが時間価値の申告が0であることは、seller として遅延しても補償要求額が0になる、という経済結果として扱う。不参加 Visit は金銭 record を持たない。申告0の seller は金銭 record を持ち、金額0であり得る。この区別を事後評価でも維持する。

#### buyer候補

declared VOT=0 という申告自体は有効である。ただし、buyer については取引成立時の予想ベースで `G_b > 0` が必要である。declared VOT=0 なら、予想時間節約が正でも `G_b = 0` になる。その Vehicle を buyer に含む候補は経済的に成立しない。

したがって、正式に成立した取引の buyer について、成立時 record の declared VOT（`declared_vot_per_second`）は正である。これは実時間ベースの実績時間節約が正になることを保証しない。

#### seller

declared VOT=0 の seller は正式 seller になり得る。

実績または予想の遅延が正でも、申告 VOT が0であれば要求補償額または参考補償額は0になり得る。

seller を buyer へ役割変更しない。補償額0を理由に seller record を省略しない。

#### 不参加

declared VOT=0 を不参加の代理に使わない。不参加は `participates_in_order_exchange=False` で表す。

### 13.2 true VOT

- 基本実験では論文・統計資料に基づく分布から設定する。
- 基本実験では `vot_declared = vot_true` である。正しい VOT 申告を前提として TVT-MP を評価する。
- 採用する分布が0を取り得る場合は true VOT=0 を許容する。
- 採用する分布が0を取り得ない場合は true VOT=0 を許容しない方向で決める。
- 使用する分布が未確定なので、true VOT=0 の最終契約も未確定である。
- 将来、虚偽申告や走行中の申告値変更を研究できるよう、取引成立時点の true VOT と declared VOT を履歴へ固定する。
- 後続評価では成立時 record の `true_vot_per_second` を使用し、live `Vehicle.vot_true` を読み直さない。

true VOT=0 が許容される場合の含意: buyer の実績利得は `-正式支払額累計` になる。正の時間節約があっても金銭換算が0であり、支払があれば不満足になる。seller の実績利得は正式補償額累計そのものになる。遅延があっても金銭換算が0であり、補償が0以上なら満足になる。この含意を、分布未確定の現時点で最終契約としては固定しない。実装時に分布が決まったあと、true VOT=0 を許容するか拒否するかを決める。

虚偽申告研究では、`vot_true` を車両が本当に持つ時間価値として扱う。`vot_declared` を `vot_true` と異なる値に設定する。成立時 record は、申告値と真値が違っていても正常とする。参考金額は declared VOT、満足判定の最終正本は true VOT である。この役割分担を入れ替えない。

## 14. 後続実装に必要な処理

後続実装で必要になる処理を記録する。本節はこれらの実装完了を意味しない。事後評価と参考金額の処理順は §8・§9 と一致させる。取引成立時の予想値に基づく**正式支払額と正式補償額は変更しない**。

### 事後評価と参考金額の処理順

1. 同じ取引の全 buyer・seller の actual passage を揃える。

2. 各 buyer の実時間ベースの実績時間節約を計算する。

3. 各 buyer の実時間ベースの実績節約価値を計算する。

4. buyer が1人でも実績節約価値が0以下なら、参考支払額・参考補償額を全員0として終了する。按分しない。

5. 全 buyer の実績節約価値が正の場合だけ、buyer 価値合計と seller 要求補償総額を計算する。

6. buyer 価値合計が seller 要求補償総額未満なら、参考支払額・参考補償額を全員0として終了する。按分しない。

7. buyer 価値合計が seller 要求補償総額以上の場合だけ、buyer 参考支払額を按分し、seller 参考補償額を記録する。

8. Vehicle 別 actual outcome record を作り、役割別集計と実績利得を計算する。

### その他の実装要件

- 対象 Node を実通過した VisitKey の特定。
- `actual_passage_timestep` の捕捉。
- 対応する成立時 record の検索。検索鍵は `tvt_decision_timestep`、`node_name`、`buyers_sorted`、`visit_key` である。
- 同じ VisitKey への actual outcome 重複記録の拒否。1つの成立時 record に対して actual outcome record を2回追加しない。
- `actual_passage_timestep` が `tvt_decision_timestep` より前でないことの検査。成立判断時刻より前に、その取引の対象通過が完了している状態は異常として扱う。異常時の例外種別は §15 未確定。
- Vehicle 別 actual outcome record は frozen であり、成立時 record を書き換えない。`order_exchange_log` へ追加する。
- buyer・seller 別集計。混ぜない。個別履歴を正本とする。
- 実績利得。成立時 record の `true_vot_per_second` を使う。過去累計へ最新 live VOT を一括乗算しない。
- 満足・不満足分類。最終判定は実績利得。1秒当たり指標は補助（§12）。実績時間累計が0以下のときは割り算しない。
- 複数 Node への対応。取引識別に `node_name` を含める。
- 同一 Vehicle の複数取引への対応。VisitKey と取引3項目で区別する。
- 同一 Vehicle が buyer と seller を切り替える場合、buyer・seller の役割別集計を混ぜない。役割別評価を車両1台の総合満足判定へ統合するかは、§15 の未確定事項とする。

## 15. 未確定事項

次は未確定のまま残す。本節で確定しない。車両1台の総合満足判定は、今回新しく決定しない。

- actual outcome record の正式型名。
- actual outcome record の正式 field 名と順序。
- actual passage の捕捉場所。
- 全参加者の通過完了を管理する主体。
- `order_exchange_log` へ追加する API。
- true VOT 分布。
- true VOT=0 の最終契約。
- Vehicle に派生累計属性を追加するか。
- 取引評価と Vehicle 累計評価の出力形式。
- true VOT が取引ごとに変化する場合の1秒当たり指標。
- welfare の定義。
- 同一 Vehicle の buyer 満足と seller 満足を、車両1台の総合判定へ統合するか。
- 統合する場合の定義。
- `actual_passage_timestep` が `tvt_decision_timestep` より前の場合の具体的な例外型。

## 16. 実装順との関係

この将来仕様の実装は、上位 driver より後である。

現在の推奨順:

1. 上位 driver
2. World から上位 driver を起動する接続
3. `Node.transfer` による順位台帳の物理利用
4. actual passage の捕捉
5. actual outcome・事後評価
6. 実験出力

actual passage の捕捉場所は、物理通過接続の設計時に同時確認する。

理由: 上位 driver だけでは台帳と金額は更新されるが、物理通過順は変わらない。物理通過が変わらない状態で actual passage を捕捉すると、実績は従来の合流順であり、台帳上の TVT 順位との差が制度効果ではなく未接続の結果になる。その差を事後評価の正本にしない。したがって、物理利用の後に捕捉する。

本節の記録は、上位 driver 設計の確定でも実装でもない。保存後は、上位 driver 設計前調査の独立確認へ戻る。

## 17. 次の再開地点

- 本節を Terminal で限定確認する。
- 進捗第2巻への要約は別作業で行う。本作業では `ORDER_EXCHANGE_PROGRESS_2.md` を変更しない。
- `git diff --check` を実行する。
- 詳細設計第3巻だけが変更されていることを確認する。
- 詳細設計第3巻の内容確認後、進捗第2巻へ短い参照要約を追記する。
- 両文書を同一保存単位で commit する。
- commit 名に `document` を含める。
- commit と push を分離する。
- 保存後、上位 driver 設計前調査の独立確認へ戻る。
- 次に確認する4ファイル:
  - `order_control_tvt_baseline_fork_alignment.py`
  - `order_control_tvt_arrived_confirmation.py`
  - `order_control_tvt_leading_nonparticipating_confirmation.py`
  - `order_control_tvt_mp_local_virtual_calculation_set.py`

# 第4巻への移行（2026-09-28）

詳細設計第3巻は、atomic applyの実装・検証、UXsim正式サンプルによる実装後スモークテスト、およびpredicted and actual outcome evaluationの詳細将来仕様までを記録した正式な過去記録として保存する。

上位driver以降の最新詳細設計は、次を参照する。

`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`

第3巻の既存内容は削除・再構成せず、第4巻から必要に応じて正式参照する。

# TVT-MP正式候補のseller非空契約 訂正注記（2026-10-03）

## 1. 訂正理由

actual passage実装項目4の設計調査中に、過去の詳細設計第3巻と一部テストが、selected candidateのseller 0件を正常扱いしていることが判明した。

利用者確認とTerminal独立確認により、この扱いはTVT-MPの制度と矛盾する誤りであると確定した。

## 2. 最新の正式契約

正式なTVT候補は、必ず次を満たす。

- buyer 1件以上
- seller 1件以上
- 実際の順位変換がある

buyer 0件・seller 0件は順位変換が全くないため、正式候補として生成してはならない。

buyer 1件以上・seller 0件も、buyerの取引相手が存在しないため、正式候補として生成してはならない。

## 3. seller 0件と補償額0の区別

不正:

- 正式候補のseller集合が空
- selected candidateのseller集合が空
- buyer 1件以上・seller 0件の順位取引

正常:

- sellerは1件以上存在する
- seller required compensationが0
- seller compensation amountが0
- total_required_compensation_Rが0

補償額0になり得る例:

1. candidate passageとbaseline passageが同じseller
2. candidate passageがbaseline passageより早いseller
3. 申告VOTが0であるseller

これらのsellerはseller roleを維持する。
補償額0を理由にseller recordを削除しない。

## 4. 正常公開生成経路でsellerが保証される理由

正常な公開生成経路では、次の連鎖によりsellerが1件以上存在する。

1. BASELINE_INFORMATION_COMPLETEではright-of-entry Visitが必須
2. right-of-entry Visitは参加車両でなければRuntimeError
3. right-of-entry inlinkのVisitはbuyer候補から除外される
4. concrete buyer candidate setはbuyer 1件以上
5. trade_scopeはright-of-entry Visitを含む
6. trade_scope内の参加する非buyerはsellerに分類される
7. よってright-of-entry Visitが少なくとも1件のsellerになる

順位生成アルゴリズム自体は変更しない。

## 5. 発見した問題

OrderControlTvtMpGeneralTradeRankResultのconstructorは、buyers_sortedを非空必須にしている一方で、sellers_sortedを空tupleでも許容している。

そのため、正常公開生成経路では発生しないseller 0件の正式resultを、直接constructorやテストfixtureから生成できる。

また、過去の一部テストと設計記録は、その破損resultを正常なselected candidateとして後段へ渡していた。

## 6. 正本となる修正

正本となる修正位置:

uxsim/order_control_tvt_mp_general_trade_rank.py

OrderControlTvtMpGeneralTradeRankResult.__init__

修正内容:

- buyers_sortedは引き続き非空必須
- sellers_sortedも非空必須

正常公開生成経路でseller 0件が発生した場合も、正式result生成時に停止する。

## 7. 重複検査を追加しない

economic evaluation、candidate selection、payment and compensation、final rank、final consistency validation、atomic applyへ、同じseller件数検査を重複追加しない。

理由:

- 正式result生成時に保証済みの不変条件である
- 後段は正式上流resultを前提にする
- 登録時に保証済みの不変条件を実行時に重複検証しない方針と整合する

## 8. 過去記述との関係

本巻にある次の趣旨の過去記述は誤りである。

- selected candidateでseller economic recordsは0件でもよい
- selected candidateでseller compensation recordsは0件でもよい
- selected branchでseller recordsは0件以上
- seller 0件を正常扱いする
- atomic applyでseller 0件を正常扱いする

これらは当時の記録として削除しない。
本節を最新の正式契約として参照する。

一方、次の過去記述は引き続き正しい。

- fallbackではbuyer・seller money recordsが空でも正常
- NO_SELECTED_CANDIDATEではbuyer・seller money recordsが空
- NO_VISITS_TO_CONFIRMではbuyer・seller money recordsが空
- 空Nodeではbuyer・seller money recordsが空
- sellerが存在し、補償額だけが0の場合もseller recordを維持する

## 9. テスト訂正方針

seller 0件を正常なselected candidate fixtureとして使用しているテストは訂正する。

- seller 0件の正常性を確認するテストは削除またはconstructor拒否テストへ変更
- 他の検査目的を持つテストはsellerを1件以上追加し、本来の検査目的を維持
- fallback、候補なし、空Nodeの空seller列は維持
- seller economic recordが存在するのにcompensation recordだけが欠落する意図的な不一致fixtureは維持
- sellerが存在し補償額0となる正常テストは維持

## 10. actual passageへの影響

actual passage実装項目1〜3のコード変更は不要である。

actual passage側は、atomic applyで登録済みのroleとVisitKeyを追跡し、seller 0件候補を生成しない。

次は変更しない。

- actual passage observation
- 3組9 field
- prepare
- physical transfer
- clearance履歴更新
- commit

実装項目4では次を前提とする。

- TradeWait.buyer_visit_keysは1件以上
- TradeWait.seller_visit_keysも1件以上
- seller_visit_keysが空のTradeWaitは正常な成立取引ではない

## 11. 実装項目4との関係

actual passage実装項目4は、本訂正のコード、テスト、文書を保存・pushした後に再開する。

本訂正前に、buyer・seller完了通知のseller空集合処理を設計しない。

## 12. 独立確認結果

Cursor報告だけで確定していない。

Terminalで少なくとも次を確認した。

- seller分類の正本
- 現constructorがseller 0件を受理すること
- seller 0件では順位変換が起きないこと
- right-of-entry Visitが参加車両であること
- right-of-entry Visitがbuyer候補から除外されること
- trade_scopeにright-of-entry Visitが含まれること
- 正常公開生成経路ではseller 1件以上になること
- FIFOの候補件数・index契約を変更する必要がないこと
- 後段へ重複検査を追加する必要がないこと
- fallback等では空seller money列が正常であること
- sellerが存在し補償額0となるケースを維持すべきこと
- seller 0件fixtureの影響範囲

BLOCKERはない。
利用者判断事項も残っていない。

## 13. 次の再開地点

次は詳細設計第4巻へ、完全実装前訂正設計を別作業で追記する。

その後、進捗第3巻へ要約と最新再開地点を別作業で追記する。

3文書の独立確認、commit、pushが完了するまで、コードとテストを変更しない。
