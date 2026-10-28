# ORDER_EXCHANGE_PROGRESS_4

本ファイルは TVT-MP 研究の進捗記録 **第4巻** である。

- 第3巻は `ORDER_EXCHANGE_PROGRESS_3.md` 末尾の「進捗第3巻終了・第4巻への移行（2026-10-26）」で終了した
- 第3巻以前の記録は履歴として維持する
- 第3巻以前の「最新再開地点」は当時の記録であり、現在地として自動的に使用しない
- 今後の最新進捗と最新再開地点は本第4巻へ記録する
- 技術的詳細の正本は、各時点で指定された詳細設計メモを参照する
- 第4巻開始時点の技術的正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` の **§23** である

**検索語:** ORDER_EXCHANGE_PROGRESS_4、進捗第4巻、TVT-MP、4交差点、nonparticipating 20％、T=382、初回Actual arrival、Actual arrival上書き、Baseline arrival一致、first divergenceなし、T=402、一時skip、clearance、C順位183、Actual通過順位177、selected=False、baseline fallback、leading nonparticipating、順位確定源、完了、最新再開地点、Git対象、commit、push。

---

# 4交差点nonparticipating 20％ trial・T=382取引確認完了と第4巻開始（2026-10-26）

## 1. 第4巻開始時点

- `ORDER_EXCHANGE_PROGRESS_3.md` は **6,708 行に達した時点で新巻移行を判断** し、その後、末尾へ最終接続記録を追加して終了した
- `ORDER_EXCHANGE_PROGRESS_4.md` は今回新規作成する
- 新巻移行の境界は、4交差点 nonparticipating 20% trial の **T=382 成立取引** に関する一連の確認完了である
- T=382 取引周辺の技術確認自体には未完了事項を残さない
- 技術的正本は詳細設計第5巻 **§23** である

## 2. 技術的正本

**技術的正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`

**参照節:** §23「4交差点nonparticipating 20％ trial・T=382取引の初回到着訂正、物理一致、通過差、および順位確定源確認完了（2026-10-26）」

第4巻には再開上必要な要点だけを記録し、詳細な時系列、CSV 行数、診断内部、static validation 修正履歴は §23 を参照する。

## 3. 第4巻開始時点の完了事項

### 3.1 正式な初回 Actual arrival

T=382 取引 4 party について、Baseline arrival と正式な初回 Actual arrival は全件一致した。

| Visit | Baseline arrival | Actual first arrival | 差 |
|---|---:|---:|---:|
| `veh_sw_nw_base_037:2` | 388 | 388 | 0 |
| `veh_nw_sw_base_047:1` | 390 | 390 | 0 |
| `veh_wn_se_base_024:1` | 392 | 392 | 0 |
| `veh_en_sw_base_025:2` | 394 | 394 | 0 |

旧診断の **395、407、403、397** は、同一 Visit の到着登録再呼出し時に診断辞書を無条件上書きした結果であり、**初回 Actual arrival ではなかった**。旧値による到着差 7、17、11、3 timestep は交通予測誤差ではない。production の `arrival_time` は再呼出し後も初回値を維持していた。

### 3.2 Baseline／Actual 物理比較

- 対象 4 Vehicle について first divergence なし
- 対象 4 inlink について比較可能範囲で差なし
- T=382 から各対象 Visit の正式な初回到着まで、対象 Vehicle の inlink 上の物理進展について Baseline fork と Actual 実 World の差は確認されなかった

**first divergence** とは、同一 timestep・同一 phase の Baseline と Actual で物理状態が **最初に** 異なる時点と field である。

### 3.3 nonparticipating Visit の通過差

**対象:** `veh_wn_se_base_024:1`

**正式値:**

- Baseline arrival=392
- Actual first arrival=392
- Baseline passage=404
- Candidate passage=403
- Actual passage=404

Candidate／Actual passage 差 1 timestep は **到着差ではない**。

**確認した流れ:**

- T=402: 入口空間不足により対象 Visit を一時 skip
- T=402: 別 inlink の C183 Visit が通過
- T=403: 対象 Visit は entry space 利用可能だが clearance 未充足
- T=403: clearance 未充足により対象 Node の通過処理終了
- T=404: clearance 充足後に対象 Visit が通過

### 3.4 C 順位と Actual 通過順位

**`veh_sw_nw_base_039:2`:**

- assigned C 順位=183
- Actual 通過順位=177
- Actual passage=402

C 順位と Actual 通過順位は **異なる概念** である。診断の `assigned_rank` は rank ledger 上の C 順位であり、Actual 通過順位ではない。

### 3.5 selected=False 時の順位確定源

**正式確認済み:**

| T | Visit | 参加属性 | C順位 | 正式確定源 |
|---:|---|---|---:|---|
| 390 | `veh_sw_nw_base_038:2` | participating | 178 | baseline fallback |
| 404 | `veh_sw_nw_base_041:2` | participating | 185 | baseline fallback |
| 406 | `veh_nw_sw_base_049:1` | nonparticipating | 186 | leading nonparticipating confirmation |

**selected=False** は、取引案が採用されなかったことを意味する。selected=False でも、Baseline fallback または leading nonparticipating 先行確定等により C 順位が正式に確定し得る。

### 3.6 production 評価

今回の確認範囲では、production 変更が必要な欠陥は確認されなかった。旧 Actual arrival 値の問題は、旧診断の観測・保存方法の欠陥であり、production の arrival 記録欠陥ではない。T=382 取引周辺の一連の確認は **完了** とする。

## 4. 今回作成した診断

1. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_baseline_actual_inlink_arrival_divergence.py`
   **目的:** 初回 Actual arrival、再登録監査、Baseline／Actual 物理比較、first divergence、selected decision、新規 C 順位

2. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_rank_confirmation_sources.py`
   **目的:** selected=False で新規 C 順位を得た Visit の正式確定源を upstream result object から特定

診断出力 directory の完全な長いパスや全 CSV 行数は、詳細設計第5巻 §23 を参照する。

## 5. 第4巻開始時点の未完了事項

### 5.1 旧診断の扱い

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py`

**検討事項:**

- 初回 Actual arrival を無条件上書きする処理を修正するか
- 歴史的診断として変更せず残すか
- 残す場合、正式な最新参照先として詳細設計第5巻 §23 を明記するか
- 旧出力の 395、407、403、397 を正式 arrival として再利用しない

**この判断は未完了である。**

### 5.2 Git 対象

**未確定:**

- 今回追加した 2 診断スクリプトを Git 対象にするか
- 今回生成した 2 つの diagnostic output directory を Git 対象にするか
- 旧 `rank_and_passage_trace` を修正する場合、その修正を同じ commit へ含めるか
- 既存の未追跡ファイル群から、今回作業に直接関係するものだけをどう選別するか

既存の未追跡ファイルを一括追加してはならない。`diagnostics/order_control.zip` は既存の未追跡ファイルであり、今回の作業対象として自動追加しない。

### 5.3 文書保存

**保存対象候補:**

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` の §23
- `ORDER_EXCHANGE_PROGRESS_3.md` 末尾の第4巻移行記録
- `ORDER_EXCHANGE_PROGRESS_4.md`
- Git 対象と判断した診断スクリプト
- Git 対象と判断した診断出力

メモを含む commit 名には、必ず **document** を含める。実装前仕様の文書化ではないため、complete を禁止する既存方針との衝突はないが、commit 名は実際の変更範囲を正確に表すものとする。

**Git 操作は Cursor に行わせない。** commit・push は利用者が Terminal で実行する。

### 5.4 次の研究分析

T=382 取引確認そのものは完了している。次の研究分析へ進む前に、4交差点 nonparticipating 20% trial について、今回の T=382 取引確認以外に新たな必須確認が残るかを整理する。確定済みの仕様や今回完了した検証を、明確な矛盾なしに再度未完了へ戻さない。

## 6. 最新再開地点

1. 旧 `rank_and_passage_trace` の扱いを決める
2. 今回作成した 2 診断スクリプトと 2 diagnostic output directory の Git 対象を決める
3. 既存の未追跡ファイル群から今回作業に直接関係するファイルだけを選別する
4. 必要なら旧診断へ修正または最新正本参照を追加する
5. py_compile、static validation、生成出力の独立確認結果を最終確認する
6. 詳細設計第5巻 §23、進捗第3巻移行記録、第4巻、および採用した診断関連ファイルを commit する
7. commit 結果・最新 commit・残存変更を確認する
8. 別の Terminal 指示で push し、push 後の git status と最新 commit を確認する
9. その後、次の研究分析へ進む

**本節が、進捗第4巻開始時点の最新再開地点である。**

本節は第4巻開始時点の再開地点である。追加検証後の最新再開地点は **§9** を参照する。

---

## 7. 第4巻開始後に完了した追加検証

**技術的正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§24**（時系列・表・診断出力の詳細は §24 を参照。本節は再開用の要点のみ）。

### 7.1 旧rank-and-passage診断の修正とeval_1000再実行

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py`

**完了事項:**

- Actual arrival を `World.T` で再登録ごとに上書きする旧診断処理を修正した
- production の `current_visit["arrival_time"]` を original method 呼出し後に読み、正式初回値を取得する
- key 未登録時だけ保存し、再登録時は上書きせず production 値が初回値を維持することを照合する
- T=382 対象 4 party の正式初回 Actual arrival:
  - `veh_sw_nw_base_037:2` = 388
  - `veh_nw_sw_base_047:1` = 390
  - `veh_wn_se_base_024:1` = 392
  - `veh_en_sw_base_025:2` = 394
- 旧値 395、407、403、397 は正式初回 arrival ではない
- static validation が `current_visit.get("arrival_time")` を誤認識した問題を修正した（runtime の `wrapped_arrival` と static validation は別件として §24.2 に記録）
- 診断専用 World を 100 timestep 延長（eval_1000: evaluation T=0..999、TSIZE=1030、simulation 後 World.T=1000）。正式 trial・production は変更していない
- `completed_trip_count`=600、`incomplete_vehicle_count`=0。eval_900 終了時未完了 3 台も完走
- 延長後の集計は eval_900 と同値（成立 228、passage 一致 611／不一致 15 等）。T=900..999 に新規成立取引なし

**出力 directory（eval_1000 区別）:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_1000_timestep_seed_1_nonparticipation_seed_3_t382_rank_and_passage_trace`

**§5.1 の未完了だった「旧診断の扱い」は、本修正により「修正済み・最新正本は §23／§24」へ更新した。**

### 7.2 成立取引228件の正式inlink全件診断

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py`

**完了事項:**

- 成立取引 228、party 626、buyer 263、seller 324、nonparticipating 39 を確認
- 正式 inlink は selected Candidate の保存済み `inlink_name` から取得（Vehicle 名・OD 名・終端 Link から推測していない）
- 複数 buyer 取引 32、複数 seller 取引 83、nonparticipating 含有 37、最大当事者 6・該当取引 1 件
- buyer／seller と nonparticipating の同一 inlink 共存は **0 件**（buyer+NP、seller+NP とも 0）

**出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_established_party_inlinks`

### 7.3 最大6当事者取引T=392の交通・順位・経済監査

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py`

**完了事項:**

- T=392 `northwest_intersection`、evaluation index 5、buyer 3・seller 3・nonparticipating 0、trade scope 6
- Candidate passage と Actual passage は 6 台全件一致
- C 順位と Actual node passage rank は別概念（個別不一致のみで production 欠陥としない）
- 経済・支払・補償・満足度は保存済み正式値の範囲で矛盾なし（完全正当性証明ではない）

**出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_t392_maximum_party_transaction_review`

### 7.4 T=392 buyer到着差の原因確認

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py`

**対象 Visit:** `veh_wn_se_base_025:1`（Baseline arrival 410、Actual first arrival 406、passage 420／416／416）

**完了事項:**

- Actual 406 は production 初回 `arrival_time` 由来であり、診断上書きではない
- T=392 common origin では対象 inlink の物理状態一致。最初の確認済み物理差は T=406 `after_node_transfer`
- 同一 inlink 前方 buyer の早期通過により後続が inlink 先頭（physical index 0）化し、Actual 到着が早まった物理効果。production arrival 記録欠陥ではない

### 7.5 nonparticipating含有取引の構成とB1・S1・N2確認

**完了事項（集計・§24.9〜24.12）:**

- nonparticipating 含有成立取引 37 件はすべて buyer≥1 かつ seller≥1（候補形成契約に矛盾なし）
- nonparticipating 含有の最大 trade scope=4、該当 **13 件**（B1・S2・N1 が 9、B2・S1・N1 が 2、**B1・S1・N2 が 2**: T=150・T=457 `northwest_intersection`）
- T=150・T=457 の 4 party 取引で Candidate／Actual passage 全件一致。T=150 は C 順位と Actual 通過順も一致。T=457 は 2 nonparticipating の Actual 通過順のみ C 順位と逆（rank difference total=0）

### 7.6 T=457のC213／C214通過順逆転の正式確認

**対象:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py`

**対象 nonparticipating:**

- C213 `veh_nw_sw_pulse_004:1`（C 順位 213、Actual passage rank 214、passage T=475）
- C214 `veh_sw_nw_base_050:2`（C 順位 214、Actual passage rank 213、passage T=472）

**完了事項（§24.13）:**

- **T=472:** C213 先判定 → Candidate／Actual とも `outlink_entry_space_unavailable`（進路先 Link 入口空間不足）。clearance 未充足ではない。一時 skip のうえ走査継続 → C214 が T=472 で通過
- **T=473:** C213 は `clearance_not_satisfied` で当該 timestep の Node 走査終了（**T=472 逆転の原因ではない**）
- **T=474:** C213 は再び入口空間不足で一時 skip
- **T=475:** C213 が通過
- Candidate 局所仮想計算と Actual 実 World の判定が一致し、取引 4 party の Candidate／Actual passage は一致。設計どおりの挙動であり、本確認範囲で production 欠陥は確認されなかった

**出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_t457_nonparticipating_passage_order_trace`

### 7.7 診断実行と詳細設計メモ§24

今回の **5 診断**（小節との対応）:

| 小節 | スクリプト |
|---|---|
| §7.1 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py` |
| §7.2 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py` |
| §7.3 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py` |
| §7.4 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py` |
| §7.6 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py` |

**§7.5** は、上記診断および標準 research output を用いた構成集計・横並び確認であり、**6 本目の診断スクリプトではない**。

上記 5 診断について、個別実行時に次を確認済み: **py_compile 成功、static contract ok、simulation 正常完了、output directory 作成成功**（§24.15 にも記録）。**py_compile の一括再確認も成功済み**。**static validation の一括再確認は未完了**。

**文書:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` に **§24** を追記済み（本進捗 §7 と対応）。

---

## 8. 現在の未完了事項

§5〜§6 は第4巻**開始時点**の未完了記録である。以下は **2026-10-27 時点** の未完了である。

### 8.1 Git とファイル採否

今回の **Git 対象候補は次の 7 ファイルに限定**する（一括追加禁止）。

**メモ 2 本:**

1. `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
2. `ORDER_EXCHANGE_PROGRESS_4.md`（本ファイル）

**診断 5 本:**

3. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py`
4. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py`
5. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py`
6. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py`
7. `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py`

第4巻開始時の次の 2 診断は **§4 の技術的参照として残す**が、今回の git status では未追跡／変更済みとして出ていないため、**今回の commit 採否対象に含めない**。

- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_baseline_actual_inlink_arrival_divergence.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_rank_confirmation_sources.py`

- diagnostic **output directory** は再生成可能であり、今回の Git 対象外候補（`research_outputs` に Git 管理済み 0 件という既存確認）
- `diagnostics/order_control.zip`、single／two intersections 関連未追跡は今回対象外
- **commit・push は利用者が Terminal で実行**（Cursor は実行しない）。メモを含む commit 名には **document** を含める

### 8.2 検証と文書

**完了済み:**

- 5 診断の個別 py_compile
- 5 診断の個別 static validation
- 5 診断の simulation
- 5 診断の output directory 作成
- 5 診断の py_compile 一括再確認
- 5 診断の static validation 一括再確認: 完了（5 本すべて `static contract ok`）
- 2 メモの `git diff --check`
- 詳細設計第 5 巻 §24 と進捗第 4 巻 §7〜§9 の独立内容確認: 完了
- 独立確認で発見した記載事項の修正: 完了
  - 詳細設計第 5 巻 §24.10 の T=382 構成を B1・S2・N1 へ訂正
  - 詳細設計第 5 巻 §24.16 の古い進捗状態と重複項目を修正
  - 進捗第 4 巻 §7.7 の 5 診断対応を訂正
  - §7.5 は 6 本目の診断ではなく、標準 research output 等を使った構成集計・横並び確認であると整理
  - Git 候補を今回の 5 診断＋2 メモの 7 ファイルへ限定
  - 第4巻開始時の 2 診断は技術的参照として残すが、今回の commit 候補から除外
  - T=472 の入口空間不足と T=473 の clearance 未充足が明確に区別されていることを確認
- Terminal 確認により、`Baseline localrank` 等の指摘表記誤りは §24.11・§24.12 の表に実在しなかった（追加の表記修正は不要）

**未完了:**

- 5 診断の最終 Git 採否
- research_outputs を Git 対象外とする最終確認
- Git 差分と status の最終確認
- 対象 7 ファイルだけの stage
- staged diff の確認
- commit
- commit 後の status と最新 commit 確認
- 別指示で push
- push 後の status と最新 commit 確認

### 8.3 研究分析

- 文書保存と Git 完了後に、4 交差点 nonparticipating 20% trial の**次の研究テーマ**を決める
- §3・§7 で完了した確認を、明確な新証拠なしに未完了へ戻さない

---

## 9. 最新再開地点

**技術的正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§23**（T=382 周辺・順位確定源）と **§24**（成立取引全体・T=392／T=457 追加検証）。

**現在地:** 第4巻開始時点（§1〜§6）の T=382 確認に加え、§7 の追加検証まで完了。production 変更は不要と判断（§24.14）。**完了済み:** 5 診断の py_compile 一括再確認、5 診断の static validation 一括再確認、2 メモの独立内容確認、独立確認で発見した記載誤りと古い状態記述の修正、詳細設計第 5 巻 §24 と進捗第 4 巻 §7〜§9 の内容整合。**残作業:** 下記 Git 手順（7 ファイル）。

**対象ファイル（Git 候補・7 ファイルのみ）:**

| # | 種別 | パス |
|---:|---|---|
| 1 | 詳細設計 | `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`（§24 含む） |
| 2 | 進捗 | `ORDER_EXCHANGE_PROGRESS_4.md`（本ファイル） |
| 3 | 診断（修正） | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py` |
| 4 | 診断（新規） | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py` |
| 5 | 診断（新規） | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py` |
| 6 | 診断（新規） | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py` |
| 7 | 診断（新規） | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py` |

第4巻開始時の 2 診断（§4）は技術参照として残るが、上表の Git 候補には含めない。

**次に利用者が Terminal で行う確認（推奨順）:**

1. `git status` と今回対象 7 ファイルの差分を確認する
2. `research_outputs` に Git 管理済みファイルがないことを最終確認する
3. 今回対象 **7 ファイルだけ**を stage する
4. `research_outputs`、`diagnostics/order_control.zip`、single intersection／two intersections 関連未追跡ファイルを stage しない
5. `git diff --cached` で staged 内容を確認する
6. `document` を含む commit 名を確定する
7. commit する
8. commit 後に `git status` と最新 commit を確認する
9. 別の Terminal 指示で push する
10. push 後に `git status` と最新 commit を確認する
11. その後、次の研究分析テーマを決める

Git 対象は今回の **5 診断＋2 メモの 7 ファイルに限定**する。第4巻開始時 2 診断、output directory、その他の未追跡ファイルを含めない。

**本節が、進捗第4巻の最新再開地点である（2026-10-27）。**

---

## 10. N=5 Candidate Visit数上限trialの検証完了

**Candidate Visit数上限**（**trade_scope上限**）を **N=10** から **N=5** に切り替えた独立 trial について、実作動検証を完了した。技術的正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§25**（本節は進捗要約）。

### 10.1 検証目的

- 既存 production、既存 **N=10** trial、既存出力を変更せず、同じ 600 台・同じ seed・同じ条件で **Candidate Visit数上限** だけを **N=5** とした独立 trial を検証した。
- 目的は、**N=10** の **T=392** 最大 6 当事者取引が消えるか、全成立取引が 5 当事者以下になるか、**上限外Visit** の後続処理、buyer／seller 必須条件、Node 単位 C 順位連続性を確認することだった。
- 詳細な技術正本は詳細設計第 5 巻 **§25** である。

### 10.2 Candidate Visit数上限N=5の実作動

- **N=5** 包括 trial は全 600 台完走済み。
- 全成立取引は 5 当事者以下。
- **T=392** では **P−1適格列** 上の適格 Visit が **6 件**あった。
- `candidate_visits` には Baseline 順位先頭 **5 件**だけが入った。
- 6 件目 `veh_wn_se_base_025:1` は同 decision の Candidate 形成から正式に除外された。
- **上限外Visit** は消失せず、後続 decision で評価された。
- **N=10** の **T=392** 最大 6 当事者取引は **N=5** では成立しなかった。
- **N=5** では buyer 1、seller 4 の別の 5 当事者取引が成立した。
- buyer 1 件以上、seller 1 件以上の正式 Candidate 条件は維持された。
- buyer あり seller なしの正式成立 Candidate は確認されなかった。
- **production変更不要**と判断した。

### 10.3 N=10とN=5のT=392 selected取引差

**N=10:**

- 6 当事者
- buyer 3、seller 3
- surplus = **1.3713611846287553**

**N=5:**

- 5 当事者
- buyer: veh_nw_sw_base_048:1
- seller: veh_en_sw_base_026:2, veh_sw_nw_base_039:2, veh_sw_nw_base_040:2, veh_wn_en_base_025:1
- surplus = **1.1234655338878686**

比較:

- **N=10** surplus − **N=5** surplus = **0.2478956507408867**
- **N=10** の余剰は **N=5** より約 22.1% 大きい
- **N=5** selected Candidate は feasible Candidate 中で一意に最大余剰
- 全不成立 Candidate より余剰が厳密に大きいわけではなく、同じ余剰値を持つ不成立 Candidate がある
- 同値の不成立 Candidate は **buyer_nonpositive_value** 等の個別成立条件を満たさない

- `veh_sw_nw_base_039:2` と `veh_sw_nw_base_040:2` は **N=5** でも **N=10** でも **seller**（buyer ではない）。
- **N=5** では両車の Candidate passage は Baseline passage と同じ（039: 402→402、040: 406→406）。

### 10.4 上限外VisitとC184／C185の連続性

**T=392** selected Candidate: **C179〜C183** を付与。

**C184:**

- VisitKey: **veh_sw_nw_base_041:2**
- 初回付与: **T=401**
- source: **baseline fallback**
- finalization_source: baseline
- final_rank_status: baseline_fallback_ranks

**C185:**

- VisitKey: **veh_wn_se_base_025:1**
- 初回付与: **T=404**
- source: **baseline fallback**
- finalization_source: baseline
- final_rank_status: baseline_fallback_ranks

- **C184** と **C185** は別 decision で付与された。
- Node 単位の C 順位に欠番、重複、上書きは確認されなかった。
- `veh_wn_se_base_025:1` が後続 selected 取引で buyer／権利保有車両となって **C184** を譲ったという当初仮説は**反証**された。
- 同 Visit は T=393〜404 に selected Candidate buyer ではなく、**selected Candidate 当事者自体でもなかった**。
- seller または nonparticipating として selected Candidate に参加した事実もない。
- T=404 に right-of-entry となったが selected Candidate はなく、**baseline fallback** で **C185** を得た。

### 10.5 veh_sw_nw_base_041:2がT=392 Candidate外だった理由

**T=392** driver 直前:

- Vehicle は `veh_sw_nw_base_041`
- current Link: `south_west_od_to_southwest_intersection`
- current Visit Node: `southwest_intersection`
- Visit ID: **1**（Northwest 向けではない）
- 対象 inlink `southwest_intersection_to_northwest_intersection` には**対象inlink未進入**
- Northwest 向け Visit 2 は未登録
- Northwest 用 **snapshot固定Visit集合**、collector export、inlink physical order、`candidate_visits` に存在しなかった
- Candidate 外理由: `not_in_snapshot_fixed_visit_set`

その後:

- **T=397** driver 前までに対象 inlink へ進入、進入時 Northwest 向け Visit ID **2**
- T=401 正式 snapshot で同 inlink の physical index 2、前方 `veh_sw_nw_base_039:2`・`veh_sw_nw_base_040:2`
- **Baseline arrival 407**、Baseline passage 414、right-of-entry、driver 後 **C184**
- 比較対象 B（`veh_wn_se_base_025:1`）の Baseline arrival は **410**
- Actual northwest **arrival** は **T=407**；T=401 の Baseline arrival **407** と Actual arrival **407** は一致

因果関係:

- T=392 の Baseline が T=407 到着を見落としたのではない。
- T=392 時点では Northwest 向け Visit 2 がまだ存在しなかったため、Northwest 用 **snapshot固定Visit集合**の対象外だった。
- Visit 2 登録後の T=401 Baseline では到着 **407** を正しく予測した。
- **407** は B の **410** より早いため、A が B より先に right-of-entry となり **C184** を得た。

### 10.6 対象inlink未進入将来VisitをCandidateへ含めない方針

- 意思決定時点で **対象inlink未進入** の **将来Visit** は Candidate 形成へ含めない。
- 将来その対象 inlink へ進入するとは限らない。将来進路は未確定の場合がある。
- TVT 取引や他 Node の順位制御により対象 inlink への進入時刻も変わり得る。
- 未進入 Visit まで含めると、不確定な進路と進入時刻に依存する順位取引になる。局所仮想計算の不確実性と計算量も増える。
- **snapshot固定Visit集合**に載り、対象 inlink 物理順へ登録可能な Visit だけを Candidate 対象とする現行方式を維持する（コード欠陥ではなく研究上やむを得ない局所化）。
- production は変更しない。

### 10.7 今回のtrial・診断・独立確認

- `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_maximum_party_transaction_review.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t404_c184_c185_rank_gap.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_t401_c184_physical_order.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_veh_sw_nw_base_041_real_world_location.py`

- 診断実装中に、driver 前／後時点、mutable rank state、正式 CSV role 別空欄、current Visit 正式 dict、Link 終端 Node、再帰上限、完走専用 API、static validation 等の**診断側**問題を修正した（production 欠陥ではない）。
- 重要箇所は Cursor 報告だけに依存せず、Terminal で原典と出力を独立確認した。
- 詳細は設計メモ第 5 巻 **§25.12** を参照する。

### 10.8 完了判断

- **N=5 Candidate Visit数上限** trial の実作動検証は**成就した**。
- **N=5** 上限、成立取引当事者数、経済条件、**上限外Visit**、C 順位連続性、**対象inlink未進入** Visit の扱いまで確認済み。
- **production変更不要**。
- これらを明確な新証拠なしに未完了へ戻さない。
- 技術的正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§25**。

---

## 11. 現在の未完了事項

### 11.1 偶数到着時刻

- **T=392** 周辺の Baseline／Actual arrival と passage が**偶数到着時刻**へ集中している。
- Arrival hook により、確認対象では raw `arrival_time` 自体が整数偶数であり、診断の丸めによるものではない。
- **N=10** でも偶数時刻が確認されている。
- 出発時刻の位相が原因か、車両更新・Link 移動・Node 処理等の実質的 2 timestep 周期が原因かは**未確定**。

### 11.2 departure plus 1 trial

推奨新規ファイル:

`research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial.py`

方針:

- 既存 production、**N=10** trial、**N=5** trial、既存出力を変更しない。
- 全 600 台の departure time だけを一律 **出発時刻1 timestep遅延**（**departure plus 1**）。
- 車両数、OD、進路、VOT、participation、seed、nonparticipation seed、**N=5**、network、TVT 設定、需要間隔の相対関係は固定。
- 旧 **T=392** と新 T=393 を比較（Visit 集合、roles、Candidate 順位、経済値、arrival／passage、C 順位、奇偶）。
- 全時刻 +1 で奇数化→出発位相主因；+1 後も偶数→2 timestep 周期；混在→交通相互作用。
- 現時点では**未作成**・**未実行**。

### 11.3 Gitとファイル採否

- **N=5** trial、4 診断、2 メモの Git 採否は**未確定**。
- `research_outputs` の Git 採否は**未確定**。
- stage、commit、push は**未実施**。
- Git 操作は利用者が Terminal で行う。メモを含む commit 名には `document` を含める。実装前仕様の文書化を表す commit 名では `complete` を使用しない。
- 既存 §8・§9 の旧 7 ファイル Git 候補は当時の記録である。最新の Git 候補は **§12** で改めて整理し、古い記録を削除しない。

---

## 12. 最新再開地点

**技術的正本:**

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§25**（**N=5 Candidate Visit数上限**・**T=392**・**C184**／**C185**）
- 過去の **N=10** 最大 6 当事者取引は同メモ **§24**

**現在地:**

- **N=5** **Candidate Visit数上限** trial の実作動検証は成就済み
- **production変更不要**
- 次の研究作業は **departure plus 1** trial（**未作成**・**未実行**）
- 出発時刻 +1 以外の変更を加えない

**次に実施する作業:**

1. 既存 **N=5** trial の車両 departure time 生成・設定箇所を read-only で確認する
2. 既存 **N=5** trial を変更せず、**departure plus 1** 専用 trial を新規作成する
3. 全 600 台の departure time だけを +1 timestep する
4. static validation で差分が departure time だけであることを検査する
5. 新 trial を完走させる
6. 旧 **T=392** と新 T=393 を比較する専用診断を作成する
7. Visit 集合、roles、Candidate 順位、経済値、arrival／passage、C 順位、奇偶を比較する
8. **偶数到着時刻**集中の原因を判定する
9. 結果を詳細設計メモと進捗メモへ反映する
10. その後に Git 採否、stage、commit、push へ進む

**最新の Git 候補（最終確定前）:**

メモ:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
- `ORDER_EXCHANGE_PROGRESS_4.md`

**N=5** trial・診断:

- `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_maximum_party_transaction_review.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t404_c184_c185_rank_gap.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_t401_c184_physical_order.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_veh_sw_nw_base_041_real_world_location.py`

**N=5** 包括 trial 作成時または検証途中に作成・修正した **N=5** 関連ファイルが他にも存在する可能性があるため、上記を最終 Git 対象と**まだ断定しない**。Git 作業前に、利用者が Terminal で `git status` と差分を確認し、今回対象を最終確定する必要がある。

`research_outputs`、`diagnostics/order_control.zip`、今回と無関係な未追跡ファイルは自動的に stage しない。

**再開時の注意:**

- Cursor には必要な調査・編集だけを行わせる
- py_compile、static validation、simulation、grep、Git 操作は Terminal で実行する
- Cursor 報告を重要節目で鵜呑みにせず、原典・出力を Terminal で独立確認する
- Cursor 処理を未完了状態のまま別作業へ移さない
- **departure plus 1** trial 以外の設計変更を同時に入れない

**本§12が、進捗第4巻の最新再開地点である（2026-10-28）。**
