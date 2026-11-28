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

## 15. 内部entropy保存とpure keyed helperの最小実装・反証・受入れ（2026-11-22）

### 15.1 記録の位置づけ

執筆日は2026-11-22である。本節は、**§14** で定めた最初の最小実装単位を、実際に実装し、読取り専用で反証し、限定修正し、Terminal で独立確認したあとの結果の詳細正本である。

既存節との関係は次のとおりである。

- **§14** は、実装前調査、反証、具体設計の正本である。本節は **§14** を削除も改変もしない。
- **§15** は、**§14** の最初の最小実装単位を実装・反証・検証した結果の正本である。
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** は研究契約の正本である。本節は研究契約を変更しない。
- 同 **§32.24** は実装前の具体設計確定である。同 **§32.25** は本節に対応する全体設計上の接続である。
- `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.25** は実装前調査完了の進捗である。同 **§21.9.26** は最初の実装単位の完了記録である。
- route choice、arrival tiebreaker、通常 merge、Vehicle counter への接続は未実装である。
- 現行 BATCH Level 2、Candidate、baseline の処理は変更していない。
- 新 BATCH は未実装・未採用である。現行 BATCH は保全する。

本節の受入れは、内部 entropy と pure keyed helper の最小単位だけである。4方式共通 seed／RNG 改修全体の完了ではない。

current branch は `feature/common-seed-rng-foundation` である。分岐元 commit は `fde6865` である。本節の文書化時点で、この branch の remote push は未実施である。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。Git 操作は利用者が Terminal で行う。Cursor は本節の文書化で Git 操作を行っていない。

### 15.2 今回の実装範囲

production:

- `uxsim/uxsim.py`
- `uxsim/common_seed_rng_keyed_uniform.py`

test:

- `tests_common_seed_rng_keyed_uniform.py`

変更内容:

- `World.__init__()` で内部 entropy を1回だけ確定し、保存する。
- 新しい内部 module で、正規化済み内部 entropy、domain、順序付き key parts から `[0, 1)` の一様値を返す。
- shared mutable RNG stream を消費しない。
- route choice 等へはまだ接続しない。
- 専用 test を新規作成する。

変更していない範囲:

- `Node.generate()`
- `Vehicle.route_next_link_choice()`
- Vehicle counter
- Link 進入 helper
- `Vehicle.record_order_control_node_arrival()`
- `_transfer_normal_merge()`
- 通常 merge 用 RNG
- baseline 処理
- Candidate 処理
- Level 2
- Candidate selection RNG
- `uxsim/__init__.py`
- research scripts
- diagnostics
- output

### 15.3 変更したproductionとtest

初回実装の時点で、新規 module は361行、新規専用 test は322行、専用 test は19件だった。この時点の成功だけで受入れ完了とはしなかった。読取り専用反証のあと、空 key の拒否、正規化入口、version と prefix の一本化、固定ベクトルを限定修正した。最終の専用 test は23件である。

production の接続先は増やしていない。`uxsim/__init__.py` から新しい module は公開していない。`uxsim.py` 側の import は、先頭が `_` の別名であり、`from uxsim import *` には出ない。

### 15.4 World内部entropyの実装

保存位置は `World.__init__()` である。次の既存初期化のあとで保存する。

- `W.rng = np.random.default_rng(seed=random_seed)`
- `order_control_seed_sequence = np.random.SeedSequence(random_seed)`
- `order_control_child_seed_sequence = order_control_seed_sequence.spawn(1)[0]`
- `W.order_control_rng = np.random.default_rng(order_control_child_seed_sequence)`
- `W.random_seed = random_seed`

属性名は `W._common_seed_rng_internal_entropy` である。保存元は、上で既に作った `order_control_seed_sequence.entropy` だけである。

行わないこと:

- 新しい `SeedSequence(None)` を作らない。
- 追加 spawn しない。
- Generator から draw しない。
- `W.rng` の state から導かない。
- 公開の `W.random_seed` を後から読み直さない。
- `W.random_seed` を書き換えても、保存済み内部 entropy は変えない。

内部表現は、非空 tuple of non-negative Python int である。現在の NumPy 2.3.5 では、明示整数 seed でも `None` でも `SeedSequence.entropy` は Python int である。Terminal 確認では、`SeedSequence(0).entropy` は `0`、`SeedSequence(7).entropy` は `7`、`SeedSequence(None).entropy` は複数 word の配列ではなく、OS 由来の大きな Python int 1個だった。

正規化 `normalize_seed_sequence_entropy()` の契約:

- Python int は1要素 tuple にする。`None` の大きな Python int は分割せず、1要素 tuple にする。
- NumPy 整数 scalar も Python int へ変換して1要素 tuple にする。反復処理へ送らない。
- 非空の整数 iterable は、順序を保った tuple へ正規化できる。1要素 iterable `[1]` と単一整数 `1` は、どちらも `(1,)` になる。
- この関数内で `SeedSequence` を作らない。OS entropy を再取得しない。spawn しない。Generator から draw しない。

受理:

- Python 非負 int
- NumPy 非負整数 scalar
- 非空の非負整数 iterable

拒否:

- bool
- 負整数
- float
- str
- bytes
- bytearray
- dict
- None
- 空 iterable
- 不正要素を含む iterable
- 非 iterable の不正型

入力境界の例外は、原因が分かる `ValueError` である。非 iterable の生の `TypeError` は外へ漏らさない。反復できない場合は `ValueError` へ変換する。bool は最初に拒否し、`True` や `False` を整数 entropy として受理しない。`bytes`、`bytearray`、整数 key の `dict`、`str` は、反復する前に拒否する。byte 列や dict key 列を entropy の整数列として受理しない。

### 15.5 pure keyed helperの実装

新規 module は `uxsim/common_seed_rng_keyed_uniform.py` である。最上位 helper は `keyed_uniform_value(...)` である。

入力:

- 正規化済み内部 entropy
- 非空 domain
- 非空 tuple の key parts

key parts として正式に受けるのは、非空 `str` と非負 Python `int` である。bool、負整数、空 `str`、未対応型、空 tuple は `ValueError` で拒否する。

空 key を拒否する理由は、origin、in-trip、arrival tiebreaker で、Vehicle、Node、Link、訪問、attempt 等の構築漏れを隠さないためである。domain だけの派生は、この helper へ空 tuple を渡す方式にしない。将来の通常 merge 用 seed 派生は、別 helper として設計する。空 key を許可する理由にしない。

pure function 契約:

- module global の mutable state はない。
- Generator はない。
- counter はない。
- cache はない。
- 呼出し順に依存しない。
- 呼出し回数に依存しない。
- attempt を変更しない。
- 同じ入力には同じ値を返す。
- `W.rng` を消費しない。
- `W.order_control_rng` を消費しない。

可読性は **§15.13** に記録する。seed 正規化、validation、serialization、hash、uniform 変換は別関数のままである。

### 15.6 serialization version 1

定数:

- `SERIALIZATION_VERSION = 1` が version の正本である。
- `_FORMAT_PREFIX_BASE = b"UXSIM_COMMON_SEED_RNG_V"`
- version を ASCII decimal へ変換し、base と連結して `FORMAT_PREFIX` を作る。
- version 1 の最終 prefix は、従来どおり `b"UXSIM_COMMON_SEED_RNG_V1"` である。
- prefix と version を別々に手入力しない。
- 新しい version field を bytes へ追加していない。prefix の位置も変えていない。

layout:

- fixed prefix
- entropy field
- domain field
- key-part count
- ordered key parts

field と type tag:

- entropy: `E`
- domain: `D`
- string key: `S`
- nonnegative integer key: `I`
- nonnegative sign marker: `0x00`

境界:

- entropy word count
- domain の UTF-8 byte 長
- key-part count
- string の UTF-8 byte 長
- integer magnitude の byte 長
- すべての複数 byte 整数は big-endian

保証:

- `("ab", "c")` と `("a", "bc")` を区別する。
- `(1, 23)` と `(12, 3)` を区別する。
- `"1"` と `1` を区別する。
- domain の違いを区別する。
- key 順序の違いを区別する。
- Python 組込み `hash()` を使わない。
- `id()` を使わない。
- `repr()` だけに依存しない。

### 15.7 SHA-256と53-bit一様値変換

hash:

- Python 標準ライブラリの `hashlib.sha256` を使う。
- digest は32 bytes である。
- process-wide の hash randomization に依存しない。
- 外部依存はない。

一様値変換:

- digest の先頭8 bytes を使う。
- big-endian の64-bit 整数として読む。
- 上位53 bits を使う。shift は11 bits である。
- 53-bit 整数を `2**53` で割る。
- 結果は `0.0 <= value < 1.0` である。
- `1.0` を返さない。53-bit 整数の最大値は `2**53 - 1` だからである。
- NumPy Generator を作らない。

53 bits の理由:

- Python float の有効整数精度に対応する。
- それ以上の bit をそのまま float へ変換すると、丸めにより `[0, 1)` の契約が不明確になる。
- digest の残り24 bytes は一様値へ使わない。
- SHA-256 出力の先頭53 bits を決定的に利用する。
- modulo による偏りはない。割る数は2の累乗である。

### 15.8 初回専用testと既存回帰

初回実装のあと、受入れ前に利用者が Terminal で確認した。

- 新規 module 361行。
- 新規専用 test 322行。
- 専用 test 19件。
- `py_compile` は成功した。
- 専用 test は成功した。
- `tests_order_control_rng.py` は成功した。
- `tests/test_other_functions.py::test_world_copy` は1 passed だった。
- 6 warnings は、既存の未登録 `pytest.mark.flaky` と NumPy の test collection warning であり、今回の実装失敗ではない。
- `git diff --check` の出力はなかった。

この時点では直ちに受入れ完了とはしない。読取り専用反証レビューへ進んだ。

### 15.9 読取り専用反証レビュー

Cursor Grok 4.7、effort high により、production と専用 test の読取り専用反証レビューを行った。Cursor は編集、test 実行、Git 操作を行っていない。Cursor の報告は、Terminal 確認の代わりにはしていない。

総合判定は「小修正後に受入れ可能」だった。blocking はなかった。現在の正しい入力で production 結果を誤らせる反例はなかった。

high 相当は2件だった。

1. 固定ベクトルがなく、serialization、digest、53-bit 変換の値契約が test で固定されていない。
2. 空の `key_parts=()` が一様値を返し、将来の key 構築漏れを隠す。

medium は3件だった。

1. entropy 正規化入口で、NumPy 整数 scalar、bytes、dict、非 iterable 等の扱いが不十分である。
2. `SERIALIZATION_VERSION` と `FORMAT_PREFIX` が別正本である。
3. seed 0 等の具体的な正規化値を固定していない。

low:

- AST 禁止 test は、別名や間接 call を検出できない。
- `open(...).read()` の file を明示的に閉じると読みやすい。
- 53-bit 変換で digest の残りを使わない理由を、説明に残す。

`_append_uint64()` へ追加の重複検証は不要と判断した。caller は `len(...)` と非負整数の magnitude 長だけを渡す。現実の入力では、`2**64` へ到達する前にメモリ上不可能である。過剰な実行時検証を追加しない方針と整合する。

### 15.10 反証後の限定修正

production module だけを次のとおり修正した。`uxsim.py` は、この限定修正では変更していない。

- 空 key parts を `ValueError` にする。
- NumPy 整数 scalar を1要素 tuple にする。
- `str`、`bytes`、`bytearray`、`dict` を反復前に拒否する。
- 非 iterable の `TypeError` を `ValueError` へ変換する。
- version 定数から prefix を構築する。
- docstring を受理範囲と拒否範囲へ同期する。

専用 test:

- seed 0 の内部 entropy は `(0,)` である。
- seed 1 の内部 entropy は `(1,)` である。
- seed 7 の内部 entropy は `(7,)` である。
- 正規化の正常入力を直接確認する。
- 正規化の異常入力を直接確認する。
- 空 key を拒否する。
- version と prefix の対応を確認する。
- serialization version 1 の固定ベクトルを追加する。
- AST test は `with open(...)` で file を閉じる。

最終の専用 test 数は23件である。SHA-256、53-bit の式、serialization の field 順、type tag、byte order は変えていない。

### 15.11 固定ベクトル転記失敗とTerminal独立修正

固定ベクトルの入力は次である。

- entropy: `(1,)`
- domain: `"d"`
- key parts: `("a", 1)`

production serializer の正しい出力は、162 hex characters、81 bytes である。この不一致は production serializer の欠陥ではない。修正したのは test の固定値だけである。

正しい serialization hex:

`555853494d5f434f4d4d4f4e5f534545445f524e475f5631450000000000000001000000000000000101440000000000000001640000000000000002530000000000000001614900000000000000000101`

正しい SHA-256 digest:

`02b81eccf53766e351c8bc3b042a94a09aa4fcb972b99fcb205ab2793870e199`

正しい53-bit integer:

`95674047571692`

正しい uniform value:

`0.0106219530473175`

失敗経緯:

- Cursor は最初、固定 serialization hex を79 bytes で記録した。
- Terminal の専用 test で `AssertionError` になった。
- Terminal 比較で、actual は81 bytes、fixed は79 bytes と判明した。entropy field の8-byte 長さ表現に zero が合計2 byte 不足していた。
- Cursor へ限定修正を依頼した。
- Cursor は81 bytes へ修正したと報告したが、実ファイルは80 bytes だった。
- Terminal 独立確認で再び `same = False` だった。
- Cursor の報告と実ファイルは、2回一致しなかった。
- 3回目は Cursor へ依頼せず、利用者が Terminal の Python スクリプトで production serializer の actual hex を直接読み、固定リテラルへ書き込んだ。
- 書込み後、actual 162 chars、fixed 162 chars、actual 81 bytes、fixed 81 bytes、`same = True` を確認した。

digest と53-bit 整数は、この81-byte の actual serialization から Terminal で独立算出し、test の固定値と一致していた。したがって digest と53-bit 整数は、hex 転記の修正では変更していない。

教訓:

- 長い zero 列を含む固定 hex を、人手または Cursor の転記だけで確定しない。
- production serializer の actual bytes を Terminal で直接取得する。
- 固定値の長さを、文字数と bytes 数で確認する。
- Cursor の完了報告だけで終了しない。
- test 実行前にも固定値を独立確認する。
- test 失敗時に production を直ちに疑わず、固定ベクトル自体を比較する。

### 15.12 最終検証結果

最終状態で、利用者が Terminal から次を実行し、成功した。Cursor はこの最終検証を実行していない。

構文:

- `python -m py_compile` の対象は `uxsim/uxsim.py`、`uxsim/common_seed_rng_keyed_uniform.py`、`tests_common_seed_rng_keyed_uniform.py` である。
- エラーはなかった。

専用 test:

- `python tests_common_seed_rng_keyed_uniform.py`
- 表示は `Common seed/RNG keyed uniform tests passed.` である。
- 23件成功した。

既存 RNG 回帰:

- `python tests_order_control_rng.py`
- 表示は `Order-control RNG tests passed.` である。

固定ベクトルの独立確認:

- actual chars 162
- fixed chars 162
- actual bytes 81
- fixed bytes 81
- same True

差分品質:

- `git diff --check`
- 出力はなかった。

過去に実行済みの World copy:

- `tests/test_other_functions.py::test_world_copy`
- 1 passed
- 6 warnings は既存 warning である。

### 15.13 受入れ判定

今回の最小実装単位は、次の理由で受入れ可能とする。test 成功だけを理由にはしない。

- blocking 反例はなかった。
- 反証で判明した high と medium を限定修正した。
- fixed serialization format を固定ベクトルで監査できるようにした。固定 hex の転記失敗は、Terminal で actual bytes を直接書いて解消した。
- 専用 test 23件が成功した。
- 既存 RNG 回帰が成功した。
- World copy の確認が成功した。
- shared RNG stream を消費しない。
- route choice 等の既存挙動へ未接続である。
- 対象外の production を変更していない。
- 可読性原則を維持した。

可読性として維持したこと:

- 正しさを最優先する。
- Python 初心者が処理順を追える。
- seed 正規化、validation、serialization、hash、uniform 変換を分割する。
- 複雑な内包表記を使わない。
- 過度な関数合成をしない。
- 中間変数へ意味のある名前を付ける。
- byte order と length を明示する。
- 例外条件を明示する。
- 高度な技巧で短縮しない。
- docstring に研究上の意味を書く。

今後の Cursor 実装指示にも、この原則を必ず含める。

この受入れは、内部 entropy と pure keyed helper の最小単位だけである。4方式共通 seed／RNG 改修全体の完了ではない。

### 15.14 今回未実装の範囲

次は未実装である。

- Vehicle の Link 別進入回数
- origin attempt
- in-trip attempt
- 共通 Link 進入 helper
- 通常 production の5進入経路への接続
- Candidate binding 通過への接続
- origin route choice の keyed 化
- in-trip route choice の keyed 化
- 候補0件、1件、2件以上の production 分岐
- arrival tiebreaker の keyed 化
- Node 訪問番号
- 通常 merge 用 sequential RNG
- `_transfer_normal_merge()` への接続
- baseline での実使用
- Candidate での実使用
- N=1 BATCH 対 FCFS の統合回帰
- 4方式統合回帰
- performance 確認

### 15.15 次の直接作業

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書を修正し、production 2ファイル、専用 test 1ファイル、対象 Markdown 3ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push はその確認後の別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、次の実装単位である Vehicle 状態と Link 進入 helper へ進む。

利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。

### 15.16 検索語

内部entropy実装、pure keyed helper、common seed RNG、最小実装単位、World内部entropy、_common_seed_rng_internal_entropy、normalize_seed_sequence_entropy、keyed_uniform_value、serialization version 1、FORMAT_PREFIX、SHA-256、53-bit、2の53乗、mutable RNG非消費、W.rng非消費、order_control_rng非消費、空key拒否、NumPy整数scalar、bytes拒否、dict拒否、固定ベクトル、fixed vector、81 bytes、162 hex characters、02b81ecc、95674047571692、0.0106219530473175、固定hex転記失敗、79 bytes、80 bytes、Cursor報告不一致、Terminal直接修正、専用test 23件、既存RNG回帰、World copy、blockingなし、小修正後受入れ、route choice未接続、arrival tiebreaker未接続、normal merge未接続、Vehicle counter未実装、次の作業、seed RNGの最初の実装、固定値testが失敗した、serialization hexが足りない、Cursorの修正報告と実ファイルが違う、entropyをどこへ保存したか、shared RNGを消費しない乱数、route choice接続前の基盤、次の実装単位、feature/common-seed-rng-foundation、fde6865

## 16. Vehicle状態とLink物理進入helperの実装・反証・受入れ（2026-11-23）

### 16.1 記録の位置づけ

執筆日は2026-11-23である。本節は、Vehicle 状態と Link 物理進入 helper の実装、test fixture 修正、読取り専用反証、反証後の test 修正、Terminal 独立確認、最終受入れ結果の詳細正本である。

既存節との関係は次のとおりである。

- **§14** は、4方式共通 seed／RNG 改修の具体実装前設計の正本である。本節は **§14** を削除も改変もしない。
- **§15** は、内部 entropy 保存と pure keyed helper の実装・反証・受入れ結果の正本である。本節は **§15** を削除も改変もしない。
- **§16** は、Vehicle 状態と Link 物理進入 helper の実装・反証・受入れ結果の正本である。
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** は研究契約の正本である。本節は研究契約を変更しない。
- 同 **§32.24** は実装前の具体設計確定である。同 **§32.25** は内部 entropy と pure keyed helper の実装結果である。同 **§32.26** は本節に対応する全体設計上の接続である。
- 進捗の対応節は `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.27** である。**§21.9.26** は前の実装単位の進捗として残す。

今回の実装は、4方式共通 seed／RNG 改修全体の完了ではない。route choice の keyed 化、attempt 増分、arrival tiebreaker の keyed 化、通常 merge 用 RNG は未実装である。新 BATCH は未実装・未採用である。

受入れは、Terminal の独立確認と読取り専用反証のあとに行った。test 成功だけを受入れ理由にはしない。Cursor の報告を無条件には採用していない。Cursor は Git 操作を行っていない。

### 16.2 今回の実装範囲

受入れ範囲は次だけである。

- Vehicle の 3 状態
- Link 物理進入 helper
- 通常 production の 5 進入経路への接続
- Candidate binding を含む Candidate 局所 transfer への接続
- Candidate 局所前進と Level 2 mimic への非接続

route choice の乱数、attempt の増分、arrival tiebreaker、通常 merge 用 RNG は、この単位では変えていない。

### 16.3 変更したproductionとtest

production は 2 ファイルである。

- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_candidate_binding_transfer.py`

test は新規の root-level ファイル1件である。

- `tests_vehicle_link_entry_state.py`

新規ファイルにした理由は、初期状態、helper 単体、origin、BATCH、両 FCFS、共通物理移動、loop 再進入、Candidate binding、Candidate 局所前進、Level 2、World copy、小規模行程を、一つの既存 test へ足すと、その既存 test の責務がぼやけるためである。

`uxsim/common_seed_rng_keyed_uniform.py` と `tests_common_seed_rng_keyed_uniform.py` は、この単位では変更していない。

### 16.4 Vehicleへ追加した3状態

`Vehicle.__init__()` で次の 3 属性を初期化する。mimic の `addVehicle` も同じ初期値を持つ。Level 2 はそれを参照しない。

#### 16.4.1 `link_entry_count_by_link_name`

- 初期値は空 dict である。Vehicle ごとに別 object である。
- key は正式 Link 名である。value は、その Vehicle がその Link へ物理進入した累積回数である。
- 初回進入後は 1 である。loop 等で同じ Link へ再進入すれば 2 以上である。
- 進入失敗では増えない。行程終了では消さない。
- 現在 Link だけの値を別属性へ重複保存しない。Node 別 counter は追加しない。
- `order_control_visit_id` を流用しない。`log_t_link` を正本にしない。
- Link object や object identity を dict key にしない。整数 Link ID を新設しない。

正式 Link 名を採用した理由は次である。

- World 内で一意である。
- auto rename 後の正式名を使う。
- real World と copy で同じ文字列になる。
- object identity に依存しない。
- 将来の key serializer へ非空 str として渡せる。
- 初心者が状態を確認しやすい。

これは **§14.19** が、最初の該当単位で専用 test とともに決めてよい事項である。有力案だった正式 Link 名を、この単位で採用した。

#### 16.4.2 `current_link_route_choice_attempt_count`

- 初期値は 0 である。
- 現在 Link 訪問中の確率的 in-trip route choice の試行回数である。
- 今回は増分しない。
- 新しい Link へ物理進入したとき 0 へ戻す。
- 同じ Link 上の待機では reset しない。
- Candidate 局所前進では reset しない。

#### 16.4.3 `origin_route_choice_attempt_count`

- 初期値は 0 である。
- 最初の Link へ入る前の確率的 origin route choice の試行回数である。
- 今回は増分しない。
- Link 進入 helper は変更しない。
- 最初の Link へ進入しても reset しない。
- 今回は初期値と不変性だけを検証した。

### 16.5 共通Link物理進入helper

method は `Vehicle.record_successful_physical_link_entry()` である。

責務は次の2点だけである。

1. 現在の `vehicle.link.name` に対応する回数を 1 増やす。
2. `current_link_route_choice_attempt_count` を 0 へ戻す。

呼出し前提は次である。

- 物理的 Link 進入が成功したあとである。
- `vehicle.link` は進入後の Link を指している。
- 同じ進入につき 1 回だけ呼ぶ。
- 既存の Visit 開始の前である。

`vehicle.link is None` の場合は、原因の分かる `ValueError` とする。

helper が変更しないものは次である。

- `vehicle.link`
- origin attempt
- order-control Visit
- `order_control_visit_id`
- arrival tiebreaker
- route choice
- append
- pop
- capacity
- Node 訪問番号
- output
- audit

同じ進入で 2 回呼ぶと、2 回分として数える。二重呼出し検出用の新しい状態は追加しない。1 回だけ呼ぶ責務は caller にある。

helper は `begin_order_control_visit_on_link_entry()` の内部へ入れていない。理由は次である。

- Level 2 mimic も Visit 開始を呼ぶ。
- Level 2 へ正式 Link 進入状態の更新を自動接続しない。
- Link 進入状態と order-control Visit は別責務である。
- Candidate binding には接続するが、Level 2 には接続しない。

Link 名の型や、既存 counter の負値・非整数を helper 内で重ねて検査することはしない。登録時の保証を、helper で繰り返さない。前単位の `_append_uint64()` の議論とは混同しない。

### 16.6 通常productionの5接続経路

最終確認では、`uxsim.py` の helper 呼出しは 5 箇所である。いずれも Link 代入のあと、Visit 開始の前である。caller 側と内部 helper の双方では呼んでいない。

#### 16.6.1 origin `Node.generate()`

接続位置は次の順である。

- 進入条件が成立したあと
- `veh.link = outlink`
- lane／leader 処理
- `outlink.vehicles.append(veh)`
- arrival log
- `cum_arrival`
- `link_arrival_time`
- helper
- Visit 開始
- capacity 減算

入口空間や流入容量不足による `break` では helper を呼ばない。origin attempt は今回変更しない。

atomicity は次のとおりである。

- helper と Visit 開始は capacity 減算より前である。
- Visit 開始で例外が起きる場合、counter は更新済みで、capacity は未減算になり得る。
- この経路は、helper 追加前から、append、arrival log、`cum_arrival`、link 変更等を先に行う非 atomic な順序だった。
- helper は、既に成立した物理進入状態へ追随する。
- 今回、経路全体を atomic 化していない。

#### 16.6.2 BATCH実通過 `_transfer_vehicle`

- 物理条件を満たしたあとである。
- 容量減算と inlink からの pop のあとである。
- `veh.link = outlink` の直後、Visit 開始の直前に 1 回だけ呼ぶ。
- `_can_transfer` が不成立のときは呼ばない。
- Level 2 の `_transfer_vehicle_reference` とは別関数である。

#### 16.6.3 `transfer_fcfs_no_clearance()`

- 正式通過のときだけ呼ぶ。
- `veh.link = outlink` の直後、Visit 開始の直前である。
- 容量、入口空間、物理先頭等を満たさない場合は呼ばない。

#### 16.6.4 `transfer_fcfs_clearance()`

- judgment が `pass` の正式通過のときだけ呼ぶ。
- `veh.link = outlink` の直後、Visit 開始の直前である。
- clearance 未充足と容量不足では呼ばない。
- baseline collector の既存順序は変更していない。

#### 16.6.5 `_transfer_one_vehicle_between_links()`

- `vehicle.link = outlink` の直後、Visit 開始の直前である。
- 通常 merge と TVT-MP 確定順位の正式実移動は、この共通関数を 1 回呼ぶ。
- caller 側には helper を追加していない。
- 二重計上しない。

### 16.7 Candidate binding局所通過

対象は `uxsim/order_control_tvt_mp_candidate_binding_transfer.py` の `_transfer_one_vehicle_like_uxsim()` である。最終確認では、このファイルの helper 呼出しは 1 箇所である。

接続位置は次である。

- `local_vehicle.link = outlink`
- helper
- Visit 開始

契約は次である。

- Candidate local World は real World の copy である。
- local Vehicle の dict は real Vehicle と別 object である。
- 局所 World で outlink へ物理進入した事実を記録する。
- local Vehicle の outlink 回数を増やす。
- current Link attempt を 0 へ戻す。
- origin attempt は変えない。
- real Vehicle へ戻さない。
- Candidate の通常 route choice は発生しない。
- outlink 上を下流端まで処理する。
- 下流端では退出、sink 相当として扱う。
- 下流 Node へ通常進入させない。
- 新しい Node Visit や通常 route choice を発生させない。

この関数は binding と unbound 局所 FCFS で共有している。そのため、Candidate unbound 局所 FCFS も、同じ正式な局所進入として更新される。これは契約違反ではない。上位 caller と関数内部の双方で helper を呼んではいない。

### 16.8 非接続経路

#### 16.8.1 Candidate局所前進

正式関数は `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` である。

同一 inlink 上の位置前進と到着登録であり、新しい Link への物理進入ではない。次を変更しない。

- Link 別進入回数
- current Link attempt
- origin attempt

最終確認では、Candidate 局所前進ファイルの helper 呼出しは 0 箇所である。

#### 16.8.2 Level 2 mimic

次へは接続していない。

- `_transfer_vehicle_reference`
- mimic Vehicle への新状態の追加コピー
- `begin_order_control_visit_on_link_entry()` の内部

維持する意味は次である。

- mimic Vehicle は `Vehicle.__init__()` により 3 属性を初期値で持つ。
- Link 別進入回数は空 dict である。attempts は 0 である。
- real Vehicle の値を追加コピーしない。
- mimic 内物理通過後も Link 別進入回数は空である。
- 正式な将来交通 World 状態を構築する World ではない。
- 局所通過時刻推定の限定例外である。
- この例外を Candidate や、将来の全 World 型 BATCH へ一般化しない。

最終確認では、Level 2 production の helper 呼出しは 0 箇所である。

#### 16.8.3 その他

次も helper を呼ばない。

- `Vehicle.end_trip()`
- `vehicle.link = None`
- 進入失敗
- 同一 Link 上の位置更新
- 到着登録だけ
- route choice だけ
- baseline snapshot
- World copy
- log 記録
- rollback と snapshot 復元

snapshot 復元は新しい Link 進入ではなく、保存済み状態の復元なので、helper を呼ばない。World copy は属性を写す。copy 後の正式進入は、通常 production の 5 経路で更新する。baseline snapshot の作成だけでは回数を増やさない。

### 16.9 専用test 17件

新規 test は `tests_vehicle_link_entry_state.py` である。最終 test 数は 17 件である。

1. `test_new_vehicle_link_entry_state_starts_empty_and_is_not_shared`。新規 Vehicle の dict は空、attempt は 0、Vehicle 間で dict を共有しない。
2. `test_helper_records_link_name_and_resets_only_in_trip_attempt`。helper 直接呼出しで Link 名の回数を増やし、in-trip attempt だけを 0 に戻し、origin attempt と visit id は変えない。正式経路の証明には使わない。
3. `test_helper_rejects_missing_link`。`link is None` で `ValueError` とし、dict は空のままである。
4. `test_origin_entry_success_records_the_entered_link_once`。`Node.generate()` の成功で `link1` が 1 回、in-trip attempt は 0、origin attempt は維持する。
5. `test_origin_entry_failure_does_not_record_a_link`。流入容量不足の `break` では回数も attempt も変えない。
6. `test_batch_real_transfer_records_outlink_once`。BATCH 実通過の成功で outlink が 1 回である。
7. `test_batch_real_transfer_failure_does_not_record_outlink`。`_can_transfer` 不成立では記録しない。
8. `test_fcfs_without_clearance_records_only_a_successful_pass`。clearance なし FCFS は成功時だけ 1 回である。
9. `test_fcfs_with_clearance_records_only_a_successful_pass`。clearance あり FCFS は `pass` のときだけ 1 回である。
10. `test_common_physical_transfer_and_normal_merge_record_once`。共通物理移動と通常 merge は各 1 回である。二重なら 2 になる。
11. `test_formal_reentry_keeps_cumulative_link_counts`。共通物理移動の loop 再進入で、同じ Link 名が 2 になる。行程開始前の origin attempt は 0 のままである。
12. `test_candidate_binding_updates_only_the_copied_vehicle`。copy 側の outlink 回数だけが増え、dict は別 object であり、real Vehicle は不変である。
13. `test_candidate_local_advance_does_not_record_a_new_link`。Candidate 局所前進の正式関数のあと、同じ inlink のままで 3 状態は不変である。修正経緯は **§16.13** である。
14. `test_level2_reference_transfer_does_not_record_link_entry`。mimic は初期値のままで、reference 通過後も空 dict であり、real の回数は不変である。
15. `test_begin_visit_and_level2_do_not_call_the_link_entry_helper`。Visit 開始、Level 2、Candidate 局所前進の source に helper 名がない。source 検査だけを受入れ根拠にしない。
16. `test_world_copy_keeps_link_entry_state_on_a_distinct_dict`。copy は値を引き継ぎ、dict object は別である。
17. `test_single_path_trip_still_uses_the_only_route`。hard deterministic の単一路で完走し、2 Link が各 1 回残る。RNG state や旅行時間は固定していない。小規模な既存交通結果の非変更確認である。

test 群の読み方は次である。

- helper 直接 test だけで正式経路を証明していない。
- origin、BATCH、両 FCFS、共通移動、通常 merge、loop は正式経路を実行する。
- Candidate binding は copy 側だけの更新を確認する。
- Candidate 局所前進は正式関数を呼ぶ。
- Level 2 は実動作 test と source-level test の両方がある。
- World copy は値の継承と dict 非共有である。
- 単一路行程は小規模な既存交通結果の非変更を確認する。
- source-level test だけを受入れ根拠にしない。

### 16.10 初回Level 2 fixture失敗と修正

初回の専用 test では、`py_compile` は成功した。専用 test は Level 2 の 1 件で失敗した。

失敗 test は `test_level2_reference_transfer_does_not_record_link_entry` である。

例外は `'_mimic_up_link1' is not Node in this World` である。

原因は test fixture の不整合である。production 欠陥ではない。

- `_create_mimic_vehicle()` は、real inlink `link1` 上の Vehicle について、mimic origin を `_mimic_up_link1`、destination を `merge` とする。
- test は通常の merge network を mimic World として流用していた。
- 通常 network には `orig1` 等はあるが、`_mimic_up_link1` がない。

修正は test 側だけである。production は変更していない。

- `_build_level2_mimic_world_for_real_merge(real_W, name)` を追加した。
- real target Node は `merge` である。
- 各 inlink 用に `_mimic_up_{link_name}` を置く。
- 各 outlink 用に `_mimic_sink_{link_name}` を置く。
- mapping は real Link から mimic Link である。
- mimic `link1` は `_mimic_up_link1` から `merge` である。
- mimic `out` は `merge` から `_mimic_sink_out` である。

修正後、`py_compile` は成功した。専用 17 件は成功した。表示は `Vehicle link-entry state tests passed.` である。

Level 2 fixture は production の `_build_mimic_world()` そのものではなく、この test に必要な Node 名、Link 名、向きを再実装したものである。反証では low とした。今回の 1 台の reference 通過には足りる。production builder の全属性へは追従しない。

### 16.11 既存回帰

利用者の Terminal で、次を確認した。

Candidate binding:

- `python tests_order_control_tvt_mp_candidate_binding_transfer.py`
- `binding transfer scan tests passed (21 tests).`

BATCH transfer:

- `python tests_order_control_batch_transfer.py`
- `Order-control batch transfer tests passed.`

FCFS transfer:

- `python tests_fcfs_order_control_transfer.py`
- `FCFS order control transfer test passed.`

Level 2 reference:

- `python tests_order_control_batch_t_trigger_level_2_reference.py`
- `All 20 Level 2 reference tests passed.`
- 表示された単一 call 0.20 ms は参考値である。今回の性能合否条件には使わない。

ファイル名の誤りがある。当初、存在しない `tests_order_control_batch.py` と、存在しない `tests_order_control_fcfs.py` を実行し、`No such file or directory` となった。これは test failure ではなく、案内したファイル名の誤りである。`find` で実在する test 名を確認し、対象が明確な test だけを実行した。実行失敗と実装失敗を混同しない。

この単位の受入れ前に、追加必須の既存回帰はない。N=1 BATCH 対 FCFS は統合回帰で実行する。baseline route choice は、将来の接続時に確認する。

### 16.12 読取り専用反証レビュー

Cursor Grok 4.7、effort high で、読取り専用の反証レビューを行った。Cursor は編集、test、`py_compile`、simulation、Git を行っていない。

総合判定は、このまま受入れ可能である。blocking はない。high はない。

成立した主要事項は次である。

- 正式接続経路は、通常 production の 5 経路と、Candidate 局所 transfer の 1 経路である。
- 通常 merge と TVT-MP 確定順位は、共通物理移動を 1 回だけ呼ぶ。
- Candidate binding と unbound 局所 FCFS は、共通局所 transfer を 1 回だけ呼ぶ。
- 二重計上はない。
- 進入失敗では非接続である。
- Candidate 局所前進は非接続である。
- Level 2 は非接続である。
- baseline fork 後の正式進入も、通常の 5 経路を使う。
- helper 境界は `link is None` の最小検査で十分である。
- Link 名や既存 counter の過剰な重複検証は追加しない。
- 二重呼出し検出用の追加状態は持たない。
- `_append_uint64()` 等の前単位の議論とは混同しない。

medium は次の2件である。

1. Candidate 局所前進 test の名前と、実際の検証対象が不一致だった。これは **§16.13** で修正した。
2. source-level の AST 検査には、間接呼出しを見逃す限界がある。Level 2 の非接続は、実動作 test と合わせて読む。

low は次である。

- Level 2 mimic fixture は production builder の再実装である。
- Candidate unbound 局所 FCFS の専用 test はない。共有関数のため、binding と同じ更新になる。
- 単一路行程 test は、RNG state や旅行時間を固定しない。
- Level 2 call 時間は参考値である。

反証の「このまま受入れ可能」は、production 契約の判定である。test 対象の不一致は残さず、その後に修正した。test 成功だけを理由にしていない。

### 16.13 Candidate局所前進testの対象誤りと修正

反証で判明した問題は次である。

- test 名は `test_candidate_local_advance_does_not_record_a_new_link` である。
- 実際に呼んでいたのは、Level 2 の `_advance_inlink_vehicles` である。
- Candidate 局所前進の正式関数を、実動作では検証していなかった。
- production の読取りでは、Candidate 局所前進に helper 呼出しも、新しい Link 代入もなかった。
- production 契約自体は成立している。
- test 名と検証対象の不一致は残さなかった。

修正は test だけである。production は変更していない。

- Level 2 の `_advance_inlink_vehicles` の import と呼出しを削除した。
- Candidate 局所前進の正式関数を import した。
- 呼ぶ関数は `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` である。
- Candidate local state を、正式な既存の初期化順で作成した。
- binding transfer が起きない条件を設定した。
- Candidate 局所前進だけを実行した。
- local Vehicle は同じ `link1` である。
- Link 進入回数は `{"link1": 1}` のままである。
- current Link attempt は 4 のままである。
- origin attempt は 2 のままである。
- real Vehicle の状態も不変である。
- test 総数は 17 件のままである。

修正後、利用者の Terminal で、import と正式関数の呼出しを独立確認した。Level 2 関数の参照は説明 comment だけである。`git diff --check` の出力はなかった。専用 17 件の再実行は成功した。表示は `Vehicle link-entry state tests passed.` である。

### 16.14 最終検証結果

最終状態で、次を確認済みである。

- production の call site は、`uxsim.py` が 5 箇所、Candidate binding transfer が 1 箇所、Level 2 が 0 箇所、Candidate 局所前進が 0 箇所である。
- 6 接続はすべて、Link 代入のあと、Visit 開始の前である。
- Vehicle の 3 属性を初期化している。
- `py_compile` は成功した。
- 専用 test 17 件は成功した。
- Candidate binding 21 件は成功した。
- BATCH transfer は成功した。
- FCFS transfer は成功した。
- Level 2 reference 20 件は成功した。
- 読取り専用反証で blocking と high はない。
- Candidate 局所前進 test の修正後も、専用 17 件は成功した。
- `git diff --check` の出力はなかった。

今回、広範な simulation、benchmark、N=1 回帰は実行していない。

### 16.15 受入れ判定

今回の実装単位を受入れ可能とする。理由は次である。

- 正式進入経路の網羅性を原典で確認した。
- 通常の 5 経路と Candidate 局所 transfer へ接続した。
- 二重計上はない。
- 失敗経路では非接続である。
- helper の責務は 2 点に狭い。
- Level 2 は非接続である。
- Candidate 局所前進は非接続である。
- copy は値を引き継ぎ、dict は共有しない。
- 専用 17 件は成功した。
- 直接関係する既存回帰は成功した。
- 反証で blocking と high はない。
- test 対象の誤りを修正し、正式関数で再検証した。
- route choice 等へは未接続である。
- 可読性原則を維持した。

維持した可読性は次である。

- 正しさを最優先する。
- Python 初心者が処理順を追える。
- 3 属性の意味を comment で明示する。
- helper の責務を 2 点へ限定する。
- 6 接続位置を、Link 代入のあと、Visit 開始の前へ統一する。
- 中間変数へ意味のある名前を付ける。
- 複雑な内包表記を使わない。
- 過度な関数合成をしない。
- 例外条件を明示する。
- test の準備、実行、期待値を分ける。
- 実 World、Candidate、Level 2 を区別する。
- Cursor 報告を Terminal で独立確認する。
- test 成功だけで受入れない。

今後の Cursor 実装指示にも、この原則を含める。

受入れ範囲は、Vehicle の 3 状態、Link 物理進入 helper、正式進入経路への接続、Candidate と Level 2 の接続区別だけである。4方式共通 seed／RNG 改修全体の完了ではない。

### 16.16 今回未実装の範囲

次は未実装である。

- origin route choice の keyed 化
- in-trip route choice の keyed 化
- origin attempt の増分
- in-trip attempt の増分
- 候補 0 件、1 件、2 件以上の production 分岐変更
- arrival tiebreaker の keyed 化
- Node 訪問番号の実利用
- 通常 merge 用 sequential RNG
- `_transfer_normal_merge()` の乱数変更
- baseline route choice での実使用
- Candidate route choice での実使用
- N=1 BATCH 対 FCFS の完全一致
- 4方式統合回帰
- performance 確認

### 16.17 次の直接作業

**§14.17** の単位順を再確認した。Vehicle 状態と Link 進入 helper の次は、origin と in-trip の keyed 化である。arrival tiebreaker、通常 merge 用 RNG、統合回帰はその後である。この順序を飛ばさない。

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書を修正し、production 2 ファイル、専用 test 1 ファイル、対象 Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push はその確認後の別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、次の実装単位である origin と in-trip route choice の keyed 化へ進む。

利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。

### 16.18 検索語

Vehicle状態、Link進入回数、link_entry_count_by_link_name、current_link_route_choice_attempt_count、origin_route_choice_attempt_count、record_successful_physical_link_entry、物理進入成功、Link名key、正式Link名、origin進入、BATCH実通過、FCFS clearanceなし、FCFS clearanceあり、_transfer_one_vehicle_between_links、Candidate binding、Candidate unbound FCFS、Candidate局所前進非接続、Level 2非接続、_transfer_vehicle_reference、begin_order_control_visit_on_link_entry、helperをVisit内部へ入れない、二重計上なし、進入失敗非接続、loop再進入、World copy、dict非共有、Level 2 fixture、_mimic_up_link1、_mimic_sink_out、Candidate局所前進test対象誤り、advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals、専用test 17件、Candidate binding 21件、BATCH transfer、FCFS transfer、Level 2 reference 20件、blockingなし、highなし、route choice未接続、attempt増分未実装、arrival tiebreaker未実装、normal merge RNG未実装、次の作業、feature/common-seed-rng-foundation、ef008ce、VehicleがLinkへ何回入ったか、同じLinkへ再進入した回数、新しいLinkへ入るとattemptが0になる、origin attemptをresetしない、CandidateでLink回数を増やすか、Level 2でLink回数を増やすか、Link進入helperの接続漏れ、Link進入回数が二重になった、Candidate局所前進でcounterが変わった、Level 2 mimicへcounterをコピーするか、test名と実際の関数が違った、_mimic_up_link1がない、Vehicle状態実装後の次作業

## 17. origin・in-trip route choice keyed化の実装・反証・受入れ（2026-11-23）

### 17.1 記録の位置づけ

執筆日は2026-11-23である。本節は、origin route choice と in-trip route choice の keyed 化、専用 test、初回 fixture 失敗、既存回帰、読取り専用反証、反証後の test 補強、Terminal 独立確認、最終受入れ結果の詳細正本である。

既存節との関係は次のとおりである。

- **§14** は、4方式共通 seed／RNG 改修の具体実装前設計の正本である。本節は **§14** から **§16** の本文を削除も置換もしない。
- **§15** は、内部 entropy 保存と pure keyed helper の実装・反証・受入れ結果の正本である。
- **§16** は、Vehicle 状態と Link 物理進入 helper の実装・反証・受入れ結果の正本である。
- **§17** は、origin・in-trip route choice keyed 化の実装・反証・受入れ結果の正本である。
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** は研究契約の正本である。本節は研究契約を変更しない。
- 同 **§32.24** は実装前の具体設計確定である。同 **§32.25** は内部 entropy と pure keyed helper の実装結果である。同 **§32.26** は Vehicle 状態と Link 進入 helper の実装結果である。同 **§32.27** は本節に対応する全体設計上の接続である。**§32.21** と **§32.24** から **§32.26** の本文は削除も置換もしない。
- 進捗の対応節は `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.28** である。**§21.9.27** は前の実装単位の進捗として残す。

今回の実装は、4方式共通 seed／RNG 改修全体の完了ではない。arrival tiebreaker の keyed 化、Node 訪問番号の production 利用、通常 merge 用 RNG は未実装である。N=1 BATCH 対 FCFS 回帰と 4方式統合回帰は未実行である。新 BATCH は未実装・未採用である。

受入れは、Terminal の独立確認と読取り専用反証のあと、反証で判明した test 不足を補強し、補強後の専用 test を Terminal で再確認してから行った。test 成功だけを受入れ理由にはしない。Cursor の報告を無条件には採用していない。Cursor は Git 操作を行っていない。

### 17.2 今回の実装範囲

受入れ範囲は次だけである。

- origin route choice の keyed 化。対象は `Node.generate()` である。
- in-trip route choice の keyed 化。対象は `Vehicle.route_next_link_choice()` である。
- route choice の category selection helper。
- origin attempt と in-trip attempt の増分。
- 候補 0 件、1 件、2 件以上の明示分岐。
- route choice からの mutable RNG 非消費。

arrival tiebreaker、Node 訪問番号の production 利用、通常 merge 用 RNG、Candidate selection RNG、N=1 完全一致、4方式統合回帰は、この単位の範囲外である。

### 17.3 変更したproductionとtest

production は 2 ファイルである。

- `uxsim/uxsim.py`
- 新規 `uxsim/common_seed_rng_route_choice.py`

test は新規の root-level ファイル 1 件である。

- `tests_common_seed_rng_route_choice.py`

新規 module にした理由は次である。

- generic な serialization と hash は、受入れ済みの `uxsim/common_seed_rng_keyed_uniform.py` に残す。UXsim 固有の route choice category selection 契約は別 module に置く。
- origin と in-trip で、候補選択の処理を共有する。
- `uxsim.py` へ確率境界の検査を詰め込まない。
- `uxsim/__init__.py` から公開しない。public API へ露出しない。
- World も Vehicle も変更しない pure helper にする。attempt の増分は caller が行う。

専用 test を新規ファイルにした理由は、origin、in-trip、候補 0 件・1 件・2 件以上、hard deterministic、specified route、World copy、process 順序独立、helper 境界、候補順序、loop 再進入を、既存の keyed uniform test や Vehicle Link 進入 test の責務へ混在させないためである。

反証後に変えた production は、`Vehicle.__init__()` の 3 属性付近の説明 comment だけである。route choice の処理、key、domain、attempt 更新位置、候補形成、helper 本体は反証後に変えていない。

### 17.4 既存route choice制御フロー

#### origin

対象は `Node.generate()` である。

- generation queue の先頭 Vehicle について、呼出しごとに候補を構築する。
- 選択した Link を専用属性へ保存しない。進入成功時に `veh.link` へ設定する。
- 入口空間または流入容量が足りないときは `break` する。同じ `generate()` 呼出しの中では再抽選しない。
- 次 timestep に、再び候補形成と選択を行う。候補が 2 件以上なら、次の origin attempt を使う。

origin Node 自体に outlink がない場合は、`Node.generate()` の処理に入らない。queue に残る既存挙動である。候補 0 件の成功としては扱わない。

#### in-trip

対象は `Vehicle.route_next_link_choice()` である。正式な caller は `Vehicle.update()` である。

- Vehicle が Link 終端にいるあいだ、timestep ごとに呼ばれる。終端到達前には呼ばれない。
- 結果は既存の `route_next_link` へ保存する。
- 通過できず同じ Link 終端に残れば、次 timestep に再選択する。同一 Link 訪問中の再選択は次の attempt を使う。
- 新しい Link へ物理進入すると、**§16** の Link 進入 helper が in-trip attempt を 0 に戻す。Link 進入回数は累積し、route choice では変更しない。origin attempt は Link 進入では戻さない。

`single_trip` で目的地に着いているときは、この関数を呼ばず行程終了の準備へ進む。`trip_abort` が有効な dead-end も、update 側で `route_next_link = None` とし、この関数を呼ばない。関数自体も、Node に outlink がないときは `route_next_link = None` とし、attempt は増やさない。

#### 候補順序

- prefer も avoid もないときは、outlink の登録順である。
- prefer を適用したあとは、Link 名の昇順である。
- avoid を適用したあとも、Link 名の昇順である。
- origin と in-trip で同じ規則である。
- key には候補集合も候補順序も入れない。同じ uniform を、その event 時点の候補分布へ適用する。候補集合または順序が違えば、同じ uniform でも選ばれる Link は異なり得る。その差は抑制しない。

### 17.5 route choice用domain

固定 domain は次である。

- origin は `origin_route_choice` である。定数名は `ORIGIN_ROUTE_CHOICE_DOMAIN` である。
- in-trip は `in_trip_route_choice` である。定数名は `IN_TRIP_ROUTE_CHOICE_DOMAIN` である。

origin と in-trip は domain を共有しない。arrival tiebreaker とも、通常 merge とも共有しない。caller が自由文字列で domain を渡す一般 API にはしない。定数は内部 module に置く。domain が違うと、同じ key parts でも uniform が違うことを、専用 test が確認する。

### 17.6 共通category selection helper

module は `uxsim/common_seed_rng_route_choice.py` である。関数は `select_route_choice_candidate(candidate_links, preference_weights, uniform_value)` である。

責務は次である。

- caller が渡した候補順を維持する。関数内では sort しない。
- candidate Link object を copy しない。
- World を読まない。Vehicle を読まない。
- attempt を変更しない。
- mutable RNG を使わない。新しい Generator も作らない。

候補数ごとの契約は次である。

- 候補 0 件は `ValueError` である。空 list を成功にしない。
- 候補 1 件は、その唯一候補を直接返す。weight も uniform も読まない。draw なし契約である。
- 候補 2 件以上では、preference を float へ変換する。候補数と weight 数が違うときは `ValueError` である。負値、NaN、正の無限大、負の無限大、bool は拒否する。uniform は exact な Python `float` で、範囲は `[0, 1)` である。範囲外、NaN、bool、整数は `ValueError` である。
- preference の合計が正のときは、`weight / total` の累積確率を候補順に作る。最初に `u < cumulative_probability` となる候補を選ぶ。通常の浮動小数点丸めで最後まで閾値を超えない場合だけ、最後の候補を明示的な remainder とする。この remainder は空 list を成功にしない。
- 合計が 0 のときは、`int(u * candidate_count)` の等確率 slot である。`u * n` が `n` に丸まる場合の上限補正はある。state は変えない。

有限 weight の合計自体が overflow して `inf` になる極端値は、通常の route preference の範囲外である。今回の受入れを妨げる反例にはしない。

正の合計で最後の候補へ落ちる remainder 分岐は、helper の source 上の契約として残す。安全に到達させる直接 test は追加していない。helper 本体は、この分岐を test しやすくするために変更していない。

### 17.7 origin route choice keyed化

key は、Vehicle 正式名、origin Node 正式名、その時点の `origin_route_choice_attempt_count` である。

具体形は `(veh.name, origin_node.name, origin_attempt)` である。domain は `origin_route_choice` である。保存済み内部 entropy と domain は、keyed uniform の引数として key parts の外に渡す。

契約は次である。

- Vehicle 名は auto rename 後の正式名である。Node 名は正式名である。
- object identity を使わない。Vehicle ID も Node の整数 ID も使わない。
- 現在の attempt を、uniform を得る前に key へ使う。
- 確率選択が正常に返ったあと、入口判定より前に attempt を 1 増やす。
- 入口空間または流入容量が足りず進入できなくても、attempt は戻さない。
- 同じ `generate()` 呼出しの中では、容量不足の `break` のあと再抽選しない。
- 次 timestep の再抽選は次の attempt である。
- 候補 0 件、候補 1 件、hard deterministic、specified route では attempt を増やさない。
- preference、key、category 選択の途中で例外が出た場合、attempt は進めない。

選択 Link は、成功して進入するまで Vehicle の専用属性へ保存しない。失敗した選択は捨て、attempt だけが残る。これは **§14.8** の契約である。

### 17.8 in-trip route choice keyed化

key は、Vehicle 正式名、current Link 正式名、その Link への累積進入回数、その時点の `current_link_route_choice_attempt_count` である。

具体形は `(vehicle.name, current_link.name, link_entry_count, in_trip_attempt)` である。domain は `in_trip_route_choice` である。

契約は次である。

- Link 名は正式名である。Link object identity も Link の整数 ID も使わない。
- `order_control_visit_id` は key に使わない。
- 進入回数が dict に無いとき、または値が int でないとき、または 1 未満のときは `ValueError` である。missing も 0 も 1 へ補正しない。
- この検査は、確率的な候補 2 件以上の分岐だけで行う。候補 1 件、hard deterministic、specified route は key を作らないので、この検査をしない。
- `route_next_link` へ選択結果を保存したあとで、attempt を 1 増やす。
- 同じ Link 終端に残れば、次 timestep は次の attempt である。`route_next_link` は再選択で上書きされる。
- 新しい Link へ正式進入すると、in-trip attempt だけが 0 に戻る。Link 進入回数は route choice では変更しない。
- 候補 0 件、候補 1 件、hard deterministic、specified route では attempt を増やさない。

方式間で、同じ Link 終端に留まる timestep 数が違うと、通過時点で使われる attempt 番号は異なり得る。契約が揃えるのは、同じ attempt 番号の uniform である。待ち時間そのものや、通過に使った attempt 番号を方式間で強制一致させる契約ではない。**§14.9** は、終端に留まる各 timestep の再選択を別 attempt とする。N=1 の完全一致は、後続の統合回帰で確認する。

### 17.9 候補0件・1件・2件以上の契約

#### 候補0件

origin または in-trip で、Node に outlink はあるが、prefer または avoid のあとで 0 件になる場合は次である。

- `ValueError` である。
- keyed draw はない。
- attempt は増えない。
- mutable RNG は消費しない。
- 空 list を成功にする fallback はない。
- 既存の `route_next_link` は消さない。`Vehicle.__init__()` はこの属性を常設しない。例外経路でも新しく代入しない。

正当な in-trip dead-end は別である。Node 自体に outlink がないとき、`route_next_link = None` とし、attempt は増やさない。prefer／avoid 後の 0 件と、Node に outlink がない dead-end を、同じ成功経路にはしない。

#### 候補1件

- 唯一の候補を直接選ぶ。
- keyed uniform はない。SHA-256 もない。
- mutable RNG は消費しない。
- attempt は増えない。
- preference の正規化はない。

#### 候補2件以上

- 現在の attempt を含む explicit key を使う。
- pure keyed uniform を 1 つ使う。
- 既存の候補順を維持する。
- 既存の preference 比を使う。合計が正ならその重み、合計が 0 なら等確率である。
- 選択が成功したあとだけ、attempt を 1 増やす。

### 17.10 hard deterministicとspecified route

hard deterministic は次を維持する。

- 既存の最大 preference 選択である。同点のときは候補順の先頭である。
- keyed draw はない。attempt は増えない。mutable RNG は消費しない。
- preference の負値や NaN の検査を、新しい category helper へ移していない。既存の `max` の経路に残す。

specified route は次を維持する。

- origin は `specified_route[0]` である。
- in-trip は `len(log_t_link) - 1` の既存索引である。route progression の式は変えていない。
- 候補と一致しないときは、既存の `ValueError` である。
- keyed draw はない。attempt は増えない。Link 進入回数を key に使わない。

空の specified route list による既存の `IndexError` などは、今回の単位の外である。今回新しく導入した欠陥ではない。

### 17.11 mutable RNG非消費

確率的 route choice は、次を使わない。

- `W.rng.choice()`
- `W.order_control_rng`
- Python 標準 `random`
- built-in `hash()`
- 新しい NumPy Generator

使うのは、保存済み内部 entropy、domain、explicit key から得る pure keyed uniform だけである。

route choice 以外の既存の mutable RNG は変えていない。Vehicle や Node や Link の auto rename、到着 tiebreaker、通常 merge の `W.rng.choice` は、この単位の置換対象ではない。

意図した非互換は次である。

- 確率的 route choice が選ぶ具体的な Link。旧 seed の選択結果との数値一致は要求しない。
- shared RNG の消費順。route choice が `W.rng` を進めなくなる。

維持する契約は次である。

- 候補集合
- 候補順序
- preference 比
- 合計 0 の等確率
- hard deterministic
- specified route
- dead-end
- route progression
- 候補 1 件の決定論性
- 交通処理そのもの

### 17.12 copy・baseline・Candidate・Level 2

- World copy は dill である。`World.__init__` は再実行されない。保存済み内部 entropy は copy される。World 名は entropy に入っていない。
- Vehicle copy は、attempt と Link 進入回数を属性として引き継ぐ。
- 同じ key、同じ候補、同じ重みなら、original と copy は同じ Link を選ぶ。
- copy 側で増えた attempt は、real または original へ戻らない。
- baseline 全 World が通常の `generate()` と `Vehicle.update()` を使うとき、keyed route choice が働く。fork 時点の attempt を引き継ぐ。baseline 開始 timestep は key に入れない。
- Candidate 局所前進は、通常の `Vehicle.update()` も `route_next_link_choice()` も呼ばない。
- Candidate binding transfer は route choice を呼ばない。outlink の下流端から新しい route choice は発生させない。
- Level 2 は route choice を呼ばない。
- Candidate と Level 2 へ、新しい route choice helper の接続は追加していない。

### 17.13 専用testの初期18件

新規 test は `tests_common_seed_rng_route_choice.py` である。最初の test 数は 18 件である。具体的な uniform の小数は、World event の期待値として固定していない。明示 key を `keyed_uniform_value()` へ渡し、production の category helper を使わない test 側の累積規則で期待 Link を求める。

初期 18 件の名前と保証は次である。

1. `test_origin_and_in_trip_domains_are_distinct_fixed_strings`。domain 定数が `origin_route_choice` と `in_trip_route_choice` であり、同じ parts でも domain が違えば uniform が違う。
2. `test_origin_zero_candidates_does_not_draw_or_increment_attempt`。prefer と avoid で origin 候補が 0 件になると `ValueError` であり、attempt は 0、queue に残り、mutable RNG は不変である。
3. `test_origin_one_candidate_selects_without_keyed_draw`。唯一の outlink を直接進入し、origin attempt は 0、mutable RNG は不変である。
4. `test_origin_two_candidates_uses_current_attempt_and_not_world_rng`。key は Vehicle 名、origin Node 名、attempt 0 である。選択は test 側の累積規則と一致し、attempt は 1、mutable RNG は不変である。
5. `test_origin_zero_preference_uses_equal_categories`。preference 合計 0 は等確率 slot であり、attempt は 1 になる。
6. `test_origin_rejected_entry_keeps_the_consumed_attempt`。進入できなくても attempt は 1 のままである。次の成功は attempt 1 の key を使う。
7. `test_origin_negative_preference_does_not_increment_attempt`。負の preference は選択前に `ValueError` であり、attempt は 0 のままである。
8. `test_in_trip_dead_end_sets_no_next_link_without_an_attempt`。outlink がない Node では `route_next_link = None` であり、attempt は 0、進入回数 dict は空、mutable RNG は不変である。
9. `test_in_trip_zero_final_candidates_does_not_increment_attempt`。prefer と avoid で in-trip 候補が 0 件になると `ValueError` であり、attempt は増えない。初回 fixture の不備と修正は **§17.14** に書く。
10. `test_in_trip_one_candidate_does_not_increment_attempt`。唯一候補を直接選び、attempt は 0、進入回数は不変、mutable RNG は不変である。
11. `test_in_trip_two_candidates_uses_link_name_entry_count_and_attempt`。key は Vehicle 名、Link 名、進入回数 1、attempt 0 である。同じ Link 上の次の呼出しは attempt 1 である。進入回数は 1 のままである。
12. `test_in_trip_missing_or_zero_entry_count_stops_without_increment`。進入回数が無いときと 0 のときは `ValueError` であり、0 を 1 にせず、attempt は 0 である。
13. `test_loop_reentry_changes_the_in_trip_uniform`。初期版は、同じ attempt 0 で進入回数 1 と 2 の uniform が違うことを見た。回数 2 と attempt の 0 戻しは、正式な物理再進入ではなく、test が dict と attempt を手で書き換えていた。正式経路への置換は **§17.17** に書く。test 名は維持した。
14. `test_hard_deterministic_keeps_max_preference_without_an_attempt`。最大 preference を選び、同点は登録順の先頭であり、attempt は増えず、mutable RNG は不変である。
15. `test_specified_route_does_not_draw_or_increment_attempt`。origin と in-trip の指定 Link を選び、不一致は `ValueError` であり、attempt は増えない。
16. `test_world_copy_matches_and_keeps_attempts_separate`。copy は entropy を引き継ぐ。copy 側の origin attempt だけが進み、同じ key なら同じ Link 名になる。
17. `test_vehicle_choice_does_not_depend_on_call_order`。同じ seed の別 World で、呼出し順を入れ替えても各 Vehicle の選択は同じである。World 名は key に入らない。
18. `test_single_path_trip_still_reaches_the_only_destination`。hard deterministic の一本道で目的地へ到達し、進入回数は各 Link 1、両 attempt は 0 である。

この 18 件の成功は、helper の異常値、登録順と名前順の差、正式な loop 再進入を、すべて直接証明するものではない。その不足は反証で指摘し、**§17.17** で補強した。

### 17.14 初回fixture失敗と修正

初回の Terminal 確認では、`py_compile` は成功した。専用 test は最初の失敗で停止した。その時点では 18 件全体の成否は未確定である。

失敗した test は `test_in_trip_zero_final_candidates_does_not_increment_attempt` である。

例外は `AttributeError: 'Vehicle' object has no attribute 'route_next_link'` である。

原因は test fixture である。production 欠陥ではない。

- `route_next_link` は `Vehicle.__init__()` の常設属性ではない。
- production は、prefer／avoid 後 0 件の `ValueError` の前に、`route_next_link` を変更しない。
- test は例外の前に既存値を設定していなかった。
- 例外のあとで `vehicle.route_next_link is None` を参照したため、属性未作成の `AttributeError` になった。

修正は test だけである。次の各例外経路で、同一 World の実在 Link object を、事前の `route_next_link` として設定した。

- prefer／avoid 後の 0 件
- missing の Link 進入回数
- zero の Link 進入回数

例外のあとで確認するのは、同じ Link object が維持されること、attempt が 0 であること、Link 進入回数が不変であること、mutable RNG が不変であることである。`None` を事前値にしても属性未作成は解消するが、既存選択を消さないことを見るため、実在 Link を sentinel にした。

修正後の Terminal 確認は、`py_compile` 成功、専用 18 件成功、表示は `Common seed/RNG route choice tests passed.` である。

空白誤記と疑った表示については、Terminal で `grep -F` により実ファイルを確認した。`but that link has no` と `The count is` は、実ファイル上では空白が入っており、修正不要だった。Terminal 表示の詰まりを、実ファイルの誤記と誤認して修正指示を出さない。以後は固定文字列で確認する。

### 17.15 既存回帰

初期 18 件の成功のあと、利用者の Terminal で次を実行した。

既存 route choice 検証は `python tests/test_verification_route_choice.py` である。エラー、Traceback、標準失敗出力はなく終了した。この script は成功メッセージを表示しない形式である。旧 seed の個別 Link を固定する test ではなく、複数経路の均衡を見る。確率的選択の具体 Link が旧結果と違いうることは、**§17.11** の意図した非互換である。この終了をもって、候補集合や均衡の意味まで壊れたとは扱わない。

keyed uniform 基盤は `python tests_common_seed_rng_keyed_uniform.py` である。表示は `Common seed/RNG keyed uniform tests passed.` である。

Vehicle Link 進入状態は `python tests_vehicle_link_entry_state.py` である。表示は `Vehicle link-entry state tests passed.` である。

### 17.16 読取り専用反証レビュー

Cursor Grok 4.7、effort high で、読取り専用の反証レビューを実施した。Cursor は編集、test、`py_compile`、simulation、Git を行っていない。

総合判定は、このまま受入れ可能、である。blocking はない。high はない。この判定は、当時の production と初期 18 件に対する読取りである。受入れそのものは、その後の test 補強と Terminal 再確認を経ている。Cursor 報告をそのまま正本の最終判定にはしていない。

読取りで成立した主要事項は次である。

- origin の key と domain
- in-trip の key と domain
- 候補 0 件、1 件、2 件以上の分岐
- attempt の更新位置
- origin の進入失敗後も attempt を戻さないこと
- missing と 0 の進入回数を 1 へ補正しないこと
- hard deterministic の維持
- specified route の維持
- mutable RNG の非消費
- copy と baseline の継承
- Candidate と Level 2 への新しい接続がないこと

方式差による待ち timestep 数は、blocking にしなかった。同じ Link 終端での待ち timestep 数が方式間で違うと、通過時に使う attempt 番号はずれ得る。**§14.9** は各再選択を別 attempt とする。揃えるのは同じ attempt 番号の uniform である。待ち時間や使用 attempt 番号の強制一致は契約ではない。N=1 の完全一致は統合回帰で確認する。

反証で判明した medium は次である。

1. 当時の fork fixture は、登録順と Link 名順が同じだった。prefer／avoid 後の名前 sort を削除しても、18 件では検出できない。
2. 候補 1 件などで helper を呼ばないことは、mutable RNG の比較だけでは証明できない。helper は pure であり、RNG を変えない。
3. loop 再訪 test は、正式な物理再進入を使わず、進入回数と attempt を手で変えていた。
4. category helper の異常値と境界を、18 件では直接検証していなかった。

low は次である。

- taxi の専用 test はない。
- in-trip の preference 合計 0 は、origin 側の等確率 test だけである。
- zero count の例外のあと、mutable RNG を再比較していない。
- specified route の test は、複数 Link の progression ではない。
- `Vehicle.__init__()` の comment が、前単位の「attempt を増やさない」のままだった。
- 有限 weight の合計が overflow する極端値は、通常の route preference の範囲外である。
- route choice 毎の hash の性能は未測定である。合否条件ではない。

反証は、受入れ前の追加必須回帰はない、とした。そのうえで、medium のうち test 契約上重要な事項と、古い comment は、受入れ前に補強した。helper 非呼出しを monkeypatch で証明する test、taxi、in-trip 合計 0 の重複、specified route の複数 Link、performance は追加していない。

### 17.17 反証後の4点補強

production の route choice ロジックは変更していない。変更したのは `tests_common_seed_rng_route_choice.py` と、`uxsim/uxsim.py` の Vehicle の 3 属性付近の comment だけである。

#### 候補順序test

追加 test は `test_prefer_uses_link_name_order_not_registration_order` である。名前は prefer だけに合わせた。この test は avoid を実行しない。

fixture は次である。

- 登録順は `z_link`、その次が `a_link` である。
- Link 名順は `a_link`、その次が `z_link` である。
- prefer は両方を含む。
- weight は両方 1.0 である。

等重みでは、`[0, 1)` のどの uniform でも、登録順と名前順の期待 Link は反対になる。test は explicit origin key で uniform を得て、両期待 Link が異なることを、`Node.generate()` の前に assert する。production の結果は名前順の期待 Link である。origin attempt は 1 である。`W.rng` と `W.order_control_rng` は不変である。

avoid 後の sort は、origin と in-trip で prefer と同じ `sorted(..., key=name)` である。読取りで確認し、専用 test は重複追加していない。

#### helperの異常値

追加 test は `test_route_choice_candidate_helper_rejects_invalid_weights_and_uniforms` である。`select_route_choice_candidate()` を直接呼ぶ。

確認したのは、候補 0 件の `ValueError`、候補 1 件が weight と uniform を読まず唯一候補を返すこと、weight 数が足りないこと、weight 数が多いこと、負値、NaN、`inf`、`-inf`、`True`、`False`、uniform の `-0.1`、`1.0`、NaN、`True`、整数 `0` である。候補 1 件が不正値を読まないことは、draw なし契約であると test の comment に書いた。

#### helperの境界

追加 test は `test_route_choice_candidate_helper_handles_boundaries` である。

確認したのは、正の weight で `u=0.0` が先頭であること、等 weight で `nextafter(0.5, 0.0)` が先頭であること、`u=0.5` が 2 番目であること、合計 0 の 3 候補で `0.0`、`0.5`、`0.9` が slot 0、1、2 であること、候補順を維持することである。比較は strict `<` である。

最後の候補への浮動小数点 remainder fallback は、安全に到達させる直接 test を追加していない。helper 本体は変更していない。

#### 正式loop再進入

既存の `test_loop_reentry_changes_the_in_trip_uniform` を、同名のまま置換した。追加件数には数えない。

経路は `feeder`、`loop_in`、`hop`、`return_feeder`、再び `loop_in` である。`n2` の登録順は `hop`、`spur` であり、両方を候補にする。使用関数は `Node._transfer_one_vehicle_between_links()` と `Vehicle.route_next_link_choice()` である。choice が `spur` を選んでも、帰還の移動は `hop` を指定する。transfer は route choice をしない。

この test 単独で確認するのは次である。

1. `loop_in` への初回の正式進入で、回数は 1、attempt は 0 である。
2. in-trip 選択のあと、attempt は 1 である。選択は進入回数 1、attempt 0 の key と一致する。
3. `hop` への正式進入で、attempt は 0 に戻る。
4. `return_feeder` への正式進入でも、attempt は 0 である。
5. `loop_in` への正式再進入で、回数は 2、attempt は 0 である。
6. 進入回数 1・attempt 0 と、進入回数 2・attempt 0 の uniform は異なる。
7. 2 回目の production 選択は、進入回数 2 の key と一致する。
8. `order_control_visit_id` は 0 のままである。key の第 3 要素は進入回数 2 であり、visit id ではない。
9. origin attempt は 0 のままである。
10. mutable RNG は不変である。

#### comment

`Vehicle.__init__()` の comment を、現在の実装に合わせた。属性名、初期値、配置は変えていない。

明記した内容は次である。

- Link 進入回数は Vehicle の生涯で累積する。
- current Link attempt は、現在 Link の訪問中に行った確率的 in-trip 選択の回数である。
- origin attempt は、最初の Link へ入る前の確率的 origin 選択の回数である。
- 候補 2 件以上の通常の確率選択が成功したときだけ、`Node.generate()` と `route_next_link_choice()` が増やす。
- 候補 0 件、候補 1 件、hard deterministic、specified route では増やさない。
- 新しい Link への物理進入で 0 に戻すのは、current Link attempt だけである。
- origin attempt は Link 進入では reset しない。

### 17.18 最終専用test 21件

補強後の test 数は 21 件である。初期 18 件は残している。loop test は同名置換であり、21 件への加算ではない。

追加 3 件は次である。

1. `test_prefer_uses_link_name_order_not_registration_order`
2. `test_route_choice_candidate_helper_rejects_invalid_weights_and_uniforms`
3. `test_route_choice_candidate_helper_handles_boundaries`

最終の Terminal 確認は次である。

- `py_compile` は成功した。
- 専用 21 件は成功した。
- 表示は `Common seed/RNG route choice tests passed.` である。
- `git diff --check` の出力はなかった。
- helper module は反証後に変更していない。
- route choice の production 処理は反証後に変更していない。変更した production 箇所は、`Vehicle.__init__()` の説明 comment だけである。

### 17.19 最終検証結果

利用者の Terminal で確認済みの結果は、次の順である。

1. 初回は `py_compile` 成功のあと、**§17.14** の fixture 不備で専用 test が停止した。18 件全体はその時点では未確定である。
2. fixture 修正後、`py_compile` 成功、専用 18 件成功、表示は `Common seed/RNG route choice tests passed.` である。
3. 既存回帰は **§17.15** のとおり成功した。`tests/test_verification_route_choice.py` は成功メッセージのない終了である。
4. 読取り専用反証は **§17.16** のとおり、編集も実行もしていない。blocking と high はなかった。
5. 反証後の補強のあと、`py_compile` 成功、専用 21 件成功、同じ成功表示、`git diff --check` の出力なし、である。

Cursor の反証と、Terminal の実行確認は別である。21 件の成功は、remainder fallback の直接実行や、N=1 の完全一致を含むものではない。

### 17.20 受入れ判定

今回の実装単位を受入れ可能とする。理由は次である。

- origin と in-trip の event key が、**§14.8**、**§14.9**、**§32.21.3** と一致する。
- domain を分離した。
- object identity や整数 ID に依存しない。
- 候補 0 件、1 件、2 件以上を明示的に分岐した。
- 確率的な候補 2 件以上だけが draw する。
- attempt は選択成功のあとだけ増える。
- origin の進入失敗後も attempt を戻さない。
- in-trip の Link 進入回数の欠落を、1 へ暗黙補正しない。
- hard deterministic と specified route を維持した。
- mutable RNG を route choice で消費しない。
- copy と baseline で同じ event key を使える。
- Candidate と Level 2 へ誤って接続していない。
- 初回の `AttributeError` を production 欠陥と混同しなかった。
- 専用 18 件と既存回帰が成功した。
- 反証で blocking と high はなかった。
- 反証で判明した test の穴を、21 件へ補強した。
- 正式な loop 再進入、回数の増加、attempt の reset、再選択を、1 本の test で横断した。
- test 成功だけを受入れ理由にしていない。
- Python 初心者が、候補分岐と attempt の位置を追える。

受入れ範囲は、origin route choice の keyed 化、in-trip route choice の keyed 化、route choice category helper、attempt 増分、候補別分岐、mutable RNG 非消費、である。4方式共通 seed／RNG 改修全体の完了ではない。

### 17.21 今回未実装の範囲

次は未実装、または未完了である。

- arrival tiebreaker の keyed 化
- Node 訪問番号の production 利用
- 通常 merge 用の sequential RNG
- `_transfer_normal_merge()` の乱数変更
- Candidate selection RNG の変更
- N=1 BATCH 対 FCFS の完全一致
- 4方式統合回帰
- route choice の hash 性能確認
- taxi の専用 route choice test
- specified route の複数 Link progression の追加 test
- baseline の full simulation
- Candidate の full simulation
- performance benchmark

新 BATCH は未実装・未採用である。正の合計で最後の候補へ落ちる remainder の直接 test も、この単位にはない。

### 17.22 実装完了までの現在地

完了した単位は次である。

1. 内部 entropy 保存と pure keyed uniform helper。詳細は **§15** である。
2. Vehicle の Link 進入状態と物理進入追跡。詳細は **§16** である。
3. origin・in-trip route choice の keyed 化。詳細は本 **§17** である。

残る単位は次である。

4. arrival tiebreaker の keyed 化と、Node 訪問番号の production 利用。
5. 通常 merge 用 RNG の分離。
6. N=1 BATCH 対 FCFS と、4方式統合回帰。
7. 最終正本記録と、全体受入れ。

次の実装単位を完了すると、主要 production 接続の残りは、通常 merge 用 RNG と統合回帰になる。

### 17.23 次の直接作業

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で独立確認することである。

その後の予定は、必要なら文書を修正し、production 2 ファイル、専用 test 1 ファイル、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push はその確認後の別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、次の実装単位である arrival tiebreaker の keyed 化と、Node 訪問番号の production 利用へ進む。

production 2 ファイルは `uxsim/uxsim.py` と `uxsim/common_seed_rng_route_choice.py` である。専用 test 1 ファイルは `tests_common_seed_rng_route_choice.py` である。Markdown 3 ファイルは、本ファイル、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`、`ORDER_EXCHANGE_PROGRESS_4.md` である。

利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。`research_scripts/route_choice_rng_diagnostic.py` も、この記録の対象外である。

### 17.24 検索語

origin route choice keyed化、in-trip route choice keyed化、origin_route_choice、in_trip_route_choice、origin_route_choice_attempt_count、current_link_route_choice_attempt_count、link_entry_count_by_link_name、Vehicle正式名、origin Node正式名、current Link正式名、累積進入回数、explicit key、pure keyed uniform、common seed RNG、candidate 0件、candidate 1件、candidate 2件以上、dead-end、prefer、avoid、Link名順、登録順、route preference、合計0、等確率、hard deterministic、specified route、mutable RNG非消費、W.rng非消費、W.order_control_rng非消費、select_route_choice_candidate、World copy、baseline fork、Candidate非接続、Level 2非接続、初回fixture失敗、route_next_link未作成、AttributeError、sentinel Link、専用test 18件、反証、blockingなし、highなし、候補順序test、helper境界test、正式loop再進入、専用test 21件、Common seed/RNG route choice tests passed、tests/test_verification_route_choice.py、keyed uniform回帰、Vehicle Link進入状態回帰、arrival tiebreaker未実装、Node訪問番号未利用、normal merge RNG未実装、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、3a4c3ee、originでどの乱数を使うか、Link終端で毎timestep経路を再選択する、capacity不足でorigin attemptを戻すか、同じLinkでroute choiceを何回試したか、loop再進入で同じ乱数になるか、candidateが1本なら乱数を使うか、candidateが0本ならどうなるか、preference合計0ならどう選ぶか、preferとavoid後の順序、登録順とLink名順、hard deterministicでattemptが増えるか、specified routeでattemptが増えるか、W.rngを経路選択で消費するか、baseline copyで同じ経路選択になるか、Candidateで通常route choiceを行うか、Level 2でroute choiceを行うか、route_next_linkのfixtureが失敗した、test名と実際の対象、route choice実装後の次作業、実装完了までの残り区分

## 18. arrival tiebreaker keyed化とNode訪問番号のproduction利用の実装・反証・受入れ（2026-11-23）

### 18.1 記録の位置づけ

執筆日は2026-11-23である。本節は、arrival tiebreaker の keyed 化と、Node 訪問番号の production 利用について、実装、専用 test、既存 test 更新、fixture 不備、交差回帰、読取り専用反証、Candidate コメント修正、Terminal 独立確認、最終受入れを記録する詳細正本である。

関係は次である。

- **§14** は、4方式共通 seed／RNG 改修の具体実装前設計の正本である。本節は **§14.11** の契約を実装した結果であり、**§14** の本文は削除も書換えもしない。
- **§15** は、内部 entropy 保存と pure keyed uniform helper の実装・反証・受入れ結果の正本である。
- **§16** は、Vehicle 状態と Link 物理進入 helper の実装・反証・受入れ結果の正本である。
- **§17** は、origin・in-trip route choice keyed 化の実装・反証・受入れ結果の正本である。
- 本 **§18** は、arrival tiebreaker keyed 化と Node 訪問番号の production 利用の実装・反証・受入れ結果の正本である。
- 研究契約の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** である。実装前の具体設計確定は **§32.24** である。内部 entropy と pure keyed helper の実装結果は **§32.25** である。Vehicle 状態と Link 進入 helper の実装結果は **§32.26** である。route choice keyed 化の実装結果は **§32.27** である。本単位の全体設計上の実装結果は **§32.28** である。
- 進捗の対応節は `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.29** である。**§21.9.28** は前の実装単位の進捗として残す。

最新の詳細参照先は本 **§18** である。**§14** から **§17**、**§32.21**、**§32.24** から **§32.27**、**§21.9.28** は残す。今回の実装は、4方式共通 seed／RNG 改修全体の完了ではない。通常 merge 用 RNG は未実装である。N=1 BATCH 対 FCFS 回帰と 4方式統合回帰は未実行である。新 BATCH は未実装・未採用である。

test 成功だけを受入れ理由にはしない。Cursor の報告を無条件には正本化していない。反証は読取りであり、Terminal の `py_compile` と test と `git diff --check` は利用者の独立確認である。Cursor は Git 操作を行っていない。

### 18.2 今回の実装範囲

今回の production 接続は、arrival tiebreaker だけである。origin route choice、in-trip route choice、通常 merge、Candidate selection RNG、BATCH 形成、BATCH service queue、signal 制御、Link 進入 helper の接続位置、`order_control_visit_id` の意味は変えていない。

置き換えたのは、初回到着の `W.rng.random()` と、再訪到着の `W.order_control_rng.random()` である。どちらも、保存済み内部 entropy、固定 domain `arrival_tiebreaker`、明示 key から得る pure keyed uniform になった。値は `[0, 1)` の float である。

Node 訪問番号は、新しい mutable counter ではない。対象 Node を終端とする全 inlink について、その Vehicle の Link 別累積進入回数を合計した値である。

### 18.3 変更したproductionとtest

production:

- `uxsim/uxsim.py`
- 新規 `uxsim/common_seed_rng_arrival_tiebreaker.py`
- `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`。ここは production 処理ではなく、古い説明コメント 4 行だけである。詳細は **§18.18** である。

test:

- 新規 `tests_common_seed_rng_arrival_tiebreaker.py`
- 更新 `tests_order_control_current_visit_arrival.py`

`uxsim/__init__.py` は変えていない。helper は public API へ出していない。

新規 module にした理由は次である。

- Node 訪問番号の算出と arrival key の構築を `uxsim.py` から分ける。
- World、Vehicle、Visit を変更しない pure helper にする。
- real World、baseline full World、World copy で同じ関数を使う。
- route choice helper と generic hash helper と責務を分ける。

関数は `node_visit_number_from_link_entries(vehicle, node)` と `arrival_tiebreaker_key_parts(vehicle_name, node_name, node_visit_number)` である。定数は `ARRIVAL_TIEBREAKER_DOMAIN` である。tiebreaker の保存、Visit 開始、到着判定、台帳更新は、この module に入れていない。

専用 test を新規ファイルにした理由は、Node 訪問番号、arrival key、初回と再訪、current Visit 保存、legacy 初回台帳、mutable RNG 非消費、World copy、方式非依存、Candidate／Level 2 接続契約を、keyed uniform test、Link 進入 test、route choice test へ混ぜないためである。

`uxsim.py` で変えた production 関数は次である。

- `Vehicle.record_order_control_node_arrival(node)`。simulation が使う正式 recorder である。
- `Vehicle.record_order_control_node_first_arrival(node)`。production caller は確認されなかった。legacy 台帳だけの補助関数である。`W.rng` を消費しないよう、同じ keyed 経路にした。current Visit へは保存しない。今回は削除しない。
- `Vehicle.__init__()` の属性説明 docstring。初回は `W.rng`、再訪は `W.order_control_rng`、という古い説明を、現在の keyed 契約へ更新した。属性名、初期値、保存構造、代入は変えていない。

### 18.4 現行arrival記録制御フロー

正式な arrival recorder は `Vehicle.record_order_control_node_arrival(node)` である。

主な production caller は次である。

- `Vehicle.update()`。Link 終端で、通常の転送要求と、taxi の目的地更新の経路が、`node.incoming_vehicles` へ追加したあとで呼ぶ。
- Candidate 局所前進 `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals`。対象 Node へ新たに到達した Vehicle について、既存の `vehicle.record_order_control_node_arrival(target_node)` を呼ぶ。今回、この call site の位置は変えていない。

既存の処理順は次である。

1. Vehicle が Link 終端へ到達する。
2. `node.incoming_vehicles` へ追加する。
3. current Visit が存在する。
4. その Visit の arrival は未記録である。
5. arrival recorder を呼ぶ。
6. arrival time と arrival tiebreaker を保存する。
7. baseline collector があれば、保存済みの tiebreaker を渡す。

次も維持した。

- Link へ物理進入しただけでは arrival tiebreaker を生成しない。進入 helper は回数だけを増やす。
- `begin_order_control_visit_on_link_entry()` は、対象 Node なら `arrival_time` も `arrival_tiebreaker` も `None` の Visit を作る。生成は入れていない。
- Link 終端到達前には生成しない。
- `order_control_eligible` でない Node は何もしない。
- `order_control_type="none"` は何もしない。signalized UXsim の通常実 World へ、arrival tiebreaker を新規導入しない。
- current Visit が無いのは `ValueError` である。
- current Visit の Node が到着 Node と違うのは `ValueError` である。
- arrival time と tiebreaker の片方だけがある状態は `ValueError` である。
- 両方が記録済みなら、Node 訪問番号を算出する前に return する。同じ Visit では再生成しない。`incoming_vehicles` への再登録でも値は変わらない。

single-trip の目的地終端と、dead-end による trip abort は、従来どおりこの recorder を呼ばない。これは今回の変更で増えた経路ではない。研究上、order-control Node を目的地にしない前提は維持する。

`record_order_control_node_first_arrival(node)` は次である。

- production caller は、今回の確認範囲では無かった。専用 test が呼ぶ。
- legacy の `order_control_node_arrival_times` と `order_control_node_arrival_tiebreakers` だけを保存する。
- current Visit へは保存しない。関数名と docstring に合う。
- keyed 化済みであり、`W.rng` も `W.order_control_rng` も消費しない。
- 既にその Node 名が legacy 時刻台帳にあれば上書きしない。
- Node 訪問番号が 1 未満なら保存前に `ValueError` である。
- 今回は削除しない。将来の整理候補ではあるが、受入れを妨げない。本記録関数と生成手順が重複するため、将来乖離し得ることは low として残す。

### 18.5 arrival tiebreaker用domain

固定 domain は `arrival_tiebreaker` である。定数名は `ARRIVAL_TIEBREAKER_DOMAIN` である。

- origin route choice の `origin_route_choice` と共有しない。
- in-trip route choice の `in_trip_route_choice` と共有しない。
- 通常 merge と共有しない。
- caller が自由文字列を渡す一般 API にはしない。recorder は定数だけを渡す。
- 初回と再訪で同じ domain である。
- 同じ key parts でも domain が違えば uniform が違うことを、専用 test が文字列 `"arrival_tiebreaker"` で確認する。

### 18.6 Node訪問番号

helper は `node_visit_number_from_link_entries(vehicle, node)` である。

定義は次である。

- `node.inlinks` の全 Link を明示的な for loop で走査する。
- 各 Link の正式名を使う。
- `vehicle.link_entry_count_by_link_name` から累積進入回数を取る。
- その名前が無いときは 0 である。
- それらの合計が Node 訪問番号である。

例:

- 初回。対象 Node 向けの inlink A が 1 で、他の対象 inlink は 0 または未登録なら、Node 訪問番号は 1 である。
- 別 inlink からの再訪。inlink A が 1、inlink B が 1 なら、Node 訪問番号は 2 である。現在 Link の回数だけではない。
- 同一 inlink への再進入。inlink A が 2 で、他の対象 inlink が 0 なら、Node 訪問番号は 2 である。
- **§32.21.6** の例と同じく、3 本の inlink が 2、1、0 なら、Node 訪問番号は 3 である。

次を守った。

- 現在 Link の回数だけを Node 訪問番号にしない。
- `order_control_visit_id` で代用しない。Visit ID は、対象 Node をまたぐ Vehicle 単位の連番である。Node 訪問番号は、その Node を終端とする進入回数の合計である。
- arrival log を正本にしない。
- `log_t_link` を正本にしない。
- Node 別の新しい mutable counter を追加しない。計算済み番号を current Visit へ重複正本として保存してもいない。必要時にその場で合計する。
- 対象 Node を終端としない Link は、`node.inlinks` に無いので合計へ入れない。
- parallel Link は正式名が違うので、別々に合計する。同一 Node の inlink 辞書は Link 正式名を key にする。
- Link object identity と Node object identity は key に使わない。合計の入力は正式名である。
- missing は 0 である。個別 Link の 0 は許容する。
- 負値、bool、float、str は `ValueError` である。`bool` は int として扱わない。
- helper は合計 0 をそのまま返す。1 へ補正しない。World、Vehicle、Visit は変えない。tiebreaker も生成しない。
- arrival recorder が、合計 1 未満を `ValueError` にする。そのときは uniform も保存もしない。mutable RNG も消費しない。
- 手動 fixture の不足を production が埋めない。

正式な物理進入のあと、対象 inlink の回数は進入 helper により記録済みである、という前提は **§16** のとおりである。到着記録は、その回数を読み直す。

### 18.7 arrival tiebreakerのevent key

具体形は `(vehicle.name, node.name, node_visit_number)` である。helper は `arrival_tiebreaker_key_parts` であり、この 3 要素の tuple を返すだけである。

要素は次である。

- Vehicle 正式名。auto rename 後の `vehicle.name` である。同一 World 内で名前が衝突すると、auto rename でなければ `ValueError` である。
- Node 正式名。`node.name` である。
- production がその場で算出した Node 訪問番号である。

次は入れない。

- object identity
- Vehicle ID
- Node 整数 ID
- timestep
- arrival time
- inlink 名
- order-control type
- World 名
- clearance
- batch size
- transaction case
- signal phase

同じ Vehicle、同じ Node、同じ訪問番号は、同じ event である。同じ Node への再訪は、Node 訪問番号が違うので別 event である。別 Vehicle は別 event である。別 Node は別 event である。

baseline fork と real World は、同じ物理訪問なら同じ key である。World 名も baseline 開始 timestep も key に入らない。fork 後に物理訪問回数が違えば、Node 訪問番号が違うので別 key である。

rollback 後の同じ未記録 Visit も同じ key である。Candidate 局所前進は Link 進入回数を変えない。失敗時の snapshot は到着フィールドを戻す。再試行は同じ回数から同じ uniform を得る。keyed 値は共有 stream を消費しない。

### 18.8 初回訪問と再訪

初回は Node 訪問番号 1 である。current Visit の `arrival_time` と `arrival_tiebreaker` へ保存し、legacy の `order_control_node_arrival_times` と `order_control_node_arrival_tiebreakers` へも同じ値を保存する。

再訪は Node 訪問番号 2 以上である。current Visit へだけ保存する。legacy 初回台帳は上書きしない。

両方とも、同じ domain、同じ key 形、同じ helper である。初回だけの `W.rng` 分岐と、再訪だけの `W.order_control_rng` 分岐は残していない。同じ Visit では再生成しない。

legacy へ書くかの判定は、`node.name` が `order_control_node_arrival_times` に無いか、である。Node 訪問番号が 1 かではない。正式な進入と `Vehicle.update` の到着では、最初の到着時に回数は 1 であり、legacy も同時に書かれる。2 回目以降は回数が 2 以上で、legacy は既にある。

台帳の手動削除や、caller の無い legacy helper の単独利用では、legacy の有無と Node 訪問番号がずれ得る。arrival recorder は、その登録済み不変条件を重複検査しない。これは反証の low であり、blocking ではない。

### 18.9 生成タイミングと保存順序

`record_order_control_node_arrival()` の順序は次である。

1. eligible と `order_control_type` を確認する。対象外なら return する。
2. current Visit の存在を確認する。無ければ `ValueError` である。
3. current Visit の Node が到着 Node と一致するか確認する。違えば `ValueError` である。
4. arrival time と tiebreaker の片側だけが埋まっていれば `ValueError` である。
5. 両方が記録済みなら return する。ここより前なので、Node 訪問番号は再計算しない。
6. Node 訪問番号を算出する。
7. 1 未満なら、保存前に `ValueError` で停止する。1 へ補正しない。
8. key parts を別変数で作る。
9. `keyed_uniform_value(saved_internal_entropy, ARRIVAL_TIEBREAKER_DOMAIN, key_parts)` で uniform を別変数へ取る。
10. arrival time を `W.T * W.DELTAT` として別変数で作る。
11. current Visit へ arrival time と tiebreaker を保存する。
12. その Node 名が legacy 時刻台帳に無ければ、同じ arrival time と同じ tiebreaker を legacy の 2 辞書へ保存する。
13. `W._order_control_baseline_collector` があれば、current Visit に保存済みの tiebreaker を `record_baseline_arrival` へ渡す。collector は別の乱数を引かない。

例外の位置は次である。

- invalid な Link 進入回数は、helper 内で、保存前に停止する。
- Node 訪問番号 0 は、uniform の前に停止する。保存しない。
- keyed uniform の例外は、保存の前である。
- Visit 不整合は、訪問番号の前である。
- collector の例外だけは、current Visit と、初回なら legacy への保存のあとである。

collector が例外を出したあとで同じ Visit を再呼出しすると、Visit が記録済みなので 5 で return し、collector 記録だけが欠け得る。これは、保存のあとで collector を呼ぶ既存順序であり、今回新たに導入した欠陥ではない。Candidate 局所前進は、この recorder の例外を snapshot で戻す。実 World の `Vehicle.update()` には、その snapshot は無い。受入れを止める追加検査にはしない。

### 18.10 mutable RNG非消費

arrival tiebreaker の生成では、次を使わない。

- `W.rng.random()`
- `W.order_control_rng.random()`
- Python 標準 `random`
- built-in `hash()`
- 新しい NumPy Generator

使うものは、保存済み内部 entropy、domain `arrival_tiebreaker`、明示 event key、`keyed_uniform_value()` である。

変えていないものは次である。

- 通常 merge の `W.rng`。`_transfer_normal_merge()` は、非 hard deterministic で従来どおり `W.rng.shuffle` と `W.rng.choice` を使う。今回の単位では分離していない。
- route choice。domain、key、attempt、`uxsim/common_seed_rng_route_choice.py` は未変更である。
- Vehicle 色など、到着以外の既存 RNG 用途。
- Candidate selection RNG。

意図した非互換は次である。

- arrival tiebreaker の具体的な float。
- その後の `W.rng` と `W.order_control_rng` の state。
- 同着時の具体的な順位。
- その順位差から波及する交通結果。

旧 trial の tiebreaker 値との一致は要求しない。

維持する契約は次である。

- arrival 条件。
- arrival timestep。時刻の式は `W.T * W.DELTAT` のままである。
- Visit identity。
- 値が `[0, 1)` であること。
- 時刻が違う Vehicle は時刻を優先すること。
- 同着の中で tiebreaker を使う順位決定。FCFS rank と BATCH trigger rank は、引き続き current Visit の `(arrival_time, arrival_tiebreaker, veh.id)` を読む。legacy 辞書は順位の正本ではない。
- 保存先。
- batch assignment。
- confirmed rank。
- passage。
- trip end。
- order-control type の意味。

### 18.11 legacy first-arrival台帳とcurrent Visit

legacy 台帳は次である。

- `order_control_node_arrival_times`
- `order_control_node_arrival_tiebreakers`
- key は Node 名である。
- 初回訪問だけの互換台帳である。
- 再訪では上書きしない。
- current Visit の正本ではない。

current Visit は次である。

- `order_control_current_visit["arrival_time"]`
- `order_control_current_visit["arrival_tiebreaker"]`
- 各訪問の正本である。
- arrival 成立前は両方 `None` である。
- 同じ Visit では一度だけ保存する。
- FCFS rank と BATCH trigger rank は current Visit を読む。

`Vehicle.__init__()` の属性説明は、初回 `W.rng`、再訪 `W.order_control_rng` という古い文を残していない。domain、key、初回と再訪の同じ形、到着前は `None`、同じ Visit では再生成しない、`W.rng` と `W.order_control_rng` を使わない、legacy は初回だけで current Visit の正本ではない、と書いた。代入は空 dict と `None` のままである。

### 18.12 baseline・Candidate・Level 2

#### baseline full World

- World copy は保存済み内部 entropy を引き継ぐ。`World.__init__()` は copy の復元では再実行されない。
- Vehicle copy は Link 進入回数を引き継ぐ。
- current Visit も copy される。snapshot 時点で到着済みの Visit は、既存の tiebreaker のままである。再生成しない。
- snapshot 後に baseline 内で新規到着する Visit は、同じ recorder が key から値を得る。
- 同じ Vehicle 名、同じ Node 名、同じ Node 訪問番号なら、real World と同じ tiebreaker である。到着時刻が違っても tiebreaker は同じである。
- baseline 開始 timestep は key に入らない。
- fork 後に物理訪問回数が違えば別 key である。
- collector は、保存済み tiebreaker を受け取る。別の乱数正本にしない。
- original と copy の台帳は独立である。copy 側の保存は original へ戻らない。

#### Candidate局所前進

対象関数は `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` である。

既存接続は次である。

- 局所前進は Link 進入ではない。同一 inlink 上で位置を進め、対象 Node へ新たに到達した Vehicle だけを `incoming_vehicles` に足す。
- その Vehicle について `vehicle.record_order_control_node_arrival(target_node)` を呼ぶ。今回、呼出し位置は変えていない。
- Node 訪問番号は、copy 時点までにその inlink へ進入した回数を含む合計である。局所前進自体は Link 進入回数と attempt を増やさない。
- 同じ Visit の tiebreaker は再生成しない。
- Candidate binding transfer のあと、outlink の下流端退出を、新しい通常 Node 到着としては記録しない。binding 側は `record_order_control_node_arrival` を呼ばない。
- 局所 World 内の arrival 値を real World へ戻さない。
- 到着処理が失敗したときは、呼出し前の snapshot から局所 World の該当状態を戻す。復元は新しい到着ではない。

古いコメントは **§18.18** で直した。処理はコメント修正の前から keyed だった。

#### Level 2

- 現行 Level 2 mimic は、正式な将来交通 World ではない。
- `_build_mimic_world` は別 World を作る。mimic Vehicle は `Vehicle.__init__()` の初期値を持つ。Link 進入回数を実 World から追加コピーしない。
- `record_order_control_node_arrival` を呼ばない。inlink 上の仮想到着は、`incoming_vehicles` への追加と通過時刻観測であり、正式な arrival 台帳ではない。
- Visit 開始 helper の内部へ arrival tiebreaker 生成を入れていない。`_transfer_vehicle_reference` は recorder を呼ばない。
- Node 訪問番号用の正式進入状態を、Level 2 のために新設しない。
- keyed arrival tiebreaker を Level 2 へ接続しない。
- snapshot 時点の既存 arrival tiebreaker を、従来の個別コピーで失ってはいない。新しい生成はしない。
- この非接続を、将来の全 World 型 BATCH へ一般化しない。将来方式は World 全体を copy する設計であり、正式な Vehicle 状態を維持する。

### 18.13 専用test 19件

新規ファイルは `tests_common_seed_rng_arrival_tiebreaker.py` である。件数は 19 である。期待 uniform は、test に書いた domain 文字列 `"arrival_tiebreaker"` と、test に書いた `(Vehicle名, Node名, 訪問番号)` を `keyed_uniform_value()` へ渡して作る。production の key helper で期待 key を作らない。Node 訪問番号の期待値は、test 側が対象 Node の inlink と回数から合計する。固定小数の uniform は書いていない。

各 test の保証は次である。

1. `test_arrival_tiebreaker_domain_is_distinct_from_route_choice`。定数と文字列 `"arrival_tiebreaker"` が一致し、`origin_route_choice` と `in_trip_route_choice` とは違う。同じ parts でも domain が違えば uniform が違う。
2. `test_node_visit_number_is_one_on_the_first_inlink_entry`。対象 inlink が 1、他は未登録で、訪問番号は 1 である。
3. `test_node_visit_number_sums_every_inlink_on_a_later_visit`。別 inlink が 1 と 1 で合計 2 である。現在 Link の回数だけではない。
4. `test_same_inlink_reentry_makes_node_visit_number_two`。正式な物理再進入で、同一 inlink の回数が 2 であり、その Node の訪問番号は 2 である。
5. `test_links_that_do_not_end_at_the_node_are_excluded`。終端が違う Link の大きい回数は合計へ入らない。
6. `test_zero_on_one_inlink_is_allowed_when_the_total_is_positive`。個別の 0 は許容し、他の対象 inlink と合計する。
7. `test_invalid_link_entry_counts_are_rejected`。負値、`True`、`False`、float、str を拒否する。
8. `test_zero_node_visit_number_does_not_record_a_tiebreaker`。合計 0 は `ValueError` であり、1 へ補正せず、tiebreaker を保存せず、`W.rng` と `W.order_control_rng` は不変である。
9. `test_record_order_control_node_first_arrival_stores_keyed_legacy_value`。caller の無い legacy helper が、明示 key の値を初回台帳へ 1 回だけ保存する。current Visit は作らない。再呼出しでも上書きしない。合計 0 は保存しない。
10. `test_first_arrival_stores_the_keyed_tiebreaker_once`。訪問番号 1、current Visit と legacy が同じ値、同じ Visit の再登録では再生成しない。時刻が違っても tiebreaker は同じである。timestep は key に入らない。
11. `test_revisit_uses_a_new_key_and_keeps_the_first_ledger`。2 回目は訪問番号 2 で、1 回目と uniform が違い、legacy は初回値のままである。`order_control_visit_id` を 9 にずらしてあり、Visit ID を key に使う実装は、訪問番号 2 の明示 key と一致しない。
12. `test_another_vehicle_name_is_a_different_arrival_key`。同じ Node、同じ訪問番号でも Vehicle 名が違えば別 key である。別 World で処理順を入れ替えても、各 Vehicle の値は明示 key と一致する。
13. `test_world_copy_keeps_the_same_tiebreaker_on_a_separate_ledger`。entropy、Vehicle 名、Node 名、訪問番号が同じなら同じ値である。copy の台帳更新は original へ戻らない。
14. `test_order_control_type_is_not_part_of_the_arrival_key`。FCFS と BATCH は、同じ明示 key なら同じ値である。方式名は key に入らない。
15. `test_physical_entry_does_not_record_an_arrival_tiebreaker`。正式な物理進入と Visit 開始だけでは、tiebreaker は `None` のままである。
16. `test_none_order_control_type_does_not_record_an_arrival_tiebreaker`。`order_control_type="none"` は、回数が空でも生成しない。
17. `test_ineligible_node_does_not_record_an_arrival_tiebreaker`。eligible でない Node は、合計 0 でも `ValueError` にしない。
18. `test_arrival_recording_call_sites_match_the_world_contracts`。Candidate 局所前進は recorder を呼び、binding transfer と Level 2 の `_transfer_vehicle_reference` は呼ばない。これは source-level の確認である。値の一致は recorder の実行 test が受け持つ。Candidate と Level 2 の full 実動作 fixture は、今回追加していない。
19. `test_arrival_record_keeps_visit_identity_and_attempt_counters`。Visit ID、earliest arrival、`batch_assignment`、Link 進入回数、origin attempt、in-trip attempt は、到着記録では変わらない。

baseline collector の実動作は、この 19 件には含まない。World copy の test が、同じ event の値と台帳の独立性を見る。

### 18.14 既存current-visit arrival test 13件の更新

対象は `tests_order_control_current_visit_arrival.py` である。旧 mutable RNG を期待値にしていた 3 件を、keyed 契約へ更新した。test の削除は無い。総数は 13 件のままで、`TESTS` は 13 件すべてを呼ぶ。

`test_first_visit_records_matching_values` の旧期待は、`visit["arrival_tiebreaker"] == W_ref.rng.random()` だった。新しい期待は、fixture 上の対象 inlink 合計が 1 であること、明示 key `(veh.name, "merge", 1)`、domain `"arrival_tiebreaker"`、`W._common_seed_rng_internal_entropy`、`keyed_uniform_value()` である。current Visit の arrival time は `W.T * W.DELTAT`、tiebreaker は期待値、legacy の時刻と tiebreaker は current Visit と一致する。`W.rng` と `W.order_control_rng` は、同一 seed の `W_ref` と stream が一致することで、消費されていないことを確認する。`W_ref.rng.random()` は期待値に使わない。test 名は変えていない。

`test_first_visit_tiebreaker_uses_existing_rng_stream` は、名前が旧契約を表していたため、`test_first_visit_tiebreaker_uses_keyed_uniform_without_consuming_rng_streams` へ改名した。`TESTS` も新しい名前を参照する。確認内容は、訪問番号 1、明示 key `(veh.name, "merge", 1)`、keyed uniform、`W.rng` 非消費、`W.order_control_rng` 非消費である。`expected_tiebreaker = W_ref.rng.random()` は削除した。

`test_revisit_updates_current_visit_only` の旧期待は、`visit["arrival_tiebreaker"] == W_ref.order_control_rng.random()` だった。新しい確認は、再訪前に `link1` が 1、`link2` が 1、対象 Node の inlink 合計が 2 であること、明示 key `(veh.name, "merge", 2)`、current Visit の時刻が `W.T * W.DELTAT`、tiebreaker がその key の uniform、legacy の初回時刻と初回 tiebreaker が維持されること、両 mutable RNG が消費されないことである。test 名は変えていない。

残る既存 test は、ineligible、`none`、current Visit 欠落、Node 不一致、partial arrival、same Visit 再登録、revisit 再登録を、同一 seed の参照 World との RNG stream 比較として維持した。旧 mutable RNG を arrival の期待値にする assert は残していない。

### 18.15 既存13件の初回再実行失敗とfixture修正

専用 19 件は初回から成功した。表示は `Common seed/RNG arrival tiebreaker tests passed.` である。

既存 13 件の初回再実行は、`test_revisit_tiebreaker_reproducible_for_same_seed` で停止した。比較した 2 つの値は、actual が約 0.350942、desired が約 0.241633 だった。この小数は、失敗時に観測された差の記録であり、test へ固定した期待値ではない。

原因は production 欠陥ではない。World 1 の Vehicle 名が `veh_repro_1`、World 2 の Vehicle 名が `veh_repro_2` だった。arrival key には Vehicle 正式名が入る。異なる Vehicle 名なら異なる uniform になるのが契約である。この test は同じ event の再現性を見るのに、同じ event key を作っていなかった。World の random seed は同じだった。

修正は test fixture だけである。別 World の両 Vehicle 名を、同じ `veh_repro` にした。World 名は `arrival_repro_1` と `arrival_repro_2` のままである。World object も別である。random seed、network、test 名、`_run_first_visit_and_revisit` は変えていない。production は変えていない。Vehicle 名、Node 名、Node 訪問番号が同じなので、同じ arrival event key になり、同じ tiebreaker になる。

Terminal 独立確認では、2 台とも `veh_repro` であり、古い `veh_repro_1` と `veh_repro_2` は残っていなかった。`git diff --check` の出力は無かった。修正後の既存 13 件は成功し、表示は `Order-control current visit arrival tests passed.` である。

異なる Vehicle 名なら異なる値になる契約は、専用 test の `test_another_vehicle_name_is_a_different_arrival_key` が確認する。既存の再現性 test へ、その契約を重複追加していない。

### 18.16 交差回帰

利用者の Terminal 確認である。Cursor は再実行していない。

- `python tests_common_seed_rng_arrival_tiebreaker.py` の表示は `Common seed/RNG arrival tiebreaker tests passed.` である。
- fixture 修正後の `python tests_order_control_current_visit_arrival.py` の表示は `Order-control current visit arrival tests passed.` である。
- `python tests_common_seed_rng_keyed_uniform.py` の表示は `Common seed/RNG keyed uniform tests passed.` である。
- `python tests_vehicle_link_entry_state.py` の表示は `Vehicle link-entry state tests passed.` である。
- `python tests_common_seed_rng_route_choice.py` の表示は `Common seed/RNG route choice tests passed.` である。
- `py_compile` は成功した。

Candidate 局所前進の full suite、Level 2 の full suite、baseline collector の追加実行、N=1、4方式統合は、この単位の Terminal 確認には含めていない。反証は、受入れ前の追加実行を必須としなかった。

### 18.17 読取り専用反証レビュー

Cursor Grok 4.7、effort high で、実装後の読取り専用反証を行った。Cursor は編集、test、`py_compile`、simulation、Git を行っていない。判定の根拠はコードの制御フローであり、test 成功だけでは「問題なし」としていない。

総合判定は、このまま受入れ可能、である。blocking は無い。high は無い。

成立した主要事項は次である。

- Node 訪問番号は、対象 Node の全 inlink の累積進入回数の合計である。
- domain と key は **§18.5** と **§18.7** のとおりである。
- 初回と再訪は同じ domain と key 形で、訪問番号だけが違う。
- 同じ Visit の再登録は、訪問番号の計算前に return する。
- 保存順序は **§18.9** のとおりである。
- mutable RNG は到着生成で消費しない。通常 merge の `W.rng` は残っている。
- baseline copy は同じ event を共有できる。
- Candidate 局所前進は既存の recorder を呼び、進入回数はそこで増やさない。
- Level 2 は recorder を呼ばない。
- 専用 19 件は、期待 key を production helper から作っていない。再訪 test は Visit ID 9 と訪問番号 2 をずらしている。
- 更新済み既存 13 件に、旧 mutable RNG の期待値は残っていない。再現性 test の初回失敗は、Vehicle 名が key に入る契約と、fixture が名前を揃えていなかったことの組合せである。

low は次の 4 点である。受入れ前の production 修正と追加 test は不要と判断した。Terminal の追加回帰も必須無しと判断した。

1. Candidate 局所前進に、古い「one candidate RNG」というコメントが残っていた。処理は keyed だった。このコメントはその後 **§18.18** で直した。
2. production caller の無い `record_order_control_node_first_arrival` が、本 recorder と keyed 生成を重複して持つ。将来の整理候補である。
3. collector 例外のあと、保存済み Visit だけが残り、再呼出しでは collector を再通知しない。既存順序である。
4. legacy 台帳の有無と Node 訪問番号は別管理である。正式経路では揃う。重複検査は足していない。

Candidate と Level 2 の接続有無の一部は source-level である。専用 19 件は、その 2 経路の full 実動作 fixture を持たない。値の契約は recorder の実行 test が受ける。この範囲を、反証は blocking にしなかった。

### 18.18 Candidate局所前進の古いコメント修正

反証が指摘したコメントは、修正前に Terminal で実在を独立確認した。

対象は `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py` の、`_snapshot_local_advance_for_rollback()` 直前の 4 行である。

旧説明は、それより前の検査が Vehicle を動かさず arrival tiebreaker を draw しないこと、`record_order_control_node_arrival` が Visit、初回台帳、one candidate RNG を書くこと、だった。`one candidate RNG` は現在の実装と一致しない。

現在の実装は次である。

- それより前の検査は、Vehicle を動かさず、arrival tiebreaker を記録しない。
- recorder は current Visit へ書く。
- 初回なら legacy 台帳へも書く。
- 書く値は one keyed arrival value である。
- Candidate 固有の mutable RNG は消費しない。`W.rng` も `W.order_control_rng` も、この生成では消費しない。
- その後の失敗で局所 World の書込みを戻すため、呼出し前の snapshot は引き続き必要である。

修正はコメント 4 行だけである。production 処理、snapshot の位置、rollback、recorder の呼出し位置、Candidate の移動処理は変えていない。動作変更ではない。説明の修正である。

Terminal 独立確認では、変更はコメント 4 行だけであり、`one candidate RNG` は消え、keyed arrival value の説明になっていた。`git diff --check` の出力は無かった。コメントだけなので追加 test は不要である。

### 18.19 最終検証結果

最終確認は次である。

- Node 訪問番号 helper が、対象 Node の全 inlink を正式名で合計する。
- 合計 0 を 1 へ補正しない。invalid count を拒否する。
- domain が `arrival_tiebreaker` の 1 つであり、route choice の 2 domain と違う。
- key が Vehicle 正式名、Node 正式名、Node 訪問番号である。
- 初回と再訪が同じ helper と domain と key 形である。
- arrival 成立前に生成しない。同じ Visit で再生成しない。
- current Visit と legacy 初回台帳の役割を維持する。
- `W.rng` と `W.order_control_rng` を到着生成で使わない。
- baseline の same event を共有できる。
- Candidate 局所前進の既存 call を残し、binding と Level 2 へは接続しない。
- 専用 19 件が成功した。
- 更新済み既存 13 件が、fixture 修正後に成功した。
- 初回の 13 件失敗を、production 欠陥と fixture の Vehicle 名不一致に分けた。
- keyed uniform、Link 進入、route choice の交差回帰が成功した。
- `py_compile` が成功した。
- 反証で blocking と high が無かった。
- 古い Candidate コメントを、処理を変えずに直した。
- `git diff --check` の出力が無かった。

空白が正常と確認済みの次の文字列は、誤記として直していない。`entry count`、`node visit number is`、`Arrival tiebreaker is not recorded`、`arrival time for ``node.name`` is already stored` である。

### 18.20 受入れ判定

今回の実装単位を受入れ可能とする。

理由は次である。

- Node 訪問番号が正本どおり、対象 Node の全 inlink の累積進入回数の合計である。
- 0 を 1 へ補正しない。invalid count を拒否する。
- arrival domain が独立している。
- key が Vehicle 正式名、Node 正式名、Node 訪問番号である。
- 初回と再訪が同じ domain と key 形であり、Node 訪問番号が event を分ける。
- arrival 成立前に生成しない。同じ Visit で再生成しない。
- current Visit と legacy の役割を維持する。
- mutable RNG を消費しない。
- baseline で same event を共有できる。
- Candidate 局所前進の既存接続を維持する。
- Level 2 へ誤接続していない。
- 専用 19 件が成功した。
- 更新済み既存 13 件が成功した。
- fixture 不備と production 欠陥を分けた。
- 交差回帰が成功した。
- 反証で blocking と high が無かった。
- 古い Candidate コメントを修正した。
- test 成功だけを理由にしていない。

受入れ範囲は、Node 訪問番号 helper、arrival key helper、初回と再訪の keyed arrival tiebreaker、current Visit 保存、legacy 初回台帳、mutable RNG 非消費、Candidate の既存 arrival 記録への適用、である。

4方式共通 seed／RNG 改修全体の完了ではない。

### 18.21 今回未実装の範囲

次は未実装、または未完了である。

- 通常 merge 用 RNG の分離。
- `_transfer_normal_merge()` の乱数変更。
- Candidate selection RNG の変更。
- N=1 BATCH 対 FCFS の完全一致。
- 4方式統合回帰。
- 最終正本記録と全体受入れ。
- arrival hash の性能測定。
- Candidate 局所前進の full 実動作回帰。
- Level 2 の full 実動作回帰。
- baseline collector の、今回の単位での追加実行。
- production caller の無い legacy first-arrival helper の削除検討。
- collector 例外後の再通知設計。

新 BATCH は未実装・未採用である。旧 trial の tiebreaker 数値一致は、この単位の合格条件ではない。

### 18.22 実装完了までの現在地

完了した単位は次である。

1. 内部 entropy 保存と pure keyed uniform helper。詳細は **§15** である。
2. Vehicle の Link 進入状態と物理進入追跡。詳細は **§16** である。
3. origin・in-trip route choice の keyed 化。詳細は **§17** である。
4. arrival tiebreaker の keyed 化と、Node 訪問番号の production 利用。詳細は本 **§18** である。

残る単位は次である。

5. 通常 merge 用 RNG の分離。
6. N=1 BATCH 対 FCFS と、4方式統合回帰。
7. 最終正本記録と、全体受入れ。

今回の単位を完了すると、主要 production 接続で残るのは、通常 merge 用 RNG だけである。

### 18.23 次の直接作業

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で全文独立確認することである。

その後の予定は、必要なら文書を修正し、production 3 ファイル、test 2 ファイル、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。push はその確認後の別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、次の実装単位である通常 merge 用 RNG の分離へ進む。

production 3 ファイルは次である。

- `uxsim/uxsim.py`
- `uxsim/common_seed_rng_arrival_tiebreaker.py`
- `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`

test 2 ファイルは次である。

- `tests_common_seed_rng_arrival_tiebreaker.py`
- `tests_order_control_current_visit_arrival.py`

Markdown 3 ファイルは、本ファイル、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`、`ORDER_EXCHANGE_PROGRESS_4.md` である。

利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。`research_scripts/route_choice_rng_diagnostic.py` も、この記録の対象外である。

### 18.24 検索語

arrival tiebreaker keyed化、arrival_tiebreaker、ARRIVAL_TIEBREAKER_DOMAIN、Node訪問番号、node_visit_number_from_link_entries、arrival_tiebreaker_key_parts、Vehicle正式名、Node正式名、全inlink合計、累積進入回数、同一inlink再進入、別inlink再訪、parallel Link、missing 0、合計0、0を1へ補正しない、invalid count、bool拒否、float拒否、str拒否、pure keyed uniform、common seed RNG、current Visit、legacy first-arrival、初回台帳、再訪非上書き、同じVisit再生成なし、arrival成立前未生成、W.rng非消費、W.order_control_rng非消費、初回と再訪、明示key、World copy、baseline fork、baseline collector、Candidate局所前進、Candidate binding非接続、Level 2非接続、専用test 19件、既存test 13件、fixture不備、veh_repro_1、veh_repro_2、veh_repro、異なるVehicle名、same event key、blockingなし、highなし、one candidate RNG、keyed arrival value、Candidateコメント修正、Common seed/RNG arrival tiebreaker tests passed、Order-control current visit arrival tests passed、keyed uniform回帰、Vehicle Link進入状態回帰、route choice回帰、normal merge RNG未実装、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、58521aa、到着順の乱数、同着順位をどう決めるか、同じNodeへの何回目の訪問か、Node訪問回数の数え方、同じinlinkへ再進入した場合、別inlinkから同じNodeへ戻る場合、到着時にW.rngを消費するか、初回到着と再訪で別の乱数か、current Visitと初回台帳の違い、同じVisitでtiebreakerを作り直すか、Candidateでarrival tiebreakerを作るか、Level 2でarrival tiebreakerを作るか、baseline copyで同じtiebreakerになるか、Vehicle名が違うと別の値になるか、same seedなのに結果が違った、fixtureのVehicle名が違った、candidate RNGという古いコメント、arrival実装後の次作業、実装完了までの残り区分

## 19. 通常merge用RNG分離の実装・反証・受入れ（2026-11-23）

### 19.1 記録の位置づけ

執筆日は2026-11-23である。本節は、通常 merge 用の逐次 RNG を共有の `W.rng` から分離した実装、専用 test、交差回帰、読取り専用反証、Terminal 独立確認、最終受入れを記録する詳細正本である。

関係は次である。

- **§14** は、4方式共通 seed／RNG 改修の具体実装前設計の正本である。本節は **§14.4** と **§14.12** から **§14.16** の通常 merge 契約を実装した結果であり、**§14** の本文は削除も書換えもしない。
- **§15** は、内部 entropy 保存と pure keyed uniform helper の実装・反証・受入れ結果の正本である。
- **§16** は、Vehicle 状態と Link 物理進入追跡の実装・反証・受入れ結果の正本である。
- **§17** は、origin・in-trip route choice keyed 化の実装・反証・受入れ結果の正本である。
- **§18** は、arrival tiebreaker keyed 化と Node 訪問番号利用の実装・反証・受入れ結果の正本である。
- 本 **§19** は、通常 merge 用 RNG 分離の実装・反証・受入れ結果の正本である。
- 研究契約の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** である。実装前の具体設計確定は **§32.24** である。これまでの各実装単位の結果は **§32.25** から **§32.28** である。本単位の全体設計上の実装結果は **§32.29** である。
- 進捗の対応節は `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.30** である。**§21.9.29** は前の実装単位の進捗として残す。

最新の詳細参照先は本 **§19** である。**§14** から **§18**、**§32.21**、**§32.24** から **§32.28**、**§21.9.29** は残す。今回の単位により、4方式共通 seed／RNG 改修の主要 production 接続は揃った。ただし、改修全体の受入れ完了ではない。N=1 BATCH 対 FCFS 回帰と 4方式統合回帰は未実行である。最終正本記録と全体受入れも未完了である。新 BATCH は未実装・未採用である。

test 成功だけを受入れ理由にはしない。Cursor の報告を無条件には正本化していない。反証は読取りであり、Terminal の `py_compile`、test、`git diff --check` は利用者の独立確認である。Cursor は Git 操作を行っていない。

### 19.2 今回の実装範囲

今回の production 接続は、通常 merge の乱数源だけである。origin route choice、in-trip route choice、route choice の domain と attempt、arrival tiebreaker、Node 訪問番号、arrival 保存、Link 進入 helper、Candidate selection RNG、Candidate binding、Candidate 局所前進、Level 2、FCFS transfer、BATCH transfer、確定順位の TVT-MP transfer、signal 制御、signal phase、BATCH 形成、BATCH service queue、baseline 順位処理は変えていない。

置き換えたのは、`_transfer_normal_merge()` の非 hard deterministic 分岐にある `W.rng.shuffle(outlinks)` と `W.rng.choice(...)` である。どちらも `W.normal_merge_rng` を使う。交通上の候補形成、判定順、通過処理は変えていない。これは抽選契約の再設計ではなく、乱数の出どころの分離である。

新規 module は作っていない。Generator 本体を World 属性として明示し、初期化は数行だけにし、状態を別 module へ隠さず、過度な抽象化を避け、`World.copy()` による state 継承をそのまま使うためである。

### 19.3 変更したproductionとtest

production:

- `uxsim/uxsim.py`

test:

- 新規 `tests_common_seed_rng_normal_merge.py`。18 件である。

変更していないもの:

- `uxsim/common_seed_rng_keyed_uniform.py`
- `uxsim/common_seed_rng_route_choice.py`
- `uxsim/common_seed_rng_arrival_tiebreaker.py`
- `uxsim/__init__.py`
- 既存の route choice、arrival、Link 進入、current-visit arrival の test
- `research_scripts/`。特に `research_scripts/route_choice_rng_diagnostic.py` には触れていない。
- `diagnostics/`
- output、CSV、JSON、ZIP

### 19.4 現行通常merge制御フロー

`_transfer_normal_merge()` は、signalized UXsim だけの関数ではない。`Node.transfer()` の順は次である。

1. `order_control_eligible` かつ `order_control_type == "fcfs"` なら `transfer_fcfs_clearance()` して return する。
2. `order_control_eligible` かつ `order_control_type == "batch"` なら `transfer_batch()` して return する。
3. `order_control_eligible is True` かつ `order_control_type == "time_value"` なら `transfer_tvt_mp_passage_attempts()` のあと `_finish_node_transfer()` して return する。
4. それ以外が `_transfer_normal_merge()` のあと `_finish_node_transfer()` である。

したがって、`order_control_type="none"` の eligible Node も通常 merge へ進む。信号の有無では分岐しない。signalized UXsim の通常 Node も、信号のない通常 Node も、同じ関数を使う。

関数内部の順は、今回も次のままである。

- `allowed_vehicles` が `None` なら、現在の `incoming_vehicles` が候補源である。tuple なら、その固定集合に限る。
- `route_next_link` が `None` の車両は outlink 候補に入れない。
- 同じ outlink は 1 回だけ登録する。出現順は incoming の走査順である。
- そのあと、各 outlink を `number_of_lanes` の回数だけリストへ複製する。
- 非 hard deterministic なら、その複製後のリストを 1 回 shuffle する。
- 各 outlink について、downstream space、outlink inflow capacity、Node flow capacity をこの順で見る。どれかが足りなければ、その outlink では choice しない。
- 中に入ったあと、inlink の物理先頭、`route_next_link` がその outlink、signal、inlink outflow capacity を満たす車両だけを `vehs` にする。0 件なら `continue` する。
- `merge_priority` の合計が 0 なら均等重みにする。非 hard deterministic なら `choice` を 1 回呼ぶ。hard deterministic なら最大 priority を選ぶ。
- `enforce_order_control_clearance` が True のとき、clearance 判定は choice のあとである。未充足なら return し、残りの集合は後の timestep に残す。RNG state は巻き戻さない。
- 通過するときは `_transfer_one_vehicle_between_links()` である。この helper は `incoming_vehicles` を消さない。cleanup は `Node.transfer()` の `_finish_node_transfer()` である。

同一 timestep で複数 outlink、または同じ outlink の複数 lane を処理するとき、先に動かした車両が後の候補集合を変え得る。この相互影響は維持している。単一車線の同じ outlink は、1 timestep に 1 回処理される。

### 19.5 normal merge専用RNG

World 属性は `normal_merge_rng` である。型は NumPy `Generator` である。

性質:

- 通常 merge 専用である。
- 逐次状態を持つ。
- pure keyed uniform ではない。
- merge event key を作らない。
- timestep や Node 名で再 seed しない。
- merge ごとに Generator を作り直さない。
- World 初期化時に 1 回だけ作る。

使用箇所は次の 2 つだけである。

- `_transfer_normal_merge()` の非 hard deterministic 時の `shuffle`
- 同関数の非 hard deterministic 時の `choice`

使用しない箇所:

- route choice
- arrival tiebreaker
- Candidate selection
- FCFS
- BATCH
- 確定順位の TVT
- signal 制御
- Candidate binding
- Candidate 局所前進
- Level 2 参照移動

初期化の局所変数名は `ordinary_merge_seed_sequence` である。World 属性名は `normal_merge_rng` である。用語は揃っていない。これは low の読みやすさの留保であり、使用箇所は属性名で追跡できる。今回は名称を変えていない。

### 19.6 seed派生とstream分離

`World.__init__` では、既存の順を維持したうえで、保存済み entropy の直後に通常 merge 用 Generator を作る。

1. `W.rng = np.random.default_rng(seed=random_seed)`。これは spawn key なしである。
2. `order_control_seed_sequence = np.random.SeedSequence(random_seed)`。
3. `order_control_child_seed_sequence = order_control_seed_sequence.spawn(1)[0]`。
4. `W.order_control_rng = np.random.default_rng(order_control_child_seed_sequence)`。既存の `spawn(1)[0]` は変えていない。
5. `W._common_seed_rng_internal_entropy` を、その `order_control_seed_sequence.entropy` の正規化結果として保存する。
6. `ordinary_merge_seed_sequence = np.random.SeedSequence(W._common_seed_rng_internal_entropy, spawn_key=(1,))`。
7. `W.normal_merge_rng = np.random.default_rng(ordinary_merge_seed_sequence)`。

使っていないもの:

- 用途ごとの `SeedSequence(None)`。`random_seed=None` の OS entropy は、既存の order-control 用 `SeedSequence` を作ったときに 1 回だけ取り、それを保存して派生する。
- Python 組込み `hash()`。
- World 名。
- object identity。
- `W.rng` の現在 state。
- route choice の domain `origin_route_choice` と `in_trip_route_choice`。
- arrival の domain `arrival_tiebreaker`。
- keyed uniform。
- merge ごとの再 seed。

NumPy 2.3.5 では、明示整数 seed の `SeedSequence.entropy` はその整数である。正規化はそれを 1 要素 tuple にする。したがって `normal_merge_rng` は、その tuple と `spawn_key=(1,)` から作られる。`W.order_control_rng` は同じ親 entropy の child 0、つまり `spawn_key=(0,)` に相当する既存系列である。`W.rng` は spawn key なしである。現行 3 本は別 object であり、別の初期系列である。

同じ明示 seed なら、World 名が違っても `normal_merge_rng` の初期 state は同じである。異なる seed なら、代表的な複数 draw が異なる。`random_seed=None` で独立に作った別 World 同士の一致は要求しない。同一 World とその copy の一致は要求する。

留保: **§14** は、保存済み entropy から用途を分けた別 stream を要求した。`spawn_key=(1,)` という番号自体は事前に固定していなかった。現在の 3 本はこの番号で衝突しない。将来、同じ entropy と同じ spawn key を別用途で再利用してはならない。これは low であり、今回の受入れを妨げない。

### 19.7 初期化位置と再初期化しない契約

- `_common_seed_rng_internal_entropy` を設定した直後に初期化する。
- World 初期化で 1 回だけ作る。代入箇所は `World.__init__` のこの 1 箇所である。
- `finalize_scenario()` では作り直さない。
- `exec_simulation()` では作り直さない。
- `World.copy()` の復元では `World.__init__()` を再実行しない。
- 公開の `W.random_seed` を生成後に書き換えても、この Generator は読み直さない。
- baseline 開始 timestep を seed へ入れない。
- `set_order_control_for_randomly_selected_eligible_nodes(..., random_seed=...)` は、そのメソッドのノード選択引数であり、World の通常 merge RNG の再 seed ではない。

### 19.8 _transfer_normal_mergeの変更

変更前:

- `W.rng.shuffle(outlinks)`
- `W.rng.choice(vehs, p=merge_priorities/sum(merge_priorities))`

変更後:

- `W.normal_merge_rng.shuffle(outlinks)`
- `W.normal_merge_rng.choice(vehs, p=merge_priorities/sum(merge_priorities))`

引数、位置、条件は同じである。乱数源以外の交通処理は変更していない。

維持したもの:

- 候補形成
- outlink の重複除去
- lane 数に応じた outlink 複製
- shuffle の位置
- downstream space 判定
- inflow capacity
- Node flow capacity
- inlink 先頭 Vehicle
- `route_next_link`
- signal
- inlink outflow capacity
- merge priority
- 合計 0 の均等重み
- choice の位置
- clearance 判定
- transfer 処理
- cleanup
- return と continue
- 同一 timestep 内の反復

docstring は、非 hard deterministic では `W.normal_merge_rng` を使い、それが逐次であり keyed uniform ではなく、hard deterministic では消費しない、と追記した。反証の low として、この文は choice が通過可能車両 1 件以上のときだけである点を簡略化している。コードの分岐は、0 件なら `continue` で choice しない。

### 19.9 RNG消費条件

非 hard deterministic では、変更前と同じ条件で専用 RNG を消費する。消費回数の整理や削減はしていない。

- outlink リストを作ったあと、0 件でも 1 件でも 2 件以上でも `shuffle` を 1 回呼ぶ。
- lane 数分の複製のあとに shuffle する。
- downstream space、inflow capacity、Node flow のいずれかが不足なら、その outlink では choice しない。
- signal、先頭車両、`route_next_link`、inlink outflow で通過可能車両が 0 件なら choice しない。
- 通過可能車両が 1 件でも choice する。1 件だから draw を省略する最適化は入れていない。
- 通過可能車両が 2 件以上でも、その outlink の choice は 1 回である。
- priority 合計が 0 なら `np.ones` の均等重みである。例外型は変えていない。
- clearance 判定は choice のあとである。未充足でも choice は消費済みである。
- failure 時に state を巻き戻さない。
- 複数 outlink、または複数 lane では、条件を満たす各回に choice する。先の移動が後の候補を変え得る。

hard deterministic:

- shuffle しない。
- choice しない。
- `normal_merge_rng` は不変である。
- `W.rng` は不変である。
- `W.order_control_rng` は不変である。
- 最大 `merge_priority` を選ぶ。
- 同点時は、既存の `max(zip(merge_priorities, vehs), key=lambda x: x[0])` であり、先に出た最大を維持する。
- lane 複製、候補形成、capacity、signal、clearance の処理は従来どおりである。

専用 test が実関数で確認した範囲と、コード上維持しているが専用 fixture が無い範囲は **§19.15** と **§19.17** で分ける。2 車線で choice が 2 回、downstream space 不足だけ、clearance 未充足、hard deterministic の同点は、専用 fixture が無い。制御フローは未変更である。

### 19.10 hard deterministic

`hard_deterministic_mode=True` の分岐は、shuffle も choice も入らない。選ぶ式は変更前と同じ `max` である。専用 test `test_hard_deterministic_merge_does_not_draw` は、priority 1 と 3 の 2 台で実関数を呼び、高い側が outlink へ移り、低い側が inlink に残り、3 本の Generator state が不変であることを見ている。同点の専用 test は無い。同点規則の式は変えていない。

### 19.11 World copyとbaseline

`World.copy()` は `pickle.loads(pickle.dumps(W))` である。`normal_merge_rng` は World 属性なので、その時点の Generator state が別 object として写る。追加の copy 処理は入れていない。

確認した契約:

- copy は現在 state を引き継ぐ。
- copy と original は別 Generator object である。
- copy 直後は同じ次 draw を出せる。
- 一方だけ進めても、他方は進まない。
- copy 前に一部消費済みでも、その現在地から継承する。
- 実 merge のあとの copy も、その時点の state を共有し、copy 側の追加 draw は original へ戻らない。

baseline fork は、baseline driver が real World を 1 回 serialize し、bytes から `pickle.loads` する。`World.__init__` は再実行されない。開始時に初期 seed へ戻さない。開始 timestep を seed へ入れない。baseline 専用の merge RNG は新設していない。fork 内の消費は別 object なので、real World へ戻らない。same state かつ same merge 順なら same result である。merge event の順が違えば逐次 state が分かれる。これは設計どおりであり、route choice や arrival のような event key による呼出し順独立性ではない。

baseline full simulation で通常 merge の交通結果を今回は実行していない。機構は copy test と同じである。実行結果の確認は統合回帰時である。

### 19.12 方式別分岐

FCFS、BATCH、確定順位の TVT は、`Node.transfer()` の早期 return、または確定順位の通過処理であり、`_transfer_normal_merge()` に入らない。したがって `normal_merge_rng` を消費しない。

generic baseline fork は別である。`transfer_tvt_mp_passage_attempts()` は、`_order_control_baseline_collector` があり、`apply_copied_tvt_confirmed_ranks is False` のときだけ、引数なしで `node._transfer_normal_merge()` を呼んで return する。**§14.12** のとおり、この test-only の generic normal merge は同じ `normal_merge_rng` を使う。production の TVT-MP baseline は `apply_copied_tvt_confirmed_ranks=True` であり、確定順位側である。過去確定順位を適用しない baseline が production にある、とは書かない。

専用 test の time_value fixture は collector を付けず、incoming も空である。台帳を読む前に return する経路であり、generic fork は通っていない。test 名 `test_fcfs_and_time_value_transfer_do_not_use_normal_merge_rng` は、その fixture の確認範囲より少し広い。これは low であり、機能上の穴ではない。generic fork が通常 merge RNG を使うことは、コードと **§14.12** で意図どおりである。

`allowed_vehicles` と `enforce_order_control_clearance=True` を渡す production caller は、今回確認した範囲には無い。定義は残している。使われた場合も、非 hard deterministic の shuffle と choice は同じ `normal_merge_rng` である。clearance は choice のあとである。helper 名も RNG 名も変える必要はない。N=1 の FCFS と BATCH は、この helper に入らない。この分離が、両者の比較構造そのものを変える経路ではない。

### 19.13 CandidateとLevel 2

Candidate:

- 局所前進 `advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals` は、位置更新と到着記録までであり、`_transfer_normal_merge()` も `Node.transfer()` も呼ばない。
- Candidate binding は自前の通過判定と移動であり、通常 merge を呼ばない。
- 局所 World は real World の pickle なので、`normal_merge_rng` 属性も copy される。未使用である。
- 局所の state を real World へ戻さない。
- Candidate selection RNG とは別であり、混同していない。今回の単位は Candidate selection の seed を変えていない。

Level 2:

- `_build_mimic_world` は `mimic_random_seed` で別 World を作る。`World.__init__` が走るので `normal_merge_rng` 属性自体はある。
- mimic World は `hard_deterministic_mode=True` のままである。
- 物理移動は `_transfer_vehicle_reference()` であり、`Node.transfer()` も `_transfer_normal_merge()` も呼ばない。
- したがって mimic 上の `normal_merge_rng` は未使用である。
- Level 2 固有の `mimic_random_seed` は変えていない。
- この非接続を、将来の全 World 型 BATCH の省略規則として一般化しない。将来方式は正式 World 全体を copy して続ける設計である。

### 19.14 mutable RNG境界

`W.rng`:

- 通常 merge には使わない。
- route search の travel time noise、Vehicle 色、auto rename など、今回の対象外の既存用途は残る。

`W.order_control_rng`:

- 通常 merge には使わない。
- 既存の `spawn(1)[0]` の作り方も変えていない。

`W.normal_merge_rng`:

- 通常 merge の shuffle と choice だけである。
- 逐次である。
- keyed ではない。

pure keyed uniform:

- route choice と arrival tiebreaker に使う。
- 通常 merge には使わない。

通常 merge を実行しても、route choice と arrival の keyed 値は mutable state を持たないので、その生成状態は影響を受けない。逆に、route choice と arrival を実行しても `normal_merge_rng` は進まない。

通常 merge event 自身の呼出し順が変われば、同じ World の中で割り当たる draw は変わり得る。これは逐次 RNG の設計どおりである。route choice や arrival の呼出し順では、この Generator は進まない。

### 19.15 専用test 18件

新規ファイルは `tests_common_seed_rng_normal_merge.py` である。18 件すべてを `TESTS` から実行する。期待 Generator は、test 側が整数 seed と `spawn_key=(1,)` から自分で作る。production の seed helper には渡さない。固定 float は書いていない。Generator state と実 draw の両方を見る。実 `Node.transfer()` または `_transfer_normal_merge()` を含み、実際に移動した Vehicle を確認する test がある。

各 test の保証は次である。

1. `test_world_has_separate_normal_merge_generator`。属性がある。NumPy `Generator` である。`W.rng` とも `W.order_control_rng` とも別 object であり、初期 state も別である。test 内で組んだ初期 state と一致する。
2. `test_same_seed_same_normal_merge_series_for_different_world_names`。同じ明示 seed、違う World 名で、初期 state と 4 draw が一致する。
3. `test_different_seeds_have_different_normal_merge_series`。seed 21 と 22 で state が違い、4 draw のうち複数位置が違う。1 draw の偶然一致には依存しない。
4. `test_the_three_generators_do_not_advance_each_other`。3 本のうち 1 本を進めても、残り 2 本は進まない。
5. `test_copy_keeps_current_normal_merge_state_on_a_different_generator`。一部消費後の copy は次 draw が同じで、object は別である。original だけ進めても copy は残る。copy だけ進めても original は残る。
6. `test_copy_after_merge_matches_then_one_side_can_diverge`。実 `Node.transfer()` のあと copy し、state は一致し、copy 側の追加 draw は original へ戻らない。
7. `test_normal_merge_follows_the_dedicated_series`。実 `Node.transfer()` で選ばれた車両が、専用系列の shuffle と priority 付き choice と一致する。`W.rng` と `W.order_control_rng` は不変である。
8. `test_multiple_outlinks_are_shuffled_by_the_dedicated_generator`。2 outlink を長さ 2 のリストとして shuffle する。容量 0 の側は choice せず、開いている側の 1 台だけが専用系列の choice と一致する。shuffle の順列が、両方通過可能なときに選択を変える fixture ではない。
9. `test_choice_uses_merge_priority_on_the_dedicated_generator`。priority 1 と 4 が重みになり、高い側の重みが大きい。専用 RNG は進み、`W.rng` は進まない。この 1 件は `W.order_control_rng` を個別には見ていない。他の実合流 test が 3 本を見ている。
10. `test_zero_merge_priority_sum_uses_equal_weights`。priority 合計 0 は均等重み `np.ones(2) / 2` の choice と一致する。
11. `test_hard_deterministic_merge_does_not_draw`。実関数で高 priority が通り、3 本とも不変である。同点の専用 test は無い。
12. `test_no_outlink_only_shuffles_an_empty_list`。`route_next_link` が `None` のときは空リストの shuffle だけで、新しい choice は無く、車両は動かない。
13. `test_one_candidate_still_shuffles_and_chooses`。候補 1 件でも shuffle と choice を省略しない。
14. `test_merge_order_changes_the_later_draw`。同じ seed で通常 merge の呼出し順を入れ替えると、最終 state が違う。各順の選択は、その位置の独立 replay と一致する。`W.rng` と `W.order_control_rng` は両 World で一致する。
15. `test_route_choice_and_arrival_do_not_advance_normal_merge_rng`。2 本の outlink で in-trip route choice を実行し、訪問番号 1 の arrival tiebreaker を生成しても、3 本とも不変である。
16. `test_fcfs_and_time_value_transfer_do_not_use_normal_merge_rng`。空 incoming の FCFS `transfer()` と、collector なしの空 time_value `transfer()` では専用 RNG が進まない。generic baseline fork と BATCH の実呼出しは、この test の対象ではない。
17. `test_signal_block_does_not_choose`。signal 長が 2 で、位相が signal group に入らないとき、shuffle は行い、choice はせず、車両は動かない。
18. `test_capacity_block_does_not_choose`。outlink inflow が 0 のとき、shuffle は行い、choice はせず、車両は動かない。downstream space だけの専用 fixture ではない。

test 上の low であり、受入れ前の追加 test は不要としたもの:

- time_value test は generic baseline fork を通らない。
- BATCH 非消費の専用実動作 test は無い。早期 return はコードで確認した。
- 2 車線で choice が 2 回になる fixture は無い。
- downstream space だけの専用 fixture は無い。
- clearance 未充足の専用 fixture は無い。現行 caller はこの引数を渡さない。
- hard deterministic の同点専用 test は無い。式は未変更である。
- 一部の test は 3 stream の全部をその 1 件では見ていない。他 test が横断して確認している。

### 19.16 交差回帰

次は利用者の Terminal 独立確認である。Cursor は再実行していない。

- `python -m py_compile uxsim/uxsim.py tests_common_seed_rng_normal_merge.py` は成功した。
- `python tests_common_seed_rng_normal_merge.py` は `Common seed/RNG normal merge tests passed.` である。
- `python tests_common_seed_rng_keyed_uniform.py` は `Common seed/RNG keyed uniform tests passed.` である。
- `python tests_vehicle_link_entry_state.py` は `Vehicle link-entry state tests passed.` である。
- `python tests_common_seed_rng_route_choice.py` は `Common seed/RNG route choice tests passed.` である。
- `python tests_common_seed_rng_arrival_tiebreaker.py` は `Common seed/RNG arrival tiebreaker tests passed.` である。
- `python tests_order_control_current_visit_arrival.py` は `Order-control current visit arrival tests passed.` である。
- `git diff --check` の出力は無かった。

Link 進入 test の通常 merge 呼出しは `hard_deterministic_mode=True` の World であり、今回の専用 RNG を消費しない経路である。その成功は、hard deterministic の物理移動が残っていることの交差確認である。非 hard deterministic の選択結果は、専用 18 件が見ている。

### 19.17 読取り専用反証レビュー

Cursor Grok 4.7、effort high で読取り専用反証を行った。Cursor は編集、test、`py_compile`、simulation、Git を行っていない。

総合判定は、このまま受入れ可能、である。blocking は無い。high は無い。受入れ前の修正は無い。受入れ前の追加回帰は無い。

成立した主要事項:

- seed 派生。保存済み entropy と `spawn_key=(1,)`。`SeedSequence(None)`、`hash()`、World 名、object identity、`W.rng` の state からは作らない。
- stream 分離。現行 3 本は別 object、別初期系列である。既存 `spawn(1)` の系列は変えていない。
- 初期化位置。entropy 保存の直後、World 初期化の 1 回だけである。finalize、simulation、copy 復元では作り直さない。
- shuffle と choice だけの置換。候補形成から cleanup までの交通処理順は未変更である。
- RNG 消費条件の維持。0 件でも shuffle し、1 件でも choice し、clearance は choice のあとで、失敗時に巻き戻さない。
- hard deterministic の非消費と、最大 priority の維持。
- copy と baseline。pickle で現在 state を別 object として継承し、初期 seed へ戻さない。
- 方式別分岐。FCFS、BATCH、確定順位 TVT は非接続である。generic fork の False だけが同じ helper を呼ぶ。
- Candidate と Level 2 の非接続。copy や mimic 初期化で属性が存在しても未使用であり、real World へ戻さない。
- mutable RNG 境界。route choice と arrival は keyed のままである。
- 専用 18 件の独立性。期待系列は test 内の seed と spawn key から作り、実移動と state を見ている。

low であり、受入れを止めないもの:

1. time_value test 名が、確認した fixture の範囲より広い。generic fork は通っていない。
2. BATCH 非消費の専用実動作 test が無い。
3. 2 車線の 2 回目の choice、downstream space 不足、clearance 未充足の専用 fixture が無い。
4. `spawn_key=(1,)` という番号は **§14** で事前固定されていない。現在の stream とは衝突しない。将来の再利用は禁止である。
5. `ordinary_merge_seed_sequence` と `normal_merge_rng` の用語差。
6. docstring は、choice が候補 1 件以上のときだけである点を簡略化している。

### 19.18 最終検証結果

実装の読取り、専用 18 件、交差回帰、読取り専用反証、利用者の Terminal 確認は一致している。

- production の使用箇所は、初期化、shuffle、choice だけである。
- 通常 merge から `W.rng` と `W.order_control_rng` と keyed uniform は消えている。
- hard deterministic は 3 本を消費しない。
- route choice と arrival tiebreaker の production は未変更である。
- Candidate selection は未変更である。
- copy は現在 state を別 object で継承する。
- Markdown、research script、diagnostics、output は、この実装単位では変更していない。この節を書く文書化は、その後の別作業である。

`git diff --check` の出力が無かったことは、利用者の Terminal 確認である。Cursor はその Git 操作を行っていない。

### 19.19 受入れ判定

今回の実装単位を受入れ可能とする。

理由は次である。

- 専用 RNG が `W.rng` とも `W.order_control_rng` とも別 stream である。
- 保存済み entropy から確定的に派生する。
- 逐次 RNG として実装し、keyed uniform にしていない。
- 通常 merge の shuffle と choice だけに接続している。
- 交通処理の順序を変更していない。
- 既存の消費条件を維持している。候補 0 件でも shuffle し、候補 1 件でも choice する。
- hard deterministic を維持している。
- copy と baseline で現在 state を継承する。
- FCFS、BATCH、確定順位 TVT、Candidate、Level 2 へ誤接続していない。
- route choice と arrival から分離している。
- 専用 18 件が成功した。
- 交差回帰が成功した。
- 反証で blocking と high が無かった。
- test 成功だけを理由にしていない。

受入れ範囲は、`normal_merge_rng`、その seed 派生、World copy による state 継承、通常 merge の shuffle と choice、3 本の stream 分離、hard deterministic の非消費、である。

意図した非互換:

- 通常 merge の shuffle 順。
- merge で選ばれる具体 Vehicle または inlink。
- その後の `W.rng` の state。
- そこから波及する交通結果。

維持する契約:

- 候補形成。
- shuffle の位置。
- merge priority。
- choice の確率。
- signal。
- inlink 先頭。
- `route_next_link`。
- capacity。
- downstream space。
- clearance。
- transfer。
- hard deterministic。
- trip end。
- order-control type。

旧 trial との具体的な通常 merge 結果の一致は要求しない。

### 19.20 主要production接続の完成状況

主要 production 接続として完了したものは次である。

1. 内部 entropy 保存と pure keyed uniform。詳細は **§15** である。
2. Vehicle の Link 進入状態。詳細は **§16** である。
3. origin・in-trip route choice の keyed 化。詳細は **§17** である。
4. arrival tiebreaker の keyed 化と Node 訪問番号。詳細は **§18** である。
5. 通常 merge 用 RNG の分離。詳細は本 **§19** である。

これにより、4方式共通 seed／RNG 改修で予定した主要 production 接続は揃った。

未完了のものは次である。

- N=1 BATCH 対 FCFS。
- 4方式統合回帰。
- 最終正本記録。
- 全体受入れ。

実装接続の完了と、研究上の全体受入れの完了は混同しない。N=1 回帰済みとも、4方式統合回帰済みとも書かない。

### 19.21 今回未実装の範囲

次は未実行、または未実装である。

- N=1 BATCH 対 FCFS の完全一致。
- 4方式統合回帰。
- signalized UXsim を含む交通結果の確認。通常 merge の具体的な選択が旧 `W.rng` と違うのは、意図した非互換である。
- baseline fork 上で通常 merge を実際に走らせた交通結果。機構は pickle copy である。
- Candidate selection RNG の変更。
- 新 BATCH。未実装・未採用のままである。
- 最終正本記録。
- 全体受入れ。
- 性能測定。merge ごとの Generator 作成はしていない。初期化 1 回の `SeedSequence` の計測はしていない。

### 19.22 実装完了までの現在地

完了した単位は次である。

1. 内部 entropy と pure keyed uniform。
2. Link 進入状態。
3. route choice。
4. arrival tiebreaker。
5. normal merge RNG。

残る単位は次である。

6. N=1 BATCH 対 FCFS と、4方式統合回帰。
7. 最終正本記録と、全体受入れ。

### 19.23 次の直接作業

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で全文独立確認することである。

その後の予定は、必要なら文書を修正し、次のファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。

- `uxsim/uxsim.py`
- `tests_common_seed_rng_normal_merge.py`
- 本ファイル
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
- `ORDER_EXCHANGE_PROGRESS_4.md`

push はその確認後の別指示である。push 後に status、最新 commit、local と remote の一致を確認する。その後に、N=1 BATCH 対 FCFS と 4方式統合回帰の具体的な実行計画へ進む。

利用者への指示は、その時点で次に実行する内容だけを提示する。Git 操作は利用者が Terminal で行う。Cursor には行わせない。作業ツリーの無関係な既存変更と未追跡ファイルには触れない。`research_scripts/route_choice_rng_diagnostic.py` も、この記録の対象外である。

### 19.24 検索語

normal merge RNG、normal_merge_rng、通常merge用RNG、通常合流乱数、逐次RNG、sequential RNG、spawn_key=(1,)、ordinary_merge_seed_sequence、保存済みentropy、stream分離、W.rng分離、W.order_control_rng分離、shuffle、choice、merge priority、合計0、均等重み、候補0件、候補1件、複数候補、hard deterministic、World copy、baseline fork、generic baseline fork、apply_copied_tvt_confirmed_ranks、allowed_vehicles、order-control clearance、clearance未充足、Candidate非接続、Level 2非接続、専用test 18件、Common seed/RNG normal merge tests passed、keyed uniform回帰、Vehicle Link進入状態回帰、route choice回帰、arrival tiebreaker回帰、current-visit arrival回帰、blockingなし、highなし、主要production接続完了、N=1未実行、4方式統合回帰未実行、feature/common-seed-rng-foundation、a730e08、通常合流はどの乱数を使うか、合流乱数を分離した理由、W.rngを通常mergeで使うか、shuffleは何の乱数か、choiceは何の乱数か、候補1台でも乱数を使うか、候補0台でもshuffleするか、hard deterministicで乱数を使うか、merge priorityが0ならどうするか、signalで通れないとき乱数を使うか、capacity不足でchoiceするか、clearance未充足でも乱数を使うか、World copyで合流乱数はどうなるか、baselineで合流乱数を引き継ぐか、Candidateで通常mergeを使うか、Level 2で通常mergeを使うか、FCFSとBATCHでnormal merge RNGを使うか、time_valueのgeneric fork、merge eventの順序依存、共通seed実装の残り、主要production接続が揃ったか、統合回帰前の状態

## 20. 共通seed／RNG改修後N=1統合回帰の実測完了と「4方式統合回帰」の工程訂正（2026-11-23）

執筆日は2026-11-23である。本節は、共通 seed／RNG 改修後に実施した N=1 BATCH 対 FCFS 診断の実測結果を記録し、「4方式統合回帰」という表現が、合否基準付きの正式工程として確定していたと誤読され得ないよう、工程判断を訂正する最新正本である。

関係:

- **§14** は、4方式共通 seed／RNG 改修の具体実装前設計の正本である。**§14.18** は、N=1 BATCH 対 FCFS 回帰契約の正本である。試験条件、比較 field、合否基準は、そこと tracked の `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py` に拘束される。
- **§15** から **§19** は、各実装単位の実装・反証・受入れ結果の正本である。本文は削除も書換えもしない。
- **§19.22**、**§19.23**、**§32.29**、**§21.9.30** に書かれた「残る単位に 4方式統合回帰がある」「その後 4方式統合回帰の実行計画へ進む」という文言は、当時の計画表記である。最新の工程判断は本 **§20** を優先する。
- 研究契約の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` **§32.21** である。全体設計上の追記は **§32.30** である。進捗の対応節は `ORDER_EXCHANGE_PROGRESS_4.md` **§21.9.31** である。

Cursor は、本記録のために test、simulation、diagnostic script、Git、追加調査を行っていない。記載する N=1 結果は、利用者が Terminal で実行し提示した事実だけである。test 成功や diagnostic 成功だけを、production 全体の正しさや 4方式交通結果一致の証拠としては扱わない。

### 20.1 「4方式統合回帰」の工程訂正

責任関係は次である。利用者は「4方式統合回帰」を独立した正式工程として提案も承認もしていない。Copilot が **§15** の実装結果を文書化した際、試験条件・比較項目・合否基準・一括 script などの具体設計も利用者確認もないまま、未実装事項へ「4方式統合回帰」という表現を追加した。Copilot が後続の **§16** から **§19** の文書化でも、その記述を既定の残作業として自己参照的に転記した。記録の反復自体が、当初は未確定だった表現に独立根拠があるかのように扱われ、「残る単位」「具体的な実行計画」へ格上げされた。これは不適切だった。利用者が知らない間に正式工程として確定したものではない。今回の訂正は、責任主体を明確にし、同じ自己参照的な工程追加を再発させないためのものである。最新の工程判断は本 **§20** を優先する。

「4方式統合回帰」という独立した正式工程は、研究契約 **§32.21** にも、具体実装前設計 **§14** にも、試験条件・比較項目・合否基準まで含めて定義されていなかった。

最初の明示的な出現は、内部 entropy と pure keyed uniform helper の実装結果を記録した **§15** の未実装事項である。**§16** 以降の同語の反復は、上記のとおり Copilot が **§15** で追加した未確定の表現を、後続節の文書化で既定の残作業として自己参照的に転記した結果であり、新しい独立根拠や利用者承認を表さない。後続節で「残る単位」「具体的な実行計画」とまで書かれたが、実行対象 network、台数、seed、方式条件、比較 field、許容差、合否基準、一括実行 script は、その時点で確定していなかった。

tracked file から、共通 seed／RNG 改修後の「4方式統合回帰」を一括実行する正式 script は確認されなかった。「4方式を対象に設計した共通 seed／RNG 基盤」と、「4方式を一括実行する正式回帰試験」は同じ意味ではない。

本節以降の最新判断は次である。

- 「4方式統合回帰」を、利用者が承認済みの必須工程として扱わない。
- N=1 BATCH 対 FCFS 回帰と同列の、合否基準付きの確定済み試験として扱わない。
- 自動的に次の実行工程へ進めない。
- 将来、4方式横断確認が必要と判断する場合は、実行前に目的、対象方式、network、需要、台数、seed、方式固有設定、比較項目、許容差、合否基準、出力保存方針を明示し、利用者判断を得る。
- 過去節の記述は歴史的記録として残すが、最新の工程判断は本 **§20**、**§32.30**、**§21.9.31** を優先する。

この訂正は、4方式共通 seed／RNG 研究契約そのものを否定するものではない。問題は、未設計の検証工程を Copilot が文書上の必須工程として追加し、自己参照的な転記で格上げしたことである。production 実装、N=1 の実測、**§32.21** の研究契約を無効にするものではない。

### 20.2 維持する研究契約

維持する研究契約は次である。

- route choice は、signalized UXsim、FCFS、BATCH、TVT-MP 実 World、および TVT-MP baseline で共通の keyed 契約を使う。
- arrival tiebreaker は、FCFS、BATCH、TVT-MP 実 World、および TVT-MP baseline で共通化する。
- signalized UXsim の通常 merge は、専用の逐次 RNG を使う。
- Candidate と Level 2 の接続境界は、既存契約どおりである。
- 各方式の制御差により、交通結果そのものを 4 方式間で完全一致させる契約ではない。

N=1 で示したのは、新共通 seed 環境の横並びで FCFS と N=1 BATCH Level 2 が厳密一致することであり、FCFS、BATCH、TVT-MP、signalized UXsim の 4 方式を同一 network で一括比較し、交通結果が一致したことではない。

### 20.3 N=1診断の正式位置づけ

実行した正式診断 script は、tracked file の `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py` である。これは N=1 BATCH Level 2 対 FCFS の既存正式診断であり、**§14.18** の契約に対応する。本記録はこの script を変更していない。

条件は次である。

- 6×6 grid
- 内部 grid Node 36
- 外部 OD Node 24
- dynamic free routing
- signal なし
- internal Link length 400
- OD connector length 300
- free-flow speed 20
- clearance 1 timestep
- random seed 0
- demand generation seed 42
- BATCH `batch_size=1`
- `order_control_batch_t_trigger_level=2`
- virtual horizon 30
- FCFS と N=1 BATCH で同じ Vehicle plan
- N=1 専用 shortcut なし
- Level 2 を実際に呼ぶ

この診断は単なる平均値比較ではない。比較は丸めや tolerance なしの厳密一致であり、`comparison_class != "exact_match"` なら script 自身が `AssertionError` で失敗終了する。

集計 11 項目:

1. `total_vehicles`
2. `completed_trips`
3. `unfinished_trips`
4. `completed_ratio`
5. `total_travel_time`
6. `average_travel_time`
7. `average_delay`
8. `delay_ratio`
9. `total_distance_traveled`
10. `last_completed_trip_time`
11. `analyzer_reference_average_speed`

Vehicle 別 7 項目:

1. `state`
2. `departure_time`
3. `arrival_time`
4. `travel_time`
5. `destination_name`
6. `traveled_route_link_names`
7. `log_t_link_history`

さらに Vehicle 名集合と completion order も比較する。

### 20.4 200台の実測結果

利用者の Terminal 実行:

`python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 200`

結果:

- diagnostic script は正常終了した。
- `comparison_class: exact_match`
- `aggregate_mismatch_count: 0`
- `mismatched_vehicle_level_items: 0`
- FCFS 200／200 完走
- N1-L2 200／200 完走
- Level 2 call count 1497
- resolved 1497
- unresolved 0
- Level 1 fallback 0
- input identity check PASS
- assignment prefix violation なし
- visit_id／batch_assignment／service unit mismatch なし

FCFS と N1-L2 で一致した代表値:

- total travel time 32029.0 秒
- average travel time 160.1 秒
- average delay 0.4 秒
- total distance traveled 638800.0 m
- last completed trip time 684.0 秒

補助的な終了値確認コマンドでは、zsh 上の `PIPESTATUS` の扱いにより `test: unknown condition: -eq` が出た。これは diagnostic script の失敗ではない。script 本体は `comparison_class: exact_match`、不一致 0、正常終了メッセージがあり、script は不一致なら自ら失敗する。この補助コマンドの誤りを simulation 失敗として記録しない。

### 20.5 1,000台の実測結果

利用者の Terminal 実行:

`python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 1000`

ログ: `/tmp/n1_batch_vs_fcfs_1000_after_common_seed_836b99f.log`

結果:

- exit status 0
- `comparison_class: exact_match`
- `aggregate_mismatch_count: 0`
- `mismatched_vehicle_level_items: 0`
- FCFS 全車完走
- N1-L2 全車完走
- Level 2 call count が 0 より大きい
- script 正常終了

### 20.6 5,000台の実測結果

利用者の Terminal 実行:

`python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 5000`

ログ: `/tmp/n1_batch_vs_fcfs_5000_after_common_seed_836b99f.log`

結果:

- exit status 0
- `comparison_class: exact_match`
- `aggregate_mismatch_count: 0`
- `mismatched_vehicle_level_items: 0`
- FCFS 全車完走
- N1-L2 全車完走
- script 正常終了

Level 2 counters:

- call count: 46266
- resolved: 46229
- unresolved: 37
- Level 1 fallback: 37

単純な全 resolved ケースだけではない。Level 2 unresolved 37 件と Level 1 fallback 37 件を含めても、FCFS と N=1 BATCH が完全一致した。

### 20.7 seed改修前結果との関係

seed 改修前の 5,000 台記録:

- call count 46428
- resolved 46390
- unresolved 38
- fallback 38
- comparison class exact_match

今回の新共通 seed 環境:

- call count 46266
- resolved 46229
- unresolved 37
- fallback 37
- comparison class exact_match

旧 seed 環境と新共通 seed 環境の counter 数値一致は合格条件ではない。共通 seed／RNG 改修は、具体的な route choice、arrival tiebreaker、通常 merge 選択、そこから波及する交通展開を意図的に変え得る。必要な契約は、同じ新共通 seed 環境の横並びで `FCFS = N=1 BATCH` となることである。fallback 38 から 37 への変化を回帰失敗と断定しない。

### 20.8 N=1回帰の判定

共通 seed／RNG 改修後の N=1 BATCH 対 FCFS 統合回帰を完了とする。

合格した規模は 200 台、1,000 台、5,000 台である。10,000 台は今回実行していない。今回の正式合格範囲は 200、1,000、5,000 台である。

全規模共通:

- 全車完走
- aggregate mismatch 0
- Vehicle-level mismatch 0
- `comparison_class: exact_match`
- Level 2 が実際に作動した
- N=1 shortcut なし

5,000 台では unresolved と Level 1 fallback を含めて一致した。

書かないこと:

- 他 network、他 seed、他需要、他 parameter の一般的同値性を証明した、とは書かない。
- 性能優位性を示した、とは書かない。
- 4 方式の交通結果一致を示した、とは書かない。

### 20.9 現在地の訂正

最新の現在地は次とする。

完了:

1. 内部 entropy 保存と pure keyed uniform
2. Vehicle Link 進入状態
3. origin・in-trip route choice keyed 化
4. arrival tiebreaker keyed 化と Node 訪問番号
5. normal merge RNG 分離
6. 共通 seed／RNG 改修後の N=1 BATCH 対 FCFS 統合回帰（200、1,000、5,000 台、exact_match）

未確定または別判断:

- 「4方式統合回帰」という名称の一括試験
- 4方式横断確認の具体的な目的
- network
- 台数
- seed
- 比較項目
- 合否基準
- 一括 script
- 実行要否

未完了として残すもの:

- 共通 seed／RNG 改修の最終正本整理
- 全体受入れ判定
- 10,000 台 N=1 診断を追加で行うかの判断
- 他 network／他 seed での N=1 確認を追加するかの判断
- Candidate selection RNG は今回の共通 seed 改修範囲外のまま
- 新 BATCH は未実装・未採用
- 性能測定は合否条件外

「残りは 4方式統合回帰」とは書かない。

### 20.10 次の直接作業

次の直接作業は、今回の Markdown 差分を、利用者が Terminal で全文独立確認することである。

その後の予定は、必要なら訂正文を修正し、Markdown 3 ファイルだけを明示して stage し、commit し、commit 結果、最新 commit、残存変更を確認することである。production、test、diagnostic script は今回 commit 対象にしない。push は別指示である。push 後に status、最新 commit、local と remote の一致を確認する。

その次は、利用者判断なしに「4方式統合回帰」へ進まない。

次の技術判断候補は、事実として列挙するだけにし、利用者の承認前に選択しない。

- 現時点の証拠で共通 seed／RNG 改修を全体受入れできるか
- 10,000 台 N=1 診断を追加するか
- 別 seed または別 network の N=1 反証を追加するか
- 方式横断の追加確認が必要なら、その目的と合否基準を新しく設計するか

Git 操作は利用者が Terminal で行う。Cursor には行わせない。

### 20.11 検索語

4方式統合回帰、工程訂正、具体設計なし、合否基準未確定、正式scriptなし、利用者未承認、§15初出、後続節転記、N=1 BATCH対FCFS、exact_match、200台、1000台、5000台、10000台未実行、aggregate mismatch 0、Vehicle-level mismatch 0、全車完走、completion order、Level 2 call count 1497、Level 2 call count 46266、resolved 46229、unresolved 37、fallback 37、seed改修前fallback 38、新共通seed環境、旧seed結果非互換、grid_n1_level_2_vs_fcfs_check.py、batch_size=1、Level 2、virtual horizon 30、clearance 1、random seed 0、demand seed 42、6x6 grid、strict comparison、toleranceなし、N=1 shortcutなし、feature/common-seed-rng-foundation、836b99f、共通seed改修の全体受入れ、4方式横断確認の事前設計、Copilotによる工程追加、Copilotによる自己参照転記、利用者未提案、利用者未承認、具体設計なしの工程追加、正式工程への不適切な格上げ、責任主体、工程追加の再発防止

## 21. 共通seed／RNG改修に対する利用者Terminal原典とCopilot独立監査（2026-11-24）

執筆日は2026-11-24である。**§20** までの本文は削除も書換えもしない。本節は、Grok による既存反証だけで共通 seed／RNG 改修を受け入れず、利用者 Terminal の原典出力を使って Copilot が独立監査した結果を記録する。Grok の完了報告は、今回の独立監査の根拠として扱わない。

記録は次を分ける。

1. production 原典の独立確認。
2. test 設計の独立性確認。
3. 専用 test と既存回帰の再実行。
4. baseline fork 既存 fixture 不足の発見と test 限定修正。
5. 旧 route-choice RNG 診断が改修後方式へ適用できないこと。
6. 新しい full-simulation invariance test の新設と実測。
7. 現時点の受入れ判断と限界。

N=1 の実測記録 **§20** は本節で置き換えない。

### 21.1 production原典の独立確認

分岐元 `fde6865` から監査開始時 HEAD `87d10fd` までの実差分を、利用者 Terminal で確認した。

production 変更は次の 6 ファイル、合計 910 行追加・53 行削除だった。

- `uxsim/common_seed_rng_arrival_tiebreaker.py`
- `uxsim/common_seed_rng_keyed_uniform.py`
- `uxsim/common_seed_rng_route_choice.py`
- `uxsim/order_control_tvt_mp_candidate_binding_transfer.py`
- `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`
- `uxsim/uxsim.py`

独立確認した内容は次である。

- 既存の `W.rng` と `W.order_control_rng` の生成契約。
- 既存 `SeedSequence` の entropy 保存。
- SHA-256 による pure keyed uniform。
- domain と key 部分の明示的な直列化。
- origin route choice。
- in-trip route choice。
- Vehicle 別の Link 物理進入回数。
- origin attempt。
- current-Link 内の in-trip attempt。
- arrival tiebreaker。
- Node 訪問番号。
- normal merge 専用逐次 Generator。
- BATCH、FCFS、通常 transfer、Candidate binding の Link 進入接続。
- World copy。
- generic baseline fork。
- TVT rank 適用 baseline fork。
- Candidate local World。
- Level 2 mimic との境界。

原典確認で得た判断は次である。

- route choice と arrival tiebreaker に、旧 `W.rng` または `W.order_control_rng` の消費が残っている形跡は確認されなかった。
- normal merge の shuffle と choice は `W.normal_merge_rng` へ分離されていた。
- Link 物理進入記録は、origin、BATCH、FCFS no-clearance、FCFS clearance、共通 transfer、Candidate binding へ接続されていた。
- Level 2 mimic は局所時刻推定用の参照計算であり、新しい実 World の Link 進入 identity を作らない既存境界として、非接続を維持していた。
- Candidate local advance も新しい物理 Link 進入を起こさないため、Link 進入記録へ接続しない。
- World copy は pickle copy により、内部 entropy、Vehicle 状態、normal merge Generator 状態を複製する。
- この原典確認の範囲では、production に重大または high 相当の欠陥は見つからなかった。

原典確認で見つからなかったことと、すべての将来条件で正しいことが証明されたこととは、同一視しない。

### 21.2 test設計の独立性確認

専用 test の構造も、利用者 Terminal で確認した。

- keyed uniform test には、固定直列化 byte 列、SHA-256 digest、53-bit 整数の固定 vector がある。
- route choice test の候補選択期待値は、test 側の独立実装で計算され、production の selection helper を期待値生成に使っていない。
- arrival test の Node 訪問番号は、test 側で Node の inlink を独立集計している。
- normal merge test の期待 Generator は、test 側で `SeedSequence` と `spawn_key=(1,)` から独立生成している。
- production の正式経路を実際に通す test がある。
- source 文字列検査だけで全体を合格させる構成ではない。

これにより、独立性を高める構造が確認された。test と production が同じ誤りをそのまま共有する可能性を、完全に排除したとは書かない。

### 21.3 再実行した専用testと既存回帰

利用者 Terminal で、共通 seed／RNG 専用 6 系統を再実行し、終了値 0 だった。

- `tests_common_seed_rng_keyed_uniform.py`
- `tests_vehicle_link_entry_state.py`
- `tests_common_seed_rng_route_choice.py`
- `tests_common_seed_rng_arrival_tiebreaker.py`
- `tests_order_control_current_visit_arrival.py`
- `tests_common_seed_rng_normal_merge.py`

表示は次である。

- `Common seed/RNG keyed uniform tests passed.`
- `Vehicle link-entry state tests passed.`
- `Common seed/RNG route choice tests passed.`
- `Common seed/RNG arrival tiebreaker tests passed.`
- `Order-control current visit arrival tests passed.`
- `Common seed/RNG normal merge tests passed.`

直接関係する既存回帰 9 系統も、`set -e` 付きで再実行し、終了値 0 だった。

- `tests_order_control_rng.py`
- `tests/test_verification_route_choice.py`
- `tests_fcfs_order_control_transfer.py`
- `tests_order_control_batch_service_queue_transfer.py`
- `tests_order_control_batch_t_trigger_level_2_reference.py`
- `tests_order_control_batch_t_trigger_level_2_unarrived_reference.py`
- `tests_order_control_batch_transfer.py`
- `tests_order_control_tvt_mp_candidate_binding_transfer.py`
- `tests_order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`

production 6 ファイルの `py_compile` も終了値 0 だった。

専用 test と既存回帰ログに対する次の failure scan は該当なしだった。

- `Traceback`
- `AssertionError`
- `FAILED`
- `ERROR`
- `failed:`

`grep` 終了値 1 は該当文字列なしの意味であり、test 失敗ではない。

### 21.4 baseline fork既存fixture不足

追加で次を実行した。

- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_candidate_local_state.py`

最初の一括実行は、baseline fork alignment 側で終了値 1 となり、Candidate local state 側は `set -e` により未実行だった。

失敗は次である。

- test: `test_calls_alignment_once_per_node_in_target_node_order`
- Vehicle: `veh_b`
- Node: `junction_b`
- 症状: node visit number 0 のため、arrival tiebreaker 記録が停止した。

独立調査で原因を確定した。`veh_b` は通常走行で `in_a` へ到達した後、test fixture helper `_place_vehicle_on_inlink_with_new_order_control_visit()` により、上流の time_value Node を通過させず、人為的に `in_b` へ移されていた。

この helper は次を行っていた。

- `vehicle.link = inlink`
- `vehicle.begin_order_control_visit_on_link_entry()`

その間に、正式な物理 Link 進入記録 `vehicle.record_successful_physical_link_entry()` を行っていなかった。そのため、fixture 上では新しい Visit だけが開始され、`in_b` への物理進入回数が 0 のままになった。

判定は次である。

- production の自然走行経路で発生した欠陥ではない。
- 共通 seed／RNG 改修による厳格な整合性確認が、既存 test fixture の不完全な人為配置を検知した。
- production の node visit number 0 検証を緩めない。
- 0 を 1 へ補正しない。
- test fixture だけを、正式な物理進入契約へ適合させる。

修正したファイルは `tests_order_control_tvt_baseline_fork_alignment.py` だけである。

修正内容は次である。

- `_place_vehicle_on_inlink_with_new_order_control_visit()` で、`vehicle.link = inlink` による人為配置の後、`begin_order_control_visit_on_link_entry()` の前に `record_successful_physical_link_entry()` を 1 回追加した。
- Link 進入回数が 1 以上であることを assert した。
- in-trip attempt が 0 へ reset されたことを assert した。
- 同じ inlink 上の位置だけを戻す `_place_not_yet_arrived_vehicle_at_snapshot()` は変更せず、二重計上を防いだ。
- production は変更しなかった。

修正後の利用者 Terminal 結果は次である。

- `tests_order_control_tvt_baseline_fork_alignment.py`: 25 tests passed、exit status 0。
- `tests_order_control_tvt_mp_candidate_local_state.py`: 25 tests passed、exit status 0。

### 21.5 旧route-choice RNG診断の適用不能

既存の次の 2 本を、改修後の受入れ根拠へ再利用できるか調べた。

- `research_scripts/run_route_choice_rng_diagnostic_invariance_two_route.py`
- `research_scripts/run_route_choice_rng_diagnostic_invariance_12_vehicle_tvt_mp.py`

2 本目は `--help` に対応していなかったため、`--help` 指定でも実 simulation が起動した。

12 台 scenario の simulation 自体は、診断なしと診断ありの両方で完了したが、coverage validation で停止した。

- required origin draws: 12
- observed origin draws: 0
- `RuntimeError: Origin draws 0 < 12.`

独立調査により、旧診断 `research_scripts/route_choice_rng_diagnostic.py` は、production の `W.rng.choice` を一時 proxy で包み、その呼出しと Generator state を記録する設計だった。

旧診断自身の本文にも、次が明記されていた。

- keyed randomization ではない。
- production が `W.rng.choice` を呼んだときだけ draw として数える。
- 改修前の逐次 RNG 経路選択を監視する設計である。

共通 seed／RNG 改修後の origin／in-trip route choice は `W.rng.choice` を使用しない。

したがって、次のとおり判断する。

- origin draws 0 は、経路選択が行われなかったことを示さない。
- 共通 seed／RNG の production 欠陥を示さない。
- 旧診断が新しい keyed 方式を観測できないことを示す。
- 旧診断 2 本は、今回の改修後受入れ根拠から外す。
- 旧診断の過去用途まで無効だったとは判断しない。
- 旧診断を、改修後方式の合否判定へ流用しない。
- 旧診断 3 ファイルは、今回変更していない。

`research_scripts/route_choice_rng_diagnostic.py` には、今回以前からの作業ツリー変更が存在する。今回の独立監査では変更していない。この既存変更を、今回の成果へ含めない。

### 21.6 新しいfull-simulation invariance test

旧診断を大改造せず、改修後方式専用の独立実走行 test を新規作成した。

新規ファイルは `tests_common_seed_rng_full_simulation_invariance.py` である。synthetic fixture であり、field network でも正式 3,000 台実験でもない。test は 3 件である。

#### 21.6.1 two-route full simulation

test 名は `test_two_route_full_simulation_matches_after_world_rng_advance` である。

同じ network、同じ Vehicle plan、同じ明示 seed で、control World と perturbed World を独立構築した。全 Vehicle 追加後、本実行前に、perturbed 側の `W.rng.random()` だけを 4 回余分に消費した。

変更していないものは、`_common_seed_rng_internal_entropy`、`normal_merge_rng`、network、Vehicle plan、Vehicle name、OD、departure time、route preference 条件である。

network は次を実際に含む。origin で 2 本以上の選択肢、走行途中でも 2 本以上の選択肢、signal なし、order control なし、hard deterministic mode なし、specified route なし、低需要、全車完走、である。

各 World で、origin probabilistic choice count と in-trip probabilistic choice count が 0 より大きいことを確認した。in-trip count は、test 側が `Vehicle.route_next_link_choice` を薄く包み、元 method を 1 回だけ呼び、呼出し前後の正式 attempt count 増分だけを記録した。選択結果は変更せず、`finally` で元 method を復元した。

完全一致の比較対象は、Vehicle 名集合、state、departure time、arrival time、travel time、destination、traveled route、`log_t_link`、completion order、total vehicles、completed trips、unfinished trips、total travel time、average travel time、total distance traveled、last completed trip time である。tolerance、丸め、近似比較は使用しない。

結果は、完全一致、全 3 台完走、origin choice 実作動あり、in-trip choice 実作動あり、である。

#### 21.6.2 World copy

test 名は `test_world_copy_preserves_route_choice_counts_and_normal_merge_state` である。

実行途中の World を `W.copy()` し、次を確認した。

- World は別 object である。
- `_common_seed_rng_internal_entropy` は同値である。
- 各 Vehicle の `link_entry_count_by_link_name` は同値である。
- その dict は別 object である。
- `origin_route_choice_attempt_count` は同値である。
- `current_link_route_choice_attempt_count` は同値である。
- 少なくとも 1 件の Link 進入記録が実在する。
- `normal_merge_rng` は別 Generator object である。
- copy 直後の Generator state は同値である。
- copy 側だけ進めると state が分離する。
- 元 World の state は不変である。

#### 21.6.3 ordinary merge separation

test 名は `test_ordinary_merge_full_simulation_matches_after_world_rng_advance` である。

同じ seed の小規模 merge network を 2 つ構築し、perturbed 側の `W.rng` だけを本実行前に余分に進めた。

確認したことは次である。

- 実行前の `normal_merge_rng` state は同一である。
- `_common_seed_rng_internal_entropy` は同一である。
- `W.rng` state は意図どおり異なる。
- 2 台は同時刻に各 inlink へ進入する。
- outlink 通過順は両 World で一致する。
- Vehicle 別と全体の交通結果は完全一致する。
- merge 後に `normal_merge_rng` は開始 state から進んだ。
- merge 後の `normal_merge_rng` state は両 World で一致する。
- 全車完走である。

実行結果は、3 tests passed、exit status 0 である。

### 21.7 最終独立回帰

fixture 修正と full-simulation test 追加後、次の 9 系統を `set -e` 付きでまとめて再実行した。

- `tests_common_seed_rng_keyed_uniform.py`
- `tests_vehicle_link_entry_state.py`
- `tests_common_seed_rng_route_choice.py`
- `tests_common_seed_rng_arrival_tiebreaker.py`
- `tests_order_control_current_visit_arrival.py`
- `tests_common_seed_rng_normal_merge.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_candidate_local_state.py`
- `tests_common_seed_rng_full_simulation_invariance.py`

結果は、exit status 0、全 9 系統合格である。内訳は、baseline fork alignment 25 tests passed、Candidate local state 25 tests passed、full-simulation invariance 3 tests passed である。

最終ログに対する failure scan で、`Traceback`、`AssertionError`、`FAILED`、`ERROR`、`failed:` は該当なしだった。`grep` 終了値 1 は該当なしの意味である。

今回の監査で変更・追加した 2 test ファイルの `py_compile` は終了値 0 だった。

- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_common_seed_rng_full_simulation_invariance.py`

書式確認は次である。

- tracked fixture の `git diff --check` は出力なしだった。
- 未追跡新規 test の `git diff --no-index --check /dev/null ...` は警告なしだった。
- 後者の終了値 1 は、新規ファイル全体が差分であるためであり、trailing whitespace 等の警告は無かった。

### 21.8 N=1実測との関係

**§20** に記録済みの N=1 BATCH 対 FCFS 結果も維持する。共通 seed／RNG 改修後の結果は次である。

- 200 台: exact_match。
- 1,000 台: exact_match。
- 5,000 台: exact_match。5,000 台は Level 2 unresolved 37 件、fallback 37 件を含めて完全一致である。
- 10,000 台は未実行である。

今回の独立監査は、N=1 結果を置き換えるものではない。N=1 は BATCH と FCFS の等価性を確認する。今回の full-simulation invariance は、`W.rng` の余分な消費から keyed route choice と normal merge が分離されていること、および copy 状態を確認する。両者は異なる証拠であり、相互補完する。

### 21.9 現時点の判定

次を、この監査範囲の判断として記録する。

- Grok の反証だけではなく、利用者 Terminal の原典出力を用いた Copilot 独立監査を実施した。
- production 原典、test 独立性、専用 test、既存回帰、baseline fork、Candidate copy、World copy、実走行不変性まで確認した。
- 独立監査中に、既存 baseline fixture 不足を 1 件発見し、production を緩めず test 側だけを修正した。
- 旧 route-choice RNG 診断が新方式に適用できないことも発見した。
- 旧診断を不適切に合格根拠へ使わず、新方式専用の実走行反証へ置き換えた。
- 現時点で、共通 seed／RNG 改修の production に、重大または high 相当の欠陥は見つかっていない。
- 監査した範囲については、共通 seed／RNG 改修の全体受入れを妨げる事象は確認されていない。
- これは、監査した範囲に限った判断である。全体受入れの完了そのものを、本節だけで断定しない。
- 全 network、全 seed、全将来条件の完全証明ではない。
- 10,000 台 N=1、別 network、別 seed、性能評価、Candidate selection RNG、新 BATCH は、今回確認していない。
- 「4方式統合回帰」は未承認工程として撤回済みであり、今回の監査を理由に復活させない。
- 方式横断確認を将来行う場合は、別途目的と合否基準を設計し、利用者判断を得る。
- 利用者による最終受入れ判断は、まだ必要である。

### 21.10 現在の作業ツリー

今回の独立監査で新たに変更・追加したものは次だけである。

- 修正: `tests_order_control_tvt_baseline_fork_alignment.py`
- 新規: `tests_common_seed_rng_full_simulation_invariance.py`

既存の無関係な作業ツリー変更と未追跡ファイル群には触れていない。今回以前から変更済みの `research_scripts/route_choice_rng_diagnostic.py` を、今回の変更へ含めない。

本節の文書化では、production、test、diagnostic、research script、output を変更していない。

### 21.11 次の直接作業

次の直接作業は、利用者が Terminal で Markdown 3 ファイルの差分を独立確認することである。

その後の判断候補は次である。選択は利用者判断であり、本節はどれかを先に実行しない。

- 文書訂正。
- 独立監査範囲に基づく、共通 seed／RNG 改修の最終受入れ可否。
- 今回の test 2 ファイルと Markdown 3 ファイルの commit。
- push は、commit 確認後の別指示である。

10,000 台 N=1、別 network、別 seed、方式横断確認へ、自動的に進まない。

### 21.12 検索語

共通seed RNG独立監査、Copilot独立確認、Terminal原典確認、Grok反証だけではない、production差分精読、test独立性、baseline fork fixture不足、veh_b、junction_b、node visit number 0、人為配置、record_successful_physical_link_entry、production非変更、baseline fork alignment 25 tests、Candidate local state 25 tests、旧route choice RNG診断、W.rng.choice監視、Origin draws 0、旧診断適用不能、keyed route choice、新方式専用実走行反証、full simulation invariance、W.rng余分消費、two-route、origin choice実作動、in-trip choice実作動、World copy、normal merge separation、完全一致、3 tests passed、最終9系統、exit status 0、failure scan該当なし、py_compile成功、N=1 BATCH FCFS equivalence、200台、1000台、5000台、unresolved 37、fallback 37、highなし、重大欠陥なし、全条件証明ではない、4方式統合回帰を復活させない、最終受入れ判断

## 22. 共通seed／RNG後clearance=1 FCFS対TVT-MP再実行とVOT・役割・外部便益分析（2026-11-25）

共通seed／RNG改修後の production を使い、旧 clearance=1 結果を上書きせず、6×6ネットワーク・3000台について FCFS と TVT-MP を別 directory へ正式再実行した。旧結果との完全一致は合格条件にしない。目的は、同じ計画・seed 条件の FCFS対TVT-MP再実行から、同一 Vehicle の旅行時間差を比較し、VOT・役割・非参加車・金銭移転・外部便益を確認することである。単一seed の観察であり、因果効果ではない。4方式統合回帰を復活させない。

### 22.1 新規runnerと再実行条件

既存 runner・既存 output・production は変更せず、新規別ファイルとして次を作成した。

- `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng.py`
- `research_scripts/run_fcfs_6x6_grid_3000_vehicle_clearance_1_common_seed_rng.py`

共通条件は、6×6 network、3000台、departure T=0..999、traffic seed 0、demand seed 42、VOT seed 1、cohort／nonparticipation seed 3、participating 2400、nonparticipating 600、clearance timesteps 1、TVT-MP candidate Visit 上限 10、hard deterministic mode なし、full completion、traffic clearance、旧 output 非変更、新規別 directory、既存 directory があれば停止、production 非変更、である。

新 FCFS output は `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3`。新 TVT-MP output は `research_outputs/trial/tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_nonparticipation_seed_3`。両 runner は `py_compile` と static validation を通過してから、利用者 Terminal で `caffeinate` 付き実行を行った。新規 output directory はローカル出力であり、文書 commit へ自動的には含めない。`research_scripts/route_choice_rng_diagnostic.py` とその他の無関係な未追跡 script・CSV・output には触れない。

### 22.2 TVT-MP再実行結果

TVT-MP は正常完走した。3000台、participating 2400、nonparticipating 600、final World.T = 2022、evaluation end timestep = 2021、final actual passage timestep = 1975、full trip completion = True、traffic clearance = True、transaction count = 4,233、transaction audit rows = 4,233、Visit audit rows = 11,691、buyer audit rows = 4,966、seller audit rows = 6,068、nonparticipating audit rows = 657、FIFO violation total = 0、audit CSV validation passed。AWT = 477.346 s、AWWT = 454.0903012017529、Route-Conditional AWT = 464.13 s、Route-Conditional AWWT = 441.49287823490187、average detour = 13.216 s。participating cohort AWT = 480.37708333333336 s、participating cohort AWWT = 464.0380557226082。nonparticipating cohort AWT = 465.2216666666667 s、nonparticipating cohort AWWT = 414.29928311832987。exec_simulation seconds = 34,713.055519、final script total seconds = 34,776.145572。saved-result equality comparison performed = False。common-seed RNG production active = True。

### 22.3 FCFS再実行結果と平均総旅行時間

FCFS も正常完走した。3000台、clearance=1、full completion、traffic clearance、Vehicle plan hash matched、cohort hashes matched。AWT = 574.9213333333333 s、AWWT = 570.6055096886787、Route-Conditional AWT = 560.1053333333333 s、Route-Conditional AWWT = 556.215696107889、average detour = 14.816 s、average weighted detour = 14.389813580789948、average OD minimum free-flow trip time = 105.576 s、average actual-route free-flow trip time = 120.392 s。AWT identity passed、AWWT identity passed。FCFS simulation seconds = 5.738035792019218、production evaluation seconds = 54.16278566699475、script total seconds = 117.26025816705078、formal output success。saved-result equality comparison performed = False。

全 3000台の平均総旅行時間は、FCFS = 574.9213333333333 + 105.576 = 680.4973333333333 s、TVT-MP = 477.346 + 105.576 = 582.922 s。TVT-MP は FCFS より平均 97.575秒短い（97.5753333333333 s）。この平均総旅行時間差は全車両平均であり、participating のみの値ではない。

### 22.4 旧clearance=1分析の再現

旧 clearance=1 保存済み FCFS／TVT-MP 結果から、participating 2400 の VOT 分析を Terminal 上で再計算し、正本文書の旧値を完全再現した。短縮量は `travel_time_saving = FCFS actual_travel_time_s − TVT-MP actual_travel_time_s`。正なら TVT-MP で短縮、0 なら同じ、負なら TVT-MP で悪化。旧結果は N = 2,400、mean saving = 144.22708333333333 s、median saving = 88.5 s、improved／equal／worsened = 1,793／20／587、improved rate = 74.70833333333333%、Spearman rho = 0.030141370025244956、p = 0.1398940588208832、Q1 = 141.614583 s、Q2 = 137.683333 s、Q3 = 147.554167 s、Q4 = 132.827083 s、Q5 = 161.456250 s、Q5−Q1 = 19.84166666666667 s。旧 clearance=1 では、VOT と最終総旅行時間短縮の明瞭な順位相関は確認できなかった。

### 22.5 共通seed／RNG後のparticipating VOT分析

新 FCFS と新 TVT-MP を同一 Vehicle 名で一対一結合した。participating = 2,400、mean saving = 99.90166666666667 s、median saving = 54.5 s、improved／equal／worsened = 1,701／24／675。VOT Spearman rho = 0.0641324186596357、p = 0.0016697836402282693、Pearson r = 0.037868571128079904、Pearson p = 0.06361445730859616。VOT 五分位平均短縮は Q1 = 77.102083 s、Q2 = 95.564583 s、Q3 = 103.806250 s、Q4 = 84.750000 s、Q5 = 138.285417 s、Q5−Q1 = 61.18333333333332 s。完全単調ではない。Spearman 効果量は小さい。大標本なので p 値が小さいことと効果量が強いことを混同しない。旧結果より VOT との正方向の関係は見えやすくなった。単一seed のため一般化しない。

### 22.6 相互排他的役割区分

参加車 2,400 台を重複しない区分へ分けた。BUYER_ONLY は buyer_count > 0 かつ seller_count == 0。SELLER_ONLY は buyer_count == 0 かつ seller_count > 0。BUYER_DOMINANT は両方を経験し buyer_count > seller_count。SELLER_DOMINANT は両方を経験し seller_count > buyer_count。BALANCED は buyer_count == seller_count > 0。NO_TRANSACTION は buyer_count == seller_count == 0。人数は BUYER_ONLY = 356、SELLER_ONLY = 447、BUYER_DOMINANT = 585、SELLER_DOMINANT = 734、BALANCED = 250、NO_TRANSACTION = 28、合計 = 2,400。過去に広義の buyer dominant として BUYER_ONLY も含めた 941 台、広義の seller dominant として SELLER_ONLY も含めた 1,181 台を表示したが、今回の相互排他的役割区分では 585 台・734 台である。

役割別の FCFS 比総旅行時間短縮は次である。BUYER_ONLY は N = 356、mean saving = 119.21910112359551 s、median = 52 s、Spearman rho = 0.1455488169339345、p = 0.005937436019902466、Q5−Q1 = 87.76604068857591 s。SELLER_ONLY は N = 447、mean saving = 75.1185682326622 s、median = 28 s、Spearman rho = 0.017622701488794062、p = 0.7102120148251589、Q5−Q1 = 16.477777777777774 s。BUYER_DOMINANT は N = 585、mean saving = 113.17606837606837 s。SELLER_DOMINANT は N = 734、mean saving = 95.0 s。BALANCED は N = 250、mean saving = 108.848 s。NO_TRANSACTION は N = 28、mean saving = 21.214285714285715 s。BUYER_ONLY では正の VOT 関係が比較的明瞭だが、SELLER_ONLY では確認できない。これは関連分析であり、VOT 上昇の因果効果を直接示すものではない。因果効果ではない。

### 22.7 VOT Top層の役割構成

分析順は、役割群を先に限定せず、まず全参加車の VOT Top 層を抽出し、その中の役割構成を見る。Top 20% は N = 480、VOT threshold = 1.1026898912438625、mean saving = 138.28541666666666 s、median = 81 s、BUYER_ONLY = 211（43.96%）、BUYER_DOMINANT = 204（42.50%）、buyer 側合計 = 86.46%、BALANCED = 37（7.71%）、SELLER_DOMINANT = 13（2.71%）、SELLER_ONLY = 9（1.88%）、NO_TRANSACTION = 6（1.25%）。Top 10% は N = 240、threshold = 2.2128076988664263、mean saving = 136.75416666666666 s、median = 83 s、BUYER_ONLY = 143（59.58%）、BUYER_DOMINANT = 79（32.92%）、buyer 側合計 = 92.50%。Top 5% は N = 120、threshold = 4.006230310754763、mean saving = 127.09166666666667 s、median = 62 s、BUYER_ONLY = 85（70.83%）、BUYER_DOMINANT = 25（20.83%）、buyer 側合計 = 91.66%。Top 1% は N = 24、threshold = 10.793873103649728、mean FCFS 比 travel-time saving = 129.375 s、median = 38.5 s、improved = 19、equal = 0、worsened = 5、improved rate = 79.1666667%、BUYER_ONLY = 19（79.17%）、BUYER_DOMINANT = 5（20.83%）、buyer 側合計 = 100%、seller 側・BALANCED・NO_TRANSACTION = 0。Top 1%全車buyer側である。Top 1% は 24 台と小さく、平均・中央値・割合はブレが大きい。Top 層内部の Spearman は VOT 範囲を狭くした後の制限範囲相関であり、主指標にしない。主要結論は、高 VOT 層ほど buyer 側へ強く偏ることである。

### 22.8 VOT Top 1%の総旅行時間・局所実現短縮・金銭

VOT Top 1% は participating 2,400 台の true VOT 99パーセンタイル以上として抽出した。VOT cutoff = 10.793873103649728、N = 24、全 24 台が buyer 側、BUYER_ONLY = 19 台（79.16666666666667%）、BUYER_DOMINANT = 5 台（20.833333333333332%）。Top 1% 全 24 台は、mean TVT-MP total travel time = 533.875 s（Top 1%平均総旅行時間533.875秒）、median TVT-MP total travel time = 574.0 s、mean realized signed saving = 11.916666666666666 s（Top 1%局所実現短縮11.9167秒）、median realized signed saving = 10.0 s、mean payment = 5.7788930240214 円（Top 1%平均支払5.7789円）、median payment = 4.313735607715271 円、mean compensation = 0.6694662526163522 円、median compensation = 0 円、mean net receipt = −5.109426771405048 円（Top 1%平均正味受取マイナス5.1094円）、median net receipt = −3.697115454486527 円。

Top 1% 内 BUYER_ONLY 19 台は、mean TVT-MP total travel time = 441.89473684210526 s、mean realized signed saving = 11.631578947368421 s、median = 9.0 s、mean payment = 5.70492020956274 円、median payment = 4.004600075648474 円、compensation = 0 円、mean net receipt = −5.70492020956274 円。Top 1% 内 BUYER_DOMINANT 5 台は、mean TVT-MP total travel time = 883.4 s、mean realized signed saving = 13.0 s、median = 15.0 s、mean payment = 6.059989718964308 円、median payment = 5.6487336305911215 円、mean compensation = 3.2134380125584903 円、median compensation = 0 円、mean net receipt = −2.8465517064058177 円。VOT Top 1% は全車が buyer 側であり、時間を買う側へ強く選別された。Top 1% 全体では、平均約 11.92 秒の局所実現短縮と引き換えに、平均約 5.11 円の支払超過。Top 1% の支払額は全 BUYER_ONLY 平均 3.471 円より大きい。Top 1% 内 BUYER_DOMINANT は 5 台しかなく、平均値を一般化しない。Top 1% 全体も 24 台であり、単一seed の探索的記述値として扱う。局所実現短縮と FCFS 比最終総旅行時間短縮を混同しない。

### 22.9 FCFS単独とnonparticipatingのVOT対照

共通seed／RNG後 FCFS の participating cohort 2,400 台では、VOT vs FCFS OD waiting の Spearman rho = 0.03421327460298571、p = 0.09379330766429333。VOT vs FCFS travel time の Spearman rho = 0.03398814088045213、p = 0.095975506608839。FCFS waiting の VOT 五分位平均は Q1 = 576.527083 s、Q2 = 562.554167 s、Q3 = 584.414583 s、Q4 = 566.170833 s、Q5 = 611.727083 s、Q5−Q1 = 35.2 s。FCFS travel time の五分位平均は Q1 = 682.002083 s、Q2 = 667.954167 s、Q3 = 690.889583 s、Q4 = 672.820833 s、Q5 = 717.602083 s、Q5−Q1 = 35.6 s。五分位は非単調であり、FCFS単独VOT相関なし、と確認できる範囲では明瞭な順位相関はない。

TVT-MP nonparticipating 600 台は、N = 600、mean saving = 88.27 s、median = 41.5 s、Spearman rho = 0.03263077060366099、p = 0.42496736732706486、improved／equal／worsened = 422／5／173、improved rate = 70.33333333333333%。五分位平均は Q1 = 81.35 s、Q2 = 96.358333 s、Q3 = 52.75 s、Q4 = 110.908333 s、Q5 = 99.983333 s、Q5−Q1 = 18.63333333333334 s。非単調であり、nonparticipating VOT相関なし。比較整理は、FCFS participating 単独 rho 約 0.034 で明瞭でない、TVT-MP nonparticipating rho 約 0.033 で明瞭でない、TVT-MP participating の FCFS 比短縮 rho 約 0.064 で弱い正関係、BUYER_ONLY の FCFS 比短縮 rho 約 0.146 でより明瞭な正関係、である。単一seed・観察分析であり、因果効果ではない。

### 22.10 participatingとnonparticipatingの平均短縮差

participating は N = 2,400、mean saving = 99.90166666666667 s、median = 54.5 s、standard deviation = 246.38767867050322 s、improved／equal／worsened = 1,701／24／675、improved rate = 70.875%。nonparticipating は N = 600、mean saving = 88.27 s、median = 41.5 s、standard deviation = 233.89172566001636 s、improved／equal／worsened = 422／5／173、improved rate = 70.33333333333333%。平均差 participating − nonparticipating = 11.631666666666675 s。参考的な車両単位 bootstrap 20,000 回の 95% CI は −9.640885416666666 ～ 32.79994791666663 s（bootstrap参考値）。参考的な車両単位並べ替え検定 20,000 回の two-sided p = 0.29678516074196293（並べ替え検定参考値）。単純比較では 11.63 秒差は明瞭とは確認できない。参加車と非参加車では OD 構成が異なる（OD未調整）。車両間相互作用により独立ではない。この bootstrap と並べ替え検定は、この単一run で車両を独立観測と仮定した参考値にすぎない。参加属性の因果効果や正式な統計検定とは扱わない。より適切には OD・出発時刻帯内比較、割当方式を再現した層内並べ替え、複数 seed run が必要である。

### 22.11 同経路nonparticipatingと異経路nonparticipating

経路文字列は FCFS と TVT-MP で JSON 内空白表現が異なったため、文字列直接比較を使わず、JSON list を tuple へ正規化した（経路JSON正規化）。全 nonparticipating は N = 600、mean saving = 88.27 s、median = 41.5 s、standard deviation = 233.89172566001636 s、improved rate = 70.33333333333333%、net total saving = 52,962 s、gross positive saving = 79,742 s、gross worsening magnitude = 26,780 s。同経路nonparticipating は N = 236（39.333333333333336%）、mean saving = 66.24152542372882 s、median = 23.5 s、standard deviation = 120.58603767048422 s、improved／equal／worsened = 188／4／44、improved rate = 79.66101694915254%、net total saving = 15,633 s、gross positive = 17,425 s、worsening magnitude = 1,792 s、net total saving 寄与 = 29.51738982666818%。異経路nonparticipating は N = 364（60.666666666666664%）、mean saving = 102.5521978021978 s、median = 107.5 s、standard deviation = 283.43911171581937 s、improved／equal／worsened = 234／1／129、improved rate = 64.28571428571429%、net total saving = 37,329 s、gross positive = 62,317 s、worsening magnitude = 24,988 s、net total saving 寄与 = 70.48261017333182%。異経路平均 − 同経路平均 = 36.31067237846898 s。nonparticipating の便益を経路変更だけでは説明できない。同経路車でも平均 66.24 秒短縮した。異経路群は平均短縮が大きく、正味短縮の約 70.48% を担う。同経路で短縮が残ることは、交通流・通過タイミングの外部便益を示唆する。ただし、TVT 対象交差点付近の通過改善だけが原因とは未確認である。通常 Node、下流混雑、他車の経路・取引連鎖も含み得る。

### 22.12 公式支払・公式補償の収支均衡とFCFS比総便益

CSV の正式列は、buyer 支払 `official_payment`、seller 補償 `official_compensation`、buyer 実現時間価値 `realized_time_value`、seller 実現遅延損失 `realized_delay_loss`、Visit 局所純便益 `realized_gain` である。Visit 行数は buyer Visit = 4,966、seller Visit = 6,068、nonparticipating Visit = 657。Visit 表は buyer 公式支払合計 = 3,173.109890768508 円、seller 公式補償合計 = 3,173.109890768508 円、差 = 0。Transaction 表は buyer 公式支払合計 = 3,173.1098907685086 円、seller 公式補償合計 = 3,173.1098907685086 円、差 = 0。記録上の均衡額は 3173.109890768508円 である。Visit 表と Transaction 表の差は約 4.55e-13 円で、浮動小数点集計順の差である。nonparticipating Visit の公式支払・公式補償は全件 0。収支均衡検証は成功した。参加車全体では `sum(seller compensation − buyer payment) = 0` であり、参加車全体の平均総便益は参加車全体の平均時間便益と一致する。

定義は `time_benefit = true_vot_per_second × (FCFS travel time − TVT-MP travel time)`、`net_money_received = seller compensation − buyer payment`、`total_benefit = time_benefit + net_money_received`。金額単位は円。VOT の対数正規分布平均を 1 円としている研究設定に基づく。全参加車は mean travel-time saving = 99.90166666666667 s、mean time benefit = 123.04433689226586 円、mean net money はほぼ 0 円、mean total benefit = 123.04433689226586 円、median total benefit = 12.143195283855919 円、positive total benefit rate = 72.91666666666666%。nonparticipating は mean travel-time saving = 88.27 s、mean time benefit = 90.39869486556745 円、money = 0、mean total benefit = 90.39869486556745 円、median total benefit = 9.01200841974001 円、positive total benefit rate = 70.33333333333334%。

役割別は次である。BUYER_ONLY は mean time benefit = 434.31824788778533 円、mean net money = −3.470934530729829 円、mean total benefit = 430.84731335705544 円、median total benefit = 79.26256715674683 円、positive total benefit = 79.7752808988764%。SELLER_ONLY は mean time benefit = 16.653930848775815 円、mean net money = +0.8411989809585508 円、mean total benefit = 17.49512982973437 円、median total benefit = 1.9382861084679557 円、positive total benefit = 75.39149888143176%。BUYER_DOMINANT は mean time benefit = 168.1063230519461 円、mean net money = −0.35152551144866095 円、mean total benefit = 167.75479754049746 円。SELLER_DOMINANT は mean time benefit = 27.13066695174298 円、mean net money = +1.2244997614845778 円、mean total benefit = 28.35516671322756 円。BALANCED は mean time benefit = 59.3376204329145 円、mean net money = +0.6659853908765333 円、mean total benefit = 60.003605823791034 円。NO_TRANSACTION は mean time benefit = 5.510413135258408 円、net money = 0、mean total benefit = 5.510413135258408 円。buyer 側は支払超過、seller 側は受取超過で、方向は制度設計と整合する。今回の公式金銭移転は FCFS 比の時間便益に比べて小さい。参加車全体では金銭が相殺される。参加車と非参加車の総便益差を参加属性の因果効果とは解釈しない。OD、VOT 分布、出発時刻、交通相互作用が異なる。

### 22.13 TVT-MP内の局所実現短縮と役割別金銭

TVT-MP 内の局所的実現時間変化は、各 Visit の `baseline_minus_actual_passage_seconds` を車両単位で符号付き合計した。正は baseline より actual が早い、負は baseline より actual が遅い。buyer 短縮と seller 遅延を同一車両内で相殺する。この値は FCFS 世界との最終総旅行時間差とは別である。

全参加車は N = 2,400、mean TVT-MP total travel time = 586.352 s、mean realized signed saving = +2.308 s、median = +2 s、mean payment = 1.322 円、mean compensation = 1.322 円、mean net receipt はほぼ 0 円。BUYER_ONLY は N = 356、mean TVT-MP total travel time = 497.447 s、mean realized saving = +12.028 s、median = +10 s、mean payment = 3.471 円、median payment = 2.142 円、compensation = 0、mean net receipt = −3.471 円。SELLER_ONLY は N = 447、mean TVT-MP total travel time = 491.691 s、mean realized saving = −7.989 s、median = −7 s、payment = 0、mean compensation = 0.841 円、median compensation = 0.465 円、mean net receipt = +0.841 円。BUYER_DOMINANT は N = 585、mean travel time = 638.950 s、mean realized saving = +10.453 s、median = +10 s、mean payment = 2.441 円、mean compensation = 2.090 円、mean net receipt = −0.352 円。SELLER_DOMINANT は N = 734、mean travel time = 689.605 s、mean realized saving = −2.933 s、median = −2 s、mean payment = 0.422 円、mean compensation = 1.646 円、mean net receipt = +1.224 円。BALANCED は N = 250、mean travel time = 501.136 s、mean realized saving = +3.460 s、median = +3 s、mean payment = 0.799 円、mean compensation = 1.465 円、mean net receipt = +0.666 円。NO_TRANSACTION は N = 28、mean travel time = 183.143 s、realized saving = 0、money = 0。NONPARTICIPATING は N = 600、mean travel time = 569.202 s、mean trade-scope local external effect = +0.717 s、median = 0、money = 0。

BUYER_ONLY の詳細は、356 台、observed buyer Visit = 1,197、local actual TVT saving total = 4,282 s（BUYER_ONLY 4282秒、1.1894444444444445 hours）、per buyer Visit mean = 3.5772765246449456 s、median = 3 s、min = 0、max = 15、positive／zero／negative = 1,173／24／0、per BUYER_ONLY Vehicle cumulative mean = 12.02808988764045 s（平均12.028秒）、median = 10 s、min = 1、max = 39、positive／zero／negative Vehicle = 356／0／0。BUYER_ONLY では平均総旅行時間 497.447 秒に対し、局所実現短縮平均 12.028 秒で約 2.42%。平均支払3.471円。SELLER_ONLY平均遅延7.989秒、平均補償0.841円。trade-scope外部効果0.717秒。BUYER_ONLY の FCFS 比最終総旅行時間短縮合計は 42,442 秒だが、TVT 取引の局所実現短縮合計は 4,282 秒である。差 38,160 秒をそのまま間接効果とは断定しない。経路、混雑、通常 Node、他車取引、下流波及、baseline 定義差が混ざる。

### 22.14 フリーライダー問題の暫定評価

直接取引層では、BUYER_ONLY は平均 12.03 秒の局所短縮を得て平均 3.47 円を支払い、SELLER_ONLY は平均 7.99 秒局所的に遅延し平均 0.84 円を受け取る。NONPARTICIPATING の trade-scope 局所外部効果は平均 0.717 秒、中央値 0、金銭授受なし。直接的な TVT 取引便益を nonparticipating が buyer と同程度に無償取得する構造は確認されない。この層では顕著なフリーライダー問題は見えにくい。ネットワーク全体層では、FCFS 比最終総旅行時間短縮は participating 平均 99.90 秒、nonparticipating 平均 88.27 秒である。同経路 nonparticipating でも平均 66.24 秒短縮する。nonparticipating は金銭授受なしで大きな外部便益を受ける。参加車と非参加車の単純平均差 11.63 秒は明瞭とは確認できない。この層では参加せずネットワーク外部効果を受けるフリーライダー誘因が残る可能性がある。現時点の最も正確な表現は、「直接的な取引便益の横取りは小さい一方、ネットワーク全体の効率改善による nonparticipating への外部便益は大きい。フリーライダー問題は消滅したのではなく、取引局面からネットワーク外部効果の層へ移っている可能性がある。」である。「フリーライダー問題を回避できた」とは断定しない。

### 22.15 将来の参加資格介入とVOT介入

現時点では未実行・未採用の備忘録である。案 A の参加資格介入は、600 台の nonparticipating から 1 台を選び、その 1 台だけを participating へ変更し、VOT、OD、departure、その他 seed を固定して、元 TVT-MP と介入後 TVT-MP を比較する。特定車両へ参加資格を与えた限界効果を測る。15 台程度なら VOT 五分位ごとに 3 台の層化抽出案。1 回約 9 時間 30 分なら 15 回で約 142.5 時間。15 例は探索的であり一般的母平均とはしない。案 B の VOT介入は、participating 車 1 台だけの VOT を Top 1% 水準へ引き上げる。正直申告実験なら true VOT と declared VOT を同時に変更する。参加状態、OD、departure、その他 seed を固定する。候補値は participating の 99パーセンタイル10.793873103649728。将来的には元 VOT、2 倍、5 倍、99 パーセンタイルの段階介入も検討可能である。VOT 変化は取引成立や候補選択を離散的に変え得る。現在の関連分析より因果解釈に近づくが、交通相互作用と共通基準 run 依存は残る。これらは今すぐ実行する工程ではない。

### 22.16 総合判定、未確認、次の直接作業

共通seed／RNG後も TVT-MP は FCFS より全 3000台平均で約 97.575秒短い。participating の VOT と FCFS 比短縮には弱い正の関係がある。BUYER_ONLY ではその関係がより明瞭である。高 VOT Top 層ほど buyer 側へ強く偏り、Top 1% は全 24 台が buyer 側である。Top 1% は平均約 11.92 秒の局所短縮を得て、平均約 5.11 円の支払超過である。FCFS 単独と TVT-MP nonparticipating には明瞭な VOT 相関がない。すべて単一seed の観察結果であり一般化しない。participating と nonparticipating の短縮差は OD未調整で、参加効果とは扱わない。nonparticipating にも大きなネットワーク外部便益がある。同経路 nonparticipating でも短縮が残り、経路変更だけでは説明できない。収支均衡は厳密に確認された。金銭移転は役割方向と整合するが、FCFS 比時間便益に比べて小さい。局所取引短縮と FCFS 比最終総旅行時間差を混同しない。フリーライダー問題は直接取引層では顕著でないが、ネットワーク外部便益層では残る可能性がある。TVT 対象交差点付近の通過改善が同経路 nonparticipating 短縮の主因かは未確認である。複数 seed、OD・departure 調整、参加資格介入、VOT介入は将来課題である。今回を理由に 4方式統合回帰を復活させない。

本節の文書化では runner、production、output、CSV、JSON、Git を変更していない。次の直接作業は、利用者 Terminal で新節の見出し・重要数値・差分・書式を独立確認することである。その後、必要なら文書訂正、runner 2 本と Markdown 3 本の commit 可否判断、output を Git へ含めるかは別判断、commit 後に最新 commit と残存変更を確認する。push は別指示である。新しい simulation や局所介入実験へ自動的に進まない。

### 22.17 検索語

共通seed RNG後clearance 1、6×6ネットワーク、3000台、FCFS対TVT-MP再実行、平均総旅行時間、97.575秒、participating 2400、nonparticipating 600、VOT Spearman、Q5−Q1、BUYER_ONLY、SELLER_ONLY、BUYER_DOMINANT、SELLER_DOMINANT、BALANCED、NO_TRANSACTION、相互排他的役割区分、Top 20%、Top 10%、Top 5%、Top 1%、Top 1%全車buyer側、Top 1%平均総旅行時間533.875秒、Top 1%局所実現短縮11.9167秒、Top 1%平均支払5.7789円、Top 1%平均正味受取マイナス5.1094円、FCFS単独VOT相関なし、nonparticipating VOT相関なし、bootstrap参考値、並べ替え検定参考値、OD未調整、車両間相互作用、同経路nonparticipating、異経路nonparticipating、経路JSON正規化、外部便益、公式支払、公式補償、収支均衡、3173.109890768508円、time benefit、total benefit、局所実現短縮、baseline_minus_actual_passage_seconds、BUYER_ONLY 4282秒、平均12.028秒、平均支払3.471円、SELLER_ONLY平均遅延7.989秒、平均補償0.841円、trade-scope外部効果0.717秒、フリーライダー、ネットワーク外部効果、参加資格介入、VOT介入、99パーセンタイル10.793873103649728、単一seed、因果効果ではない、4方式統合回帰を復活させない

## 23. 共通seed／RNG後signalized UXsim再実行とFCFS・TVT-MP全体効率比較（2026-11-25）

TVT-MP の全体効率を FCFS だけでなく signalized UXsim とも比較し、研究上の位置づけを明確にする。FCFS 対 TVT-MP は同一 Vehicle、VOT、buyer／seller、金銭移転、nonparticipating 外部便益までの詳細比較である。signalized UXsim との比較は同じ詳細分析ではなく、同一 network・需要・seed 条件の全体効率比較である。TVT-MP は FCFS より全体効率が高い。ただし今回の正式 signalized UXsim 条件より全体効率が低く、signalized UXsim に劣る。全体効率だけで signalized UXsim の代替とは位置づけない。TVT-MP 固有の価値は VOT選別、seller補償、金銭移転、参加・非参加車への便益配分、外部便益にある。この不利な比較を明示した上で、FCFS詳細比較を位置づける。将来の BATCH 改修では signalized UXsim を上回る全体効率を研究目標とする。将来的には FCFS ベースの BATCH を baseline として TVT-MP 取引を組み合わせる BATCHベースTVT-MP を検討する。BATCH が signalized UXsim を上回ることは現時点では未達・未確認であり、達成済みとは書かない。単一seed、特定信号設定であり、一般化しない。4方式統合回帰を復活させない。

### 23.1 新規runnerと正式条件

新規 runner は `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_common_seed_rng.py`。基準は `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_awt_awwt_od_reference_validation.py`。scenario は `signalized_uxsim_6x6_grid_3000_vehicle_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3_signal_59_0_59_0`。output は `research_outputs/trial/signalized_uxsim_6x6_grid_3000_vehicle_common_seed_rng_departure_999_seed_0_demand_seed_42_vot_seed_1_cohort_seed_3_signal_59_0_59_0`。既存 runner、旧 signalized output、FCFS、TVT-MP、production は変更しない。旧保存結果との完全一致は合格条件にしない。共通seed／RNG後の FCFS・TVT-MP・signalized UXsim全体比較用に別 directory へ保存した。新規 output はローカル出力であり文書 commit へ自動包含しない。`research_scripts/route_choice_rng_diagnostic.py` とその他の無関係な未追跡 script・CSV・output には触れない。

条件は、6×6 network、3000台、departure T=0..999、traffic seed 0、demand seed 42、VOT seed 1、cohort seed 3、participating 比較用 cohort 2,400、nonparticipating 比較用 cohort 600。全車両の交通制御は signalized UXsim であり、cohort は比較用区分にすぎず、signalized UXsim に TVT 参加・非参加の制度差はない。`SIGNAL_SETTING = (59, 0, 59, 0)`（signal setting 59 0 59 0）、API cycle 118、effective phase durations `[60, 1, 60, 1]`、east-west signal group 0、north-south signal group 2、phase 1 と phase 3 は link 未割当の all-red equivalent、offset interval 29.5、offset 0 29.5 59 88.5（`[0.0, 29.5, 59.0, 88.5]`）、internal signalized Node 36、external unsignalized Node 24、order control used false、common-seed RNG production active true、saved-result equality comparison performed false。これは今回の正式な signalized UXsim 比較条件である。あらゆる信号条件、最適信号制御一般、他 network 一般を代表するとは断定しない。

### 23.2 static validation 自己検出不具合

初回 static validation は `RuntimeError: Static contract must not fix saved AWT values.` で停止した。source 全文に `REFERENCE_AWT`、`EXPECTED_AWT`、`EXPECTED_WORLD_T` を検索しており、検査コード自身の文字列を検出した。禁止定数が無くても失敗し得る。全文部分文字列検索を削除し、AST の module 直下 `ast.Assign` と `ast.AnnAssign` の代入先名だけを集め、禁止名への実在する module-level 代入があるときだけ停止するようにした。コメント、docstring、エラーメッセージ、検査用文字列による誤検出を防いだ。AWT／AWWT 恒等検査、simulation 本体、その他の static validation は変更していない。修正後は `py_compile` 成功、static validation 成功、新 output directory 未存在確認成功、`PRE_RUN_VALIDATION_STATUS=0`。

### 23.3 完走結果

signalized UXsim は正常完走した。exit status = 0、vehicles = 3,000、order control used = False、full completion = True、traffic clearance = True、final World.T = 2025、evaluation end timestep = 2024。signal setting = `[59, 0, 59, 0]`、API cycle length = 118、effective phase durations = `[60, 1, 60, 1]`、offset interval = 29.5、offset values = `[0, 29.5, 59, 88.5]`。AWT 353.473秒（353.473 s）、AWWT 348.7114914206239、Route-Conditional AWT 338.545秒（338.545 s）、Route-Conditional AWWT 333.62701197899923、平均detour 14.928秒（14.928 s）、VOT-weighted average detour = 15.084479441624135。participating cohort AWT = 353.46541666666667 s、AWWT = 351.3497355587132。nonparticipating cohort AWT = 353.50333333333333 s、AWWT = 338.15851486826585。exec_simulation seconds = 3.9692655000835657、network-wide evaluation seconds = 39.65598008292727、output write seconds = 0.08221795782446861、script total seconds = 58.38720687502064。formal output 生成成功。平均総旅行時間459.049秒（459.049000000000 s）。

### 23.4 正式AWWT定義

3 方式の Vehicle CSV から独立再集計した。正式AWWT定義は `AWWT = sum(weighted_od_based_waiting_time) / vehicle_count`、`Route-Conditional AWWT = sum(weighted_route_conditional_waiting_time) / vehicle_count`、`VOT-weighted average detour = sum(weighted_detour_time) / vehicle_count`。vehicle countで除算する。今回の vehicle_count は 3,000。`sum(VOT × waiting) / sum(VOT)` は正式定義ではない。VOT合計で除算しない。最初の独立集計で誤って VOT 合計を分母にした値を一度表示したが、直ちに訂正し、正式再集計で保存値と 1e-9 以内で一致した。誤正規化値不使用。研究結果・文書・比較に使わない。将来の再分析で同じ誤りを繰り返さない。

### 23.5 3方式の正式全体比較

全方式は 3000台、vehicle row 3,000、unique Vehicle 3,000、同じ平均 OD 最小自由流旅行時間 105.576 s、full completion、traffic clearance、共通seed／RNG後 production、Vehicle CSV から同一定義で独立再計算した。

| 方式 | 平均総旅行時間 s | AWT s | AWWT | Route-Conditional AWT s | Route-Conditional AWWT | 平均detour s | VOT加重平均detour |
|---|---:|---:|---:|---:|---:|---:|---:|
| FCFS | 680.497333333333 | 574.921333333333 | 570.605509688679 | 560.105333333333 | 556.215696107889 | 14.816 | 14.389813580790 |
| TVT-MP | 582.922000000000 | 477.346000000000 | 454.090301201753 | 464.130000000000 | 441.492878234901 | 13.216 | 12.597422966852 |
| signalized UXsim | 459.049000000000 | 353.473000000000 | 348.711491420623 | 338.545000000000 | 333.627011978999 | 14.928 | 15.084479441624 |

恒等 `平均総旅行時間 = AWT + 平均OD最小自由流旅行時間` を 3 方式で確認した。

### 23.6 方式間差、効率順位、detour

TVT-MP versus FCFS は平均総旅行時間短縮 97.575333333333 s、FCFS 比改善率 14.338826701256%（TVT-MP対FCFS 97.575秒14.34%）。signalized UXsim versus FCFS は 221.448333333333 s、32.542130951285%。signalized UXsim versus TVT-MP は 123.873000000000 s、21.250355965292%（signalized対TVT-MP 123.873秒21.25%）。AWT 差は共通の平均 OD 最小自由流旅行時間のため平均総旅行時間差と一致する。AWT 改善率は TVT-MP versus FCFS = 16.971945147278%、signalized versus FCFS = 38.518023335366%、signalized versus TVT-MP = 25.950358859192%。

旅行時間と waiting time は小さいほど高効率である。数値順位は `signalized UXsim < TVT-MP < FCFS`。効率順位は `signalized UXsim > TVT-MP > FCFS`（全体効率順位signalized UXsim TVT-MP FCFS）。今回の正式条件では signalized UXsim が TVT-MP を明確に上回り、TVT-MP が FCFS を上回った。次は断定しない。すべての信号設定が TVT-MP を上回ること、最適信号制御一般を測定したこと、他 network・他 seed・他需要でも同じ順位になること、単一seed の差が一般的な母平均であること。

平均 detour は TVT-MP 13.216 s、FCFS 14.816 s、signalized UXsim 14.928 s。VOT 加重平均 detour は TVT-MP 12.597422966852、FCFS 14.389813580790、signalized UXsim 15.084479441624。detour 単独では TVT-MP が最小である。detour 差は signalized UXsim の AWT・平均総旅行時間の大きな優位を覆さない。detour が小さいことだけで全体効率が高いとは判断しない。

### 23.7 役割分担、BATCH、判定

FCFS詳細比較は、TVT-MP の作用機序、同一 Vehicle の旅行時間差、VOT 別便益、buyer／seller の局所実現時間変化、支払・補償、nonparticipating 外部便益、同経路・異経路、フリーライダーを扱う。signalized全体比較は全体的な交通効率の位置づけであり、個車・buyer／seller・金銭の詳細対応は行わない。signalized UXsim には TVT 取引、VOT選別、seller補償がないため同じ役割分析を要求しない。

現時点の表現は次である。「TVT-MP は FCFS より全体効率が高いが、今回の正式 signalized UXsim 条件には劣る。したがって TVT-MP を全体効率だけで signalized UXsim の代替とは位置づけない。一方、TVT-MP は VOT による buyer 選別、seller への金銭補償、参加・非参加車への便益配分を扱う固有機能を持つ。signalized UXsim に劣る事実を明示した上で、FCFS との詳細比較によって TVT-MP の作用機序と分配効果を評価する。」

BATCH 改修後は FCFS、TVT-MP、signalized UXsim、BATCH の全体比較を想定する。BATCH目標は signalized UXsim超過目標、すなわち signalized UXsim を上回る全体効率である。現時点では未達・未確認であり、結果を先取りしない。BATCHベースTVT-MP は、現 TVT-MP が FCFS baseline に VOT 取引を重ねるのに対し、将来方式が BATCH baseline に VOT 取引を重ねる構想である。BATCH が効率的な基本順位を作り、その順位を baseline とし、VOT 取引で限定範囲の再配分、buyer の時間価値と seller の必要補償、BATCH の効率を大きく損なわない取引だけを採用する。未採用、未実装、未検証である。

総合判定は、共通seed／RNG後の 3 方式正式全体比較を完了したこと、全体効率順位が signalized UXsim > TVT-MP > FCFS であること、TVT-MP は FCFS より約 97.575 秒・14.34% 短いこと、signalized UXsim は TVT-MP より約 123.873 秒・21.25% 短いこと、TVT-MP は全体効率で signalized UXsim に劣ること、この不利な結果も明示すること、研究価値は全体効率だけでなく VOT選別・金銭補償・便益配分・外部効果にあること、FCFS とは詳細比較、signalized UXsim とは全体比較と役割を分けること、単一seed・特定信号設定・特定 network・需要であり一般化しないこと、BATCH 目標は未達・未確認、BATCHベースTVT-MP は将来構想であること、である。4方式統合回帰を復活させない。

本節の文書化では runner、production、output、CSV、JSON、Git を変更していない。次の直接作業は、利用者 Terminal で固定見出し、重要数値、AWWT 正式定義、誤正規化値を使っていないこと、signalized UXsim に TVT-MP が劣ることの明記、FCFS 詳細比較と signalized 全体比較の区別、BATCH 目標と BATCHベースTVT-MP の未実装、差分と書式、signalized runner の既存正本との差分を独立確認することである。その後、必要なら文書訂正、signalized runner 1 本と Markdown 3 本の commit 可否、output の Git 包含は別判断、commit 後に最新 commit と残存変更を確認する。push は別指示である。新しい simulation、BATCH 改修、BATCHベースTVT-MP へ自動的に進まない。

### 23.8 検索語

共通seed RNG後signalized UXsim、FCFS・TVT-MP・signalized UXsim全体比較、signal setting 59 0 59 0、API cycle 118、offset 0 29.5 59 88.5、3000台、平均総旅行時間459.049秒、AWT 353.473秒、AWWT 348.7114914206239、Route-Conditional AWT 338.545秒、Route-Conditional AWWT 333.62701197899923、平均detour 14.928秒、全体効率順位signalized UXsim TVT-MP FCFS、TVT-MP対FCFS 97.575秒14.34%、signalized対TVT-MP 123.873秒21.25%、正式AWWT定義、vehicle countで除算、VOT合計で除算しない、誤正規化値不使用、signalized UXsimに劣る、FCFS詳細比較、signalized全体比較、VOT選別、seller補償、外部便益、BATCH目標、signalized UXsim超過目標、BATCHベースTVT-MP、未採用、未実装、未検証、単一seed、特定信号設定、一般化しない、4方式統合回帰を復活させない

## 24. 共通seed／RNG後clearance=0三方式比較とTVT-MPのVOT加重配分性能（2026-11-29）

本節は、共通seed／RNG後の FCFS clearance=0、TVT-MP clearance=0、signalized UXsim `[59,59]` の正式再実行と横断比較、および nonparticipating 50% 相補割当の runner 準備を記録する。暫定モデルの探索結果であり、最終論文値ではない。解釈の詳細は設計ノート **§32.34**、進捗側は **§21.9.35**。既存の clearance=1 系比較（本ファイル **§23**）は変更しない。

**位置づけ。** FCFS と TVT-MP の clearance=0 は、方向変更後に次の timestep で通過可能、clearance timesteps = 0、clearance=1 より 1 timestep 短い、という意味である。clearance=0 は安全性または実装可能性の証明ではない。clearance による性能損失と、clearance 短縮時の性能ポテンシャルを見る感度条件である。signalized の対応条件は `[59,0,59,0]` ではなく `[59,59]`、all-red equivalent なし、API cycle 118、effective phase durations `[60,60]`、effective cycle 120、east-west group 0、north-south group 1、offset `[0,29.5,59,88.5]` である。FCFS／TVT-MP の clearance=0 と signalized `[59,59]` は同じ変数を変えた実験ではない。類似するのは、timestep 1 秒、1 Link から 1 timestep に進入できる車両は最大 1 台、他方向へ切り替える際に追加の空白 timestep を要求しないこと、同一 network・Vehicle plan・OD・departure・seed、全車完走と traffic clearance である。位置づけは「方向切替時に追加clearance timestepを要求しない類似の最小通過間隔条件下での方式比較」である。制御構造は異なる。FCFS は到着・物理条件に応じた逐次処理で、原則として早い順、固定長の方向別位相はない。TVT-MP はその逐次処理を基礎に VOT 取引で限定的に順位を再配分し、固定長の方向別位相はない。signalized `[59,59]` は固定二位相で、各方向群へ約 60 timestep ずつ通行権を交互に付与し、一方向を流す間は反対方向が待つ。到着状況に応じた方向切替ではない。今回の性能差は、この制御構造の相違を含む方式差として解釈する。signalized 一般の優劣とはしない。

**新規 runner。** 次の 3 本を新設した。既存 runner、production、既存 output は変更していない。新しい別 scenario・別 output directory を使い、旧保存交通結果との完全一致は合格条件にしていない。共通seed／RNG production が有効であることを確認した。

- FCFS clearance=0: `research_scripts/run_fcfs_6x6_grid_3000_vehicle_clearance_0_common_seed_rng.py`
- signalized `[59,59]`: `research_scripts/run_signalized_uxsim_6x6_grid_3000_vehicle_no_all_red_common_seed_rng.py`
- TVT-MP clearance=0: `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_clearance_0_common_seed_rng.py`

**共通比較条件。** 6×6、3,000 台、Link 長 200 m、自由流速度 60 km/h。Vehicle 名集合と Vehicle plan hash `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`、name／OD／departure、departure T=0..999、traffic seed 0、demand seed 42、VOT seed 1、cohort／nonparticipation seed 3、比較用 cohort 2,400／600、平均 OD 最小自由流旅行時間 105.576 秒、common-seed RNG production active、full completion、traffic clearance が三方式で一致する。signalized の cohort は比較用区分であり、TVT 制度上の参加差ではない。

**FCFS clearance=0。** 正常完走・監査済み。exit status 0、3,000 台、比較用 cohort 2,400／600、clearance timesteps 0、semantics は next timestep passage is allowed、full completion と traffic clearance は True、common-seed RNG active、saved-result equality comparison は False、formal output success。正式値は平均総旅行時間 125.756 秒、AWT 20.180 秒、AWWT 20.718790788876102、Route-Conditional AWT 19.284 秒、Route-Conditional AWWT 19.540619001244753、平均 detour 0.896 秒、VOT 加重平均 detour 1.178171787631352、平均 OD 最小自由流 105.576 秒、平均 actual-route 自由流 106.472 秒。Vehicle CSV は 3,000 行、名前一意 3,000、必須列欠損なし、保存値と独立再計算は 1e-9 以内、旅行時間恒等 residual 0。

**TVT-MP clearance=0。** 正常完走・監査済み。exit status 0、3,000 台、participating 2,400、nonparticipating 600、clearance timesteps 0、semantics は next timestep passage is allowed after direction change、candidate Visit 上限 10、hard deterministic mode False、final World.T 1184、full completion と traffic clearance は True。transaction count 2,465、transaction audit rows 2,465、Visit audit rows 5,522、buyer audit rows 2,636、seller audit rows 2,773、nonparticipating audit rows 113、actual arrival saved rows 5,522、FIFO violation total 0。common-seed RNG active、saved-result equality comparison は False、audit CSV validation passed、formal output success。正式値は平均総旅行時間 125.581 秒、AWT 20.005 秒、AWWT 18.971887076820874、Route-Conditional AWT 19.109 秒、Route-Conditional AWWT 17.89853971444065、平均 detour 0.896 秒、VOT 加重平均 detour 1.0733473623802254、平均 OD 最小自由流 105.576 秒、平均 actual-route 自由流 106.472 秒。Vehicle CSV は 3,000 行、名前一意 3,000、必須列欠損なし、保存値と独立再計算は 1e-9 以内、旅行時間恒等 residual 約 1.42e-14。今回監査した経済恒等は transaction audit 全体の `sum(G) - sum(R) = sum(surplus)`、residual 0、`sum(G) = 5837.434589073977`、`sum(R) = 823.6264983141591`、`sum(surplus) = 5013.808090759818` である。別定義の buyer 公式支払合計と seller 公式補償合計の一致は未確認のまま推測して追加しない。

**signalized UXsim `[59,59]`。** 正常完走・監査済み。exit status 0、3,000 台、比較用 cohort 2,400／600、signal setting `[59,59]`、API cycle 118、effective phase durations `[60,60]`、effective cycle 120、phase 数 2、east-west group 0、north-south group 1、all-red phase count 0、all-red equivalent なし、offset interval 29.5、offset values `[0,29.5,59,88.5]`、内部 signalized Node 36、外部 unsignalized Node 24、order control False、final World.T 2232、full completion と traffic clearance は True、common-seed RNG active、saved-result equality comparison は False。正式値は平均総旅行時間 533.430 秒、AWT 427.854 秒、AWWT 408.86320311644073、Route-Conditional AWT 413.238 秒、Route-Conditional AWWT 393.1320837428641、平均 detour 14.616 秒、VOT 加重平均 detour 15.731119373576625、平均 OD 最小自由流 105.576 秒、平均 actual-route 自由流 120.192 秒。Vehicle CSV は 3,000 行、名前一意 3,000、必須列欠損なし、保存値と独立再計算は 1e-9 以内、旅行時間恒等 residual 0。

**signalized runner と保存 output の世代差。** 初回正式 simulation は exit 0、必須 8 ファイル、完走、traffic clearance、独立再計算、恒等、信号契約を確認した。ただし初回生成済み `run_summary.txt` には文字列 `formal output success` がなかった。その後、新規 signalized `[59,59]` runner だけを修正し、成功パスの `summary_lines` 最終要素へ `formal output success` を追加し、run summary 構築構造を AST で検査する static validation を追加した。信号、network、simulation 本体、評価、出力 schema は変更していない。修正後は py_compile 成功、AST 構造監査成功、simulation 再実行なし、既存 output 変更なし。static validation 再実行は、既存 output directory を拒否する実行前契約により exit 1 となった。これは runner 修正の失敗ではなく、正式 run 後に output が存在するための想定された停止である。生成済み output は監査済み正式結果として維持する。修正後 runner と生成済み output の差は、run summary 末尾の成功行と対応 AST 契約だけである。

**正式 AWWT。** 三方式とも `AWWT = sum(weighted_od_based_waiting_time) / vehicle_count`、`Route-Conditional AWWT = sum(weighted_route_conditional_waiting_time) / vehicle_count`、`VOT-weighted average detour = sum(weighted_detour_time) / vehicle_count`。vehicle_count は 3,000。VOT 合計では除算しない。

**clearance=0 系比較表。** 数値が小さいほど高効率。

| 方式 | N | 平均総旅行時間 s | AWT s | AWWT | Route-Conditional AWT s | Route-Conditional AWWT | 平均detour s | VOT加重平均detour | 平均OD最小自由流 s | 平均actual-route自由流 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FCFS clearance=0 | 3000 | 125.756 | 20.180 | 20.718790788876102 | 19.284 | 19.540619001244753 | 0.896 | 1.178171787631352 | 105.576 | 106.472 |
| TVT-MP clearance=0 | 3000 | 125.581 | 20.005 | 18.971887076820874 | 19.109 | 17.89853971444065 | 0.896 | 1.0733473623802254 | 105.576 | 106.472 |
| signalized UXsim `[59,59]` | 3000 | 533.430 | 427.854 | 408.86320311644073 | 413.238 | 393.1320837428641 | 14.616 | 15.731119373576625 | 105.576 | 120.192 |

**方式間差。** TVT-MP versus FCFS の平均総旅行時間は TVT-MP − FCFS = −0.175 秒、saving 0.175 秒、FCFS 比改善率約 0.139%。AWT も −0.175 秒、FCFS 比約 0.866%。AWWT は −1.746903712055228、FCFS 比約 8.43%。signalized `[59,59]` versus FCFS の平均総旅行時間差は +407.674 秒で signalized の方が長く、改善ではなく大幅悪化。versus TVT-MP は +407.849 秒で signalized の方が長い。数値順位は `TVT-MP clearance=0 < FCFS clearance=0 << signalized [59,59]`。効率順位は `TVT-MP clearance=0 > FCFS clearance=0 >> signalized [59,59]`。ただし TVT-MP と FCFS の平均差は 0.175 秒、約 0.139% であり、ほぼ同等と解釈する。

**clearance=1 系からの感度。** 既知の clearance=1 正式値は、FCFS が平均総旅行時間 680.497333333333 秒、AWT 574.921333333333 秒、AWWT 570.605509688679。TVT-MP が 582.922 秒、477.346 秒、454.090301201753。signalized `[59,0,59,0]` が 459.049 秒、353.473 秒、348.7114914206239。FCFS は 680.497333333333 秒から 125.756 秒へ 554.741333333333 秒短縮、改善率約 81.52%、AWT 約 96.49%、AWWT 約 96.37%。TVT-MP は 582.922 秒から 125.581 秒へ 457.341 秒短縮、改善率約 78.45%、AWT 約 95.81%、AWWT 約 95.82%。signalized は `[59,0,59,0]` から `[59,59]` への信号設定差であり、459.049 秒から 533.430 秒へ 74.381 秒悪化、約 16.20% 悪化、AWT も 74.381 秒悪化、AWWT は約 60.152 悪化。同一 clearance パラメータの変更ではない。

**設計思想との関係。** TVT-MP の中心は平均交通効率の向上だけではない。高 VOT 車の優先機会、限られた待ち時間の VOT 再配分、buyer の対価、seller への補償、平均効率と VOT 加重効率の区別が中心である。clearance=1 では FCFS の AWT 574.921 秒に対し TVT-MP は AWT 477.346 秒、AWWT 454.090 であり、平均効率と VOT 加重効率の改善が同時に現れた。clearance=0 では FCFS の AWT が 20.180 秒で既に高効率、TVT-MP の AWT は 20.005 秒、平均総旅行時間差は 0.175 秒でほぼ同等、AWWT は 20.719 から 18.972 へ約 8.43% 改善した。現時点の記録は、「clearance=0 では FCFS が既に高効率であり、TVT-MP による平均交通効率の追加改善余地はほぼ消失した。一方、AWWT は約 8.43% 改善した。この結果は、TVT-MP の中心機能が交通処理能力の増強だけではなく、限られた待ち時間を VOT に応じて再配分することにあるという設計思想と整合的である。」および「今回の単一 run では、平均効率をほぼ損なわず、VOT 加重待ち時間を改善した。」である。一般に平均効率を損なわないこと、AWWT 改善の機序が VOT 選別だけであること、設計思想どおりの作動の証明、clearance=1 の改善が TVT-MP だけに起因すること、他 seed・network・投入モデルでの再現は断定しない。安全な表現は、設計思想と整合的、設計思想を支持する探索結果、機序は VOT 層別・役割別・複数 seed で追加確認が必要、である。

**signalized `[59,59]` の解釈。** all-red equivalent を除いた `[59,59]` は `[59,0,59,0]` の 459.049 秒より 533.430 秒へ 74.381 秒悪化した。「all-red equivalent を除けば必ず信号効率が上がる」とは言えない。追加の空白 timestep を置かない点は三方式で類似するが、signalized は固定二位相、FCFS／TVT-MP は逐次処理である。大差は固定方向別位相と逐次処理の差が現れた可能性がある。原因は確定しない。signalized 制御一般、最適固定信号、短 cycle、actuated、adaptive、Node 別 green split または offset 最適化、他 network・他需要へ一般化しない。

**言える範囲。** 今回の暫定モデル・単一 seed・同一 plan では、clearance=0 により FCFS と TVT-MP の絶対性能が大幅改善した。FCFS clearance=0 は AWT 約 20.18 秒で既に高効率。TVT-MP clearance=0 は FCFS と平均総旅行時間・AWT でほぼ同等。TVT-MP の AWWT は FCFS より約 8.43% 低い。平均効率をほぼ維持しながら VOT 加重効率を改善し、設計思想と整合的である。signalized `[59,59]` は今回の条件では FCFS／TVT-MP より大幅に遅い。direction-change clearance を置かない類似条件でも、固定二位相と逐次処理で大きな差が生じた。

**言えない範囲。** clearance=0 の安全性、実装可能性、TVT-MP の一般的優位、signalized 一般に対する優位、他 seed・他 network・新しい需要投入モデルでの再現、clearance だけが結果差の唯一原因、AWWT 改善が VOT 選別機序だけによること、因果効果、最終論文の主要推定値は断定しない。将来は少なくとも、車両投入間隔の指数分布化、OD 設定のランダム性と恣意性耐性の改善、BATCH 完成、正式な複数条件・複数 seed 評価を予定する。今回は本格実験前の情報収集・仮説形成・設計支援である。

**50% 相補割当の準備。** 新規 runner 2 本を作成済み。Pattern A は `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_nonparticipating_50_pattern_a.py`。Pattern B は `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_clearance_1_common_seed_rng_nonparticipating_50_pattern_b_complement.py`。共通条件は clearance=1、3,000 台、participating 1,500、nonparticipating 1,500、candidate Visit 上限 10、seed 0／42／1／3、同一 Vehicle plan・OD・departure・true VOT、common-seed RNG。Group は plan 順 3,000 名を `random.Random(3).shuffle` し、前半 1,500 が Group A、後半 1,500 が Group B。Pattern A は Group A participating・Group B nonparticipating。Pattern B はその逆。declared VOT は participating が true VOT、nonparticipating が None。固定するのは true VOT であり、declared VOT は label に従う。

事前監査の hash は、Vehicle plan `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`、true VOT assignment `6b56e754fcc34d6b9b877389e184289db6fbc50dc6e752aa06a6107463a35932`、Group A shuffle-order `eea09bc60090845150f497f7ab244c6d7b47ae1e495a6fb3b515496f1ab23503`、Group B shuffle-order `796dfbfc7ee5bdd62d13035670aa5e6838b519ee16f5a52f26b48d90a3f4918e`、Group A plan-order `07d8cc591f62cbae4e4ca1e663481d10009c663b11d53326ce68375b568fa53d`、Group B plan-order `bcac57de76b618058faa857959831752e55ee29193c52648ee51f15477db84ef`、complementary pair `2d0a8db67ab4b690c22a0b4a55ec41363d2b5d793b0bf0cd91652fe99163ca34`。両 runner の py_compile と static validation は成功、output directory は未存在、Group A／B 各 1,500、重複なし、欠落なし、全 3,000 台を被覆、plan と true VOT は 3,000 台で一致、group hash と pair hash は一致、A participating = B nonparticipating、A nonparticipating = B participating、全 3,000 台で label 反転、declared VOT は label に従い、failure count 0。この事前監査の時点では simulation 未実行、Git 操作なし。shuffle-order hash は分割手順の再現性、plan-order hash は集合メンバーと A participating／B nonparticipating の対応を確認する。評価できるのは参加率 50% に固定した参加者構成感度、相補的参加割当に対する network 結果、どの Vehicle 集合が参加するか、OD・departure・true VOT が結び付いた構成差である。OD だけ、departure だけ、VOT だけ、個車の独立な参加因果、自発的参加率の均衡、他 seed への一般化は評価できない。「OD と departure だけを交換した実験」とは書かない。

**現在地。** clearance=0 系は FCFS、signalized `[59,59]`、TVT-MP が完走・監査済みで、三方式の独立再集計と比較条件監査が済み、正本へ文書化している。50% 相補割当は Pattern A／B の runner 作成と事前監査が済み、Pattern A は別の macOS Terminal で長時間 simulation 実行中、Pattern B は未実行、Pattern A の結果は未確認・未記録である。Pattern B は Pattern A 完走・監査後に実行し、片方だけで比較を確定しない。80% nonparticipating は未着手。

**次の直接作業。** 現在実行中の Pattern A が完走したあと、Cursor で Pattern A output の事後監査を行う。合格した場合だけ Pattern B を長時間実行し、完走後に事後監査、output 間の補集合契約の再確認、2 pattern 比較のあと、nonparticipating 80% へ進むかを判断する。現在は Pattern B 実行、80% runner 作成、新しい clearance simulation、BATCH 改修、4 方式統合回帰の復活、Pattern A 結果の推測、clearance=0 の追加詳細分解を行わない。

**Git。** branch は `feature/common-seed-rng-foundation`。利用者が示した最新 push 済み commit は `b1f60c6cde4c241cca5a2825e4d570496617331b`。今回の新規 runner は未 commit である。少なくとも FCFS clearance=0、signalized `[59,59]`、TVT-MP clearance=0、Pattern A、Pattern B の各 runner と、今回の各 output directory は未追跡である。既存 tracked 変更 `research_scripts/route_choice_rng_diagnostic.py`、および大量の既存未追跡 CSV、script、output、`diagnostics/order_control.zip`、`g_0_0` には触れない。Git 操作は利用者が Terminal で行う。本節の文書作成では Git 操作をしていない。

**検索語:** 共通seed RNG後clearance 0、FCFS clearance 0、TVT-MP clearance 0、signalized UXsim 59 59、方向変更後次timestep通過、追加clearanceなし、類似最小通過間隔、固定二位相、逐次処理、平均総旅行時間125.756秒、平均総旅行時間125.581秒、AWT 20.180秒、AWT 20.005秒、AWWT 20.718790788876102、AWWT 18.971887076820874、AWWT 8.43%改善、平均効率ほぼ同等、VOT加重効率、TVT-MP設計思想、平均効率をほぼ維持、待ち時間再配分、signalized 533.430秒、signalized 59 59悪化、all-redなし、signalized一般へ一般化しない、clearance 0安全性未証明、暫定モデル、指数分布投入予定、ODランダム性改善予定、50%相補割当、Pattern A、Pattern B complement、Group A、Group B、shuffle順hash、plan順hash、true VOT固定、declared VOT label依存、全3000台label反転、参加者構成感度、個車因果効果ではない、Pattern A実行中、Pattern B未実行、80%未着手
