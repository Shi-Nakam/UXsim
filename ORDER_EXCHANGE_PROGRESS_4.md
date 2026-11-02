# ORDER_EXCHANGE_PROGRESS_4

本ファイルは TVT-MP 研究の進捗記録 **第4巻** である。

- 第3巻は `ORDER_EXCHANGE_PROGRESS_3.md` 末尾の「進捗第3巻終了・第4巻への移行（2026-10-26）」で終了した
- 第3巻以前の記録は履歴として維持する
- 第3巻以前の「最新再開地点」は当時の記録であり、現在地として自動的に使用しない
- 今後の最新進捗と最新再開地点は本第4巻へ記録する
- 技術的詳細の正本は、各時点で指定された詳細設計メモを参照する
- 第4巻開始時点の技術的正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` の **§23** である
- **2026-11-02 追記:** 監査出力・full-run audit helper・3,000 台長期 trial の技術的正本は詳細設計 **§30**。進捗の最新再開地点は **§19**（§23・§18 等は **歴史記録**として維持）

**検索語:** ORDER_EXCHANGE_PROGRESS_4、進捗第4巻、TVT-MP、横並び表示、事後分析、監査出力、full-run audit helper、nonparticipating 20％、全車完走、交通解消、3,000台、T=999、departure-end、4交差点、T=382、初回Actual arrival、Actual arrival上書き、Baseline arrival一致、first divergenceなし、T=402、一時skip、clearance、C順位183、Actual通過順位177、selected=False、baseline fallback、leading nonparticipating、順位確定源、完了、最新再開地点、Git対象、commit、push。

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

本 §11 は当時の未完了記録である。**偶数到着時刻** の局所反証、**departure shift** 0〜3、**arrival tiebreaker** 原因は **§13** で完了として記録した。残る未完了は **§14**。最新再開地点は **§15**。本節は削除しない。

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

本 §11.2 は当時の履歴である。その後、予備 **departure plus 1** trial と aligned **departure shift** 0〜3 trial を作成・実行し、shift 0／3 の最初の成立取引分岐を **arrival tiebreaker** 割当て変化まで確認した。最新状態は **§13〜§15**、技術的正本は詳細設計第5巻 **§26**。予備 plus 1 は evaluation end 899／TSIZE 930 のままなので、全期間比較の最終正本には使わない。

### 11.3 Gitとファイル採否

- **N=5** trial、4 診断、2 メモの Git 採否は**未確定**。
- `research_outputs` の Git 採否は**未確定**。
- stage、commit、push は**未実施**。
- Git 操作は利用者が Terminal で行う。メモを含む commit 名には `document` を含める。実装前仕様の文書化を表す commit 名では `complete` を使用しない。
- 既存 §8・§9 の旧 7 ファイル Git 候補は当時の記録である。本 §11.3 執筆時点の最新 Git 候補は **§12** であった。その後の候補整理は **§15**。古い記録を削除しない。

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

**本§12は、進捗第4巻の当時の再開地点である（2026-10-28）。** 当時の次作業は **departure plus 1** trial（未作成・未実行）であった。その後の **departure shift** 0〜3 検証と **arrival tiebreaker** 原因分析は完了した。最新状態は **§13〜§15**、技術的正本は詳細設計第5巻 **§26**、最新再開地点は **§15**。本 §12 は削除せず履歴として残す。

---

## 13. departure shift 0〜3 trialとarrival tiebreaker原因分析の完了

**技術的正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§26**

§11〜§12 の「**departure plus 1** trial は未作成・未実行」「次作業は departure plus 1」は当時の記録である。本 §13 以降が最新状態である。古い節は削除しない。

### 13.1 trial条件

- 既存 **N=5** trial を **departure shift** 0 とした
- 全 600 台の departure timestep だけを一律 +1／+2／+3
- Vehicle 名、順序、OD、VOT、participation、nonparticipating 120 台、seed、network、N=5、clearance、baseline horizon は維持
- aligned 比較のため evaluation end、internal TSIZE、expected World.T も shift 分だけ後方へ移動
- aligned timestep = actual timestep − departure shift
- production は変更していない

予備スクリプト:

`research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial.py`

aligned 共通スクリプト:

`research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_shift_trial.py`

予備 plus 1 は evaluation end 899／TSIZE 930 のままなので、全期間比較の最終正本には使わない。

### 13.2 shift別成立取引数

| shift | evaluation end | TSIZE | World.T | 成立取引 | 完走 | 未完走 |
|------:|---------------:|------:|--------:|--------:|-----:|-------:|
| 0 | 899 | 930 | 900 | 226 | 600 | 0 |
| 1 | 900 | 931 | 901 | 230 | 598 | 2 |
| 2 | 901 | 932 | 902 | 226 | 600 | 0 |
| 3 | 902 | 933 | 903 | 228 | 600 | 0 |

未完走は正式評価終了時点の trip completion である。shift 1 の 2 台を TVT 順位未確定や内部 Link 残存と断定しない。

### 13.3 マクロ比較と反証

- shift 0／2 は aligned T=0〜899 で成立取引 **226 件の transaction signature が完全一致**
- shift 1／3 は不一致
- shift 0 ≠ shift 1、shift 0 ≠ shift 3、shift 1 ≠ shift 2、shift 1 ≠ shift 3、shift 2 ≠ shift 3
- 最初の aligned 成立取引分岐: 0対1 は T=621、0対2 は分岐なし、0対3／1対3／2対3 は T=602、1対2 は T=621
- 「**T=0固有説**」（shift 0 だけ特殊で 1／2／3 が一致）は成立しなかった
- 「単純な絶対時刻**偶奇依存**説」（0＝2 かつ 1＝3）も成立しなかった
- shift 0／2 完全一致が偶然か 2 timestep 構造かは **未確定**。shift 0／3 原因から周期と断定しない

旧 T=392 と shift 1 の T=393 では、局所的に Node、Candidate 集合、role、scope、C 順位、Actual passage rank、payment／compensation が一致し、passage は全 5 Visits で +1、旧偶数は奇数へ反転した。時刻が常に **偶数時刻** へ強制される仕組みではない。ただし全期間が単純な +1 **時間平行移動**とは結論しない。

### 13.4 shift 0／3最初の分岐

診断:

`research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_departure_shift_0_3_first_divergence_t602_t605.py`

- shift 0 actual T=602、shift 3 actual T=605、aligned T=602、`northeast_intersection`
- Candidate Visit集合は同一: `veh_wn_en_base_041:2`、`veh_ne_ws_base_031:1`
- aligned Baseline arrival は両 Visit とも **608**（**同着**）
- 正式順は反転。shift 0 は 041:2 → 031:1、shift 3 は 031:1 → 041:2
- right-of-entry も反転
- shift 0 は selected なし（`no_economically_feasible_candidate`）
- shift 3 は selected あり（buyer `veh_wn_en_base_041:2`、seller `veh_ne_ws_base_031:1`、buyer 1、seller 1、NP 0、scope 2、total_G 5.7009177956295645、total_R 0.0、surplus 5.7009177956295645）
- 公式支払 0.0 と Candidate 経済値は別。診断側で混同した runtime 期待値は修正済み（production 欠陥ではない）

### 13.5 arrival tiebreaker原因

- vehicle_id は shift 間で同一（408 と 303）
- **arrival tiebreaker** が変化し、大小関係が反転
- shift 0: 041:2 の 0.15385491114815542 < 031:1 の 0.3309686535605816
- shift 3: 031:1 の 0.12907910374092646 < 041:2 の 0.4920934727576123
- Vehicle ID 比較まで到達していない
- 正式 Baseline alignment sort key `(aligned arrival, arrival_tiebreaker, vehicle_id)` で再構築した順は正式 Candidate 順と一致（`formal_candidate_order_matches_sort_key` = True）
- `first_divergence_layer` = `candidate_visit_order_divergence`
- `detail_cause` = `arrival_tiebreaker_assignment_divergence`
- Candidate 順実装が sort key 契約に反した事実はない
- **fixed tiebreaker** は同一 simulation 内で一度付与後に固定される意味であり、別 simulation 間の同一乱数値保証ではない
- 初回は `W.rng.random()`、再訪は `W.order_control_rng.random()`
- 直接原因は正式 snapshot の tiebreaker 大小反転。最初に割当てをずらしたイベントは未追跡
- **production変更なし**

詳細正本は詳細設計 **§26**。

---

## 14. 研究運用方針と未完了事項

### 14.1 確定方針（利用者確定）

- 主たる比較対象は **signalized UXsim**／**FCFS**／**BATCH**／**TVT-MP**
- すべて **T=0開始**、同一 departure schedule、同一 Vehicle 生成順、同一 OD、同一 VOT、同一 participation、同一 network、同一 seed 条件、同一評価期間へ統一する
- **T=0開始** は departure 位相の不要な差を避ける実験統制である。方式間の交通状態・経路・到着イベント順が変われば **arrival tiebreaker** 割当てと `W.rng` **乱数消費順** はなおずれ得る
- **departure shift** trial は主性能比較に使用しない。**時間平行移動**・**偶数時刻**・tiebreaker 割当て依存の感度・反証試験として扱う
- production の tiebreaker 生成は現時点で変更しない（**production変更未採用**）。**決定論的tiebreaker** 化および **乱数源分離** は未採用・未実装
- 複数 seed の平均・分散を中心に方式性能を評価する。単一 seed の小さな数値差や個別順位・個別取引を方式固有の決定論的効果として厳密に解釈しない
- 同じ seed 番号でも方式間の厳密な **common random numbers** 対応は保証されない。paired 分析は乱数ストリーム対応が別途確認されている場合に限る
- 個別順位・個別取引の因果解釈には **arrival tiebreaker** 依存の留保を置く

### 14.2 未完了

- **決定論的tiebreaker** 化の具体設計
- **乱数源分離**
- FCFS／BATCH／TVT 全体への影響評価（route choice 等への実測波及を含む）
- **common random numbers** 設計
- shift 0／2 完全一致の原因（偶然か 2 timestep 構造か）
- production 変更の採否と実施時期
- 既存実験との後方互換方針

将来の **決定論的tiebreaker** 化、**乱数源分離**、**legacy mode**、**common random numbers**、**回帰試験**、**移行手順** の技術的叩き台は、詳細設計第5巻 **§26.21〜§26.34** を参照する。**未採用**・**未実装**である。現在の研究を停止する必須作業ではない。利用者の明示判断なしに production 改修へ進まない。

ただし、これらは現在の研究を停止する必須作業ではない。**決定論的tiebreaker** 実装へ自動的に進まない。

---

## 15. 最新再開地点

**技術的正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§26**。将来の arrival tiebreaker 改修候補はとくに **§26.21〜§26.34**（**未採用**・**未実装**。production 変更の承認ではない）。

N=5 Candidate Visit数上限検証の正本は同メモ **§25**。本 §15 が進捗第4巻の**最新再開地点**である。§12 は当時の再開地点として残す。

**現在地:**

- **N=5 Candidate Visit数上限** 検証完了
- **departure shift** 0〜3 検証完了
- **arrival tiebreaker** による最初の **同着順位** 分岐原因確認完了
- **production変更なし**（**production変更未採用**）
- 将来の **決定論的tiebreaker**／**乱数源分離** 叩き台は詳細設計 **§26.21〜§26.34** に記録。**未採用**・**未実装**
- 詳細正本は詳細設計第5巻 **§26**

次の研究作業については、今回のメモ追記後に利用者と決定する。**決定論的tiebreaker** 実装へ自動的に進まない。

**Git候補は未確定**として記録する。少なくとも今回新規・修正した次を候補として列挙する。

- `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial.py`
- `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_shift_trial.py`
- `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_departure_shift_0_3_first_divergence_t602_t605.py`
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
- `ORDER_EXCHANGE_PROGRESS_4.md`

ただし、関連ファイルが他にも存在する可能性があるため、Git 対象を最終確定しない。`research_outputs` は採否未確定。既存未追跡ファイルを自動 stage しない。

**再開時の注意:**

- Cursor には必要な調査・編集だけを行わせる
- py_compile、static validation、simulation、grep、Git 操作は Terminal で実行する
- Cursor 報告を重要節目で鵜呑みにせず、原典・出力を Terminal で独立確認する
- **決定論的tiebreaker** 実装や production 変更へ、利用者決定なしに進まない

**本§15が、進捗第4巻の最新再開地点である（2026-10-29）。**

---

## 16. 6×6 grid高需要スケーリング事前検証と最新再開地点（2026-10-31）

**記録日:** 2026-10-31。

**本 §16 を進捗第4巻の新しい最新再開地点とする。** 既存 **§15** は、arrival tiebreaker 検討完了時点の**当時の**最新再開地点として残す。

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§27**。

arrival tiebreaker および乱数源分離の将来設計は引き続き同メモ **§26** であり、§27 のスケーリング検証とは**別論点**である。

### 16.1 位置づけ

- 6×6 grid における TVT-MP の**作動可能性**、交通状態、入口 connector 飽和、計算量を調べる**事前検証**である。
- **正式な方式性能比較ではない**。
- FCFS 対照は、入口目詰まりが network・需要条件に由来するかを**集計的に**確認するために行った。
- 同じ seed 番号でも方式により乱数消費順が変わり得るため、**Vehicle 単位 paired 比較ではない**。
- **production は変更していない**。
- **5,000 台全車完走 TVT-MP trial** と **10,000 台 TVT-MP trial** は**実行していない**。

### 16.2 今回追加したスクリプト

既存 production、既存 trial、既存 test を**変更せず**、新規別スクリプトとして追加した。

- `research_scripts/run_tvt_mp_6x6_grid_high_demand_1000_vehicle_short_benchmark.py`
- `research_scripts/run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark.py`
- `research_scripts/run_fcfs_6x6_grid_high_demand_5000_vehicle_eval_600_comparison_trial.py`

### 16.3 1,000 台 TVT-MP 短期 benchmark

**条件:** 6×6 内部 grid、内部 Node 36、外部 OD Node 24、Link 168、Vehicle 1,000 台、departure T=0〜500、evaluation T=0〜999、internal TSIZE 1030、World.T 1000、全参加、clearance 1、baseline horizon 30、Candidate Visit 数上限 N=10、recursion limit 50,000。

**結果（保存済み観測値）:**

- completed 1,000 / incomplete 0
- 成立取引 1,078 件
- `exec_simulation_seconds = 7620.127332167001`
- `seconds_per_evaluation_timestep = 7.6201273321670016`
- output total bytes = 1,749,859
- transaction CSV、manifest、Node 別取引数合計が 1,078 で一致
- vehicle CSV と manifest Vehicle 数が 1,000 で一致
- production 例外なく完了し、正式 research output を生成した

**最大当事者数:** 最大 trade scope Visit 数 4、該当 28 取引、N=10 上限には未到達。

**代表取引（T=421、Node `g_2_3`、buyer 2、seller 2）:** buyer `veh_709:4`、`veh_364:7`；seller `veh_547:5`、`veh_696:4`。buyer 実現時間短縮価値合計 28.5218776672919、seller 必要補償合計 0.6592801312154991、buyer 公式支払合計 0.6592801312154991、seller 公式補償合計 0.6592801312154991、buyer 実現利得合計 27.8625975360764、seller 実現利得合計 0。Candidate passage と Actual passage が全 4 Visit で一致、assigned rank と Actual passage rank も一致、全 4 当事者 satisfied。

詳細は設計正本 **§27.6〜§27.7**。

### 16.4 5,000 台 TVT-MP early scaling benchmark

**条件:** Vehicle 5,000 台、departure T=0〜500、evaluation T=0〜599、internal TSIZE 630、World.T 600、全参加、clearance 1、baseline horizon 30、N=10、recursion limit 50,000。**全車完走を要求しない** early scaling benchmark。

**結果（保存済み観測値）:**

- end/completed 576、run 3,339、wait 1,085、not completed 4,424
- 成立取引 2,381 件（transaction CSV、manifest、Node 別合計が 2,381 で一致）
- `exec_simulation_seconds = 79685.76344854198`
- `seconds_per_evaluation_timestep = 132.80960574756998`
- output total bytes = 4,628,323

1,000 台 benchmark 保存値に対する per-timestep runtime ratio は **17.428790879509066**。**解釈:** evaluation 範囲と交通状態が異なるため、厳密な台数スケーリング則とは扱わない。

**実行条件の留保:** 実行中に Mac の sleep／screen lock 条件が一定でなく、途中から `caffeinate` を適用した。スクリプトの `perf_counter` 値、UXsim 進行表示の computation time、Mac sleep の関係は**未検証**。保存済み 79,685.763 秒を**純粋 CPU 時間と断定しない**。

### 16.5 5,000 台 trial の最大当事者取引

- 最大 trade scope Visit 数 **7**、該当 **2** 取引、N=10 上限には未到達。

**評価可能（T=301、Node `g_4_5`、buyer 1、seller 6、`ex_post_feasible`、全 7 Visit Actual passage 観測済み）:** buyer `veh_962:2` Baseline T=326、Candidate/Actual T=319、7 秒短縮、realized time value 5.247508144327783、official payment 4.57848957698266、realized gain 0.6690185673451232。seller 実績は設計正本記載どおり（`veh_1423:1` 3 秒遅延、`veh_841:4` 1 秒遅延、他 trivially satisfied 等）。全 7 当事者 satisfied。全 7 Visit で Candidate/Actual passage timestep 一致。**assigned rank と Actual node passage rank は完全一致ではない**。

**評価不能（T=598、Node `g_2_1`、buyer 6、seller 1、`evaluation_unavailable`）:** 全 7 Visit が evaluation end まで Actual passage 未観測。actual 経済値、Actual 順位、実現利得は評価不能。公式支払・補償 0。

詳細は設計正本 **§27.10**。

### 16.6 Link 理論収容力と TVT-MP 交通状態（T=599）

**理論収容（production 原典）:** jam density 0.2 台/m、単車線、`DELTAN=1`、内部 Link 400 m で 80 台、connector 300 m で 60 台、内部 120 Link で 9,600 台、connector 48 Link で 2,880 台、全 168 Link で **12,480 台**。5,000 台は 12,480 台を**超えない**。理論収容は全 Link 均等分散の仮定であり、**局所的入口飽和とは区別**する。

**TVT-MP 観測:** 内部 Link Vehicle 2,101 台、aggregate occupancy 0.21885416666666666、90%以上 6 本。外部→内部 connector Vehicle 1,224 台、aggregate occupancy **0.85**、90%以上 **13** 本、75%以上 22 本。内部→外部 connector Vehicle 14 台、aggregate occupancy 0.009722222222222222。ネットワーク全体満杯ではなく、**外部→内部 connector** とその直後の一部内部 Link が局所的に高収容となった。

### 16.7 FCFS 同条件対照

**条件:** Vehicle 5,000 台、departure T=0〜500、simulation T=0〜599、`TMAX` 600、内部 36 Node FCFS、clearance 1、network・需要は 5,000 台 TVT-MP benchmark と同条件。**正式な方式性能比較ではない。Vehicle 単位 paired 比較ではない。**

**結果:** end 513、run 3,285、wait 1,202、not completed 4,487。内部 Link 2,009 台、occupancy 0.20927083333333332、90%以上 8 本。外部→内部 connector 1,258 台、occupancy 0.8736111111111111、90%以上 12 本。内部→外部 connector 18 台、occupancy 0.0125。`exec_simulation` 3.4127832499798387 秒、seconds per evaluation timestep 0.005687972083299731、final script total 18.330203082994558 秒。

### 16.8 集計比較と原因判断

**FCFS − TVT-MP:** completed −63、run −54、wait +117、外部→内部 connector aggregate occupancy +0.023611111111111138、外部→内部 90%以上 Link 数 −1、内部 Link aggregate occupancy −0.009583333333333333。

**確定した整理（解釈）:**

- FCFS でも入口 connector 高収容と大量 wait が再現した。**入口目詰まりは TVT-MP 固有ではない**。
- 主因は、5,000 台を T=0〜500 へ集中投入した**高需要条件**と、単車線 6×6 network の入口・交差点処理能力である**可能性が高い**。
- 短期集計では TVT-MP が入口目詰まりを**特に悪化させた証拠はない**。
- TVT-MP は FCFS より completed **63 台多く**、wait **117 台少なかった**。
- 乱数消費順と route choice が方式間で変わり得るため、**TVT-MP の正式な性能優位とは結論しない**。

### 16.9 計算量に関する現在地

FCFS は同じ 5,000 台・600 timestep の simulation を約 **3.41 秒**で完了。**TVT-MP の長時間化を交通渋滞そのものだけでは説明できない**。

TVT-MP では full World Baseline 複製、baseline horizon 30 仮想計算、Candidate Visit 集合形成、最大 N=10 Candidate 検討、Candidate 局所仮想計算、経済評価と順位確定を反復する。**これらが計算量の主因である可能性が高い**。**profiling は未実施**、正式な**ボトルネックは未確定**。**production 最適化・近似化は未採用・未実装**。

FCFS との保存値比 **23,349 倍**を**純粋 CPU 性能倍率として採用しない**。**TVT-MP が FCFS より桁違いに重い**という定性的結論のみ維持する。

### 16.10 現時点の判断

- **production は変更しない**。
- **5,000 台全車完走 TVT-MP trial** へ直進しない。
- **10,000 台 TVT-MP trial** へ進まない。
- 5,000 台条件は**高需要ストレス条件**として有用。通常需要を代表する条件としては**過大な可能性**。
- 5,000 台という総台数より **T=0〜500 への集中投入**が重要。
- 1,000 台 trial は平均**約 2 台/timestep**。5,000 台を同じ平均投入強度へ揃えるなら departure 期間は**概ね 2,500 timestep**。
- departure 期間延長 trial は**未作成・未実行**。**次の優先対象は未決定**（候補: 中間規模 trial、5,000 台 departure 期間延長 trial、TVT-MP 計算量 profile）。**利用者判断前にいずれかへ自動的に進まない**。

### 16.11 未完了事項

詳細正本 **§27.16** を参照。主要項目:

- 中間規模 trial
- 5,000 台 departure 期間延長 trial
- 5,000 台全車完走 trial
- 10,000 台 trial
- 複数 seed
- signalized UXsim 同一短期条件対照
- BATCH 同一短期条件対照
- TVT-MP profiling
- World copy 回数・時間
- Baseline 回数・時間
- Candidate 形成数
- Candidate 局所仮想計算回数・時間
- Node 別・timestep 別負荷
- 計算量改善方針
- production 最適化の採否
- 通常需要条件と高需要ストレス条件の区別
- 論文上の位置づけ

### 16.12 最新再開地点（本節）

**本 §16 は 2026-10-31 時点の再開地点として記録する（歴史的記録）。**

**2026-11-01 以降の最新再開地点は §17。** 3,000 台 FCFS 需要選定・**TMAX=5000** 完走確認の詳細は詳細正本 **§28**。

| 論点 | 正本 |
|------|------|
| 6×6 高需要スケーリング・FCFS 対照 | 詳細設計 **§27** |
| arrival tiebreaker・乱数源分離（将来） | 詳細設計 **§26** |

**次の研究作業は未決定。**

**再開時:**

1. 詳細正本 **§27** を読む。
2. 本進捗 **§16** を読む。
3. 1,000 台 TVT-MP、5,000 台 TVT-MP、5,000 台 FCFS の manifest と run_summary を確認する。
4. 次の対象を、**台数調整**、**departure 期間延長**、**計算量 profile** から**利用者が決定**する。
5. **production 変更を前提にしない**。
6. profiling を行う場合は最初に **read-only 診断計画**を作る。
7. 長時間 trial は**開始時から** `caffeinate -i python <trial_script.py>` を用いる。**実行中 process への後付けのみ** `caffeinate -i -w <PID>`。
8. Cursor には編集・実装に**不可欠な調査だけ**を行わせる。
9. **py_compile**、**static validation**、**simulation**、**grep**、**Git 操作**は **Terminal** で行う。
10. 詳細設計正本と進捗メモの**双方への反映要否**を節目ごとに確認する。
11. **production 変更**や **arrival tiebreaker 実装**へ**自動的に進まない**。

### 16.13 Git 候補（未確定）

**Git 対象は未確定**として記録する。少なくとも今回の候補:

- `research_scripts/run_tvt_mp_6x6_grid_high_demand_1000_vehicle_short_benchmark.py`
- `research_scripts/run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark.py`
- `research_scripts/run_fcfs_6x6_grid_high_demand_5000_vehicle_eval_600_comparison_trial.py`
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
- `ORDER_EXCHANGE_PROGRESS_4.md`

`research_outputs` の採否は**未決定**。既存未追跡ファイルを**自動 stage しない**。関連ファイルが他にも存在する可能性があるため、**Git 対象を最終確定しない**。

**最新参照（2026-11-01）:** 3,000 台 FCFS 需要選定・**TMAX=5000** 完走確認の詳細は詳細正本 **§28**。進捗の最新再開地点は **§17**（本 **§16** は 5,000 台スケーリング時点の歴史的記録として維持）。

---

## 17. 3,000台FCFS需要条件選定・全車完走確認と最新再開地点（2026-11-01）

**検索語:** 3,000台、3台/timestep、2.5台/timestep、200m Link、60km/h、capacity_in、capacity_out、臨界密度、FCFS完走確認、TMAX=5000、最終完走時刻、需要条件選定、TVT-MP評価期間、vehicle plan digest。

### 17.1 今回の作業範囲

- **5,000 台集中投入**（§16）の次に、**3,000 台**条件を **FCFS** で選定した。
- **新規 FCFS スクリプト 4 本**を作成・実行した（§17.2）。
- **production**、既存 trial、既存 test、既存出力は **変更していない**。
- **3,000 台 TVT-MP 本体**は **未作成・未実行**。

### 17.2 作成・実行した4スクリプト

| # | スクリプト | 役割 |
|---|-----------|------|
| 1 | `run_fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial.py` | 当初 **400 m / 300 m / 20 m/s**、**2.5 台/timestep**、T=1,200 観測（道路未調整） |
| 2 | `run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial.py` | **全 Link 200 m / 60 km/h**、**2.5 台/timestep**、T=1,200 観測 |
| 3 | `run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_evaluation_t999_pretrial.py` | 同上道路、**3 台/timestep**、**T=999** 投入終了 snapshot（**全車完走不要求**） |
| 4 | `run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check.py` | 同上需要、**TMAX=5000** **FCFS完走確認**（T=999 snapshot **再取得なし**） |

（いずれも `research_scripts/` 配下。出力は `research_outputs/trial/` 配下の各 scenario directory。詳細 **§28.14**。）

### 17.3 採用候補となった道路条件

- 全 Link **200 m**、**60 km/h**、jam density **0.2 台/m**、reaction time **1 s**
- **capacity_in / capacity_out 未指定**（**1,500 台/h** は **参考値**として保持、今回 **未設定**）
- 単車線、merge priority 1
- 今回の **4 本 FCFS 事前 trial** では内部 36 Node を **FCFS**・clearance 1 で実測した。**将来 3,000 台 TVT-MP** は内部 36 Node を **TVT-MP 対象**（clearance 1 維持候補）とする想定であり、FCFS 事前検証は **TVT-MP でも FCFS を採用する**意味ではない（§28.11）。
- FD 容量 ≈ **0.76923 台/s**；**臨界密度** ≈ **0.04615 台/m**；1 Link **40 台**収容；臨界密度相当 ≈ **9.23 台/Link**（≈**23.08% occupancy**）

### 17.4 2.5台/timestep条件の結果（200 m / 60 km/h、T=1,200）

- run **1,400** / wait **1** / 内部 occupancy **0.277** / 外部→内部 **0.05625**
- 内部 **臨界密度以上 46 本**、**90% 以上 1 本**
- **解釈:** **入口余裕**（wait 1）、**内部Link混雑**。**入口飽和・大量 wait なし**（§28.5）。

### 17.5 3台/timestep条件の結果（T=999）

- run **1,940** / wait **1** / 内部 occupancy **0.360625** / 外部→内部 **0.208**
- 内部 **臨界密度以上 59 本**、全 Link **90% 以上 5 本**
- **解釈:** **内部Link混雑**は **2.5 台/timestep** より強い。**connector** にも混雑開始だが **wait 1** で **入口外大量待機には至らない**（§28.7）。

### 17.6 現時点の需要条件判断

- **主たる TVT-MP 候補:** 3,000 台、departure **T=0〜999**、名目 **3 台/timestep**、名目 **0.125 台/timestep・外部 OD Node**（**実配分非均等**）
- **2.5 台/timestep:** 感度分析候補として保持
- **5,000 台・T=0〜500:** 高需要ストレス条件（§16）
- **通常需要 / 準高需要 / 高需要** の呼称は **未確定**（**強い混雑**は明記）

### 17.7 完走確認結果（TMAX=5000）

- **全 3,000 台正常完走**、**abort 0**
- **最終完走 T=2,296**、最終完走 Vehicle **veh_2818**
- departure 終了 **T=999** から **1,297 timestep** で解消
- **T=4,999** で全 Link 上 Vehicle **0**
- T=999 pretrial との **vehicle_plan_sha256 完全一致:** `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`

### 17.8 実行時間（FCFS）

| trial | exec_simulation (s) |
|-------|---------------------|
| 2.5 台/timestep・200 m、T=1,200 | **3.1263249160256237** |
| 3 台/timestep、T=999 | **2.7421296659158543** |
| completion check **TMAX=5000** | **5.314151040976867** |

**FCFS は軽量**だが、これを **TVT-MP 実行時間と同一視しない**（§16.9、§27.9）。

### 17.9 設計上の重要な留保

- **departure 終了時点同士**の比較（2.5 は T=1,200、3 は T=999）。**同一絶対時刻比較ではない**。
- occupancy は **jam density 基準**。**臨界密度 ≈ 23.08% occupancy**。
- **snapshot Vehicle 数のみ**で動的交通状態を完全断定しない。
- **3 台/timestep** は **強い混雑**だが **100% Link**・**大量 wait** はない。
- **capacity_in/out へ 1,500 台/h を設定していない**。
- **FCFS 完走 T=2,296** を **TVT-MP evaluation end へそのまま採用しない**。

### 17.10 最新の確定事項

- **3 台/timestep** を **主候補**
- **全 Link 200 m、60 km/h、capacity_in/out 未指定** を **主候補**
- FCFS **最終完走 T=2,296**
- **3,000 台 TVT-MP へ自動進行しない**
- **profiling または短期 benchmark の先行判断が必要**

### 17.11 未完了事項

詳細正本 **§28.15** と整合: 3,000 台 TVT-MP 本体、短期 benchmark、profiling、正式 **evaluation end** / **internal TSIZE**、VOT、TVT-MP 出力、複数 seed 等 **未実施**。

### 17.12 最新再開地点（本節）

**本 §17 が進捗第4巻の最新再開地点である（2026-11-01）。** 詳細設計正本 **§28** を正本とする。

**再開時に最初に行うこと（3,000 台 TVT-MP 本体の作成ではない）:**

1. **§28** と本 **§17** を読む。
2. T=999 pretrial と **TMAX=5000** completion check の manifest / run_summary を確認する。
3. **TVT-MP 計算量 profile を先に行うか、短期 benchmark を先に行うか**を **利用者判断**する。

**判断材料:**

- FCFS **最終完走 T=2,296**
- T=999 時 **run 1,940 台**
- 内部 Link **59 本**が **臨界密度**以上
- 全 Link **90% 以上 5 本**
- §27 実績: **1,000 台 TVT-MP** 1,000 timestep 約 **7,620 s**；**5,000 台 TVT-MP** T=599 約 **79,685 s**

**profiling または短期 benchmark の範囲を決めるまで、3,000 台 TVT-MP 全期間 trial は作成・実行しない。**

**production 最適化、arrival tiebreaker、乱数源分離へ自動的に進まない。**

**歴史的注記（§17 執筆時点との関係）:** 上記 §17.1・§17.11 は **FCFS 需要選定完了時点**（3,000 台 **TVT-MP 本体未作成**）の記録である。**2026-11-01 後続**に 3,000 台 TVT-MP **短期 benchmark**、**T=96 profiling**、**共有直列化** production 最適化、**完全一致再検証**まで実施した。**進捗の最新正本は §19**（本 **§17** は改番・削除しない）。

---

## 18. 3,000台TVT-MP共有直列化最適化・完全一致検証と最新再開地点（2026-11-01）

**検索語:** 3,000台TVT-MP、短期benchmark、T=0〜299、profiling、T=96、World.copy、dill、pickle、直列化、共有直列化、production最適化、完全一致、CSV完全一致、816取引、3.84倍、73.98%削減、N=10、baseline horizon 30、計算時間短縮、Python可読性。

### 18.1 今回の作業範囲

- 3,000 台 **TVT-MP** を **T=0〜299** で **通常実行**（最適化前 **短期 benchmark**）
- **単一 timestep profiling**（**T=96**）
- **Candidate 共有直列化 A/B 診断**（**T=96**）
- **production 最適化**（Candidate 集合内 **dumps 1 回 / loads per Candidate**）
- **関連 test**（**250 件**成功）
- **最適化後全体再検証**（同一研究条件 + **`show_progress_deltat=600`**）
- **CSV 全内容独立比較**（scenario_name 除外）
- **production、test、script、diagnostic、出力**を **新規・変更**した
- **まだ commit・push していない**（§18.11）

### 18.2 最適化前短期benchmark

**正本:** 詳細設計 **§29.2**。

**主要条件:** §28 採用候補（3,000 台、departure T=0〜999、全 Link **200 m / 60 km/h**、capacity_in/out 未指定、内部 36 Node TVT-MP、**N=10**、baseline horizon **30**、evaluation **T=0〜299**、VOT seed **1** 等）。

**主要結果:**

- **816 取引**
- **state** end **318** / home **2,099** / run **580** / wait **3**
- **exec_simulation** **6295.571890000021 s**（**20.985239633333403 s/timestep**、約 **1 時間 45 分**）
- **T=0〜299** は **交通立ち上がり期間**（T=999 強混雑を代表しない）

### 18.3 profilingで特定した原因

**正本:** 詳細設計 **§29.5**。

- **T=96** の **1 timestep のみ** cProfile（T=0〜95 通常、T=0〜299 全体は profile しない）
- **FIFO True Candidate 17 件**（当該 timestep）
- **`World.copy()` 18 回**（Baseline 1 + Candidate 17）
- Candidate 局所状態構築 **17 回**、累積約 **118.72 s**（cProfile 尺度）
- **`dill.dumps` 累積約 124.324 s** が支配；**Candidate 仮想前進** 約 **0.198 s** は軽量
- **主因:** Candidate **ごとの全 World 重複直列化**（**ボトルネック**）

### 18.4 共有直列化A/B結果

**正本:** 詳細設計 **§29.7**。

| 指標 | 値 |
|------|-----|
| A 平均 wall-clock | **25.672572375042364 s** |
| B 平均 wall-clock | **3.2193430835031904 s** |
| 平均 speedup（A/B） | **7.9744754470549495 倍**（**T=96 Candidate 集合部分**。全体 **3.84 倍**と混同しない） |
| 結果 | **完全一致** |
| Candidate 独立 / real_W 不変 / 両 RNG 不変 | **確認済み** |
| 判定 | **`promising_for_production_design_review`** |

### 18.5 production変更

**正本:** 詳細設計 **§29.8**。

- Candidate **evaluation set** ごとに **`dill.dumps(real_W)` 1 回**（**FIFO True ≥1** のときのみ）
- FIFO True Candidate **ごとに `loads` 1 回** → **独立 local World**
- **FIFO True 0 件** / normal-not-generated / FIFO False のみ → **直列化なし**
- **global cache・World 属性 cache なし**
- 既存 **単独 `build_tvt_mp_candidate_local_state()`** は **`World.copy()` 互換**
- **baseline copy**、**TVT-MP アルゴリズム**（FIFO、N、horizon、経済、rank、RNG）は **変更なし**
- **Python 可読性:** 直列化・復元・局所状態構築を **明示的関数**で分割

### 18.6 test結果

**正本:** 詳細設計 **§29.9**。**関連 test 250 件すべて成功。**

| モジュール | passed |
|-----------|--------|
| `tests_order_control_tvt_mp_candidate_local_state.py` | 25 |
| `tests_order_control_tvt_mp_local_virtual_calculation_set.py` | 41 |
| `tests_order_control_tvt_mp_local_virtual_calculation.py` | 90 |
| `tests_order_control_tvt_mp_candidate_outlink_boundary.py` | 22 |
| `tests_order_control_tvt_mp_candidate_unbound_fcfs_transfer.py` | 28 |
| `tests_order_control_tvt_mp_candidate_virtual_time.py` | 13 |
| `tests_order_control_tvt_mp_driver.py` | 31 |
| **合計** | **250** |

### 18.7 最適化後全体再検証

**正本:** 詳細設計 **§29.10**。

| 指標 | 値 |
|------|-----|
| exec_simulation | **1637.9535257919924 s** |
| s / eval timestep | **5.459845085973308** |
| speedup vs 最適化前 | **3.8435595338127504 倍** |
| 短縮 | **4657.618364208029 s**（約 77 分 38 秒） |
| runtime reduction | **73.9824506111392%** |
| final_script_total 目安 | 約 **27 分 18 秒** |
| 816 取引 | **一致** |
| Vehicle 状態 / Link 数 / plan digest | **一致** |

### 18.8 CSV完全一致

**正本:** 詳細設計 **§29.11**。**scenario_name 列除外**の独立比較。

- `tvt_mp_transactions.csv` **816** 行 — 完全一致
- `tvt_mp_visits.csv` **1,927** 行 — 完全一致
- `tvt_mp_vehicles.csv` **877** 行 — 完全一致
- `tvt_mp_nodes.csv` **36** 行 — 完全一致
- `tvt_mp_scenario.csv` **1** 行 — 完全一致
- `vehicle_vot.csv` **3,000** 行 — 完全一致

### 18.9 現時点の受入れ判断

- **コード修正に問題なし**と判断（§29.12）
- **追加の同規模完全一致 trial** は **直ちに不要**
- **将来の別 seed・長期 trial** は **追加回帰確認**として利用可能
- **production 最適化（Candidate 集合内共有直列化のみ）を受入れる**

### 18.10 未完了事項

- **文書化後の commit・push**
- **正式な 3,000 台 TVT-MP evaluation end**
- **internal TSIZE**（長期 trial 用）
- **T=599** または **T=999** 延長 trial
- **全車完走 trial** の要否
- **複数 seed**
- **長期 trial** の **計算時間**見積り（**単純比例禁止**）
- **研究室デスクトップ**との性能比較
- **memory pressure**（shared bytes）の実行時観察
- **追加高速化**の要否（**自動進行しない**）

**研究室デスクトップ（別論点）:**

- 2 年前購入の **AMD Ryzen** 搭載 **らしい**が、**正確な CPU 型番・RAM・OS は未確認**
- 現時点では研究室へ行かないと確認できないため、作業を **中断せず Mac で継続**
- 将来、**同一 benchmark** で実機比較可能
- **今回の production 最適化**とは **別論点**

### 18.11 最新再開地点（本節）

**本 §18 が進捗第4巻の最新再開地点である（2026-11-01 後半）。** 詳細設計正本 **§29** を正本とする（§28・§17 は **歴史的記録**として維持）。

**歴史的注記（2026-11-02 追記）:** その後 **T=999 departure-end trial**、**full-run audit helper**、**audit validation**、**3,000 台 full completion 長期 trial** まで進んだ。**進捗の最新再開地点は §19**、詳細設計正本は **§30**（本 **§18.11** の当時の再開手順は **歴史記録**として残す）。

**再開時に最初に行うこと（2026-11-01 後半時点の記録）:**

1. 詳細設計 **§29** と本 **§18** を読む。
2. 今回の **変更・新規ファイル**（§29.14）と **出力 directory**（4 箇所）を確認する。
3. **文書化を含めて commit・push** する。
   - **commit 名に `document` を含める**
   - **commit と push は分ける**
   - **`diagnostics/order_control.zip` は対象外**
   - 既存の **大量未追跡 diagnostic/output** を **自動 stage しない**
4. **commit・push 後**、**正式な 3,000 台 TVT-MP** の **次の実行範囲**を **利用者判断**する。

**次の判断前に自動進行しないもの:**

- **追加 profiling**
- **production 高速化**（baseline copy 最適化等）
- **T=599 / T=999 / T=2,296** への **自動延長**

**数値の整理（混同禁止）:**

| 尺度 | speedup / 削減 |
|------|----------------|
| T=96 Candidate 集合 A/B | **≈7.97 倍**（§18.4） |
| T=0〜299 全体通常 exec | **3.8435595338127504 倍**、**73.9824506111392% 削減**（§18.7） |

**歴史的注記（§17 執筆時点との関係）:** 上記 §17.1・§17.11 は **FCFS 需要選定完了時点**（3,000 台 **TVT-MP 本体未作成**）の記録である。**2026-11-01 後続**に 3,000 台 TVT-MP **短期 benchmark**、**T=96 profiling**、**共有直列化** production 最適化、**完全一致再検証**、**T=999 departure-end trial**、**full-run audit helper**、**3,000 台 full completion 長期 trial 準備**まで実施した。**進捗の最新正本は §19**（本 **§17**・**§18** は改番・削除しない）。

---

## 19. 3,000台長期trialの監査出力準備と全車完走実行（2026-11-02）

**検索語:** 横並び表示、事後分析、監査出力、long-run trial、full-run audit helper、T=999、3,000台、departure-end、transactions 3579、1727台未完走、production監査不採用、git restore、f323820、12台audit validation、600台、nonparticipating 20%、same-inlink、actual arrival、奇数到着、全車完走、交通解消、safety cap T=5000、正式10ファイル、finalize TSIZE、AttributeError、caffeinate、console log、結果未確定。

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§30**。

**区分（混同禁止）:**

| 対象 | 状態 |
|------|------|
| **T=999 departure-end trial** | **正常完了**（**全車完走 trial ではない**） |
| **audit validation**（12 台 / 600 台 20% NP） | **完了** |
| **3,000 台 full completion + audit trial** | **実行中**、**結果未確定** |
| **production 大規模監査拡張** | **不採用・破棄済み** |
| **full-run audit helper** | **採用**（production **非変更**） |

### 19.1 完了事項

- **T=999・3,000 台 departure-end trial**を **正常完了**（`run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_1000_timestep_departure_end_trial.py`）
- **exec_simulation** 約 **6 時間 35 分**（**23697.24 s**、**23.70 s/timestep**）
- **transactions 3579**
- **T=999 時点**で **1727 台未完走**（end 1273 / run 1726 / wait 1）
- **正式出力 8 ファイル**保存
- **manifest / CSV / Node 別取引合計 / state counts / Link Vehicle 数**を **独立確認**
- **正式 CSV だけ**では **従来横並び監査を完全再現できない**ことを確認（詳細 **§30.2**）
- **production 大規模監査拡張案**を **不採用**
- 未 commit **13 ファイル・約 2112 行**を **`git restore`** で破棄、production/test を **`f323820`** へ復元（patch 退避 **`/tmp/tvt_mp_audit_overdesign_backup.patch`**）
- **`tvt_mp_full_run_audit_helper.py`** を **新規作成**（helper **py_compile**・**static validation** 通過）
- **12 台全参加** audit validation trial：**audit CSV 検証通過**
- **4 交差点・600 台・20% nonparticipating** audit validation trial：**228 取引**、**626 visit audit 行**、**FIFO violation 0**、**検証通過**
- **buyer / seller / nonparticipating** の **横並び監査**を **保存可能**（inlink、actual arrival、局所順位、Node 累積順位、passage、**G_b/R_s/P_b/C_s**）
- **same-inlink 複数 buyer/seller** の **横並び再構成**に成功（例 **T=392 northwest**、詳細 **§30.6**）
- **奇数到着**を含む **成立取引 136 件**を確認（helper **偶数丸めなし**、**§30.7**）
- **3,000 台・20% NP・全車完走・監査** 長期本番スクリプトを **新規作成**（`run_tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_trial.py`）
- 作成後 **py_compile**・**static validation** **通過**
- **finalize 前 TSIZE 参照**不具合を **修正**（finalize **前**の `verify_network_runtime` **削除のみ**）
- **修正後**も **py_compile**・**static validation** **通過**

### 19.2 現在実行中

- **3,000 台** TVT-MP
- **nonparticipating 20%**（600 / 2400、seed **3**）
- **全車完走・交通解消**まで（**safety cap T=5000**、internal TSIZE **5031**）
- **full-run audit helper** 接続
- **想定約 12 時間**（**未確定**）
- **caffeinate** 使用
- **console log** 保存

**注意:** 「**全車完走した**」「**交通解消した**」「**12 時間で終了した**」等は **未確定**のため **確定事項として書かない**。

### 19.3 未確定事項（長期 trial 完了待ち）

- 最終 **World.T**
- 最終 **actual passage timestep**
- **実行時間**（exec_simulation / script total）
- **transaction 数**
- **audit transaction / visit 行数**
- **buyer / seller / nonparticipating 監査行数**
- **same-inlink 最大値**
- **FIFO violation** 合計
- **全車完走・交通解消**の **成否**
- **safety cap T=5000 以内**で終了するか

### 19.4 再開時チェックリスト

1. **長期実行 process** が継続中か確認
2. 終了後 **console output** を確認
3. **正式 10 ファイル**の存在確認（研究 CSV 5 + audit 2 + vehicle_vot + manifest + run_summary）
4. **run_summary** と **manifest** を確認
5. **Vehicle state**、**Link 上 Vehicle**、**completion 条件**を **独立確認**
6. **transaction / visit audit 行数**を **正式 CSV** と比較
7. **buyer / seller / nonparticipating 監査行**を確認
8. **same-inlink 最大構成**を **横並び表示**
9. **奇数到着・奇数通過**を含む取引も確認
10. 結果を **詳細設計 §30** と **本 §19** へ **追記**
11. その後 **commit 対象**を整理

### 19.5 最新再開地点（本節）

**本 §19 が進捗第4巻の最新再開地点である（2026-11-02）。** 技術的正本は詳細設計 **§30**。

**§18.11**（共有直列化・T=0〜299 完全一致時点）は **歴史的再開地点**として維持する。**T=999 departure-end 結果**は **§30.1**。**audit validation 完了**は **§30.5**。**3,000 台 full completion trial** は **§30.8 / 本 §19.2**（**結果未確定**）。

**歴史的注記（§18 執筆時点との関係）:** 上記 **§18.11** は **2026-11-01 後半**（共有直列化受入れ・完全一致検証時点）の最新再開地点であった。**その後** T=999 trial、監査 helper、validation trial、長期本番スクリプトまで進んだ。**進捗の最新正本は §19**（**§18** は改番・削除しない）。

---

## 20. Schepperle・Böhm系列への第二段階初回適用完了（2026-11-02）

本§20は**先行研究調査**の進捗だけを記録する節である。**§19**は削除・変更・置換しない。

- **TVT-MP実装・長期trial側**の最新再開地点は引き続き **§19**（**結果未確定**）。
- **文献調査側**の最新再開地点は **本§20**。
- 両者は別系統の再開地点であり、混同しない。

本§20の追加を理由に、実行中の長期trialが完了したとは記録しない。

### 20.1 完了した文献調査

- Schepperle・Böhm系列の**第二段階初回適用**を完了した。
- 詳細正本：`ORDER_EXCHANGE_LITERATURE_FIRST_STAGE_SCORING_AND_POSITIONING.md` **§22**
- 方法論・ポジショニング要約：`ORDER_EXCHANGE_LITERATURE_POSITIONING_FRAMEWORK.md` **§5D**
- 第一段階採点は変更していない。
- Schepperle・Böhm系列は、**取引構造上の直接競合**として維持した。

### 20.2 ポジショニング上の主要結論

**1. 系列内の役割分担**

- ITSAはauction-based initial allocation。
- TSRはrequest順とspace-time feasibilityに基づくreservation。
- TSEは割当済みslotのvoluntary bilateral exchange。
- Free Choice・Clockedはauction側のconcurrency拡張。
- TVT-MPとの直接比較の中核は**TSE**。

**2. Initial slotとfairness**

- TSEは割当済みslotを交換前entitlementとして使う。
- Initial-allocation mechanismの具体的方法は**未確認**。
- TSRで確認できたのはreservation確定の**処理規則**であり、その規則の公平性・正当性ではない。
- Initial slotの公平性は、TSEを公平な制度として強く評価する場合の**条件付き解釈前提**。

**3. 非参加者保護**

- TSEは自分のslotを交換しない自由を保護する。
- 他者間exchangeによるactual crossing time、traffic position、utilityへの影響は確認できない。
- TVT-MPのnonparticipating Visitに対する**直接的baseline順位後退防止**とは同一ではない。

**4. Network適用性**

- TSR・TSE系列はsingle intersection中心。
- Spillback、downstream blocking、outlink入口空間、隣接交差点queueは研究対象外。
- Single-intersection局所reservationとしての価値は認める。
- 現実的な過飽和networkへの一般化は支持しない。
- 取引構造では**直接競合**だが、network統合軸ではTVT-MPと**十分に分離可能**。

**5. 構造的前提**

特筆する前提：Linear valuation、Moneyの同一marginal utility、Initial time-slot entitlementの公平性・実行可能性、Voluntary participationがfairnessを十分保護すること。

暫定評価：系列全体の構造的前提依存性は**Medium候補**。Network applicabilityへ拡張する場合は**High候補**（Low・Medium・Highの正式閾値は未確定）。Overall satisfaction、fairness、network applicabilityの**強い一般化は割り引く**。

### 20.3 TVT-MPとの差別化

共通するため**単独独自貢献としない**もの：Crossing priority・time slotの取引、交換前allocationをbaseline entitlementとして使うこと、Waiting-time reduction valuation、Slot譲渡側への金銭移転、Voluntary participation、Exchange拒否権、No-overtaking、Physically feasible allocation。

**組合せとして**評価する有力な差別化候補：Baseline順位からmulti-party候補を形成、非参加Visitの直接的baseline順位後退を防止、各sellerの必要補償額 `R_s` を個別充足、Seller必要補償総額だけをbuyer側へ配分、順位sellerとactual payeeを分離、順位変化と時間結果を分離、Candidate predictionとactual passageを比較、Nonparticipatingへのactual外部効果を記録、複数Node・OD・右左折・単車線FIFO・下流容量制約を統合。未実装・未評価のTVT-MP機能を確定済み成果として書かない。

### 20.4 未確認理由と次の文献対象

- **TSEの価格・交渉手順：** 本文の該当箇所を未取得
- **TSEのbudget balance、individual rationality、strategy-proofness：** 本文の該当箇所を未取得
- **TSE simulationの詳細parameter・効果量：** 本文の該当箇所を未取得
- **2009年overview chapter全文：** 資料未入手
- **Multiple intersections、spillback、downstream blocking、multiple OD、route choice：** 研究対象外
- **非参加者のactual traffic outcome保護：** 本文の該当箇所を未取得

**次の文献対象：** **PEXIC系列**

**次の文献作業：** PEXICの正式書誌と全文資料を固定する。制度構造と中核結論を5〜6点へ絞って把握する。TVT-MPとの本質的な共通点と差異を特定する。ポジショニングに効く構造的前提だけを抽出する。追加調査では、既述内容を再掲せず、新たに判明した事項だけを報告する。

TSE完全PDFまたは2009年overview chapter全文を別経路で入手した場合は、価格式、budget balance、IR、誘因性質、非参加者外部効果を再確認する。この再確認可能性を理由に、PEXIC調査の開始を自動的に延期しない。

### 20.5 TVT-MP実装・長期trial側との分離

- 本§20は文献調査の進捗だけを記録する。
- TVT-MP実装仕様を変更しない。詳細設計正本 **§30** を変更しない。
- **§19** の長期trial**実行中**という状態を変更しない。長期trialの**結果は未確定**。
- 全車完走、交通解消、実行時間、transaction数、audit行数等を**確定事項として記録しない**。
- 実装・長期trial側へ戻る場合は **§19** と詳細設計 **§30** を読む。
- 文献調査を再開する場合は **本§20**、詳細正本 **§22**、FRAMEWORK **§5D** を読む。
