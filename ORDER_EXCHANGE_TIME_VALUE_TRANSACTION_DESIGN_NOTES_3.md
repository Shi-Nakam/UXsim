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
