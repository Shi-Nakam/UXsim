# UXsim Order Exchange 改変作業メモ 2

## 本メモの位置づけ

- 本ファイルは `ORDER_EXCHANGE_PROGRESS.md` の継続版である。進捗メモ第2巻とする。
- 第1巻は削除、移動、置換しない。第1巻の既存内容は歴史的記録として維持する。
- 2026-09-26以降の新規進捗は、原則として本ファイルへ追記する。最新現在地は第2巻を先に確認する。
- 過去経緯が必要な場合だけ第1巻を参照する。第1巻の内容を本ファイルへ大量複写しない。
- 2026-09-26以降の最新の詳細設計と実装結果は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` を正本とする。切替前の仕様と履歴は、第1巻および第2巻を必要に応じて参照する。
- 本ファイルは完了範囲、検証結果、未実装境界、次の再開地点を中心に記録する。

## 文書保守方針

- 過去の記録は原則として削除しない。古い記述と最新状態が異なる場合は、更新注記と最新参照先で整理する。
- 歴史的記録を推測で書き換えない。実装前仕様と実装完了記録を区別する。
- Cursorの報告だけで実装完了と確定しない。実コード、テスト、差分、Git状態、独立確認を根拠にする。
- 詳細設計メモと最新進捗メモの双方への反映要否を、各節目で確認する。
- Git操作は利用者がTerminalで行う。commitとpushを分ける。メモを含むコミット名には `document` を含める。
- `diagnostics/order_control.zip` は対象外とする。文献調査側の記録とコーディング進捗を混同しない。

## 第1巻との関係

- 第1巻: `ORDER_EXCHANGE_PROGRESS.md` — 第2巻開始前までの詳細な歴史的進捗記録。
- 第2巻: `ORDER_EXCHANGE_PROGRESS_2.md` — 2026-09-26以降の最新進捗本流。
- 第1巻の既存見出しや本文は変更または移動しない。過去の詳細が必要な場合は必要な箇所だけ第1巻を参照する。
- 第1巻の末尾には、2026-09-26付で第2巻への短い移行注記を追加済みである。

## 第2巻開始時のGit状態

- 作成日: 2026-09-26
- 作業ブランチ: `feature/intersection-order-control`
- 最新保存済み・push済みコミット: `5cde1aa` — document pre-implementation specification for TVT-MP candidate selection
- HEADと `origin/feature/intersection-order-control` は一致
- 未追跡の新規実装: `uxsim/order_control_tvt_mp_candidate_selection.py`、`tests_order_control_tvt_mp_candidate_selection.py`
- `diagnostics/order_control.zip` は既存未追跡
- 第2巻作成時点では git add、commit、push を行っていない

## 第2巻開始時の研究・実装現在地

**主対象:** TVT-MP、複数ネットワーク、複数OD需要、右左折あり、単車線条件、時間価値取引型交差点管理。

**重要原則:** Case IIIは使用しない。strategy-proofnessは未証明。基本実験は正しいVOT申告を前提。不参加は `participates_in_order_exchange=False`。VOT=0は合法入力で不参加の代理にしない。TVT-MP一般形を直接実装。非参加Visitあり・なしを一般形で扱う。候補選択は surplus 最大 → surplus同値なら buyer 数最大 → 最終同値時だけ選択専用局所RNG。traffic RNGと order-control再訪RNGを候補選択で消費しない。

**実装済みの主なTVT-MP処理:** candidate Visit整理、inlink別snapshot物理順、具体的買い手候補集合、一般形順位再構成、FIFO検査接続、局所拘束順位列、候補別局所仮想計算、全候補局所仮想計算集合、経済性評価、成立候補選択。成立候補選択の最新実装結果は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` を参照する。それ以前の各処理の詳細は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md` を必要に応じて参照する。

## TVT-MP成立候補選択部品を実装・検証（2026-09-26）

**前段仕様:** commit `5cde1aa`（document pre-implementation specification for TVT-MP candidate selection）。

**新規ファイル:** 本番 `uxsim/order_control_tvt_mp_candidate_selection.py`、専用テスト `tests_order_control_tvt_mp_candidate_selection.py`。

**公開:** Enum `OrderControlTvtMpCandidateSelectionStatus`（`SELECTED`、`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`）。frozen型 `OrderControlTvtNodeMpCandidateSelectionResult`、`OrderControlTvtMpCandidateSelectionSetResult`。API `select_tvt_mp_candidates(economic_evaluation_set_result, real_W)`。

**実装要点:** Nodeごとに最大1候補。`economically_feasible` のみ対象。保存済み surplus 最大、同値なら `len(buyer_economic_records)` 最大（seller数・当事者総数は使わない）。最終同値2件以上のみ局所RNG。identityは `(node_name, buyers_sorted)`。identityで決定論的整列。seed材料は `random_seed`、T、Node名、整列済み同値identity（UTF-8長さ付きbytes符号化）。`hash()`・object id・`real_W.rng`・`order_control_rng` 非使用。RNG state保存復元なし。列挙順・Node処理順独立。feasible 0件は正常（`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`、selected `None`、`rng_was_used=False`）。selectedは入力同一object。入力経済結果と実World不変。重大不整合で全体停止、部分overall resultなし。

**今回未実装:** payment、compensation、final rank、baseline fallback、formal route、順位台帳更新、実World反映、actual比較。

## 検証結果

- 専用テスト35件: 直接35 passed、pytest 35 passed・35 collected、定義35・TESTS登録35（重複・漏れ・未定義参照なし）。
- py_compile: 新規本番・専用テストとも成功。
- 関係回帰: 指定7ファイル **366 passed**；`tests_order_control_baseline_driver.py` と `tests_order_control_baseline_downstream_boundary.py` **121 passed**（合計値だけへまとめない）。
- 静的確認: 経済評価・局所仮想計算・FIFO再実行なし、`hash()`・`id()`・World RNG参照・RNG state保存復元なし、payment・compensation・final rank・actual・実World書込みなし。
- 独立確認: 保存済み完全実装前仕様と整合、追加修正不要。
- 全pytest、GUI、デモ、長時間性能テストは実行していない。

## 現在の実装完了範囲

候補選択部品: selection status、Node/全体frozen結果、一括公開API、feasible抽出、surplus・buyer数最大抽出、candidate identity・重複検出、deterministic整列、seed材料、局所RNG、最終同値選択、RNG非使用、候補なし正常、World RNG不変性、列挙順・Node順独立、重大不整合・部分結果なし、専用テスト、関係回帰、独立確認。

## 現在の未実装範囲

payment、compensation、P_b比例配分、seller実補償配分、`payment_paid` / `payment_received` / `order_exchange_log` 更新、成立時最終順位列、不成立時baseline fallback、情報未解決時最終確定、formal route保存、順位台帳更新、確定順位ブロック接続、実World交通反映、actual記録・expected/actual比較、realized utility、ex-post welfare、上位TVT driver、strategy-proofness検証、文献制度の移植。API・型・配分規則・処理順は本メモ作成だけでは確定しない。

## TVT-MP payment・compensation計算部品・完全実装前仕様を確定（2026-09-26）

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` の「TVT-MP payment・compensation計算部品・完全実装前仕様」。本節は要約である。Python実装と専用テストは未着手である。

**対象:** candidate selection後の純計算部品。Nodeごとに選択された最大1候補について、buyer支払額とseller補償額を計算する。新しいfrozen結果だけを返す。

**入力:** `OrderControlTvtMpCandidateSelectionSetResult` だけ。`real_W` なし。Vehicle検索なし。選択結果から `G_b`、`R_s`、`G`、`R`、VisitKey、`vehicle_name`、selected candidateへ到達する。

**規則:** `P_b = R * G_b / G`。`compensation_amount = R_s`。sellerへ追加surplusを配らない。surplusは制度主体の金銭残高ではない。予測値で事前確定し、actual passageによる事後精算は行わない。strategy-proofnessは未証明。

**早期通過seller:** `compensation_amount` は 0。seller自身の支払額も 0。role維持。buyerへ変更しない。時間短縮価値を `G` へ加えない。支払いなしで時間短縮の交通上の便益を得る。同時刻も同様に 0。

遅延sellerでも、申告VOTが0であるため保存済み `R_s` が0の場合、`compensation_amount` は0とし、人工的に正値へ補正しない。

**数値:** float。内部丸めなし。toleranceなし。Decimalなし。最後のbuyerへ残差なし。buyer順を補正に使わない。`sum(P_b)` と `R` のbit単位一致を重大不整合にしない。保存済み `G`/`R` と明示加算した `G_b`/`R_s` 合計は完全一致を確認する。経済性評価と候補選択は再実行しない。

**公開:** Enum `OrderControlTvtMpPaymentAndCompensationStatus`（`CALCULATED`、`NO_SELECTED_CANDIDATE`）。frozen型 `OrderControlTvtMpBuyerPaymentRecord`、`OrderControlTvtMpSellerCompensationRecord`、`OrderControlTvtNodeMpPaymentAndCompensationResult`、`OrderControlTvtMpPaymentAndCompensationSetResult`。API `calculate_tvt_mp_payments_and_compensations(candidate_selection_set_result)`。入力とselectedは同一object参照。

**候補なし:** 正常。status `NO_SELECTED_CANDIDATE`、selected `None`、両records空tuple。例外にしない。0額recordを作らない。

**非保存:** `G_b`/`R_s` の複写、share、net benefit、utility、早期通過flag、総額field、`institutional_balance`、`sum(P_b)` 診断値、final rank、actual、Vehicle台帳、live World、RNG。field名 `actual_compensation` は使わない。

**不変:** selection / economic / local / FIFO / collector / rank state / Vehicle / `payment_paid` / `payment_received` / `order_exchange_log` / 実World / RNG。

**処理順:** 計算はfinal rank前に行ってよい。Vehicle台帳更新は final rank と全体整合確認の成功後のatomic applyまで遅延する。

**予定ファイル:** `uxsim/order_control_tvt_mp_payment_and_compensation.py`、`tests_order_control_tvt_mp_payment_and_compensation.py`。既存経済評価・候補選択の本番とテストは変更しない。

**次の直接作業:** 第3巻新規節と本節をTerminalで直接表示して独立確認する。問題がなければ2文書をcommitしてpushする。保存後に新規本番と専用テストだけを実装する。Vehicle台帳更新とfinal rankは実装しない。

## TVT-MP payment・compensation計算部品を実装・検証（2026-09-26）

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` の「TVT-MP payment・compensation計算部品・完全実装前仕様」§21 実装・検証結果。前段仕様: commit `1cc579f`。

**新規ファイル:** 本番 `uxsim/order_control_tvt_mp_payment_and_compensation.py`、専用テスト `tests_order_control_tvt_mp_payment_and_compensation.py`。

**実装要点:** candidate selection後の純計算。入力は `OrderControlTvtMpCandidateSelectionSetResult` のみ。`real_W` なし。API `calculate_tvt_mp_payments_and_compensations(candidate_selection_set_result)`。`payment_P_b = R * G_b / G`（buyerごと個別、残差補正なし）。`compensation_amount = R_s`（上流保存済み、再計算なし）。Enum `CALCULATED` / `NO_SELECTED_CANDIDATE`。frozen結果、入力とselectedは同一object参照。

**seller:** 遅延sellerは `compensation_amount = R_s`。同時刻・早期通過sellerは予想遅延がないため上流で `R_s = 0`、補償額と支払額0、role維持。早期通過sellerは支払いなしで時間短縮の交通上便益を得る（`G` に加えない）。申告VOTが0の遅延sellerは、申告VOTが0であるため上流で `R_s = 0`、補償額0（人工的な正値補正なし、role維持）。

**数値:** float、内部丸めなし、tolerance/Decimal/残差補正なし。`sum(P_b)` と `R` のbit一致を重大不整合にしない。

**不変・責務外:** selection/economic/local/FIFO/collector/rank state/Vehicle/台帳/RNG不変。Vehicle台帳更新、final rank、baseline fallback、formal route、順位台帳、atomic apply、実World反映、actualは未実装。

**独立確認:** 初回専用テストの常時成功assertを削除し `test_three_equal_buyers_each_use_formula_without_residual_or_sum_bit_check` に修正。**追加修正不要**。

**検証:** 専用36件（直接36、pytest 36/36 collected、TESTS 36）。py_compile 新規2ファイル成功。TVT-MP関係8ファイル **437 passed**（新規36＋その他401）。baseline driver/downstream **121 passed**。全pytest・GUI・性能テストは未実行。

## TVT-MP final rank construction部品・完全実装前仕様を確定（2026-09-26）

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` の「TVT-MP final rank construction部品・完全実装前仕様」（記録日 2026-09-26）。本節は要約である。Python実装と専用テストは未着手である。

**位置づけ:** payment・compensation 純計算の次。今回新たに確定する Visit の順位と正式進路を構築する純計算部品。新しい frozen 結果だけを返す。順位台帳へ書き込まない。Vehicle金銭台帳へ書き込まない。atomic apply は後続の別部品。

**予定ファイル:** `uxsim/order_control_tvt_mp_final_rank.py`、`tests_order_control_tvt_mp_final_rank.py`。

**入力:** `OrderControlTvtMpPaymentAndCompensationSetResult` だけ。`real_W` なし。rank state 引数なし。selection set 等の追加公開引数なし。optional 引数なし。空窓・fallback・selected 専用 API なし。

**公開API:** `build_tvt_mp_final_ranks(payment_and_compensation_set_result)`。位置引数1つ。全Node一括。公開 API は1つ。

**payment set:** 金額計算済み候補だけを意味しない。既存の全Node APIを順に呼ぶことで、空窓・情報不足・採用候補なし・全件先行確定済みも正常な空結果として payment set まで伝播する。空recordsは架空の金額ではない。payment status は原因ではなく結果ラベル。正式原因は上流の保存済み情報（decision window、remaining window、`build_status`、上流候補結果等）から判定する。

**原因別5分岐:**

1. **selected candidate あり** — 区分3と区分4をこの順で使用。区分3は `trade_scope` 内の Visit を selected candidate の取引後順位で確定。区分4は `trade_scope` 外で今回の意思決定窓内に残る Visit を baseline 順位で確定。区分1・2は再確定しない。
2. **候補検討後、採用候補なし** — 意思決定窓内 Visit は存在した。候補検討後に採用候補が0件。先行確定後に残る意思決定窓内 Visit 全体を baseline 順位で確定。正常な baseline fallback。
3. **baseline 情報不足** — 意思決定窓内 Visit は存在した。候補形成または評価に必要な baseline 情報が不足。経済的不成立へ変換しない。残る窓全体を baseline 順位で確定。正常な baseline fallback。
4. **意思決定窓内 Visit が最初から0件** — `decision_window_visit_keys` が最初から空。実質的な候補検討や金額計算を行わず、正常な空Node結果を payment set まで伝播。`NO_VISITS_TO_CONFIRM`、final rank 列は空。baseline fallback ではない。
5. **意思決定窓内 Visit は存在したが、全件先行確定済み** — `decision_window_visit_keys` は1件以上、`remaining_decision_window_visit_keys` は空。final rank 部品で追加確定する Visit なし。`NO_VISITS_TO_CONFIRM`、final rank 列は空。baseline fallback ではない。先行確定済み Visit を再掲しない。

分岐4と分岐5は同じ `NO_VISITS_TO_CONFIRM` だが、原因は異なる（最初から空窓／窓内はあったが全件先行確定）。

**既確定順位・正式進路:** 区分1・2はすでに確定済み。final rank 列へ再掲しない。baseline fallback は先行確定後に残る意思決定窓内 Visit だけを対象。すでに確定済みの順位・正式進路を上書きしない。重複 Visit を自動除外して続行しない。重複混入は重大不整合。

**formal route:** field 名 `formal_route_next_link_name` を Visit ごとに順位と一緒に保存。selected 時は保存済み binding Visit の route。fallback 時は baseline collector の保存済み route。World・Vehicle から再探索しない。推測しない。欠落・空文字は重大不整合。

**公開型:** Enum `OrderControlTvtMpFinalRankStatus`（`SELECTED_CANDIDATE_RANKS`、`BASELINE_FALLBACK_RANKS`、`NO_VISITS_TO_CONFIRM`）。`OrderControlTvtMpFinalizationSource`（`SELECTED_CANDIDATE`、`BASELINE`）。frozen: `OrderControlTvtMpFinalRankVisitRecord`（`visit_key`、`final_local_rank`、`formal_route_next_link_name`、`finalization_source`）、`OrderControlTvtNodeMpFinalRankResult`、`OrderControlTvtMpFinalRankSetResult`。

**NO_VISITS_TO_CONFIRM:** 分岐4（原因A: `decision_window_visit_keys` が最初から空）と分岐5（原因B: 窓は1件以上だが全件先行確定で remaining が空）。共通: selected は None、final rank 列は空、baseline fallback 列は作らない、例外ではない。残る窓が1件以上で selected がない場合は `BASELINE_FALLBACK_RANKS`（`NO_VISITS_TO_CONFIRM` ではない）。

**payment status:** `NO_SELECTED_CANDIDATE` だけで原因決定・baseline fallback 選択・経済的不成立判断をしない。payment status と selection status は整合確認に使う。

**順位台帳・atomic apply:** 本部品は順位台帳へ書き込まない。既存の原子的確定 API は後続 apply が利用（全件先に確認、問題なければ一括登録、途中問題なら1件も登録しない）。Vehicle金銭台帳更新も後続 apply。複数Node全体の atomic 単位は後続設計。

**上位driver（未実装）:** 全Nodeについて既存 API を payment まで順に呼ぶ。空窓・情報不足を理由に Node をチェーンから落とさない。全Nodeを含む payment set を final rank へ渡す。原因別5分岐・baseline fallback 列・分岐4/5 の別API化は driver で再実装しない。

**不変:** payment / selection / economic / local / FIFO / collector / rank state / Vehicle / `payment_paid` / `payment_received` / `order_exchange_log` / World / RNG。

**今回未実装:** final rank 本番・専用テスト、rank state 書込み、Vehicle金銭台帳、atomic apply、実World反映、actual、utility/welfare、上位driver本体、strategy-proofness、文献制度の移植。

## TVT-MP final rank construction部品を実装・検証（2026-09-26）

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` の「TVT-MP final rank construction部品・完全実装前仕様」§29 実装・検証結果（2026-09-26）。前段仕様: commit `e364238`。

**新規ファイル:** 本番 `uxsim/order_control_tvt_mp_final_rank.py`、専用テスト `tests_order_control_tvt_mp_final_rank.py`。既存 Python・既存テスト・既存結果型は変更していない。

**公開:** Enum `OrderControlTvtMpFinalRankStatus`（`SELECTED_CANDIDATE_RANKS`、`BASELINE_FALLBACK_RANKS`、`NO_VISITS_TO_CONFIRM`）。`OrderControlTvtMpFinalizationSource`（`SELECTED_CANDIDATE`、`BASELINE`）。frozen: `OrderControlTvtMpFinalRankVisitRecord`、`OrderControlTvtNodeMpFinalRankResult`、`OrderControlTvtMpFinalRankSetResult`。API `build_tvt_mp_final_ranks(payment_and_compensation_set_result)`。入力は payment set だけ。位置引数1つ。`real_W` なし。rank state 引数なし。全Node一括。部分的 overall result なし。payment set と selected candidate は入力と同一 object 参照。

**入力経路:** 上流参照連鎖は private helper `_saved_node_columns_from_payment_set` に集約。payment set から selection、economic、local、FIFO、general trade rank、concrete buyer、inlink、candidate visit set、right-of-entry、leading confirmation、arrived confirmation、alignment fork、baseline collector へ既存 object の同一参照で到達。新しい共通入力型へ複写しない。

**payment status:** 原因ではない。selection status と records の整合確認にだけ使用。`NO_SELECTED_CANDIDATE` だけで fallback、経済的不成立、`NO_VISITS_TO_CONFIRM` を決めない。空窓・情報不足 Node も空候補・空 records の正常な Node 結果として payment set まで伝播。架空の候補や金額は作らない。

**原因別5分岐:**

1. **selected candidate あり** — `SELECTED_CANDIDATE_RANKS`。区分3と区分4をこの順で使用。区分3は trade_scope 内の取引後順位。区分4は trade_scope 外で今回の意思決定窓内に残る Visit の baseline 順位。
2. **候補検討後、採用候補なし** — `BASELINE_FALLBACK_RANKS`。remaining decision window 全体を baseline 順位。正常結果。
3. **baseline 情報不足** — `BASELINE_FALLBACK_RANKS`。remaining decision window 全体を baseline 順位。経済的不成立へ変換しない。正常結果。
4. **意思決定窓内 Visit が最初から0件** — `NO_VISITS_TO_CONFIRM`。final rank 列は空。baseline fallback ではない。
5. **意思決定窓内 Visit は存在したが全件先行確定済み** — `NO_VISITS_TO_CONFIRM`。final rank 列は空。先行確定済み Visit を再掲しない。baseline fallback ではない。

分岐4と分岐5は同じ status だが、原因は異なる。

**順位・formal route:** Visit record に `visit_key`、`final_local_rank`、`formal_route_next_link_name`、`finalization_source`。`final_local_rank` は今回の Node 内の列で1から連続、tuple 順と一致。順位台帳全体の絶対順位ではない。selected 時は binding Visit の保存済み route。fallback 時は collector の保存済み route。World・Vehicle から再探索しない。推測補完しない。欠落・None・空文字は重大不整合。

**既確定 Visit:** 区分1・2を再掲しない。先行確定済み Visit を fallback 列へ含めない。arrived 確定済み Visit を再掲しない。既確定順位・正式進路を上書きしない。重複を自動除外して続行しない。混入または重複は重大不整合。

**不変・責務外:** payment / selection / economic / local / FIFO / collector / rank state / Vehicle / `payment_paid` / `payment_received` / `order_exchange_log` / World / RNG 不変。`confirm_visits_and_formal_target_node_routes_atomically` 呼出しなし。rank state 書込み、Vehicle 金銭台帳、atomic apply、上位 driver、actual、utility/welfare は未実装。

**独立確認:** 初回専用テストの `assert "uxsim" not in imported_modules or True` は `or True` により常時成功のため問題として検出。常時成功 assert、`imported_modules` 変数、import 収集処理を削除。具体的な責務外処理の禁止確認は維持。**追加修正不要**。

**検証:** 専用43件（直接43、pytest 43/43 collected、TESTS 43）。py_compile 新規2ファイル成功。関係回帰指定16ファイル **772 passed**（新規43＋その他729）。全 pytest・GUI・デモ・長時間性能テストは未実行。

**未実装:** final consistency validation、rank state 書込み、Vehicle 金銭台帳更新、atomic apply、上位 driver、実 World 反映、actual 比較、utility/welfare、strategy-proofness 検証、文献制度の移植。

## TVT-MP final consistency validation部品・完全実装前仕様を確定（2026-09-26）

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md` の「TVT-MP final consistency validation部品・完全実装前仕様」（記録日 2026-09-26）。本節は要約である。Python 実装と専用テストは未着手である。

**位置づけ:** final rank construction の次、atomic apply の前。final rank 結果と payment・compensation 結果、および上流結果を相互照合する。順位結果と金銭記録が同じ取引内容を表しているか確認する。全 Node をまとめて確認する。1 Node でも重大不整合があれば承認結果を返さない。部分的 validation result を返さない。frozen 結果間の純照合だけを行う。rank state、Vehicle、World は変更しない。

**正式処理順:** (1) candidate selection、(2) payment・compensation pure calculation、(3) final rank construction、(4) final consistency validation、(5) rank state と Vehicle 金銭台帳への atomic application。

**予定ファイル:** 本番 `uxsim/order_control_tvt_mp_final_consistency_validation.py`、専用テスト `tests_order_control_tvt_mp_final_consistency_validation.py`。

**入力・API:** 唯一の入力は `OrderControlTvtMpFinalRankSetResult`。API `validate_tvt_mp_final_consistency(final_rank_set_result)`。位置引数1つ、final rank set だけ。`real_W` なし。rank state・Vehicle・Vehicle mapping・Node・outlink 集合・RNG・optional 引数なし。全 Node 一括、公開 API は1つ。成功時だけ frozen 全体結果を返す。上流参照は private helper に集約し、新しい共通入力型へ複写しない。

**結果型:** `OrderControlTvtMpFinalConsistencyValidationSetResult`（frozen）。field は `final_rank_set_result` だけ。入力と同一 object 参照。final rank 列・buyer payment records・seller compensation records・formal route を複写しない。rank state・Vehicle・outlink 集合を保持しない。failed status・boolean だけの独立承認 token を作らない。公開 Enum なし。Node 単位の公開 validation result 型なし。部分的な承認結果なし。

**pure validation と実状態:** 本部品は frozen 結果同士の整合、final rank と payment・compensation の対応、selected candidate の対応、buyer・seller の Visit 対応、原因別5分岐、formal route の保存値対応、final rank 列の内部整合を確認する。rank state 上の未確定・既確定、実 outlink 所属、Vehicle 存在、金銭属性の書込み可能性、apply 直前の実状態変化は確認しない。これらは atomic apply が書込み直前に確認する。validation 成功は frozen 結果間の整合確認済みのみを意味し、実状態への書込み成功を保証しない。

**selected 同一 object:** 分岐1では final rank・payment・selection の selected candidate と economic 候補 tuple 内の selected がすべて同一 object（`is`）。値の等しさだけでは不十分。複製は正常としない。

**buyer payment:** selected 時は buyer economic records と buyer payment records が1件以上、件数・保存順・VisitKey・`vehicle_name` が一致、VisitKey 重複なし。各 record の Visit は区分3に存在し role は `BUYER`。区分3の `BUYER` 集合と buyer payment record 集合が一致。`payment_P_b` 式、`G`・`R`・payment 式・tolerance・Decimal の再計算はしない。

**seller compensation:** selected 時は seller economic records と seller compensation records は0件でも正常。件数・保存順・VisitKey・`vehicle_name` が一致、VisitKey 重複なし。各 record の Visit は区分3に存在し role は `SELLER`。区分3の `SELLER` 集合と seller compensation record 集合が一致。`compensation_amount` と保存済み `required_compensation_R_s` が一致。`R_s` 式、VOT・通過時刻差・予想待ち増加・seller role の再計算はしない。

**補償0 seller:** 同時刻 seller、早期通過 seller、申告 VOT が0の遅延 seller はいずれも seller record を保持し `compensation_amount` は0。role は seller を維持、buyer へ変更しない。補償0を理由に record を削除しない。economic record と compensation record の存在と対応を確認する。

**buyer・seller 重複禁止:** 同一 VisitKey を buyer と seller の両方にしない。buyer 内・seller 内の重複なし、buyer と seller の共通 VisitKey なし、payment と compensation の共通 VisitKey なし。重複を自動除外しない。重複は `RuntimeError`。

**非参加・区分4:** 区分3の `NONPARTICIPATING` は final rank に含まれ source は `SELECTED_CANDIDATE`、金銭 record なし。区分4の `OUTSIDE_TRADE_SCOPE` は final rank に含まれ得 source は `BASELINE`、金銭 record なし（空でも正常）。非参加・区分4に金銭 record を要求しない。存在すれば重大不整合。金銭 record を持つのは selected 時の区分3の `BUYER` と `SELLER` だけ。final rank 全 Visit へ金銭 record を要求しない。

**原因別5分岐:** (1) selected — `SELECTED_CANDIDATE_RANKS`・`CALCULATED`・`SELECTED`・同一 selected・buyer records 1件以上・seller 0件以上・区分3 `BUYER`/`SELLER` と金銭一致・非参加・区分4に金銭なし。(2) 採用候補なし — `BASELINE_FALLBACK_RANKS`・`NO_SELECTED_CANDIDATE`・`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`・selected None・金銭空・`BASELINE_INFORMATION_COMPLETE`・remaining 全体・source `BASELINE`。(3) 情報不足 — 同形 fallback・`build_status` は情報不足3種・経済的不成立へ変換しない。(4) 空窓 — `NO_VISITS_TO_CONFIRM`・金銭空・final rank 空・decision/remaining 空・`NOT_BUILT_NO_RIGHT_OF_ENTRY`。(5) 全件先行確定 — 同 `NO_VISITS_TO_CONFIRM`・decision 1件以上・remaining 空・先行確定 Visit を再掲しない。分岐4と5は同じ status だが原因を混同しない。`NO_SELECTED_CANDIDATE` だけでは分岐を決めない。

**formal route:** 全 final rank Visit の `formal_route_next_link_name` が非空 str。selected 時は binding `route_next_link_name`、fallback 時は collector snapshot と VisitKey 対応で一致。実 outlink 集合・Link・World 接続・再探索は確認しない。実 outlink 妥当性は atomic apply が書込み直前に確認。

**final rank 列:** VisitKey 重複なし、`final_local_rank` 1から連続、tuple 順一致、source と Node status 一致、区分1・2・先行確定・arrived 確定の再掲なし。列を再構築しない。

**エラー:** `ValueError` は外部入力が `OrderControlTvtMpFinalRankSetResult` でない場合だけ。`RuntimeError` は Node 対応・status・selected 同一 object・金銭と role・VisitKey 重複・補償0 record 欠落・非参加・区分4・fallback・`NO_VISITS` の金銭・順位・source・route・分岐取り違え・1 Node 後続続行・部分結果。正常扱い: 分岐2–5、seller 0件、補償0 seller、非参加・区分4の金銭なし。

**過剰検証回避:** candidate formation、general trade rank、FIFO、local virtual calculation、economic evaluation、candidate selection、payment・compensation 式、`G`/`R` 再加算、surplus、final rank construction、VOT、passage difference、交通シミュレーションは再実行しない。完成済み結果間の対応だけを確認する。

**不変:** final rank、payment、selection、economic、local、FIFO、collector、rank state、Vehicle、`payment_paid`、`payment_received`、`order_exchange_log`、World、RNG。

**atomic apply:** validation result は apply の入力の一つ。apply は validation 成功を理由に実状態検査を省略しない。書込み直前に rank state・未確定/既確定・outlink・実 route・Vehicle・金銭属性・log・適用 Node・複数 Node 一括単位を確認する予定。本部品は confirm API、台帳書込み、log、rollback、実 World 反映を行わない。複数 Node の一括書込み単位は後続 apply 設計の未確定事項。

**上位 driver（未実装）:** 全 Node を final rank まで通し、final rank set を validation へ、成功結果を apply へ渡す。5分岐・buyer/seller 再照合・金銭列再構築・Node ごとの validation 直後部分適用はしない。

**今回未実装:** validation 本番・専用テスト、rank state 書込み、Vehicle 金銭台帳、atomic apply、上位 driver、実 World 反映、実 outlink 検査、actual、utility/welfare、strategy-proofness、文献制度の移植、複数 Node atomic 書込み単位の確定。

## 次の再開地点

1. 詳細設計第3巻と進捗第2巻の final consistency validation 仕様を Terminal で直接確認する。
2. 問題がなければ2文書を同一保存単位で commit する。
3. commit 結果、最新コミット、残存変更を確認する。
4. 別の指示で push し、push 後の状態を確認する。
5. 保存後に新規本番 `uxsim/order_control_tvt_mp_final_consistency_validation.py` と専用テスト `tests_order_control_tvt_mp_final_consistency_validation.py` だけを実装する。
6. 実装後に独立確認する。
7. atomic apply と上位 driver は、その後の別設計とする。

## 新しいチャットでの再開方法

1. `ORDER_EXCHANGE_PROGRESS_2.md`
2. `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md`
3. 必要な場合だけ `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`
4. 必要な場合だけ `ORDER_EXCHANGE_PROGRESS.md`
5. 必要な場合だけ `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`

最新現在地は進捗第2巻から確認する。最新の詳細設計と実装結果は詳細設計第3巻を参照する。過去の詳細は必要な場合だけ旧進捗メモまたは旧設計メモの該当箇所を検索する。旧巻の全文を毎回同時に読み込ませない。
