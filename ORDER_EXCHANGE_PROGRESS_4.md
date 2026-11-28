# ORDER_EXCHANGE_PROGRESS_4

本ファイルは TVT-MP 研究の進捗記録 **第4巻** である。

- 第3巻は `ORDER_EXCHANGE_PROGRESS_3.md` 末尾の「進捗第3巻終了・第4巻への移行（2026-10-26）」で終了した
- 第3巻以前の記録は履歴として維持する
- 第3巻以前の「最新再開地点」は当時の記録であり、現在地として自動的に使用しない
- 今後の最新進捗と最新再開地点は本第4巻へ記録する
- 技術的詳細の正本は、各時点で指定された詳細設計メモを参照する
- 第4巻開始時点の技術的正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` の **§23** である
- **2026-11-02 追記:** 監査出力・full-run audit helper・3,000 台長期 trial の技術的正本は詳細設計 **§30**。進捗の最新再開地点は **§19**（§23・§18 等は **歴史記録**として維持）
- **2026-11-03 最新参照:** 3,000 台 full-completion trial の **確定結果**、**総合評価指標**、および **次の実装・高速化課題**について、TVT-MP 実装・評価側の最新再開地点は **§21**、詳細技術正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31**。
- **§19・§30** は、長期 trial の **実行前・実行中** および **監査準備**の **歴史的記録**として維持する。
- **文献調査側**の最新再開地点は **§20**。
- **2026-11-04 追記（network-wide Route-Conditional production 完了）:** **4 方式共通評価**の **Route-Conditional** **production 実装・専用 test・独立検証**の **歴史的再開地点**は **§21.9.12**。**詳細技術正本**は **§31.18.23**。**§31.18.22** と **§21.9.11** は **production 実装前**として **歴史的に有効**。
- **2026-11-06 追記（主指標 AWT・AWWT・OD Reference 設計確定）:** **FCFS 3,000 台 Route-Conditional 実算**、**320 OD 検証**、**実装前の指標整理・OD Reference 設計**の **歴史的再開地点**は **§21.9.13**。**詳細技術正本**は **§31.18.24**（**実装前設計**）。**削除しない**。
- **2026-11-07 追記（OD 基準 AWT・AWWT production・FCFS 正式算出・route_pref 原典）:** **network-wide** の **OD Reference・主指標 AWT・AWWT・迂回・恒等関係**の **production 実装完了**の **歴史的再開地点**は **§21.9.14**。**詳細技術正本**は **§31.18.25**。**§31.18.23** / **§21.9.12** は **Route-Conditional のみ**。**§31.18.24** / **§21.9.13** は **実装前設計・320 OD 事前検証**。**旧 ACWT・ACWWT** は **Route-Conditional 指標の歴史的呼称**として **§31.18.23** 等に **残す**。
- **2026-11-08 追記（baseline・Candidate 共通 snapshot 最適化・正式受入れ）:** **TVT-MP performance・production snapshot 経路**の **歴史的再開地点**は **§21.9.15**。**詳細技術正本**は **§31.19**（**§29** は **Candidate 集合内共有直列化**の **歴史正本**。**§31.15** は **~18 h 未解決時点**の **歴史**）。
- **2026-11-09 追記（signalized UXsim 3,000 台 OD 基準 AWT・AWWT 正式算出・3 方式暫定比較）:** **signalized UXsim 主指標正式結果**・**FCFS・TVT-MP との暫定比較**・**次の TVT-MP VOT 五分位・取引経験別分解**の **最新再開地点**は **§21.9.17**。**詳細技術正本**は **§31.21**。**TVT-MP 正式結果・FCFS 比較**は **§31.20** / **§21.9.16**（**歴史**）。**共通評価関数・FCFS 正式値**は **§31.18.25**。
- **2026-11-09 追記（TVT-MP 3,000 台 OD 基準 AWT・AWWT 正式算出・FCFS 比較）:** **TVT-MP 主指標正式結果**・**FCFS 比較**の **歴史的再開地点**は **§21.9.16**。**詳細技術正本**は **§31.20**。**共通評価関数・FCFS 正式値**は **§31.18.25**。
- **2026-11-12 追記（clearance・signal候補再評価開始）:** **buyerのみ悪化17台**・**FCFS clearance=0**・**signalized全赤なし**の **歴史的再開地点**は **§21.9.18**。**詳細技術正本**は **§31.22**。当時は **TVT-MP clearance=0未実行**。**削除しない。**
- **2026-11-14 最新参照:** TVT-MP **clearance=0正式分析完了**、participating **VOT・role・Q5・Top 1%**、buyer局所効果、nonparticipating 600台、**30反復**の日々変動目的、**最初の経路分岐**乱数監査の **最新再開地点**は **§21.9.19**。**詳細正本**は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32**。**次作業**は **読取り専用原典監査**。**§21.9.18** / **§31.22** は実行前の **歴史**。
- **2026-11-14 追記（route-choice乱数原典監査完了）:** 全体判定 **NOT_GUARANTEED_BY_CURRENT_CODE**、仮想World **NO_DIRECT_VIRTUAL_TO_REAL_RNG_CONTAMINATION_FOUND**、keyed randomization **暫定分類2**、**4方式共通seed/RNG基盤**の **最新再開地点**は **§21.9.20**。**詳細正本**は **§32.17〜§32.19**。**次の利用者判断**は、production変更なしの最小診断を先に行うか、共通基盤の詳細設計を先に行うか。**§21.9.19** は原典監査前の **歴史**。
- **2026-11-14 追記（route-choice RNG診断の第一層・第二層反証完了）:** production変更なしの **route-choice RNG診断**を実装し、第一層と第二層の不変性反証が完了した。**最新再開地点**は **§21.9.21**。**詳細正本**は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.20**。**§21.9.20** と **§32.17〜§32.19** は診断実装前の **歴史**。**production seed/RNG改修は未着手**。**seed改善は未完成**。keyed randomization は **暫定分類2・未採用・未実装**。**次作業**は、限定した 3,000台 FCFS対TVT-MP route-choice RNG監査の設計。

**検索語:** ORDER_EXCHANGE_PROGRESS_4、進捗第4巻、TVT-MP、横並び表示、事後分析、監査出力、full-run audit helper、nonparticipating 20％、全車完走、交通解消、3,000台、T=999、departure-end、4交差点、T=382、初回Actual arrival、Actual arrival上書き、Baseline arrival一致、first divergenceなし、T=402、一時skip、clearance、C順位183、Actual通過順位177、selected=False、baseline fallback、leading nonparticipating、順位確定源、完了、最新再開地点、Git対象、commit、push、TVT-MP clearance=0、transaction 2421、Visit 5457、AWT 21.676、AWWT 20.427812923323355、Top 1%、buyer局所効果、nonparticipating 600台、30反復、最初の経路分岐、keyed randomization、暫定分類2、原典監査、§21.9.19、§32、NOT_GUARANTEED_BY_CURRENT_CODE、NO_DIRECT_VIRTUAL_TO_REAL_RNG_CONTAMINATION_FOUND、4方式共通seed/RNG基盤、§21.9.20、§32.17。

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

**2026-11-03 最新参照（歴史的注記）:** 上記の **§19・結果未確定** という記述は、**先行研究調査 §20 を作成した時点**の **歴史的状態**である。その後、**3,000 台 full-completion trial** は **正常終了**し、**確定結果**を記録した。**TVT-MP 実装・評価側**の最新再開地点は **§21**。**詳細技術正本**は詳細設計 **§31**。**文献調査側**の最新再開地点は引き続き **§20**。**§20 を §21 で置換しない**。

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

**2026-11-03 最新参照:** 本 §20.5 の「長期 trial **実行中**」「**結果未確定**」「**§19・§30 を読む**」という記述は、**文献調査作業時点**の **歴史的状態**である。**長期 trial の確定結果**、**総合評価指標**、および **次の実装・高速化課題**は、進捗 **§21** と詳細設計 **§31** を参照する。**文献調査**の再開先は引き続き **本 §20**、詳細文献正本 **§22**、FRAMEWORK **§5D**。**TVT-MP 実装・評価**の再開先は **§21・§31**。**両系統を混同しない**。

---

## 21. 3,000台full-completion結果、総合評価指標設計、および次の実装・高速化課題（2026-11-03）

本§21は **TVT-MP 実装・評価**側の進捗を記録する。**§20** は Schepperle・Böhm 系列の **文献調査**進捗として **削除・変更・置換しない**。文献調査側の最新再開地点は **§20**、TVT-MP 実装・評価側の最新再開地点は **本§21**。

### 21.0 検索語と正本

**検索語:** 3,000台、full completion、traffic clearance、20% nonparticipating、AWT、AWWT、ACWT、ACWWT、Vehicle当たり累積waiting time、平均Visit数、総旅行時間、総遅延、最終Vehicle完走時刻、FCFS比較、Buyer、Seller、Nonparticipating、Seller unsatisfied、18時間、pickle.load、GC、高速化、評価指標算出、makespan、conservative makespan、詳細設計§31。

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31**

### 21.1 完了事項

**長期 trial（確定）:**

| 項目 | 値 |
|------|-----|
| Vehicle | **3000** 台（participating **2400** / nonparticipating **600**） |
| departure | **T=0〜999** |
| 終了 | **全車完走・交通解消** |
| final **World.T** | **2035** |
| evaluation end timestep | **2034** |
| Vehicle state | end **3000** / run **0** / wait **0** / home **0** |
| transaction count | **4298** |
| transaction audit rows | **4298** |
| visit audit rows | **11871** |
| buyer / seller / nonparticipating audit rows | **5013 / 6170 / 688** |
| actual arrival rows | **11871** |
| same-inlink max party / buyer / seller / nonparticipating | **3 / 3 / 3 / 2** |
| FIFO violation total | **0** |
| audit CSV validation | **passed** |
| exec_simulation | **65093.892005 s** |
| final script total | **65116.178632 s** |
| wall-clock | **約 18 時間 5 分** |
| 正式出力 | **10 ファイル** |

**scenario / スクリプト:** 詳細設計 **§31.1**（`run_tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_trial.py`、output directory 名は同節）。

**FCFS 比較（同条件性）:**

- **同一 Vehicle plan SHA-256**、**同じ 3000 台**、departure **T=0〜999**、Link **200 m**、**60 km/h**、jam density **0.2**
- FCFS **last_vehicle_completion_timestep = 2296**
- FCFS **World.T=5000** は **固定観測終了値**であり **比較値ではない**
- TVT-MP は **遅くとも T=2033** までに **全車完走・交通解消**
- TVT-MP の **exact な最終 Vehicle 完走 timestep** は **未保存**
- **保守的**に **少なくとも 263 timestep**、**約 11.45% 短い makespan**（詳細設計 **§31.2**）
- **最終 departure 後だけ**を比較した **20.3% 短縮**という **旧解釈は不採用**
- **makespan** は **補助指標**であり、**最終総合評価を単独で決めない**

**メモ:**

- 詳細設計 **§31** を **追加済み**
- **Terminal** で **§31.1〜§31.17** を **独立通読済み**
- **修正必須の誤りなし**

**区分:** **§19**・**§20.5** の「長期 trial **結果未確定**」は **実行前・実行中の歴史記録**。**確定数値**は **本§21** および詳細設計 **§31** を参照（**§19** は改番・削除しない）。

### 21.2 総合評価指標の確定事項

**最新参照（2026-11-04、不採用注記）:** 本節の **Visit 単位 AWT・AWWT** と **平均 Visit 数** による **ACWT・ACWWT** は、**定義検討過程の歴史的記録**である。**network 全体の最新定義・再開先**は **§21.9** および詳細設計 **§31.18**。本節の Visit 数恒等式を **最新定義として読まない**。

**中核指標:**

1. Visit 単位 **AWT**
2. Visit 単位 **AWWT**
3. **平均 Visit 数**
4. **ACWT**
5. **ACWWT**
6. **平均旅行時間**
7. **総旅行時間**
8. **平均遅延**
9. **総遅延**
10. **最終 Vehicle 完走時刻**
11. **全車完走**
12. **交通解消**

**ACWT:** Average Cumulative Waiting Time (per Vehicle) — Vehicle 当たり平均累積 waiting time

**ACWWT:** Average Cumulative Weighted Waiting Time (per Vehicle) — Vehicle 当たり平均累積 weighted waiting time

**重要:**

- **ACWT = Visit 単位 AWT × 平均 Visit 数**
- **ACWWT = Visit 単位 AWWT × 平均 Visit 数**
- これは **線形近似ではなく**、**同じ Visit 集合と分母**を用いる限り **恒等式**
- FCFS 基準の **補正値**ではなく **各方式の実値**を **主表**へ示す
- **名称**は **有力候補**であり、**既存用語との重複調査前**に **最終確定しない**
- **数理定義**は **固定可能**

**方式比較行:** signalized UXsim、FCFS、BATCH、TVT-MP

**当面保留（最初から過剰実装しない）:** Node 別 AWT・AWWT、時間帯別 AWT・AWWT、詳細空間分布、時系列 throughput、VOT 階層別詳細分析

（定義・主表・waiting time: 詳細設計 **§31.3〜§31.10**）

### 21.3 Role別評価

**Buyer:** FCFS より **AWWT** が **大幅に改善**することを **期待**。**集計単位は未確定**。

**Seller:** **AWT・AWWT** 悪化を **できるだけ小さく**。**Seller unsatisfied 率**を **必須**。**新規 NetLoss・NetBenefit** 等の **補償込み独自式は導入しない**。**既存 Satisfied / Unsatisfied 事後評価**を使う。**集計単位は未確定**。

**Nonparticipating:** **出発から trip end まで固定 Vehicle 属性**。**600 台**を **Vehicle 単位**で評価。FCFS の **同一 Vehicle 集合**と比較。**ACWT・ACWWT** が **不変または改善**することを **期待**。**旅行時間・遅延**も比較。**改善・不変・悪化 Vehicle 数**、**最大悪化量**を確認する **候補**。

**Buyer・Seller 未確定集計単位:** **Role-Visit 方式** / **Role 経験 Vehicle 方式** / **両方式併記** — **小規模 output** で **試算してから決定**。**コード実装時に無断で一方式へ固定しない**（詳細設計 **§31.11〜§31.12**）。

### 21.4 旅行時間・遅延・計測範囲

**最新参照（2026-11-04）:** Visit 計測漏れを理由に ACWT を補完指標扱いする本節の記述は、**Visit 数ベース定義時点の歴史的記録**である。**network-wide ACWT・ACWWT** の最新定義は **§21.9** および詳細設計 **§31.18**（**CW_z = TT_z − T_min,z**）。最終 OD Link を人工 Visit へ追加しない方針は維持する。

- **inlink** 上の **queue**、**congestion**、**spillback** は **waiting time** へ **反映される**
- **最後の内部交差点後**の **最終 OD Link** は **別 Visit を形成しない**場合がある
- **ACWT・ACWWT だけ**で **trip 全体**を **完全には表さない**
- **旅行時間**は **departure から trip end まで直接計測**
- **総遅延**は **実旅行時間 − 実走行経路の自由走行時間**
- **200 m、60 km/h** では **1 Link 自由走行時間は 12 秒**
- **12 × Link 数 + 累積 waiting time** は **概念的整合確認に限る** — **正式な旅行時間算定式にしない**
- **最終 OD Link** を **人工的な order-control Visit** へ **追加しない**

（詳細: 詳細設計 **§31.9・§31.13**）

### 21.5 次の課題1: 評価指標算出基盤

**最新参照（2026-11-04）:** **最新実装方針**は **§21.9** および詳細設計 **§31.18**。**Visit 単位指標を先に実装しない**。**`travel_time`**、**`traveled_route`**、自由流経路時間、ACWT、ACWWT を **先に検証**する。下記の Visit / earliest arrival 調査リストは **検討過程の歴史的記録**。

**実装前**に **読取り専用**で確認する項目:

- **departure** / **trip end**
- **Link 通過履歴** / **route 履歴**
- **earliest arrival** / **actual intersection entry**
- **外部 OD Link**
- **revisit Visit ID**
- **最終 Vehicle 完走 timestep**
- FCFS、BATCH、TVT-MP、signalized UXsim で **共通利用できる field**

**注意:**

- UXsim 上の **actual intersection entry** を **actual node arrival** または **actual passage** の **どちらへ対応させるか**は **未確定** — **原典確認後**に決める
- **passage から arrival を逆算しない**
- **trip end** や **実経路**を **推測しない**
- **定義確認前**に **production** を **変更しない**

（必須出力・禁止: 詳細設計 **§31.14**）

### 21.6 次の課題2: 約18時間実行の高速化

**確定:**

- **exec_simulation 約 18 時間 5 分**（§21.1）
- **混雑中盤**で **非線形**に重い
- **macOS sample** では **`pickle.load`** と **Python GC** が **主要負荷**
- process は **停止・sleep・deadlock ではなかった**
- **console log** が **約 5 時間更新されない区間**があった
- **正規の共有直列化復元の多数回実行**か、**想定外反復**かは **未判定**
- **py-spy** による **Python 関数 stack** 取得は **失敗**

**高速化調査方針:**

- **推測**で **production** を **変更しない**
- **再現可能な短縮 trial** または **限定 instrumentation** を **先に**作る
- **計測候補:** pickle 復元 **回数・bytes・時間**、GC **回数・時間**、decision timestep 別 **Candidate 数**、Candidate **World 復元数**、**living Vehicle 数**、**serialized World size**
- **原因確認後**に **のみ** **最適化**を設計
- **最適化前後**で **取引結果・順位・passage・RNG・Vehicle state** の **完全一致**を確認
- **原因不明のまま** **長期 trial** を **再実行しない**

（詳細: 詳細設計 **§31.15**）

### 21.7 次の再開順序

**最新参照（2026-11-04）:** **最新再開順序**は **§21.9**（最初に **単車両・無交通検証**）。下記 1〜12 は **§21 初稿時点**の順序であり、network 定義訂正後の再開先としては **§21.9** および詳細設計 **§31.18.11** を優先する。

1. **本§21** の記録
2. **Terminal** による **独立確認**
3. **評価指標**に必要な **既存 field・履歴**の **読取り専用調査**
4. **ACWT・ACWWT・旅行時間・遅延・最終完走時刻**の **算出設計**
5. **Buyer・Seller 集計単位**を **小規模 output** で **試算**
6. **評価算出コード**を **最小実装**
7. **4 方式**の **共通定義**を検証
8. **高速化用**の **短縮再現 trial** または **限定 instrumentation** 設計
9. **pickle・GC・Candidate 反復**を **計測**
10. **原因確定後**に **のみ** **最適化**
11. **小規模完全一致検証**
12. **必要時のみ** **長期 trial 再実行**

（詳細設計 **§31.16** と整合）

### 21.8 最新再開地点

- **TVT-MP 実装・評価側**の最新再開地点は **本§21**
- **詳細設計正本**は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31**（監査・長期 trial 準備の **§30** は **歴史・準備記録**として維持）
- **文献調査側**の最新再開地点は **§20**（**本§21 で置換しない**）
- **§19** は **長期 trial 実行前・実行中**の **歴史的再開地点**として **維持**（**確定結果**は **§21**・**§31** を参照）
- **長期 trial の確定結果**は **本§21** および **詳細設計 §31** を参照

**2026-11-04 追記:** **TVT-MP 実装・評価側**の最新再開地点は **§21.9**。**詳細設計正本**は **§31.18**。**§31.4〜§31.10** および **§21.2** 等の **Visit 数ベース定義**は **検討過程の歴史的記録**であり、**network-wide ACWT・ACWWT の最新定義として読まない**。

**2026-11-04 追記（reference replay 検証完了）:** **実装・評価側**の最新再開地点は **§21.9.1**。**詳細正本**は **§31.18.12**（**T_{\min,z}** = **reference replay**）。

**2026-11-04 追記（route signature 属性感度検証完了）:** **実装・評価側**の最新再開地点は **§21.9.2**。**詳細正本**は **§31.18.13**。

**2026-11-04 追記（物理識別値・float 安全性検証完了）:** **実装・評価側**の最新再開地点は **§21.9.3**。**詳細正本**は **§31.18.14**。

**2026-11-04 追記（実装前設計 1/4 完了）:** **最新再開地点**は **§21.9.4**。**詳細正本**は **§31.18.15**。**実装前設計**は **1/4 完了**、**残り 3 つ**。

**2026-11-04 追記（実装前設計 2/4 完了）:** **最新再開地点**は **§21.9.5**。**詳細正本**は **§31.18.16**。**実装前設計**は **2/4 完了**、**残り 2 つ**。

**2026-11-04 追記（実装前設計 3/4 完了）:** **最新再開地点**は **§21.9.6**。**詳細正本**は **§31.18.17**。**実装前設計**は **3/4 完了**、**残り 1 つ**。

**2026-11-04 追記（実装前設計 4/4 完了）:** **最新再開地点**は **§21.9.7**。**詳細正本**は **§31.18.18**。**実装前設計 4/4 すべて完了**。**production 実装**は **未着手**。

**2026-11-04 追記（4 方式共通評価の実装場所等の調査完了）:** **最新再開地点**は **§21.9.8**。**詳細正本**は **§31.18.19**。**調査 1/3〜3/3 完了**。**4 方式共通評価**である。**production 実装未着手**。

**2026-11-04 追記（production 実装前 1/3 完了）:** **最新再開地点**は **§21.9.9**。**詳細正本**は **§31.18.20**。**production 実装開始まで残り 2 工程**。**production 未実装**。

**2026-11-04 追記（production 実装前追加確認 4/4 完了）:** **最新再開地点**は **§21.9.11**。**詳細正本**は **§31.18.22**。**production 実装前の追加確認は残件 0**。**当時は production 未実装**（**現行**は **§21.9.12**）。

**2026-11-04 追記（network-wide ACWT・ACWWT production module・専用 test 実装・独立検証完了）:** **最新再開地点**は **§21.9.12**。**詳細正本**は **§31.18.23**。

### 21.9 ACWT・ACWWTの方式共通network定義への訂正

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18**

**確定:**

- **order-control Visit** は TVT-MP・BATCH 等の **内部概念**
- **external Node**、途中の **external Node**、**最終 OD Link**、**order-control 対象外 Node**、**signalized UXsim** 等を **網羅しない**
- **Visit 数**を **network 全体 ACWT・ACWWT 算出に使わない**
- **平均 Visit 数**を **経路長や自由流時間へ使わない**
- **ACWT** は **`Vehicle.travel_time`** と **`Vehicle.traveled_route()`** から計算する
- **T_min,z = Σ length/u** を候補とする
- **CW_z = TT_z − T_min,z**
- **ACWT = average(CW_z)**
- **ACWWT = average(true VOT_z × CW_z)**
- **ACWT** は **active delay を含む平均遅延**
- **ACWT** は **ACWWT の前段となる基礎時間量**
- **ACWWT が最重要指標**
- **全方式混在 network** にも **共通適用**する
- **Nonparticipating** は **固定 Vehicle 集合**として比較
- **Buyer・Seller 評価**は **network-wide ACWT・ACWWT と分離**

**原典確認（`Node._transfer_one_vehicle_between_links()`）:**

- Node transfer は **同一 `W.T`** で inlink から outlink へ移る
- **`link_arrival_time` も同じ `W.T`**
- **`move_remain`** を outlink へ引き継ぐ
- **Node に固定通過時間を設定していない**
- **ただし数値的一致**は **単車両・無交通 trial** で **実作動確認が必要**（未完了）

**次の作業:**

1. **単車両・無交通・複数 Link** の最小 trial（**`departure_time`**、**最初の Link 進入時刻**、**起点流入待ち**、**`travel_time`**、**Σ length/u**、**trip end 時刻**、**off-by-one** を確認）
2. **`travel_time` と Σ length/u** の一致確認
3. **external Node 中継**と **最終 OD Link** 確認
4. **off-by-one** 確認（起点・Link 境界・trip end を含む）
5. 方式共通の **ACWT・ACWWT 算出設計**
6. **最小実装**
7. その後に **高速化調査**

**最小 trial で特に確認すること:**

- **起点での network 進入待ち**が **`travel_time`** と **`CW_z`** へ **含まれる**こと
- **`departure_time`** と **最初の Link 進入時刻**を **同一視せず**、**実データ**で確認する

**最新注記（2026-11-04）:** **単車両・無交通検証は完了**。**最新結果**は **§21.9.1**。**下記 1〜7** は **検証前の再開順序**（**歴史的記録**）。**今後**は **§21.9.1** の **再開順序**を **優先**する。

#### 21.9.1 単車両・無交通reference replay検証完了

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`

**実施:**

- **production**、**tests** は **未変更**
- **CASE 1〜5** を **実行**、**全ケース合格**
- **output file なし**、**console 検証**

**不採用（記録）:**

- **Σ(length/u) 単独**は **CASE 1〜3** で **UXsim 最短旅行時間と不一致**（例: CASE 1 で **TT=13**、**Σ=12**）
- **1 + Σ(length/u)** は **CASE 4** で **反証**（**TT=42**、**1+Σ=43**）
- **Node 固定通過時間**が **原因ではない**
- **UXsim 離散処理**、**Link 進入 timestep 内移動**、**move_remain**、**trip-end 境界**を **解析式だけ**で **完全再現しない**

**正式 T_{\min,z}:**

- **同一実走行経路**の **無交通 reference replay** における **`Vehicle.travel_time`**
- **CW_z = TT_z − replay T_{\min,z}**

**CASE 1〜5（確定）:**

| CASE | Σ(length/u) | replay T_{\min,z} | TT_z | CW_z |
|------|-------------|-------------------|------|------|
| 1 | 12 s | 13 s | 13 s | 0 s |
| 2 | 36 s | 37 s | 37 s | 0 s |
| 3 | 36 s | 37 s | 37 s | 0 s |
| 4 | 42 s | 42 s | 42 s | 0 s |
| 5 | 12 s | 13 s | 17 s | **4 s**（**起点流入待ち 4 s** が **CW_z** へ **含まれる**） |

**その他確認:**

- **external 中継 Node** と **最終 OD Link** を **`traveled_route()`** が **保持**（CASE 3）

**指標:**

\[
\text{ACWT} = \frac{1}{N} \sum_z \text{CW}_z,\quad
\text{ACWWT} = \frac{1}{N} \sum_z C_z \text{CW}_z
\]

- **ACWWT** が **最重要指標**
- **route signature** 単位で **reference 結果**を **共有**する方針（**cache 未実装**、script は **memory 表示のみ**）
- **production 実装**は **未着手**

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.12**

**最新注記（2026-11-04）:** **route signature 候補属性**の **感度検証**は **完了**（**§21.9.2**、**§31.18.13**）。**下記 1〜11** は **感度検証前**の **再開順序**（**歴史的記録**）。**今後**は **§21.9.2** の **再開順序**を **優先**する。

**次の再開順序:**

1. **route signature** に必要な **属性の確定**
2. **reference replay helper** 設計
3. **memory cache** 設計
4. **Vehicle 別 CW_z**
5. **ACWT**
6. **ACWWT**
7. **Nonparticipating 固定 600 台**
8. **4 方式共通検証**（FCFS、BATCH、TVT-MP、signalized UXsim）
9. **小規模 manual 一致確認**
10. **3,000 台 output** 適用
11. **その後**に **高速化調査**

#### 21.9.2 Reference replay route signature属性感度検証完了

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`

**実施:**

- **CASE 6A〜6E-2** を **追加実行**、**全ケース合格**
- **CASE 1〜5** も **再合格**（**All cases passed**）
- **production**、**tests**、**当該 script 以外**は **未変更**
- **cache 未実装**、**console 検証**、**file 出力なし**

**感度結果（要約）:**

- **jam_density:** **非拘束 capacity** 条件では **物理 T_{\min,z} へ影響なし**（**6A**、replay **37 s**）
- **number_of_lanes:** **leader なし・非拘束 capacity** では **影響なし**（**6B**、replay **37 s**）
- **Link 名:** **物理影響なし**（**6C**）；**監査・debug・cache 衝突診断**には **有用**
- **DELTAT:** **必須**（**6D**、actual/reference **36 s**、**DELTAT=1 診断 reference 37 s**）
- **DELTAN:** **DELTAT 固定**・**非拘束 capacity** では **影響なし**（**6E-2**、**37 s**）；**6E-1** は **DELTAT も変化**するため **DELTAN 単独効果として読まない**
- **本研究**では **DELTAN = 1** を **World 前提条件**として **維持**（**reference** も **DELTAN = 1**）

**reference World 待ち要因除外（感度 CASE 共通方針）:**

- **capacity_in / out = 1000000.0**（**NON_BINDING_CAPACITY**）を **設定する CASE**
- **signal・order-control・Node flow_capacity・user_function なし**
- **Vehicle 1 台**、**route 固定**

**現時点の物理 cache key 候補:** **DELTAT** + **(length, free_flow_speed) の Link 順序列**（**Link 名は物理 key に含めない**）。**詳細**は **§31.18.13.10**。

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.13**

**最新注記（2026-11-04）:** **float key**（**物理識別値**）の **検証**は **完了**（**§21.9.3**、**§31.18.14**）。**下記 1〜15** は **float 検証前**の **再開順序**（**歴史的記録**）。**今後**は **§21.9.3** の **再開順序**を **優先**する。

**次の再開順序:**

1. **float key**（**丸め・正規化**）
2. **Link 名 audit identity**
3. **DELTAN = 1 validation**
4. **reference 標準条件**
5. **cache 設計**（**key / value / lifecycle**）
6. **replay helper 設計**
7. **cache hit 小規模検証**
8. **CW_z**
9. **ACWT**
10. **ACWWT**
11. **Nonparticipating 固定 600 台**
12. **4 方式**（FCFS、BATCH、TVT-MP、signalized UXsim）
13. **manual 一致**
14. **3,000 台 output**
15. **高速化調査**

#### 21.9.3 同一走行条件の物理識別値とfloat安全性検証完了

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`

**実施:**

- **CASE 7A〜7G** を **追加実行**
- **CASE 1〜6** も **再合格**
- **All cases passed**
- **production**、**tests**、**当該 script 以外**は **未変更**
- **永続保存形式**は **未確定**、**production 実装**は **未着手**

**結果（要約）:**

- **同じ数値** → **同じ物理識別値**（**7A**）
- **Link 名だけ違う** → **物理識別値は同じ**、**audit identity は異なる**（**7B**）
- **Link 順序が違う** → **別**（**7C**）
- **DELTAT が違う** → **別**（**7D**）
- **length 微小差** → **別**（**7E**；**round(10)** は **診断のみ**）
- **speed 差**が **同じ Python float** に **吸収** → **同じ**（**7F**）
- **物理 key** は **`link.u`**（**7G**）
- **`round` しない**
- **同一評価処理内 memory 辞書 key 候補**

**正式候補:**

```python
(
    float(W.DELTAT),
    tuple(
        (
            float(link.length),
            float(link.u),
        )
        for link in actual_route_links
    ),
)
```

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.14**

**最新注記（2026-11-04）:** **Link 名 audit identity** の **設計**は **完了**（**§21.9.4**、**§31.18.15**）。**下記 1〜17** は **1/4 設計前**の **再開順序**（**歴史的記録**）。**今後**は **§21.9.4** を **優先**する。**次**は **2/4 DELTAN=1 validation**。

**次の再開順序:**

1. **Link 名 audit identity**
2. **DELTAN=1 validation**
3. **reference 標準条件**
4. **共有辞書**の **所有者・存続範囲**
5. **保存値**
6. **軽量 counter**
7. **failure 診断**
8. **replay helper**
9. **重複経路** **小規模検証**
10. **CW_z**
11. **ACWT**
12. **ACWWT**
13. **Nonparticipating**
14. **4 方式**
15. **manual 一致**
16. **3,000 台**
17. **高速化**

#### 21.9.4 実装前設計1/4: Link名audit identity設計完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.15**

**確定（設計のみ。production 未実装）:**

- **physical_route_key** と **route_audit_identity** を **分離**する
- **Link 名列**は **実走行順**を維持した **tuple**（**`str(link.name)`**、**`traveled_route()`** を正本）
- **Link 名**を **物理識別値**へ **含めない**
- **同じ物理識別値**に **複数の Link 名列**を **保持**する
- **最初の観測順序**を **維持**する
- **完全一致**する Link 名列は **重複登録しない**
- **Link 名列が違うだけ**では **reference replay** を **重複実行しない**
- **Vehicle ごと**に **物理識別値**と **Link 名列**を **取得できる**設計とする
- **全 Vehicle 名**の保持方法、**counter**、**failure の最終例外**は **今回決めない**

**実装前設計の進捗:**

- **1/4 完了:** Link 名 audit identity（**本節**）
- **2/4 未着手:** **DELTAN=1 validation**（**次**）
- **3/4 未着手:** reference World 標準条件
- **4/4 未着手:** 共有の **所有者・存続範囲・保存内容・確認記録**

**最新再開地点:** **§21.9.4**。**詳細正本**は **§31.18.15**。**次**は **2/4**。

**最新注記（2026-11-04）:** **DELTAN=1 validation** の **設計**は **完了**（**§21.9.5**、**§31.18.16**）。**今後**は **§21.9.5** を **優先**する。**次**は **3/4 reference World 標準条件**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.5 実装前設計2/4: DELTAN=1 validation設計完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.16**

**確定（設計のみ。production 未実装）:**

- **実 World** は **評価処理入口**で **一度だけ** **DELTAN=1** を確認する
- **reference World** は **構築直後・replay 前**に **一度**確認する
- **Vehicle ごと**に **重複確認しない**
- **型と値**を厳密に確認する（**`type(...) is int` かつ値 1**）
- **`bool`** や **文字列の `"1"`**、**`1.0`** は **受け入れない**
- **不適合**時は **警告継続**ではなく、**評価開始前に停止**する
- **DELTAN=1 確認**と **DELTAT 一致確認**を **分離**する（**DELTAT の具体手順**は **3/4**）
- **order-control を使わない方式**もあるため、**評価処理側の確認**を **独立して持つ**
- **World 生成時**は **DELTAN の型・値を実行時検査しない**。**order-control 用検査**は **制御 Node 作成時だけ**である

**実装前設計の進捗:**

- **1/4 完了:** Link 名 audit identity
- **2/4 完了:** DELTAN=1 validation（**本節**）
- **3/4 未着手:** reference World 標準条件（**次**）
- **4/4 未着手:** 共有の **所有者・存続範囲・保存内容・確認記録**

**最新再開地点:** **§21.9.5**。**詳細正本**は **§31.18.16**。**次**は **3/4**。

**最新注記（2026-11-04）:** **reference World 標準条件**の **設計**は **完了**（**§21.9.6**、**§31.18.17**）。**今後**は **§21.9.6** を **優先**する。**次**は **4/4**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.6 実装前設計3/4: Reference World標準条件設計完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.17**

**確定（設計のみ。production 未実装）:**

- **reference World** は実 World の **交通状態や制御を再現しない**
- 目的は **同一 Link 物理条件列**の **UXsim 最短旅行時間**の取得
- **DELTAN=1**、**REACTION_TIME = real_W.DELTAT**、したがって **reference_W.DELTAT = real_W.DELTAT**
- **Node** は **直列**。**分岐・合流・signal・flow capacity・order-control なし**
- **Link** は実 World から **length** と **`link.u`** だけを物理的に引き継ぐ
- **capacity_in / out** は **1000000.0**（非拘束）
- **number_of_lanes=1**、**jam_density=0.2**
- **Vehicle 1 台**、**departure timestep 0**、**single_trip**、**`enforce_route()`** で route 固定
- **十分な実行時間上限**を設定し、**未完走なら停止**する
- **空経路**や **不正な Link 値**を受け入れない
- **通常 output を生成しない**（logging interval は **1** を維持）

**実装前設計の進捗:**

- **1/4 完了:** Link 名 audit identity
- **2/4 完了:** DELTAN=1 validation
- **3/4 完了:** reference World 標準条件（**本節**）
- **4/4 未着手:** 共有の **所有者・存続範囲・保存内容・確認記録**（**次**）

**最新再開地点:** **§21.9.6**。**詳細正本**は **§31.18.17**。**次**は **4/4**。

**最新注記（2026-11-04）:** **結果共有設計**は **完了**（**§21.9.7**、**§31.18.18**）。**今後**は **§21.9.7** を **優先**する。**次**は **独立確認**、**commit・push**、**実装場所調査**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.7 実装前設計4/4: Reference replay結果共有設計完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.18**

**確定（設計のみ。production 未実装）:**

- 共有結果は **評価処理ごとの局所 context** が所有する
- **1 回の評価処理内だけ**有効である
- **global** や **World の恒久属性**にしない
- **次回評価へ持ち越さない**
- **physical_route_key** ごとに reference 結果を **1 回だけ**計算する
- Link 名列は **audit identity** として **複数保持**する
- **Vehicle 別 record** と **summary counter** を分離する
- **Reference World object** 自体は保存し続けない
- **未完走**や **重大不整合**があれば、正式結果を出さない
- 初期実装は **直列**

**実装前設計の進捗:**

- **1/4 完了:** Link 名 audit identity
- **2/4 完了:** DELTAN=1 validation
- **3/4 完了:** reference World 標準条件
- **4/4 完了:** 結果共有設計（**本節**）
- **実装前設計 4/4 すべて完了**

**最新再開地点:** **§21.9.7**。**詳細正本**は **§31.18.18**。**次**は **4 設計の独立確認**、**commit・push**、**実装場所候補の読取り専用調査**。

**最新注記（2026-11-04）:** **4 方式共通評価**の **実装場所等の調査**は **完了**（**§21.9.8**、**§31.18.19**）。**今後**は **§21.9.8** を **優先**する。**次**は **具体設計**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.8 4方式共通評価の実装場所・変更範囲・小規模検証方法の調査完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.19**

**調査 1/3〜3/3 完了（記録のみ。production 未実装）:**

- **signalized UXsim、FCFS、BATCH、TVT-MP** の **4 方式共通評価**
- **TVT-MP 専用評価ではない**
- **いずれか 1 方式の専用処理へ入れない**
- **独立した方式共通評価 module** が有力（ファイル名候補 **`uxsim/network_wide_waiting_time_evaluation.py`**）
- **Analyzer へ直接入れない**
- **`uxsim.py` へ直接入れない**
- 既存 Analyzer の delay 定義とは **分離**
- **reference World は Analyzer なし**
- 新 module 中心に変更範囲を小さくする
- **`__init__.py` 公開は検証後判断**
- 正式 test は **共有動作検証後**
- 既存 validation script への **CASE 8** 追加が有力
- **4 方式で同じ入口と同じ定義**を使用する

**最新再開地点:** **§21.9.8**。**詳細正本**は **§31.18.19**。**次**は **4 方式共通 module** の **具体的な部品構成**と **CASE 8 設計**。

**最新注記（2026-11-04）:** **具体設計**は **完了**（**§21.9.9**、**§31.18.20**）。**今後**は **§21.9.9** を **優先**する。**次**は **CASE 8**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.9 production実装前1/3: 4方式共通評価の具体設計完了

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.20**

**確定（設計のみ。production 未実装）:**

- 新 module 候補 **`uxsim/network_wide_waiting_time_evaluation.py`**
- 公開入口候補 **`evaluate_network_wide_waiting_time`**
- データ構造は physical key、audit identity、reference 結果、Vehicle record、counters、summary、評価結果
- 評価ごとの小さな context dataclass
- helper は入力確認、経路取得、key、replay、record、summary に分離
- 処理順序は入口確認から結果返却まで 16 段
- 正式式は **CW_z = 実旅行時間 − T_min,z**、**ACWT** と **ACWWT** はその平均
- participation は participating、nonparticipating、unspecified
- 不適合と不整合は停止する
- 終了時に replay 回数と再利用回数の整合を確認する
- CASE 8 は **8A〜8F** の 6 群。4 方式の method_name 確認は 8A または 8F へ統合する

**固定工程:**

- **1/3 完了:** 具体設計（**本節**）
- **2/3 次:** CASE 8 小規模検証
- **3/3 未着手:** 検証結果確認と production 実装可否判断
- **その後** production 実装開始

**最新再開地点:** **§21.9.9**。**詳細正本**は **§31.18.20**。**次**は **2/3 CASE 8 小規模検証**。

**最新注記（2026-11-04）:** **最新契約**は **§21.9.11** および **§31.18.22**。**`true_vot_per_second`**、**`evaluation_cohort`**、**timestep 差を正本とする CW_z**、**reference 専用 runner**。**§31.18.20** の **`true_vot`** / **`participation_category`** は **読み替え**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.10 production実装前2/3: CASE 8小規模検証（validation script）

**詳細正本:** **§31.18.20.11**、**§31.18.20.12**（CASE 8 設計）。**実装**は **`research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`** への **CASE 8A〜8F** 追加。

**記録（script 変更は別途実行・記録。production 未実装）:**

- **verification-only** 限定実装。**production module は未作成**
- **Analyzer なし loop** は **検証用**。**§31.18.22** で **production 専用 runner** を **正式確定**
- **CASE 1〜7** は **変更しない**契約

**最新注記（2026-11-04）:** **追加確認 4 項目**は **§21.9.11**、**§31.18.22**。**今後**は **§21.9.11** を **優先**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.11 production実装前追加確認4/4完了と最終統合契約

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.22**

**確定（設計統合のみ。本節執筆時点では production 未実装）:**

- **reference 専用 runner** が必要。**通常 `exec_simulation()`** は **Analyzer なし World** に **使用しない**
- **true VOT** は **`true_vot_per_second`**。**CW_z 秒値へ直接乗算**。**3600 換算なし**
- **同一 Vehicle plan** による **4 方式 paired 比較**
- **複数 replication** でも **replication 内 paired 構造**を維持
- **Vehicle 名**を **同一 plan 内対応 key** とする
- **`vehicle_plan_digest` 等**で **同一標本**を監査
- **TVT-MP nonparticipating 集合**は **他方式**では **比較 cohort**（**`evaluation_cohort`**）。**他方式へ制度上 nonparticipating を適用しない**
- **CW_z** は **整数 timestep 差**を **正本**とする
- **負の timestep 差**は **tolerance なし**で **停止**
- **`near_zero_negative`** 区分は **廃止**

**production 実装前（本節執筆時点）:**

- **追加確認 4/4 完了**
- **残件 0**
- **production 未実装**（**完了後**は **§21.9.12**）

**最新再開地点:** **§21.9.11**。**詳細正本**は **§31.18.22**。**当時の次**は **独立確認**、**commit・push**、**production 実装**（**歴史的記録**）。**production 実装・検証完了後**の **最新再開地点**は **§21.9.12**。**詳細正本**は **§31.18.23**。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。Visit 数ベース定義の最新参照先は **本 §21.9** および **§31.18**。

#### 21.9.12 network-wide ACWT・ACWWT production moduleと専用testの実装・回帰確認完了

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.23**

**新規作成（既存 production・test・trial・validation script は変更なし）:**

- `uxsim/network_wide_waiting_time_evaluation.py`（**1,407 行**）
- `tests/test_network_wide_waiting_time_evaluation.py`（**933 行**）

**公開入口:** **`evaluate_network_wide_waiting_time`**

**4 方式共通 module:** **`signalized_uxsim`**、**`fcfs`**、**`batch`**、**`tvt_mp`**。**`method_name`** は **監査のみ**。**CW_z**、**ACWT**、**ACWWT** の **式は共通**。

**主要 production 契約（要点）:**

- **完走済み real World**。**real World 非変更・再 simulation なし**
- **評価ごと新規 context**。**global cache なし**。**World へ評価状態を保存しない**
- **Reference replay** は **同一評価内**の **physical_route_key** 共有
- **`create_analyzer=False`** の **Reference World** と **Reference 専用 runner**（**通常 `exec_simulation()` 不使用**）
- **Reference 専用 logging:** **本体走行記録と `log_t_link` を維持**。**Analyzer average_speed 書込みのみ除外**（**「log_t_link だけ」ではない**）
- **CW_z** は **整数 timestep 差**。**`true_vot_per_second`**。**`evaluation_cohort`** 集計
- **正式結果に simulation object なし**。**file 出力なし**

**独立確認（利用者 Terminal）:**

| 項目 | 結果 |
|---|---|
| **`py_compile`**（2 module） | **成功** |
| **専用 pytest** | **51 passed**（**16.02 s**） |
| **CASE 1〜8** validation script | **All cases passed.** |
| **UXsim 原典照合** | **`traveled_route` / `record_log` / finalize / exec_simulation** 確認 **完了** |
| **可読性** | **初心者向け処理順**を **優先**。**修正必須の問題なし** |

**CASE 8 script:** summary の **`Production implementation has not started.`** は **script 作成時点の歴史的表示**。**script は今回変更しない**。**現行**は **§31.18.23** / **本節**。

**今回未実装（完了扱いしない）:**

- **package 公開**、**Analyzer 呼出し口**、**CSV/JSON/DataFrame**、**trial 統合**
- **3,000 台**からの **ACWT・ACWWT 正式算出**
- **正式 4 方式比較**、**nonparticipating 固定 Vehicle 集合**の **正式比較**
- **performance 最適化**、**並列化**、**persistent cache**

**最新再開地点（Route-Conditional production 完了時点）:** **本 §21.9.12**。**詳細契約**は **§31.18.23**。**2026-11-07 以降**の **OD 基準 AWT・AWWT・FCFS 正式検証**は **§21.9.14** / **§31.18.25** を **優先**する。**実装前設計**は **§21.9.13** / **§31.18.24**（**歴史**）。

**次の直接作業（Git は Cursor 外・利用者が実施）:**

1. **メモ更新後**、**4 ファイル**（**2 code + 2 memo**）を **Terminal で確認**
2. **`py_compile`**
3. **専用 pytest**
4. **CASE 1〜8 回帰**
5. **`git diff`**
6. **`git add`**
7. **cached diff 確認**
8. **`commit`**（**document 含む**。メッセージは **diff 確認後に確定**）
9. **commit 結果・最新 commit・残存変更**
10. **別指示で push**
11. **push 後 status・最新 commit・local/remote 一致**

**commit 候補:** 上記 **4 ファイル**（**利用者が diff 確認後に確定**）。

**歴史的記録:** §21.2、§21.4、§21.5、§21.7 の旧記述は **削除しない**。**§21.9.11** は **production 実装前**の **再開地点**として **維持**。

#### 21.9.13 FCFS 3,000台Route-Conditional実算と320 OD最短自由流Reference検証完了

**歴史的記録（2026-11-06 時点）:** **本節**は **OD Reference を production に載せる前**の **再開地点**であった。**production 実装後・FCFS 主指標正式算出後**は **§21.9.14** / **§31.18.25** を **優先**する。

**詳細技術正本（当時）:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.24**（**実装前設計**）。**Route-Conditional production 完了**は **§31.18.23** / **§21.9.12** を **歴史**として **参照**する。

**完了した作業（3 本）:**

1. **FCFS 3,000 台** — 現行 production **`evaluate_network_wide_waiting_time`** による **Route-Conditional** 接続検証（script 新規・output 確定・**未 commit**）
2. **320 OD** — UXsim **通常経路選択**が **OD 間最短自由流コスト**と一致（validation script 新規・**All 320 OD pairs passed.**・**未 commit**）
3. **設計確定** — **主指標 AWT・AWWT**、**補助 Route-Conditional AWT・AWWT**、**detour**、**OD Reference production 方針**（**§31.18.24**。**production 未実装**）

**FCFS Route-Conditional 実算（要点）:**

- Vehicle plan / cohort **hash 一致**、**3,000 完走**、production 評価 **成功**
- **Route-Conditional AWT 相当 579.2676666666666 s**（**主指標 AWT ではない**）
- **Route-Conditional AWWT 相当 553.3012723371289**
- participating **585.22 s / 569.654…**、nonparticipating **555.458… / 487.890…**
- actual route Reference **27 replay、2,973 reuse**
- 平均 actual-route 自由流 **125.352 s**、平均 Link 数 **10.3627**、最大 **44 Link**（**veh_1481** 遠回り）

**320 OD 検証（要点）:**

- **320/320** shortest cost match、**loop 0**、**2 回 replay 安定**
- 代表同率最短 **37/37** Reference 時間一致
- OD Reference 加重平均 **105.576 s**
- **平均迂回監査 19.776 s**（**125.352 − 105.576**。**production 正式集計前**）
- **AWT 監査予測 599.0436666666666 s**（**579.2676666666666 + 19.776**。**正式実装後に timestep 再計算**）

**指標整理（本節以降の呼び方）:**

- **主指標:** **AWT**、**AWWT**（**OD_minimum_free_flow_trip_time** 基準）
- **補助:** **Route-Conditional AWT・AWWT**（現行 **`cumulative_waiting_time_*`** と **同義**。**field 意味は変更しない**）
- **恒等:** `od_based = route_conditional + detour`（timestep 正本）

**後方互換:** **方式 B**（既存 field 維持 + 新 field 追加）。**Route-Conditional 名称**は **property**。**黙って主指標へ読み替えない**。

**未実装:** **OD Reference・AWT・AWWT の production**、**新 FCFS 主指標検証 script/output**、**既存 51 test 変更**。

**当時の最新再開地点（歴史）:** **本 §21.9.13**。**詳細契約**は **§31.18.24**（**実装前**）。

**現行の最新再開地点（AWT 完了後・本最適化前の当時記録）:** **§21.9.14** / **§31.18.25**。**現在地**は **§21.9.15** / **§31.19**。

**歴史的記録:** **§21.9.12** は **Route-Conditional production module・51 test 完了**の記録として **削除しない**。**§31.18.23** 本文の **ACWT・ACWWT** 表記は **当時の Route-Conditional 指標**を指す。

#### 21.9.14 AWT・AWWT production実装とFCFS 3,000台正式算出完了

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.18.25**（**実装前設計**は **§31.18.24**。**Route-Conditional のみ**は **§31.18.23** / **§21.9.12**）。

**完了した作業（概要）:**

1. **production:** `uxsim/network_wide_waiting_time_evaluation.py` — **OD Reference**、**主指標 AWT・AWWT**（**`average_waiting_time_s` / `average_weighted_waiting_time`**）、**detour**、**Route-Conditional 明示 property**、**Network signature**、**恒等関係**、**負値停止**、**simulation object 非保持**。既存 **cumulative_*** は **Route-Conditional のみ**（**意味変更なし**）。
2. **新規 test:** `tests/test_network_wide_waiting_time_od_reference.py`（**793 行**、**23 件**、**約 21.52 s**）。**初回 2 件不合格**は **test が `capacity_in` を作成後代入**したため **`capacity_in_remain` が想定通りでなかった**こと。**`addLink` 時に `capacity_in=0` と user_function** を渡す **test 修正**。**production は変更なし**。**修正後 23 件全合格**。
3. **既存回帰:** `tests/test_network_wide_waiting_time_evaluation.py` **未変更**。**51 passed**、**約 20.05 s**。**pytest 合計 74 件合格**。
4. **CASE 1〜8:** **All cases passed.**
5. **320 OD:** **320/320**、**mismatch 0**、**安定**、**loop 0**、**同率 37/37**、**All 320 OD pairs passed.** 旧 output は **`...before_awt_production`** へ **退避**。新 output は **元 directory**。
6. **FCFS 3,000 台正式検証:** `research_scripts/run_fcfs_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py`。**static validation passed**。**正常終了**。

**FCFS 正式結果（要点）:**

- **AWT:** **599.0436666666667 s**、**AWWT:** **571.69001350099**
- **Route-Conditional AWT:** **579.2676666666666 s**、**Route-Conditional AWWT:** **553.3012723371289**
- **Average Detour Time:** **19.776 s**、**Average Weighted Detour Time:** **18.388741163860672**
- **平均 OD 最短自由流:** **105.576 s**、**平均実走行ルート自由流:** **125.352 s**
- **恒等:** `599.0436666666667 = 579.2676666666666 + 19.776`、`571.69001350099 = 553.3012723371289 + 18.388741163860672`（**Vehicle・全体・cohort・weighted** で確認。**分解の正しい言い方:** **AWT を Route-Conditional AWT と Average Detour Time に分解**）

**Reference counter:** OD **320 / 320 / 2680**、actual-route physical **27 / 27 / 2973**（**27** は **physical 条件列**の **固有数**）。

**performance（記録）:** FCFS sim **約 6.447 s**、production eval **約 53.872 s**（**Route-Conditional のみ 約 24.21 s** から **増**）、script total **約 117.56 s**。

**正式 output directory:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3`（**manifest** の **`AWT_s` / `AWWT`** と production **`average_waiting_time_s` / `average_weighted_waiting_time`** の **対応**は **§31.18.25**）。

**route_pref 原典:** **§31.18.25.13〜.15**（**600 秒ごと全 Node 間最短**、**homogeneous DUO_update**、**確率的出口選択**（**`hard_deterministic_mode=False`**）、**情報数 9,912**、**配列 10,080**）。**本評価は実 World の route 条件を変更していない**。

**未実装（§21.9.14 執筆時点）:** TVT-MP 正式算出、**4 方式比較**等（**TVT-MP AWT・AWWT 算出完了は §21.9.16** / **§31.20**）。

**当時の最新再開地点（歴史）:** **本 §21.9.14**。**詳細契約**は **§31.18.25**。**baseline・Candidate 共通 snapshot 最適化・full-completion 正式受入れ**後の **最新再開地点**は **§21.9.15**。**詳細正本**は **§31.19**。

**次の直接作業（§21.9.14 執筆時点・歴史）:** 実装 **3 file** と **メモ 2 file** の **Terminal 確認**（**py_compile**、**pytest 74**、**CASE 1〜8**、**320 OD**、**FCFS 結果確認**、**git diff / add / commit**）。**現行の次作業**は **§21.9.15** を参照。

**歴史的記録:** **§21.9.13**（**320 OD 事前検証・設計確定**）、**§31.18.24**（**実装前設計全文**）は **削除しない**。

#### 21.9.15 baseline・Candidate共通snapshot高速化の正式受入れ

**執筆日:** 2026-11-08

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.19**（**§29** = **Candidate 集合内共有直列化**。**本節** = **baseline と Candidate 集合の 2 回 dumps を 1 回に統合**）。

**位置付け（非技術）:** 同一 real timestep の同一交通状態を、**baseline 全体予測**と **Candidate 局所予測**の **2 用途で二重保存**していた重複を除いた。**共有するのは immutable な snapshot bytes のみ**。**baseline / Candidate の World・mutable 状態は共有しない**。

**完了した作業:**

1. **T=0〜199 性能診断** — `research_scripts/diagnose_tvt_mp_6x6_grid_3000_vehicle_performance_first_200_timesteps.py`。**driver ~707 s**、**約 97%** が保存・複製・復元（**§31.19.6**）。
2. **production 前 A/B** — `diagnostics/order_control/tvt_mp_baseline_candidate_shared_snapshot_ab.py`。**平均 ~35.6% 短縮**、**~1.55×**、**transactions 816** 維持、**全 run 完全一致**。**weakref 修正**（**diagnostic のみ**）。
3. **production 実装** — `order_control_baseline_driver.py`、`order_control_tvt_mp_local_virtual_calculation_set.py`、`order_control_tvt_mp_candidate_local_state.py`（**`serialize_baseline_real_world_snapshot`**、**`build_baseline_fork_from_serialized_world`**、**`serialized_real_world_snapshot`**）。
4. **関連 test 横断監査・更新** — **777 件合格**（**test を通すため production を旧方式へ戻していない**）。
5. **T=0〜299 回帰** — `..._eval_300_timestep_baseline_candidate_shared_snapshot_validation.py`。**exec ~1021.93 s**、研究 CSV **完全一致**（**§29 後 ~1637.95 s から ~37.6% 短縮**）。
6. **3,000 台・nonparticipating 20%・full-completion** — `..._full_completion_audit_baseline_candidate_shared_snapshot_validation.py`。**Reference** `..._candidate_limit_10_seed_0_vot_seed_1_nonparticipation_seed_3` と **研究・監査・VOT・manifest 研究 key 完全一致**。**`formal_production_acceptance_ready: true`**。**transactions 4298**、**exec ~34245.23 s**（旧 **65093.89 s**、**~47.39% 短縮・~1.90×**）。

**正式受入れ判断:** **採用してよい**（A/B 両順序一致、**777 test**、T=0〜299・full-completion **first difference なし**、**研究結果不変**の **実装最適化**）。

**AWT・AWWT（§21.9.15 時点）:** 保存済み Reference に **OD 基準 AWT・AWWT 出力なし**。**当時**は **TVT-MP 正式算出が次工程**。**算出完了**は **§21.9.16** / **§31.20**。

**残る高速化候補:** snapshot からの不要履歴除外、局所復元縮小、bytes 増加抑制、等（**本最適化と混在させない・別作業**）。

**変更・新規 file（commit 前・一覧）:** production **3**、test **7+**、diagnostic **2**（新）、validation script **2**（新）。**旧** `tvt_mp_candidate_shared_serialization_ab.py` は **現 production 再実行時は更新要**（**歴史有効**）。

**失敗履歴:** **production 欠陥なし**。**diagnostic** object id。**test** 旧契約一括監査。**validation** REFERENCE 名・sys.modules・manifest key 等（**§31.19.14**）。

**当時の最新再開地点（歴史）:** **本 §21.9.15**。**詳細正本**は **§31.19**。**TVT-MP AWT・AWWT 正式算出後**の **最新再開地点**は **§21.9.16**（**§31.20**）。

**次の直接作業（§21.9.15 執筆時点・歴史）:** commit 前 diff 等。**現行**は **§21.9.16**。

#### 21.9.16 TVT-MP AWT・AWWT正式算出完了と次の分析課題

**執筆日:** 2026-11-09

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.20**（**評価関数・FCFS:** **§31.18.25**。**高速化受入れ:** **§31.19**）。

**完了:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py` で **完走後 1 回** `evaluate_network_wide_waiting_time`（**`tvt_mp`**）。出力 `.../tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation_departure_999_seed_0_demand_seed_42_vot_seed_1_nonparticipation_seed_3` に **vehicles / cohorts / summary.json** を追加。**TVT-MP 正式 10 file 維持**。**旧 Reference** と **研究・監査・VOT・manifest 一致**（**AWT file は Reference 比較外**）。

**TVT-MP 全体（3,000）:** **AWT 458.570 s**、**AWWT 440.371**（**秒ではない**）、Route-Conditional AWT **445.522 s**、Route-Conditional AWWT **429.624**、Average Detour **13.048 s**、VOT-weighted Average Detour **10.746**（**単位は §31.20.6**。**詳細・合計は §31.20.6**）。

**cohort:** 参加 2,400 — AWT **461.023 s**、AWWT **453.387**；非参加 600 — AWT **448.757 s**、AWWT **388.305**（**§31.20.7**）。

**FCFS 比較（同条件）:** AWT **599.044 → 458.570**（**約 23.45% 短縮**）、AWWT **571.690 → 440.371**（**約 22.97% 短縮**）。detour 平均 **約 34.0%** 短縮（**表は §31.20.10**）。

**未解決点:** **AWWT 改善率が AWT を上回らなかった**（全体・参加 cohort）。**VOT 選別効果は集計で未確認**。**制度失敗・production 欠陥等は断定しない**（**§31.20.12**）。

**性能（参考）:** exec **~34,757.75 s**、評価 **~39.79 s**、AWT 書出し **~0.071 s**、script total **~34,819.61 s**。

**次の順序（§21.9.16 執筆時点・歴史）:** 1 本メモ更新 → 2 **signalized UXsim** 正式 sim・AWT・AWWT → 3 **TVT-MP VOT 五分位分析** → 4 設計判断 → 5 **3 方式比較**（**§31.20.14**）。

**当時の最新再開地点（歴史）:** **本 §21.9.16**。**signalized UXsim 完了後**の **最新再開地点**は **§21.9.17**（**§31.21**）。

**当時の直接作業（歴史）:** signalized UXsim **AWT・AWWT script 設計**（**完了: §21.9.17**）。

#### 21.9.17 signalized UXsim AWT・AWWT正式算出完了とTVT-MP分解分析への移行

**執筆日:** 2026-11-09

**詳細技術正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.21**（**TVT-MP・FCFS 比較:** **§31.20**。**評価関数・FCFS:** **§31.18.25**）。

**完了:** `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py` で **完走・交通解消後 1 回** `evaluate_network_wide_waiting_time`（**`signalized_uxsim`**、**method-specific participation status なし**）。出力 `.../signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3_signal_59_0_59_0`。**信号:** **`[59,0,59,0]`**、API cycle **118**、offset **0 / 29.5 / 59 / 88.5**、実効 **60/1/60/1**（**§31.21.4〜6**）。**`--validate-signal-timing-only`** 合格。

**full-completion:** **3,000** 台 **`end`**、**`World.T` 2117**、evaluation end **2116**、safe cap **12,000**（**2117 は事前仮定ではない**）。

**signalized 全体（3,000）:** **AWT 391.899 s**、**AWWT 396.730**（**秒ではない**）、Route-Conditional AWT **377.283 s**、Route-Conditional AWWT **381.559**、Average Detour **14.616 s**、VOT-weighted Average Detour **15.171**（**§31.21.9**）。

**cohort:** 参加 2,400 — AWT **392.889 s**、AWWT **398.548**；非参加 600 — AWT **387.94 s**、AWWT **389.461**（**§31.21.10**。**共通比較 cohort**）。

**3 方式暫定比較（同 plan・seed・cohort）:** FCFS AWT **599.044 s** → TVT-MP **458.570 s** → signalized **391.899 s**。**AWWT** FCFS **571.690** → TVT-MP **440.371** → signalized **396.730**。**signalized は TVT-MP より AWT 約 14.54%・AWWT 約 9.91% 低い**（**単一 seed・需要条件。一般化しない**。§31.21.13）。

**分布:** **到着時刻**・**OD waiting** の **中央値・95%・99%** は signalized < TVT-MP、**最大のみ**わずかに大きい（末尾に長い値。**§31.21.14**）。**各方式の分布統計の比較**。**Vehicle 別 paired 比較（早着・遅着台数）は未集計**。**個別優劣割合は Vehicle 単位分析で確認**（**§31.21.15**）。

**AWWT 注意:** signalized では **AWWT > AWT**。**TVT-MP では AWWT < AWT**。**FCFS からの改善率で AWWT 優位は未確認**（**§31.21.16**・**§31.20.12**）。

**性能（参考）:** exec **~4.61 s**、評価 **~39.72 s**、書出し **~0.080 s**、script total **~58.65 s**。

**次の順序:** 1 **TVT-MP VOT 五分位・取引経験別分解 analysis script 設計**（**§31.21.17**・**§31.20.13**）→ 2 原因確認後の設計判断 → 3 **3 方式比較表の整理**（必要時）。

**当時の再開地点として維持:** **本 §21.9.17**。**当時の詳細正本**は **§31.21**。

**当時の直接作業:** **TVT-MP 分解 analysis script 設計**。**その前**に **signalized script**・**TVT-MP script**・**本メモ**の確認と **必要な commit・push**（**§31.21.18**）。

**最新再開地点（2026-11-12 追記）:** **§21.9.18** / 詳細 **§31.22**。**本 §21.9.17 の古い文言は削除しない。**

#### 21.9.18 TVT-MP VOT効果の17台原因分析とclearance・signal候補条件再評価

**執筆日:** 2026-11-12

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§31.22**（単位注記は **§31.20.6** / **§31.21.9**。signalized 全赤あり当時の記録は **§31.21**）。

**検索語:** AWWTがAWTより改善しない、VOT効果、buyerのみ悪化17台、経路差、route choice、seed交絡、確率的経路選択、往復、再訪、共通Link、方式固有Link、clearance=0、clearance=1、次timestep、全赤あり、全赤なし、offset 0、signalized比較、TVT-MP clearance=0未実行、主条件未確定、感度分析未確定。

**完了した作業:**

1. TVT-MP 17 台 timing trace 診断（`diagnose_tvt_mp_6x6_grid_3000_vehicle_buyer_only_worsened_17_timing_trace.py`。production 一致、raw trace 先行確定）
2. FCFS route timing 診断（`diagnose_fcfs_6x6_grid_3000_vehicle_buyer_only_worsened_17_route_timing.py`）
3. FCFS node arrival timing 診断（`diagnose_fcfs_6x6_grid_3000_vehicle_buyer_only_worsened_17_node_arrival_timing.py`）
4. 17 台 route Apple-to-Apple 比較（出発差 0 秒、総旅行時間差 **+3012 秒**）
5. **共通Link** と **方式固有Link** の重複なし分解
6. FCFS **clearance=0** 候補 trial
7. signalized **全赤なし** 候補 trial
8. signal timing validation（2 相・全赤なし、offset 初期 phase 再計算、6×6 件数 9/10/9/8）
9. Vehicle-level clearance=0 waiting 分布再確認（AWT 再現）

**主要結果（17 台・単一 seed の事例分析。正式相関判定ではない）:**

- 総悪化 **+3012 秒**（3363 秒や 3352 秒と混同しない）
- **共通Link** **−413 秒**（同一 Vehicle・同一 Link 98 件。Link 進入〜交差点到着 **−284**、交差点到着後待ち **−129**）
- **方式固有Link** **+3425 秒**（自由流差 **+144**、自由流超過差 **+3281**）
- 恒等式 **3012 = −413 + 3425**、**3425 = 144 + 3281**
- **16 台経路差**、`veh_124` のみ同一経路
- 一部で **往復**・**再訪**（order exchange 自体とは断定しない）
- **AWWTがAWTより改善しない** ことの原因切り分けは継続中。単一 seed の 17 台で **VOT効果**不成立とは結論しない

**未確認:**

- 分岐時点の候補 Link 別 `route_pref`・混雑評価・乱数値が未保存
- **経路差**の理由（当時の評価 / `route_pref` 履歴 / **確率的経路選択** / **seed交絡**）は分離不能
- 前方車両別寄与は既存出力不足（前方車両名・停止履歴なし）
- 追加 TVT-MP 前方車両診断は行わない
- **TVT-MP clearance=0** の取引数・AWT・AWWT は未確認（**TVT-MP clearance=0未実行**）

**clearance=0 の意味:** 時間差が文字どおり 0 ではない。**追加 clearance 0、直前通過の次timestepから通過可能。** order-control は **1 timestep 最大 1 台**。**clearance=1** は異方向切替時に次 timestep を空け、その次から通過可能。同一 inlink 連続通過はこの異方向 clearance では止めない。

**FCFS clearance=0 結果:** AWT **21.738666666666667 秒**、AWWT **21.428271940078936**（**秒ではない**）。median **9 秒**、p90 **66 秒**、p95 **100 秒**、p99 **124 秒**、max **202 秒**。**>60 秒 331 台**、**>120 秒 37 台**。AWT 大幅低下は集計ミスではない。TVT-MP 発動機会が消えたとは断定しない。取引件数は未確認。

**signal 候補（signalized比較）:**

- **全赤あり** `[59, 0, 59, 0]`: AWT **391.899 秒**、AWWT **396.73046930775473**
- **全赤なし** `[59, 59]`: AWT **435.9433333333333 秒**、AWWT **433.70148368735846**
- 全赤なし−あり: AWT **+44.04433333333327 秒**、AWWT **+36.97101437960373**（約 +11.24% / +9.32%）
- 差の原因は未確認。全赤除去の一般悪化結論にしない
- **主条件未確定**、**感度分析未確定**

**新規未追跡 script 5 本:**

- `research_scripts/diagnose_tvt_mp_6x6_grid_3000_vehicle_buyer_only_worsened_17_timing_trace.py`
- `research_scripts/diagnose_fcfs_6x6_grid_3000_vehicle_buyer_only_worsened_17_route_timing.py`
- `research_scripts/diagnose_fcfs_6x6_grid_3000_vehicle_buyer_only_worsened_17_node_arrival_timing.py`
- `research_scripts/run_fcfs_6x6_grid_3000_vehicle_awt_awwt_od_clearance_0_trial.py`
- `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_no_all_red_trial.py`

**最新再開地点:** **本 §21.9.18**。**詳細:** **§31.22**。

**直接作業:** 全赤あり `[59, 0, 59, 0]`・全交差点 **offset 0** と、全赤なし `[59, 59]`・全交差点 **offset 0** の 2 trial 設計。その後に 4 signal 候補を比較し、**TVT-MP clearance=0** 長期実行可否を判断。続けて seed 設計改善。VOT と効果の正式判定は seed 設計改善後の複数 seed 比較。

**未作成・未実行:** offset 0 の 2 trial、**TVT-MP clearance=0**。Git 操作は利用者が行う。

#### 21.9.19 TVT-MP clearance=0正式分析完了と30反復seed・最初の経路分岐乱数監査への移行

**執筆日:** 2026-11-14

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32**

**歴史:** **§21.9.18** および **§31.22** は TVT-MP clearance=0 **実行前**の歴史的記録である。当時の「未実行」「直接作業は offset 0 trial 設計」は **当時の記録**として維持する。**現在の未実行を意味しない。** 最新状態は **本 §21.9.19** / **§32** を優先する。

**検索語:** TVT-MP clearance=0、transaction 2421、Visit 5457、AWT 21.676、AWWT 20.427812923323355、VOT五分位、buyerのみ、Top 1%、buyer局所効果、局所baseline、counterfactual、nonparticipating 600台、trade scope 112台、nonparticipating Visit 129件、30反復、日々の交通変動、seed交絡、最初の経路分岐、keyed randomization、未採用、原典監査。

**完了:**

1. TVT-MP clearance=0 正式 trial 実行・独立出力確認
2. participating 2,400 台の VOT・取引 role・Q5 分析
3. Top 1% 24 台の FCFS/TVT route 比較
4. 同一ルート悪化 7 台の buyer Visit 局所実現確認
5. nonparticipating 600 台の FCFS 比較
6. 30 反復の研究目的確定
7. 最初の経路分岐における seed 交絡を次の監査対象とすることを確定

**TVT-MP clearance=0 正式結果（要点。全文は §32.2）:**

- script: `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_clearance_0_trial.py`
- output: `research_outputs/trial/tvt_mp_6x6_grid_3000_vehicle_awt_awwt_od_clearance_0_trial_departure_999_seed_0_demand_seed_42_vot_seed_1_nonparticipation_seed_3`
- transaction **2421**（今回の正式出力の取り違え防止。production 一般契約ではない）
- Visit **5457**
- full completion true、traffic clearance true
- FIFO violation **0**
- AWT **21.676 s**
- AWWT **20.427812923323355**（**秒ではない**）
- FCFS clearance=0 AWT **21.738666666666667 s**
- small-scale の bare `visit_id` World 全体一意性検査は誤り。`visit_id` は Vehicle 間で同値になり得る。production Visit ID 生成は未変更

**研究上の位置づけ:**

- clearance=0・3,000 台は低混雑の機構確認として有用
- 参加車平均 FCFS 比 waiting saving **0.1133333333 s**、Q5 平均 **1.947916667 s**。総旅行時間・主要性能評価としては小さい
- **当然の中心シナリオとはしない**
- **clearance=1 が中心候補として再び有力**
- clearance=0 を性能中心にするなら高需要の別シナリオが必要。未設計・未実行
- 主条件・感度分析は未確定。clearance=0 が主条件、clearance=1 が感度分析、とは書かない

**participating 分析（§32.4〜32.6）:**

- VOT vs `buyer_count` Spearman rho=**0.5461134458**
- VOT vs `seller_count` rho=**-0.5883832968**
- 高 VOT を buyer、低 VOT を seller へ選別する機構は明瞭。旅行全体改善の保証とは別問題
- Top 1% 24 台は全車 buyer のみ、`seller_count` 合計 0、`buyer_count` 合計 53
- Top 1%: 11 改善・1 同一・12 悪化、平均 **-1.375 s**
- 「Top 1% が一般に悪化する」とは結論しない。24 台・単一 seed の事例

**route と buyer Visit（§32.7〜32.8）:**

- 15 台同一ルート、9 台異経路
- 同一ルート悪化 7 台の 14 buyer Visit は全件で局所短縮を実現（class A、candidate どおり、rank・next Link 一致、FIFO preserved）
- 局所合計 +18 timestep、最終 waiting_saving 合計 **-20 s**
- **buyer 局所 baseline と FCFS 実走行は異なる counterfactual**
- 局所実現と FCFS 比旅行全体短縮は等置しない
- production 欠陥・概念破綻とは断定しない

**nonparticipating 600 台（§32.9）:**

- 全体 mean saving **-0.14 s**、median **0**
- improved / equal / worsened: 250 / 76 / 274
- participating との平均差 **-0.2533333333 s**。大きな平均損失は確認されない。一般化しない
- trade scope 経験者 **112 台**、延べ Visit **129 件**
- 局所外部効果: 127 件 0、2 件だけ 1 timestep 遅延、FIFO false 0
- この 2 timestep だけで最終 FCFS 比効果を説明しない
- Node 別 FCFS/TVT 時刻比較は既存出力だけではできない
- nonparticipating 車が制度的に犠牲になった、とは書かない

**30 反復（§32.10）:**

- 目的は同一固定交通の 30 回繰返しではない
- 各反復は、同じ network・シナリオ定義の下で発生する **独立した一日の交通実現**
- 日々変動する OD・出発時刻・VOT・参加配置・交通状態を表す
- 同一反復内で FCFS と TVT へ同じ外生条件を与え、方式だけを変える
- 主分析候補は `ΔAWT[r]`、`ΔAWWT[r]` の paired difference
- ただし route-choice 乱数の厳密な対応は未確認
- 30 反復は現行 seed 体制でも必要。seed 改善は代替ではなく追加統制
- 「あらゆる交通状態」へ一般化しない。設定した分布・需要規模・network 範囲内に限定する

**最初の経路分岐と seed 交絡（§32.13〜32.15）:**

- 同じ traffic seed でも、呼出順・回数が変われば同一 Vehicle へ同一乱数値が割当たる保証はない **可能性がある**
- 最初の対応可能な経路分岐が **乱数差**によるか **交通状態差**によるかを識別する必要
- 分岐後の全乱数一対一対応は必須としない
- seed 交絡が実際に原因である、とはまだ断定しない
- **keyed randomization は未採用・未実装**。必須とも書かない
- 現行方式で最初の分岐まで同一乱数入力を保証できるなら不要
- 保証できない場合に限り検討。経路の強制同一化はしない

**未確認理由:** 原典コードの該当箇所をまだ読取り監査していない。資料未入手ではない。

**次の直接作業:**

- UXsim route choice、RNG、World copy、TVT baseline / Candidate 仮想 World の **読取り専用原典監査**
- production 変更なし
- 監査結果を §32 へ追記してから実装要否を判断する

**最新再開地点:** **本 §21.9.19**。**詳細正本:** **§32**。

**Git 操作は利用者が行う。commit / push はまだ行わない。**

#### 21.9.20 route-choice乱数原典監査完了と4方式共通seed/RNG基盤設計への移行

**執筆日:** 2026-11-14

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.17〜§32.19**

**歴史:** **§21.9.19** および **§32.1〜§32.16** は原典監査前の記録として維持する。当時の「まだ読取り監査していない」は当時の事実である。最新状態は **本 §21.9.20**。

**2026-11-14 最新参照:** 本節は診断実装前の歴史的記録である。当時の未設計・未実装・未検証は当時の事実である。**§21.9.21** および詳細 **§32.20** で、production変更なし診断の実装と第一層・第二層の結果不変性反証が完了した。production seed/RNG 改修はなお未着手である。最新再開地点は **§21.9.21**。

**検索語:** NOT_GUARANTEED_BY_CURRENT_CODE、NO_DIRECT_VIRTUAL_TO_REAL_RNG_CONTAMINATION_FOUND、keyed randomization暫定分類2、4方式共通seed/RNG基盤、Node.generate、route_next_link_choice、初回arrival tiebreaker、用途別RNG、BATCH改修前先行。

**完了:** FCFS対TVT-MP route-choice乱数対応の読取り専用原典監査。production・script・tests・output は未変更。診断 script と seed/RNG 実装は未着手。

**原典要点:**

- `Node.generate` の origin choice は受入れ判定前に `W.rng` を消費する
- `Vehicle.route_next_link_choice` は Link 終端待機中に毎 timestep 再抽選し得る
- 初回 arrival tiebreaker は route choice と同じ `W.rng` を使用する
- 再訪 tiebreaker は `W.order_control_rng`
- DUO noise、通常 merge 等も `W.rng` を使用する
- baseline／Candidate 仮想 World は独立 copy
- 仮想 World から実 World への RNG 書戻しは確認されない

**判定:**

- 仮想 World: `NO_DIRECT_VIRTUAL_TO_REAL_RNG_CONTAMINATION_FOUND`（確認範囲での直接汚染なし。絶対証明ではない）
- 最初の分岐時の同一 draw: `NOT_GUARANTEED_BY_CURRENT_CODE`
- keyed randomization: **暫定分類2**、未採用・未実装。必須とは現時点で判断しない
- production ファイルを変更しない診断には設計可能性がある
- ただし診断方法は未設計・未実装・未検証
- 単純な method 前後 wrapper だけで十分とは未確認
- `Node.generate` は 1 呼出し中に複数 choice を含み得る
- 診断なし／ありの結果完全一致を小規模 trial で確認する必要
- 診断が安全に成立した後に分類2を確定する
- 成立しない場合は keyed randomization 等を再評価する
- 過去の特定 Vehicle 経路差の実原因は断定しない

**4方式共通方針:**

- seed 改善を FCFS対TVT だけの応急処置にしない
- signalized UXsim、FCFS、BATCH、TVT-MP を方式設定だけで切替える共通基盤として設計する
- `Node.transfer` の既存 4 方式分岐を維持する
- scenario 層（`od_seed`、`departure_seed`、`vot_seed`、`participation_seed`）と用途別 RNG 層（`route_choice_rng`、`duo_noise_rng`、`merge_rng`、`arrival_tiebreaker_rng`、`method_rng` 受皿）を分ける
- 用途別分離だけでは、route-choice 呼出回数差があれば stream はずれ得る。strict CRN の自動完成とは書かない
- BATCH 共通基盤は大幅改修前に先行可能。BATCH 固有乱数契約は改修後
- 現行 seed のまま 30 反復本番へ直ちに進まない。30 反復自体は依然必要で、seed 改善の代替ではない

**次の利用者判断:**

1. production 変更なしの最小 route-choice RNG 診断を先に設計するか
2. 4 方式共通 seed/RNG 基盤の詳細設計を先に固めるか

今回は診断 script 作成と seed/RNG 実装へ進まない。

**最新再開地点:** **本 §21.9.20**。**詳細正本:** **§32.17〜§32.19**。

**Git 操作は利用者が行う。**

#### 21.9.21 production変更なしroute-choice RNG診断の実装と二層不変性反証完了

**執筆日:** 2026-11-14

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.20**

**歴史:** **§21.9.20** は診断実装前の記録である。当時の「未設計・未実装・未検証」は当時の事実である。最新状態は本 **§21.9.21** である。

**目的:** FCFS対TVT-MP の最初の経路分岐が seed差か、交通状態・preference 差かを監査するため、追加 random draw なしの route-choice RNG診断基盤を作った。これは seed改善の完成ではない。

**新規 3 ファイル:**

- `research_scripts/route_choice_rng_diagnostic.py`
- `research_scripts/run_route_choice_rng_diagnostic_invariance_two_route.py`
- `research_scripts/run_route_choice_rng_diagnostic_invariance_12_vehicle_tvt_mp.py`

**第一層:** 4 case が成功した。pあり、p省略、候補1件、複数候補、origin 拒否と再試行、in-trip 再抽選を含む。全 case で formal snapshot、rng、`order_control_rng` が完全一致した。第一層の代表件数は、two-route case の event 7件、blocked origin の event 29件、in-trip retry の event 31件である。第二層の 80件、4,950回、1,512回とは別の結果である。

**第二層:** 12台 TVT-MP。transaction 2件。Visit 8件。buyer 2件。seller 6件。diagnostic event 80件。real origin draw 12件。real in-trip draw 68件。virtual `Node.generate` 4,950回。virtual `route_next_link_choice` 1,512回。proxy pickle rejection 0回。研究 bundle、full-run audit、Vehicle、Link、rng、`order_control_rng` が完全一致した。method 復元は成功した。baseline World と Candidate local World の pickle 経路で、proxy 混入は観測されなかった。これは当該反証条件の結果であり、全状況での絶対証明ではない。

**明確な未完了:**

- production seed/RNG 改修は未着手である。
- seed改善は未完成である。
- keyed randomization は未採用・未実装であり、暫定分類2を維持する。
- 4方式共通 seed/RNG 基盤は未実装である。signalized UXsim、FCFS、BATCH、TVT-MP への共通実装には進んでいない。
- 3,000台への診断適用は未実施である。
- 最初の対応可能な経路分岐の event pairing は未実装である。
- 現行共有 RNG stream が過去の経路差の実原因かは未判定である。common random numbers は未実装である。

**次の作業:** 既知の buyer-only 悪化 Vehicle 群、または代表 Vehicle を対象とした、限定 3,000台 FCFS対TVT-MP route-choice RNG監査を設計する。実装前に、対象 Vehicle、停止条件、ログ上限、性能見積りを決める。production、Vehicle plan、seed、VOT、出発時刻は変更しない。新規診断 script として実装する。この次作業は未着手である。30反復の本番設計へはまだ進まない。

**最新再開地点:** 本 **§21.9.21**。**詳細正本:** **§32.20**。

**Git 操作は利用者が行う。commit／push はまだ行わない。**

**検索語:** route-choice RNG診断、第一層、第二層、結果不変性、12台TVT-MP、baseline World、Candidate local World、pickle混入、proxy pickle rejection 0、transaction 2、Visit 8、buyer 2、seller 6、virtual Node.generate 4950、virtual route_next_link_choice 1512、seed改善未完成、keyed randomization未実装、最初の経路分岐、次の作業

#### 21.9.22 4方式比較のseed／RNG改変基本設計確定とBATCHレビュー前の区切り

**執筆日:** 2026-11-18

**詳細正本:** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21**

**§21.9.21** および **§32.20** は、診断実装と二層不変性反証までの歴史的記録である。当時の「keyed randomization 未採用」「限定 3,000台診断が次作業」は当時の状態である。削除も書換えもしない。最新状態は本 **§21.9.22** および詳細 **§32.21** を優先する。

production の seed／RNG 改修は未着手である。seed 改善が完成したとはしない。BATCH production コードのレビューは未着手である。今すぐ別チャットへ移る予定ではなく、当面はこのチャットで BATCH レビューを進める。

**確定した基本方針:**

1. route choice
   - 4 方式共通の keyed randomization
   - origin と in-trip を分離
   - 1 候補は乱数なし・attempt 非消費
   - 2 候補以上だけ attempt 消費
   - Vehicle、Link、Link 訪問番号、attempt 等で識別
   - Candidate 局所計算の決定的進路には導入しない
2. arrival tiebreaker
   - FCFS・BATCH・TVT-MP で対応する Node 訪問に共通の keyed 値
   - inlink は key に含めない
   - Node 訪問番号は Link 別進入回数から導く
   - signalized UXsim には導入しない
3. signalized UXsim merge
   - 他方式と共有しない
   - 専用順次消費型 RNG へ分離
   - outlink shuffle と Vehicle choice に使用
   - 自然な「同じ merge 機会」がないため、無理に keyed 対応しない
4. 最小追加状態
   - Link 別進入回数
   - 現在 Link 訪問中の確率的 route-choice attempt
   - origin の確率的 route-choice attempt
   - Node 別 counter は持たない
5. production baseline 確認
   - 現行 TVT-MP production は過去確定順位を適用する baseline 経路を使用する
   - `apply_copied_tvt_confirmed_ranks=False` 側は production 呼出しなし
   - 確認した呼出し元は tests のみ
   - production baseline が通常 merge を使うという誤説明は採用しない
   - TVT-MP には baseline 計算と局所 Candidate 計算があり、「最初の baseline 計算」という構造はない
6. 実装 branch
   - seed／RNG 実装は現在の production branch へ直接行わない
   - BATCH レビュー完了後、専用の新規 branch で実装・検証する
   - branch 名と分岐元 commit は実装開始時に確定する
   - Git 操作は利用者が Terminal で行う
   - Cursor には Git 操作をさせない
   - 検証完了前に production へ統合しない

**明確な未完了:**

- 具体的な hash／乱数生成方式
- 正式な属性名・メソッド名
- snapshot／rollback／pickle 反映
- BATCH Level 2 mimic への具体接続
- BATCH production コードの処理レビュー
- production 実装
- test／trial
- 30 反復本番

**次の作業:**

- まずメモ差分を Terminal で独立確認する。
- メモだけをコミットし、残存変更を確認する。
- その後、現在のチャットで現行 BATCH production コードをレビューする。
- コードから処理順の疑似コードを作成する。
- 利用者が BATCH 設計を思い出せるよう、交通上の意味と Python 処理を丁寧に説明する。
- BATCH レビュー後に seed／RNG 基盤との接続範囲を確定する。
- BATCH レビュー完了後、実装は専用 branch・別チャットで開始する予定である。
- BATCH レビューが長引き、チャット上限が近づく場合は、安全な節目で停止し、確認済み範囲・未確認事項・再開手順を両メモへ追記してから別チャットへ移行する。未完了の Cursor 処理を残したまま移らない。
- Git 操作は利用者が行う。

**検索語:** seed/RNG基本設計、route choice keyed randomization、arrival tiebreaker、Link別進入回数、Node訪問番号、signalized UXsim merge、専用merge RNG、apply_copied_tvt_confirmed_ranks、production未実装、専用branch、別branch、別チャット、BATCHレビュー、疑似コード、次の作業

#### 21.9.23 現行BATCH productionレビュー完了と将来大幅改修の基本設計確定

**執筆日:** 2026-11-21

**詳細正本:**

- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28**
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.22**
- seed／RNG 正本は同詳細メモ **§32.21**

**§21.9.22** の「BATCH レビューは未着手」「次は現在のチャットで BATCH を読む」は 2026-11-18 時点の記録である。最新状態は本節を優先する。レビューが完了したのは現行 production の読取りと将来設計の確定であり、production 実装ではない。

**完了:**

- 現行 BATCH production コードの読取り
- trigger 候補と trigger 順位
- t_trigger Level 0／1／2
- Level 2 mimic
- 未到着 Vehicle と、別 inlink の未到着 Vehicle
- candidate 抽出と inlink 順序
- max_batch_size
- service unit、service queue、residual 部分
- clearance と通常物理制約
- 0 台通過時の別 inlink 試行
- reformation
- arrival tiebreaker の同一 Visit 内不変
- TVT-MP baseline の未確定 Visit に対する一時 FCFS の確認
- BATCH 専用メモとの整合確認
- 将来大幅改修の基本設計確定

別 inlink 未到着 Vehicle を service unit へ含め、Level 2 で前進させる現行処理は、専用メモと整合していた。未到着 Vehicle の対象 Node 通過後 outlink が通常決定済みである、とは一般化しない。

**将来設計要約:**

- 全 World 仮想計算。Node 間相互作用を維持する
- T-1 までの既存 BATCH を維持する
- T 以後の仮想 World では新規 BATCH を形成しない
- 未割当 Vehicle は一時 FCFS。正式順位台帳へは書かない
- Node ごとに到着順位 1 位の trigger から 1 つの t を得る
- 同時到着 2 位以下に個別 t を設けない
- horizon 30。全 trigger 解決後に早期終了する
- unresolved は Level 1 fallback。新方式では Level 0 fallback は使わない（clearance=0・clearance=1 いずれも新 Level 1 の t は horizon 30 以内）
- clearance=0 では新 Level 1 の t は常に 1（通過 T+1、対象距離 0）
- clearance=1 では新 Level 1 の t は 1 または 2
- clearance=0 かつ t=1 では対象距離 0。1 つの BATCH は到着済み・未割当 Vehicle 1 台で構成（Node 端未到着後続を距離条件で追加しない）
- 対象距離 = (t-1)×DELTAT×u。時刻 T の実 World 位置を使う
- 1 台 BATCH は max_batch_size >= 1 で常に上限以下。max_batch_size=1 では各 BATCH の Vehicle 数は上限に等しい
- N=1 BATCH 対 FCFS 完全一致性を将来の全 World 仮想計算型 BATCH 改修後も回帰検証する（同一 clearance、候補順位、network、需要、seed 等で比較。現行確認済み基準の回帰）
- `earliest_arrival_timestep` を新形成範囲に使用しない
- 同時到着 Vehicle と仮想計算中に順位判明する Vehicle は、順位判明後に同じ BATCH 形成規則（判明タイミングのみ異なる）
- max_batch_size で残った Vehicle は翌 timestep の通常再評価。特別な救済はしない
- arrival tiebreaker は再生成しない
- 仮想対実績の予測精度比較はしない。監査は形成手順の再現確認
- seed／RNG 改修を先に実装し、BATCH 大幅改修はその後

仮想 World で T+t までに実際に到着した Vehicle だけを BATCH 構成員にはしない。

**明確な未完了:**

- seed／RNG production 実装
- BATCH 大幅改修の production 実装
- 全 World 仮想計算 runner
- 仮想到着 collector
- 監査出力
- 専用 test
- 独立 trial
- branch 作成
- 30 反復本番

**次の作業:**

1. 3 メモの差分を Terminal で独立確認する
2. 必要なら文書修正する
3. メモだけを commit する。commit 名には document を含め、complete は使わない
4. commit 結果、最新 commit、残存変更を確認する
5. 別指示で push する
6. push 後の status、最新 commit、local／remote 一致を確認する
7. その後、seed／RNG 改修用 branch と別チャットへの移行準備をする
8. seed／RNG 改修を実装・検証する
9. その後に BATCH 大幅改修へ進む

Git 操作は利用者が Terminal で行う。Cursor には行わせない。branch も Cursor は作らない。

**検索語:** BATCHレビュー完了、BATCH大幅改修、全World仮想計算、horizon 30、Level 1 fallback、Level 0不使用、(t-1)×DELTAT×u、arrival tiebreaker不変、max_batch_size、seed改修前、production未実装、次の作業

#### 21.9.24 seed／RNG改修とBATCH大幅改修のbranch分離・現行基準確認・案C採用

執筆日は2026-11-22である。**§21.9.23** と、そこにある「seed／RNG改修を先に実装する」は当時の記録として維持する。本節はそれを否定せず、現行基準の固定とbranch分離を後続判断として追加する。

詳細正本:

`ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md`

関連正本:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21**
- 同 **§32.22**
- 同 **§32.23**
- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28**
- 同 **§1H.29**

- 案Cを採用した。現行基準確認を先に実施し、その後seed／RNG改修をBATCH大幅改修より先に行う。
- 2026-11-22に200、1,000、5,000台のFCFS対N=1 BATCH Level 2を再確認し、全て exact_match だった。集計不一致0、Vehicle-level不一致0。
- 5,000台は Level 2 call 46428、resolved 46390、unresolved 38、fallback 38 を含めて完全一致した。
- 10,000台は過去exact_match実績であり、今回は未実行である。200台だけで完了したとは扱わない。
- 現行基準固定は完了した。
- seed／RNG production実装は未着手である。
- BATCH production大幅改修は未着手である。
- branch作成は未実施である。
- seed／RNG専用branchを先に作成する。現在のproduction branchへ直接実装しない。
- seed／RNG受入れ済みcommitからBATCH専用branchを作成する。旧seed基準から直接派生させない。両改修を同じbranchで連続実装しない。
- 現行BATCHを保全し、新BATCHは採否評価前に正式置換しない。`order_control_type="batch"` を黙って新方式へ置換しない。新BATCHは未実装・未採用の評価候補である。正確性または性能が不足すれば現行BATCHを継続採用できる。恒久runtime併存は未確定である。
- baseline collectorの既知test契約不一致（`test_batch_passage_stops_before_physical_transfer_on_inconsistency`、visit_id mismatch期待と現行collector契約の不一致。記録は `ORDER_EXCHANGE_PROGRESS_3.md`）は未解決であり、今回のexact_matchで解決とはしない。
- 30反復本番へは進まない。
- 性能はN=1一致性の合否条件にしない。5,000台の時間短縮の全てをshort TMAXだけの効果とは断定しない。固定printの assignment／visit_id／service unit 表示を実構造比較の結果としない。
- 現行branchは `feature/intersection-order-control`。記録作成前の最新commitは `4c6d9da`。local HEADとremoteは一致確認済みだった。無関係な作業ツリー変更・未追跡ファイルには触れない。

**次の作業:**

1. Markdown差分をTerminalで独立確認する
2. 必要なら文書修正する
3. 対象Markdownだけを明示してstageし、commitする
4. commit結果、最新commit、残存変更を確認する
5. pushはcommit確認後の別指示で行う
6. push後にgit status、最新commit、local／remote一致を確認する
7. その後、seed／RNG専用branchを作成する前のGit状態を確認する

Git操作は利用者がTerminalで行う。CursorにはGit操作をさせない。branchもCursorは作らない。利用者への作業指示は、その時点で次に実行する内容だけを提示する。

**検索語:** seed改修順序、RNG改修順序、BATCH改修順序、案A、案B、案C、現行基準固定、N=1 BATCH、FCFS完全一致、exact_match、200台、1000台、5000台、10000台、fallback 38、Level 2、short TMAX、branch分離、seed branch、BATCH branch、分岐元commit、現行BATCH保全、旧BATCH維持、新BATCH試作、新旧横並び、同一commit比較、production未統合、不採用、性能不十分、正確性不合格、採否判断、全World仮想計算、baseline collector、visit_id mismatch、未解決test、production未実装、branch未作成、30反復未着手、次の作業

#### 21.9.25 4方式共通seed／RNG基盤の具体実装前調査・反証・独立確認完了

執筆日は2026-11-22である。**§21.9.24** の「branch 作成は未実施」「現行 branch は `feature/intersection-order-control`」は、その節の時点の記録として残す。本節時点では seed／RNG 改修 branch は作成済みである。

詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§14** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.24** である。研究契約は同 **§32.21**、branch 分離と案 C は同 **§32.23** と本メモ **§21.9.24**、将来 BATCH は同 **§32.22** と BATCH 詳細 **§1H.28** である。本節はそれらを覆さない。

- 原典調査は完了した。対象は World 初期化、origin 生成、BATCH 実通過、両 FCFS、共通物理移動、通常 merge、Vehicle の route choice と到着記録、baseline の dill fork、Candidate の copy、局所前進、binding 通過、Level 2 mimic、Candidate 選択の既存 seed material、および影響する既存 test 群である。
- Cursor の読取り専用反証レビューは完了した。判定は「条件を追記すれば実装へ進める」だった。blocking 反例はなかった。high 相当の条件補正は4件だった。`random_seed=None` の entropy を用途別に再生成しないこと、最終候補 0 件を成功経路にしないこと、Link 進入回数の合計 0 を訪問番号 1 へ補正しないこと、通常 merge 用 RNG を signalized 専用と呼ばず `_transfer_normal_merge()` の非 hard deterministic 分岐に置くこと、である。
- Level 2 と Candidate 局所計算は、利用者が Terminal で独立確認した。
- 独立確認のあと、Candidate 局所 binding 通過について1件補正した。局所 World 内で outlink へ物理進入したら、その局所 World の Link 進入状態を更新する。outlink 上を下流端まで処理し、下流端では退出、sink 相当として扱う。下流 Node へ通常進入させず、新しい Node Visit と通常 route choice は発生させない。Cursor の「当座の到着計算には helper が必須ではない」は、helper を付けない理由にはしなかった。
- seed／RNG 改修を BATCH 大幅改修より先に行う案 C は維持する。順序を変える反例はなかった。単一の保存済み内部 entropy を、route choice、arrival tiebreaker、通常 merge 用 RNG の共通の基礎とする。現行 Level 2 へ新しい Link 進入回数と attempt を追加コピーしない判断は、局所通過時刻推定に限定された mimic の例外であり、Candidate 局所 World や将来の全 World 型 BATCH へ一般化しない。
- 次の直接実装では、初心者が追える明示的な Python を優先する。
- production の seed／RNG 実装は未着手である。production コード、test、診断は変更していない。simulation は実行していない。
- current branch は `feature/common-seed-rng-foundation` である。分岐元 commit は `fde6865` である。remote push は未実施である。無関係な既存変更と未追跡ファイルには触れない。
- 既知の baseline collector test 契約不一致は、今回解決済みにしない。

**次の作業:**

次の直接作業は、今回の Markdown 差分を利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書修正、対象 Markdown だけの stage と commit、commit 結果と最新 commit と残存変更の確認、push は別指示、push 後の status と最新 commit と local／remote 一致の確認、その後に内部 entropy と pure keyed helper の最小実装単位へ進むことである。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** seed RNG具体実装前調査、Cursor反証、Terminal独立確認、blockingなし、条件付き成立、random_seed None、内部entropy、単一entropy、stable hash、keyed randomization、pure function、domain separator、origin attempt、in-trip attempt、候補0件、候補1件、候補2件以上、Link別進入回数、Node訪問番号、合計0不整合、arrival tiebreaker、通常merge RNG、signalized専用ではない、_transfer_normal_merge、baseline全World、Candidate局所World、Candidate binding通過、outlink下流端、sink相当、下流Nodeへ通常進入しない、Candidate rollback、現行BATCH Level 2、mimic、追加コピー不要、N=1 BATCH、FCFS完全一致、fallback 38、旧seed結果非互換、production未実装、test未変更、次の作業、seed改修前に確認したこと、RNG実装前の問題、CandidateでLink回数を増やすか、BATCH Level 2に新状態をコピーするか、merge乱数をどこへ分けるか、random_seedがNoneのとき、route choice候補が0件のとき、arrival tiebreaker再訪、Node訪問番号が0、FCFSとN=1 BATCHが一致しなくなった、seed改修のテスト範囲、feature/common-seed-rng-foundation、fde6865

#### 21.9.26 内部entropy保存とpure keyed helperの最小実装・反証・受入れ完了

執筆日は2026-11-22である。**§21.9.25** の「production の seed／RNG 実装は未着手」は、その節の時点の記録として残す。本節は最初の実装単位が終わったあとの進捗である。

詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§15** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.25** である。研究契約 **§32.21** と実装前設計 **§32.24**、実装前進捗 **§21.9.25** は変更していない。

- production は2ファイルである。`uxsim/uxsim.py` と `uxsim/common_seed_rng_keyed_uniform.py` である。
- 専用 test は1ファイルである。`tests_common_seed_rng_keyed_uniform.py` である。
- 実装範囲は、`World.__init__()` で `W._common_seed_rng_internal_entropy` を1回保存することと、正規化済み entropy、非空 domain、非空 key tuple から `[0, 1)` の一様値を返す pure helper だけである。serialization version 1、SHA-256、上位53 bits を `2**53` で割る変換を含む。`W.rng` と `W.order_control_rng` は消費しない。
- 初回は専用 test 19件、`py_compile`、既存 RNG test、World copy の1 passed が成功した。6 warnings は既存 warning である。この成功だけでは受入れ完了としなかった。
- Cursor Grok 4.7、effort high の読取り専用反証は完了した。Cursor は編集、test、Git を行っていない。blocking はなかった。判定は小修正後に受入れ可能だった。high は固定ベクトルの欠如と空 key の受理だった。
- 小修正は完了した。空 key を拒否し、NumPy 整数 scalar を1要素 tuple にし、bytes、bytearray、dict、str を反復前に拒否し、非 iterable の `TypeError` を `ValueError` にし、version から prefix を構築した。最終の専用 test は23件である。seed 0、1、7 は `(0,)`、`(1,)`、`(7,)` である。
- 固定ベクトルの転記は2回失敗した。最初の Cursor 記録は79 bytes、production の actual は81 bytes、162 hex characters だった。2回目は Cursor が81 bytes と報告したが実ファイルは80 bytes で、Terminal の `same` は False だった。3回目は Cursor へ依頼せず、利用者が Terminal で actual hex を直接書いて固定した。書込み後は162 chars、81 bytes、`same = True` だった。これは production serializer の欠陥ではない。digest `02b81eccf53766e351c8bc3b042a94a09aa4fcb972b99fcb205ab2793870e199` と53-bit 整数 `95674047571692`、uniform value `0.0106219530473175` は、81-byte 列から Terminal で独立確認済みであり、変更していない。
- 最終の専用 test は成功した。表示は `Common seed/RNG keyed uniform tests passed.` である。
- 既存 RNG test は成功した。表示は `Order-control RNG tests passed.` である。`py_compile` はエラーなし、`git diff --check` は出力なし、過去の World copy は1 passed である。
- route choice、arrival tiebreaker、通常 merge、Vehicle counter、Link 進入 helper、Level 2、Candidate、baseline は未接続のままである。新 BATCH は未実装・未採用である。4方式共通 seed／RNG 改修全体は未完了である。
- 受入れは、blocking がないこと、反証後の限定修正、固定ベクトル、専用 test 23件、既存 RNG 回帰、shared RNG 非消費、対象外を変えていないことによる。test 成功だけを理由にしない。

**次の作業:**

次の直接作業は、今回の Markdown 差分を利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書修正、production 2ファイル、専用 test 1ファイル、対象 Markdown 3ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、次の実装単位である Vehicle 状態と Link 進入 helper へ進む。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** 内部entropy実装、pure keyed helper、common seed RNG、最小実装単位、World内部entropy、_common_seed_rng_internal_entropy、normalize_seed_sequence_entropy、keyed_uniform_value、serialization version 1、FORMAT_PREFIX、SHA-256、53-bit、2の53乗、mutable RNG非消費、W.rng非消費、order_control_rng非消費、空key拒否、NumPy整数scalar、bytes拒否、dict拒否、固定ベクトル、fixed vector、81 bytes、162 hex characters、02b81ecc、95674047571692、0.0106219530473175、固定hex転記失敗、79 bytes、80 bytes、Cursor報告不一致、Terminal直接修正、専用test 23件、既存RNG回帰、World copy、blockingなし、小修正後受入れ、route choice未接続、arrival tiebreaker未接続、normal merge未接続、Vehicle counter未実装、次の作業、seed RNGの最初の実装、固定値testが失敗した、serialization hexが足りない、Cursorの修正報告と実ファイルが違う、entropyをどこへ保存したか、shared RNGを消費しない乱数、route choice接続前の基盤、次の実装単位、feature/common-seed-rng-foundation、fde6865

#### 21.9.27 Vehicle状態とLink物理進入helperの実装・反証・受入れ完了

執筆日は2026-11-23である。**§21.9.26** は前の実装単位の進捗として残す。詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§16** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.26** である。研究契約 **§32.21**、実装前設計 **§32.24**、前単位 **§32.25** と **§15**、実装前設計 **§14** の本文は変更していない。

- production は 2 ファイルである。`uxsim/uxsim.py` と `uxsim/order_control_tvt_mp_candidate_binding_transfer.py` である。
- 専用 test は新規 1 ファイルである。`tests_vehicle_link_entry_state.py` である。既存 test へ足すと責務がぼやけるため、root-level の新規ファイルにした。
- Vehicle の 3 状態は、`link_entry_count_by_link_name`、`current_link_route_choice_attempt_count`、`origin_route_choice_attempt_count` である。Link 別進入回数の key は正式 Link 名である。初期値は空 dict と 0 と 0 である。dict は Vehicle ごとに別 object である。
- 共通 helper は `Vehicle.record_successful_physical_link_entry()` である。現在 Link 名の回数を 1 増やし、current Link attempt を 0 に戻す。origin attempt は変えない。`link is None` は `ValueError` である。Visit 開始の内部へは入れていない。
- 通常 production の 5 経路は、origin の `Node.generate()`、BATCH 実通過の `_transfer_vehicle`、`transfer_fcfs_no_clearance()`、`transfer_fcfs_clearance()`、`_transfer_one_vehicle_between_links()` である。通常 merge と TVT-MP 確定順位は、最後の共通関数を 1 回呼ぶ。6接続は Link 代入のあと、Visit 開始の前である。`uxsim.py` の call site は 5 箇所である。
- Candidate binding は `_transfer_one_vehicle_like_uxsim()` の 1 箇所である。局所 World の outlink 進入だけを記録し、real Vehicle へ戻さない。共有関数のため、unbound 局所 FCFS も同じ正式な局所進入として更新される。これは契約違反ではない。
- Level 2 は非接続である。`_transfer_vehicle_reference` も、mimic への追加コピーも、Visit 開始の内部も接続していない。mimic は初期値の空 dict と attempt 0 のままである。この例外を Candidate や将来の全 World 型 BATCH へ一般化しない。
- Candidate 局所前進は非接続である。正式関数は `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` である。同一 inlink 上の前進と到着登録であり、3 状態は変えない。
- 専用 test は 17 件である。helper 直接呼出しだけで正式経路を証明していない。origin、BATCH、両 FCFS、共通移動、通常 merge、loop は正式経路である。Level 2 は実動作と source-level の両方である。source-level だけを受入れ根拠にしない。
- 初回は `py_compile` 成功のあと、`test_level2_reference_transfer_does_not_record_link_entry` が `'_mimic_up_link1' is not Node in this World` で失敗した。production 欠陥ではなく、通常 merge network を mimic に流用した fixture 不整合である。test へ `_build_level2_mimic_world_for_real_merge` を追加し、`_mimic_up_link1` から `merge`、`merge` から `_mimic_sink_out` を置いた。production は変えていない。修正後の表示は `Vehicle link-entry state tests passed.` である。
- 既存回帰は、Candidate binding 21 件 `binding transfer scan tests passed (21 tests).`、BATCH transfer `Order-control batch transfer tests passed.`、FCFS transfer `FCFS order control transfer test passed.`、Level 2 reference 20 件 `All 20 Level 2 reference tests passed.` である。単一 call 0.20 ms は参考値であり、性能合否には使わない。存在しない `tests_order_control_batch.py` と `tests_order_control_fcfs.py` の `No such file or directory` は、ファイル名の誤りであり、実装 test の失敗ではない。
- Cursor Grok 4.7、effort high の読取り専用反証は、編集、test、`py_compile`、simulation、Git を行っていない。判定は、このまま受入れ可能である。blocking はない。high はない。medium は、Candidate 局所前進 test が Level 2 の `_advance_inlink_vehicles` を呼んでいたことと、AST が間接呼出しを見逃し得ることである。production の局所前進契約は成立していた。
- test だけを修正した。正式関数 `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` を呼ぶ。local Vehicle は同じ `link1`、回数は `{"link1": 1}`、current attempt は 4、origin attempt は 2、real Vehicle も不変である。test 数は 17 のままである。Terminal で import と正式関数呼出しを独立確認した。`git diff --check` の出力はなく、再実行の表示は `Vehicle link-entry state tests passed.` である。
- route choice keyed 化、attempt 増分、arrival tiebreaker keyed 化、通常 merge 用 RNG、N=1 完全一致、4方式統合回帰、performance 確認は未実装である。新 BATCH は未実装・未採用である。4方式共通 seed／RNG 改修全体は未完了である。広範な simulation と benchmark と N=1 回帰は実行していない。
- 受入れは、経路網羅、二重計上なし、失敗時非接続、Level 2 と局所前進の非接続、専用 17 件、直接関係する既存回帰、blocking／high なし、test 対象誤りの修正後の再検証による。test 成功だけを理由にしない。

**次の作業:**

**§14.17** の順序を再確認した。次の実装単位は origin と in-trip route choice の keyed 化である。

次の直接作業は、今回の Markdown 差分を利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書修正、production 2 ファイル、専用 test 1 ファイル、対象 Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、origin と in-trip route choice の keyed 化へ進む。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** Vehicle状態、Link進入回数、link_entry_count_by_link_name、current_link_route_choice_attempt_count、origin_route_choice_attempt_count、record_successful_physical_link_entry、物理進入成功、Link名key、正式Link名、origin進入、BATCH実通過、FCFS clearanceなし、FCFS clearanceあり、_transfer_one_vehicle_between_links、Candidate binding、Candidate unbound FCFS、Candidate局所前進非接続、Level 2非接続、_transfer_vehicle_reference、begin_order_control_visit_on_link_entry、helperをVisit内部へ入れない、二重計上なし、進入失敗非接続、loop再進入、World copy、dict非共有、Level 2 fixture、_mimic_up_link1、_mimic_sink_out、Candidate局所前進test対象誤り、advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals、専用test 17件、Candidate binding 21件、BATCH transfer、FCFS transfer、Level 2 reference 20件、blockingなし、highなし、route choice未接続、attempt増分未実装、arrival tiebreaker未実装、normal merge RNG未実装、次の作業、feature/common-seed-rng-foundation、ef008ce、VehicleがLinkへ何回入ったか、同じLinkへ再進入した回数、新しいLinkへ入るとattemptが0になる、origin attemptをresetしない、CandidateでLink回数を増やすか、Level 2でLink回数を増やすか、Link進入helperの接続漏れ、Link進入回数が二重になった、Candidate局所前進でcounterが変わった、Level 2 mimicへcounterをコピーするか、test名と実際の関数が違った、_mimic_up_link1がない、Vehicle状態実装後の次作業

#### 21.9.28 origin・in-trip route choice keyed化の実装・反証・受入れ完了

執筆日は2026-11-23である。**§21.9.27** は前の実装単位の進捗として残す。詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§17** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.27** である。研究契約 **§32.21**、実装前設計 **§32.24**、前単位 **§32.25**、**§32.26**、**§15**、**§16**、実装前設計 **§14** の本文は変更していない。

- production は 2 ファイルである。`uxsim/uxsim.py` と、新規 `uxsim/common_seed_rng_route_choice.py` である。category helper は、keyed uniform の hash から route choice の候補契約を分け、public API へ出さず、World も Vehicle も変えない。
- 専用 test は新規 1 ファイルである。`tests_common_seed_rng_route_choice.py` である。候補分岐、hard deterministic、specified route、copy、順序、helper 境界、loop 再進入を、既存の keyed uniform test と Link 進入 test へ混ぜない。
- domain は origin が `origin_route_choice`、in-trip が `in_trip_route_choice` である。両者は共有しない。arrival tiebreaker とも通常 merge とも共有しない。自由文字列の domain API にはしない。
- origin key は `(veh.name, origin_node.name, origin_route_choice_attempt_count)` である。正式名を使い、object identity と整数 ID は使わない。
- in-trip key は `(vehicle.name, current_link.name, link_entry_count, current_link_route_choice_attempt_count)` である。`order_control_visit_id` は使わない。missing と 0 は 1 へ補正しない。
- 候補 0 件は、outlink があるのに prefer／avoid 後に空なら `ValueError` であり、draw も attempt 増分もなく、既存の `route_next_link` は消さない。Node 自体に outlink がない dead-end は `route_next_link = None` であり、attempt は増えない。候補 1 件は直接選択で、draw も attempt 増分もない。候補 2 件以上だけが pure keyed uniform を使い、選択成功後に attempt を 1 増やす。合計 0 は等確率である。
- origin は、選択成功後、入口判定より前に attempt を増やす。容量不足でも戻さない。同じ `generate()` では再抽選しない。次 timestep は次の attempt である。in-trip は `route_next_link` の保存後に増やす。同じ Link 終端の次 timestep は次の attempt である。新 Link 進入で 0 に戻るのは in-trip attempt だけである。方式間で待ち timestep 数が違えば、通過時の attempt は異なり得る。揃えるのは同じ attempt 番号の uniform である。N=1 完全一致は統合回帰である。
- 確率的 route choice は `W.rng` も `W.order_control_rng` も消費しない。Python `random`、built-in `hash()`、新しい Generator も使わない。具体 Link と shared RNG の消費順は、旧 seed 結果と非互換になり得る。候補集合、順序、preference 比、合計 0、hard deterministic、specified route、dead-end、route progression、候補 1 件の決定論性は維持する。
- hard deterministic は最大 preference、同点は先頭、attempt なしである。specified route は origin が先頭、in-trip が既存の `log_t_link` 索引であり、attempt なしである。空 list の既存 `IndexError` は今回の単位外である。
- 初期専用 test は 18 件である。期待 Link は明示 key と test 側の累積規則であり、uniform 小数は固定していない。
- 初回は `py_compile` 成功のあと、`test_in_trip_zero_final_candidates_does_not_increment_attempt` が `AttributeError: 'Vehicle' object has no attribute 'route_next_link'` で停止した。18 件全体はその時点では未確定である。`route_next_link` は常設属性ではなく、0 件の `ValueError` は属性を変えない。test が例外前の既存値を置かなかった fixture 不備であり、production 欠陥ではない。0 件、missing、zero の各 test で、同一 World の実在 Link を sentinel にした。修正後の表示は `Common seed/RNG route choice tests passed.` である。`but that link has no` と `The count is` は、Terminal の `grep -F` で実ファイルは正しく、修正不要だった。
- 既存回帰は、`python tests/test_verification_route_choice.py` がエラー、Traceback、標準失敗出力なしで終了したこと、keyed uniform が `Common seed/RNG keyed uniform tests passed.`、Link 進入状態が `Vehicle link-entry state tests passed.` である。route choice 検証 script は成功メッセージを出さない。
- Cursor Grok 4.7、effort high の読取り専用反証は、編集、test、`py_compile`、simulation、Git を行っていない。判定は、このまま受入れ可能、である。blocking はない。high はない。medium は、登録順と名前順が同じこと、RNG 比較では helper 非呼出しを証明できないこと、loop の手動 counter、helper 境界が 18 件に無いこと、である。古い `Vehicle.__init__()` comment は low に含まれた。
- 反証後の補強は 4 点である。production の route choice 処理は変えていない。候補順序 test `test_prefer_uses_link_name_order_not_registration_order` は、登録順 `z_link`、`a_link` と名前順 `a_link`、`z_link` の期待 Link が違うことを `generate()` 前に assert し、結果は名前順、attempt は 1、両 RNG は不変である。avoid の sort は同じ構造の読取りであり、重複 test はない。helper の異常値 test と境界 test を追加した。最後の候補 remainder の直接 test はない。`test_loop_reentry_changes_the_in_trip_uniform` は同名置換であり、追加件数ではない。`feeder`、`loop_in`、`hop`、`return_feeder`、再進入の `loop_in` を、`_transfer_one_vehicle_between_links()` と `route_next_link_choice()` で確認する。回数 1 から 2、attempt の増加と 0 戻し、回数 2 の key、visit id は 0、origin attempt は 0、RNG 不変である。comment は現在の増分と reset に合わせ、属性名と初期値は変えていない。
- 最終専用 test は 21 件である。初期 18 件に追加 3 件を足した。`py_compile` 成功、表示は `Common seed/RNG route choice tests passed.`、`git diff --check` の出力はなかった。helper と route choice 処理は反証後に変更していない。
- 受入れ範囲は、origin と in-trip の keyed 化、category helper、attempt 増分、候補別分岐、mutable RNG 非消費である。test 成功だけを理由にしない。4方式共通 seed／RNG 改修全体は未完了である。
- 未実装は、arrival tiebreaker keyed 化、Node 訪問番号の production 利用、通常 merge 用 RNG、`_transfer_normal_merge()` の乱数変更、Candidate selection RNG、N=1 完全一致、4方式統合回帰、hash 性能、taxi 専用 test、specified route の複数 Link、baseline と Candidate の full simulation、performance benchmark である。新 BATCH は未実装・未採用である。
- 実装完了までの現在地は、完了が内部 entropy、Link 進入状態、origin・in-trip route choice の 3 単位である。残りは、arrival tiebreaker と Node 訪問番号、通常 merge 用 RNG、N=1 と 4方式統合回帰、最終正本と全体受入れである。次の実装単位のあと、主要 production 接続の残りは通常 merge 用 RNG と統合回帰になる。

**次の作業:**

次の直接作業は、今回の Markdown 差分を利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書修正、production 2 ファイル、専用 test 1 ファイル、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、arrival tiebreaker の keyed 化と Node 訪問番号の production 利用へ進む。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** origin route choice keyed化、in-trip route choice keyed化、origin_route_choice、in_trip_route_choice、origin_route_choice_attempt_count、current_link_route_choice_attempt_count、link_entry_count_by_link_name、Vehicle正式名、origin Node正式名、current Link正式名、累積進入回数、explicit key、pure keyed uniform、common seed RNG、candidate 0件、candidate 1件、candidate 2件以上、dead-end、prefer、avoid、Link名順、登録順、route preference、合計0、等確率、hard deterministic、specified route、mutable RNG非消費、W.rng非消費、W.order_control_rng非消費、select_route_choice_candidate、World copy、baseline fork、Candidate非接続、Level 2非接続、初回fixture失敗、route_next_link未作成、AttributeError、sentinel Link、専用test 18件、反証、blockingなし、highなし、候補順序test、helper境界test、正式loop再進入、専用test 21件、Common seed/RNG route choice tests passed、tests/test_verification_route_choice.py、keyed uniform回帰、Vehicle Link進入状態回帰、arrival tiebreaker未実装、Node訪問番号未利用、normal merge RNG未実装、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、3a4c3ee、originでどの乱数を使うか、Link終端で毎timestep経路を再選択する、capacity不足でorigin attemptを戻すか、同じLinkでroute choiceを何回試したか、loop再進入で同じ乱数になるか、candidateが1本なら乱数を使うか、candidateが0本ならどうなるか、preference合計0ならどう選ぶか、preferとavoid後の順序、登録順とLink名順、hard deterministicでattemptが増えるか、specified routeでattemptが増えるか、W.rngを経路選択で消費するか、baseline copyで同じ経路選択になるか、Candidateで通常route choiceを行うか、Level 2でroute choiceを行うか、route_next_linkのfixtureが失敗した、test名と実際の対象、route choice実装後の次作業、実装完了までの残り区分

#### 21.9.29 arrival tiebreaker keyed化とNode訪問番号のproduction利用の実装・反証・受入れ完了

執筆日は2026-11-23である。**§21.9.28** は前の実装単位の進捗として残す。詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§18** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.28** である。研究契約 **§32.21**、実装前設計 **§32.24**、前単位 **§32.25**、**§32.26**、**§32.27**、**§15**、**§16**、**§17**、実装前設計 **§14** の本文は変更していない。

- production は `uxsim/uxsim.py` と、新規 `uxsim/common_seed_rng_arrival_tiebreaker.py` である。helper は Node 訪問番号と arrival key だけを持ち、World、Vehicle、Visit を変えず、public API へ出さない。route choice helper と hash helper とは責務を分ける。
- `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py` は、production 処理ではなく、古い説明コメント 4 行だけを更新した。動作変更ではない。
- 専用 test は新規 `tests_common_seed_rng_arrival_tiebreaker.py` の 19 件である。既存 `tests_order_control_current_visit_arrival.py` は 13 件のまま更新した。削除は無い。
- domain は `arrival_tiebreaker`、定数は `ARRIVAL_TIEBREAKER_DOMAIN` である。origin、in-trip、通常 merge と共有しない。自由文字列の domain API にはしない。初回と再訪で同じ domain である。
- Node 訪問番号は `node_visit_number_from_link_entries` である。対象 Node の全 inlink について、正式名の累積進入回数を合計する。missing は 0、個別の 0 は許容、合計 0 は 1 へ補正しない。負値、bool、float、str は拒否する。現在 Link だけ、Visit ID、arrival log、`log_t_link`、新しい Node counter は使わない。
- arrival key は `(vehicle.name, node.name, node_visit_number)` である。正式名を使い、object identity、整数 ID、timestep、到着時刻、inlink 名、方式名、World 名は入れない。
- 初回は訪問番号 1 で、current Visit と legacy 初回台帳へ保存する。再訪は 2 以上で、current Visit だけを更新し、legacy は上書きしない。同じ helper であり、mutable RNG は使わない。
- 保存先の正本は current Visit である。legacy は Node 名を key にした初回だけの互換台帳である。到着前は両方 `None` である。同じ Visit では再生成しない。FCFS rank と BATCH trigger rank は current Visit を読む。
- 生成は `W.rng.random()` も `W.order_control_rng.random()` も使わない。通常 merge の `W.rng`、route choice、Candidate selection RNG は未変更である。旧 trial の tiebreaker 一致は要求しない。
- baseline copy は entropy、進入回数、current Visit を引き継ぎ、same event なら same tiebreaker である。開始 timestep は key に入らない。collector は保存済み値を受け取り、別の乱数は引かない。
- Candidate 局所前進は、新規到達 Vehicle について既存の `record_order_control_node_arrival(target_node)` を呼ぶ。進入回数は copy 済みの値を使い、局所前進では増やさない。binding 後の outlink 退出は新しい Node arrival にしない。real World へ戻さない。Level 2 は recorder を呼ばず、この非接続を将来の全 World 型 BATCH へ一般化しない。
- 専用 19 件は初回から成功し、表示は `Common seed/RNG arrival tiebreaker tests passed.` である。期待値は明示 key から作り、固定小数は書いていない。再訪 test は Visit ID 9 と訪問番号 2 をずらす。Candidate／Level 2 の一部は source-level であり、full 実動作 fixture と collector 実動作は 19 件に含まない。
- 既存 13 件の初回再実行は `test_revisit_tiebreaker_reproducible_for_same_seed` で停止した。観測差は actual 約 0.350942、desired 約 0.241633 である。Vehicle 名が `veh_repro_1` と `veh_repro_2` で、key に正式名が入るため異なる値になった。production 欠陥ではなく、同じ event の fixture が同じ key を作っていなかった。両名を同じ `veh_repro` へ揃え、World 名と object は別のままにした。production は変えていない。修正後の表示は `Order-control current visit arrival tests passed.` である。
- 更新した既存 3 件は、初回が訪問番号 1 の明示 key、改名後の `test_first_visit_tiebreaker_uses_keyed_uniform_without_consuming_rng_streams`、再訪が `link1` 1 と `link2` 1 から訪問番号 2 の明示 key、である。旧 `W.rng` と `W.order_control_rng` の期待値は削除した。両 stream の非消費を確認する。
- 交差回帰は、keyed uniform が `Common seed/RNG keyed uniform tests passed.`、Link 進入状態が `Vehicle link-entry state tests passed.`、route choice が `Common seed/RNG route choice tests passed.` である。`py_compile` は成功した。
- Cursor Grok 4.7、effort high の読取り専用反証は、編集、test、`py_compile`、simulation、Git を行っていない。判定は、このまま受入れ可能、である。blocking は無い。high は無い。low は、古い「one candidate RNG」コメント、caller の無い legacy helper、collector 例外後の既存順序、legacy の有無と訪問番号の別管理、である。受入れ前の追加修正と追加回帰は必須としなかった。
- その後、Candidate コメント 4 行だけを、current Visit、初回 legacy、one keyed arrival value、snapshot 復元へ更新した。`one candidate RNG` は消えた。処理、snapshot 位置、rollback、呼出し位置は変えていない。`git diff --check` の出力は無かった。追加 test は不要である。
- 受入れ範囲は、Node 訪問番号、arrival key、初回と再訪の keyed tiebreaker、current Visit、legacy 初回台帳、mutable RNG 非消費、Candidate 既存接続、である。test 成功だけを理由にしない。4方式共通 seed／RNG 改修全体は未完了である。
- 未実装は、通常 merge 用 RNG、`_transfer_normal_merge()` の乱数変更、Candidate selection RNG、N=1 完全一致、4方式統合回帰、最終正本と全体受入れ、arrival hash 性能、Candidate と Level 2 の full 実動作回帰、baseline collector の今回単位での追加実行、legacy helper の削除検討、collector 例外後の再通知、である。新 BATCH は未実装・未採用である。
- 実装完了までの現在地は、完了が内部 entropy、Link 進入状態、origin・in-trip route choice、arrival tiebreaker と Node 訪問番号、の 4 単位である。残りは、通常 merge 用 RNG、N=1 と 4方式統合回帰、最終正本と全体受入れ、である。主要 production 接続で残るのは、通常 merge 用 RNG だけである。

**次の作業:**

次の直接作業は、今回の Markdown 差分を利用者が Terminal で全文独立確認することである。

その後の予定は、必要なら文書修正、production 3 ファイル、test 2 ファイル、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、通常 merge 用 RNG の分離へ進む。production 3 ファイルは `uxsim/uxsim.py`、`uxsim/common_seed_rng_arrival_tiebreaker.py`、`uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py` である。test 2 ファイルは `tests_common_seed_rng_arrival_tiebreaker.py` と `tests_order_control_current_visit_arrival.py` である。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** arrival tiebreaker keyed化、arrival_tiebreaker、ARRIVAL_TIEBREAKER_DOMAIN、Node訪問番号、node_visit_number_from_link_entries、arrival_tiebreaker_key_parts、Vehicle正式名、Node正式名、全inlink合計、累積進入回数、同一inlink再進入、別inlink再訪、parallel Link、missing 0、合計0、0を1へ補正しない、invalid count、bool拒否、float拒否、str拒否、pure keyed uniform、common seed RNG、current Visit、legacy first-arrival、初回台帳、再訪非上書き、同じVisit再生成なし、arrival成立前未生成、W.rng非消費、W.order_control_rng非消費、初回と再訪、明示key、World copy、baseline fork、baseline collector、Candidate局所前進、Candidate binding非接続、Level 2非接続、専用test 19件、既存test 13件、fixture不備、veh_repro_1、veh_repro_2、veh_repro、異なるVehicle名、same event key、blockingなし、highなし、one candidate RNG、keyed arrival value、Candidateコメント修正、Common seed/RNG arrival tiebreaker tests passed、Order-control current visit arrival tests passed、keyed uniform回帰、Vehicle Link進入状態回帰、route choice回帰、normal merge RNG未実装、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、58521aa、到着順の乱数、同着順位をどう決めるか、同じNodeへの何回目の訪問か、Node訪問回数の数え方、同じinlinkへ再進入した場合、別inlinkから同じNodeへ戻る場合、到着時にW.rngを消費するか、初回到着と再訪で別の乱数か、current Visitと初回台帳の違い、同じVisitでtiebreakerを作り直すか、Candidateでarrival tiebreakerを作るか、Level 2でarrival tiebreakerを作るか、baseline copyで同じtiebreakerになるか、Vehicle名が違うと別の値になるか、same seedなのに結果が違った、fixtureのVehicle名が違った、candidate RNGという古いコメント、arrival実装後の次作業、実装完了までの残り区分

#### 21.9.30 通常merge用RNG分離の実装・反証・受入れ完了

執筆日は2026-11-23である。**§21.9.29** は前の実装単位の進捗として残す。詳細正本は `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md` **§19** である。全体設計の接続は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.29** である。研究契約 **§32.21**、実装前設計 **§32.24**、前単位 **§32.25** から **§32.28**、**§15** から **§18**、実装前設計 **§14** の本文は変更していない。

- production 変更は `uxsim/uxsim.py` だけである。新規 module は作っていない。Generator を World 属性として明示し、初期化を数行にし、状態を隠さず、`World.copy()` の pickle で現在 state を継承するためである。
- 新規 test は `tests_common_seed_rng_normal_merge.py` の 18 件である。既存の keyed uniform、Link 進入、route choice、arrival、current-visit arrival の test は変更していない。
- World 属性は `normal_merge_rng` である。型は NumPy `Generator` である。通常 merge 専用の逐次 RNG であり、pure keyed uniform ではなく、merge event key も無い。
- seed 派生は、保存済み `_common_seed_rng_internal_entropy` と固定 `spawn_key=(1,)` である。局所変数は `ordinary_merge_seed_sequence` である。`SeedSequence(None)`、`hash()`、World 名、object identity、`W.rng` の state、route choice と arrival の domain は使わない。entropy 保存の直後に 1 回だけ作り、`finalize_scenario()`、`exec_simulation()`、copy 復元では作り直さない。公開 `random_seed` の後書き込みでも再 seed しない。baseline 開始 timestep は seed に入らない。
- stream 分離は、`W.rng` が spawn key なし、`W.order_control_rng` が既存の `spawn(1)[0]` のまま、`normal_merge_rng` が `spawn_key=(1,)` である。3 本は別 object、別初期系列である。同じ明示 seed なら World 名が違っても初期 state は同じである。異なる seed なら代表系列が異なる。`spawn_key=(1,)` の番号は **§14** で事前固定されていない。現在は衝突せず、将来の同じ entropy と同じ key の再利用は禁止である。これは low であり、受入れは妨げない。
- `_transfer_normal_merge()` は、非 hard deterministic の `W.rng.shuffle(outlinks)` と `W.rng.choice(...)` を、`W.normal_merge_rng` の同じ 2 呼び出しへ置き換えただけである。候補形成、重複除去、lane 複製、shuffle 位置、downstream space、inflow、Node flow、先頭車両、`route_next_link`、signal、outflow、merge priority、合計 0 の均等重み、choice 位置、clearance、transfer、cleanup、反復は維持している。
- 非 hard deterministic では、outlink が 0 件でも 1 件でも shuffle を 1 回呼び、通過可能車両が 1 件でも choice する。0 件の通過可能車両、signal 不一致、capacity 不足では choice しない。clearance は choice のあとで、未充足でも消費済みであり、巻き戻さない。複数 outlink や lane では条件を満たす各回に choice する。消費回数は削減していない。
- hard deterministic では shuffle も choice も無く、3 本とも不変である。最大 merge priority を選び、同点は既存順である。
- `World.copy()` は現在 state を別 Generator として引き継ぐ。一方だけの消費は他方へ戻らない。実 merge 後の copy も同じである。baseline fork は同じ機構で、初期 seed へ戻さず、専用 merge RNG も無い。same state かつ same merge 順なら same result である。merge event 順が違えば逐次 state が分かれる。これは設計どおりである。baseline full simulation の交通結果は未実行であり、統合回帰時に確認する。
- `Node.transfer()` では FCFS と BATCH が通常 merge の前に return し、time_value は TVT 処理後に return する。それ以外、`order_control_type="none"` の eligible Node と signalized UXsim を含め、通常 merge である。generic baseline fork は、collector があり `apply_copied_tvt_confirmed_ranks is False` のときだけ同じ helper を呼び、**§14.12** どおり `normal_merge_rng` を使う。production の TVT baseline は `True` の確定順位側である。専用 test の time_value は generic fork を通っておらず、test 名は確認範囲より少し広い。これは low であり、機能上の穴ではない。`allowed_vehicles` と clearance を渡す production caller は確認範囲に無い。使う場合も同じ RNG であり、clearance は choice のあとである。N=1 の FCFS と BATCH はこの helper に入らない。
- Candidate 局所前進と binding は通常 merge を呼ばない。copy された属性は未使用であり、real World へ戻さない。Candidate selection RNG とは別である。Level 2 は別 World なので属性はあるが、hard deterministic の自前 reference transfer であり、通常 merge は呼ばない。Level 2 の seed は変えていない。この非接続を将来の全 World 型 BATCH へ一般化しない。
- 専用 18 件は、属性と別 object、同じ seed と違う World 名、異なる seed の複数 draw、3 stream の非干渉、消費後 copy の両方向、実 merge 後の copy、実 `Node.transfer()` と専用系列、複数 outlink の shuffle、priority 重み、合計 0 の均等重み、hard deterministic の非消費、空 outlink の shuffle のみ、候補 1 件でも shuffle と choice、呼出し順による draw 位置の変化、route choice と arrival の非干渉、空の FCFS と collector なし time_value の非消費、signal block、capacity block、である。期待値は test 側の seed と `spawn_key=(1,)` から作り、固定 float は無い。18 件は `TESTS` から実行する。追加の low は、BATCH 実動作 test、2 車線の 2 回 choice、downstream space、clearance 未充足、hard deterministic 同点の専用 fixture が無いことである。受入れ前の追加 test は不要である。
- 交差回帰は利用者の Terminal 確認である。`py_compile` は成功した。表示は、`Common seed/RNG normal merge tests passed.`、`Common seed/RNG keyed uniform tests passed.`、`Vehicle link-entry state tests passed.`、`Common seed/RNG route choice tests passed.`、`Common seed/RNG arrival tiebreaker tests passed.`、`Order-control current visit arrival tests passed.` である。`git diff --check` の出力は無かった。
- Cursor Grok 4.7、effort high の読取り専用反証は、編集、test、`py_compile`、simulation、Git を行っていない。判定は、このまま受入れ可能、である。blocking は無い。high は無い。受入れ前の修正と追加回帰は無い。low は、time_value test 名の広さ、BATCH 実動作 test の欠如、2 車線と space と clearance の専用 fixture の欠如、`spawn_key=(1,)` が事前固定でなかったこと、用語差、docstring の簡略、である。
- 意図した非互換は、shuffle 順、選ばれる Vehicle または inlink、その後の `W.rng`、波及する交通結果である。候補形成、shuffle 位置、priority、確率、signal、先頭、経路、capacity、space、clearance、transfer、hard deterministic、trip end、order-control type は維持する。旧 trial の数値一致は要求しない。
- 受入れ範囲は、`normal_merge_rng`、seed 派生、World copy、shuffle と choice、stream 分離、hard deterministic 非消費、である。test 成功だけを理由にしない。
- 主要 production 接続は揃った。完了は、内部 entropy と pure keyed uniform、Link 進入状態、route choice、arrival tiebreaker と Node 訪問番号、通常 merge 用 RNG、の 5 単位である。これは実装接続の完了であり、研究上の全体受入れ完了ではない。
- 未実装または未実行は、N=1 BATCH 対 FCFS、4方式統合回帰、signalized UXsim を含む交通結果、baseline fork の実 merge 交通結果、Candidate selection RNG、新 BATCH、最終正本記録、全体受入れ、性能測定、である。新 BATCH は未実装・未採用である。N=1 も 4方式統合回帰も、実行済みとは書かない。
- 現在地の残りは、N=1 と 4方式統合回帰、最終正本記録と全体受入れ、である。

**次の作業:**

次の直接作業は、今回の Markdown 差分を利用者が Terminal で全文独立確認することである。

その後の予定は、必要なら文書修正、`uxsim/uxsim.py`、`tests_common_seed_rng_normal_merge.py`、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、N=1 BATCH 対 FCFS と 4方式統合回帰の具体的な実行計画へ進む。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

**検索語:** normal merge RNG、normal_merge_rng、通常merge用RNG、通常合流乱数、逐次RNG、sequential RNG、spawn_key=(1,)、ordinary_merge_seed_sequence、保存済みentropy、stream分離、W.rng分離、W.order_control_rng分離、shuffle、choice、merge priority、合計0、均等重み、候補0件、候補1件、複数候補、hard deterministic、World copy、baseline fork、generic baseline fork、apply_copied_tvt_confirmed_ranks、allowed_vehicles、order-control clearance、clearance未充足、Candidate非接続、Level 2非接続、専用test 18件、Common seed/RNG normal merge tests passed、keyed uniform回帰、Vehicle Link進入状態回帰、route choice回帰、arrival tiebreaker回帰、current-visit arrival回帰、blockingなし、highなし、主要production接続完了、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、a730e08、通常合流はどの乱数を使うか、合流乱数を分離した理由、W.rngを通常mergeで使うか、shuffleは何の乱数か、choiceは何の乱数か、候補1台でも乱数を使うか、候補0台でもshuffleするか、hard deterministicで乱数を使うか、merge priorityが0ならどうするか、signalで通れないとき乱数を使うか、capacity不足でchoiceするか、clearance未充足でも乱数を使うか、World copyで合流乱数はどうなるか、baselineで合流乱数を引き継ぐか、Candidateで通常mergeを使うか、Level 2で通常mergeを使うか、FCFSとBATCHでnormal merge RNGを使うか、time_valueのgeneric fork、merge eventの順序依存、共通seed実装の残り、主要production接続が揃ったか、統合回帰前の状態

#### 21.9.31 共通seed／RNG改修後N=1統合回帰完了と4方式統合回帰の工程訂正

執筆日は2026-11-23である。**§21.9.30** は残す。詳細正本は **§20**、全体設計は **§32.30** である。

- 工程訂正: 利用者は「4方式統合回帰」を提案・承認していない。Copilot が **§15** で具体設計なしに未実装事項へ追加し、**§16** 以降で自己参照的に転記し、正式工程のように格上げしたのは不適切。最新は **§20**・**§32.30**・**§21.9.31** を優先。将来必要なら事前設計と利用者判断。**§32.21**・**§14** に合否基準付き独立工程は無い。tracked に一括正式 script 無し。4方式共通基盤≠4方式一括回帰。必須工程・N=1 同列扱い・自動次工程へ進めない。**§32.21** 研究契約は維持。
- N=1 正式診断は `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py`（**§14.18**）。6×6 grid、36 内部 Node、24 OD、signal なし、seed 0、demand 42、batch_size=1、Level 2、virtual horizon 30、同一 plan、shortcut なし。集計 11・Vehicle 7・名集合・completion order を tolerance なし比較。`exact_match` 以外は script が失敗する。
- 利用者 Terminal 実測: **200** 台 exact_match、全 mismatch 0、200／200 完走、L2 call 1497／resolved 1497／unresolved 0／fallback 0。代表 total travel 32029.0 s、avg travel 160.1 s、avg delay 0.4 s、distance 638800 m、last completed 684 s。補助 `test -eq` エラーは zsh `PIPESTATUS` であり diagnostic 失敗ではない。**1,000** 台 exit 0、exact_match、ログ `/tmp/n1_batch_vs_fcfs_1000_after_common_seed_836b99f.log`。**5,000** 台 exit 0、exact_match、L2 46266／46229／unresolved 37／fallback 37、ログ `/tmp/n1_batch_vs_fcfs_5000_after_common_seed_836b99f.log`。37 件の unresolved・fallback を含め一致。**10,000** 台未実行。
- 改修前 5,000 台 L2 46428／46390／38／38 で exact_match。counter 旧新一致は要求しない。新環境で `FCFS = N=1 BATCH` が契約。fallback 38→37 は欠陥としない。
- **判定:** 共通 seed 改修後 N=1（200・1,000・5,000）完了。他条件一般化・性能・4方式交通一致は示さない。
- **現在地:** 完了に 1〜5 実装単位＋N=1（上述）。未確定は「4方式統合回帰」一括試験全体。未完了は最終正本・全体受入れ・10k／他条件 N=1 の要否判断。新 BATCH 未採用。Candidate selection RNG は改修範囲外。性能は合否外。「残りは 4方式統合回帰」と書かない。
- production・test・diagnostic・research script・output は本記録で変更していない。Cursor は test・simulation・Git を行っていない。

**次の作業:** Markdown 差分の利用者全文独立確認 → 必要なら訂正 → Markdown 3 ファイルのみ stage・commit → push は別指示。利用者判断なしに「4方式統合回帰」へ進まない。候補列挙のみ: 全体受入れ可否、10,000 N=1、別条件 N=1、方式横断確認の新設計。

**検索語:** 4方式統合回帰、工程訂正、具体設計なし、合否基準未確定、正式scriptなし、利用者未承認、§15初出、後続節転記、N=1 BATCH対FCFS、exact_match、200台、1000台、5000台、10000台未実行、aggregate mismatch 0、Vehicle-level mismatch 0、全車完走、completion order、Level 2 call count 1497、Level 2 call count 46266、resolved 46229、unresolved 37、fallback 37、seed改修前fallback 38、新共通seed環境、旧seed結果非互換、grid_n1_level_2_vs_fcfs_check.py、batch_size=1、Level 2、virtual horizon 30、clearance 1、random seed 0、demand seed 42、6x6 grid、strict comparison、toleranceなし、N=1 shortcutなし、feature/common-seed-rng-foundation、836b99f、共通seed改修の全体受入れ、4方式横断確認の事前設計、Copilotによる工程追加、Copilotによる自己参照転記、利用者未提案、利用者未承認、具体設計なしの工程追加、正式工程への不適切な格上げ、責任主体、工程追加の再発防止

#### 21.9.32 共通seed／RNG改修の利用者Terminal原典とCopilot独立監査

執筆日は2026-11-24である。**§21.9.31** は残す。詳細正本は **§21**、全体設計は **§32.31** である。Grok の完了報告は今回の独立監査根拠にしない。根拠は利用者 Terminal の原典出力と、それに対する Copilot 独立監査である。N=1 記録は置き換えない。

- production 原典: 分岐元 `fde6865` から監査開始時 HEAD `87d10fd`。production 6 ファイル、910 行追加・53 行削除。`uxsim/common_seed_rng_arrival_tiebreaker.py`、`uxsim/common_seed_rng_keyed_uniform.py`、`uxsim/common_seed_rng_route_choice.py`、`uxsim/order_control_tvt_mp_candidate_binding_transfer.py`、`uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`、`uxsim/uxsim.py`。確認したのは、既存 `W.rng` と `W.order_control_rng`、entropy 保存、SHA-256 keyed uniform、domain と key の直列化、origin／in-trip route choice、Link 物理進入回数、origin attempt、current-Link attempt、arrival tiebreaker、Node 訪問番号、`W.normal_merge_rng`、BATCH・FCFS・通常 transfer・Candidate binding の進入接続、World copy、generic baseline fork、TVT rank 適用 baseline fork、Candidate local World、Level 2 mimic 境界。route choice と arrival に旧 `W.rng`／`W.order_control_rng` 消費の残存形跡は無し。shuffle と choice は `W.normal_merge_rng`。進入記録は origin、BATCH、FCFS no-clearance、FCFS clearance、共通 transfer、Candidate binding へ接続。Level 2 mimic は新しい実 World の Link 進入 identity を作らず非接続を維持。Candidate local advance も新進入を起こさず非接続。World copy は pickle で entropy、Vehicle 状態、normal merge Generator 状態を複製。この範囲で重大または high 相当の production 欠陥は見つからなかった。将来条件すべての証明とは同一視しない。
- test 独立性: 固定直列化 byte 列、SHA-256 digest、53-bit 固定 vector。route choice 期待値は test 側実装で、production selection helper を期待値に使わない。arrival の Node 訪問番号は test 側の inlink 集計。normal merge 期待 Generator は test 側の `SeedSequence` と `spawn_key=(1,)`。正式経路を通す test がある。source 文字列検査だけで全体合格ではない。独立性を高める構造が確認された。同じ誤りの共有可能性を完全排除したとは書かない。
- 再実行: 専用 6 系統は終了値 0。表示は keyed uniform、Vehicle link-entry state、route choice、arrival tiebreaker、current visit arrival、normal merge の各 passed。既存回帰 9 系統も `set -e` で終了値 0。対象は `tests_order_control_rng.py`、`tests/test_verification_route_choice.py`、FCFS transfer、BATCH service queue、Level 2 reference、Level 2 unarrived reference、BATCH transfer、Candidate binding transfer、Candidate unbound FCFS transfer。production 6 ファイルの `py_compile` は終了値 0。`Traceback`、`AssertionError`、`FAILED`、`ERROR`、`failed:` は該当なし。`grep` 終了値 1 は該当なしであり、test 失敗ではない。
- baseline fixture: 最初の一括は alignment が終了値 1、Candidate local state は `set -e` で未実行。失敗は `test_calls_alignment_once_per_node_in_target_node_order`、`veh_b`、`junction_b`、node visit number 0。`veh_b` は `in_a` 到達後、`_place_vehicle_on_inlink_with_new_order_control_visit()` で上流 time_value Node を通さず `in_b` へ人為配置されていた。`vehicle.link = inlink` と Visit 開始の間に `record_successful_physical_link_entry()` が無く、進入回数 0 のまま Visit だけ始まっていた。production 自然走行の欠陥ではない。0 を 1 へ補正せず、production は緩めない。修正は `tests_order_control_tvt_baseline_fork_alignment.py` のみ。人為配置後・Visit 開始前に正式 helper を 1 回追加。進入回数 1 以上と in-trip attempt の 0 reset を assert。`_place_not_yet_arrived_vehicle_at_snapshot()` は未変更で二重計上を防いだ。修正後は baseline fork alignment 25 tests passed、Candidate local state 25 tests passed、exit status 0。
- 旧診断: `run_route_choice_rng_diagnostic_invariance_two_route.py` と `run_route_choice_rng_diagnostic_invariance_12_vehicle_tvt_mp.py`。後者は `--help` でも実 simulation が起動。12 台は診断なし／ありとも simulation 完了後、coverage で停止。required origin draws 12、observed 0、`RuntimeError: Origin draws 0 < 12.`。`route_choice_rng_diagnostic.py` は `W.rng.choice` の一時 proxy 監視であり、keyed ではなく、改修前の逐次経路選択用。改修後 route choice は `W.rng.choice` を使わない。origin draws 0 は経路選択の不在でも production 欠陥でもない。旧診断は新方式を観測できない。改修後受入れ根拠から外す。過去用途まで無効とはしない。合否判定へ流用しない。旧診断 3 ファイルは今回未変更。`route_choice_rng_diagnostic.py` の以前からの作業ツリー変更は今回の成果に含めない。
- full-simulation invariance: 新規 `tests_common_seed_rng_full_simulation_invariance.py`。synthetic fixture。field network でも正式 3,000 台実験でもない。3 件。two-route は同じ network・plan・明示 seed で、本実行前に perturbed の `W.rng.random()` だけ 4 回。entropy、`normal_merge_rng`、network、plan、name、OD、departure、route preference は不変。origin と途中の双方に 2 本以上、signal なし、order control なし、hard deterministic なし、specified route なし、低需要、全車完走。origin と in-trip の choice count は各 World で 0 より大きい。in-trip は `route_next_link_choice` を薄く包み、元 method 1 回、増分だけ記録、選択は変えず `finally` で復元。比較は Vehicle 名、state、departure、arrival、travel time、destination、traveled route、`log_t_link`、completion order、台数、完走、未完走、total／average travel time、total distance、last completed trip time。tolerance・丸め・近似なし。完全一致、全 3 台完走、origin choice 実作動、in-trip choice 実作動。World copy は実行途中の `W.copy()`。別 object、entropy 同値、進入 dict は同値かつ別 object、両 attempt 同値、進入記録が 1 件以上実在、`normal_merge_rng` は別 object で直後 state 同値、copy 側だけ進むと分離、元 state 不変。ordinary merge は同じ seed の 2 World、perturbed の `W.rng` だけ事前に進める。開始 merge state と entropy は同一、`W.rng` は異なる。2 台は同時刻に各 inlink へ進入。outlink 通過順と交通結果は完全一致。merge 後の `normal_merge_rng` は開始から進み、両 World で終了 state 一致。全車完走。3 tests passed、exit status 0。
- 最終 9 系統: 専用 6、baseline fork alignment、Candidate local state、full-simulation invariance を `set -e` で再実行。exit status 0。25、25、3 tests passed。failure scan 該当なし。`grep` 終了値 1 は該当なし。変更・追加した 2 test の `py_compile` は終了値 0。tracked fixture の `git diff --check` は出力なし。未追跡新規の `git diff --no-index --check /dev/null ...` は警告なし。終了値 1 は新規ファイル全体が差分であるためで、whitespace 警告は無い。
- N=1: 200 台、1,000 台、5,000 台は exact_match を維持。5,000 台は unresolved 37、fallback 37 を含めて完全一致。10,000 台は未実行。N=1 は BATCH と FCFS の等価性。今回は `W.rng` 余分消費からの keyed route choice と normal merge の分離、および copy。相互補完であり、置き換えない。
- **判定:** 監査範囲では、production に重大または high 相当の欠陥は無く、全体受入れを妨げる事象も確認されていない。これは監査範囲に限った判断であり、全体受入れ完了の断定ではない。利用者の最終受入れ判断はまだ必要。全 network・全 seed・全将来条件の証明ではない。10,000 台 N=1、別 network、別 seed、性能、Candidate selection RNG、新 BATCH は未確認。「4方式統合回帰」は復活させない。将来の方式横断は別設計と利用者判断。
- 作業ツリー: 今回の監査のコード変更は fixture 修正と full-simulation test 新規だけ。本進捗記録では test 2 ファイル、production、旧診断を変更していない。無関係な未追跡ファイルと、以前からの `route_choice_rng_diagnostic.py` 変更は含めない。

**次の作業:** Markdown 3 ファイルの差分を利用者が Terminal で独立確認する。その後の候補は、文書訂正、独立監査範囲に基づく最終受入れ可否、test 2 ファイルと Markdown 3 ファイルの commit、commit 確認後の別指示としての push。10,000 台 N=1、別 network、別 seed、方式横断確認へ自動的に進まない。

**検索語:** 共通seed RNG独立監査、Copilot独立確認、Terminal原典確認、Grok反証だけではない、production差分精読、test独立性、baseline fork fixture不足、veh_b、junction_b、node visit number 0、人為配置、record_successful_physical_link_entry、production非変更、baseline fork alignment 25 tests、Candidate local state 25 tests、旧route choice RNG診断、W.rng.choice監視、Origin draws 0、旧診断適用不能、keyed route choice、新方式専用実走行反証、full simulation invariance、W.rng余分消費、two-route、origin choice実作動、in-trip choice実作動、World copy、normal merge separation、完全一致、3 tests passed、最終9系統、exit status 0、failure scan該当なし、py_compile成功、N=1 BATCH FCFS equivalence、200台、1000台、5000台、unresolved 37、fallback 37、highなし、重大欠陥なし、全条件証明ではない、4方式統合回帰を復活させない、最終受入れ判断

#### 21.9.33 共通seed／RNG後clearance=1 FCFS対TVT-MP再実行とVOT・役割・外部便益分析

執筆日は2026-11-25である。詳細は **§22** と **§32.32**。共通seed／RNG改修後 production で、旧 clearance=1 を上書きせず、6×6ネットワーク・3000台の FCFS対TVT-MP再実行を別 directory へ行った。単一seed。因果効果ではない。4方式統合回帰を復活させない。

- runner: `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng.py`、`research_scripts/run_fcfs_6x6_grid_3000_vehicle_clearance_1_common_seed_rng.py`。既存 runner・output・production は非変更。完全一致は合格条件にしない。条件は departure T=0..999、traffic seed 0、demand seed 42、VOT seed 1、cohort／nonparticipation seed 3、participating 2400、nonparticipating 600、clearance=1、TVT-MP candidate Visit 上限 10、hard deterministic なし、full completion、traffic clearance、既存 directory なら停止。FCFS output は `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3`。TVT-MP output は `research_outputs/trial/tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_nonparticipation_seed_3`。`py_compile` と static validation の後、利用者 Terminal で `caffeinate` 実行。output は文書 commit に自動包含しない。`route_choice_rng_diagnostic.py` と無関係な未追跡物には触れない。
- TVT-MP: 正常完走。World.T = 2022、evaluation end = 2021、final actual passage = 1975、full completion と traffic clearance は True。transaction 4,233、Visit audit 11,691、buyer 4,966、seller 6,068、nonparticipating audit 657、FIFO violation 0。AWT 477.346 s、AWWT 454.0903012017529、Route-Conditional AWT 464.13 s、AWWT 441.49287823490187、detour 13.216 s。participating AWT 480.37708333333336 s、AWWT 464.0380557226082。nonparticipating AWT 465.2216666666667 s、AWWT 414.29928311832987。exec_simulation 34,713.055519 s、script total 34,776.145572 s。equality comparison False。common-seed RNG production active True。
- FCFS: 正常完走。plan hash と cohort hash 一致。AWT 574.9213333333333 s、AWWT 570.6055096886787、Route-Conditional AWT 560.1053333333333 s、AWWT 556.215696107889、detour 14.816 s、weighted detour 14.389813580789948、OD free-flow 105.576 s、actual-route free-flow 120.392 s。identity passed。simulation 5.738035792019218 s、evaluation 54.16278566699475 s、script total 117.26025816705078 s。equality comparison False。平均総旅行時間は FCFS 680.4973333333333 s、TVT-MP 582.922 s。差は 97.575秒（97.5753333333333 s）。全車両平均であり participating のみではない。
- 旧 clearance=1 再現: saving = FCFS actual − TVT-MP actual。N = 2,400、mean 144.22708333333333 s、median 88.5 s、1,793／20／587、improved rate 74.70833333333333%、Spearman 0.030141370025244956、p 0.1398940588208832、Q1〜Q5 は 141.614583／137.683333／147.554167／132.827083／161.456250 s、Q5−Q1 = 19.84166666666667 s。明瞭な順位相関は無かった。
- 新 participating VOT: mean saving 99.90166666666667 s、median 54.5 s、1,701／24／675。VOT Spearman rho 0.0641324186596357、p 0.0016697836402282693、Pearson r 0.037868571128079904、p 0.06361445730859616。Q1〜Q5 は 77.102083／95.564583／103.806250／84.750000／138.285417 s、Q5−Q1 = 61.18333333333332 s。完全単調ではない。効果量は小さい。p 値の小ささと効果の強さを混同しない。一般化しない。
- 相互排他的役割区分: BUYER_ONLY 356、SELLER_ONLY 447、BUYER_DOMINANT 585、SELLER_DOMINANT 734、BALANCED 250、NO_TRANSACTION 28。広義 941／1,181 は今回 585／734。mean saving は BUYER_ONLY 119.21910112359551 s（rho 0.1455488169339345、p 0.005937436019902466、Q5−Q1 87.76604068857591 s）、SELLER_ONLY 75.1185682326622 s（rho 0.017622701488794062、p 0.7102120148251589、Q5−Q1 16.477777777777774 s）、BUYER_DOMINANT 113.17606837606837 s、SELLER_DOMINANT 95.0 s、BALANCED 108.848 s、NO_TRANSACTION 21.214285714285715 s。BUYER_ONLY は比較的明瞭、SELLER_ONLY は確認できない。因果効果ではない。
- Top 20% N=480、threshold 1.1026898912438625、mean 138.28541666666666 s、BUYER_ONLY 211（43.96%）、BUYER_DOMINANT 204（42.50%）、buyer 側 86.46%。Top 10% N=240、threshold 2.2128076988664263、mean 136.75416666666666 s、buyer 側 92.50%。Top 5% N=120、threshold 4.006230310754763、mean 127.09166666666667 s、buyer 側 91.66%。Top 1% N=24、threshold 10.793873103649728、FCFS 比 mean 129.375 s、median 38.5 s、19／0／5、improved rate 79.1666667%。Top 1%全車buyer側（BUYER_ONLY 19、BUYER_DOMINANT 5）。内部 Spearman は主指標にしない。
- Top 1%: cutoff は 99パーセンタイル10.793873103649728。Top 1%平均総旅行時間533.875秒、median 574.0 s。Top 1%局所実現短縮11.9167秒（11.916666666666666 s）、median 10.0 s。Top 1%平均支払5.7789円（5.7788930240214）、median payment 4.313735607715271。compensation mean 0.6694662526163522、median 0。Top 1%平均正味受取マイナス5.1094円（−5.109426771405048）、median −3.697115454486527。BUYER_ONLY 19 台は travel 441.89473684210526 s、realized 11.631578947368421 s、payment 5.70492020956274 円、compensation 0、net −5.70492020956274 円。BUYER_DOMINANT 5 台は travel 883.4 s、realized 13.0 s、payment 6.059989718964308 円、compensation 3.2134380125584903 円、net −2.8465517064058177 円。5 台・24 台は一般化しない。局所と FCFS 比を混同しない。
- FCFS単独VOT相関なし。waiting rho 0.03421327460298571、p 0.09379330766429333。travel rho 0.03398814088045213、p 0.095975506608839。waiting Q5−Q1 = 35.2 s（Q1 576.527083、Q5 611.727083）。travel Q5−Q1 = 35.6 s（Q1 682.002083、Q5 717.602083）。nonparticipating VOT相関なし。N=600、mean 88.27 s、median 41.5 s、rho 0.03263077060366099、p 0.42496736732706486、422／5／173、rate 70.33333333333333%、Q5−Q1 = 18.63333333333334 s（Q1 81.35、Q3 52.75、Q5 99.983333）。participating の FCFS 比は rho 約 0.064、BUYER_ONLY は約 0.146。
- 短縮差: participating sd 246.38767867050322、rate 70.875%。nonparticipating sd 233.89172566001636。差 11.631666666666675 s。bootstrap参考値 95% CI −9.640885416666666 ～ 32.79994791666663 s。並べ替え検定参考値 p 0.29678516074196293。OD未調整。車両間相互作用。参加効果とは扱わない。
- 経路JSON正規化。同経路nonparticipating N=236（39.333333333333336%）、mean 66.24152542372882 s、median 23.5 s、188／4／44、rate 79.66101694915254%、net 15,633 s、寄与 29.51738982666818%。異経路nonparticipating N=364（60.666666666666664%）、mean 102.5521978021978 s、median 107.5 s、234／1／129、rate 64.28571428571429%、net 37,329 s、寄与 70.48261017333182%。差 36.31067237846898 s。全体 net 52,962 s、gross positive 79,742 s、worsening 26,780 s。同経路の外部便益は経路変更だけでは説明できない。交差点付近だけが主因かは未確認。
- 収支均衡: Visit 公式支払と公式補償は各 3173.109890768508円、差 0。Transaction は各 3,173.1098907685086 円、差 0。表間差約 4.55e-13 円。nonparticipating は 0。time benefit と total benefit は参加車平均とも 123.04433689226586 円、median 12.143195283855919 円、positive 72.91666666666666%。nonparticipating は 90.39869486556745 円、median 9.01200841974001 円、positive 70.33333333333334%。BUYER_ONLY total benefit 430.84731335705544 円（time 434.31824788778533、net −3.470934530729829）。SELLER_ONLY 17.49512982973437 円（time 16.653930848775815、net +0.8411989809585508）。金銭は役割方向と整合し、FCFS 比時間便益より小さい。
- 局所実現短縮は `baseline_minus_actual_passage_seconds` の符号付き合計。FCFS 比とは別。BUYER_ONLY 4282秒、平均12.028秒、平均支払3.471円、Visit 1,197、356／0／0。総旅行時間 497.447 s に対し約 2.42%。FCFS 比合計 42,442 秒との差 38,160 秒は間接効果と断定しない。SELLER_ONLY平均遅延7.989秒、平均補償0.841円。trade-scope外部効果0.717秒、median 0。全参加車の局所平均は +2.308 s、旅行時間 586.352 s、金銭は相殺。
- フリーライダー: 直接取引層では顕著でない。ネットワーク外部効果の層では、nonparticipating が金銭なしで大きな便益を受け、同経路でも 66.24 秒残る。消滅ではなく層が移った可能性がある。「回避できた」とは断定しない。
- 将来案は未実行。参加資格介入は 1 台だけ participating 化。15 台なら五分位 3 台、約 9.5 時間×15 で約 142.5 時間、探索的。VOT介入は 1 台を 99パーセンタイル10.793873103649728 へ。正直申告なら true と declared を同時変更。今は実行しない。
- **判定:** TVT-MP は全 3000台平均で約 97.575秒短い。VOT 関係は participating で弱く、BUYER_ONLY でより明瞭。Top 1% は全車 buyer 側。FCFS 単独と nonparticipating に明瞭な VOT 相関はない。収支は均衡。局所と FCFS 比を分ける。複数 seed、OD 調整、介入は将来。本記録では runner、production、output、CSV、JSON、Git を変更していない。

**次の作業:** 利用者 Terminal で新節の見出し・重要数値・差分・書式を独立確認する。その後、必要なら文書訂正。runner 2 本と Markdown 3 本の commit 可否は別判断。output の Git 包含も別判断。push は別指示。新しい simulation と局所介入へ自動的に進まない。

**検索語:** 共通seed RNG後clearance 1、6×6ネットワーク、3000台、FCFS対TVT-MP再実行、平均総旅行時間、97.575秒、participating 2400、nonparticipating 600、VOT Spearman、Q5−Q1、BUYER_ONLY、SELLER_ONLY、BUYER_DOMINANT、SELLER_DOMINANT、BALANCED、NO_TRANSACTION、相互排他的役割区分、Top 20%、Top 10%、Top 5%、Top 1%、Top 1%全車buyer側、Top 1%平均総旅行時間533.875秒、Top 1%局所実現短縮11.9167秒、Top 1%平均支払5.7789円、Top 1%平均正味受取マイナス5.1094円、FCFS単独VOT相関なし、nonparticipating VOT相関なし、bootstrap参考値、並べ替え検定参考値、OD未調整、車両間相互作用、同経路nonparticipating、異経路nonparticipating、経路JSON正規化、外部便益、公式支払、公式補償、収支均衡、3173.109890768508円、time benefit、total benefit、局所実現短縮、baseline_minus_actual_passage_seconds、BUYER_ONLY 4282秒、平均12.028秒、平均支払3.471円、SELLER_ONLY平均遅延7.989秒、平均補償0.841円、trade-scope外部効果0.717秒、フリーライダー、ネットワーク外部効果、参加資格介入、VOT介入、99パーセンタイル10.793873103649728、単一seed、因果効果ではない、4方式統合回帰を復活させない

#### 21.9.34 共通seed／RNG後signalized UXsim再実行とFCFS・TVT-MP全体効率比較

執筆日は2026-11-25である。詳細は **§23** と **§32.33**。FCFS 対 TVT-MP は詳細比較、signalized UXsim は全体効率比較である。TVT-MP は FCFS より高いが signalized UXsim に劣る。代替とは位置づけない。固有価値は VOT選別、seller補償、便益配分、外部便益。単一seed、特定信号設定、一般化しない。4方式統合回帰を復活させない。

- runner: `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_common_seed_rng.py`。基準は `run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py`。scenario と output は `signalized_uxsim_6x6_grid_3000_vehicle_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3_signal_59_0_59_0`（`research_outputs/trial/` 配下）。既存 runner、旧 output、FCFS、TVT-MP、production は非変更。完全一致は非要求。output は文書 commit に自動包含しない。`route_choice_rng_diagnostic.py` と無関係な未追跡物には触れない。
- 条件: 6×6、3000台、departure T=0..999、seed 0／42／1／3、比較用 cohort 2,400／600。cohort は比較用で TVT 制度差はない。signal setting 59 0 59 0、API cycle 118、effective `[60, 1, 60, 1]`、group 0 と 2、phase 1 と 3 は all-red equivalent、offset 0 29.5 59 88.5、内部 36、外部 24、order control false、common-seed RNG active true、equality comparison false。最適信号一般や他 network の代表とは断定しない。
- static validation: 初回 `RuntimeError: Static contract must not fix saved AWT values.`。全文の `REFERENCE_AWT`／`EXPECTED_AWT`／`EXPECTED_WORLD_T` が検査文自身に当たった。全文検索を削除し、module 直下の `ast.Assign` と `ast.AnnAssign` だけを見る。恒等検査と simulation 本体は不変。修正後 `py_compile` 成功、static validation 成功、directory 未存在、`PRE_RUN_VALIDATION_STATUS=0`。
- 完走: exit 0、World.T 2025、evaluation end 2024、full completion と traffic clearance は True。平均総旅行時間459.049秒、AWT 353.473秒、AWWT 348.7114914206239、Route-Conditional AWT 338.545秒、Route-Conditional AWWT 333.62701197899923、平均detour 14.928秒、VOT 加重 detour 15.084479441624135。participating AWT 353.46541666666667、AWWT 351.3497355587132。nonparticipating AWT 353.50333333333333、AWWT 338.15851486826585。simulation 3.9692655000835657 s、evaluation 39.65598008292727 s、write 0.08221795782446861 s、total 58.38720687502064 s。
- 正式AWWT定義: `sum(weighted_*) / vehicle_count`。vehicle countで除算。VOT合計で除算しない。誤った `sum(VOT × waiting) / sum(VOT)` 正規化は一度表示後に訂正し、保存値と 1e-9 以内。誤正規化値不使用。
- 表（s、AWWT は加重平均）: FCFS 680.497333333333／574.921333333333／570.605509688679／560.105333333333／556.215696107889／14.816／14.389813580790。TVT-MP 582.922000000000／477.346000000000／454.090301201753／464.130000000000／441.492878234901／13.216／12.597422966852。signalized 459.049000000000／353.473000000000／348.711491420623／338.545000000000／333.627011978999／14.928／15.084479441624。共通 OD 自由流 105.576 s。恒等確認済み。
- 差: TVT-MP対FCFS 97.575秒14.34%（97.575333333333 s、14.338826701256%）。signalized versus FCFS 221.448333333333 s、32.542130951285%。signalized対TVT-MP 123.873秒21.25%（123.873000000000 s、21.250355965292%）。AWT 改善率 16.971945147278%、38.518023335366%、25.950358859192%。全体効率順位signalized UXsim TVT-MP FCFS（効率は signalized > TVT-MP > FCFS）。detour は TVT-MP 最小だが旅行時間優位を覆さない。
- 役割: FCFS詳細比較は作用機序・VOT・buyer／seller・金銭・外部便益。signalized全体比較は全体効率のみ。signalized UXsim に TVT 取引・VOT選別・seller補償はない。
- BATCH: 将来比較に BATCH を加える。BATCH目標は signalized UXsim超過目標。未達・未確認。BATCHベースTVT-MP は BATCH baseline に VOT 取引を重ねる構想。未採用、未実装、未検証。
- **判定:** 3 方式比較完了。TVT-MP は FCFS より約 97.575 秒・14.34% 短いが、signalized UXsim より約 123.873 秒・21.25% 長く、signalized UXsim に劣る。不利な結果も明示する。一般化しない。4方式統合回帰を復活させない。本記録では runner、production、output、CSV、JSON、Git を変更していない。

**次の作業:** 利用者 Terminal で見出し、数値、正式 AWWT、誤正規化不使用、signalized に劣ること、FCFS 詳細と比較の役割、BATCH 未実装、差分、runner 差分を独立確認する。その後、必要なら文書訂正。signalized runner 1 本と Markdown 3 本の commit 可否、output の Git 包含は別判断。push は別指示。新しい simulation、BATCH 改修、BATCHベースTVT-MP へ進まない。

**検索語:** 共通seed RNG後signalized UXsim、FCFS・TVT-MP・signalized UXsim全体比較、signal setting 59 0 59 0、API cycle 118、offset 0 29.5 59 88.5、3000台、平均総旅行時間459.049秒、AWT 353.473秒、AWWT 348.7114914206239、Route-Conditional AWT 338.545秒、Route-Conditional AWWT 333.62701197899923、平均detour 14.928秒、全体効率順位signalized UXsim TVT-MP FCFS、TVT-MP対FCFS 97.575秒14.34%、signalized対TVT-MP 123.873秒21.25%、正式AWWT定義、vehicle countで除算、VOT合計で除算しない、誤正規化値不使用、signalized UXsimに劣る、FCFS詳細比較、signalized全体比較、VOT選別、seller補償、外部便益、BATCH目標、signalized UXsim超過目標、BATCHベースTVT-MP、未採用、未実装、未検証、単一seed、特定信号設定、一般化しない、4方式統合回帰を復活させない

#### 21.9.35 共通seed／RNG後clearance=0三方式比較と50％相補割当準備

執筆日は2026-11-29である。詳細は戦略正本 **§24** と設計ノート **§32.34**。これは実装・実証側の記録であり、直後の文献側 **§22** とは別である。暫定モデルの探索であり、最終論文値ではない。Pattern A の結果は未確認であり、本節へ推測を書かない。

- 位置づけ: FCFS／TVT-MP の clearance=0 は方向変更後次timestep通過、clearance timesteps 0、clearance=1 より 1 timestep 短い。clearance 0安全性未証明。性能損失と短縮時ポテンシャルの感度条件。signalized は `[59,59]`、all-redなし、API cycle 118、effective `[60,60]`、effective cycle 120、group 0／1、offset `[0,29.5,59,88.5]`。同じ変数の変更ではない。類似するのは timestep 1 秒、1 Link・1 timestep 最大 1 台、追加clearanceなし、同一 plan・OD・departure・seed、完走と traffic clearance。類似最小通過間隔条件下の方式比較。FCFS は逐次処理、TVT-MP は逐次処理に VOT 取引の限定再配分、signalized は固定二位相。signalized一般へ一般化しない。
- runner: `run_fcfs_6x6_grid_3000_vehicle_clearance_0_common_seed_rng.py`、`run_signalized_uxsim_6x6_grid_3000_vehicle_no_all_red_common_seed_rng.py`、`run_tvt_mp_6x6_grid_3000_vehicle_clearance_0_common_seed_rng.py`。既存 runner、production、既存 output は非変更。旧結果との完全一致は非要求。common-seed RNG は有効。
- 共通条件: 6×6、3000台、200 m、60 km/h、plan hash `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`、T=0..999、seed 0／42／1／3、比較用 cohort 2,400／600、平均 OD 最小自由流 105.576 秒、full completion、traffic clearance。signalized の cohort は比較用で TVT 制度差ではない。
- FCFS clearance 0: exit 0、semantics は next timestep passage is allowed、equality comparison False、formal output success。平均総旅行時間125.756秒、AWT 20.180秒、AWWT 20.718790788876102、RC-AWT 19.284、RC-AWWT 19.540619001244753、detour 0.896、VOT 加重 detour 1.178171787631352、route 自由流 106.472。CSV 3000 行・一意・欠損なし、1e-9、恒等 residual 0。
- TVT-MP clearance 0: exit 0、2,400／600、semantics は next timestep passage is allowed after direction change、candidate 上限 10、hard deterministic False、World.T 1184。transaction 2,465、Visit 5,522、buyer 2,636、seller 2,773、nonparticipating 113、actual arrival 5,522、FIFO 0、audit validation passed、formal output success。平均総旅行時間125.581秒、AWT 20.005秒、AWWT 18.971887076820874、RC-AWT 19.109、RC-AWWT 17.89853971444065、detour 0.896、VOT 加重 detour 1.0733473623802254、route 自由流 106.472。恒等 residual 約 1.42e-14。`sum(G) - sum(R) = sum(surplus)`、residual 0。G 5837.434589073977、R 823.6264983141591、surplus 5013.808090759818。buyer 公式支払合計と seller 公式補償合計の別定義一致は未確認のまま追加しない。
- signalized 59 59: exit 0、World.T 2232、order control False。signalized 533.430秒、AWT 427.854、AWWT 408.86320311644073、RC-AWT 413.238、RC-AWWT 393.1320837428641、detour 14.616、VOT 加重 detour 15.731119373576625、route 自由流 120.192。恒等 residual 0。初回 `run_summary.txt` に `formal output success` はなかった。その後 runner だけへ成功行と AST 検査を追加。信号・本体・評価・schema は不変。py_compile と AST は成功、再 simulation なし、output 不変。static 再実行は既存 directory 拒否で exit 1。修正失敗ではなく実行前契約。差は成功行と AST 契約だけ。
- 正式 AWWT: `sum(weighted_*) / 3000`。VOT 合計では除算しない。
- 表: FCFS 125.756／20.180／20.718790788876102／19.284／19.540619001244753／0.896／1.178171787631352／105.576／106.472。TVT-MP 125.581／20.005／18.971887076820874／19.109／17.89853971444065／0.896／1.0733473623802254／105.576／106.472。signalized 533.430／427.854／408.86320311644073／413.238／393.1320837428641／14.616／15.731119373576625／105.576／120.192。小さいほど高効率。
- 差: TVT−FCFS は旅行時間 −0.175 秒、約 0.139%、AWT −0.175 秒、約 0.866%、AWWT −1.746903712055228、AWWT 8.43%改善。signalized−FCFS は +407.674 秒、signalized−TVT は +407.849 秒。数値は TVT-MP < FCFS << signalized。効率は TVT-MP > FCFS >> signalized。平均効率ほぼ同等。
- clearance=1 からの感度: FCFS 680.497333333333→125.756、短縮 554.741333333333、約 81.52%、AWT 約 96.49%、AWWT 約 96.37%。TVT-MP 582.922→125.581、短縮 457.341、約 78.45%、AWT 約 95.81%、AWWT 約 95.82%。signalized は `[59,0,59,0]` 459.049 から `[59,59]` 533.430 へ 74.381 秒、約 16.20% の signalized 59 59悪化。AWT も 74.381 秒悪化、AWWT 約 60.152 悪化。同一 clearance 変更ではない。
- 解釈: clearance=1 では平均効率と VOT加重効率が同時に改善した。clearance=0 では FCFS が AWT 約 20.18 秒で既に高効率、TVT-MP の追加の平均改善はほぼ消失、AWWT は約 8.43% 改善。TVT-MP設計思想と整合的。平均効率をほぼ維持し、待ち時間再配分を支持する探索結果。機序が VOT 選別だけとは断定しない。all-redなしでも `[59,59]` は悪化し、固定二位相と逐次処理の差が大差に現れた可能性がある。原因は未確定。
- 言える範囲は、絶対性能の大幅改善、FCFS の高効率、TVT-MP の平均ほぼ同等と AWWT 改善、設計思想との整合、今回の signalized の遅さ、制御構造差の現れ、まで。言えないのは安全性、実装可能性、一般優位、他条件での再現、唯一原因、因果、最終論文値。指数分布投入予定、ODランダム性改善予定、BATCH と複数 seed は将来。本格実験前の情報収集。
- 50%相補割当: Pattern A と Pattern B complement の runner を作成・事前監査済み。clearance=1、1,500／1,500、`random.Random(3).shuffle`、Group A 前半、Group B 後半。Pattern A は A participating。Pattern B は逆。true VOT固定、declared VOT label依存。hash は true VOT `6b56e754fcc34d6b9b877389e184289db6fbc50dc6e752aa06a6107463a35932`、Group A shuffle順hash `eea09bc60090845150f497f7ab244c6d7b47ae1e495a6fb3b515496f1ab23503`、Group B shuffle `796dfbfc7ee5bdd62d13035670aa5e6838b519ee16f5a52f26b48d90a3f4918e`、Group A plan順hash `07d8cc591f62cbae4e4ca1e663481d10009c663b11d53326ce68375b568fa53d`、Group B plan `bcac57de76b618058faa857959831752e55ee29193c52648ee51f15477db84ef`、pair `2d0a8db67ab4b690c22a0b4a55ec41363d2b5d793b0bf0cd91652fe99163ca34`。py_compile と static 成功、output 未存在、各 1,500、被覆、plan と true VOT 一致、全3000台label反転、failure 0。参加者構成感度であり、個車因果効果ではない。OD だけ・departure だけ・VOT だけの交換実験とは書かない。
- 現在地: clearance=0 三方式は完走・監査・再集計済み。Pattern A実行中。Pattern B未実行。80%未着手。Pattern A の結果は未記録。片方だけで比較を確定しない。
- **次の作業:** Pattern A 完走後に output の事後監査。合格時だけ Pattern B を実行し、監査、補集合再確認、2 pattern 比較のあと 80% へ進むかを判断する。Pattern B、80% runner、新しい clearance simulation、BATCH、4方式統合回帰、Pattern A の推測、clearance=0 の追加分解は今行わない。branch `feature/common-seed-rng-foundation`。利用者が示した最新 push 済み commit は `b1f60c6cde4c241cca5a2825e4d570496617331b`。新規 runner と今回 output は未 commit。`route_choice_rng_diagnostic.py` と既存未追跡物には触れない。本記録では runner、production、output、CSV、JSON、Git を変更していない。

**検索語:** 共通seed RNG後clearance 0、FCFS clearance 0、TVT-MP clearance 0、signalized UXsim 59 59、方向変更後次timestep通過、追加clearanceなし、類似最小通過間隔、固定二位相、逐次処理、平均総旅行時間125.756秒、平均総旅行時間125.581秒、AWT 20.180秒、AWT 20.005秒、AWWT 20.718790788876102、AWWT 18.971887076820874、AWWT 8.43%改善、平均効率ほぼ同等、VOT加重効率、TVT-MP設計思想、平均効率をほぼ維持、待ち時間再配分、signalized 533.430秒、signalized 59 59悪化、all-redなし、signalized一般へ一般化しない、clearance 0安全性未証明、暫定モデル、指数分布投入予定、ODランダム性改善予定、50%相補割当、Pattern A、Pattern B complement、Group A、Group B、shuffle順hash、plan順hash、true VOT固定、declared VOT label依存、全3000台label反転、参加者構成感度、個車因果効果ではない、Pattern A実行中、Pattern B未実行、80%未着手

## 22. Schepperle・Böhm追加原文・PEXIC第二段階適用・正式再採点の完了（2026-11-27）

本§22は、2026-11-27時点の**先行研究調査**の進捗だけを記録する。既存**§20**は2026-11-02のSchepperle・Böhm初回適用として残す。既存**§21**は実装・実証側の進捗であり、文献節番号と混同しない。自研究側の最新実装・実証結果は別の実装・実証正本に記録済みであり、本節へ転載しない。

詳細正本は `ORDER_EXCHANGE_LITERATURE_FIRST_STAGE_SCORING_AND_POSITIONING.md` である。本節で書く詳細正本§21、§23、§24、§24.17は、そのファイルの節である。進捗正本の§21ではない。FRAMEWORKは `ORDER_EXCHANGE_LITERATURE_POSITIONING_FRAMEWORK.md` である。

文献調査の現在の再開地点は本§22である。§20本文が文献調査の最新再開地点を§20としている記述は、2026-11-02および2026-11-03時点の記録である。実装・実証側の再開地点は§21のままである。

### 22.1 今回の文献調査範囲

**Schepperle・Böhm系列。** 追加で全文を確認した資料は次である。

- Traffic Management Based on Negotiations between Vehicles: A Feasibility Demonstration Using Agents
- Towards Valuation-Aware Agent-Based Traffic Control
- Agent-Based Traffic Control Using Auctions
- Auction-Based Traffic Management: Towards Effective Concurrent Utilization of Road Intersections

新たに固定した範囲は、TSR、TSE、Basic ITSA、ITSA with subsidies、Free Choice、Clocked、IE・LE・CAE、formal property、simulation result、fairness、network限界である。

**PEXIC系列。** 確認した資料は、出版社版journal原論文全文と、博士論文全文である。

新たに固定した範囲は、正式書誌、PEXIC名称、Lloret-Batlle・Jayakrishnan論文との包含、phase allocation、VDS、envy-minimizing pricing、budget balance、Pareto property、complete information、full participation、BIC近似、simulation、saturation限界、network限界、X2・Y1の正式再採点である。

詳細は詳細正本§23と§24に置く。FRAMEWORK上の要約は§5Eである。初回適用の歴史的記録は、詳細正本§22、FRAMEWORK§5D、進捗§20である。

### 22.2 Schepperle・Böhm系列の追加原文と詳細更新

詳細手順と全数値は詳細正本§23にある。ここでは今回固定した位置だけを残す。

**系列内の役割。** 原文事実として、TSRとITSAはinitial allocationである。TSEはpost-allocationのbilateral exchangeである。Free ChoiceとClockedはConcurrent auctionである。こちらの評価は、誘因性質をmechanismごとに分ける、ということである。TVT-MPとの直接比較の中核はTSEである。

**TSE。** 原文事実として、割当済みslotをentitlementとする。成立はinitiatorとcandidateの1対1交換である。支払はVehicle間である。Same-laneの前後Vehicleには、限定的なslot-order protectionがある。Formal propertyとして、著者はbudget-balancedと判定し、pricingはincentive-compatibleではない。TSRのstarvation性質を継承する。こちらの評価は、initial allocationのfairness問題は残り、voluntary participationだけでは制度全体のfairnessを保証しない、ということである。

**ITSA。** Formal propertyとして、Basic ITSAはsealed-bid second-priceであり、静的なtruthful biddingを持つ。Auction revenueはVehicle間のzero-sumではない。ITSA with subsidiesはincentive-compatibleではない。Starvation回避の保証はない。Simulation resultとあわせて、low-valuation Vehicleへのwaiting burdenがある。

**Concurrent auction。** 原文事実として、IE、LE、CAE、Free Choice、Clocked、conflict area、same-lane physical order、reservation failure、cancel、reauctionを扱う。こちらの評価は、intersection-internal physicsが、追加原文確認前の理解より具体的である、ということである。Network integrationの強さとは別である。

**代表simulation result。** 詳細条件と他の数値は§23を参照する。

- TSEは、通常条件のTSR比で、average waiting timeを4.0%、valuation-weighted waiting timeを7.3%削減する。
- ITSA without subsidiesは、valuation-weighted waiting timeを30.6%削減し、average waiting timeを0.5%増加させる。ITSA with subsidiesは、valuation-weighted waiting timeを43.0%削減し、average waiting timeを1.8%増加させる。
- Free Choiceは、TSR比のvaluation-weighted waiting timeを最大38.1%削減する。

こちらの評価は、valuation-aware mechanismが常に優越するとはしない、ということである。Clockedは条件によりTSRより悪い。その条件分けは§23にある。

**最新ポジショニング。** 強い直接競合である。取引構造はTVT-MPに近い。Intersection-internal physicsは具体的である。Network integrationはLowである。Nonparty protectionは部分的に近いが、TVT-MPと同一ではない。差別化は、network統合、multi-party補償、nonparticipation、prediction-vs-actual、actual外部効果に置く。Networkとactualの軸は比較上の特徴であり、全体効率の優越を意味しない。第一段階採点は現時点では既存値を維持する。X合計8、Y合計3、制度Medium-High・network Lowである。追加原文後に変更する必要があるかは、§22.7の横断整合で判断する。

2009年overview chapter全文だけは、資料未入手のままである。

### 22.3 PEXIC系列の第二段階詳細適用

**資料。** Journal原論文は、Envy-minimizing Pareto Efficient Intersection Control with Brokered Utility Exchanges under User Heterogeneityである。Transportation Research Part B、Vol. 94、pp. 22–42、2016、DOI 10.1016/j.trb.2016.08.014である。博士論文は、Peer-to-peer and Collaborative Consumption of Supply in Transportation Systems、2017である。該当章はChapter 4、Priced Exchanges in Traffic Intersection Controlである。

**制度構造。** 原文事実として、phase allocationとpricingの二段階である。Vehicle別VDSを使い、costはVDSとdelayの積である。Total Vehicle costを最小化する。Phase order、phase duration、Vehicle delay allocationが変わる。Delayを決めたあとでenvy-minimizing priceを付ける。Price合計は0である。制御はrolling horizonである。TSE型のbilateral exchangeではない。

**Formal property。** Quasilinear utility、allocative efficiency、budget balance、Pareto optimality、envy minimization、price normalizationを持つ。こちらの評価は次のとおり分ける。Pareto optimalityは、全Vehicleのbaseline改善ではない。Budget balanceはIRではない。Envy minimizationはincome equityではない。Formal IR theoremは未固定である。

**誘因と参加。** 基本modelはcomplete informationであり、correct VDSを既知入力とする。Strategy-proofnessは示されていない。博士論文はasymptotic BIC approximationを追加する。PEXIC priceとBIC priceの平均差は、一般に0.01ドル未満である。DSICでもex-post ICでもない。参加はfull participationであり、nonparticipating Vehicleの混在はない。

**Simulation result。** Isolated signalized intersection、complete 8-phase dual-ring NEMA、PARAMICSである。Rolling horizonは80秒、timestepは1秒である。Critical volumeは150、450、750、1050、1350 veh/hである。PLVは0%、7.5%、15%である。各条件6 seedsである。比較対象はMin-Delayである。

比較した需要水準のうち低い側の450 veh/h、PLV 15%では、average costが20.21%削減された。750 veh/h、PLV 15%では14.28%、1350 veh/h、PLV 15%では4.74%削減された。Average delayは増加する。Envyは多くの条件で低下する。Saturation付近では優位が縮小し、または消失する。著者の主張として、Min-Delayへの切替が示唆されている。この示唆はformalな切替規則ではない。

**Network限界。** Predicted arrivalは検出後に固定する。Lane changeはない。Queueはvertical queueである。Spillbackとgridlockは著者による危険の指摘であり、network simulationの結果ではない。Network-level controlはfuture workである。Predicted-vs-actual auditはない。こちらの評価は、network Lowを維持する、ということである。

**最新ポジショニング。** TVT-MPの最も強い直接競合候補の一つである。Formal economic depthはHighである。Nonparticipant protectionはLowである。Network integrationはLowである。Prediction-vs-actualはLowである。Networkとactualの比較軸は、TVT-MPの全体効率の優越を意味しない。

### 22.4 PEXICのX2・Y1正式再採点

詳細正本§24.17の結果である。コードブック定義は変更していない。全文確認による既存基準の再適用である。

変更前は、Xが2, 1, 2, 2, 1, 2、X合計10、Yが1, 1, 0, 0, 0, 0、Y合計2である。

変更後は、Xが2, 2, 2, 2, 1, 2、X合計11、Yが2, 1, 0, 0, 0, 0、Y合計3である。

X2は1から2である。Vehicle別VDSが、phase order、phase duration、Vehicle別delay allocationを直接決める。Y1は1から2である。Complete 8-phase dual-ring NEMA、movement-level conflict、phase feasibility、Vehicle-level arrivalとdelayを明示する。

維持した項目は、X5=1、Y2=1、Y3からY6は0、制度High・network Low、直接競合分類である。点数差は研究品質の順位ではない。Formal economic depthとnetwork integrationは別軸である。

Schepperle・Böhm系列の第一段階採点は、この再採点では変更していない。

### 22.5 FRAMEWORKへの要約反映

FRAMEWORKでは、§5D末尾へ歴史的注記を追加し、§5Eを新設した。小節は§5E.1から§5E.8である。内容は、Schepperle・Böhm系列の最新要約、PEXICのformal properties、PEXICのsimulationとnetwork限界、PEXICの正式再採点、直接競合3系列の現在位置、第三段階へ送る前提、未確認事項、次の作業である。

古いPEXIC記述は削除していない。更新注記で、最新参照先を詳細正本§24、§24.17、FRAMEWORK§5Eへ示した。

役割は分ける。詳細正本が制度、式、実験、全未確認事項を保持する。FRAMEWORKは横断的な最新要約と再開地点を保持する。本§22は、その作業が完了したことと、次に読む節を保持する。

### 22.6 解消した未確認事項と残る主要未確認事項

**Schepperle・Böhm系列で解消した主要未確認。** TSEのinitial phase、exchange request・candidate・acceptance、budget balance、non-incentive compatibility、starvation、nonparty slot-order protection、TSE simulationと主要効果量を固定した。Basic ITSA、ITSA subsidy、truthfulnessと非ICの区別、auction revenue、starvation保証の欠如を固定した。IE、LE、CAE、Free Choice、Clocked、failure・cancel・reauction、Concurrent auctionの主要結果を固定した。

**Schepperle・Böhm系列の主要残件。**

- 2009年overview chapter全文は、資料未入手である。
- TSEの正確な支払式は、原文の該当式が未固定である。
- ITSA subsidyの支払と按分は、原文の該当式が未固定である。
- Concurrent auctionの一部実験表は、頁と表の対応が未固定である。
- Spillback、複数交差点、route choiceは、入手済み原文に対応または検証の記載がない。

**PEXICで解消した主要未確認。** 正式書誌、PEXIC名称、原論文との包含、phase allocation、VDS、pricing、budget balance、Pareto、envy、complete information、full participation、BIC近似、simulation条件、costとdelay、saturation限界、Min-Delay切替の示唆、spillback警告、network-levelのfuture work、X2・Y1の再採点を固定した。Spillback警告は、検証済みのnetwork結果として解消したわけではない。指摘であることまでを固定した。

**PEXICの主要残件。**

- Formal IR theoremは、本文の該当定理が未取得である。
- Journalと博士論文の完全差分は、差分未固定である。
- BIC比較の全parameterは、本文の該当箇所が未取得である。
- Nonparticipating Vehicleの混在simulationは、基本modelがfull participationであり、混在simulationを確認できない。
- Predicted-vs-actual auditは、入手済み原文に対応または検証の記載がない。
- Network controlは、検証がなく、future workである。

### 22.7 文献調査の現在地と次の直接作業

完了済みは次である。

- Lin・Jabari系列の第二段階詳細適用は、詳細正本§21、FRAMEWORK§5Cである。
- Schepperle・Böhm系列の追加原文後の詳細適用は、詳細正本§23、FRAMEWORK§5E.2である。初回適用は詳細正本§22、FRAMEWORK§5D、進捗§20に残る。
- PEXIC系列の第二段階詳細適用は、詳細正本§24、FRAMEWORK§5E.3から§5E.5である。
- PEXICの正式再採点は、詳細正本§24.17、FRAMEWORK§5E.5である。最新値はX合計11、Y合計3、制度High・network Lowである。

次の直接作業は、直接競合3系列の横断整合だけである。確認項目は次である。

1. 三系列の共通比較項目
2. Buyer・sellerまたはpayer・payeeの対応
3. Payment、compensation、budget balance
4. Individual rationality、Pareto、envy
5. Incentive compatibility
6. Participationとnonparticipation
7. Physical feasibility
8. Network integration
9. Predictionとactual
10. 構造的前提
11. TVT-MPとの差別化
12. 採点と概念ラベルの横断整合

Schepperle・Böhm系列の第一段階採点を、追加原文のあとで変更する必要があるかも、この横断整合で判断する。現時点の採点は、X合計8、Y合計3、制度Medium-High・network Lowのままである。PEXICのX2・Y1再採点は完了済みであり、次作業に含めない。

その後の作業候補は、第三段階の正式閾値設計、直接競合3系列の比較表、論文本文用のポジショニング記述、図の概念ラベル化である。これらは今回の次の直接作業ではない。

### 22.8 変更文書・非変更範囲・Git現在地

今回の先行研究メモ作業で変更した文書は次である。

- `ORDER_EXCHANGE_LITERATURE_FIRST_STAGE_SCORING_AND_POSITIONING.md` は、詳細正本§23、§24、§24.17を保持する。
- `ORDER_EXCHANGE_LITERATURE_POSITIONING_FRAMEWORK.md` は、要約§5Eを保持する。
- `ORDER_EXCHANGE_PROGRESS_4.md` は、進捗§22を保持する。

変更していないものは、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`、`ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md`、production、tests、runner、analysis script、research_outputs、CSV、`diagnostics/order_control.zip` である。

作業開始前から存在するtracked変更は `research_scripts/route_choice_rng_diagnostic.py` である。この既存変更は、今回の先行研究作業ではない。

Git現在地は、branch `feature/common-seed-rng-foundation`、基準HEAD `aea2a95e91613ee7eef285bfc99d1a7fc86f38dc`、originも同じcommitである。今回の先行研究メモは未commitである。Git add、commit、pushは未実施である。

実装・実証側の正本と、文献側の正本は別である。文献調査を再開するときは、本§22、詳細正本§23と§24、FRAMEWORK§5Eを読む。実装・実証へ戻るときは§21と、対応する実装・実証正本を読む。自研究側の最新数値は本節にない。
