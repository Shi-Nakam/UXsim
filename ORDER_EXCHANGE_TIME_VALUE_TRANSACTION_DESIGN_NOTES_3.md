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
