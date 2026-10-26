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
