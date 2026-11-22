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

## 14. seed／RNG具体実装前の原典調査、反証レビュー、独立確認、補正後設計（2026-11-22）

### 14.1 記録の位置づけ

執筆日は2026-11-22である。本節は、4方式共通seed／RNG基盤の具体実装に入る前の原典調査、Cursorによる読取り専用の反証レビュー、利用者によるTerminal独立確認、および反証後に補正した具体設計の詳細正本である。後日、本節だけを読んで実装設計、実装、検証を再開できる粒度で残す。

研究契約の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** である。本節は §32.21 を覆さない。§32.21.10 で未確定だった具体実装手段を、原典の処理順と反証に合わせて具体化したものである。確定済みの研究契約を、別実装が好みであるという理由で未確定へ戻さない。

関係は次のとおりである。

- **§32.21** は route choice、arrival tiebreaker、signalized UXsim の通常 merge に関する研究契約である。production 実装は本節の時点でも未着手である。
- **§32.22** と `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1H.28** は、将来の全 World 仮想計算型 BATCH の未実装設計である。現行の実装済み BATCH Level 2 ではない。
- **§32.23**、BATCH 詳細 **§1H.29**、進捗 **§21.9.24** は、branch 分離、現行 BATCH 保全、N=1 基準固定、案 C 採用の正本である。本節は案 C を維持する。
- 全体設計側の接続は **§32.24**、進捗は **§21.9.25** である。
- 本ファイル **§1** から **§13** の「branch 未作成」「現行 branch は `feature/intersection-order-control`」は、2026-11-22 前半の記録である。削除も書換えもしない。本節時点の作業 branch は `feature/common-seed-rng-foundation` であり、分岐元 commit は `fde6865` である。remote push は未実施である。

本節の時点で、production コード、test、診断 script、research output は変更していない。simulation、pytest、py_compile は実行していない。Cursor は Git 操作を行っていない。作業ツリーには本記録と無関係な既存変更と未追跡ファイルが残っている。`research_scripts/route_choice_rng_diagnostic.py`、research output、CSV、`diagnostics/order_control.zip`、`g_0_0` には触れない。

現行 BATCH Level 2 と将来の全 World 仮想計算型 BATCH を混同しない。TVT-MP baseline 全 World と Candidate 局所 World を混同しない。signalized UXsim という比較対象と、`_transfer_normal_merge()` という production 関数の全 caller を混同しない。

### 14.2 調査・反証・独立確認の完了範囲

原典調査で読んだ production は次である。追加の広範な再調査は、本記録の作成時には行っていない。

`uxsim/uxsim.py`:

- `World.__init__`。`np.random.default_rng(seed=random_seed)` と `SeedSequence(random_seed).spawn(1)[0]` から `W.order_control_rng` を各1回作り、`W.random_seed` には引数をそのまま保存する。`None` の内部 entropy は属性として保存していない。
- `Node.generate`。origin の候補形成、`specified_route`、prefer／avoid、`W.rng.choice`、受入れ判定、`veh.link = outlink`、`outlink.vehicles.append`、その後の `begin_order_control_visit_on_link_entry`。
- BATCH 実通過。`Node.transfer_batch` 内の `_transfer_vehicle`。`_transfer_one_vehicle_between_links` とは別関数である。
- `Node.transfer_fcfs_no_clearance`
- `Node.transfer_fcfs_clearance`
- `Node._transfer_one_vehicle_between_links`
- `Node._transfer_normal_merge`。非 hard deterministic で `W.rng.shuffle` と `W.rng.choice`。
- `Node.transfer`。FCFS、BATCH、`time_value` は先に return し、それ以外が通常 merge を呼ぶ。
- `Vehicle.__init__`、`Vehicle.update`、`Vehicle.route_next_link_choice`、`Vehicle.begin_order_control_visit_on_link_entry`、`Vehicle.record_order_control_node_arrival`
- `World.copy`。`pickle.loads(pickle.dumps(W))` であり、`World.__init__` は再実行されない。

その他:

- `uxsim/order_control_baseline_driver.py`。real World を dill で1回 serialize し、bytes から baseline fork を restore する。restore 時に `World.__init__` は走らない。
- `uxsim/order_control_tvt_mp_candidate_local_state.py`。Candidate local World は `real_world.copy()` による dill copy である。
- `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`。同一 inlink 上の局所前進、target Node への新規到着登録、atomic rollback。`Vehicle.update` と `route_next_link_choice` は呼ばない。
- `uxsim/order_control_tvt_mp_candidate_binding_transfer.py`。target Node から outlink への局所物理通過。`local_vehicle.link = outlink`、`begin_order_control_visit_on_link_entry`、`outlink.vehicles.append`。
- `uxsim/order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`。`apply_copied_tvt_confirmed_ranks=False` のとき `_transfer_normal_merge()` を呼ぶ。この False 経路の確認済み caller は test であり、production baseline ではない。
- `uxsim/order_control_batch_level_2_reference.py`。mimic World と mimic Vehicle を新規作成する。全 World copy ではない。`route_next_link` を snapshot から固定する。current visit、arrival time、arrival tiebreaker、legacy 到着台帳、batch assignment を個別コピーする。待機車両に `Vehicle.update` を呼ばない。`route_next_link_choice` と `record_order_control_node_arrival` を呼ばない。mimic 内物理通過 `_transfer_vehicle_reference` は `begin_order_control_visit_on_link_entry` を呼ぶ。結果は実 World へ戻らない。
- `uxsim/order_control_tvt_mp_candidate_selection.py`。Candidate 選択専用の明示的整数 seed material、UTF-8 長さ付き serialization、`SeedSequence`。`W.rng` と `W.order_control_rng` は消費しない。今回この選択 RNG を共通 module へ同時移行しない。

影響を確認した既存 test 群:

- `tests_order_control_rng.py`
- `tests_order_control_current_visit_arrival.py`
- `tests_order_control_current_visit_state.py`
- Level 2 関連 test
- Candidate local state／advance 関連 test
- baseline collector／driver 関連 test
- route choice 関連 test
- `tests/test_other_functions.py`

確認の役割分担は次のとおりである。Cursor 反証報告を、そのまま無条件の正本にはしない。

- 原典調査は、上記関数の処理順を読んだ結果である。
- Cursor には読取り専用の反証レビューを実施させた。Cursor の総合判定は「条件を追記すれば実装へ進める」だった。blocking 反例はなかった。high 相当の条件補正は4件だった。
- 重要判断へ直接影響する Level 2 と Candidate 局所計算について、利用者が Terminal で独立確認した。
- 独立確認のあと、Candidate 局所 binding 通過について1件、Cursor 報告より強い補正を採用した。Cursor は、target Node の新規到着がコピー前に進入済みの inlink 上で起きるため、binding 経路への helper 接続は現在の tiebreaker 計算には必須ではない、と整理していた。採用した補正はそれと違う。局所 World 内で outlink へ物理進入したなら、その局所 World の Link 進入状態も更新する。理由は tiebreaker の当座の計算だけでなく、Vehicle 属性の意味を実 World、baseline 全 World、Candidate 局所 World で揃えるためである。これは §32.21 の研究契約の変更ではない。

### 14.3 総合判定

- 研究契約そのものは、現行 production の処理順と矛盾しない。
- blocking 反例はない。
- 本節の条件を具体設計へ入れれば実装へ進める。
- seed／RNG 改修を BATCH 大幅改修より先に行う案 C を維持する。順序を変える反例は、原典調査、Cursor 反証、Terminal 独立確認のいずれにもなかった。
- 新 BATCH は未実装・未採用の評価候補のままである。現行 BATCH は保全する。`order_control_type="batch"` を黙って新方式へ置換しない。
- 旧 seed 環境の旅行時間と新基盤の旅行時間が一致しないこと自体は欠陥ではない。同じ新基盤の中で FCFS と N=1 BATCH Level 2 が完全一致することを要求する。

high 相当の4条件は **§14.4**、**§14.10**、**§14.11**、**§14.12** に原因、誤った場合の影響、採用した修正、test 要件まで書く。Candidate binding の追加補正は **§14.7** と **§14.14** に書く。

### 14.4 random_seed=NoneとWorld内部entropyの正式契約

原因: `np.random.SeedSequence(None)` は呼び出しごとに OS から新しい entropy を得る。route choice、arrival tiebreaker、通常 merge RNG の用途ごとに別々の `SeedSequence(None)` を呼ぶと、同一 World の中ですら対応する key の基礎が分かれる。baseline と Candidate は dill／pickle の loads であり `World.__init__` を再実行しない。fork 側で entropy を再生成すると、実 World と copy の key が一致しない。

誤る場合の影響: §32.21.3 の「実 World と baseline を別の乱数名前空間にしない」「対応する Vehicle、場所、訪問、attempt に同じ乱数入力を与える」が満たせなくなる。

採用した修正:

- `World.__init__` で、World 生成時の内部 entropy を1回だけ確定する。`random_seed=None` のとき、用途ごとに別々の `SeedSequence(None)` を呼ばない。
- 生成時に得た entropy は、pickle 可能で、明示的に正規化された内部表現として World 属性へ保存する。内部表現の有力候補は、非負 Python 整数、または非負 Python 整数から成る明示的な列である。実際の保存形式、属性型、正規化方法は、最初の実装単位で専用 test とともに確定する。現時点では「必ず tuple である」と確定しない。
- 保存済み内部 entropy は、route choice、arrival tiebreaker、通常 merge 用 RNG の共通の基礎とする。domain separator で用途を分ける。通常 merge 用の順次消費 RNG も同じ保存済み entropy から用途を分けて派生する。
- dill／pickle の restore 時には内部 entropy を再生成しない。実 World、baseline fork、Candidate copy は保存済み属性を引き継ぐ。
- `W.rng` の現在 state から内部 entropy を導かない。state を読むと、既存 stream の消費順と Generator の内部構造に key が依存する。
- 公開属性 `W.random_seed` は従来どおり保持する。引数が `None` なら `None` のまま残す。keyed 値および通常 merge 用 RNG の正本は、生成時に保存した内部 entropy である。
- 明示的な非負 Python int seed では、独立に作成した World 同士でも同じ key に同じ値を与えられる。
- `random_seed=None` で独立に作成した別 World 同士の一致は要求しない。
- `None` の同一 World と、その World から作成した baseline／Candidate copy の一致は要求する。
- 既存の `W.rng` と `W.order_control_rng` は残す。`order_control_rng` の既存 `spawn(1)` の意味を、merge 用の子系列追加で黙って変えない。

公開入力と内部 key 入力は分ける。

公開入力側:

- `World.__init__(random_seed=...)` の公開入力互換性は、今回の seed／RNG 基盤実装だけを理由に一括変更しない。
- bool、負整数、NumPy 整数、その他の値について、既存 UXsim が現在どこまで受理しているかという公開 API 上の問題と、新しい内部 key 契約の問題を区別する。
- 今回の内部基盤実装で、seed と無関係な既存利用まで突然失敗させる広範な入力厳格化は行わない。
- 既存公開 API の正式な型契約を将来変更する場合は、今回の内部実装とは別の互換性判断として扱う。

World 生成時の内部正規化:

- `World.__init__` が受理した seed から、World 生成時に内部 entropy を一度だけ確定し、正規化する。
- 以後、route choice、arrival tiebreaker、通常 merge 用 RNG は、公開属性 `W.random_seed` をその都度読み直して seed material を作らない。
- World 生成後に `W.random_seed` が書き換えられても、保存済み内部 entropy は変更しない。
- baseline fork と Candidate copy は、正規化済み内部 entropy をそのまま引き継ぐ。
- これにより、公開属性と内部乱数正本を二重に再計算しない。

keyed helper 側:

- keyed helper は `W.random_seed` を直接受け取らない。World 生成時に正規化済みの内部 entropy だけを受け取る。
- keyed helper の内部で、公開 seed の受容可否を再判定しない。
- Vehicle 名、Node 名、Link 名、event domain、訪問番号、attempt 番号などの key 部品は、それぞれの正式型を明示的に検証する。
- bool を整数の訪問番号や attempt 番号として受け入れない。訪問番号と attempt 番号は非負 Python 整数として扱う。
- 正規化済み内部 entropy についても、内部 helper が期待する型を明示する。
- 登録時、生成時に保証した事項を、実行時の全 event で過剰に重複検証しない。
- ただし、誤った研究結果や原因不明の停止につながる重大な型不整合は、境界で明示的に検出する。

test 要件: 明示 seed の独立 World 間で同じ key が一致する。`None` の同一 World と fork で同じ key が一致する。独立な `None` World 同士は一致しなくてよい。生成後の `W.random_seed` 書き換えで保存済み key が変わらない。`W.rng` の state を key 生成が消費しない。

### 14.5 共通keyed乱数純関数の具体設計

採用理由: 共有の順次消費 RNG は、方式ごとに呼び出し回数が変わると、同じ Vehicle・Visit へ同じ乱数値が届かない。対応する確率事象だけを key にし、交通状態や候補集合の差は結果に残す。

純関数の契約:

- Python 組込み `hash()` は使わない。process と PYTHONHASHSEED で変わる。
- `id(object)` は使わない。World copy の前後で object identity は変わる。
- process や Python 起動ごとに変わる識別子を key に入れない。
- 用途ごとの domain separator を必ず含める。route choice の origin、route choice の in-trip、arrival tiebreaker は別 domain である。
- 文字列は UTF-8 bytes へ明示的に変換する。長さを先に置くなど、連結境界が曖昧にならない serialization にする。
- 整数は bool と区別する。bool を int として受け入れない。
- key 要素の型と順序を明示する。
- `W.rng`、`W.order_control_rng`、通常 merge 用 Generator の mutable state を消費しない。
- 同一内部 entropy、同一 domain、同一 key には常に同じ一様値を返す pure function とする。
- baseline 開始 timestep、方式名、実 World と baseline の区分を route-choice key に入れない。
- 同じ一様値でも、候補集合、候補順、正規化確率が異なれば選択結果は異なり得る。keyed 値は結果の強制一致ではなく、対応する確率入力を揃えるものである。
- 初期実装の置き場所は内部 module とし、`uxsim/__init__.py` から公開しない。
- keyed helper は公開の `W.random_seed` を受け取らず、読み直さない。入力は **§14.4** の正規化済み内部 entropy と、用途ごとの key 部品だけである。公開 seed の受容可否は helper 内で再判定しない。
- 短いが追跡しにくい Python 技巧より、初学者が追える明示的な手順を優先する。可読性の詳細は本小節末尾の実装原則である。

hash 方式の採用方針:

- 用途名を含む明示的 serialization を、安定した固定長 hash に渡す。
- hash 結果から、偏りのない固定的な整数、または `[0, 1)` の一様値を得る pure function を基本候補とする。
- route choice は Link 終端待機のあいだ毎 timestep 呼ばれ得る。毎 event で `SeedSequence` と Generator を作る方式は、高頻度経路の性能を確認するまで採用しない。Candidate 選択の既存 `SeedSequence` は決定回数が少なく、今回の route choice と同じ負荷ではない。
- hash algorithm、byte order、整数から float への変換式、使用 bit 数は、最初の実装単位で専用 test と一緒に確定する。本節では未確定である。
- NumPy の版をまたぐ bit 完全一致は研究契約に含めない。同一実装、同一環境、同一 key の再現性は必須である。
- 性能は未実測である。実装後に軽量 benchmark、または既存規模の回帰で確認する。性能は N=1 一致性の合否条件にしない。

Candidate 選択との境界: `order_control_tvt_mp_candidate_selection.py` の既存ローカル RNG は、今回の共通 module へ同時に移行しない。既存の明示的 seed material は将来の整理候補として残す。今回の実装範囲に含めない。二重化は保守上の未整理として記録し、今回の研究契約を満たすための必須作業にはしない。

カテゴリ選択は **§14.8** のあと、origin と in-trip の共通規則として次のとおりとする。

- keyed helper は基本的に `[0, 1)` の一様値を1つ返す。
- 候補 Link の順と確率ベクトルの対応を固定する。現行の候補順を、再現性のためだけに並べ替えない。prefer／avoid 適用後に現行コードが名前順へ並べる箇所は、その現行順を維持する。
- 実 World と copy で候補順が同じなら、同じ一様値と同じ確率から同じ Link が選ばれる。候補集合または順序が異なれば結果は異なり得る。
- preference 合計が正なら、正規化した累積確率へ一様値を対応させる。
- preference 合計が0で候補が2件以上なら、候補間の一様カテゴリ選択とする。
- `u=0`、累積境界、丸め誤差、最後の候補への fallback を専用 test で固定する。
- NumPy の `Generator.choice(..., p=...)` を呼ばず、1つの keyed 一様値から明示的なカテゴリ選択を行う方式が、共有 stream を消費せず、処理を追える点で有力である。
- 受入れ条件は、現行 `choice` との bit 互換ではない。研究契約上の確率の意味と、同一 key の再現性である。旧 seed の選択結果との数値一致は要求しない。

Python 実装の可読性原則:

研究用コードでは、正しく動くことを最優先する。時間価値取引および4方式共通 seed／RNG 基盤の根幹部分では、短さや技巧性より、Python 初心者が後から処理を追える可読性を優先する。

- 高度な Python テクニックを使わなくても明示的に書ける場合は、少し長くても明示的な実装を選ぶ。
- 複雑な内包表記、過度な関数合成、暗黙的な型変換、技巧的な iterator 処理、短縮のための多段式、読み解きにくい汎用化を避ける。
- key の各構成要素、serialization の順序、domain separator、整数変換、カテゴリ選択、counter 更新位置は、コード上で個別に追跡できるようにする。
- 中間変数には役割が分かる名前を付ける。
- 条件分岐は、候補0件、1件、2件以上、hard deterministic、`specified_route` などの研究契約がコード上で見えるようにする。
- helper は責務を狭くし、1つの helper に seed 正規化、key 構築、hash、カテゴリ選択、counter 更新を過度に詰め込まない。
- コメントと docstring には、Python 処理だけでなく、その処理が交通上、研究上何を意味するかを書く。
- 高度なテクニックが正確性、性能、標準ライブラリとの整合などの理由で本当に必要な場合は使用してよい。その場合は、なぜ単純な方法では不十分なのか、入力、出力、不変条件、例外、再現性への影響をコメントまたは docstring で明示する。
- コードの短さや「美しさ」だけを理由に、高度な技巧を採用しない。
- 既に確定した研究契約を、コードを短くする目的でまとめたり省略したりしない。

今後 Cursor へ production 実装を依頼する際は、この可読性原則を指示本文へ必ず含める。Cursor には、編集と実装に必要な原典確認だけを行わせる。py_compile、pytest、simulation、grep など Terminal で実行できる確認は、原則として利用者が Terminal で行う。Cursor に Git 操作を行わせない。実装指示を修正する場合は、差分だけでなく修正版全文を提示する。

### 14.6 Vehicleへ追加する最小状態

`Vehicle.__init__` で次を初期化する。mimic の `addVehicle` もこの初期値を持つ。Level 2 はそれを参照しない。

- Link 別進入回数を保持する dict。初期値は空 dict。
- 現在 Link 訪問中の確率的 in-trip route-choice attempt 数。初期値は 0。
- origin の確率的 route-choice attempt 数。初期値は 0。

意味:

- Link 別進入回数は、その Vehicle が各 Link へ物理的に進入した累積回数である。進入に失敗した試行では増えない。同じ Link へ loop で再進入すれば増える。
- 現在 Link 訪問中 attempt は、今乗っている Link の終端で行った確率的 in-trip 選択の回数である。新しい Link へ進入したとき 0 に戻す。
- origin attempt は、最初の Link へ入る前に行った確率的 origin 選択の回数である。進入に失敗して次 timestep に再試行し、候補が2件以上なら増え続ける。最初の Link へ入れても origin attempt は 0 に戻さない。
- 現在 Link への進入回数を、別属性として重複保存しない。現在 Link は `vehicle.link` から取り、その訪問番号は Link 別進入回数から取る。
- Node 別訪問 counter を第二の永続的正本として追加しない。
- `order_control_visit_id` は order-control 対象 Node の Visit だけを数える。全 Link の route choice 識別には使わない。
- `log_t_link` は監査に使える。更新は Link 進入瞬間ではなく後続の `record_log` であるため、key の正本にしない。
- `reduce_memory_delete_vehicle_route_pref` は行程終了時に `route_pref` を消す。新しい counter と attempt は消さない。

dict の key:

- Link 名は World 内で一意であり、auto rename 後の正式名も World と copy の間で保存される。auto rename 自体は Node、Link、Vehicle の生成時に `W.rng` を使う既存処理であり、今回の keyed route choice へ置き換えない。
- Link object を dict key にすると、同一 pickle グラフの中では復元できても、実 World と copy の対応を説明する key としては不向きである。
- Link の整数 ID は追加順に依存する。
- 実装上の有力案は、正式 Link 名を key にすることである。
- 最終決定は、pure keyed helper の serialization と同時に行う。未確定である。
- いずれの key でも、実 World とその copy が同じ論理 Link を同じ key として認識することを専用 test で確認する。

### 14.7 Link物理進入時の共通状態更新

共通 helper を新設する。正式な関数名は未確定である。

責務:

- 呼び出し時点で `vehicle.link` は進入後の Link を指している。
- その Link の進入回数を 1 増やす。
- 現在 Link 訪問中の in-trip attempt を 0 に戻す。
- order-control Visit の開始とは責務を分ける。
- helper の直後に、既存の `begin_order_control_visit_on_link_entry()` を呼ぶ。
- helper を `begin_order_control_visit_on_link_entry()` の内部へ埋め込まない。現行 Level 2 mimic は同じ begin を呼ぶが、正式な Link 訪問状態の更新対象ではない。内部へ入れると mimic 通過まで自動的に数える。
- 同じ進入で helper を2回呼ばない。二重計上になる。

通常 production で接続する5経路:

1. `Node.generate()` の origin 進入成功
2. BATCH 実通過内の `_transfer_vehicle`
3. `Node.transfer_fcfs_no_clearance()`
4. `Node.transfer_fcfs_clearance()`
5. `Node._transfer_one_vehicle_between_links()`

既存順序と接続位置:

- origin の `Node.generate` だけ、受入れ成功後に `veh.link = outlink` とし、車線と leader を整えたあと `outlink.vehicles.append(veh)` を行い、その後に `begin_order_control_visit_on_link_entry()` を呼ぶ。append が Visit 開始より前にある。helper は begin の直前に1回置く。受入れ失敗の `break` より前には置かない。選択そのものは受入れ判定より前に終わっている。attempt の増分は helper ではなく、選択成功の直後である。
- BATCH `_transfer_vehicle`、両 FCFS、`_transfer_one_vehicle_between_links` は、元 Link から pop したあと `vehicle.link = outlink` とし、直ちに `begin_order_control_visit_on_link_entry()` を呼び、車線処理と走り残しのあと `outlink.vehicles.append` を行う。append は Visit 開始より後である。helper は `vehicle.link = outlink` のあと、begin の直前に1回置く。

Candidate 局所 binding 通過にも同じ helper を接続する。これは Terminal 独立確認のあとに採用した補正である。詳細は **§14.14**。

接続しない経路:

- 進入失敗。origin で容量または入口空間が足りず `break` する場合。attempt は、2件以上の選択が成功していれば既に消費済みである。Link 回数は増えない。
- `Vehicle.end_trip`。`link = None` にするが、過去の累積回数は戻さない。
- Candidate 局所前進。同一 inlink 上の位置更新と target Node 到着登録であり、Link 進入ではない。
- 現行 Level 2 の `_transfer_vehicle_reference`。begin は呼ぶが、共通 helper は接続しない。

共通原則:

- 容量、入口空間などの通過判定を通過し、Link 進入を実行する経路だけで回数を増やす。
- helper のあとで例外が起きても、現行の物理移動は既に容量減算、元 Link からの除去、`vehicle.link` の変更を行っている経路がある。新しい counter だけ更新を遅らせても、その経路が atomic になるわけではない。
- 各経路について、既存の不可逆更新と helper の位置関係を専用 test で確認する。

### 14.8 origin route choiceの具体契約

対象は `Node.generate()` である。

候補形成:

- 現行どおり出発 Node の outlink 一覧を取る。
- `specified_route` の現行の整合性確認を維持する。不一致は現行どおり `ValueError` であり、attempt は増やさない。
- `specified_route` がないとき、現行どおり `links_prefer` と `links_avoid` を適用する。
- 適用後の最終候補数で、0件、1件、2件以上を分ける。`len(outlinks)` をフィルタの前だけで見ない。現行コードはフィルタ前の長さで分岐したあと、空になったリストへ `W.rng.choice` を呼び得る。

0件、1件、2件以上の共通規則は **§14.10**。

2件以上かつ `hard_deterministic_mode=False`:

- key は、保存済み内部 entropy、Vehicle の不変識別子、event 種別 `origin`、origin Node の不変識別子、その時点の origin attempt 番号、origin 用 domain separator である。
- Vehicle と Node の不変識別子は、方式間で同じになる正式名、または検証済みの永続 ID とする。`id(object)` は使わない。
- preference 合計が正なら、その重みでカテゴリ選択する。合計が0なら候補間の一様選択とする。どちらも確率的選択であり、attempt を消費する。
- 選択が正常に完了したあとで origin attempt を 1 増やす。
- その後の入口空間、流入容量の判定で進入できなくても、attempt は戻さない。次 timestep の再試行は新しい attempt である。
- したがって attempt の増分位置は、選択成功の後、受入れ判定の前である。

`hard_deterministic_mode=True`:

- 現行の `max(zip(preference, outlinks))` を維持する。同点のとき現行の最初の最大を維持するため、候補順を変えない。
- keyed 値を作らない。attempt を増やさない。

`specified_route`:

- 確率選択の対象外である。現行コードは1本に絞ったあとでも非 hard deterministic なら `W.rng.choice` を呼ぶ。新しい契約では、この choice を行わない。attempt も増やさない。

例外:

- 候補生成、preference 取得、正規化、key 生成、カテゴリ選択の途中で例外が出た場合、attempt だけは進めない。
- 選択が正常に成立したあと、物理進入に失敗した場合は attempt を消費済みとする。

### 14.9 in-trip route choiceの具体契約

対象は `Vehicle.route_next_link_choice()` である。呼び出し元は `Vehicle.update()` の Link 終端であり、taxi が次の目的地へ進む分岐も同じ関数を呼ぶ。

維持する現行契約:

- 目的地が現在 Link の終端 Node であり `mode` が `single_trip` のときは、この関数を呼ばず行程終了の準備へ進む。route choice も attempt も発生しない。
- dead end で `trip_abort` が有効なときは、`route_next_link = None` として行程終了の準備へ進む。この関数は呼ばない。
- taxi は目的地で `route_pref_update` のあとこの関数を呼ぶ。専用の別 attempt は作らず、in-trip 契約を使う。
- `specified_route` は、現行どおり `log_t_link` の本数から次 Link を決める。この索引計算は今回直さない。確率選択ではなく、attempt を増やさない。
- hard deterministic は現行の max 選択を維持し、keyed 値も attempt も使わない。

確率的分岐:

- `specified_route` がないとき、終端 Node の outlink に prefer／avoid を適用した最終候補数を使う。
- 0件、1件、2件以上は origin と同じ原則である。**§14.10**。
- 2件以上かつ非 hard deterministic の key は、保存済み内部 entropy、Vehicle の不変識別子、event 種別 `in_trip`、現在 Link の不変識別子、その Vehicle による当該 Link の訪問番号、現在 Link 訪問中の attempt 番号、in-trip 用 domain separator である。
- 訪問番号は、その時点の Link 別進入回数である。進入時に既に増えているので、その Link への最初の滞在は 1 である。0 始まりに読み替えない。
- 選択が正常に完了したあと、現在 Link 訪問中 attempt を 1 増やす。
- `Vehicle.update` は、車両が Link 終端に留まるあいだ、毎 timestep この関数を呼ぶ。候補が2件以上なら、待機の各 timestep は別 attempt である。
- 同じ Visit の arrival tiebreaker は再生成しない。`record_order_control_node_arrival` は current visit の到着が記録済みなら return する。route choice の再実行と tiebreaker の再生成を混ぜない。
- 新しい Link へ進入したとき、共通 helper が in-trip attempt を 0 に戻す。

### 14.10 候補outlink 0件・1件・2件以上の分岐

これは high 相当の条件補正の2件目である。

原因: `Node.generate` と `Vehicle.route_next_link_choice` は、prefer／avoid の前に outlink が1本以上あることを見る。その後の集合演算で最終候補は0件になり得る。現行の非 hard deterministic は、preference 合計が0のとき空の配列へ `W.rng.choice` を呼び、失敗し得る。

誤る場合の影響: 0件を1件の直接選択と同じ経路にすると、選択の余地がないのに成功する。0件で attempt を進めると、「確率的選択を実行した回数」という §32.21.3 の意味から外れる。空の choice のままにすると、失敗位置が偶発的で原因が追えない。

採用した修正:

- 最終候補0件では乱数を使わない。attempt を消費しない。
- 現行の選択不能を、成功経路へ変えない。`route_next_link = None` などの新しい救済は導入しない。
- 空配列へ `choice` を投げる偶発的失敗ではなく、最終候補0件を明示的に検出し、原因が分かる失敗とする実装が有力である。例外型と文面は実装時に決める。
- 最終候補1件は、その Link を直接選ぶ。keyed 値を作らない。attempt を増やさない。`specified_route` で1本に絞られた場合も同様に確率選択しない。
- 最終候補2件以上かつ非 hard deterministic だけ、keyed 一様値からカテゴリ選択し、選択成功後に attempt を1増やす。
- preference 合計が0かつ2件以上は、一様カテゴリ選択であり、attempt は消費する。

test 要件: 0件、1件、2件以上、preference 合計0の2件以上を分ける。prefer と avoid の組合せで0件になるケースを含める。`specified_route` と hard deterministic では attempt が増えないことを含める。

### 14.11 arrival tiebreakerとNode訪問番号

生成契約は `Vehicle.record_order_control_node_arrival` に置く。

- `order_control_eligible` でない Node、および `order_control_type == "none"` では現行どおり何もしない。signalized UXsim の通常実 World へ arrival tiebreaker を新規導入しない。
- current visit が無い、または visit の Node が到着 Node と違うときは、現行どおり `ValueError` とする。
- 同一 current visit に `arrival_time` と `arrival_tiebreaker` が既にあるときは、現行どおり return する。`incoming_vehicles` への再登録で再生成しない。
- 片側だけ埋まっている不整合は、現行どおり `ValueError` とする。
- 初回だけ、legacy の `order_control_node_arrival_times` と `order_control_node_arrival_tiebreakers` へ書く。再訪では legacy 辞書を上書きせず、current visit だけへ書く。
- 初回を `W.rng.random()`、再訪を `W.order_control_rng.random()` とする分岐は廃止する。どちらも keyed 値にする。
- key は、保存済み内部 entropy、Vehicle の不変識別子、Node の不変識別子、Node 訪問番号、arrival-tiebreaker 用 domain separator である。inlink 名は入れない。
- baseline collector が存在するときは、現行どおり生成済みの tiebreaker を記録する。collector を別の乱数正本にしない。
- `record_order_control_node_first_arrival` は定義があるが、今回確認した production caller はない。新しい正本は `record_order_control_node_arrival` である。死んでいる helper を、共有 `W.rng` の消費元として復活させない。

Node 訪問番号:

- 当該 Node を終端とする全 inlink について、その Vehicle の Link 別進入回数を合計する。
- production で正しく進入したあとの初回到着なら、車両はまだその inlink 上にあり、進入時に増やした回数が合計に含まれる。初回は 1 である。
- 同じ Node へ loop して再訪すれば 2 以上である。別の inlink から戻っても、合計が次の番号になる。
- 例: 3本の inlink への進入回数が 2、1、0 なら、Node 訪問番号は 3 である。これは §32.21.6 の例と同じである。
- 別の永続 Node counter は追加しない。`order_control_visit_id` とは別の概念である。visit id を Node 訪問番号の代わりに使わない。

合計0は、high 相当の条件補正の3件目である。

原因: 手動 fixture は Vehicle を Link へ直接置き、`begin_order_control_visit_on_link_entry` と到着記録だけを呼ぶ。新しい counter を通らないので合計は 0 である。`tests_order_control_current_visit_arrival.py` がこの形である。

誤る場合の影響: 合計0を黙って訪問番号1にすると、production の helper 接続漏れも正規の初回 Visit として通過し、進入回数の欠落を隠せない。

採用した修正:

- 到着記録時に合計が 1 未満なら、明示的な不整合として停止する。訪問番号1へ補正しない。
- 手動 fixture を production の自動補正対象にしない。fixture を共通 helper 経由に変えるか、テストが進入回数を明示的に置く。
- fixture の救済と production 契約を混同しない。

test 要件: 初回は 1。同一 Node の再訪は 2 以上。異なる inlink からの再訪で合計が増える。helper を通さない到着は失敗する。同一 Visit の再登録では値が変わらない。legacy の初回値を再訪で上書きしない。

World 別:

- 実 World は、5経路と Candidate 以外の正式進入で回数を更新し、到着時に key を作る。
- baseline 全 World は、snapshot 時点の Vehicle 属性を copy する。その後の進入も通常 production の5経路で更新する。snapshot 時点で到着済みの Visit は既存値のままである。snapshot 後に baseline 内で新規到着する Visit は key から値を得る。
- Candidate 局所 World は **§14.14**。

rollback:

- Candidate 局所前進の失敗時は、現行 snapshot が戻しているものを維持する。対象は、位置、速度、`x_old`、`x_next`、`move_remain`、`route_next_link`、`incoming_vehicles`、current visit の arrival time と tiebreaker、legacy 到着辞書、baseline collector の到着 field、`W.rng` state、`W.order_control_rng` state である。
- keyed tiebreaker は共有 stream を消費しない。局所前進は Link 進入回数と attempt を変えない。これらを rollback 対象に追加しない。
- Candidate binding 通過は別処理であり、局所計算の通常成功経路として扱う。前進失敗の rollback と混ぜない。
- `W.rng` と `W.order_control_rng` の rollback は、同じ atomic 区間に他用途が残る可能性があるため、今回直ちに削除しない。

### 14.12 通常merge用順次消費RNG

これは high 相当の条件補正の4件目である。

原因: `_transfer_normal_merge()` は signalized UXsim だけの関数ではない。`Node.transfer` は FCFS、BATCH、`time_value` を先に return し、残りの通常 Node が信号の有無を問わずこの関数を呼ぶ。`order_control_tvt_mp_physical_transfer.py` は、`apply_copied_tvt_confirmed_ranks=False` のとき同じ関数を呼ぶ。確認済みのその caller は test である。production の TVT-MP baseline は `apply_copied_tvt_confirmed_ranks=True` であり、この通常 merge 経路を使わない、という §32.21.7 は維持する。

誤る場合の影響: 名称を「signalized 専用」のまま関数全体へ置くと、信号のない通常 Node と test の generic fork まで「信号専用の乱数」と呼ぶことになる。逆に信号の有無で分岐すると、同じ関数の中に二つの乱数正本ができ、通常 merge の再現範囲が割れる。FCFS、BATCH、確定順位 TVT へこの RNG を入れるのは、研究契約違反である。

採用した修正:

- 実装名称は「通常 merge 用の順次消費 RNG」とする。「signalized 専用 merge RNG」とは呼ばない。
- 研究上の文「4方式比較のうち、通常 merge 選択を使うのは signalized UXsim である」は維持する。これは比較対象の説明であり、関数の全 caller の説明ではない。
- `World.__init__` で、通常 merge 用の独立した順次消費 Generator を1本作る。
- `random_seed=None` も明示整数も、**§14.4** の保存済み内部 entropy から用途を分ける。別の `SeedSequence(None)` は呼ばない。
- `W.rng` を消費しない。`W.order_control_rng` とは別 object である。
- `order_control_rng` は今回削除しない。既存 `spawn(1)` へ無造作に子を足して、既存 `order_control_rng` の系列を変えない。既存テストが二つの World の `order_control_rng` の一致を見ているため、派生順は両方の World で同じであり、かつ既存系列を維持する。
- 使用箇所は `_transfer_normal_merge()` の非 hard deterministic 分岐だけである。outlink 処理順の shuffle と、merge 候補 Vehicle の choice の双方に、同じ通常 merge 用 RNG を使う。
- 信号の有無による追加分岐は設けない。
- `hard_deterministic_mode=True` では現行どおり shuffle も choice もせず、この RNG を消費しない。
- FCFS、BATCH、TVT-MP の確定順位処理では使わない。これらの経路は `Node.transfer` の先の return、または確定順位の通過処理であり、`_transfer_normal_merge()` に入らない。
- test-only の generic normal merge は、通常 merge を実行する以上、同じ RNG を使う。production の確定順位経路へ広げる意味ではない。
- baseline 全 World で通常 merge が実行される場合は、copy された Generator の state から続ける。copy 後は別 object である。
- 通常 merge は方式間の keyed 対応を目的としない。逐次消費型を維持する。Node 名、timestep、ループ番号を key にしない、という §32.21.7 は維持する。

専用 test: 通常 merge でのみ state が進む。FCFS、BATCH、TVT-MP 確定順位では進まない。hard deterministic では進まない。同一明示 seed と同一処理で再現する。World copy 後は copy 時点の state を持つが Generator object は別である。`W.rng` と `W.order_control_rng` の state を変えない。

### 14.13 baseline全Worldの扱い

- baseline driver は real World を dill で1回 serialize し、bytes から fork を restore する。
- restore 時に `World.__init__` は再実行されない。保存済み内部 entropy、通常 merge 用 RNG の state、Vehicle の Link 進入回数と attempt は、属性として copy される。
- baseline 開始時刻を route choice の key に入れない。実 World と baseline は同じ保存済み entropy と、同じ論理 event の key を使う。
- snapshot 時点までに消費した origin attempt と in-trip attempt を引き継ぐ。
- snapshot 後に baseline 内だけで起きた Link 進入と route choice は、fork 内の状態だけを更新する。実 World へ戻さない。
- snapshot 時点で到着済みの arrival tiebreaker は再生成しない。
- snapshot 後に新規到着した Visit は key から生成する。
- baseline collector は、生成済み tiebreaker を記録する。別の乱数正本にしない。

### 14.14 Candidate局所Worldの扱い

生成: Candidate local World は `real_world.copy()` による dill copy である。保存済み内部 entropy と Vehicle 属性は copy される。`World.__init__` は再実行されない。

やらないこと:

- 通常の `Vehicle.update()` を呼ばない。
- 通常の `route_next_link_choice()` を呼ばない。
- 通常の確率的 route choice の keyed 乱数を導入しない。
- 進路は、binding 進路、baseline 由来進路、既存の決定的代替進路の契約を維持する。
- copy 内の変更を実 World へ戻さない。

局所前進は Link 進入ではない。同一 inlink 上で位置を進め、target Node へ新規到着する車両だけを `incoming_vehicles` に足し、`record_order_control_node_arrival` を呼ぶ。Link 進入回数と attempt はここでは増やさない。新規到着の Node 訪問番号は、copy 時点までにその inlink へ進入した回数を含む合計から得る。

binding 通過についての補正:

Cursor 反証は、target Node への新規到着が「コピー前に進入済みの inlink 上」で起きるため、binding 経路へ helper を付けなくても、その到着の訪問番号は崩れない、と整理した。この範囲の読取りは、局所前進だけを見る限り成り立つ。

Terminal 独立確認のあと、実装設計としては次を採用する。Cursor の「現在の到着計算には必須ではない」を、helper を付けない理由にはしない。

- Candidate の binding passage が成立すると、局所 Vehicle は対象 Node から outlink へ物理的に移る。順序は `local_vehicle.link = outlink`、`begin_order_control_visit_on_link_entry()`、その後の `outlink.vehicles.append` である。
- その後、Vehicle は outlink 上を進められ、下流端の boundary 処理により退出、sink 相当として扱われる。
- その先の下流 Node へ、通常の Vehicle として進入させない。新しい Node Visit を開始しない。通常の route choice を発生させない。
- したがって、outlink の先の Link への進入回数は、この局所計算では発生しない。
- それでも、局所 World の中で outlink へ物理進入した事実は、Link 進入回数を1増やし、その outlink 訪問中の in-trip attempt を0に戻す対象である。共通 helper を、begin の直前に接続する。
- Candidate 局所計算は通常の確率的 route choice を実行しない。helper で 0 に戻した attempt は、その後増えない。
- この更新は copy 内だけであり、実 World の counter へ戻さない。
- これは §32.21 の研究契約の変更ではない。正式状態の意味を、実 World、baseline 全 World、Candidate 局所 World で揃える具体実装上の補正である。
- Candidate 局所 World で Link 進入状態を更新する方針は、**§14.15** の現行 Level 2 mimic の限定的例外とは矛盾しない。Level 2 mimic は正式な将来交通状態を継続する World ではなく、Candidate 局所 World は copy された正式 Vehicle 状態を用いて計算を続ける。

不正確な説明として残さないもの: 「Candidate 計算では outlink の先へ進めず、次の Node へ到着させない。」正確には、outlink へ物理進入し、outlink 上を下流端まで処理する。下流端では boundary により退出、sink 相当として扱う。下流 Node へ通常進入させず、新しい Node Visit と通常 route choice は発生させない。

rollback は **§14.11** のとおり、局所前進の失敗に対する既存 atomicity を維持する。binding 通過の成功経路を、前進失敗の rollback に混ぜない。

### 14.15 現行BATCH Level 2 mimicの扱い

原典:

- 現行 Level 2 は全 World copy ではない。`_build_mimic_world` が `mimic_random_seed` で別 World を作り、`_create_mimic_vehicle` が `mimic_W.addVehicle` で新しい Vehicle を作る。
- 新しい Vehicle 属性は `Vehicle.__init__` の初期値になる。Link 別進入回数は空、attempt は 0 である。
- `route_next_link` は実 World の snapshot から固定してコピーする。
- 待機車両に `Vehicle.update` を呼ばない。`_run_limited_virtual_loop` にその旨がある。
- `route_next_link_choice` を呼ばない。
- `record_order_control_node_arrival` を呼ばない。inlink 上の仮想到着は `incoming_vehicles` への追加と、通過時刻観測用の dict だけである。
- mimic 内の物理通過 `_transfer_vehicle_reference` は `begin_order_control_visit_on_link_entry` を呼ぶ。
- current visit、arrival time、arrival tiebreaker、legacy 到着台帳、batch assignment、`order_control_visit_id` は個別コピーしている。
- mimic の結果は実 World へ戻らない。実 World の `W.rng` を消費しない。

採用方針:

- Link 別進入回数、origin attempt、現在 Link 訪問中 attempt は追加コピーしない。
- mimic 内で通常 route choice も新規 arrival tiebreaker 生成も行わない。現行 Level 2 の通過時刻推定には、これらの新状態は不要である。
- mimic 内物理通過へ共通 Link 進入 helper を接続しない。
- begin の内部へ helper を埋め込まない理由の一つが、この経路である。
- 新属性は mimic Vehicle 上に初期化されるが、現行 Level 2 は参照しない。
- snapshot 時点の既存 arrival tiebreaker は、従来どおりコピーして使う。
- 軽量 counter、resolved、unresolved、Level 1 fallback、実 World 非変更は維持する。
- この「コピーしない」は、将来の全 World 仮想計算型 BATCH には適用しない。将来方式は World 全体を copy する予定であり、その時点では正式な Vehicle 状態が copy に含まれる。現行 Level 2 の個別コピー契約を、将来方式の省略ルールとして読まない。
- seed／RNG 改修を BATCH 大幅改修より先に行う順序を変える根拠はない。Level 2 は別 World であり、実 World の共有 stream を route choice と tiebreaker から外しても、N=1 の比較構造は残る。一致の再確認は実装後に行う。

現行 Level 2 mimic は、正式な交通 World 状態を将来まで継続する World ではない。目的は、対象 Node に関する局所的な通過時刻推定である。mimic Vehicle は、実 World Vehicle の正式な将来状態を構築するものではない。mimic 内の物理通過後に作られる Vehicle 状態は実 World へ戻さない。mimic 内で生成された新しい Link 上の状態を、その先の通常 route choice や新しい arrival tiebreaker 生成へ利用しない。したがって、mimic Vehicle 上で `Vehicle.__init__` により初期化される新しい Link 進入回数と attempt 属性は、現行 Level 2 では正式な交通状態として参照しない未使用の初期値である。現行 Level 2 は、mimic 内物理通過後の全 Vehicle 属性について、実 World、baseline、Candidate と同じ将来状態の意味的一貫性を保証する対象ではない。そのため、mimic 内物理通過へ共通 Link 進入 helper を接続しない。この例外は、現行 Level 2 の局所的な参照計算に限定する。Candidate 局所 World は、copy された正式 Vehicle 状態を用いて Candidate 計算を継続するため、Candidate binding 通過では局所 World 内の Link 進入状態も更新する。Candidate 局所 World と Level 2 mimic は、目的、生成方法、状態の利用範囲が異なる。将来の全 World 仮想計算型 BATCH には、この Level 2 例外を適用しない。将来 BATCH は正式 World 全体を copy して継続する設計なので、正式 Vehicle 状態を維持する必要がある。

### 14.16 既存testへの影響と新規専用test

旧 seed の旅行時間や選択結果と数値が違うこと自体は、回帰失敗ではない。新契約へ更新すべき expected value と、順位、容量、clearance、同一 Visit 不変、実 World 非変更のような交通契約の破壊を分ける。

`tests_order_control_current_visit_arrival.py`:

- 初回 tiebreaker を `W_ref.rng.random()` と直接比較する期待は、更新対象である。
- 再訪 tiebreaker を `W_ref.order_control_rng.random()` と直接比較する期待も、更新対象である。
- 同一 Visit の再登録で値が不変であること、legacy の初回値を再訪で上書きしないこと、片側だけ埋まった状態を拒否することは維持する。
- 進入回数の合計が0の fixture は、helper 経由か明示的な回数設定へ変える。production 側で1に補正してテストを通さない。

`tests_order_control_rng.py`:

- `W.rng` と `W.order_control_rng` の存在、別 object であること、同一明示 seed での再現、片方が他方の消費に影響しないことは維持する。
- `random_seed=None` で両 Generator が使える、という現行テストの意味は維持する。`None` の独立 World 同士の乱数列一致は、このテストも要求していない。
- 通常 merge 用 RNG の存在、独立性、copy、非消費経路のテストを追加する。

route choice の専用 test で分けるもの: `links_prefer`、`links_avoid`、`specified_route`、hard deterministic、0件、1件、2件以上、preference 合計0、origin 進入失敗後の再試行、Link 終端待機後の再試行、taxi の次 destination、dead end。

Link 進入状態の専用 test で分けるもの: origin、BATCH 実通過、clearance なし FCFS、clearance あり FCFS、`_transfer_one_vehicle_between_links`、Candidate binding の局所通過、進入失敗、行程終了、loop 再進入、新しい Link 進入時の attempt の 0 リセット、Level 2 へ helper を接続しないこと。

World copy と baseline: 明示 seed の独立 World で同じ key。`None` の同一 World と fork で同じ key。独立な `None` World は一致不要。copy 後の Vehicle 状態。copy 後の通常 merge RNG の state。Generator object は別であること。

Candidate: keyed 化後も到着欄、legacy 辞書、collector の rollback を維持する。局所前進は Link 進入状態を変えない。binding 通過は局所 World の Link 進入状態を更新する。実 World へ戻らない。下流 Node の新しい Visit と通常 route choice が発生しない。

Level 2: route choice を使わない。新しい tiebreaker を生成しない。実 World の RNG を変えない。軽量 counter、fallback、N=1 対 FCFS。

既知の別問題: `tests_order_control_baseline_collector_uxsim.py` の `test_batch_passage_stops_before_physical_transfer_on_inconsistency` は、visit_id mismatch 例外を期待し、現行 collector 契約と一致しない。記録は `ORDER_EXCHANGE_PROGRESS_3.md` にある。今回の seed／RNG 改修では解決済みにしない。この不一致だけで、通常実行の N=1 一致性を否定しない。

`tests/test_verification_route_choice.py` と例外系、`tests/test_other_functions.py` に、逐次 `W.rng` の旧選択結果を固定した期待がある場合は、期待値の更新対象である。未読の個別 assertion が残っていても、それを交通契約の破壊と決めつけない。実装単位の中で該当テストを読んで分ける。

### 14.17 実装単位と単位ごとの受入れ条件

ここからの見出しは仮であり、正式な Phase 名や Step 名ではない。大きな一括実装にしない。各単位は、production 変更、専用 test、既存回帰、記録が終わるまで次へ進まない。実装は **§14.5** の可読性原則に従い、初心者が処理を追える明示的な Python を優先する。Git の stage、commit、push、branch 操作は利用者が Terminal で行う。Cursor には行わせない。Cursor には編集と実装に必要な原典確認だけを行わせ、py_compile、pytest、simulation、grep など Terminal で実行できる確認は利用者が行う。利用者への作業指示は、その時点で次に実行する内容だけを提示する。実装指示を修正する場合は、差分だけでなく修正版全文を提示する。

仮: 内部 entropy と pure keyed helper。

- production の変更候補は、World 内部 entropy の1回の確定と正規化、その pickle 可能な保存、内部 serialization、stable hash、`[0, 1)` の一様値、domain separation だけである。保存形式は tuple と断定せず、この単位の専用 test で確定する。
- keyed helper は正規化済み内部 entropy だけを受け取る。公開の `W.random_seed` は都度読まない。公開 API の一括厳格化はこの単位で行わない。
- 専用 test は、同一 key の一致、key の差異、文字列境界、型境界、bool を訪問番号や attempt として拒否すること、`None` の fork 一致、明示 seed の独立 World の一致、World copy、mutable RNG の非消費、生成後の `W.random_seed` 書き換えで内部 entropy が変わらないこと、軽量な性能確認である。
- 受入れ条件は、既存の route choice など production の選択挙動をまだ変えないこと、既存テストの無関係な結果を変えないこと、内部 module を公開しないこと、**§14.5** の可読性原則に沿っていることである。

仮: Vehicle 状態と Link 進入 helper。

- production の変更候補は、Vehicle の3属性、共通 helper、通常 production の5経路、Candidate binding の局所通過である。
- 専用 test は、進入成功、進入失敗、loop、attempt の reset、Candidate copy 内だけの更新、Level 2 へ接続しないことである。
- 受入れ条件は、route choice の乱数と arrival tiebreaker をまだ変えないこと、既存の交通結果を変えないこと、5経路と binding 通過に接続漏れがないことである。

仮: origin と in-trip の keyed 化。

- production の変更候補は `Node.generate` と `Vehicle.route_next_link_choice` である。
- 専用 test は **§14.10** と **§14.16** の route choice 項目である。
- 受入れ条件は、keyed 値以外の共有 stream を消費しないこと、attempt 契約を満たすこと、旧確率結果との一致を要求しないこと、hard deterministic と `specified_route` の意味を維持することである。

仮: arrival tiebreaker の keyed 化。

- production の変更候補は `record_order_control_node_arrival` である。
- 専用 test は初回、再訪、複数 inlink、loop、同一 Visit 再登録、合計0の不整合、baseline の新規到着、Candidate の新規到着、legacy 辞書、collector である。
- 受入れ条件は、`W.rng` と `W.order_control_rng` を消費しないこと、current visit と legacy の契約を維持すること、Candidate 局所前進の rollback を維持することである。

仮: 通常 merge 用 RNG。

- production の変更候補は、World の通常 merge 用 Generator と `_transfer_normal_merge` である。
- 専用 test は **§14.12** のとおりである。
- 受入れ条件は、通常 merge の非 hard deterministic 分岐だけに適用すること、信号の有無で不要な分岐をしないこと、既存 `order_control_rng` の系列を壊さないことである。

仮: 統合回帰。

- 専用 test の全件、影響する既存 test、小規模な4方式確認、FCFS 対 N=1 BATCH Level 2 を行う。
- 受入れ条件は **§14.18** である。この回帰の前に、新 BATCH の実装へ進まない。

### 14.18 N=1 BATCH対FCFS回帰契約

- seed／RNG 改修後に、旧 seed 環境の旅行時間などとの数値一致は要求しない。
- 同じ新しい seed／RNG 基盤の中で、FCFS と N=1 BATCH Level 2 の完全一致を要求する。
- 比較 field は既存診断 `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py` の契約を維持する。
- 集計は `total_vehicles`、`completed_trips`、`unfinished_trips`、`completed_ratio`、`total_travel_time`、`average_travel_time`、`average_delay`、`delay_ratio`、`total_distance_traveled`、`last_completed_trip_time`、`analyzer_reference_average_speed` の11項目である。
- Vehicle 別は `state`、`departure_time`、`arrival_time`、`travel_time`、`destination_name`、`traveled_route_link_names`、`log_t_link_history` の7項目である。
- 加えて Vehicle 名集合と completion order を比較する。completion order は、完走 Vehicle を arrival time と Vehicle 名で並べた順序である。
- 比較は Python の `!=` による厳密一致であり、tolerance と丸めを使わない。
- `assignment prefix violation: none observed (simulation completed)` と `visit_id / batch_assignment / service unit mismatch: none observed` は固定 print であり、実構造比較の結果として扱わない。
- BATCH assignment と service unit は FCFS に同じ構造がない。完全一致 field に加えない。

再確認の規模:

- まず小規模な専用 test。
- 次に200台。
- 必要な中間規模。
- 1,000台。
- 5,000台。現行基準の Level 2 call 46428、resolved 46390、unresolved 38、fallback 38 を参考にし、fallback 経路を含む完全一致を確認する。件数そのものが新基盤で同じになることは、一致性の定義ではない。一致性は上の field の exact match である。
- 10,000台は、必要性と計算時間を見て判断する。現時点で必須の再実行とは確定しない。過去の exact match 実績は **§4** に残っている。
- 計算時間は N=1 一致性の合否条件にしない。seed／RNG 実装自体の性能劣化が研究運用上重大でないかは、別に確認する。

### 14.19 未確定事項と実装時に決めてよい事項

未確定であり、最初の該当単位で専用 test と一緒に決めるもの:

- stable hash の algorithm。性能計測は未実施であり、毎 event の `SeedSequence` は未採用のままである。
- serialization の version 文字列、または domain の version。
- byte order。
- hash 結果から整数または float へ変換する具体式。
- 使用 bit 数。
- World 内部 entropy の属性名だけでなく、保存形式と正規化方法も、実装前の具体名と具体型は未決定である。有力候補は非負 Python 整数、または非負 Python 整数の明示的な列であり、必ず tuple とは確定しない。仮の実装単位「内部 entropy と pure keyed helper」で専用 test とともに確定する。
- Vehicle の3属性の正式名。
- 共通 Link 進入 helper の正式名。
- 通常 merge 用 RNG の属性名。
- Link 別進入回数 dict の key を正式 Link 名にする最終決定。有力案は正式 Link 名であり、原典にその key 方式の既存契約はない。
- 候補0件の具体的な例外型と例外文。
- カテゴリ選択の境界処理。`u=0`、累積境界、最後の候補への fallback。
- 軽量な性能確認の規模。実行しないと未確定である。
- 10,000台の N=1 再実行を行うか。現時点の必須事項ではない。

実装時に覆さない確定事項:

- Python 組込み `hash()` を使わない。object identity を使わない。
- domain separator で用途を分ける。mutable な共有 stream を keyed 値の生成で消費しない。
- 候補0件と1件では attempt を消費しない。候補2件以上の確率的選択だけ attempt を消費する。
- Link への物理進入が成功したときだけ進入回数を増やす。
- Node 訪問番号の合計が0のとき、1へ補正しない。
- Candidate binding の局所通過でも、局所 World の Link 進入状態を更新する。
- 現行 Level 2 mimic へ新状態を追加コピーせず、helper も接続しない。
- 通常 merge 用 RNG は `_transfer_normal_merge()` の非 hard deterministic 分岐だけに使う。
- seed／RNG 改修を、BATCH 大幅改修より先に行う。
- 新 BATCH は未実装、未採用である。現行 BATCH は保全する。
- 根幹実装は、短さより、初心者が追える明示的な Python を優先する。確定した研究契約を、コードを短くする目的で省略しない。公開 `W.random_seed` と正規化済み内部 entropy を二重の正本にしない。

将来の全 World 仮想計算型 BATCH は未実装である。本節の Level 2 判断を、その方式の状態コピー省略として使わない。既知の baseline collector test 契約不一致は、今回の実装単位の外にある別問題である。

### 14.20 次の直接作業

文書化の時点では、production の seed／RNG 実装は未着手である。production コード、test、診断 script は変更していない。simulation は実行していない。seed／RNG 改修用 branch は作成済みである。current branch は `feature/common-seed-rng-foundation` である。分岐元 commit は `fde6865` である。この branch の remote push は未実施である。作業ツリーには、本記録の対象外である既存変更と未追跡ファイルが残っている。それらには触れない。

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書を修正し、対象 Markdown だけを明示して stage し、commit し、commit 結果、最新 commit、残存する作業ツリー変更を確認することである。push はその確認後の別指示である。push 後に git status、最新 commit、local と remote の一致を確認する。その後に、内部 entropy と pure keyed helper の最小実装単位へ進む。

これは記録上の工程順である。利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。

### 14.21 検索語

seed RNG具体実装前調査、Cursor反証、Terminal独立確認、blockingなし、条件付き成立、random_seed None、内部entropy、単一entropy、stable hash、keyed randomization、pure function、domain separator、origin attempt、in-trip attempt、候補0件、候補1件、候補2件以上、Link別進入回数、Node訪問番号、合計0不整合、arrival tiebreaker、通常merge RNG、signalized専用ではない、_transfer_normal_merge、baseline全World、Candidate局所World、Candidate binding通過、outlink下流端、sink相当、下流Nodeへ通常進入しない、Candidate rollback、現行BATCH Level 2、mimic、追加コピー不要、N=1 BATCH、FCFS完全一致、fallback 38、旧seed結果非互換、production未実装、test未変更、次の作業、seed改修前に確認したこと、RNG実装前の問題、CandidateでLink回数を増やすか、BATCH Level 2に新状態をコピーするか、merge乱数をどこへ分けるか、random_seedがNoneのとき、route choice候補が0件のとき、arrival tiebreaker再訪、Node訪問番号が0、FCFSとN=1 BATCHが一致しなくなった、seed改修のテスト範囲、feature/common-seed-rng-foundation、fde6865
