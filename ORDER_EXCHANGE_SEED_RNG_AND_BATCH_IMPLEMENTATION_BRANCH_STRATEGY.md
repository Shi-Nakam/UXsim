# seed／RNG改修とBATCH大幅改修の実装順、branch分離、現行BATCH保全、新BATCH採否方針

## 0. 記録の位置づけ（2026-11-22）

- 執筆日: 2026-11-22
- 本ファイルは、seed／RNG改修とBATCH大幅改修を横断する実装順、branch分離、比較基準、段階的回帰、現行BATCH保全、新BATCH採否判断の最詳細正本である。
- 本ファイルはBATCHアルゴリズム自体の詳細を `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28** から複製しない。
- 本ファイルはseed／RNGの技術契約を `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** から複製しない。
- 扱う中心範囲は、実装系列、現行基準の固定、branchの分離と派生関係、各変更境界でのN=1 BATCH対FCFS回帰、現行BATCHを失わない評価構造、新BATCHの正確性・性能評価と採否判断、不採用時に現行BATCHを継続使用できること、production統合前の受入れ条件である。
- production seed／RNG改修は未着手である。
- 全World仮想計算型BATCH production実装も未着手である。
- branch作成も未実施である。
- 30反復本番へはまだ進まない。
- 現行branchは `feature/intersection-order-control` である。
- 記録作成前の最新commitは `4c6d9da` である。
- 記録作成前に、local HEADとremoteが一致確認済みだった。
- 作業ツリーには今回と無関係な既存変更・未追跡ファイルが多数ある。削除、復元、移動、stageしてはならない。
- 特に、追跡済み変更 `research_scripts/route_choice_rng_diagnostic.py` と、多数の未追跡research output、script、CSV、`diagnostics/order_control.zip`、`g_0_0` 等に触れない。
- Git操作は利用者がTerminalで行う。Cursorには行わせない。branch作成、commit、push、merge、checkout、reset、restore、stageをCursorにさせない。

接続先:

- seed／RNG技術契約: `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21**
- BATCH将来設計: 同 **§32.22**。本方針の全体接続は同 **§32.23**
- BATCH詳細設計: `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28**。本方針の接続要約は同 **§1H.29**
- 進捗: `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.23**、**§21.9.24**
- N=1診断script: `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py`
- baseline collector既知問題: `ORDER_EXCHANGE_PROGRESS_3.md` の該当記録

**§32.22** 等にある「seed／RNG改修を先に実装する」「BATCHレビュー未着手」は当時の歴史的記録として残す。本ファイルはそれらを削除せず、後続判断として現行基準の固定とbranch分離を追加する。

## 1. 判断の目的

- seed／RNG改修とBATCH大幅改修を同時に混ぜて、N=1 BATCH対FCFS不一致の原因切分けを困難にしない。
- 現行BATCHを失わず、新BATCHを正確性と性能の両面で評価する。
- 新BATCHの性能が期待に届かない場合や、正確性契約を満たさない場合には、現行BATCHを継続採用できる状態を保つ。
- 新BATCHを実装したこと自体を採用理由にしない。
- 現行BATCHは不完全なので廃止する、とは扱わない。新BATCHへ置換することが確定した、とも扱わない。
- 新BATCHは未実装・未採用の評価候補である。
- 現行BATCHは現在動作している採用済み比較対象であり、新BATCHの正確性・性能が採用基準を満たさない場合に継続使用できるよう保全する。
- 新BATCHを正式採用できる場合でも、旧runtime経路をproduction内に恒久併存させるかは現時点で確定しない。
- Git履歴とbranchに旧実装を残すことと、同じproductionで旧実装を恒久的に選択可能にすることを混同しない。

## 2. 案A、案B、案Cの比較と案Cの採用

### 案A

- seed／RNG改修を先に全面実装し、その後BATCH大幅改修を行う。
- 正式乱数基盤へ早く統一できる。
- ただし現行基準を明示的に固定せず進めると、seed／RNG改修後の不一致原因を切り分けにくい。

### 案B

- BATCH大幅改修を先に実装し、その後seed／RNG改修を行う。
- 旧seed環境でBATCH改修単独の影響を見やすい。
- ただし後続seed／RNG改修でsnapshot、copy、tiebreaker、訪問識別を再接続する可能性があり、二重作業と再検証が必要になる。

### 案C（正式採用）

- 現行seed環境でN=1 BATCH対FCFS基準を先に確認する。
- その後seed／RNG改修を専用branchで実装・検証する。
- seed／RNG改修の受入れ後、その受入れ済みcommitからBATCH大幅改修専用branchを派生させる。
- 各変更境界でN=1 BATCH対FCFS一致を確認する。
- 2026-11-22に案Cを正式採用した。

案Cは、実装順としてはseed／RNG改修をBATCH大幅改修より先に行う。したがって **§32.22** 等の「seed／RNG改修を先に実装する」という過去判断を否定するものではない。今回追加されたのは、その前に現行基準を固定し、seed／RNGとBATCHを別branchにし、各境界で反証可能にする具体化である。

旧seedと新seedの交通結果そのものの一致は要求しない。要求するのは各段階内部での横並び一致である。

- 現行seed環境: FCFS = N=1 BATCH
- seed／RNG改修後の共通seed環境: FCFS = N=1 BATCH
- 全World仮想計算型BATCH改修後の共通seed環境: FCFS = N=1 BATCH

seed／RNG改修とBATCH大幅改修を同じbranchで連続して未分離実装しない。BATCH大幅改修branchを、現行の旧seed基準から直接派生させない。

## 3. 過去のN=1 BATCH対FCFS検証実績

以下は、2026-11-22の再確認より前に記録されていた検証実績である。今回の再実行結果と混同しない。

### 初期6台検証

- batch_size=1
- Level 1
- clearance=1
- 同一network、OD、seed、capacity、route
- 全6台についてNode初回到着時刻、outlink初回進入timestep、進入順序、通過inlink順序、trip終了timestepが完全一致
- Node状態履歴、方向切替回数、clearance待機、完走数、total/average travel timeも一致
- 最初の不一致なし
- commit `b03538c`

### zero-service修正後

- 10,000台、6×6 grid、自由経路でsize-one BATCHとFCFSの最初の差を発見した。
- veh_3573、Node g_3_4で、修正前BATCHはT=1104、FCFSはT=1103だった。
- zero-service後に同一Node.transfer呼出し・同一timestep内の別inlink未割当trigger候補から追加形成しないことが直接原因だった。
- production修正commit `2b10b08`
- 診断commit `fe9e53e`
- 修正後、200台固定routeと10,000台自由経路でVehicle別state、arrival_time、travel_time、traveled route、log_t_link等が厳密一致した。

### Level 2本体接続後

- 診断scriptは `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py` である。
- N=1でもLevel 2を実際に呼び出し、batch_size=1 bypassを設けない。
- 200、1,000、5,000、10,000台で過去にexact_matchだった。
- 5,000台ではunresolved 38回、Level 1 fallback 38回を含めてexact_matchだった。
- 10,000台でもexact_matchだった。
- 過去の5,000台765.662秒はAnalyzer省略後、full TMAX時代の歴史値である。
- その後short TMAXが正式反映されている。

## 4. 2026-11-22の現行基準再確認

2026-11-22に、現行seed環境のN=1 BATCH Level 2対FCFSを再実行し、branch分岐前の現行基準として固定した。性能は今回の等価性検証の合否基準ではない。

### 共通条件

- 6×6 grid
- internal grid Node 36
- external OD Node 24
- Link 168
- departure 0〜500
- random_seed=0
- demand_gen_seed=42
- minimum OD Manhattan distance 5
- internal Link length 400
- OD connector length 300
- free-flow speed 20
- clearance=1
- unsignalized
- free dynamic route choice
- FCFS対N=1 BATCH Level 2
- N=1側virtual horizon 30
- 全車完走
- 入力同一性確認PASS
- 集計比較とVehicle別比較はPythonの `!=` による厳密一致であり、toleranceや丸めを用いない

### 200台

- tmax 5000
- FCFS total travel time 32036.0
- average travel time 160.2
- average delay 0.5
- total distance 638800.0
- last completed trip time 684.0
- Level 2 call_count 1497
- resolved 1497
- unresolved 0
- fallback 0
- aggregate mismatch 0
- Vehicle-level mismatch 0
- comparison_class exact_match

### 1,000台

- tmax 10000
- total travel time 267509.0
- average travel time 267.5
- average delay 102.9
- total distance 3306400.0
- last completed trip time 997.0
- Level 2 call_count 7766
- resolved 7766
- unresolved 0
- fallback 0
- aggregate mismatch 0
- Vehicle-level mismatch 0
- comparison_class exact_match

### 5,000台

- tmax 30000
- total travel time 7866209.0
- average travel time 1573.2
- average delay 1408.6
- total distance 19571200.0
- last completed trip time 3409.0
- Level 2 call_count 46428
- resolved 46390
- unresolved 38
- fallback 38
- aggregate mismatch 0
- Vehicle-level mismatch 0
- comparison_class exact_match
- Level 1 fallback経路を含めて完全一致した

5,000台の今回のN1-L2 exec_simulation_secondsは168.825秒、case totalは170.279秒だった。過去の765.662秒に対し約4.54倍高速であり、過去値がfull TMAX時代、今回はshort TMAX正式反映後であることと整合する。Level 2のcall、resolved、unresolved、fallback件数は過去記録と同じである。ただし今回は厳密な性能A/B試験ではないため、時間差の全てをshort TMAXだけの因果効果とは断定しない。

### 10,000台

- 10,000台は今回は再実行していない。
- 過去の正式exact_match実績を維持する。
- 今回のbranch分岐前確認は200、1,000、5,000台で完了とする。
- 200台だけで現行基準確認を完了した、とは扱わない。

## 5. 診断scriptの正確な比較契約

診断の等価性判定に使う比較fieldは次である。集計と比較はPythonの `!=` による厳密一致であり、toleranceや丸めを用いない。

AGGREGATE_COMPARE_FIELDS:

- total_vehicles
- completed_trips
- unfinished_trips
- completed_ratio
- total_travel_time
- average_travel_time
- average_delay
- delay_ratio
- total_distance_traveled
- last_completed_trip_time
- analyzer_reference_average_speed

VEHICLE_COMPARE_FIELDS:

- state
- departure_time
- arrival_time
- travel_time
- destination_name
- traveled_route_link_names
- log_t_link_history

さらに次を比較する。

- Vehicle名集合
- completion_order

completion_orderは、完走Vehicleについてarrival_timeとVehicle名で並べた順序である。

final_link_nameはsnapshotには収集されるがVEHICLE_COMPARE_FIELDSには含まれない。ただしtraveled_route_link_names全体が比較されるため、最終Linkは実質的に包含される。

次の2行は実構造比較による判定ではなく固定printであるため、監査済み事実として扱わない。

- assignment prefix violation: none observed (simulation completed)
- visit_id / batch_assignment / service unit mismatch: none observed

BATCH assignmentやservice unitはFCFSに同じ構造が存在しない。両方式間の完全一致fieldとして無理に追加しない。

## 6. 既知の別問題（baseline collector test）

`ORDER_EXCHANGE_PROGRESS_3.md` に、`tests_order_control_baseline_collector_uxsim.py` の `test_batch_passage_stops_before_physical_transfer_on_inconsistency` が失敗する記録がある。

- 古いtestはvisit_id mismatch例外を期待する。
- 現行collector契約と一致しない。
- 当時の変更はclearanceありFCFSだけであり、BATCH本体変更による回帰ではない。
- 単独実行でも再現した。
- 当時は修正しなかった。
- 解決済みではない。

この問題と今回のN=1 BATCH対FCFS診断は別論点である。今回の200、1,000、5,000台exact_matchによって、このtest契約不一致が解決したとは扱わない。一方、このtest問題の存在だけで、通常実行条件におけるN=1一致性が否定されたとも扱わない。seed／RNG実装前または実装設計中に、現行test、collector契約、期待例外のどれを正とするかを独立確認する必要がある未解決事項である。

## 7. branchの派生関係

次の関係で進める。

現行の安定基準 → seed／RNG改修専用branch → seed／RNG改修の受入れ済みcommit → BATCH大幅改修専用branch → 現行BATCH経路を維持したまま新BATCH試験経路を追加 → 新旧横並び評価 → 採否判断

### seed／RNG改修branch

- 現在のproduction branchへ直接実装しない。
- branch名と分岐元commitはbranch作成直前に確定する。現時点では未確定であり、branchは未作成である。
- 範囲は、route choice keyed randomization、arrival tiebreaker keyed randomization、Link別進入回数、origin／in-trip attempt、signalized UXsim専用merge RNG、snapshot、copy、pickle、rollback等の必要対応である。技術契約の正本は **§32.21** であり、本節はそれを複製しない。
- 既存回帰、方式間対応、監査出力を確認する。
- 検証完了前にproductionへ統合しない。

### BATCH大幅改修branch

- seed／RNG改修が受入れられたcommitから派生させる。
- 現在の旧seed基準から直接派生させない。
- seed／RNG改修branchと同じbranchで連続して未分離実装しない。
- branch名と分岐元commitは開始直前に確定する。現時点では未確定であり、branchは未作成である。
- Git操作は利用者がTerminalで行う。
- Cursorにはbranch作成、commit、push、mergeをさせない。

## 8. 現行BATCHの保全と新旧比較

- 現行BATCHは現在動作している採用済み比較対象として維持する。
- 現行BATCHが将来設計より不完全であることだけを理由に削除・置換しない。
- 新BATCHは未実装・未採用の評価候補である。
- BATCH改修branchの評価中は、`order_control_type="batch"` の意味を黙って新方式へ置換しない。
- 現行BATCH処理経路を維持し、新BATCHを明示的な独立試験経路として追加する。
- 新方式の正式名称、内部選択方法、API値はまだ確定しない。実装前に名称、目的、範囲を利用者へ説明し、合意後に使用する。
- 同一commit内で、同じnetwork、OD、Vehicle plan、seed、clearance、max_batch_size等を用いて新旧を選択実行できる評価構造を基本方針とする。
- checkoutを繰り返す新旧比較だけには依存しない。診断版、seed基盤、audit、共通修正の差が混入し得るためである。
- 評価中に新旧を併存させることと、採用後もproduction公開APIとして永久に両方を維持することは別判断である。
- 新BATCHを正式採用できる場合でも、旧runtime経路をproduction内に恒久併存させるかは現時点で確定しない。
- Git履歴とbranchに旧実装を残すことと、同じproductionで旧実装を恒久的に選択可能にすることを混同しない。

## 9. 新BATCHの受入れ条件と採否分類

新BATCHは未実装である。以下は、実装後に採否を判断するための条件であり、採用済みの宣言ではない。

### 正確性の必須条件

- **§1H.28** の形成規則を再現する。
- assignment、service queueに欠番、重複、上書きがない。
- 物理FIFO、未到着待ち、clearance、容量、入口空間を維持する。
- max_batch_size=1でFCFSと完全一致する。
- 仮想Worldが実Worldを変更しない。
- 仮想World内でT以後に新規BATCHを形成しない。
- horizon未解決時のLevel 1 fallbackが仕様どおりである。
- 評価期間末から内部horizonを確保する。
- auditで形成根拠を再現できる。
- arrival tiebreakerの同一Visit内不変を維持する。
- seed／RNG改修後のNode訪問識別とcopy契約を正しく利用する。

### 性能・研究評価

- 現行BATCH対新BATCHのaverage travel time
- waiting time
- full completion timestep
- queueとspillback
- Vehicle別・OD別分布
- 複数seed
- 複数network・需要条件
- 計算時間
- メモリ
- fallback率
- 仮想計算起動回数
- 全World copyコスト
- 30反復本番の実行可能性

N=1一致性の合否に計算時間を使わない。単一network、単一seed、単一需要で平均旅行時間が改善しただけでは正式採用しない。新方式の実装完了自体を研究上の優位性とみなさない。全World計算のcopy・forward負荷が大きく、30反復本番に不適切なら、現行BATCH継続を選択できるようにする。

### 採否分類

1. 正確性不合格
   - 採用しない。
   - 修正または中止する。
2. 正確性合格だが性能・研究上の利点が不十分
   - 現行BATCHを正式方式として維持する。
   - 新BATCHはbranchと研究記録に残す。
   - BATCH改修branchをproductionへ統合しない選択肢を維持する。
3. 正確性合格かつ評価上採用可能
   - 新BATCHを正式実装候補とする。
   - その時点でproduction切替方法を決める。
   - 旧runtime経路を残すか削除するかは別途判断する。
   - 採用可能と判明する前に旧経路を削除しない。

## 10. 実装・検証順

- 現行N=1基準確認: 2026-11-22に200、1,000、5,000台で完了した。10,000台は今回未実行であり、過去exact_match実績を維持する。
- 正本メモ記録（本ファイル、**§1H.29**、**§32.23**、**§21.9.24**）。
- 対象Markdownだけを明示してstageする。
- commitする。
- commit結果、最新commit、残存する作業ツリー変更を確認する。
- pushはcommit確認後の別指示で行う。
- push後にgit status、最新commit、local／remote一致を確認する。
- Git操作は利用者がTerminalで行う。CursorにはGit操作をさせない。
- seed／RNG改修専用branchを利用者がTerminalで作成する。作成は未実施である。
- seed／RNG実装。production実装は未着手である。
- 小規模専用test。
- 現行診断による200台N=1対FCFS。
- 必要な中間回帰。
- 5,000台fallback込みN=1対FCFS。
- seed／RNG改修の受入れ判断。
- 受入れ済みcommitからBATCH大幅改修専用branchを作成する。旧seed基準から直接派生させない。
- 現行BATCHを維持したまま新BATCH試験経路を実装する。`order_control_type="batch"` を黙って置換しない。
- 小規模正確性検証。
- N=1対FCFS回帰。
- 現行BATCH対新BATCH比較。
- 複数条件評価。
- 採否判断。
- 30反復本番は採否判断と正式方式確定後である。現時点では進まない。

具体的な実装中の確認順は、実装設計の依存関係に応じて後続節で詳細化できる。本節では、先のTerminalコマンドや将来の問題発生時対応を利用者へ一括提示する運用にはしない。利用者への作業指示は、その時点で次に実行する内容だけを提示する。

次の直接作業は、本メモを含むMarkdown差分のTerminal独立確認と、必要な文書修正である。文書確認が完了したら、対象Markdownだけを明示してstageし、commitする。commit後に、commit結果、最新commit、残存する作業ツリー変更を確認する。pushはその確認後の別指示で行う。push後にgit status、最新commit、local／remote一致を確認する。その後に、seed／RNG専用branch作成前のGit状態確認へ進む。branch作成自体はまだ行わない。Git操作は利用者がTerminalで行う。CursorにはGit操作をさせない。

## 11. 未確定事項

- seed／RNG branch名と分岐元commit
- BATCH branch名と分岐元commit
- 新BATCH試験経路の正式名称
- 新旧選択方法
- runtime設定/API
- 全World runner
- snapshot/copy方法
- 仮想World内BATCH形成停止方法
- 未割当FCFS処理
- 仮想到着collector
- audit schema
- horizon端点
- production統合方法
- 旧runtime経路の採用後の扱い
- 複数seed・networkの正式評価条件
- 性能受入れ閾値
- baseline collectorの既知test契約不一致の解決
- 30反復本番条件

## 12. 再開時の必読順

1. 本ファイル `ORDER_EXCHANGE_SEED_RNG_AND_BATCH_IMPLEMENTATION_BRANCH_STRATEGY.md`
2. `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21**
3. 同 **§32.22**
4. 同 **§32.23**
5. `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28**
6. 同 **§1H.29**
7. `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.23**
8. 同 **§21.9.24**
9. `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py`
10. baseline collector既知問題について `ORDER_EXCHANGE_PROGRESS_3.md` の該当記録

## 13. 検索語

seed改修順序、RNG改修順序、BATCH改修順序、案A、案B、案C、現行基準固定、N=1 BATCH、FCFS完全一致、exact_match、200台、1000台、5000台、10000台、fallback 38、Level 2、short TMAX、branch分離、seed branch、BATCH branch、分岐元commit、現行BATCH保全、旧BATCH維持、新BATCH試作、新旧横並び、同一commit比較、production未統合、不採用、性能不十分、正確性不合格、採否判断、全World仮想計算、baseline collector、visit_id mismatch、未解決test、production未実装、branch未作成、30反復未着手、次の作業、feature/intersection-order-control、4c6d9da、order_control_type batch、grid_n1_level_2_vs_fcfs_check、keyed randomization、arrival tiebreaker
