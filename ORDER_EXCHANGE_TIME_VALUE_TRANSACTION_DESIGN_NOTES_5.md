# TVT-MP 時間価値取引型交差点管理 詳細設計メモ 第5巻

作成日: 2026-10-08

## 1. 本文書の位置づけ

本書は、TVT-MPの内部実装設計に関する詳細設計メモ第5巻である。

第1巻から第4巻は、TVT-MPの設計、実装、検証、変更経緯を記録した歴史的設計文書として維持する。

第4巻までに確定した既存契約は、利用者による新しい設計判断または原典確認に基づく明示的な変更がない限り覆さない。

本書は、第4巻末尾の次の節から継続する。

- 「Vehicle summary tableの重複列整理と第5巻への移行（2026-10-08）」

本書は、初期小規模trial以後に発見された追加不具合、研究出力schema変更、正式実験前の実装改善、および今後の追加実装設計の正本とする。

過去の設計を変更する場合は、過去記述を削除または書換えず、次を新しい節へ明記する。

- 変更対象となる旧契約
- 変更が必要になった観察事実
- 原因
- 新しい正式契約
- 変更しない既存契約
- 実装影響
- テスト契約
- 過去記述の最新参照先

## 2. 他文書との役割分担

### 第1巻から第4巻

- 過去の詳細設計と実装経緯
- 当時の確定事項
- 歴史的記録
- 第4巻末尾までの最新契約

### 第5巻

- 初期小規模trial以後の新しい内部実装設計
- trialで発見された追加不具合
- 研究出力schemaの変更
- 正式実験前の追加設計
- 第4巻までの契約を変更する場合の最新正本

### TVT_MP_EXPERIMENT_DESIGN_NOTES.md

- 実験条件
- 研究ネットワーク
- 需要
- VOT
- seed
- trial条件
- 正式実験条件
- 実験結果と観察事実
- 実験出力の保存方針

### ORDER_EXCHANGE_PROGRESS_3.md

- 作業工程
- 現在地
- BLOCKER
- 正本の案内
- Git状態
- 次の再開地点

実験の結果から実装変更が必要になった場合は、実験設計メモに観察事実を記録し、第5巻に原因、正式契約、修正仕様、テスト契約を記録し、進捗第3巻へ現在地を記録する。

## 3. 第5巻開始時点の状態

第5巻開始時点では、初期小規模trialは次の状態まで到達している。

- 2流入1流出の単車線合流
- 車両10台
- participating 8台
- nonparticipating 2台
- 評価期間T=0からT=299
- internal TSIZE 330
- baseline horizon 30
- candidate Visit数上限10
- 全車両がtrip完了
- World.Tは300
- evaluation end検査はすべて成功
- 成立取引は2件
- 2件ともEX_POST_FEASIBLE
- buyer 2件はいずれも個人事後評価でSATISFIED
- 研究出力5表とtrial補助3ファイルを生成済み

trial実行過程で、次の追加不具合を発見し、修正または修正設計を行った。

### participation mapping母集団不足

- 意思決定窓内Visitだけをmappingしていた
- candidate集合が意思決定窓外Visitを含み得た
- mappingをalignment済みresolved undetermined Visit全件へ拡張した
- 意思決定窓、candidate集合、leading nonparticipating契約は変更していない

### binding transferのroute_next_link属性未作成

- binding Visitにはbaseline由来の正式進路が保存済みだった
- local Vehicleのroute_next_link属性が未作成で直接参照が失敗した
- 属性未作成をNone相当として扱うよう修正した
- 実際の通過先は引き続きbinding Visitの正式進路である
- route_next_link_choiceは呼ばない

### outlink boundaryの不要なroute_next_link保存

- outlink boundary処理はroute_next_linkを進路判断に使用しない
- Vehicle.end_tripもroute_next_linkを変更しない
- snapshotとrestoreから不要なroute_next_link保存・復元を削除した

### trial scriptのWorld.T表示

- シミュレーションと出力生成は成功していた
- 最後の画面表示へworld_tを渡していなかった
- verify_evaluation_endの返却値へworld_tを追加した

## 4. Vehicle summary tableの最新schema変更

第4巻末尾の最新契約に従い、次を実装予定とする。

- Vehicle表のtransaction_countを維持する
- Vehicle表のtrade_scope_visit_countを削除する
- Transaction表のtrade_scope_visit_countは維持する
- tvt_mp_vehicles.csvからtrade_scope_visit_count列を削除する
- 不成立候補を含む本来のtrade scope回数は、現時点では新設しない

この変更の詳細な理由、調査結果、実装対象、テスト契約は、第4巻末尾の次の節を正本とする。

- 「Vehicle summary tableの重複列整理と第5巻への移行（2026-10-08）」

## 5. 第5巻開始時点の次の直接作業

次の直接作業は、第5巻の新設確認後、進捗第3巻へ次を記録することである。

- 第4巻の主要設計追記を終了したこと
- 第5巻を新しい内部実装設計の正本として新設したこと
- Vehicle表schema変更の実装前設計が第4巻末尾にあること
- 現在の未コミット本番修正とテスト修正
- trial完走
- 次の実装対象
- 最新再開地点

その後、文書をTerminalで独立確認する。

CursorはGit操作を行わない。

diagnostics/order_control.zipには触れない。

# 初期小規模trial修正・Vehicle表schema変更の実装結果（2026-10-08）

## 1. participation mapping母集団修正

変更対象:

- `uxsim/order_control_tvt_mp_driver.py`
- private helper `_build_participation_mapping`

実装結果:

- 意思決定窓によるmapping除外を削除した
- alignment済み`resolved_undetermined_visits`全件をmappingへ登録するよう変更した
- 参加情報は引き続き`_read_participation`から取得する
- declared VOTを参加判定へ使用しない
- VOT 0を不参加扱いしない
- 欠落をTrueまたはFalseとして推測しない
- 意思決定窓、candidate集合、leading nonparticipating、right-of-entryの契約は変更していない

テスト:

- 既存driver mappingテストを新しい母集団へ更新した
- 意思決定時点TのVisitとT+7のVisitもmappingへ含むことを確認した
- driver専用テスト31件成功
- 関連するcandidate Visit set、leading nonparticipating、concrete buyerテスト117件成功

## 2. binding transferのroute_next_link属性未作成修正

変更対象:

- `uxsim/order_control_tvt_mp_candidate_binding_transfer.py`

原因:

- binding Visitにはbaseline由来の正式な`route_next_link_name`が存在した
- local Vehicleの`route_next_link`属性が未作成の場合、直接参照が`AttributeError`になった

実装結果:

- 直接参照を`getattr(local_vehicle, "route_next_link", None)`へ変更した
- 属性未作成と値Noneを、正式進路との不一致検査では同じ状態として扱う
- 実際の通過先は引き続きbinding Visitの正式進路である
- `route_next_link_choice()`は呼ばない
- local Vehicleが別outlinkを明示している場合の`RuntimeError`は維持した

回帰テスト:

- `test_missing_route_next_link_attribute_uses_formal_binding_route`
- 属性を明示的に削除したVehicleが、binding Visitの正式進路へ通過することを確認した
- binding transferテスト16件成功

## 3. outlink boundaryの不要なroute_next_link保存削除

変更対象:

- `uxsim/order_control_tvt_mp_candidate_outlink_boundary.py`

確認結果:

- outlink boundary処理は`route_next_link`を進路判断に使用しない
- `Vehicle.end_trip()`も`route_next_link`を変更しない
- したがって、処理前状態への保存と失敗時の復元は不要だった

実装結果:

- `_snapshot_outlink`から`route_next_link`保存を削除した
- `_restore_outlink_snapshot`から`route_next_link`代入を削除した
- 属性未作成をNoneとして保存する方法は採用しなかった
- 処理前に存在しなかった属性を復元時に新設しない

回帰テスト:

- `test_missing_route_next_link_attribute_does_not_block_outlink_boundary_processing`
- 属性未作成Vehicleでも観測流出処理が完了することを確認した
- 処理後も不要な`route_next_link`属性を新設しないことを確認した
- outlink boundaryテスト22件成功

## 4. Vehicle summary tableのschema変更

変更対象:

- `uxsim/order_control_tvt_mp_research_output.py`
- `tests_order_control_tvt_mp_research_output.py`

実装結果:

- `OrderControlTvtMpResearchOutputVehicleRow`から`trade_scope_visit_count`を削除した
- `_build_vehicle_rows`から同列の代入を削除した
- Vehicle表の`transaction_count`を維持した
- `_distinct_transaction_count_for_vehicle`を維持した
- Transaction表の`trade_scope_visit_count`を維持した
- 代替列は追加していない

CSV契約:

- 最新の`tvt_mp_vehicles.csv`には`trade_scope_visit_count`が存在しない
- `transaction_count`は存在する
- `tvt_mp_transactions.csv`には`trade_scope_visit_count`が存在する
- Vehicle表だけを変更し、Visit表、Transaction表、Node表、Scenario表は変更していない

テスト:

- Vehicle表の旧assertionを2件削除した
- `transaction_count == 2`の期待は維持した
- assigned-only Vehicleの`assigned_visit_count == 1`の期待は維持した
- 研究出力テスト37件成功
- actual passage、individual ex-post evaluation、research outputの関連テスト251件成功

## 5. trial scriptの修正

変更対象:

- `research_scripts/run_tvt_mp_small_scale_initial.py`

### World.T表示

- `verify_evaluation_end()`の返却辞書へ`"world_t": world.T`を追加した
- evaluation end検査内容は変更していない
- 最後のconsole summaryで`World.T = 300`を表示できるようになった

### 計時記録

問題:

- `manifest.json`と`run_summary.txt`を書いた後で、`trial_auxiliary_write`と`script_total`を確定していた
- そのため保存済みファイルでは両値が0になっていた

修正:

- 補助ファイルの初回保存後に計時値を確定する
- 確定後、`manifest.json`と`run_summary.txt`だけを再保存する
- `vehicle_vot.csv`と研究用CSVは再保存しない
- 追加の計時fieldは作成していない
- 最後のメタデータ再保存時間は、確定済み計時値へ再算入しない

確認結果:

- `trial_auxiliary_write = 0.0006`秒
- `script_total = 22.6735`秒
- 保存済み`run_summary.txt`へ非ゼロ値が記録された

## 6. 最新schemaでのtrial再実行

出力directory:

- `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2`

結果:

- 全10台がtrip完了
- `World.T = 300`
- evaluation end検査はすべて成功
- TVT-MP driver呼出回数は設定上300回
- 成立取引2件
- T=14およびT=18
- 2件とも`EX_POST_FEASIBLE`
- buyer 2件はいずれも個人事後評価で`SATISFIED`
- 研究出力5表と補助3ファイルを生成した
- console summaryまで正常終了した

最新Vehicle CSV headerでは、

- `transaction_count`を確認した
- `trade_scope_visit_count`が存在しないことを確認した

最新Transaction CSV headerでは、

- `trade_scope_visit_count`が維持されていることを確認した

## 7. 最終回帰確認

次を実行した。

```text
python -m pytest tests_order_control_tvt_mp*.py -q --tb=short
```

結果:

```text
1312 passed in 42.61s
```

- 失敗0件
- TVT-MP関連テスト全体が成功した
- 過去に個別実行したテスト件数との重複合算は行わない
- 1,312件を現時点の最終一括回帰結果とする

## 8. 変更しない契約

今回の修正で、次は変更していない。

- 意思決定窓
- candidate集合
- leading nonparticipating
- right-of-entry
- formal route
- buyer、seller、nonparticipatingの役割契約
- 金銭精算
- 0円取引記録
- trade ex-post evaluation
- individual satisfaction
- 順位台帳
- 実通過履歴
- evaluation end
- Transaction表のtrade scope件数
- trialのネットワーク、需要、VOT、seed、horizon

## 9. 現在のBLOCKER

- 初期小規模trialの完走に対するBLOCKERはない
- 発見済みの本番不具合は修正・回帰済み
- Vehicle schema変更も実装・テスト・出力確認済み
- trial計時記録問題も修正・再出力確認済み

正式実験条件の未確定事項は、実装BLOCKERではなく実験設計上の今後の判断事項である。

## 10. 最新再開地点

- 本節への記録完了
- 回帰テスト完了
- TVT-MP関連一括回帰1,312件成功
- 最新schemaでtrial完走
- 最新Vehicle CSVとTransaction CSVのheader確認済み
- 保存済み計時値確認済み

次の直接作業は、実験設計メモと進捗第3巻へ、実装・回帰・最新trial確認結果を反映することである。

その後、変更対象と出力保存方針を確認し、コミット対象を整理する。

Git操作は利用者がTerminalで行う。

`diagnostics/order_control.zip`には触れない。

# TVT-MP意思決定過程の診断方式と監査用ネットワーク構想（2026-10-09）

**2026-10-09更新注記:** 本節は、診断方式と監査用ネットワーク構想を記録した時点の歴史的記録として維持する。wrapper方式、非干渉契約、出力4ファイル、候補段階の分離、選択理由の監査、将来の4交差点監査用ネットワーク構想は、引き続き有用な診断設計である。診断scriptは実際に作成・実行された。診断の詳細化により、TVT順位適用baseline forkの順位未確定Visitが通常合流で選択される問題を発見した。問題は、その通過試行方式に限定する。generic baseline fork、real World、candidate local virtual calculationは今回の問題ではない。

本節の次の記載を、現在の再開指示として読まない。「本番コード変更なし」「既存テスト変更なし」「次の直接作業は新規診断scriptの実装前設計または実装」「本番処理結果が既存trialと一致することをそのまま確認する」記載。最新契約では、本番コード修正後にtrialを再実行し、baseline通過時刻、candidate通過時刻、`G`、`R`、surplus、取引成立、支払・補償、実通過結果を再評価する。最新正本は詳細設計第4巻末尾の「TVT順位適用baseline forkの順位未確定Visit通過契約の変更（2026-10-09）」。最新進捗は進捗第3巻末尾の「TVT順位適用baseline forkの順位未確定Visit契約変更を採用（2026-10-09）」。T=13、T=14、T=18、T=21の取引成立・不成立を、現時点で交通上妥当と結論づけない。未追跡の診断scriptにはbaseline詳細を追加する途中変更があり、Node全体の順位とcandidate local rankを混同しない修正が必要である。新しいbaseline契約が実装されるまで、診断scriptの追加修正と再実行を停止している。生成済み診断出力は暫定結果である。通過試行契約は既存FCFSと同じ考え方を採用するが、実装共通化は未確定である。現在の次の直接作業は、既存FCFSコードとTVT順位適用baseline forkへの適用可能性の読み取り専用調査である。

## 1. 診断の目的

- 初期小規模trialは評価終了まで完走し、研究出力も正常に生成できた
- ただし、完走したことだけでは、TVT-MPの候補形成、候補別評価、最終候補選択が正しかったことを確認したことにはならない
- 現時点では、車両がどのように流れ、どの候補が形成され、各候補がどのように評価され、なぜ最終候補が選ばれたかを、人間が一連の流れとして確認できていない
- 正式実験へ進む前に、簡素なネットワークでTVT-MPの意思決定過程を監査する
- 監査の目的は、多数の体系的シナリオを網羅することではない
- 簡素なネットワーク上で、VehicleのOD、出発時刻、参加属性、VOTなどを柔軟に変更し、TVT-MPの処理が正式契約どおりかを人間が追跡することが目的である
- Vehicleの走らせ方は試行的・探索的でよい
- 一方、各試行で確認する項目は固定し、候補形成から実通過までを同じ観点で検証する

## 2. 最初に監査するネットワーク

最初の診断では、新しい複雑なネットワークを作らず、既に完走した次の初期小規模trialを再利用する。

- 2流入1流出
- 単車線合流
- 対象Nodeは1つ
- Vehicleは10台
- participatingは8台
- nonparticipatingは2台
- 評価期間はT=0からT=299
- internal TSIZEは330
- baseline horizonは30
- candidate Visit数上限は10
- 交通seedは0
- VOT seedは1
- 成立取引はT=14とT=18の2件

最初にこの条件を使う理由:

- 既に完走結果がある
- 研究出力と事後評価結果がある
- 取引成立時刻が既知である
- 0円取引と正の支払を伴う取引の両方が含まれる
- 最終的な成立取引と実通過結果を、診断結果と照合できる
- 新ネットワーク固有の問題と診断方式の問題を混同せずに済む
- 診断方法を確立してから、将来の4交差点ネットワークへ転用できる

T=14とT=18だけを事前指定して捕捉する方式は採用しない。

全意思決定timestepを監視し、候補形成時刻を既存resultから自動的に識別する。

## 3. 読み取り専用調査の結論

読み取り専用調査により、次を確認した。

- TVT-MP driverは、候補形成から最終適用までの各段階で、結果オブジェクトを順番に作成している
- 各段階のresultは、後段resultから前段resultへ参照を辿れる構造になっている
- 候補形成、FIFO検査、候補別局所仮想計算、経済評価、最終選択、支払・補償、最終順位の情報は、driver処理中には取得可能である
- 通常の`World.exec_simulation()`は、各timestepで`run_tvt_mp_driver(W)`を呼ぶが、その戻り値を保存せず捨てている
- 情報が計算されていないのではなく、通常simulation経路ではdriver戻り値を利用していない
- したがって、本番コードへ恒久的な診断registryやCSV出力を追加しなくても、診断用script側で戻り値を捕捉できる

## 4. 本番コードを変更しない方針

診断目的のために、次は変更しない。

- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_driver.py`
- その他のTVT-MP本番コード
- 本番研究出力schema
- World上の恒久registry
- Vehicle上の恒久診断属性
- 通常の正式実験経路

本番コードへ次の仕組みは追加しない。

- 全候補の恒久保存
- 毎timestepの詳細診断ログ
- 診断CSVの直接書出し
- candidate local Worldの保持
- liveな統括stateの保持
- 正式実験でも動作する診断callback
- 通常実行時の候補詳細コピー

理由:

- 正式実験の処理時間とメモリ使用量を増加させない
- 本番コードを診断目的で複雑化しない
- 交通制御処理と診断出力処理を分離する
- 診断用scriptを実行しない通常simulationには影響を与えない

## 5. 既存trial scriptを変更しない方針

次の既存scriptは変更しない。

- `research_scripts/run_tvt_mp_small_scale_initial.py`

同scriptは、moduleとしてimportした場合に`main()`が自動実行されないことを確認した。

末尾の`if __name__ == "__main__":`により、次はmodule import時に実行されない。

- directory作成
- 出力directory存在確認
- World構築
- Vehicle追加
- simulation
- CSV生成
- 補助ファイル生成

診断用scriptは既存trial scriptの`main()`を呼ばない。

次の関数と定数を再利用する。

- trial条件を定義する定数
- `VEHICLE_SPECS`
- `generate_vehicle_vots`
- `build_vehicle_vot_records`
- `build_world_and_network`
- `add_vehicles_to_world`
- `verify_evaluation_end`
- 評価期間、horizon、seed、Link長、自由流速度等の既存設定

既存trial scriptの`TRIAL_OUTPUT_DIR`は使用しない。

## 6. driver wrapperによる捕捉方式

診断用scriptで、次のmodule属性を一時的にwrapperへ差し替える。

- `uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver`

`World.exec_simulation()`はsimulation loop開始前にlocal importを行うため、`world.exec_simulation()`を呼ぶ前にmodule属性を差し替えれば、既存UXsim処理はwrapperを取得する。

wrapperの正式契約:

1. 元の`run_tvt_mp_driver(real_W)`を1回だけ呼ぶ
2. 元driverが返したresultを診断用の単純値へ変換する
3. 元driverと同じresultオブジェクトをそのまま返す
4. World、Vehicle、Link、Node、順位台帳、registry、RNGへ代入しない
5. resultを変更しない
6. driverを二重実行しない
7. driverの呼出時刻を変更しない
8. simulation終了後に元のmodule属性へ戻す

概念的な処理順:

    original_run_tvt_mp_driver = driver_module.run_tvt_mp_driver

    def diagnostic_run_tvt_mp_driver(real_W):
        result = original_run_tvt_mp_driver(real_W)
        extract_plain_diagnostic_values(real_W.T, result)
        return result

    driver_module.run_tvt_mp_driver = diagnostic_run_tvt_mp_driver

    try:
        world.exec_simulation()
    finally:
        driver_module.run_tvt_mp_driver = original_run_tvt_mp_driver

`try/finally`を必須とする。

simulationまたは診断変換で例外が発生した場合でも、元のdriver関数を必ず復元する。

差替え対象は`uxsim.order_control_tvt_mp_driver.run_tvt_mp_driver`だけとする。

`uxsim.py`側や別moduleの参照を追加で差し替えない。

## 7. 本番処理への非干渉契約

診断wrapperは次を変更しない。

- driver呼出回数
- driver呼出timestep
- baseline fork
- candidate Visit集合
- right-of-entry
- concrete buyer候補形成
- general trade rank
- FIFO検査
- candidate local仮想計算
- 経済評価
- 候補選択
- local RNG
- 支払・補償
- 最終順位
- atomic apply
- World更新
- evaluation end
- research output

wrapperは元driver実行後にresultを読み取る。

診断用の選択理由導出では、乱数を再実行しない。

結果に記録された選択候補と`rng_was_used`を使用する。

診断用値変換は、result内のtuple、dataclass、記録用dictを読み取るだけとし、既存containerへ要素を追加・削除しない。

## 8. driver resultの正式な参照連鎖

`OrderControlTvtMpDriverResult.atomic_apply_set_result`が`None`でない場合、次の参照連鎖から各段階を取得できる。

    result.atomic_apply_set_result
      .final_consistency_validation_set_result
        .final_rank_set_result
          .payment_and_compensation_set_result
            .candidate_selection_set_result
              .economic_evaluation_set_result
                .local_virtual_calculation_set_result
                  .fifo_inspection_set_result
                    .general_trade_rank_set_result
                      .concrete_buyer_candidate_set_result
                        .inlink_candidate_physical_order_result
                          .candidate_visit_set_result
                            .right_of_entry_selection_result
                              .leading_confirmation_result
                                .arrived_confirmation_result
                                  .alignment_fork_result
                                    .fork_result

各段階の主要なNode別結果:

- final rank:
  `node_final_rank_results`
- payment and compensation:
  `node_payment_and_compensation_results`
- candidate selection:
  `node_candidate_selection_results`
- economic evaluation:
  `node_economic_evaluation_results`
- local virtual calculation:
  `node_local_virtual_calculation_results`
- FIFO inspection:
  `node_fifo_inspection_results`
- general trade rank:
  `node_trade_rank_results`
- concrete buyer candidate set:
  `node_concrete_buyer_candidate_set_results`
- candidate Visit set:
  `node_candidate_set_results`

候補identityは、対象Node名と`buyers_sorted`の組合せとして扱う。

同じNode内では、`buyers_sorted`が候補を識別する正式な列である。

## 9. 取得できる情報

### 意思決定と候補形成前

- 意思決定timestep
- 対象Node
- candidate Visit setの`build_status`
- right-of-entry Visit
- right-of-entryのbaseline passage timestep
- candidate Visit集合
- candidate Visit数
- candidate VisitごとのVisitKey
- vehicle ID
- inlink名
- baseline arrival timestep
- arrival tiebreaker
- baseline passage timestep
- route next link名

### concrete buyer候補

- 全`concrete_buyer_candidate_sets`
- 各候補の`buyers_sorted`
- inlinkごとのbuyer prefix
- build status

### general trade rank

- buyers
- sellers
- nonparticipating Visits
- last buyer rank
- trade scope
- trade order
- Visitごとのtrade rank

### FIFO検査

- 全候補のFIFO TrueまたはFalse
- FIFO False候補が局所仮想計算へ進まなかったこと
- FIFO Falseは経済的不成立と区別して記録する

### candidate local仮想計算

FIFO True候補について、次を取得できる。

- resolved
- unresolved
- stop reason
- unresolved reasons
- required passage records
- traffic observation records
- baseline passage timestep
- candidate passage timestep
- 仮想timestepごとの結果
- 最終交通状態の凍結記録
- economic required passages完了時刻
- all trade scope passages完了時刻

### 経済評価

resolved候補について、次を取得できる。

- buyerごとのVisitKey
- declared VOT
- baseline passage timestep
- candidate passage timestep
- expected time saving
- gross time value `G_b`
- sellerごとのVisitKey
- declared VOT
- baseline passage timestep
- candidate passage timestep
- expected waiting increase
- required compensation `R_s`
- total buyer value `G`
- total required compensation `R`
- surplus
- economically feasible
- infeasibility reasons

### 最終選択

- selection status
- selected candidate
- `rng_was_used`
- selected candidateのidentity
- 候補なし
- 全候補経済的不成立
- 最大surplusによる選択
- buyer数による第2順位比較
- 最終同率時のlocal RNG選択

### 選択後

- buyerごとの支払額
- sellerごとの補償額
- final rank status
- 最終確定Visit
- final local rank
- formal route
- finalization source
- selected candidate由来かbaseline由来か

## 10. 候補段階を混同しない契約

次の件数と状態を別々に記録する。

- candidate Visit集合が形成されたか
- concrete buyer候補が形成されたか
- general trade rank候補が形成されたか
- FIFO True候補が何件か
- FIFO False候補が何件か
- resolved候補が何件か
- unresolved候補が何件か
- 経済評価対象候補が何件か
- economically feasible候補が何件か
- 最終選択候補があるか

次を混同しない。

- candidate Visitなし
- right-of-entryなし
- baseline情報不足
- concrete buyer候補なし
- FIFO違反
- local仮想計算未解決
- buyer非正価値
- buyer価値合計が必要補償未満
- 経済的成立候補なし
- 成立候補間の比較で非選択
- 最終同率抽選で非選択

## 11. 捕捉するtimestep

`decision_summary.csv`には、T=0からT=299まで、全300 timestepについて対象Nodeごとの概要を記録する。

候補なしtimestepも省略しない。

理由:

- candidateが作られなかった理由を確認できる
- right-of-entryなしと情報不足を区別できる
- 候補形成開始時刻を確認できる
- 同じVisitが繰り返し不要に評価されていないか確認できる
- T=14とT=18を事前に知っていることへ依存しない

候補明細は、candidate Visit集合またはconcrete buyer候補が存在するtimestepだけ記録する。

300件のdriver resultオブジェクト自体はリストへ保存しない。

各wrapper呼出中に、必要情報を文字列、数値、bool、None、list、tuple、dictなどの診断用単純値へ変換し、元resultへの参照を残さない。

## 12. live object保持に関する確認

次を原典確認した。

- `OrderControlTvtMpDriverResult`はlive traffic objectを保持しない
- `OrderControlTvtMpCandidateLocalVirtualCalculationResult`はlive local Worldやlive traffic objectを保持しない
- candidate local最終結果は、名前、VisitKey、時刻、数値等の独立したfrozen記録を保持する
- `OrderControlBaselineForkResult`はfork Worldを保持しない
- `OrderControlBaselineCollector`はfork Worldへの参照を保持しない
- baseline collectorはVehicleオブジェクトではなく、Vehicle名、Vehicle ID、Node名、Link名、Visit ID、時刻等の記録を保持する
- mutableな準備stateにはreal Worldとfork Worldが存在するが、最終fork resultへは保持されない

したがって、既存resultは診断に利用可能である。

ただし、不要な参照連鎖とメモリ消費を避けるため、driver result自体を長期保持せず、その場で単純値へ変換する方針を採用する。

## 13. 選択理由の診断用導出

選択理由は本番resultへ文章として保存されていない。

診断用scriptで、既存の全経済評価結果、selected candidate、`rng_was_used`から次を導出する。

### `no_economically_feasible_candidate`

- selection statusが`NO_ECONOMICALLY_FEASIBLE_CANDIDATE`
- selected candidateがNone
- economically feasible候補が0件

### `unique_maximum_surplus`

- selection statusが`SELECTED`
- `rng_was_used`がFalse
- economically feasible候補のうち、最大surplus候補が1件

### `maximum_surplus_then_unique_maximum_buyer_count`

- selection statusが`SELECTED`
- `rng_was_used`がFalse
- 最大surplus候補が複数
- その中で最大buyer数の候補が1件

### `final_tie_resolved_by_local_rng`

- selection statusが`SELECTED`
- `rng_was_used`がTrue
- 最大surplusかつ最大buyer数の候補が複数

診断用scriptはlocal RNGを再実行しない。

既存resultに保存されたselected candidateを正式結果として使用する。

浮動小数点比較は、本番選択処理と同じ完全比較を前提とする。

診断側で独自Toleranceを導入しない。

## 14. 診断用script

新規作成予定のscript名:

- `research_scripts/diagnose_tvt_mp_small_scale_initial_decision_trace.py`

このscript 1ファイルだけを新設する。

本番コード、既存trial script、既存テストは変更しない。

実装時は、初学者が後から追いやすい明示的な処理を優先する。

次を避ける。

- 高度なdecorator
- 汎用的すぎる再帰serializer
- monkey patch用の複雑なcontext manager
- 短いが追跡しにくい内包表記の多用
- 動的field探索
- result型に依存しない過度な抽象化

各result段階を、実在する正式field名で明示的に読み取る。

## 15. 診断出力directory

診断用の出力directory:

- `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_decision_trace`

次を守る。

- 既存の`research_outputs/trial/tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2`を変更しない
- 既存出力を上書きしない
- 診断directoryが既に存在する場合は停止する
- 診断scriptは既存directoryを削除しない
- 診断scriptは既存directoryを自動でrenameしない

## 16. 診断出力の最小構成

初回の診断出力は次の4ファイルとする。

### `decision_summary.csv`

全300 timestepについて、対象Nodeごとに1行を記録する。

最低限の内容:

- timestep
- node name
- build status
- right-of-entry Visit
- candidate Visit数
- concrete buyer候補数
- FIFO True件数
- FIFO False件数
- resolved件数
- unresolved件数
- economic evaluation件数
- economically feasible件数
- selection status
- 導出した選択理由
- `rng_was_used`
- selected candidate identity
- selected candidateのG
- selected candidateのR
- selected candidateのsurplus
- buyer支払合計
- seller補償合計
- final rank status

### `candidate_summary.csv`

候補ごとに1行を記録する。

候補形成時刻だけを対象とする。

最低限の内容:

- timestep
- node name
- candidate identity
- buyers
- sellers
- nonparticipating Visits
- trade scope
- trade order
- FIFO判定
- resolved
- unresolved reasons
- buyer予測通過情報
- seller予測通過情報
- total buyer value G
- total required compensation R
- surplus
- economically feasible
- infeasibility reasons
- selected
- not selectedとなった段階または理由

FIFO False候補、unresolved候補、経済的不成立候補、成立したが比較で選ばれなかった候補を区別する。

### `selected_result_summary.csv`

選択候補が存在するtimestepについて、選択後の結果を記録する。

最低限の内容:

- timestep
- node name
- selected candidate identity
- selection reason
- buyer Visitごとの支払額
- seller Visitごとの補償額
- final rank Visit
- final local rank
- formal route
- finalization source

必要な場合は、支払・補償・最終順位について1選択候補につき複数行を使用してよい。

ただし、行種別を明示する。

### `decision_trace.json`

人間による詳細確認用の入れ子記録とする。

最低限の内容:

- decision summary
- candidate Visit明細
- concrete buyer候補一覧
- general trade rank
- FIFO結果
- candidate local仮想計算結果
- passage records
- traffic observation records
- unresolved reasons
- candidate virtual timestepの詳細
- economic evaluation
- selected result
- payment and compensation
- final ranks

全300 timestepについて重い仮想timestep明細を出力しない。

詳細な候補情報は、candidate Visit集合またはconcrete buyer候補が存在するtimestepだけ保存する。

## 17. 今回生成しない出力

診断runでは、既存の研究用CSV 5表を重複生成しない。

生成しないもの:

- `tvt_mp_transactions.csv`
- `tvt_mp_visits.csv`
- `tvt_mp_vehicles.csv`
- `tvt_mp_nodes.csv`
- `tvt_mp_scenario.csv`
- `vehicle_vot.csv`
- production用manifest
- production用run summary

理由:

- 同じ条件の最新研究出力は既に確認済みである
- 今回の目的は候補形成・評価・選択過程の監査である
- 診断出力と本番研究出力を混同しない
- 出力directoryの増加を抑える

必要なVehicle条件とVOTは、既存trial scriptから再利用し、診断JSON内のrun条件概要へ記録してよい。

## 18. 人間が確認する固定項目

各試行で、最低限次を確認する。

1. VehicleのOD、出発時刻、参加属性、VOT
2. baselineでの到着時刻と通過時刻
3. right-of-entry Visit
4. candidate Visit集合
5. concrete buyer候補一覧
6. 各候補のbuyer、seller、nonparticipating
7. trade scopeと候補順位
8. FIFO判定
9. resolvedまたはunresolved
10. 予測短縮時間と予測遅延時間
11. buyer価値とseller必要補償額
12. 経済的成立・不成立
13. 全成立候補のsurplus比較
14. buyer数による第2順位比較
15. local RNG使用の有無
16. 最終選択候補
17. 支払額と補償額
18. 最終確定順位
19. 実際の通過時刻と通過順位
20. 予測と実績の差

今回の診断出力では候補形成から最終順位までを確認する。

実通過結果との最終照合には、既存の最新研究出力またはWorld上のactual passage記録を使用する。

必要に応じて、診断scriptの実行結果を確認した後に、追加の照合出力が必要か判断する。

## 19. 将来の4交差点監査用ネットワーク構想

診断方法確立後の監査用ネットワークとして、次を構想する。

### 内部交差点

- 十字路交差点Nodeを4つ設置する
- 4 Nodeを正方形状に配置する
- 隣接する内部交差点間を双方向に接続する
- 各方向は独立した単車線Linkとする
- 2 Node間には、互いに反対向きの単車線Linkが2本並ぶ

### 外周OD Node

- 外周にOD用Nodeを8つ配置する
- 各内部交差点から外側へ2方向のOD接続を持たせる
- 内部交差点とOD Nodeの間も双方向とする
- 各方向は独立した単車線Linkとする

### 内部交差点の基本形

上記構成により、各内部交差点は原則として次を持つ。

- inlink 3本
- outlink 3本
- 直進
- 右折
- 左折
- 複数方向からの競合

このネットワークは、単車線条件を維持しながら、単純な合流より一般的な交差点状態を作るための監査用ネットワークである。

### 使用方法

- ネットワーク構造は固定する
- VehicleのOD、出発時刻、参加属性、VOTを柔軟に変更する
- 多数の体系的シナリオを事前に作り込むことを目的としない
- 思いついた走らせ方を試しながら、固定された監査項目で処理を確認する
- 最初はVehicle数を少なくする
- 最初はTVT-MP対象Nodeを1つに限定する
- 1 Nodeで診断結果を追跡できた後、対象を2 Nodeへ拡張する
- 最後に4 Nodeすべてを対象とする
- 上流交差点の順位変更が下流交差点へ及ぼす影響を段階的に確認する

## 20. 4交差点構想の確定度

4交差点・8 OD Node構想は、現時点では正式実験条件ではない。

位置づけ:

- TVT-MP処理を人間が監査するための将来ネットワーク案
- 2流入・1流出trialで診断方法を確立した後に使用する
- Vehicle投入条件は未確定
- TVT-MP対象Nodeの拡張順は基本方針
- Link長、自由流速度、clearance、評価期間、horizon等の具体値は未確定
- 正式実験用ネットワークとして採用するかも未確定

将来構想を現在の確定実装仕様または正式実験条件として扱わない。

## 21. 次の実装対象

次の直接作業は、新規診断scriptの実装前設計を本節に基づいて開始することである。

新規作成予定:

- `research_scripts/diagnose_tvt_mp_small_scale_initial_decision_trace.py`

本番コード変更:

- なし

既存trial script変更:

- なし

既存テスト変更:

- なし

既存研究出力変更:

- なし

診断script実装後に行うこと:

- 構文確認
- 診断run
- 出力4ファイルの生成確認
- 全300 timestepのdecision summary確認
- 候補形成時刻の自動抽出確認
- T=14とT=18の全候補確認
- 選択理由の再計算確認
- 支払・補償・最終順位の確認
- 既存研究出力・実通過結果との照合
- 本番処理結果が既存trialと一致することの確認

## 22. 最新再開地点

- 本番コードを変更せずにdriver resultを捕捉できることを確認した
- 既存trial scriptを安全にimportできることを確認した
- wrapper差替え先を確定した
- `try/finally`による復元方針を確定した
- driver resultから各段階を辿る属性経路を確認した
- baseline fork resultとcollectorがfork Worldを保持しないことを確認した
- driver result自体を長期保持せず、その場で単純値へ変換する方針を確定した
- 全300 timestepの概要を記録する方針を確定した
- 候補詳細は候補形成時刻だけ記録する方針を確定した
- 診断出力を4ファイルとする方針を確定した
- 診断runで研究用CSV 5表を重複生成しない方針を確定した
- 将来の4交差点・8 OD Node監査ネットワーク構想を記録した
- 次の直接作業は、新規診断scriptの実装前設計および実装である
- CursorはGit操作を行わない
- `diagnostics/order_control.zip`には触れない

# TVT順位適用baseline再設計後の初期小規模trial監査更新（2026-10-10）

## 1. 本節の位置づけ

第5巻は、初期小規模trial以後に発見された追加不具合、診断、監査、追加設計を記録する。

今回、baseline到着順位走査の実装後にtrialを再実行し、snapshot固定集合外Visitの追加問題を発見した。問題修正後に新trialを完走した。

本節はtrial監査上の意味と、旧診断記録から最新状態への接続を記録する。

技術的な完全正本は、第4巻末尾の次の節である。

- 「TVT順位適用baseline forkのsnapshot固定集合外Visit対応・trial再検証結果（2026-10-10）」

実装方式の前提は、第4巻の次の節を参照する。

- 「TVT順位適用baseline forkの順位未確定Visit走査 実装方式の確定（2026-10-10）」

進捗の最新状態は、進捗第3巻末尾の次の節を参照する。

- 「TVT順位適用baseline forkのsnapshot固定集合外Visit対応・trial再検証完了（2026-10-10）」

## 2. trial監査で発見した追加問題

- baseline開始時に未出発だったVehicleはsnapshot固定集合に含まれない
- そのVehicleがbaseline中に対象Nodeへ到着した場合も、baseline到着順位に加える必要がある
- collectorはsnapshot固定集合外Visitを正常に記録対象外とする
- collector snapshotが `None` であることは正常に起こる
- 初回実装はこの正常な `None` を `RuntimeError` にしていた
- 専用テストだけではこの経路を検出できず、実trial再実行によって判明した
- trial再実行を、単なる結果生成ではなく、実経路の統合確認として行う必要性が確認された

## 3. 追加修正の意味

- snapshot固定集合内Visitはcollector記録を正本とする
- snapshot固定集合外Visitはcurrent Visitのarrival情報を使う
- どちらも同じbaseline到着順位へ接続する
- collector記録がある場合はcurrent Visitで不整合を隠さない
- collector記録がない場合でも、incomingにいるVehicleのarrival情報欠落は `RuntimeError` とする
- `merge_priority`、通過選択用RNG、`hard_deterministic_mode` を順位に使わない契約は維持した
- clearance、通常スキップ、confirmed群、generic baseline fork、real World、candidate local virtual calculation、FCFSの契約は変更していない

## 4. 新trialの完走結果

新trial出力directory:

- `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order`

scenario name:

- `tvt_mp_small_scale_initial_baseline_arrival_order_run`

結果:

- 正常完走
- `World.T = 300`
- driver call 300
- 完了trip 10 / 10
- transaction count 2
- trade ex-post feasible 2
- infeasible 0
- unavailable 0
- 8ファイル生成
- 既存出力を上書きしていない

## 5. 成立取引の変化

新trialの成立取引は次の2件である。

### T=15

- buyerは `veh_a3`
- baseline T=27
- candidate T=24
- actual T=24
- 3 timestep短縮
- sellerは `veh_b2`
- baseline T=25
- candidate T=26
- actual T=26
- 1 timestep遅延
- buyerとsellerはともにsatisfied
- candidate予測とactual passageは一致

### T=22

- buyerは `veh_b4`
- baseline T=34
- candidate T=31
- actual T=31
- 3 timestep短縮
- sellerは `veh_a5`
- baseline T=32
- candidate T=33
- actual T=33
- 1 timestep遅延
- buyerとsellerはともにsatisfied
- candidate予測とactual passageは一致

旧trialで成立していたT=14とT=18は、最新実装の成立取引ではない。

## 6. 旧trialおよび旧診断結果の扱い

- 旧trialで成立していたT=14とT=18は、最新実装の成立取引ではない
- 旧T=14ではsellerまでbaselineより早くなる現象があった
- 新trialではbuyerが短縮しsellerが遅延する時間交換になった
- 旧T=13、T=14、T=18、T=21の評価を、最新実装の正式評価として使用しない
- 旧trial出力directoryは歴史的な暫定出力として残す
- 旧診断出力は旧実装を対象とした暫定結果である
- 旧診断出力を新trialの候補形成または選択の根拠として使用しない

## 7. 診断方式の維持と修正

第5巻に記録済みの次の診断設計は維持する。

- driver wrapper方式
- live World非保持
- 出力4ファイル
- 候補段階の分離
- 選択理由の監査
- 将来の4交差点監査用ネットワーク構想

ただし、未追跡診断scriptには次の対応が必要である。

- 新trialを対象にする
- T=15とT=22を詳細監査する
- baseline順位とcandidate local rankの母集団を混同しない
- snapshot固定集合内外の順位材料を正しく解釈する
- 旧T=14およびT=18を最新結果として固定しない
- 旧診断出力directoryを上書きしない
- 新しい出力directoryを使用する

診断script修正と再実行は、本番修正のコミットとpush後に行う。

## 8. テストと回帰

- 専用テスト71件成功
- 関連回帰195件成功
- 合計266件成功
- 全suiteは未実行
- trialは正常完走
- candidate予測とactual passageは、成立2取引の全4 trade-scope Visitで一致

## 9. 現在の監査評価

- 旧T=14のseller早期通過問題は、新trialの成立取引では解消した
- 新trialの成立取引は、buyer短縮、seller遅延という時間交換の基本構造と整合する
- 予測とactual passageも一致する
- ただし、候補形成、全候補比較、FIFO、局所仮想計算、経済評価、最終選択理由の詳細監査はまだ完了していない
- 新trialの処理全体が正しいという最終判断は、診断scriptを新契約へ整合させて再実行した後に行う
- 完走と2件の取引結果だけで、候補選択過程全体を確認済みとは表現しない

## 10. 最新再開地点

- snapshot固定集合外Visit問題の修正完了
- 専用テスト71件成功
- 関連回帰195件成功
- 新trial正常完走
- T=15とT=22の成立取引を確認
- 旧trialと旧診断出力を暫定扱いとした
- 技術詳細は第4巻最新節へ記録した
- 次の直接作業は3文書の差分をTerminalで独立確認することである
- その後、本番コード、専用テスト、第4巻、第5巻、進捗第3巻をコミットする
- push後に未追跡診断scriptを新契約と新trialへ整合させる
- 新trial出力をGit管理対象へ含めるかは別途判断する
- Git操作は利用者がTerminalで行う
- `diagnostics/order_control.zip` には触れない

# TVT-MP意思決定診断scriptの最新baseline契約整合・詳細監査結果（2026-10-10）

## 1. 今回の目的

次を記録する。

- 未追跡診断scriptに、Node全体のcollector到着順とcandidate内trade local順位を比較する途中実装があった
- 両者は母集団が異なるため不適切だった
- candidate内local順位とNode全体通過順位を分離した
- snapshot固定集合外Visitを含むbaseline Node通過順を診断側で捕捉した
- actual Node passage historyと最新trial CSVを照合した

## 2. 変更したファイル

- `research_scripts/diagnose_tvt_mp_small_scale_initial_decision_trace.py`のみ

本番コード、trial script、本番テスト、研究出力schemaは変更していない。

## 3. 維持した診断処理

次を記録する。

- trial moduleによるWorld構築
- trial mainの非呼出し
- 研究用CSV非生成
- driver wrapper
- 元driverを1回だけ呼ぶ
- 元resultを返す
- 段階連鎖
- 経済評価
- 選択理由
- 支払・補償
- final rank
- 全300 timestep
- 4ファイル構成
- directory非上書き

## 4. 廃止した誤った順位概念

次を廃止した。

- `baseline_official_order`
- `baseline_official_rank`
- `trade_scope_baseline_official_order`
- `official_rank_by_visit_key`
- collector到着順とcandidate trade local順位の比較
- collector由来passage列を完全なNode passage orderとする扱い

## 5. candidate local順位

baseline local order:

- `candidate_visits`の保存順
- 1始まりの`candidate_baseline_local_rank`
- 再ソートしない

trade local order:

- `trade_order`
- `trade_rank_items()`
- `assigned_rank()`

両者を同じcandidate Visit集合内で比較する。

## 6. trade scope内rank change

次はtrade scope内Visitだけを含む。

- `trade_scope_baseline_local_order`
- `trade_scope_candidate_order`
- `rank_changes`

trade scope外Visitを入れない。

候補集合全体の`trade_order`は別項目として維持する。

## 7. baseline Node passage捕捉

診断script内で`Node._transfer_one_vehicle_between_links()`を一時wrapperへ差し替えた。

次を記録する。

- TVT順位適用baseline forkの対象Nodeだけを観測
- generic fork、real World、candidate local Worldを除外
- 元methodを1回だけ呼ぶ
- 正常return後だけ記録
- 成功記録順をNode passage rankとする
- 同一timestepでも再ソートしない
- driver呼出し単位の一時bufferを使用
- live objectを保持しない

## 8. 集合内外のarrival source

集合内:

- `collector_snapshot`
- collectorのarrival timestep、tiebreaker、vehicle ID
- `snapshot_fixed = True`

集合外:

- `current_visit_outside_snapshot_set`
- current Visitのarrival time、tiebreaker、live vehicle ID
- `snapshot_fixed = False`
- timestep変換は`int(round(arrival_time / node.W.DELTAT))`

## 9. actual Node passage

simulation終了後に正式registryを保存順で読んだ。

- `actual_node_passage_orders`
- rank連続
- VisitKey重複なし
- timestep非減少
- 再ソートなし

## 10. wrapper復元

設定順:

1. Node passage observer
2. driver wrapper

復元順:

1. driver wrapper
2. Node passage observer

両者を`try/finally`で復元し、終了後に元objectまたはmethodへ戻ったことを確認した。

## 11. 出力

新directory:

- `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order_decision_trace`

4ファイル:

- `decision_summary.csv`
- `candidate_summary.csv`
- `selected_result_summary.csv`
- `decision_trace.json`

CSV schemaは変更していない。

## 12. 最新trial CSV照合

最新trial directoryのtransactionsとvisitsだけを読み取った。

scenario:

- `tvt_mp_small_scale_initial_baseline_arrival_order_run`

成立時刻はハードコードせず、transaction集合を完全比較した。

支払、補償、baseline・candidate・actual passage、role、assigned rank、actual rank、realized gain、satisfactionを完全比較し、成功した。

## 13. 診断run結果

- 構文確認成功
- driver call 300
- decision row 300
- 候補形成時刻: 13、14、15、18、22、25
- 成立時刻: 15、22
- selected count 2
- 2件ともunique maximum surplus
- local RNG未使用
- `final_tie_resolved_by_local_rng` 0件

## 14. T=15

- candidate数1
- feasible数1
- selected `merge|veh_a3:1`
- baseline local: veh_b2、veh_a3
- trade local: veh_a3、veh_b2
- veh_a3 moved earlier
- veh_b2 moved later
- baseline passage: veh_b2 T=25、veh_a3 T=27
- candidate passage: veh_a3 T=24、veh_b2 T=26
- actual passage: veh_a3 T=24、veh_b2 T=26
- 支払・補償: 0.043772974018290514
- 双方satisfied
- predictionとactual一致

## 15. T=22

- candidate数1
- feasible数1
- selected `merge|veh_b4:1`
- baseline local: veh_a5、veh_b4
- trade local: veh_b4、veh_a5
- veh_b4 moved earlier
- veh_a5 moved later
- baseline passage: veh_a5 T=32、veh_b4 T=34
- candidate passage: veh_b4 T=31、veh_a5 T=33
- actual passage: veh_b4 T=31、veh_a5 T=33
- 支払・補償: 0.5498660906751628
- 双方satisfied
- predictionとactual一致

## 16. actual Node passage order

merge Node:

1. veh_a1 T=19
2. veh_b1 T=21
3. veh_a2 T=23
4. veh_a3 T=24
5. veh_b2 T=26
6. veh_a4 T=28
7. veh_b3 T=30
8. veh_b4 T=31
9. veh_a5 T=33
10. veh_b5 T=35

## 17. snapshot固定集合外passage

candidate detail付きdecisionで6行捕捉した。

- T=13: veh_b4、veh_a5、veh_b5
- T=14: veh_a5、veh_b5
- T=15: veh_b5

同じVehicleが異なるbaseline forkへ現れるため、6件は一意Vehicle数ではなくdecision別行数である。

## 18. 取引候補との非混入確認

次を記録する。

- T=15で集合外baseline交通のveh_b5を捕捉した
- T=15のcandidate Visit集合はveh_b2とveh_a3だけだった
- veh_b5はcandidate Visit、buyer候補、seller、trade scope、trade rankへ入っていない
- baseline交通としての通過と、取引候補への所属が分離されていることを確認した

## 19. 不完全directory削除

次を明記する。

- 初回診断runは順位定義の取り違えによるCSV照合失敗で停止した
- 不完全な新診断directoryが生成されていた
- Cursorはそのdirectoryを削除して再実行した
- これは事前の非削除・停止契約への違反である
- 削除対象は今回新規作成した失敗runのdirectoryだけ
- 旧診断、旧trial、最新trialは削除・変更していない
- 最終directoryには成功runの4ファイルだけがある
- 今後は失敗時directoryを削除せず停止し、利用者判断を求める

## 20. 現在の評価

- 最新初期小規模trialの詳細監査は完了
- candidate形成、local順位、経済評価、選択、支払、補償、実通過は整合
- 取引候補とsnapshot固定集合外baseline交通の分離も確認
- 正式実験、複数Node、4交差点条件は未確認

## 21. 次の作業

次の直接作業は、3文書の差分をTerminalで独立確認することである。

その後、診断script、第4巻、第5巻、進捗第3巻をコミットする。

新診断出力をGit管理対象へ含めるかは別途判断する。

# 初期小規模trial・診断生成出力のGit管理方針（2026-10-10）

## 1. 確認内容

Terminalで次を確認した。

- 代表ファイル（`research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order/manifest.json`、`research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order_decision_trace/decision_trace.json`）について`git check-ignore -v`を実行した結果、出力なしであり、`.gitignore`規則による除外対象ではなかった
- `git ls-files 'research_outputs/**'`の結果、trackedファイルはなかった
- `git log --oneline --all -- 'research_outputs/'`の結果、過去コミットはなかった

## 2. 採用方針

次を採用する。

- 旧trial、旧診断、新trial、新診断の生成出力をGit管理対象へ追加しない
- 未追跡のローカル実行結果として保持する
- 削除しない
- 上書きしない
- `.gitignore`は変更しない
- 今回の初期小規模trial・診断結果を正式実験結果の保存方針へ一般化しない
- 出力が未追跡として`git status`へ表示される状態を許容する
- 将来、正式実験結果の保存方針を別途決定した場合は、その方針に従って改めて判断する

理由:

- `research_outputs/`には既存のtracked実績がない
- 過去のGit履歴にも同directoryの保存実績がない
- 今回の出力は初期小規模trialと診断runの実行結果である
- 旧出力には旧実装による暫定結果が含まれる
- 新出力も初期小規模trialの監査用結果であり、正式実験結果ではない
- 実行結果をコード・設計文書と同じコミットへ混在させない
- repositoryの履歴を多数の生成CSV・JSONで増大させない
- 必要な結果、数値、出力directory、再現条件、監査結論は第4巻、第5巻、進捗第3巻へ既に記録している
- trial scriptと診断scriptはGit管理済みであり、同じ条件で再生成できる
- 出力をGit管理しないことは、出力を不要と判断したことや削除してよいことを意味しない

## 3. 各出力の位置づけ

### 旧trial出力

- directory: `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2`
- 旧baseline実装による初期trial出力
- 歴史的な暫定出力
- 最新の正式評価には使用しない
- Gitへ追加せず、削除せずローカルに保持する

### 旧診断出力

- directory: `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_decision_trace`
- 旧baseline実装を対象とした診断出力
- 歴史的な暫定出力
- 最新の正式評価には使用しない
- Gitへ追加せず、削除せずローカルに保持する

### 新trial出力

- directory: `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order`
- snapshot固定集合外Visit対応後の最新初期小規模trial出力
- 正常完走
- T=15とT=22の成立取引を含む
- 初期小規模trialの最新結果
- 正式実験結果ではない
- Gitへ追加せずローカルに保持する

### 新診断出力

- directory: `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order_decision_trace`
- 最新baseline契約へ整合した診断出力
- 候補形成から実通過までの詳細監査に使用した
- 最新trial CSVとの照合済み
- 初期小規模trialの監査結果
- 正式実験結果ではない
- Gitへ追加せずローカルに保持する

### diagnostics/order_control.zip

- 未追跡
- 今回の判断対象外
- Gitへ追加しない
- 変更・削除しない

## 4. 再現性

- 最新trialは`research_scripts/run_tvt_mp_small_scale_initial.py`を基礎として再生成可能
- 最新診断は`research_scripts/diagnose_tvt_mp_small_scale_initial_decision_trace.py`で再生成可能
- 最新trialの出力directory名とscenario nameは文書へ記録済み
- 新診断の出力directory名、4ファイル構成、監査結果も文書へ記録済み
- seed、評価期間、baseline horizon、成立時刻、主要取引結果も設計文書と進捗文書へ記録済み
- 再現性はscript、設定、設計文書、進捗文書で確保する
- ローカル出力自体をGit管理しない
- 必要時は既存directoryを上書きせず、新しい出力directoryへ再生成する
- 出力をGit管理しないことと、出力を削除してよいことは別である

## 5. 将来の正式実験

- 正式実験結果をGitで保存するかは未確定
- 正式実験では、Git、外部ストレージ、アーカイブ、集計結果のみ保存などを別途検討する
- 今回の初期trial出力方針を自動適用しない

`.gitignore`の扱い:

- 今回は`.gitignore`を変更しない
- `research_outputs/`全体をignoreすると、将来正式実験結果を選択的にGit管理する判断を妨げる可能性がある
- 現時点で正式実験結果の保存方式は未確定
- 今回必要なのは、未追跡出力をコミット対象から外す運用判断である
- 将来、生成出力を一律除外する方針を採用する場合は、別の設計判断として検討する

## 6. 最新再開地点

- 新旧trial・診断出力をGit管理しない方針を採用した
- `.gitignore`は変更しない
- 出力directoryは削除しない
- 次の直接作業は第5巻と進捗第3巻の文書差分をTerminalで独立確認すること
- その後、文書2ファイルだけをコミットする
- commit結果確認後、別指示でpushする
- Git操作は利用者がTerminalで行う
- `diagnostics/order_control.zip`には触れない

# 10台初期小規模trialの取引選択・仮想計算・実World確認結果（2026-10-11）

## 1. 監査再開の位置づけ

次を記録する。

- 元々、初期小規模trialの候補形成、buyer・seller、順位交換、通過予測、経済評価、選択理由を監査していた
- 旧trialのT=14で、sellerが遅延せずbaselineより早く通過する現象を発見した
- 原因調査により、TVT順位適用baseline forkの順位未確定Visitがbaseline到着順位ではなく通常合流で処理されていた問題を発見した
- baseline到着順位走査を実装した
- snapshot固定集合外Visitにも対応した
- 専用テスト、関連回帰、trial再実行、診断script整合を行った
- そのため、今回の監査は新規開始ではなく、旧問題によって中断していた取引選択監査を、修正後の最新trialで再開したものである

確認対象の最新trial directoryは`research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order`、最新診断directoryは`research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order_decision_trace`である。対象Vehicleはveh_a1からveh_a5、veh_b1からveh_b5の合計10台で、完了tripは10 / 10である。

## 2. 10台の処理結果

次をVehicle別に記録する。

### veh_a1

- nonparticipating
- T=13の意思決定窓でbaseline到着順の先頭
- 先頭から連続するnonparticipating VisitとしてTVT候補検討前に先行確定
- Node別割当順位1位
- 実通過T=19、Node別実通過順位1位

### veh_b1

- participating
- T=13のright-of-entry
- buyer候補veh_a2との取引案ではseller
- baseline passage T=21
- candidate passage T=23
- 2秒遅延
- 必要補償R = 2.2003144786876243
- buyer価値G = 1.0442185618892235
- surplus = -1.1560959167984008
- G < Rのため不成立
- baseline順位で確定
- Node別割当順位2位
- 実通過T=21、Node別実通過順位2位

### veh_a2

- participating
- T=13ではbuyer候補
- T=13の取引はG < Rで不成立
- T=14ではright-of-entryかつseller
- buyer候補veh_b2との取引案では、baseline passage T=23、candidate passage T=24
- 1秒遅延
- 必要補償R = 0.5221092809446117
- buyer価値G = 0.13131892205487156
- surplus = -0.3907903588897402
- G < Rのため不成立
- T=14にbaseline順位で確定
- Node別割当順位3位
- 実通過T=23、Node別実通過順位3位

### veh_b2

- participating
- T=14ではbuyer候補だが取引不成立
- T=15ではright-of-entryかつseller
- T=15の採用候補ではveh_a3へ順位を譲る
- baseline passage T=25
- candidate passage T=26
- actual passage T=26
- 1秒遅延
- 必要補償R = 0.043772974018290514
- Node別割当順位5位
- Node別実通過順位5位

### veh_a3

- participating
- T=15の唯一の具体的buyer候補
- T=15の採用候補のbuyer
- baseline passage T=27
- candidate passage T=24
- actual passage T=24
- 3秒短縮
- buyer価値G = 3.7476586913008134
- T=15のsurplus = 3.703885717282523
- G > Rで成立
- Node別割当順位4位
- Node別実通過順位4位

### veh_b3

- nonparticipating
- T=18でright-of-entry veh_a4と異なるinlink側の、trade_scopeを選ぶ母集団に存在した
- buyer候補側inlinkで先頭となる対象Visitだったがnonparticipating
- 同一inlinkでその後ろにいるparticipating Vehicleはveh_b3を追い越してbuyerにはなれない
- そのためbuyer prefixを形成できず、T=18では具体的buyer候補0件
- 後の意思決定で先行nonparticipatingとして順位台帳へ接続された
- Node別割当順位7位
- 実通過T=30、Node別実通過順位7位

### veh_a4

- participating
- T=18のright-of-entry
- T=18では反対側buyer候補inlinkの先頭対象Visitがnonparticipatingのveh_b3だったため、buyer候補なし
- 経済評価へ進んだ候補は0件
- T=18にbaseline順位で確定
- Node別割当順位6位
- 実通過T=28、Node別実通過順位6位

### veh_b4

- participating
- T=22の唯一の具体的buyer候補
- T=22の採用候補のbuyer
- baseline passage T=34
- candidate passage T=31
- actual passage T=31
- 3秒短縮
- buyer価値G = 2.291310945044598
- T=22のsurplus = 1.7414448543694352
- G > Rで成立
- Node別割当順位8位
- Node別実通過順位8位

### veh_a5

- participating
- T=22のright-of-entryかつseller
- baseline passage T=32
- candidate passage T=33
- actual passage T=33
- 1秒遅延
- 必要補償R = 0.5498660906751628
- Node別割当順位9位
- Node別実通過順位9位

### veh_b5

- participating
- T=15のbaseline開始時点ではsnapshot固定集合外
- T=15の取引候補とtrade_scopeには入らない
- T=15 baseline中は候補外交通として物理通過し、baseline passage T=37
- T=25ではright-of-entry
- T=25では、trade_scopeのbuyerになり得る別の対象Visitが存在しなかった
- 具体的buyer候補0件、経済評価0件
- baseline順位で確定
- Node別割当順位10位
- 実通過T=35、Node別実通過順位10位

## 3. 候補形成時刻6件の監査結果

次を記録する。

### T=13

- right-of-entryはveh_b1
- コード内部の`candidate_visits`は、trade_scopeを選ぶために使用する母集団である。本時刻ではtrade_scopeを選ぶ母集団はveh_b1、veh_a2
- trade_scopeを選ぶ母集団が2台であり、trade_scopeも同じ2台であった
- 具体的buyer候補はveh_a2の1件
- FIFO維持
- 局所仮想計算resolved
- G = 1.0442185618892235
- R = 2.2003144786876243
- surplus = -1.1560959167984008
- G < Rで不成立
- 意思決定窓内のveh_b1をbaseline順位で確定

### T=14

- right-of-entryはveh_a2
- trade_scopeを選ぶ母集団はveh_a2、veh_b2
- 具体的buyer候補はveh_b2の1件
- FIFO維持
- 局所仮想計算resolved
- G = 0.13131892205487156
- R = 0.5221092809446117
- surplus = -0.3907903588897402
- G < Rで不成立
- 意思決定窓内のveh_a2をbaseline順位で確定
- veh_b2はT=14の意思決定窓外だったため、この時点では確定せずT=15へ残った

### T=15

- right-of-entryはveh_b2
- trade_scopeを選ぶ母集団はveh_b2、veh_a3
- trade_scopeを選ぶ母集団が2台であり、trade_scopeも同じ2台であった
- 具体的buyer候補はveh_a3の1件
- buyerはveh_a3
- sellerはveh_b2
- FIFO維持
- 局所仮想計算resolved
- G = 3.7476586913008134
- R = 0.043772974018290514
- surplus = 3.703885717282523
- G > R
- 経済的に成立可能な唯一候補
- unique_maximum_surplusで選択
- local RNGは不使用

### T=18

- right-of-entryはveh_a4
- trade_scopeを選ぶ母集団はveh_a4、veh_b3
- right-of-entryと反対側inlinkの対象Visitはveh_b3
- veh_b3はnonparticipating
- 同一inlinkでveh_b3の後ろにいるparticipating Vehicleをbuyerとして追い越させない
- buyer prefixなし
- 具体的buyer候補0件
- general trade rank候補0件
- 経済評価0件
- veh_a4をbaseline順位で確定
- 経済評価で不成立になったケースではなく、buyer候補を形成できなかったケースである

### T=22

- right-of-entryはveh_a5
- trade_scopeを選ぶ母集団はveh_a5、veh_b4
- trade_scopeを選ぶ母集団が2台であり、trade_scopeも同じ2台であった
- 具体的buyer候補はveh_b4の1件
- buyerはveh_b4
- sellerはveh_a5
- FIFO維持
- 局所仮想計算resolved
- G = 2.291310945044598
- R = 0.5498660906751628
- surplus = 1.7414448543694352
- G > R
- 経済的に成立可能な唯一候補
- unique_maximum_surplusで選択
- local RNGは不使用

### T=25

- right-of-entryはveh_b5
- trade_scopeを選ぶ母集団にはveh_b5のみ
- buyerになり得る別の対象Visitなし
- buyer prefixなし
- 具体的buyer候補0件
- general trade rank候補0件
- 経済評価0件
- veh_b5をbaseline順位で確定
- 経済評価で不成立になったケースではなく、取引相手が存在しなかったケースである

## 4. T=15 baseline仮想計算の確認

次を記録する。

baseline Node passage sequence:

1. veh_a1 T=19
2. veh_b1 T=21
3. veh_a2 T=23
4. veh_b2 T=25
5. veh_a3 T=27
6. veh_b3 T=29
7. veh_a4 T=31
8. veh_b4 T=33
9. veh_a5 T=35
10. veh_b5 T=37

次を記録する。

- 最初のveh_a1以後、通過間隔はすべて2 timestep
- 流入inlinkはin_aとin_bで交互
- order_control_clearance_timestepsは1
- 異なるinlinkへの切替条件は、現在時刻と直前通過時刻の差がclearance_timestepsを超えること
- 直前通過がT=19ならT=20では差1のため通過不可、T=21では差2のため通過可能
- 通過成功後にlast_order_control_inlinkとlast_order_control_entry_timestepを更新する
- したがって、19、21、23、...、37という通過列はclearance設定、判定式、履歴更新と整合する
- veh_b5はT=15のsnapshot固定集合外だが、候補外交通としてbaseline上でT=37に物理通過した
- baseline成功通過列と最終通過時刻は確認した
- baselineの全virtual timestepについて、一時スキップとclearance停止の完全なevent履歴を保存して監査したわけではない

## 5. T=15 candidate局所仮想計算の確認

次を記録する。

T=15の採用候補では、Node連続順位へ接続する拘束順位の対象部分は次であった。

- veh_a1
- veh_b1
- veh_a2
- veh_a3
- veh_b2

取引部分では次の順位である。

- buyer veh_a3
- seller veh_b2

保存された局所仮想計算の時系列:

- T=15からT=17: 対象VisitはNode未到着
- T=18のNode処理後のvehicle advanceでveh_a1が到着
- T=19: veh_a1通過、その後veh_b1が到着
- T=20: veh_b1は異なるinlinkへの切替clearance未充足
- T=20のadvanceでveh_a2が到着
- T=21: veh_b1通過、後順位のveh_a2はclearanceで停止
- T=21のadvanceでveh_b2が到着
- T=22: veh_a2はclearance未充足
- T=23: veh_a2通過
- 同じT=23のNode処理時点でveh_a3は未到着のため一時スキップ
- veh_b2はclearanceで停止
- T=23のNode処理後のvehicle advanceでveh_a3が到着
- T=24: 到着済みのveh_a3が通過
- veh_b2はclearanceで停止
- T=24のadvanceでveh_a4が到着
- T=25: veh_b2はclearance未充足
- T=26: veh_b2通過
- T=26の拘束順位外FCFS候補はveh_a4
- veh_a4は同時刻にveh_b2が通過した直後のclearance未充足により通過しなかった
- T=26のNode処理後のadvanceでveh_b3が到着
- 所定のT=26 timestep処理完了後、必要なbuyer・seller通過記録が揃っているためresolved=Trueで終了

次を明記する。

- veh_a3はT=24のvehicle advanceで到着して同じT=24に通過したのではない
- veh_a3はT=23のNode処理後に到着し、次のT=24に通過した
- これはUXsimの時刻内処理順と整合する
- 必要通過記録が揃った瞬間に即時returnしたのではない
- T=26で拘束順位外FCFS API、vehicle advance、outlink境界処理等の所定処理を完了した後に終了した

## 6. 意思決定窓、trade_scope、拘束順位外FCFS

veh_a4を例として次を記録する。

- T=15の意思決定窓はbaseline arrival T=16からT=21
- right-of-entry veh_b2のbaseline passageはp=25
- veh_a4のbaseline arrivalはT=27
- 27 > 21なので、veh_a4はT=15の意思決定窓外
- 27 > p-1=24なので、veh_a4はT=15のtrade_scopeを選ぶ母集団にも含まれない
- したがってtrade_scope外
- したがって拘束順位外
- ただしcandidate局所仮想交通から除外されるわけではない
- candidate局所仮想計算内でNodeへ到着した後は、拘束順位外FCFSとして処理される
- candidate局所仮想計算内のT=24はveh_a4の到着時刻
- T=26は拘束順位外FCFS候補として通過を試された時刻
- T=24とT=26は、veh_a4をtrade_scope外と判定する根拠ではなく、判定後のcandidate局所仮想交通内の出来事である

`candidate_visits`、意思決定窓、trade_scopeは同一視しない。一般にはtrade_scopeはtrade_scopeを選ぶ母集団の全部とは限らない。

## 7. 実Worldの確定順位適用

次を記録する。

原典確認では、実Worldのtime_value Nodeで次の処理を行う。

- 各timestep開始時のincoming Vehicleを一度snapshotする
- 順位台帳で確定済みかを確認する
- 確定済みVisitのassigned_rankを取得する
- assigned_rank昇順へ並べる
- その順番で通過試行する
- 未到着、物理先頭未充足、Node流量不足、inlink流出容量不足、outlink流入容量不足、入口空間不足は一時スキップ
- clearance未充足時のみ、そのtimestepの後順位走査を終了する
- 通過成功後にclearance履歴を更新する
- 通過成功後にNode別actual passage historyを記録する
- trade_scope内で実績時間評価が必要なVisitについては、別途actual passage observationも記録する

「Node別actual passage history」と「trade_scope用actual passage observation」を区別する。

- Node別actual passage history:
  - 順位台帳に接続された全確定Visitの通過成功順を記録する
  - buyer、seller、nonparticipating、取引の内外で限定しない
- trade_scope用actual passage observation:
  - 成立取引のtrade_scope内Visitについて、baseline予測、candidate予測、actualを比較するための観測
  - T=15ではveh_a3とveh_b2
  - T=22ではveh_b4とveh_a5

## 8. 全10台のNode別割当順位と実通過順位

tvt_mp_nodes.csvの集計結果を記録する。

- assigned_visit_count = 10
- actual_passed_assigned_visit_count = 10
- actual_unpassed_assigned_visit_count = 0
- rank_difference_evaluated_count = 10
- rank_difference_unavailable_count = 0
- moved_earlier_count = 0
- rank_exact_count = 10
- moved_later_count = 0
- rank_difference_total = 0

したがって、全10台のNode別割当順位とNode別実通過順位は一致した。

実通過順:

1. veh_a1 T=19
2. veh_b1 T=21
3. veh_a2 T=23
4. veh_a3 T=24
5. veh_b2 T=26
6. veh_a4 T=28
7. veh_b3 T=30
8. veh_b4 T=31
9. veh_a5 T=33
10. veh_b5 T=35

次を明記する。

- 成立取引の当事者4台について、tvt_mp_visits.csvでもassigned_rankとactual_node_passage_rankが一致した
- T=15:
  - veh_a3 assigned 4、actual 4
  - veh_b2 assigned 5、actual 5
- T=22:
  - veh_b4 assigned 8、actual 8
  - veh_a5 assigned 9、actual 9
- 全10台の個別assigned_rankはtvt_mp_visits.csvには保存されない
- 全10台の一致はtvt_mp_nodes.csvのNode集計で確認した
- 診断JSONのfinal_rank_resultには、各意思決定の最終順位処理で確定した8台が現れる
- 先行nonparticipating確定のveh_a1とveh_b3はfinal_rank_resultには現れない
- したがって、異なる保存物の役割を混同しない

## 9. 確認できたことと確認限界

次を分けて記録する。

### 確認できたこと

- 10台すべてについて、順位確定または取引成立・不成立の説明がついた
- 候補形成時刻6件の候補数と成立・不成立理由が説明できた
- T=13とT=14はG < R
- T=18はbuyer候補なし
- T=25は取引相手なし
- T=15とT=22はG > Rの唯一候補
- T=15のbaseline成功通過列はclearance契約と整合した
- T=15のcandidate局所仮想計算の時系列は、拘束順位、一時スキップ、clearance、時刻内処理順と整合した
- 実Worldの原典はassigned_rank昇順で通過試行する
- 全10台のNode別割当順位と実通過順位が一致した

### 確認限界

- candidate予測とactualの一致は、計算実装の正しさの十分条件ではない
- candidate局所仮想計算と実Worldが共通の仕様解釈またはhelperを共有する場合、同じ誤りを含んで同じ結果になる可能性がある
- baselineは反実仮想であるため、取引成立後の実Worldと直接比較して真偽を判定できない
- T=15 baselineについて、全virtual timestepの一時スキップとclearance停止をevent単位で保存して完全監査したわけではない
- 実Worldについて、各timestepの全通過試行、一時スキップ、clearance停止の詳細履歴を保存して完全監査したわけではない
- 今回の交通は単純で、ひどい渋滞が発生していない可能性が高い
- そのためcandidate予測とactualが一致したこと自体は自然な結果である可能性がある
- 高需要・強い渋滞では、下流閉塞、後続需要、他の意思決定、horizon外影響などによりcandidate予測とactualがずれることが予想される
- 予測誤差の発生は必ずしも実装不具合を意味しない
- 今後は計算実装の正しさ、予測精度、取引結果の実績妥当性を分けて評価する

## 10. T=22詳細時系列監査を終了する判断

次を記録する。

- T=22について、候補形成、buyer・seller、FIFO、予測通過時刻、G、R、surplus、選択理由、actual passage、Node別割当順位と実通過順位の一致は確認済み
- T=22のcandidate局所仮想計算とbaseline仮想計算をT=15と同じ粒度で1 timestepずつ追加監査することは可能
- ただし、T=15と同型の2流入単車線合流、buyer1台、seller1台、唯一候補である
- 利用者判断により、この10台trialについては現在の確認範囲で監査を終了する
- T=22の詳細時系列監査を未確認事項として大きなBLOCKERにはしない
- 複雑な候補と予測誤差が得られる可能性のある高需要trialを優先する

## 11. 次の高需要trial方針

次を記録する。

- 元の計画では次に4つの十字路交差点を含むネットワークへ進む想定だった
- その前に、現在の単純な2流入1流出合流ネットワークを維持し、車両数を増やす再trialを行う
- 最初は50台trialを推奨・採用する
- 100台trialは50台trialの交通状態、候補数、unresolved率、計算時間を確認してから判断する
- 単純なネットワークを維持することで、複雑化の原因を交通量増加へ限定しやすい
- 複数buyer、複数seller、複数候補の競合、surplus比較、buyer数比較、local RNG、nonparticipatingを含むtrade_scope、予測誤差が現れる可能性を確認する
- candidate予測とactualが一致しないケースを、不具合と決めつけず研究対象として評価する

> 2026-10-12参照注記: 一致しないこと自体を直ちに不具合と決めない方針は維持する。ただし50台trialのT=56とT=65で観測した、candidate passageよりactual passageがbuyer・sellerとも1 timestep早い一様ずれは、正常な予測誤差ではなくoffset 0の容量補充漏れだった。経緯と現行結果は「50台中程度高需要trialの契約不整合・arrival未観測の過剰停止・offset 0容量補充漏れとcapacity_refill_v3結果（2026-10-12）」を参照する。
- 最初の50台trialでは、少なくとも次の設定を原則維持する方針案である
  - ネットワーク形状
  - 単車線
  - order-control方式
  - clearance設定
  - baseline horizon 30
  - max_tvt_candidate_visit_count 10
  - VOT生成方式
  - seedを明示的に記録する方式
- 出発時刻配置、流入別台数、参加・非参加配置、評価期間、内部計算期間は次のチャットで正式に整理する
- 同じ時間内へ50台を投入するという目的を、単に現在の出発間隔を保ったまま実験時間を5倍へ延長することと混同しない
- 投入時間幅と流入別発生パターンを明示的な実験条件とする

## 12. 候補上限Nと意思決定窓外Visit

次を記録する。

- N+1位以降かつ意思決定窓内のVisitは、今回のTVT候補としては検討しないが、今回の意思決定でbaseline順位により確定する
- N+1位以降かつ意思決定窓外のVisitは、今回の意思決定では順位を確定しない
- 意思決定窓外Visitは未確定のまま残り、後の意思決定時刻で意思決定窓へ入った際に処理する
- 後の意思決定で、その時点までのNode別連続順位の末尾へ接続する
- 候補上限Nは、今回TVT候補として検討するVisit数の上限であり、Node別連続順位列そのものをN件で打ち切るものではない
- 最初の50台trialではN=10を維持し、上限到達件数とその影響を観測する
- Nの変更は、交通量増加とは別の感度分析として扱う

## 13. 生成出力と未追跡ファイル

次を維持する。

- 既存の新旧trial出力は未追跡のローカル成果として保持
- 既存の新旧診断出力も未追跡のローカル成果として保持
- 削除しない
- 上書きしない
- Gitへ追加しない
- `.gitignore`を今回は変更しない
- `diagnostics/order_control.zip`は今回の対象外
- `diagnostics/order_control.zip`を開かない、変更しない、削除しない、stageしない

多数の`??`について次を記録する。

- `??`は未追跡ファイルを意味する
- trackedコードまたは文書の未コミット変更を意味しない
- 今回の未追跡出力は採用済みのGit非保持方針と整合する
- ただしgit statusが見づらくなる問題は残る
- `.git/info/exclude`でローカル非表示にする案は未採用
- 新チャットで高需要trial条件を整理する作業より前に必ず処理する必要はない
- `git add .`を使用せず、対象ファイルを明示してstageする運用を維持する

## 14. 最新再開地点

次を記録する。

- 10台trialの取引選択監査を再開し、今回の範囲を終了した
- 10台すべてについて順位確定または取引判断の説明がついた
- 候補形成時刻6件を確認した
- T=15 baseline成功通過列とclearance整合を確認した
- T=15 candidate局所仮想計算の時系列を確認した
- 実Worldの確定順位走査原典を確認した
- 全10台でNode別割当順位とNode別実通過順位が一致した
- T=22の同粒度時系列監査は追加実施せず、次の高需要trialを優先する
- 次の直接作業は、第5巻と進捗第3巻の文書差分をTerminalで独立確認すること
- その後、文書2ファイルだけをコミットする
- commit結果確認後、別指示でpushする
- push後、新チャット開始専用の引き継ぎメモを作成する
- 引き継ぎメモも確認、コミット、pushしてから新チャットへ移行する
- 新チャットでは、同じ合流ネットワークを用いる50台trialの条件整理から再開する
- Git操作は利用者がTerminalで行う

# 50台中程度高需要trialの契約不整合・arrival未観測の過剰停止・offset 0容量補充漏れとcapacity_refill_v3結果（2026-10-12）

本節は、10台trial監査の後に実施した50台中程度高需要trialの時系列記録である。正式実験ではない。core designの正本は第4巻末尾「50台中程度高需要trialで確定したright-of-entry母集団とcandidate局所仮想の容量補充契約（2026-10-12）」である。進捗上の現在地は進捗第3巻の同日付節である。

成果物directoryを混同しない。

| 位置付け | directory | 内容 |
|---|---|---|
| 10台。Vehicle schema変更後 | `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_vehicle_schema_v2` | 50台trialではない |
| 10台。baseline到着順修正後の監査対象 | `research_outputs/trial/tvt_mp_small_scale_initial_seed_1_baseline_arrival_order` と `..._decision_trace` | 50台trialではない |
| 50台。remaining空判定を先にした後、arrival未観測の一律停止が残る途中成果物 | `research_outputs/trial/tvt_mp_50_vehicle_medium_demand_seed_1_initial` と `..._initial_decision_trace` | 成立取引3件。最終成果物ではない |
| 50台。arrival未観測の一律停止を外した後、offset 0容量補充漏れが残る途中成果物 | `research_outputs/trial/tvt_mp_50_vehicle_medium_demand_seed_1_passage_resolution_v2` と `..._passage_resolution_v2_decision_trace` | 成立取引13件。最終成果物ではない |
| 50台。容量補充修正後の最新成果物 | `research_outputs/trial/tvt_mp_50_vehicle_medium_demand_seed_1_capacity_refill_v3` と `..._capacity_refill_v3_decision_trace` | 成立取引10件。本節の最新結果 |

既存の10台成果物と、上記の途中50台成果物は削除も上書きもしていない。

## 1. 50台trial条件

位置付けは、正式実験ではなく、2流入1流出の単純ネットワークを維持したまま需要だけを増やすtrialである。

- Vehicle数は50台。`orig_a` 25台、`orig_b` 25台。
- participatingは35台。nonparticipatingは15台。
- 出発時刻はT=5からT=38。平均投入率は50/34、約1.47台/timestep。
- traffic seedは0。VOT seedは1。
- evaluationはT=0から299。internal TSIZEは330。
- baseline horizonは30。max candidate Visit countは10。clearanceは1 timestep。
- 単車線。merge NodeのみTVT-MP対象。
- 既存10台scriptと既存成果物は上書きしない。50台用scriptと一意なdirectoryを使う。

新規scriptは次である。

- `research_scripts/run_tvt_mp_50_vehicle_medium_demand_trial.py`
- `research_scripts/diagnose_tvt_mp_50_vehicle_medium_demand_decision_trace.py`

診断は10台trialと同じdriver wrapper方式である。T=0から299を保存する。trial CSVとの再現一致を検証する。50台trialで必要になった次のfieldを追加した。

- `decision_window_visit_count` / keys
- `remaining_decision_window_visit_count` / keys
- `unresolved_undetermined_visit_count` / keys
- `p_minus_one_eligible_visit_count_before_limit`
- `candidate_limit_reached`
- `right_of_entry_selection_status`

意思決定窓、remaining、trade_scopeを選ぶ母集団、trade_scope、拘束順位は同一視しない。

## 2. remaining 0件とunresolved arrivalの契約不整合

最初の50台trial実行で次のRuntimeErrorが発生した。完走成果物は残っていない。

- remaining decision windowが空。
- candidate build statusが`NOT_BUILT_UNRESOLVED_ARRIVALS`。
- final-rankは、remainingが空なら`NOT_BUILT_NO_RIGHT_OF_ENTRY`でなければならないとして拒否した。

原因はステージ間契約の矛盾である。right-of-entry選定が`unresolved_undetermined_visits`をremaining空判定より先に処理していた。final-rank側は、remaining 0件なら`NO_RIGHT_OF_ENTRY` / `NO_VISITS_TO_CONFIRM`を要求していた。

確定した契約は次である。

- remainingが0件なら、今回TVT検討するVisitも確定するVisitもない。
- 別のVisitにarrival未観測があっても、right-of-entry statusは`NO_RIGHT_OF_ENTRY`。
- candidate build statusは`NOT_BUILT_NO_RIGHT_OF_ENTRY`。
- final-rank statusは`NO_VISITS_TO_CONFIRM`。
- arrival未観測Visitは後の意思決定へ残る。

修正は、`uxsim/order_control_tvt_right_of_entry_selection.py`でremaining空を先に判定することである。関連テストを更新した。final-rankの防御契約は維持した。

この修正後、50台trialは最初の例外を越えて完走した。その保存先が`seed_1_initial`である。成立取引は3件で、意思決定時刻はT=14、90、95である。これはarrival未観測の一律停止が残る途中成果物である。

## 3. arrival未観測を一律BLOCKERとしていた過剰停止

`seed_1_initial`の診断では、23 timestepで次が発生した。

- remaining decision-window Visitは1件。
- `unresolved_undetermined_visits`は1件以上。
- right-of-entryは未選択。
- build statusは`NOT_BUILT_UNRESOLVED_ARRIVALS`。
- final rankはremaining 1件をbaseline fallbackで確定。

当初は正式設計どおりと解釈した。時間関係の再検証で、その解釈は過剰停止だと確定した。論理は第4巻の同日付節に書いた。要点だけ再記する。

- Pは到着時刻からの推定ではない。同じbaseline forkで対象VehicleがNodeを通過した`W.T`である。
- baseline forkはPで早期終了せず、開始Tからhorizon末尾まで実行する。
- arrival未観測Visitはfork処理期間中に対象Nodeへ到着していない。
- Pはfork処理期間内でのみ観測される。
- したがってarrival未観測VisitはP−1以前に到着せず、今回のP−1母集団には入らない。
- arrival未観測とpassage未観測は別である。

修正後の処理は、remaining 0件なら`NO_RIGHT_OF_ENTRY`、remaining 1件以上なら先頭をright-of-entryとする。P未観測なら`UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`。Pが観測済みなら`baseline_arrival_timestep is None`のVisitをP−1母集団外として除外する。`baseline_arrival_timestep <= P−1`のVisitだけを候補母集団へ含める。その母集団のうち候補上限内で必要なbaseline passageが未観測なら`UNRESOLVED_CANDIDATE_PASSAGES`。情報不足を経済的不成立へ変換しない。情報不足時はremaining意思決定窓全体をbaseline順位で確定する。意思決定窓内だがP−1母集団外、またはtrade_scope外のVisitも、最終順位処理でbaseline順位により確定する。

旧status `UNRESOLVED_BASELINE_ARRIVALS`と`NOT_BUILT_UNRESOLVED_ARRIVALS`は、古い保存結果や手製テスト結果を読み得る下流互換のため残る場合がある。前者は旧right-of-entry選定status、後者は旧candidate Visit集合構築statusである。現行の通常処理経路では生成しない。

修正ファイルは次である。

- `uxsim/order_control_tvt_right_of_entry_selection.py`
- `uxsim/order_control_tvt_candidate_visit_set.py`
- 関連テスト
- 50台診断scriptの契約検査

関連テスト415件が成功した。全テストsuiteは実行していない。

修正効果は、成立取引が3件から13件へ増えたこと、`NOT_BUILT_UNRESOLVED_ARRIVALS`が23件から0件になったことである。旧処理が、本来評価可能だった候補をarrival未観測だけで落としていた。

この13件は`passage_resolution_v2`に保存した。意思決定時刻はT=14、20、23、42、47、56、59、62、65、76、79、82、87である。容量補充問題が残る途中成果物であり、最終成果物ではない。

## 4. candidate局所仮想計算offset 0の容量補充漏れ

`passage_resolution_v2`のT=56とT=65では、buyer・sellerともcandidate passageよりactual passageが1 timestep早かった。取引対象だけでなく、決定後のbinding通過列全体がcandidate側で1 timestep遅れていた。順位列とclearance間隔は一致し、時刻だけが一様にずれていた。

T=56の代表例は次である。

- 実Worldでは`veh_b12`はT=56に通過した。
- candidate局所仮想では`veh_b12`は仮想T=56で通過試行された。skip理由は`outlink_inflow_capacity_unavailable`である。通過は仮想T=57だった。
- この1 timestep遅れが後続clearance列へ伝播した。
- T=56取引のbuyer `veh_b15`はcandidate 66、actual 65。seller `veh_a13`はcandidate 68、actual 67。
- T=65も同じ開始境界である。offset 0で`veh_b15`が同じ流入容量不足により一時スキップされ、取引のcandidate passageがactualより1 timestep遅れた。

原因は処理順の不一致である。実Worldは、driver、Link容量補充、Node容量補充、Node transferの順である。candidate局所仮想はdriver時点のsnapshotを使うが、offset 0では容量補充なしでbinding transferしていた。容量補充は仮想T+1へ進むときに初めて実施されていた。offset 0だけ補充前容量で通過を判定していた。

これは正常な予測誤差ではない。candidate局所仮想計算の実装不整合である。

修正契約、処理順、baseline仮想計算には同じ修正が不要であることは、第4巻の同日付節に書いた。実装は次である。

- `refill_tvt_mp_candidate_local_capacity_at_current_timestep`を追加した。
- `advance_tvt_mp_candidate_virtual_time_one_step`から容量補充を分離した。
- `_capacity_refilled_virtual_timesteps`により同一時刻の二重補充を拒否する。

修正ファイルは次である。

- `uxsim/order_control_tvt_mp_candidate_virtual_time.py`
- `uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`
- 関連テスト

限定テスト168件が成功した。対象はcandidate virtual time、candidate local virtual calculation、binding transfer、unbound FCFS、outlink boundary、local vehicle advanceである。全テストsuiteは実行していない。

## 5. 容量補充修正後の最新50台trial

最新成果物は`capacity_refill_v3`とそのdecision traceである。

- driver call数は300。
- completed tripsは50 / 50。
- right-of-entry選定は25 timestep。
- `baseline_information_complete`は25。
- `no_right_of_entry`は275。
- concrete buyer candidateの合計は14。
- general trade rank candidateの合計は14。
- 1意思決定当たり最大候補は1。
- FIFO trueは14。FIFO falseは0。
- local resolvedは14。local unresolvedは0。
- economically feasibleは10。economically infeasibleは4。
- selected transactionsは10。
- selection reasonは全10件`unique_maximum_surplus`。
- buyer数比較は0。local RNGは0。candidate limit reachedは0。
- snapshot固定集合外baseline passageは4件。
- selected transaction timestepsはT=14、20、23、32、43、52、57、60、81、90。
- trial CSVと診断再simulationの成立時刻は完全一致した。

予測対実績は次である。

- buyer・seller計20 Visit。
- actual observedは20。actual unobservedは0。
- candidate passageとactual passageの完全一致は20 / 20。
- 非0差は0。最大絶対差は0 timestep。
- buyer satisfiedは10 / 10。seller satisfiedは10 / 10。

v2で見られた1 timestep差は、正常な予測誤差ではなくoffset 0容量補充漏れが原因だった。修正後、その差は解消した。ただしcandidate予測とactualの一致は、実装全体の正しさの十分条件ではない。単純ネットワークで、candidate計算後に結果を変える外乱が少ないため一致が自然だった可能性がある。

## 6. 未確認事項と次の直接作業

まだ詳細確認していない事項は次である。

- 経済的不成立4件のG、R、surplusと不成立理由。
- buyer候補なしの各時刻の理由分類。nonparticipating物理先頭による遮断、取引相手なし、その他を分ける。
- snapshot固定集合外baseline passage 4件の代表追跡。
- 10成立取引すべての詳細反復監査は行わない。

今回の50台中程度高需要trialでは発生していないものは次である。

- 複数buyer
- 複数seller
- 複数concrete buyer candidate
- 複数general trade rank candidate
- surplus比較による複数候補選択
- buyer数比較
- local RNG
- FIFO false
- local unresolved
- candidate limit N=10到達
- nonparticipatingを含むtrade_scope
- actual未観測
- buyerまたはseller unsatisfied

次に推奨する作業は次の順である。

1. 最新`capacity_refill_v3`について、経済的不成立4件をまとめて確認する。
2. buyer候補なしの理由を分類する。
3. snapshot固定集合外baseline passageの代表ケースを確認する。
4. その後、50台trial監査の終了可否を判断する。
5. 未発生ケースを得るため、需要配置や参加配置を変更した追加trialが必要か判断する。

## 7. capacity_refill_v3の追加監査結果

本小節は、前節で未確認として残していた事項について、その後に実施した追加監査の記録である。前節の未確認一覧は当時の記録として残す。`capacity_refill_v3`の既存集計は上書きしない。

### 7.1 経済的不成立4件

4件とも、FIFO違反、局所仮想計算未解決、情報不足ではない。

共通は次である。

- buyer 1台。seller 1台。trade_scope 2台。
- FIFO preservedはtrue。local virtual calculation resolvedはtrue。
- buyerはbaselineより3 timestep短縮。sellerはbaselineより1 timestep遅延。
- infeasibility reasonは`total_buyer_value_below_required_compensation`。
- G < Rにより経済的不成立。candidateは選択されない。
- remaining意思決定窓はbaseline順位で確定。

各件は次である。

- T=50。buyer `veh_a13`。seller `veh_b12`。G = 0.01550377470139688。R = 1.4569398477533346。surplus = -1.4414360730519378。buyer VOTが非常に低く、seller補償を大幅に賄えない例である。
- T=63。buyer `veh_b17`。seller `veh_a16`。G = 2.5310757582650676。R = 7.86461383460219。surplus = -5.333538076337122。seller VOTが非常に高く、必要補償が大きい例である。
- T=79。buyer `veh_b21`。seller `veh_a20`。G = 0.3364092245338354。R = 0.4077190272970466。surplus = -0.0713098027632112。
- T=84。buyer `veh_b22`。seller `veh_a22`。G = 0.22621441259039682。R = 0.2834800352717827。surplus = -0.05726562268138591。

T=79とT=84は成立境界に比較的近いが、完全比較によりG < Rなので不成立である。Toleranceや丸めは使用していない。

### 7.2 concrete buyer候補0件の11時刻

right-of-entryが選定されたが、concrete buyer候補が0件だった意思決定は11時刻である。

分類は次である。

1. 反対側のP−1母集団先頭Visitがnonparticipatingで、単車線物理prefixを遮断したケースは10件。
2. right-of-entry以外の取引相手が存在しなかったケースは1件。

nonparticipatingによる遮断は次である。

- T=12: `veh_a1`
- T=16: `veh_b3`
- T=28: `veh_a7`
- T=35: `veh_b8`
- T=39: `veh_b9`
- T=46: `veh_a12`
- T=65: `veh_a17`
- T=69: `veh_a18`
- T=75: `veh_b20`
- T=86: `veh_a23`

共通は次である。

- P−1母集団はright-of-entryを含む2台。
- 相手側Visitはnonparticipating。
- 単車線上でそのVisitを越えて後続participating Visitをbuyer prefixへ含めない。
- concrete buyer候補は0件。経済評価前に候補形成が終了する。
- remaining意思決定窓をbaseline順位で確定する。

取引相手なしはT=99である。right-of-entryは`veh_b25`。P−1母集団はright-of-entry自身の1台だけである。concrete buyer候補は0件。baseline順位で確定する。

解釈は次である。nonparticipating 15台の影響は、今回の成立trade_scopeへ入る形ではなく、主としてbuyer候補形成を物理prefixで遮断する形で現れた。nonparticipatingを含む成立trade_scopeは今回発生していない。

### 7.3 snapshot固定集合外baseline交通

診断集計では、snapshot固定集合外baseline passageは4件である。

全件は次である。

- T=12 baseline fork。
  - `veh_b5`。arrival_sourceは`current_visit_outside_snapshot_set`。snapshot_fixedはFalse。baseline arrivalはT=31。baseline passageはT=35。baseline passage rankは9。inlinkは`in_b`。
  - `veh_b6`。arrival_sourceは`current_visit_outside_snapshot_set`。snapshot_fixedはFalse。baseline arrivalはT=35。baseline passageはT=39。baseline passage rankは11。inlinkは`in_b`。
  - `veh_a6`。arrival_sourceは`current_visit_outside_snapshot_set`。snapshot_fixedはFalse。baseline arrivalはT=37。baseline passageはT=41。baseline passage rankは12。inlinkは`in_a`。
- T=14 baseline fork。
  - `veh_b7`。arrival_sourceは`current_visit_outside_snapshot_set`。snapshot_fixedはFalse。baseline arrivalはT=39。baseline passageはT=43。baseline passage rankは13。inlinkは`in_b`。

T=12の代表確認は次である。

- right-of-entryは`veh_b1`。Pは19。P−1は18。
- P−1母集団は`veh_b1`と`veh_a1`の2台。
- snapshot固定集合外3台のarrivalはT=31、35、37であり、P−1母集団とは無関係である。
- T=18からT=31まで交通が空だったわけではない。その間にはsnapshot固定集合内の後続Visitが連続して到着・通過した。snapshot固定集合外Visitはその後続交通へ混入した。

T=12のbaseline passage列は次である。

1. `veh_b1`、T=19、snapshot固定
2. `veh_a1`、T=21、snapshot固定
3. `veh_b2`、T=23、snapshot固定
4. `veh_a2`、T=25、snapshot固定
5. `veh_b3`、T=27、snapshot固定
6. `veh_a3`、T=29、snapshot固定
7. `veh_b4`、T=31、snapshot固定
8. `veh_a4`、T=33、snapshot固定
9. `veh_b5`、T=35、snapshot固定集合外
10. `veh_a5`、T=37、snapshot固定
11. `veh_b6`、T=39、snapshot固定集合外
12. `veh_a6`、T=41、snapshot固定集合外

baseline passage rank 10は欠落していない。snapshot固定集合外だけを抽出したため、9、11、12となった。10位の`veh_a5`はsnapshot固定集合内である。

T=12のsnapshot固定集合外3台は、candidate Visit集合、concrete buyer候補、general trade rank候補、FIFO評価、candidate局所仮想評価、economic evaluationのいずれにも含まれなかった。

結論は次である。snapshot固定集合外Visitは時刻Tの候補へ追加しない。baseline交通としては到着後に物理通過する。候補形成とbaseline交通再現の分離は設計どおりである。

### 7.4 先頭nonparticipating Visitの先行順位確定

意思決定窓内の先頭nonparticipating Visitをbaseline順位で先行確定した事例は14件である。

- T=18: `veh_b3`
- T=26: `veh_a6`
- T=30: `veh_a7`
- T=37: `veh_b8`
- T=41: `veh_b9`
- T=48: `veh_a12`
- T=55: `veh_b14`
- T=67: `veh_a17`
- T=71: `veh_a18`
- T=73: `veh_b19`
- T=77: `veh_b20`
- T=88: `veh_a23`
- T=93: `veh_a25`
- T=95: `veh_b24`

全14件の共通処理は次である。

1. 該当nonparticipating Visitが意思決定窓内先頭である。
2. baseline順位で先行確定する。
3. その時刻のremainingは0件である。
4. right-of-entryはない。
5. final-rank statusは`NO_VISITS_TO_CONFIRM`である。
6. preconfirmed Visitをfinal-rankで重複確定しない。

このtrialでは、先頭nonparticipating先行確定後もremaining参加Visitが残るケースは発生していない。全14件とも、先行確定後のremainingは0件だった。

### 7.5 trade_scope外かつ意思決定窓内Visitのbaseline確定

成立10件について確認した。

選択されたtrade_scopeより外側に、未確定の意思決定窓内Visitが残った事例は0件である。したがって、trade_scope内を採用候補順位で確定し、残る意思決定窓内Visitをbaseline順位で確定する混合処理は今回発生していない。

この分岐は未発生ケースとして残る。次の非対称需要trialでは、意思決定窓内に複数Visitが残る状況を増やすことで、観測可能性が高まる。

### 7.6 Tで順位確定したVisitのT+1再登場防止

確認方法は次である。各Tで、先頭nonparticipatingとして先行確定されたVisitと、selected candidateまたはbaseline final-rankで確定されたVisitを、順位確定Visitとして収集した。T+1で、decision window、remaining decision window、candidate Visit集合、trade_scopeへ再登場していないかを比較した。

結果は次である。

- TからT+1への確定Visit確認は50 Visit。
- 再登場違反は0件。

したがって、Tで意思決定窓内に入り、順位確定されたVisitは、T+1でbaseline到着予測上引き続き6 timestep以内に位置し得ても、順位台帳で確定済みなので未確定Visit集合から除外される。その結果、T+1の意思決定窓、remaining、candidate Visit集合、trade_scopeへ再登場しない。移動する意思決定窓によって同じVisitを重複して順位確定または取引する問題は発生していない。

代表例は、T=12で`veh_b1`と`veh_a1`を確定し、T=13では両Visitとも、意思決定窓、remaining、candidate Visit集合、trade_scopeのいずれにも再登場しないことである。

## 8. 50台中程度高需要trial監査の終了判断と次trial

現在の50台中程度高需要trial監査は、この範囲で終了する。

監査済みは次である。

- trialと診断再simulationの成立時刻一致
- candidate passageとactual passageの比較
- economic infeasible候補4件
- buyer候補0件11時刻
- snapshot固定集合外baseline交通
- 先頭nonparticipating先行確定
- trade_scope外かつ意思決定窓内Visitの有無
- 確定済みVisitのT+1再登場防止
- 全50台completed
- Node別assigned/actual関連集計
- FIFO、local resolved、候補上限、RNG等の全体集計

終了理由は次である。

- 成立10件はすべてbuyer 1台、seller 1台、唯一候補の同型である。
- 同じ型の詳細監査を反復しても新しい情報が少ない。
- 今回発生しなかった分岐を得るには、需要配置を変える方が有効である。
- candidateとactualの一致は正しさの十分条件ではないという留保は維持する。

今回未発生は次である。

- 複数buyer
- 複数seller
- 複数concrete buyer candidate
- 複数general trade rank candidate
- 複数候補間のsurplus比較
- buyer数比較
- local RNG
- FIFO false
- local unresolved
- candidate limit N=10到達
- nonparticipatingを含む成立trade_scope
- trade_scope外かつ意思決定窓内Visitのbaseline確定
- 先頭nonparticipating先行確定後にremaining参加Visitが残るケース
- actual未観測
- buyerまたはseller unsatisfied

次のtrial方針は、利用者の希望に沿う。一方向からの進入を高密度にし、他方からの進入を低密度にする。「一方向はギチギチ、他方向はスキスキ」の非対称需要trialを行う。

目的は次である。

- 高密度側に複数Vehicleの物理列を形成する。
- 低密度側のright-of-entryに対し、高密度側から複数buyer候補が形成される可能性を高める。
- 流入方向によるbuyer・sellerの発生非対称を確認する。
- 複数buyer、複数seller、複数候補、複数候補間のsurplus比較、buyer数比較、local RNG、nonparticipatingのprefix遮断、trade_scope外かつ意思決定窓内Visitのbaseline確定、候補上限への接近の発生可能性を高める。

次の直接作業は、非対称需要trialの車両配分と出発時刻を簡潔に決めることである。現時点では40対10、35対15、45対5等を確定していない。需要配分は次の作業で決める。ネットワーク、単車線、merge Node、horizon 30、候補上限N=10、clearance 1等を原則維持する案から始める。

# 50台非対称需要trialと2流入単車線1共通outlink mergeの候補構造分析（2026-10-13）

本節は50台中程度高需要trialの後に行った非対称需要trialの時系列記録である。

core design上の正本は、第4巻末尾の「2流入単車線1共通outlink mergeのP−1候補構造と将来の二層意思決定窓案（2026-10-13）」である。

本節はtrial条件、成果物、実行結果、診断集計、考察経緯を記録する。

現在の1共通outlink mergeで確認した事項と観測結果を、複数outlinkや十字路へ一般化しない。

## 1. trialと診断の成果物

新規trial script:

- research_scripts/run_tvt_mp_50_vehicle_asymmetric_demand_trial.py

新規診断script:

- research_scripts/diagnose_tvt_mp_50_vehicle_asymmetric_demand_decision_trace.py

trial directory:

- research_outputs/trial/tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial

diagnostic directory:

- research_outputs/trial/tvt_mp_50_vehicle_asymmetric_demand_seed_1_initial_decision_trace

これらは既存の中程度高需要50台trialとは別の成果物である。既存成果物は削除も上書きもしていない。

## 2. 非対称需要trial条件

- Vehicle総数50台
- 高密度側はorig_a、40台
- veh_a1からveh_a40
- orig_aはT=5からT=44まで毎timestep 1台
- 低密度側はorig_b、10台
- veh_b1からveh_b10
- orig_bの出発時刻はT=5、9、13、17、21、25、29、33、37、41
- T=5ではorig_aとorig_bの両方から出発
- 同一時刻のspec順はorig_a、orig_b
- 全50台participating
- nonparticipating 0台
- declared VOTはtrue VOTと同値
- traffic seed 0
- VOT seed 1
- evaluation T=0から299
- INTERNAL_TSIZE 330
- baseline horizon 30
- max candidate Visit count 10
- clearance 1 timestep
- 2流入1流出
- 両inlinkは単車線
- 両inlinkは同じ1本のoutlinkへ合流
- merge NodeだけTVT-MP対象

## 3. trial実行結果

- evaluation終了検証は全項目合格
- World.T = 300
- completed trips 50 / 50
- transaction count 7
- feasible 7
- infeasible 0
- unavailable 0
- buyer Visit 7
- seller Visit 7
- nonparticipating Visit 0
- trialの総実行時間は約32.3秒

成立取引時刻:

- T=20
- T=24
- T=26
- T=36
- T=38
- T=44
- T=45

## 4. 診断結果

- driver wrapper call数 300
- decision summary 300行
- baseline_information_complete 40
- not_built_no_right_of_entry 260
- final-rank selected_candidate_ranks 7
- final-rank baseline_fallback_ranks 33
- final-rank no_visits_to_confirm 260
- right-of-entry selected 40
- right-of-entry no_right_of_entry 260
- concrete buyer candidate合計12
- general trade rank candidate合計12
- FIFO true 12
- FIFO false 0
- local resolved 12
- local unresolved 0
- economic evaluation candidate 12
- economically feasible 7
- economically infeasible 5
- selected candidate 7
- buyer数比較 0
- local RNG 0
- candidate limit reached 0
- snapshot固定集合外baseline passage 43件
- trial CSVと診断再simulationの成立時刻は完全一致

非対称需要向け集計:

- 1意思決定当たり最大candidate Visit数 2
- P−1 eligible count before limitの最大 2
- concrete buyer候補数の最大 1
- general trade rank候補数の最大 1
- candidate内buyer数の最大 1
- candidate内seller数の最大 1
- 選択trade_scopeの最大件数 2
- 複数buyer発生時刻なし
- 複数seller発生時刻なし
- 複数concrete buyer candidate発生時刻なし
- 複数general trade rank candidate発生時刻なし
- 複数候補間surplus比較なし
- buyer数比較なし
- local RNGなし
- candidate limit到達なし
- trade_scope外かつ意思決定窓内Visitのbaseline確定なし
- 選択取引buyerはorig_a 4件、orig_b 3件
- 選択取引sellerはorig_a 3件、orig_b 4件

## 5. 長い物理列とP−1候補母集団の違い

高密度側orig_aには長い物理列が形成された。低密度側orig_bがright-of-entryになった時刻でも、orig_aのsnapshot物理列には多数のVehicleが存在した。

例:

- T=44ではorig_bのveh_b9がright-of-entry
- P=52
- orig_aのsnapshot物理列にはveh_a11からveh_a30まで存在
- しかしcandidate Visitはveh_b9とveh_a14の2台だけ
- P−1候補母集団も2台

次を同一視しない。

- inlink上に物理的に存在するVehicle
- 順位未確定Visit
- baseline arrivalがP−1以前のVisit
- candidate Visit
- trade_scope内Visit

過去の意思決定で順位確定済みのVisitは、未確定Visit集合から除外される。未確定でもbaseline arrivalがP−1より後なら、今回の候補母集団へ入らない。

## 6. 複数sellerが生じない理由

right-of-entryをS、そのbaseline passage timestepをPとする。

Sと同じ単車線inlinkの後続車S2はSを追い越せない。S2が対象Nodeへ到着できるのは、早くてもSが物理先頭から外れるP以降である。

候補母集団条件は、baseline_arrival_timestep <= P−1 である。

したがってS2はSに基づくP−1候補母集団へ入らず、同じ取引のsellerにならない。

この結論は、同一inlinkが単車線で追越しがない現行条件を前提とする。

## 7. 現在のmergeにおける複数buyerの観測と未確認事項

ここは、両inlinkが同じ1本のoutlinkへ合流する現在のmergeに限定する。

right-of-entryをS、そのbaseline passage timestepをPとする。反対側inlinkの物理先頭車をB1、その後続車をB2とする。

40対10の非対称需要trialでは、長いorig_a物理列があっても最大P−1母集団は2台だった。candidate内buyer数とseller数の最大は各1台だった。trade_scope最大2台、general trade rank candidate最大1件だった。これは確認済みの観測結果である。今回のtrialでは、反対側inlinkからP−1候補母集団へ入ったbuyerは物理先頭B1の1台だけだった。

共通outlink側の容量不足または入口空間不足でSが通過できない場合、B1も同じ制約を受ける。この場合、B1がSを越えて先行通過し、B2を早期に物理先頭へ進めることはできない。

今回のtrialの限定調査では、比較可能12件のすべてでB1はSより先にbaseline通過せず、全件でB1 passage = P+2だった。したがって、今回のtrialにはB1先行通過事例がなかったことを確認済みである。一方、S側inlink固有またはS固有の一時スキップを意図的に生じさせる別条件を含め、現在のmergeのあらゆる交通状態でB1先行通過が絶対に不可能であることは未証明である。したがって、複数buyerが構造的に絶対不可能とはまだ記録しない。

複数outlinkでは、さらに次が起こり得る。

- Sの進路outlinkだけが混雑
- B1の進路outlinkは通過可能
- Sが一時スキップ
- B1がSより先に通過
- B2が早く物理先頭となる

この場合、B2がSのP−1以前に到着する可能性を否定できない。したがって、複数buyerが生じないという説明を十字路や複数outlinkへ一般化しない。

## 8. 現段階の限定的結論と未確認事項

確認済み:

- 同一単車線inlink上のS後続車S2は、Sに基づくP−1候補母集団へ入らず、同じ取引のsellerにならない
- 今回のtrialでは複数buyer・複数seller・複数候補は発生しなかった
- 共通outlink側制約はB1の先行通過を妨げる
- 40対10の非対称需要trialでは、長いorig_a物理列があっても最大P−1母集団は2台だった
- candidate内buyer数とseller数の最大は各1台だった
- trade_scope最大2台、general trade rank candidate最大1件だった

今回のtrialの限定調査により、次は確認済みである。

- 比較可能ケース12件すべてで、B1はSより先にbaseline通過しなかった
- B1後続B2を観測できた11件すべてで、B2 arrival > P−1であった
- 今回のtrialで複数buyerが形成されなかった直接的な時間関係を確認した
- 今回のtrialに関する原因分析は完了した

一般命題上の留保:

- S側固有の一時スキップを意図的に発生させた別条件で、B1がSより先に通過し、B2がP−1以前に到着できるかは未検証である
- 現行mergeで複数buyerが構造的に可能か不可能かの最終判断は、4十字路trial等の結果を踏まえて行う
- 複数buyerが構造的に絶対不可能であることは、現時点では記録しない

これらの確認済み事項と観測結果を、複数outlink、異なる進路、右左折、3流入以上、複車線、進路別待ち列等へ一般化しない。

## 9. S・B1通過順とB2到着時刻の限定調査

本小節は、50台非対称需要trialにおいて、right-of-entry Sと反対側inlink先頭B1のbaseline通過順、およびB1後続B2のbaseline arrival timestepを確認した結果を記録する。

### 比較可能12件（SとB1がともにcandidate Visit）

- T=12: S veh_b1:1、P 19、B1 veh_a1:1 passage 21
- T=16: S veh_b2:1、P 24、B1 veh_a3:1 passage 26
- T=20: S veh_b3:1、P 28、B1 veh_a4:1 passage 30
- T=21: S veh_a5:1、P 31、B1 veh_b4:1 passage 33
- T=24: S veh_b4:1、P 33、B1 veh_a6:1 passage 35
- T=26: S veh_a7:1、P 36、B1 veh_b5:1 passage 38
- T=32: S veh_a9:1、P 39、B1 veh_b6:1 passage 41
- T=33: S veh_a10:1、P 43、B1 veh_b7:1 passage 45
- T=36: S veh_b7:1、P 45、B1 veh_a11:1 passage 47
- T=38: S veh_a12:1、P 48、B1 veh_b8:1 passage 50
- T=44: S veh_b9:1、P 52、B1 veh_a14:1 passage 54
- T=45: S veh_a15:1、P 55、B1 veh_b10:1 passage 57

集計:

- 比較可能ケース12件
- B1がSより先にbaseline通過したケース0件
- 全件でSが先に通過した
- 全件でB1 passage = P+2

### B2を観測できた11件

- T=12: B2 veh_a2、arrival 21、P−1 18
- T=16: B2 veh_a4、arrival 26、P−1 23
- T=20: B2 veh_a5、arrival 30、P−1 27
- T=21: B2 veh_b5、arrival 34、P−1 30
- T=24: B2 veh_a7、arrival 35、P−1 32
- T=26: B2 veh_b6、arrival 38、P−1 35
- T=32: B2 veh_b7、arrival 42、P−1 38
- T=33: B2 veh_b8、arrival 46、P−1 42
- T=36: B2 veh_a12、arrival 47、P−1 44
- T=38: B2 veh_b9、arrival 50、P−1 47
- T=44: B2 veh_a15、arrival 54、P−1 51

集計:

- B2観測11件
- B2 arrival <= P−1は0件
- 全件でB2 arrival > P−1
- B2 arrivalはP+2またはP+3
- T=45は反対側inlinkにB1後続B2が存在しないため、B2未観測

代表例T=44:

- S = veh_b9:1、P = 52、P−1 = 51
- B1 = veh_a14:1、B1 baseline arrival = 50、B1 baseline passage = 54
- B2 = veh_a15、B2 baseline arrival = 54、B2 baseline passage = 55
- B2 arrival 54 > P−1 51

結論:

- 今回のtrialではB1先行通過は発生しなかった。
- B2はすべてP−1より後に到着した。
- したがって今回のtrialで複数buyerが形成されなかった直接的な時間関係を確認した。
- 今回のtrialに関する原因分析は完了した。
- 一般的な構造的不可能性は証明していない。

## 10. 二層意思決定窓案の位置付け

第4巻の2026-10-13節に記録した二層案を参照する。

- 近接層: 到着まで1〜3 timestep
- 遠方層: 到着まで4〜6 timestep
- 非当事者の近接層はbaseline順位で確定
- 非当事者の遠方層は未確定のまま後続意思決定へ残す

この案は未採用・未実装である。現在の1共通outlink mergeで複数sellerを発生させる方法とは位置付けない。複数buyerについては、現在のmergeで絶対に発生しないとまだ確定していない。二層案が複数buyer形成へ影響するかも現時点では未確認である。二層案は現在の非対称需要trialおよび今回の限定調査だけでは採用しない。4十字路ネットワークtrialの結果を確認した後で、導入適否を判断する。

## 11. 次のtrial方針

次のtrialは4つの十字路を含むネットワークで行う。非対称需要trialの限定調査は完了し、原因分析は一区切りとする。

確認対象:

- 複数流入
- 複数流出
- 異なる進路
- 右左折
- 単車線
- 複数TVT-MP対象Node
- 3流入以上での複数buyer・複数seller
- 複数outlinkでSが一時スキップされB1が先行通過するケース
- 進路別物理条件
- 複数Node間の交通状態
- 後続Node訪問との順位整合
- baseline予測とcandidate予測への交差点間交通の影響

次の直接作業:

1. 4十字路ネットワークtrialの条件整理へ進む。
2. ネットワーク形状、OD、進路、右左折、TVT-MP対象Node、需要条件を整理する。
3. 二層案はまだ実装しない。

# 単独十字路12台trialの実行・候補21件・時系列監査（2026-10-14）

- 本節は、単独十字路12台trialの条件、実行結果、診断集計、候補形成、経済評価、時系列監査を記録する。
- core design上の整理と次段階は、第4巻末尾の
  「単独十字路4流入4流出trialで確認した候補形成構造と次段階（2026-10-14）」
  を正本とする。
- 今回のtrialは、小規模な4流入・4流出条件でTVT-MPの基本動作を監査するためのtrialである。
- 同一inlink上の連続する複数buyer・複数sellerを検証する高需要trialではない。

## 1. scriptと成果物

trial script:
- research_scripts/run_tvt_mp_single_cross_intersection_12_vehicle_trial.py

診断script:
- research_scripts/diagnose_tvt_mp_single_cross_intersection_12_vehicle_decision_trace.py

trial directory:
- research_outputs/trial/tvt_mp_single_cross_intersection_12_vehicle_seed_1_initial

diagnostic directory:
- research_outputs/trial/tvt_mp_single_cross_intersection_12_vehicle_seed_1_initial_decision_trace

trial出力:
- manifest.json
- run_summary.txt
- tvt_mp_nodes.csv
- tvt_mp_scenario.csv
- tvt_mp_transactions.csv
- tvt_mp_vehicles.csv
- tvt_mp_visits.csv
- vehicle_vot.csv

診断出力:
- decision_summary.csv
- candidate_summary.csv
- selected_result_summary.csv
- decision_trace.json

既存のtrial・診断成果物は削除も上書きもしていない。

## 2. ネットワーク条件

Nodeは5つ。

- intersection
- north
- east
- south
- west

中央Node:
- intersection
- TVT-MP対象
- inlink 4本
- outlink 4本
- clearance 1 timestep

Linkは8本。

進入Link:
- north_to_intersection
- east_to_intersection
- south_to_intersection
- west_to_intersection

退出Link:
- intersection_to_north
- intersection_to_east
- intersection_to_south
- intersection_to_west

全Link:
- length 200 m
- 単車線
- free-flow speed 60000 / 3600 m/s
- UXsimの既定容量

経路:
- Vehicleにはoriginとdestinationだけを指定
- specified_routeは使用しない
- 固定Link列を使用しない
- UXsimの通常の動的経路選択を維持
- 迂回防止のための人工的なネットワーク制約は設けない

## 3. Vehicle条件

Vehicle総数:
- 12台

全Vehicle:
- participating
- nonparticipating 0台
- declared VOT = true VOT
- VOTは既存trialと同じlognormal生成
- TRAFFIC_SEED = 0
- VOT_SEED = 1

同一出発時刻のVehicleSpec順:
1. north
2. east
3. south
4. west

T=5:
- veh_n1: north -> south
- veh_e1: east -> west
- veh_s1: south -> north
- veh_w1: west -> east

直接経路ではstraightに相当する4 OD。

T=9:
- veh_n2: north -> east
- veh_e2: east -> south
- veh_s2: south -> west
- veh_w2: west -> north

直接経路ではleftに相当する4 OD。

T=13:
- veh_n3: north -> west
- veh_e3: east -> north
- veh_s3: south -> east
- veh_w3: west -> south

直接経路ではrightに相当する4 OD。

U-turn ODは設定していない。

ただし、movementはODから決めつけず、中央Nodeで実際に使用したinlinkとoutlinkから事後分類した。

## 4. 時間条件

- evaluation T=0から299
- INTERNAL_TSIZE = 330
- baseline horizon 30 timestep
- candidate上限N=10
- clearance 1 timestep
- EXPECTED_DRIVER_CALL_COUNT = 300
- timestep size 1秒

## 5. trial実行結果

- evaluation終了検証は全項目合格
- World.T = 300
- completed trips 12 / 12
- transaction count 2
- feasible 2
- infeasible 0
- unavailable 0
- buyer Visit 2
- seller Visit 6
- nonparticipating Visit 0

実行時間:
- setup / finalize 約14.487秒
- exec_simulation 約4.159秒
- total 約18.650秒

成立取引時刻:
- T=16
- T=20

## 6. 実現movementと経路結果

中央Nodeで実際に使用したinlinkとoutlinkから集計した結果:

- straight 4 Visit
- left 4 Visit
- right 4 Visit
- u_turn 0 Visit
- unknown 0 Visit
- intersection再訪Vehicle 0台

全12台について、計画ODに対応する直接movementが実現した。

予想外の迂回、U-turn、中央Node再訪は今回発生しなかった。

ただし、経路を固定した結果ではない。
UXsimの動的経路選択による今回の実現結果である。

## 7. decision trace診断結果

- driver wrapper call数 300
- decision summary 300行
- baseline_information_complete 3
- not_built_no_right_of_entry 297
- right-of-entry selected 3
- right-of-entry no_right_of_entry 297
- final-rank selected_candidate_ranks 2
- final-rank baseline_fallback_ranks 1
- final-rank no_visits_to_confirm 297
- 候補形成時刻:
  T=12、16、20
- concrete buyer candidate合計21
- general trade rank candidate合計21
- 1意思決定当たり最大concrete buyer candidate 7
- 1意思決定当たり最大general trade rank candidate 7
- FIFO true 21
- FIFO false 0
- local resolved 21
- local unresolved 0
- economic evaluation candidate 21
- economically feasible 8
- economically infeasible 13
- selected candidate 2
- buyer数比較による選択 0
- local RNG使用 0
- candidate limit到達 0
- snapshot固定集合外baseline passage 4件

selection reason:
- no_economically_feasible_candidate 1件
- unique_maximum_surplus 2件
- maximum_surplus_then_unique_maximum_buyer_count 0件
- final_tie_resolved_by_local_rng 0件

trial CSVの成立時刻と診断再simulationの成立時刻は完全一致した。

## 8. 候補形成の規模

T=12、16、20の各意思決定で:

- candidate Visit 4台
- P−1 eligible count before limit 4台
- concrete buyer candidate 7件
- general trade rank candidate 7件
- candidate内buyer最大3台
- candidate内seller最大3台

3時刻合計:
- candidate 21件
- 全21件でFIFO preserved
- 全21件でcandidate局所仮想計算resolved

複数buyerを含む候補:
- T=12、16、20で発生

複数sellerを含む候補:
- T=12、16、20で発生

複数候補間surplus比較:
- T=16、20で発生

今回形成された複数buyer・複数sellerは、それぞれ異なるinlinkに1台ずつ存在する構造だった。

同一inlink上の連続buyer・連続sellerは今回未確認である。

## 9. T=12第一波のbaseline

T=12時点の各inlink物理列:

north:
- veh_n1
- veh_n2

east:
- veh_e1
- veh_e2

south:
- veh_s1
- veh_s2

west:
- veh_w1
- veh_w2

第一波4台のbaseline arrivalはすべてT=18。

固定tiebreakerによるbaseline通過順:
1. veh_e1: arrival 18、passage 19
2. veh_s1: arrival 18、passage 21
3. veh_w1: arrival 18、passage 23
4. veh_n1: arrival 18、passage 25

right-of-entry:
- veh_e1
- P = 19
- P−1 = 18

4台すべてarrival <= P−1を満たした。

T=12の意思決定窓内Visit:
- veh_e1
- veh_s1
- veh_w1
- veh_n1

4台から7候補を形成した。

## 10. T=12の7候補と経済評価

候補1:
- buyer:
  veh_w1
- sellers:
  veh_e1
  veh_s1
- G = 0.17509189607316206
- R = 3.2445330405768478
- surplus = -3.0694411445036858
- economically infeasible

時間変化:
- veh_w1: 23 -> 19、4 timestep短縮
- veh_e1: 19 -> 21、2 timestep遅延
- veh_s1: 21 -> 23、2 timestep遅延

候補2:
- buyer:
  veh_s1
- seller:
  veh_e1
- G = 1.0442185618892235
- R = 2.2003144786876243
- surplus = -1.1560959167984008
- economically infeasible

時間変化:
- veh_s1: 21 -> 19、2 timestep短縮
- veh_e1: 19 -> 21、2 timestep遅延

候補3:
- buyers:
  veh_s1
  veh_w1
- seller:
  veh_e1
- G = 1.1317645099258045
- R = 4.400628957375249
- surplus = -3.2688644474494444
- economically infeasible

時間変化:
- veh_s1: 21 -> 19、2 timestep短縮
- veh_w1: 23 -> 21、2 timestep短縮
- veh_e1: 19 -> 23、4 timestep遅延

候補4:
- buyer:
  veh_n1
- sellers:
  veh_e1
  veh_s1
  veh_w1
- G = 3.2054925209733423
- R = 3.332078988613429
- surplus = -0.12658646764008674
- economically infeasible

時間変化:
- veh_n1: 25 -> 19、6 timestep短縮
- veh_e1: 19 -> 21、2 timestep遅延
- veh_s1: 21 -> 23、2 timestep遅延
- veh_w1: 23 -> 25、2 timestep遅延

候補5:
- buyers:
  veh_w1
  veh_n1
- sellers:
  veh_e1
  veh_s1
- G = 2.31208691005539
- R = 6.4890660811536955
- surplus = -4.1769791710983055
- economically infeasible

時間変化:
- veh_w1: 23 -> 19、4 timestep短縮
- veh_n1: 25 -> 21、4 timestep短縮
- veh_e1: 19 -> 23、4 timestep遅延
- veh_s1: 21 -> 25、4 timestep遅延

候補6:
- buyers:
  veh_s1
  veh_n1
- sellers:
  veh_e1
  veh_w1
- G = 3.1812135758714515
- R = 4.48817490541183
- surplus = -1.3069613295403784
- economically infeasible

時間変化:
- veh_s1: 21 -> 19、2 timestep短縮
- veh_n1: 25 -> 21、4 timestep短縮
- veh_e1: 19 -> 23、4 timestep遅延
- veh_w1: 23 -> 25、2 timestep遅延

候補7:
- buyers:
  veh_s1
  veh_w1
  veh_n1
- seller:
  veh_e1
- G = 2.2002620169169185
- R = 6.600943436062873
- surplus = -4.400681419145954
- economically infeasible

時間変化:
- veh_s1: 21 -> 19、2 timestep短縮
- veh_w1: 23 -> 21、2 timestep短縮
- veh_n1: 25 -> 23、2 timestep短縮
- veh_e1: 19 -> 25、6 timestep遅延

T=12では7候補すべて、
total_buyer_value_below_required_compensation
により不成立だった。

候補形成、FIFO、局所仮想計算の失敗ではない。

最も成立に近かったのは候補4であり、
surplus = -0.12658646764008674
だった。

内部計算ではToleranceや丸めを使わず、完全比較を行うため不成立である。

T=12の最終結果:
- no_economically_feasible_candidate
- 第一波4台をbaseline順位で確定

確定順位:
1. veh_e1
2. veh_s1
3. veh_w1
4. veh_n1

## 11. T=12候補4の局所仮想計算

対象:
- buyer veh_n1
- sellers veh_e1、veh_s1、veh_w1

拘束順位:
- veh_n1
- veh_e1
- veh_s1
- veh_w1

時系列:
- T=12〜17:
  4台ともNode未到着。
  not_arrived_at_target_nodeで一時スキップ。
- T=18:
  veh_n1、veh_e1、veh_s1、veh_w1がNodeへ到着。
  到着登録は通過試行後なので同時刻には通過しない。
- T=19:
  veh_n1通過。
  veh_e1はclearance未充足で停止。
- T=20:
  clearance待ち。
- T=21:
  veh_e1通過。
  veh_s1はclearance未充足で停止。
- T=22:
  clearance待ち。
  veh_n2、veh_e2がNodeへ到着。
- T=23:
  veh_s1通過。
  veh_w1はclearance未充足で停止。
  veh_s2がNodeへ到着。
- T=24:
  clearance待ち。
- T=25:
  veh_w1通過。
  veh_w2がNodeへ到着。
  取引対象4台の必要な通過観測が揃いresolved=True。

第2波Vehicleも局所仮想Worldの交通から除外されていない。

T=25の拘束順位外FCFS候補には、
- veh_n2
- veh_e2
- veh_s2
が存在した。

ただし、veh_w1通過直後のclearance不足により、veh_n2から停止した。

取引対象4台の観測が揃ったため、局所仮想計算はT=25で終了した。

## 12. T=16第二波のbaselineと候補形成

T=16時点では、各inlinkに3台ずつ存在した。

north:
- veh_n1
- veh_n2
- veh_n3

east:
- veh_e1
- veh_e2
- veh_e3

south:
- veh_s1
- veh_s2
- veh_s3

west:
- veh_w1
- veh_w2
- veh_w3

第一波4台はT=12で順位確定済み。

第一波baseline通過:
1. veh_e1: 19
2. veh_s1: 21
3. veh_w1: 23
4. veh_n1: 25

第二波baseline通過:
5. veh_e2: arrival 22、passage 27
6. veh_s2: arrival 22、passage 29
7. veh_w2: arrival 23、passage 31
8. veh_n2: arrival 25、passage 33

right-of-entry:
- veh_e2
- P = 27
- P−1 = 26

第二波4台すべてarrival <= P−1を満たした。

意思決定窓内Visit:
- veh_e2
- veh_s2

P−1候補母集団:
- veh_e2
- veh_s2
- veh_w2
- veh_n2

意思決定窓とP−1候補母集団は一致しなくてよい。
これは設計どおりである。

第二波4台から7候補を形成した。

economically feasible:
- 5件

選択:
- candidate identity:
  intersection|veh_n2:1
- selection reason:
  unique maximum surplus

## 13. T=16の選択候補

buyer:
- veh_n2

sellers:
- veh_e2
- veh_s2
- veh_w2

baseline順位:
- veh_e2
- veh_s2
- veh_w2
- veh_n2

採用候補順位:
- veh_n2
- veh_e2
- veh_s2
- veh_w2

予測時間変化:
- veh_n2:
  baseline 33 -> candidate 26
  7 timestep短縮
- veh_e2:
  baseline 27 -> candidate 28
  1 timestep遅延
- veh_s2:
  baseline 29 -> candidate 30
  1 timestep遅延
- veh_w2:
  baseline 31 -> candidate 32
  1 timestep遅延

経済計算:
- G = 8.744536946368566
- R = 1.526312266525999
- surplus = 7.218224679842567

この候補が7候補中の一意なmaximum surplusだった。

T=16では複数buyer候補も形成され、一部は経済的に成立した。
しかし、それらは選択候補よりsurplusが低かった。

## 14. T=16選択候補の局所仮想計算

局所仮想計算では、T=12で確定済みの第一波順位を先に維持し、その後にT=16の採用候補順位を適用した。

全拘束順位:
1. veh_e1
2. veh_s1
3. veh_w1
4. veh_n1
5. veh_n2
6. veh_e2
7. veh_s2
8. veh_w2

時系列:
- T=16〜17:
  第一波・第二波ともNode未到着。
- T=18:
  第一波4台が到着。
- T=19:
  veh_e1通過。
- T=20:
  clearance待ち。
- T=21:
  veh_s1通過。
- T=22:
  clearance待ち。
  veh_e2、veh_s2が到着。
- T=23:
  veh_w1通過。
  veh_w2が到着。
- T=24:
  clearance待ち。
- T=25:
  veh_n1通過。
  veh_n2がNodeへ到着。
  同じT=25の通過試行時点では未到着だったため、veh_n2は一時スキップされた。
- T=26:
  buyer veh_n2通過。
- T=27:
  clearance待ち。
- T=28:
  seller veh_e2通過。
- T=29:
  clearance待ち。
- T=30:
  seller veh_s2通過。
- T=31:
  clearance待ち。
- T=32:
  seller veh_w2通過。
  取引対象4台の必要な通過観測が揃いresolved=True。

到着登録と通過試行の処理順により、VehicleはNodeへ到着した同じtimestepには通過しない。

第一波の確定順位、第二波の採用候補順位、clearance、到着時刻、終了条件は整合していた。

## 15. T=20第三波と成立取引

T=20でもcandidate Visit 4台と7候補が形成された。

選択候補:
- buyer:
  veh_w3
- sellers:
  veh_n3
  veh_e3
  veh_s3
- buyer 1台
- seller 3台
- trade_scope 4台
- selection reason:
  unique maximum surplus

予測:
- veh_w3:
  baseline 40 -> candidate 33
  7 timestep短縮
- veh_n3:
  baseline 34 -> candidate 35
  1 timestep遅延
- veh_e3:
  baseline 36 -> candidate 37
  1 timestep遅延
- veh_s3:
  baseline 38 -> candidate 39
  1 timestep遅延

経済計算:
- G = 5.074432623897665
- R = 1.3741551491655684
- surplus = 3.7002774747320966

複数buyer候補も形成され、一部は経済的に成立した。
ただし、veh_w3単独buyer候補のsurplusが最大だった。

T=20はT=16と同型の構造である。
全candidateとtrial CSV・診断再simulationの整合は確認済みであり、同じ粒度のtimestep手作業監査は反復しない。

## 16. 成立取引の実績

T=16取引:
- buyer veh_n2
- sellers veh_e2、veh_s2、veh_w2
- buyer支払総額:
  1.526312266525999
- seller補償総額:
  1.526312266525999
- ex-post feasible
- buyer satisfied 1
- seller satisfied 3
- buyer realized gain:
  7.218224679842567
- seller realized gain合計:
  0

T=20取引:
- buyer veh_w3
- sellers veh_n3、veh_e3、veh_s3
- buyer支払総額:
  1.3741551491655684
- seller補償総額:
  1.3741551491655684
- ex-post feasible
- buyer satisfied 1
- seller satisfied 3
- buyer realized gain:
  3.7002774747320966
- seller realized gain合計:
  0

sellerはいずれも必要補償額と同額を受領した。

## 17. candidate予測とactual結果

成立取引の8 Visitについて:

- candidate passageとactual passageの不一致 0件
- predicted route情報とactual routeの不一致 0件
- formal route情報とactual routeの不一致 0件
- predicted route情報とformal route情報の不一致 0件
- assigned rankとactual Node passage rankの不一致 0件

当時の記録は、この12台trialの観察事実である。当該trialでは不一致が0件だった。

今回の最新結論は、C順位（Node連続・通過試行優先順位）とActual順位（Node連続）の一致を必須としない。順位不一致、temporary skip、downstream spillback下のoutlink入口空間、Candidate P Actual P全件一致の静的反証監査、および未完了の動的反証診断は、末尾の「Candidate P対Actual P全件一致の静的反証監査、Node連続順位の再解釈、および動的反証診断の未完了事項（2026-10-19）」を正本とする。C順位（Node連続）をCandidate予測通過順位と読まない。

ただし、上記の「未完了の動的反証診断」は2026-10-19時点の記録である。動的反証診断は2026-10-20に完了した。最新正本は、同節末尾の「動的反証診断完了、Candidate P対Actual Pの強い物理的一致、およびnonparticipating約20％混入trialへの移行（2026-10-20）」である。

predicted route fieldは、candidate予測記録に付属するroute情報であり、candidate局所仮想計算が進路自体を独自予測したという意味ではない。

candidate局所仮想計算では、baseline処理で得たrouteを使用する。

formal route fieldは順位確定時に保存されたroute情報である。

actual route fieldは実Worldで実際に通過したoutlinkである。

実Worldの進路はformal routeにより強制されず、UXsimがその時点で決定したlive routeを使用する。

今回3者が一致したことは、実Worldへformal routeを強制した結果ではない。

同一baseline仮想計算の同一Visitでは、Node到着時に決まったroute_next_linkに従って通過する。
到着記録のroute_next_link_nameと通過時のlive route_next_linkの一致検査は、この同一Visit内の整合性検査である。

この一致検査を異なるbaseline計算間の進路固定と誤認して、一時的に一致検査を削除するコード変更とテスト追加を行ったが、前提誤認が判明したため採用しなかった。

変更はgit restoreで完全に破棄済みであり、UXsim本体と既存テストには残っていない。

## 18. 今回確認できたこと

確認済み:
- 4 inlink・4 outlinkの中央NodeでTVT-MPが完走
- 12台全車完走
- straight、left、rightを各4台確認
- u_turn、unknown、中央Node再訪なし
- candidate Visit 4台
- 7候補形成
- buyer最大3台
- seller最大3台
- 21候補すべてFIFO preserved
- 21候補すべてlocal resolved
- T=16、20で複数候補間surplus比較
- buyer 1台・seller 3台の取引が2件成立
- 第一波のbaseline fallback
- 確定済み第一波順位を維持した第二波candidate局所仮想計算
- candidate予測、actual passage、順位の一致

上記「順位の一致」は、2026-10-14時点の12台trial観察である。C順位（Node連続）とActual順位の一致必須契約ではない。最新結論は末尾の2026-10-19節を読む。

今回未確認:
- 同一inlink上の連続する複数buyer
- 同一inlink上の連続する複数seller
- それらを含む経済的成立候補
- それらが最終選択されるケース
- nonparticipatingを含む単独十字路取引
- candidate limit N=10到達
- local RNG
- FIFO false
- local unresolved
- 高密度条件での正常なcandidate予測差

## 19. 次のtrial方針

次は、同じ単独十字路ネットワークでVehicle数を増やす。

維持:
- 5 Node
- 8 Link
- 各Link 200 m
- 単車線
- 中央NodeだけTVT-MP対象
- clearance 1
- OD指定
- UXsimの動的経路選択
- specified_route不使用
- 最初は全車participating
- 二層意思決定窓案は未実装

変更対象:
- Vehicle数
- 出発時刻
- 方向別投入配置

確認目的:
- 同一inlink上の複数Vehicleが同じP−1候補母集団へ入るか
- 同一inlink上の複数buyer候補
- 同一inlink上の複数seller候補
- それらの経済的成立
- それらの最終選択
- 高需要時のcandidate予測とactual結果の差

同一inlink上の連続buyer・sellerが形成されない場合は、
- 物理的にP−1までに到着できないためか
- 過去の意思決定で順位確定済みとなったためか
を区別する。

この結果を確認するまで、二層意思決定窓案は採用・実装しない。

2026-10-14時点の次trial方針は、上記の単独十字路でのVehicle増加である。この方針の本文は当時の記録として残す。

2026-10-19時点の未完了作業は、downstream spillback extended south pulse trialにおけるCandidate P対Actual P全件一致の動的反証診断である。再開手順の正本は、末尾の「Candidate P対Actual P全件一致の静的反証監査、Node連続順位の再解釈、および動的反証診断の未完了事項（2026-10-19）」である。

この未完了記述は当時の記録である。動的反証診断は2026-10-20に完了した。最新正本は同節末尾の2026-10-20追記である。次の未完了作業は、全参加条件の次のtrialとして、nonparticipating約20％の非参加車両混入trialを設計することである。

# Candidate P対Actual P全件一致の静的反証監査、Node連続順位の再解釈、および動的反証診断の未完了事項（2026-10-19）

本節は、downstream spillback extended south pulse trialの研究CSV、診断スクリプトの順位表示修正、T=316のNode連続順位の入れ替わり、全158取引の予測通過時刻と実通過時刻の集計、および全観測件一致に対する静的反証監査を、実装再開用に記録する。

検索時は、見出しを覚えていなくても、次の語で本文を探す。Candidate P Actual P 全件一致。予測通過時刻。実通過時刻。C順位。Actual順位。Node連続順位。通過試行優先順位。順位不一致。情報漏洩。循環参照。共有状態。downstream spillback。outlink入口空間。outlink終端境界。動的反証診断。未完了。再開手順。診断スクリプトの順位表示修正。

状態は未完了である。静的監査の分類はCである。動的反証診断は未実施である。productionコード、テスト、trialスクリプト、診断スクリプトは、本節を書いた時点で変更していない。

この4文は本節作成時点（2026-10-19）の記録である。「動的反証診断は未実施」「状態は未完了」は、当時の動的反証診断待ちを指す。2026-10-20追記が最新正本である。静的監査の分類C自体は維持する。動的反証診断完了後の次の未完了作業と再開手順は、同節末尾の2026-10-20追記を読む。

## 1. 対象trialと出力

trial名:

- `tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_initial`

研究CSV:

- `research_outputs/trial/tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_initial/tvt_mp_visits.csv`

診断スクリプト:

- `research_scripts/diagnose_tvt_mp_two_cross_intersections_post_fix_multiple_buyer_transactions.py`

この診断スクリプトのhookは、production本体の通過判定ではない。`tvt_mp_visits.csv` の生成経路は production の research output である。診断hookの表示不具合を、UXsim本体の通過不具合と混ぜて読まない。

## 2. 既存記述との関係

2026-10-10節「TVT-MP意思決定診断scriptの最新baseline契約整合・詳細監査結果」は、当時の小規模診断スクリプト `diagnose_tvt_mp_small_scale_initial_decision_trace.py` の記録である。そこでの `candidate_baseline_local_rank` は、そのスクリプト当時のlocal baseline順位の名前である。本節の4順位は、上記の two-cross 診断スクリプトと production の順位objectを読む現在の契約である。古い節の本文は削除していない。

2026-10-14節「単独十字路12台trialの実行・候補21件・時系列監査」の「assigned rankとactual Node passage rankの不一致 0件」と「順位の一致」は、その12台trialの観察事実である。一致必須の契約として読まない。最新結論は本節である。

## 3. 参加属性とtrade scope外の順位確定

`nonparticipating` は、時間価値取引への非参加車両という参加属性である。

trade scope外Visitの確定を「nonparticipatingとして順位確定」と書かない。必要な表現は次のどちらかである。

- TVTの非当事者として順位確定
- trade scope外のVisitとしてBaseline順位で確定

参加属性がnonparticipatingである先頭連続Visitを、driverがCandidate形成前に確定する処理は別である。それは参加属性の話であり、trade scope外Visitの言い換えではない。

## 4. 正式な4順位

「C順位」だけで比較しない。C順位（ローカル）とC順位（Node連続・通過試行優先順位）を分ける。C順位（Node連続）はCandidate予測通過順位ではない。Candidate PはCandidate局所仮想計算による予測通過時刻である。Actual Pは実Worldで物理通過した時点の `node.W.T` である。

### 4.1 B順位（ローカル）

- field: `baseline_local_rank`
- 保存済み `candidate_visits` の順番を再ソートせず、1始まりで数える
- 取引前のCandidate Visit集合内順位

### 4.2 C順位（ローカル）

- field: `post_trade_local_rank`
- 取得元: `OrderControlTvtMpGeneralTradeRankResult.assigned_rank(visit_key)`
- B順位と同じ母集団の取引後順位
- `rank_change = baseline_local_rank - post_trade_local_rank`

### 4.3 C順位（Node連続・通過試行優先順位）

- field: `OrderControlTvtNodeRankState.assigned_rank`
- 成立記録上の対応値: `ledger_assigned_rank`
- Node全体で1から続く確定順位
- 実Worldで通過を試す優先順位
- 通過予定時刻順ではない
- 通常物理制約によるtemporary skipにより、後順位Visitが先に実通過し得る

### 4.4 Actual順位（Node連続）

- field: `actual_node_passage_rank`
- 実WorldにおけるNode実通過順
- `new_rank = len(existing_records) + 1`

### 4.5 比較契約

- B順位とC順位（ローカル）は同一母集団・同一尺度で比較できる。
- C順位（Node連続）とActual順位は意味が異なり、一致は必須ではない。
- `binding_rank` は完全拘束順位列上の補助位置であり、4順位の代用ではない。
- 診断では `binding_sequence_auxiliary_rank` としてのみ残す。

## 5. k_confirmed_before

Node連続順位は次で作る。

`ledger_assigned_rank = k_confirmed_before + final_rank_visit.final_local_rank`

`k_confirmed_before = rank_state.k_confirmed()`

この値には次が含まれる。

- 過去までの確定Visit
- 今回先行確定した到着済みVisit
- 今回先行確定したleading nonparticipating Visit

最後の1項は、参加属性がnonparticipatingであるVisitの先行確定である。trade scope外Visitをnonparticipatingと呼ぶ意味ではない。

driverは同じ `rank_states` を、次の順で使う。

1. 到着済みVisit確定
2. leading nonparticipating確定
3. Candidate形成・評価
4. final rank作成
5. atomic apply

したがって、今回先行確定したVisitも、後続CandidateのNode連続順位へ反映される。

## 6. 診断スクリプトの順位表示修正

対象は `research_scripts/diagnose_tvt_mp_two_cross_intersections_post_fix_multiple_buyer_transactions.py` だけである。productionの順位計算は、この表示修正では変更していない。

parties CSVに横並びで出す正式順位は次の4つである。

- `baseline_local_rank`
- `post_trade_local_rank`
- `assigned_rank`
- `actual_node_passage_rank`

B-C差分列は追加していない。C-Actual差分列も追加していない。

summary:

- `baseline_order_visit_keys` は `baseline_local_rank` 昇順
- `candidate_order_visit_keys` は `post_trade_local_rank` 昇順

east T=35全候補監査:

- baselineは同じcandidate Visit集合の `baseline_local_rank`
- candidateは `post_trade_local_rank`
- `binding_rank` は使わない

この修正後の確認結果:

- `python -m py_compile` 成功
- `--static-validate-only` 成功
- 出力に `Static contract validation passed.`

構文検査と静的契約検証の段階では、長時間simulationを実行していない。その後、修正済み診断スクリプトで630 timestep simulationを複数回実行した。4順位の出力、Node連続順位不一致、実World到着時刻、T=324〜334のphysical trace、passed VisitKey修正後の出力を確認した。

## 7. T=316のNode連続順位不一致

対象:

- decision T=316
- Node = `west_intersection`
- mismatch Visit = `veh_wn_116:1`

これはC順位（Node連続・通過試行優先順位）とActual順位（Node連続）の順位不一致である。予測通過時刻と実通過時刻の不一致ではない。

### 7.1 主要データ

`veh_ws_83:1`

- buyer
- C連続198、Actual198
- Baseline A=326、Actual arrival=325
- Baseline P=328、Candidate P=326、Actual P=326

`veh_ws_84:1`

- buyer
- C連続199、Actual199
- Baseline A=328、Actual arrival=326
- Baseline P=332、Candidate P=327、Actual P=327

`veh_wn_116:1`

- seller
- B local=1、C local=4
- C連続200、Actual201
- Baseline A=322、Actual arrival=322
- Baseline P=330、Candidate P=331、Actual P=331

`veh_ws_85:1`

- T=316のtrade scope外
- TVTの非当事者
- C連続201、Actual200
- Baseline A=332、Actual arrival=328
- T=316の正式Candidate Pなし
- Actual P=329

`veh_wn_117:1`

- C連続202、Actual202
- Baseline A=330、Actual arrival=331、Actual P=332

`veh_ws_86:1`

- C連続203、Actual203
- Baseline A=336、Actual arrival=329、Actual P=334

Baseline Aは同一decisionのcollector snapshotである。Actual arrivalは実Worldの到着登録である。両者を同じ値として読まない。

### 7.2 trade scope外だった理由

`veh_ws_85:1` がT=316のtrade scope外だった理由は次である。

- right holder / seller `veh_wn_116:1` のBaseline P=330
- 境界はP-1=329
- `veh_ws_85:1` のBaseline A=332
- 332 > 329

`veh_ws_85:1` はT=316ではtrade scope外のTVT非当事者だった。最終的にC順位（Node連続）201を付与されたが、その順位を確定した正確なdecision Tとfinalization sourceは追加追跡していないため、T=316にBaseline順位として確定したとは断定しない。nonparticipatingとして順位確定した、とは記録しない。

### 7.3 後続車両が早着した原因

- `veh_ws_83:1` はBaseline P=328からCandidate P=326、Actual P=326へ2 timestep前進した
- `veh_ws_84:1` はBaseline P=332からCandidate P=327、Actual P=327へ5 timestep前進した
- 前方車両が早く通過したため、後続 `veh_ws_85:1` はBaseline A=332より4 timestep早いT=328に実到着した
- `veh_ws_86:1` もBaseline A=336より7 timestep早いT=329に実到着した

### 7.4 物理処理

- T=324: `veh_ws_81:1` 通過後、`veh_wn_116:1` でclearance停止
- T=325: `veh_ws_82:1` 通過後、同様
- T=326: `veh_ws_83:1` 通過後、同様
- T=327: `veh_ws_84:1` 通過後、同様
- T=328: 前timestepのwest_south通過によりclearance停止
- T=329:
  - `veh_wn_116:1` は到着済み、物理先頭、clearance充足
  - inlink流出、Node流量、outlink流入容量は充足
  - east側outlink入口空間不足でtemporary skip
  - 後順位 `veh_ws_85:1` はwest_outer側へ通過可能
  - `veh_ws_85:1` がT=329通過
- T=330: T=329のwest_south通過によるclearance停止
- T=331: `veh_wn_116:1` 通過

### 7.5 結論

- Node連続順位200と201だけがActualでは入れ替わった。
- production本体の実装エラーではない。
- 直接原因はT=329のeast側outlink入口空間不足である。
- C順位（Node連続）は通過試行優先順位であり、Actual順位との不一致は許容される。
- 取引当事者 `veh_wn_116:1` はCandidate P=Actual P=331であり、経済条件予測への実害はない。
- `veh_ws_85:1` は取引当事者ではなく、本人の経済条件用Candidate Pはない。

## 8. 診断スクリプト固有の修正

ここはproduction本体の問題と分ける。

### 8.1 Baseline AとActual arrivalの混同

初期表示はBaseline AをActual到着のように扱い、不可能な時系列を表示した。

修正後は別field、別取得元である。

- Baseline A: 同一decisionのcollector snapshot
- Actual arrival: 実World到着登録後の軽量観測
- Actual P: Actual passage history

T=316のBaseline AをActual arrivalとして扱わない。

### 8.2 trade scope外VisitのBaseline A欠落

trade scope外でも、同一decisionのcollectorに正式なBaseline Aがあり得る。

取得元は、`mismatch_decision_timestep` とNodeに対応するcollectorである。T=316固定ではない。

Candidate Pは、正式recordがなければ補完しない。`veh_ws_85:1` にT=316の正式Candidate Pがある、とは書かない。

### 8.3 passed VisitKeyの誤記録

production通過後の `current_visit` を読むと次Visitになる。このため `veh_wn_116:1` を `veh_wn_116:2` と誤記録した。

修正後は、通過呼出し前のVisitKeyを保存し、正常終了後だけpassedを記録する。例外時はpassedを記録しない。元関数は1回だけ呼び、return valueは変えない。

### 8.4 標準出力の未修正事項

`first blocking reason at or before swapped passage` は、最初の阻害理由であり、直接原因ではない。

T=316では表示上clearanceが選ばれる。順位入れ替わりの直接原因は、T=329のoutlink入口空間不足である。

これは診断表示上の低優先度事項であり、UXsim本体の問題ではない。本節の時点では未修正である。

## 9. 全158取引のCandidate P対Actual P

母数は `tvt_mp_visits.csv` の集計である。

- transaction_count = 158
- visit_row_count = 458
- Candidate PとActual Pの双方を観測できた当事者 = 449
- Actual P未観測 = 9
- 観測済み449件の全件で Candidate P = Actual P
- buyer観測206件すべて一致
- seller観測243件すべて一致
- 全458件中455件で Baseline P ≠ Candidate P
- 全458件中3件で Baseline P = Candidate P

455/458は、449件の内訳ではない。449件中455件とは書かない。

206と243は、双方観測449件のrole内訳である。206 + 243 = 449。未観測9件は、この206と243には入らない。458 = 449 + 9。

Actual未観測9件:

- 評価終了付近
- Candidate P = 600〜615
- Actual status = `actual_passage_unobserved_at_evaluation_end`
- Actual P = None
- 実Worldを評価終了後へ進めない設計と整合する

Baseline P − Candidate P の分布は、全458件に対する件数である。正値は前進、負値は後退である。正値は Baseline P より Candidate P が早い。負値は Baseline P より Candidate P が遅い。

- -6: 9
- -4: 36
- -3: 2
- -2: 38
- -1: 159
- 0: 3
- 1: 8
- 2: 54
- 3: 68
- 4: 45
- 5: 7
- 7: 29

この分布の合計は458である。0が3件なので、不一致は455件である。

追加の幅:

- buyer最大前進 = 7 timestep
- seller最大後退 = 6 timestep
- Candidate P − decision T は 7〜20 timestep

## 10. 静的反証監査

Copilotの原典確認と、Cursor Grok 4.6による独立した読み取り専用監査を実施した。監査は、一致が正常であると仮定せず、情報漏洩、循環参照、共有状態、Candidate Pの実Worldへの間接適用、出力の誤対応を探した。

最終分類はCである。

Cの意味:

- 全件一致を不正に生む具体的な実装不備は、静的監査で確認されなかった。
- Candidate PとActual Pは独立生成と判断される。
- ただし449件全一致が交通条件から自然であることは、静的解析だけでは未確定である。
- 動的反証診断が必要である。

「動的反証診断が必要である」は、2026-10-19の静的監査時点の判断である。当時は動的反証診断待ちだった。2026-10-20に代表2件の動的反証診断を完了した。最新正本は本節末尾の2026-10-20追記である。静的監査の分類Cは維持する。449件すべてを動的traceしたわけではない。

分類AでもBでもDでもない。Aは、一致を不正に生む具体経路が確認された場合である。Bは、直接経路は未確定だが共有状態・循環・誤対応の具体的危険がある場合である。Dは、独立生成に加え、全件一致が設計と交通条件から説明でき、動的診断が追加保証にとどまる場合である。今回はDにしない。outlink終端境界が実World下流の完全再現ではないため、全件一致は自明ではない。

### 10.1 反証済み

次の経路は、production原典上は確認されなかった。

- Candidate PからActual Pへの直接コピー
- Actual PのCandidate Pによるfallback
- CSV列の取り違え
- Actual未観測へのCandidate P補完
- Candidate Pによる実World通過時刻の強制
- Candidate局所Worldの位置・容量・outlink状態の実Worldへの書戻し
- Candidate計算による実World未来状態の再参照
- 主要Node、Link、Vehicle、`route_next_link` の共有
- Vehicle名だけによるCandidateとActualの誤結合

### 10.2 生成経路

Candidate P:

- decision時点の `World.copy` は `pickle.loads(pickle.dumps(W))` である（`uxsim/uxsim.py` の `World.copy`）。
- 候補状態の構築は `build_tvt_mp_candidate_local_state` である。
- 仮想時刻は baseline T + offset であり、コピーの `local_world.T` と一致しないと停止する。
- binding transferがコピー上で通過させた仮想時刻を、`candidate_passage_timestep` としてtraffic observationとpassage recordへ書く。
- 同じVisitへCandidate Pを再代入すると停止する。

Actual P:

- 実Worldの time_value 通過は `transfer_tvt_mp_passage_attempts` から `_try_confirmed_candidates` へ進む。
- 通過すると決めた後にだけ、`actual_passage_timestep=node.W.T` でhistoryとobservationをprepareする。
- history側は、渡された時刻が `node.W.T` と違うと拒否する。
- `_transfer_one_vehicle_between_links` が正常に戻った後だけcommitする。
- 未通過ならprepareされない。Actual Pは保存されない。
- 評価終了時の未観測recordは `actual_passage_timestep=None` のままである。WaitEntry上のCandidate Pは予測値として残る。fallbackではない。

CSV:

- Visit行の `candidate_passage_timestep` と `actual_passage_timestep` は別fieldである。
- `candidate_minus_actual` は、WaitEntryに保存済みのCandidate Pと、今回の `node.W.T` の差である。同じ一時変数を両方の値として使っていない。
- 結合キーは `(node_name, visit_key)` と、transactionの `(tvt_decision_timestep, node_name, buyers_sorted)` である。同一VisitKeyが複数TradeWaitに属すると停止する。

実Worldへatomic applyが渡すものは、台帳上のassigned rank、formal route名、payment、compensation、establishment log、WaitEntryである。establishment logとWaitEntryにCandidate Pが入るのは記録である。Vehicle位置、速度、capacity、clearance、`incoming_vehicles`、outlink列、通過時刻は戻さない。formal route名は、`vehicle.route_next_link` への代入ではない。実Worldの通過は `vehicle.route_next_link` を使う。

assigned rankは通過試行優先順位である。通過予定時刻ではない。Candidate Pを実Worldの通過条件と比較していない。`order_control_tvt_mp_physical_transfer.py` は `candidate_passage` を参照しない。

Candidate側の通過走査はbinding順である。実Worldの通過走査は、その後の台帳に入ったassigned rank順である。予測に使った順と実現時の試行順は同じ関数ではない。したがって、同じ時刻変数を両方へ書いて一致させている構造ではない。

### 10.3 限定的な残存事項

- rank ledgerとActual passage registryは、pickleで通常は別objectになる。ただし、Node、Link、Vehicle、`route_next_link` ほど明示的なidentity検査はない。構築直後の検査が拒否するのは、対象Node、inlink、outlink、車両、leader、follower、`route_next_link` が実Worldの同一objectである場合である。
- Candidate側outlink終端近似と実World下流交通の差が、今回のoutlink入口空間へ影響しなかった理由は、静的には未確認である。

候補計算後のコードが、実World objectを交通状態の読込み先として保持している経路は、この監査では見つかっていない。保持されるのは時刻の整数と、構築時の名前・ID対応である。候補ファイルから `exec_simulation` や driver の再入は見つかっていない。

## 11. 全件一致が自明でない理由

Candidate側のoutlink終端境界は、実World下流交通の完全再現ではない。downstream spillbackがあるtrialでは、この差が予測通過時刻を動かし得る。

boundary mode:

- `OBSERVED_WAIT_WITH_OUTFLOW`
  - baseline平均流出率をflow allowanceへ加算する
- `OBSERVED_WAIT_WITHOUT_OUTFLOW`
  - baselineで待ちがあり、流出がゼロである
  - Candidate側でも除去しない
- `NO_OBSERVED_WAIT_CONSTRAINED_SINK`
  - baselineで待ちがない
  - 容量が許せばsinkとして除去する

Candidate仮想timestepの順:

1. capacity refill
2. binding transfer
3. unbound FCFS
4. Candidate P記録
5. local Vehicle advance
6. outlink boundary処理
7. 次のtimestep

終端近似の差は、主に次timestep以降のoutlink入口空間へ影響する。

今回の条件:

- リンク長 200 m
- 自由流速度 約16.67 m/s（`60000 / 3600`）
- `DELTAT = reaction_time * deltan = 1` 秒
- 自由流リンク通過 約12 timestep
- 予測距離 7〜20 timestep

下流境界の差が入口空間へ波及し得る時間幅を含む。449件のCandidate P Actual P全件一致は不可能ではない。自明でもない。

「同じロジックだから一致した」では説明しない。binding transferは、実Worldの `transfer_tvt_mp_passage_attempts` を呼ばない。同順の条件を、コピー上で別実装している。初期状態がdecision時点のpickleと揃い、当該Visitの通過を止めていた条件が両方で同じ時刻に外れたとき、時刻は一致し得る。入口空間が束縛条件だった場合は、終端近似が時刻を分け得る。後続decisionがassigned rankを変えても、そのVisitがまだ物理先頭でない、またはclearance待ちなら、通過時刻は変わらず順位だけ変わり得る。T=316の200と201の入れ替わりは、その例である。当事者 `veh_wn_116:1` の予測通過時刻と実通過時刻はどちらも331である。

## 12. 未完了の動的反証診断

本12節の見出しと本文は、2026-10-19時点の計画である。当時は動的反証診断待ちであり、診断コードもsimulationも開始していなかった。この「未完了」は歴史的記録として残す。2026-10-20に代表2件の動的反証診断は完了した。最新正本は本節末尾の2026-10-20追記である。

最初は次の2件だけを対象とする。全449件へ先に広げない。

最大前進buyer:

- T=60
- `east_intersection`
- `veh_ee_10:1`
- Baseline P=80
- Candidate P=73
- Actual P=73
- 7 timestep前進

最大後退seller:

- T=135
- `east_intersection`
- `veh_ee_19:1`
- Baseline P=149
- Candidate P=155
- Actual P=155
- 6 timestep後退

Candidate局所Worldと実Worldで、各timestepの次を比較する。

- 到着
- inlink物理先頭
- clearance
- inlink流出容量
- Node流量容量
- outlink流入容量
- outlink入口空間
- temporary skip
- clearance停止
- passage
- outlink内車両数
- Candidate boundary mode
- Candidate終端除去Vehicle
- 実World下流流出

分類:

1. 強い独立一致
   - 通過時刻だけでなく、停止理由と入口空間推移も一致する
2. 時刻だけ一致
   - 時刻は一致するが、途中状態が異なる
3. 実装不整合疑い
   - 同じ状態で異なる判定、説明不能な共有状態、予測値の不正流入がある

2件とも強い独立一致なら、全449件へ拡張しない。それ以外なら、spillbackが強いケースを追加する。

実装方針:

- 既存CSVだけでは不足する
- 読み取り専用hookによる再simulationが必要である
- productionコードは変更しない
- 元関数を各1回だけ呼ぶ
- return valueや交通状態を変更しない
- 乱数消費と `World.copy` を追加しない

この動的反証診断は未完了である。本節の作成時点では、診断コードもsimulationも開始していない。

上の2文は2026-10-19作成時点の記録である。動的反証診断待ちという状態は当時の未完了事項である。2026-10-20追記が最新正本である。

## 13. 追加追跡を中止した事項

`veh_ws_85:1` について、次の追跡は中止した。

- 順位201を確定した正確なdecision T
- finalization source
- T=316 Candidate局所World内のunbound FCFS参考通過時刻

中止理由:

- transaction_count = 0
- buyer_count = 0
- seller_count = 0
- nonparticipating_count = 0
- trade scope observation = 0
- TVTの非当事者である
- 本人の経済条件算定対象ではない
- `veh_wn_116:1` は Candidate P = Actual P = 331
- 追加診断の研究価値が小さい

`nonparticipating_count = 0` は、このVisitを参加属性nonparticipatingとして扱った件数が0という意味で記録する。trade scope外であることをnonparticipating確定とは呼ばない。

## 14. 再開手順

本14節の手順は、2026-10-19時点の動的反証診断待ちに対する再開手順である。歴史的記録として残す。動的反証診断は2026-10-20に完了した。最新の未完了作業と再開手順は、本節末尾の2026-10-20追記を読む。

1. 本節を読む。
2. `ORDER_EXCHANGE_PROGRESS_3.md` の最新節を確認する。進捗第3巻は、本節を書いた時点では未更新である。
3. T=60 buyer `veh_ee_10:1` と T=135 seller `veh_ee_19:1` だけを対象に、動的反証診断を設計する。
4. Candidate側・Actual側hookの対象関数と時刻範囲を原典確認する。
5. static contractを先に設計する。
6. productionコードを変更しない。
7. CursorにGit操作をさせない。
8. Terminalで差分、`py_compile`、static validationを独立確認する。
9. 既存出力directoryを削除せず退避する。
10. 630 timestep simulationを実行する。
11. Candidate側とActual側を横並びにして、強い独立一致、時刻だけ一致、実装不整合疑いの3分類をする。
12. 結果を本詳細設計メモと `ORDER_EXCHANGE_PROGRESS_3.md` へ反映する。

標準出力の `first blocking reason at or before swapped passage` は、再開時の必須修正ではない。診断表示の低優先度事項として残っている。

## 15. 動的反証診断完了、Candidate P対Actual Pの強い物理的一致、およびnonparticipating約20％混入trialへの移行（2026-10-20）

本15節は、2026-10-19節の動的反証診断待ちを完了した記録である。2026-10-19節本文の「未完了」「動的反証診断は未実施」は当時の記録として残す。Candidate P Actual P 全件一致に関する最新正本は本15節である。次のtrialは、全参加条件のまま複雑なnetworkへ進むことではなく、同一networkへのnonparticipating 20％前後の非参加車両混入である。再開手順は本15節末尾である。

検索時は、次の語で本文を探す。Candidate P Actual P 全件一致。strong_physical_match。強い物理的一致。動的反証診断。情報漏洩。通過時刻の強制。未到着。clearance。outlink入口空間。走査手続。物理状態。nonparticipating 20％。非参加車両混入。全参加条件。次のtrial。未完了。再開手順。

### 15.1 診断対象

新規診断スクリプト:

- `research_scripts/diagnose_tvt_mp_candidate_actual_physical_reason_comparison.py`

対象trial:

- `tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_initial`

対象は次の2件だけである。全458当事者中の最大前進buyerと最大後退sellerとして選んだ。全449観測件へ動的traceを広げていない。

最大前進buyer:

- `case_id=buyer_t60_veh_ee_10_1`
- decision T=60
- Node=`east_intersection`
- VisitKey=`veh_ee_10:1`
- role=buyer
- Baseline P=80
- Candidate P=73
- Actual P=73
- 7 timestep前進
- 比較時刻=T=60〜73

最大後退seller:

- `case_id=seller_t135_veh_ee_19_1`
- decision T=135
- Node=`east_intersection`
- VisitKey=`veh_ee_19:1`
- role=seller
- Baseline P=149
- Candidate P=155
- Actual P=155
- 6 timestep後退
- 比較時刻=T=135〜155

### 15.2 診断目的

静的監査までに確認できていたのは次である。

- Candidate PとActual Pは別経路で生成される
- Candidate PからActual Pへの直接コピーはない
- Candidate Pを実Worldの通過時刻として強制する処理はない
- 情報漏洩として、Candidate PをActual Pへ直接流す経路は見つかっていない
- Actual Pは実World物理通過時の `node.W.T`
- 観測可能な449件でCandidate P=Actual P

静的監査だけでは、次の3つを区別できなかった。

1. Candidate局所Worldと実Worldが同じ物理状態から同じ通過時刻へ到達した
2. 途中の物理状態は異なるが、偶然同じ通過時刻になった
3. 未発見の共有状態や間接的強制がある

今回の動的反証診断では、Candidate局所Worldと実Worldについて、各時刻の物理状態と停止・通過理由を別々に観測し、同じ通過時刻が同じ物理過程から生じたかを確認した。

### 15.3 診断スクリプトの安全契約

- UXsim production本体は変更していない
- trialは変更していない
- 既存診断スクリプトは変更していない
- 新規の読み取り専用診断スクリプト1本だけを作成した
- wrapperは元production関数を各呼出しにつき1回だけ実行する
- return valueは変更しない
- capacity、clearance履歴、Vehicle位置、incoming、outlink車列を変更しない
- Actual passage historyと順位台帳を変更しない
- 追加の `World.copy` なし
- 追加の乱数消費なし
- passageは元関数正常終了後だけ、通過前に保存したVisitKeyへ記録する
- hookは例外時を含めて `finally` で復元する
- baseline forkをActual観測へ混入させない
- Candidate側official reasonは凍結済みbinding resultから取得する
- Actual側official reasonはproduction関数の正式返値から取得する

`py_compile` と `--static-validate-only` はいずれも成功した。630 timestep simulationも正常終了した。

### 15.4 診断設計の修正履歴

診断の結論だけでなく、比較契約を誤ると誤判定するため、修正経緯を原因付きで残す。比較契約の誤りは診断設計の誤りである。UXsim本体の不具合ではない。

#### 15.4.1 初期診断

初期診断では、通過時刻と一部の正式理由を比較した。

結果:

- buyerはT=72でCandidate側 `not_arrived_at_target_node`、Actual側 `not_scanned`
- sellerはT=142〜152でCandidate側 `not_scanned`、Actual側 `not_observable`
- 両ケースとも暫定的に「時刻だけ一致」

これは実際の物理状態差を確定した結果ではない。Actual側の走査到達状態の記録不足を含んでいた。

#### 15.4.2 走査到達状態追加後の問題

次に、confirmed candidatesへの所属、走査位置、先行Visitのclearance stopを記録した。未到着期間に多数の理由差が現れた。

原因:

Candidate側:

- 将来到着するVisitもbinding sequenceに含まれる
- 先行Visitのclearance stopで対象Visitまで走査が到達しない場合がある

実World側:

- 未到着Visitはconfirmed candidatesに含まれない場合がある

これはUXsim本体の目的に応じた正常な走査手続の違いである。

- Candidate局所計算は将来交通を予測する
- 実Worldは現時点の到着済みVehicleを通過候補として扱う

走査手続の違いを物理状態の不一致として数えた比較契約が誤りだった。productionの通過判定そのものが壊れていたわけではない。

#### 15.4.3 最終的な段階別物理比較

最終版では、物理状態と走査手続を分離した。

物理状態はproductionの判定順に比較する。

1. 到着
2. inlink物理先頭
3. clearance
4. inlink流出容量
5. Node流量容量
6. outlink流入容量
7. outlink入口空間
8. passage

後段の項目は、前段が両側で充足した場合だけ比較する。

例:

- 両側が未到着なら、到着状態だけを比較する
- 未到着時にclearance、容量、入口空間、車列を比較しない
- 両側が物理先頭でなければ、clearance以降を比較しない
- clearance未充足なら容量以降を比較しない

この修正により、走査方法の違いを物理状態差として誤計上しない。

次を別fieldとして保持した。

- physical state
- official reason
- scan reach status

Candidate側とActual側でscan reach statusが異なっても、段階別physical stateが一致すれば物理的不一致にはしない。

### 15.5 buyerの最終結果

`buyer_t60_veh_ee_10_1`

- Candidate P=73
- Actual P=73
- 全時刻数=14
- 到着前時刻数=13
- 物理状態比較可能時刻数=14
- physical state mismatch数=0
- scan procedure mismatch数=13
- exact official reason mismatch数=12
- physical official reason mismatch数=0
- passage flag mismatch数=0
- 最終分類=`strong_physical_match`

時系列の要点:

- T=60〜72:
  - Candidate局所Worldと実Worldの両方で対象Visitは未到着
  - 走査手続は異なる時刻がある
  - ただし段階別物理状態は一致
- T=72:
  - Candidate側 `not_arrived_at_target_node`
  - Actual側 `not_arrived_at_target_node`
  - `physical_state_match=True`
  - `official_reason_semantic_status=exact_match`
- T=73:
  - 両側とも到着済み
  - 両側とも通過条件充足
  - 両側とも `passed`
  - `physical_state_match=True`
  - `official_reason_semantic_status=exact_match`

Candidate P=Actual P=73は、単なるCSV値の一致ではない。両Worldで未到着状態から同じ時刻に通過可能状態へ移行した結果である。

### 15.6 sellerの最終結果

`seller_t135_veh_ee_19_1`

- Candidate P=155
- Actual P=155
- 全時刻数=21
- 到着前時刻数=18
- 物理状態比較可能時刻数=21
- physical state mismatch数=0
- scan procedure mismatch数=7
- exact official reason mismatch数=7
- physical official reason mismatch数=0
- passage flag mismatch数=0
- 最終分類=`strong_physical_match`

時系列の要点:

- T=135〜152:
  - Candidate局所Worldと実Worldの両方で対象Visitは未到着
  - 一部時刻で走査手続は異なる
  - 段階別物理状態は一致
- T=153:
  - 両側とも到着済み
  - 両側ともinlink物理先頭
  - 両側とも `clearance_not_satisfied`
  - `physical_state_match=True`
  - `official_reason_semantic_status=exact_match`
- T=154:
  - T=153と同様に、両側ともclearance未充足
- T=155:
  - 両側ともclearanceと通常物理制約を充足
  - 両側とも `passed`
  - `physical_state_match=True`
  - `official_reason_semantic_status=exact_match`

Candidate P=Actual P=155は、通過時刻だけの偶然一致ではない。T=153〜154に同じ理由で停止し、T=155に同じ物理条件で通過した。sellerの通過直前はclearance停止であり、outlink入口空間不足ではない。

### 15.7 最終分類の意味

`strong_physical_match` は強い物理的一致である。次を意味する。

- Candidate P=Actual P
- 全比較時刻で段階別physical stateが一致する
- passage flagが一致する
- 通過直前から通過までのphysical official reasonが一致する
- official reasonと保存済み状態に矛盾がない
- Candidate PのActual側への不正流入が確認されない

未到着期間のscan procedure差は、物理状態差ではないため、この分類を妨げない。通過時刻の一致だけで強い物理的一致とはしない。

outlink終端比較は、Candidate側がlocal Vehicle advance後、Actual側がVehicle advance前であり、同一処理時点ではない。

したがって:

- `comparison_phase=not_equivalent`
- 終端除去Vehicleの一致はstrong physical matchの必須条件にしない
- 参考情報としてのみ保存する

outlink終端近似が一般に完全であるとは書かない。

### 15.8 今回追加的に言えるようになったこと

静的監査後に言えたのは、Candidate PとActual Pが独立生成であり、不正な直接コピーと通過時刻の強制が見つからないことまでだった。

今回の動的反証診断により、次が追加的に確認された。

- 最大前進buyerと最大後退sellerの両方で、通過時刻だけでなく物理過程も一致した
- buyerは未到着から通過可能状態への移行が一致した
- sellerは通過直前のclearance停止2 timestepと、その後の通過が一致した
- 両ケースでphysical state mismatchは0件
- physical official reason mismatchも0件
- passage flag mismatchも0件
- Candidate PとActual Pの一致が、同じ物理状態から導かれたことを確認した

したがって、このtrialにおける449観測件のCandidate P=Actual P全件一致は、現時点では実装不備ではなく、Candidate局所計算が実Worldを適切に予測した結果と暫定評価する。

ただし、動的traceを確認したのは代表2件である。449件すべてについて同じ物理過程を個別確認したわけではない。全件を `strong_physical_match` と個別判定したわけでもない。

### 15.9 結論の適用範囲

正式な限定付き結論:

現在の2交差点downstream spillback extended south pulse trialの全参加条件では、観測可能な449当事者でCandidate PとActual Pが一致した。静的監査では両時刻を不正に一致させる具体的経路を確認できず、最大前進buyerと最大後退sellerの動的反証診断では、通過時刻だけでなく段階別物理状態と通過直前理由も一致した。したがって、本trialのCandidate P対Actual P全件一致は、Candidate局所計算が実Worldを適切に予測した結果と暫定評価する。

次は書かない。

- すべてのnetworkでCandidate PとActual Pが常に一致する
- 全449件で `strong_physical_match` を個別確認した
- outlink終端近似が一般に完全である
- より複雑なnetworkでも予測誤差が生じない
- nonparticipating混入後も同じ結果になる

### 15.10 全449件への拡張判断

今回の2ケースは次を代表する。

- 最大前進buyer
- 最大後退seller

両ケースで強い物理的一致（`strong_physical_match`）を確認したため、現trialの全449件へ詳細な動的traceを拡張しない。

理由:

- 既に全449観測件でCandidate P=Actual P
- 静的監査で直接コピー・情報漏洩・通過時刻の強制を確認できない
- 最大変化2ケースで物理過程まで一致
- 全件traceの追加研究価値が小さい
- 次の実験条件へ時間を配分する方が有益

### 15.11 次の実験段階

複雑なnetworkへ移行する前に、同じnetwork設定へnonparticipating車両を約20％混入させる。

目的:

- 全参加条件から参加構成を変更する
- nonparticipating Visitの手続的処理を確認する
- 非参加車両の存在がTVT成立、順位確定、Candidate P、Actual P、参加者の経済評価へ与える影響を確認する
- nonparticipatingへのpredicted/actual外部効果記録を確認する
- Candidate P−Actual Pの分布が全参加条件から変化するか確認する

現時点では、nonparticipating約20％混入trialは未設計・未実行である。これが次の未完了作業である。

約20％の具体的な割当方法、seed、対象Vehicle選択規則、参加属性固定方法、期待件数、static contractは次の作業で設計する。

複雑なnetwork trialは、その後の段階とする。

### 15.12 未完了事項

最優先:

- 同一networkへのnonparticipating約20％混入trialの設計

設計項目:

- nonparticipating割当seed
- 約20％の正確な定義
- Vehicle単位かVisit単位か
- 全対象Vehicleからの抽出か、VOT適格Vehicleからの抽出か
- 既存VOT生成との独立性
- 再現可能な選択規則
- buyer・seller・nonparticipatingの期待件数
- 取引数とCandidate P−Actual P分布の比較
- nonparticipating predicted/actual external effect
- baseline順位保護
- 実通過時の外部効果
- 評価終了時未観測の扱い
- static contract
- 出力directoryとreference trialの分離

低優先度:

- 既存診断標準出力 `first blocking reason at or before swapped passage` の表示改善
- UXsim production本体の問題ではない
- 次のnonparticipating trial開始前の必須作業ではない

### 15.13 再開手順

後日、次の順で再開する。

1. 本動的反証診断完了節（本15節）を読む
2. `ORDER_EXCHANGE_PROGRESS_3.md` の最新再開地点を読む
3. nonparticipating約20％混入trialの設計を開始する
4. 既存trialを直接変更するか、新規trialを作るかを原典確認する
5. 参加属性の現在の生成・保存経路を確認する
6. Vehicle単位の再現可能な抽出契約を設計する
7. 既存VOT RNGと独立したseedを使用するか決定する
8. static contractを先に設計する
9. productionコードは変更しない
10. 既存出力directoryを上書きしない
11. trial実行後、全参加referenceと主要指標を比較する
12. Candidate P−Actual Pに差が出た場合だけ、最大差ケースへ今回の動的診断を適用する

## 16. nonparticipating約20％混入trial、順位保護、difference=1境界候補反証、および同一inlink複数buyer比較（2026-10-20）

### 16.1 記録の位置づけ

本節は、同一networkへ **nonparticipating（非参加車両）** を約 **20％** 混入させたTVT-MP trialと、その成立取引・診断結果を記録する。作業の対象は次に限定する。

- 同一networkへのnonparticipating約20％混入trial（nonparticipating **110台** / 総数551台）
- Vehicle単位で固定したnonparticipating属性（simulation中に変更しない）
- 交通・OD・departure・true VOTを全参加referenceと揃えた比較trial
- 成立取引の集計と、全参加referenceとの主要指標比較
- nonparticipatingを含む取引、および **複数buyer**・ **複数seller** 取引の抽出（詳細診断対象 **63取引**、**233 party行**）
- trade scope内nonparticipatingの **Baseline順位** と取引後ローカル順位の **順位保護** 確認

検索用キーワード: nonparticipating、非参加車両、20％、110台、fixed seed、seed 3、Baseline順位、Candidate順位、順位保護、複数buyer、複数seller、trade scope、63取引、233 party行、payment recordなし、effective amount 0、未完了、分割記録。

本節全体（difference=1境界候補反証、同一inlink複数buyer比較、payment balance、人間レビュー等）は **分割記録** として段階的に追記する。今回の追記は前半（trial設計〜nonparticipating順位保護）に限定する。

### 16.2 trial設計

**基準trial（全参加reference）**

- スクリプト: `research_scripts/run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_trial.py`

**新規trial（nonparticipating約20％混入）**

- スクリプト: `research_scripts/run_tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_nonparticipating_20_trial.py`
- scenario名: `tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_nonparticipating_20_trial`
- 出力directory: `research_outputs/trial/tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_nonparticipation_seed_3_initial/`

**構成方針**

- 基準trialを複製せず、import wrapper方式で構成した
- production変更なし、基準trialスクリプト変更なし

**Vehicle数と参加属性**

- Vehicle総数は551台
- participatingは441台
- nonparticipatingは110台
- nonparticipating率は110/551（約19.96％）
- 参加属性はVehicle単位で固定し、simulation中に参加属性を変更しない

**nonparticipating抽出（fixed seed）**

- `NONPARTICIPATION_SEED=3`
- `random.Random(3).sample` を用いて、551台から110台を重複なしで抽出する
- 抽出後はreference Vehicle順へ戻す

**交通・VOT・network（referenceと同一）**

- 交通、OD、departure、traffic group、planned movement、Vehicle順、true VOTは全参加referenceと同一
- nonparticipatingのみ `participating=False`（`participates_in_order_exchange=False`）
- nonparticipatingのdeclared VOTは `None`
- nonparticipatingにもtrue VOTは保持する
- participatingではdeclared VOT=true VOT
- traffic seed=0
- east destination seed=1
- west-north destination seed=2
- VOT seed=1
- networkは同一

**simulation・TVT設定**

- 実World評価期間はT=0〜599
- simulation内部TSIZEは630
- horizonは30
- TVT candidate上限は10
- clearanceは1

**nonparticipating Vehicle名一覧のstatic contract**

- 110台の完全一覧はメモ本文へ重複羅列しない
- 一覧の正本は新規trialスクリプト内の `NONPARTICIPATING_VEHICLE_NAMES`
- 一覧のSHA-256（母集団順のVehicle名を改行結合して計算）: `f91065b60888f0c2d9a8bf1a60efad5d40828546445bd0909dde25897c1ca111`
- hashは交通計算や抽出には使わない。一覧の不意な変更を検出するためのstatic contractである

### 16.3 trial全体結果

**nonparticipating約20％混入trial**

- 成立取引数=130取引
- 複数取引におけるbuyer数の延べ合計=150台
- seller数の延べ合計=193台
- trade scope内nonparticipating数の延べ合計=24台
- trade scope party合計=367
- Candidate PとActual Pの双方を観測できたparty=360
- Candidate P=Actual P=360
- Candidate P≠Actual P=0
- Actual P未観測=7
- spillback link最大Vehicle数=36
- entrance blocked timestep数=137

**全参加referenceとの主要指標比較**

| 指標 | 全参加reference | nonparticipating約20％ | 差 |
|------|-----------------|-------------------------|-----|
| 成立取引数 | 158 | 130 | −28 |
| trade scope party合計 | 458 | 367 | −91 |
| buyer数の延べ合計 | 209 | 150 | −59 |
| seller数の延べ合計 | 249 | 193 | −56 |
| trade scope内nonparticipating数の延べ合計 | 0 | 24 | +24 |
| Candidate PとActual Pの双方観測 | 449 | 360 | −89 |
| Actual P未観測 | 9 | 7 | −2 |
| spillback link最大Vehicle数 | 37 | 36 | −1 |
| entrance blocked timestep数 | 182 | 137 | −45 |

用語統一: 取引ごとのbuyer数、複数取引におけるbuyer数の延べ合計、seller数の延べ合計、trade scope内nonparticipating数の延べ合計。異なる取引間では同一Vehicleが再登場する可能性があるため、複数取引の合計には「延べ」を付ける。

### 16.4 詳細診断対象63取引の抽出

成立130取引から、次のいずれかを満たす取引を抽出した。

- trade scope内nonparticipating数が1以上
- 取引ごとのbuyer数が2以上
- 取引ごとのseller数が2以上

重複を除いた抽出結果:

- 63取引
- 233 party行
- buyer数の延べ合計83台
- seller数の延べ合計126台
- trade scope内nonparticipating数の延べ合計24台

**63取引の排他的な条件内訳**

- nonparticipatingだけ: 7取引
- 複数buyerだけ: 8取引
- 複数sellerだけ: 27取引
- nonparticipatingかつ複数buyer: 4取引
- nonparticipatingかつ複数seller: 10取引
- 複数buyerかつ複数seller: 7取引
- 3条件すべて: 0取引

合計確認: 7 + 8 + 27 + 4 + 10 + 7 = 63取引

**条件別の重複込み取引数**

- nonparticipatingを含む: 21取引
- buyerが2台以上: 19取引
- sellerが2台以上: 44取引

**buyer数と取引数の関係**

- buyerが1台の取引は44取引。この44取引のbuyer数は44台
- buyerが2台以上の取引は19取引。この19取引に含まれるbuyer数の延べ合計は83−44=39台
- 複数buyer取引における平均buyer数は39/19（約2.05台/取引）

### 16.5 nonparticipating 24件の順位保護

対象は、詳細診断63取引のtrade scopeに含まれるnonparticipating Visit 24件である。

**順位保護（同一trade scope母集団上のローカル順位同士）**

- 比較: `baseline_local_rank` と `post_trade_local_rank`
- 一致=24、不一致=0

次の値は順位保護判定へ代用していない: binding rank、assigned rank、actual node passage rank、passage timestep。

**参加属性とVOT**

- `participates_in_order_exchange=False`: 24
- `declared_vot_per_second=None`: 24
- `true_vot_per_second` は保持されている

**支払・補償（正式対象外と実効額の区別）**

nonparticipatingの `official_payment` と `official_compensation` が空欄なのは、金額が不明だからではない。`participates_in_order_exchange=False` であるため、payment transactionから正式に除外され、payment recordとcompensation recordが作られないためである。

| 区分 | production・research outputの生値 | 実際の金銭移転額 |
|------|-----------------------------------|------------------|
| 支払 | `official_payment=None` | `effective_payment_amount=0` |
| 補償 | `official_compensation=None` | `effective_compensation_amount=0` |

診断上の集計:

- payment record不存在、`absent_not_applicable`: 24
- compensation record不存在、`absent_not_applicable`: 24
- `effective_payment_amount=0`: 24
- `effective_compensation_amount=0`: 24
- unexpected payment record=0
- unexpected compensation record=0

None、空欄、数値0、正式な対象外を混同しない。

### 16.6 分割記録状態

**今回の記録で完了した範囲**

- trial設計
- trial全体結果
- 63取引の抽出関係
- nonparticipating 24件の順位保護
- nonparticipatingの支払・補償対象外契約

**同じ## 16へ後続作業で追記する予定の範囲**

- payment balanceの浮動小数点丸め差
- 取引別横並びレビュー
- T=367の同一inlink buyer 3台取引
- 全参加reference 5取引対nonparticipating条件1取引の比較
- difference=1境界候補反証
- 限定付き結論
- 最新再開地点

上記後続事項は、チャット上では調査済みであるが、本メモへの **分割記録は未完了** である。今回の追記時点では完了済みとして扱わない。

`ORDER_EXCHANGE_PROGRESS_3.md` への反映は、詳細設計第5巻の## 16が完成した後に別作業で行う。

### 16.7 payment balanceの浮動小数点丸め差

初回診断では、buyer支払合計とseller補償合計を浮動小数点の完全一致（`==`）で比較したため、実際には収支が成立している取引を **13取引** 不一致と誤判定した。

**確認された生の差**

- 非0の生差があった取引: 13取引
- 絶対差の範囲: 約6.94e-18から2.22e-16
- 最大絶対差: `2.220446049250313e-16`
- 特定の1取引だけの問題ではない

**原因**

- 複数の浮動小数点数を別々に加算したことによる丸め差
- productionの支払・補償計算の不整合ではない
- 診断スクリプト側の完全一致判定が不適切だった

**修正後の契約**

- `payment_balance_difference` には生の差をそのまま保存する（0へ丸めたり書き換えたりしない）
- `payment_balance_satisfied` は `math.isclose()` で判定する（`rel_tol=1e-12`、`abs_tol=1e-12`）
- `None`、`bool`、非数値、NaN、正負のinfinityは成立扱いにしない
- buyerのofficial paymentだけを支払合計へ入れる
- sellerのofficial compensationだけを補償合計へ入れる
- nonparticipatingのeffective amount 0を正式合計へ重複加算しない

**修正後の結果（詳細診断63取引）**

- payment balance satisfied: 63取引
- payment balance unsatisfied: 0取引
- 最大絶対差: `2.220446049250313e-16`（生値として残る）

初回出力は削除せず、次へ退避した。

`research_outputs/trial/tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_nonparticipation_seed_3_selected_transaction_fundamentals_diagnostic_before_payment_tolerance_fix_20261020/`

### 16.8 取引別横並びreviewと人間による確認範囲

**review生成スクリプト**

- `research_scripts/summarize_tvt_mp_nonparticipating_20_selected_transaction_review.py`

**主要出力**

- `research_outputs/trial/tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_nonparticipation_seed_3_selected_transaction_fundamentals_diagnostic/selected_transaction_fundamentals_review.csv`

**review CSVの構造**

- 1行は、1選択取引のtrade scope内1 Visit
- 233行、63取引
- 対象decision Tは15〜596
- 各行にdecision T、Node、candidate identityを明示
- 同一取引の全party行を連続配置
- 取引内はBaselineローカル順位順

**横並びにした主要情報**

- Baseline A、Actual A、Baseline P、Candidate P、Actual P
- Baselineローカル順位、Candidateローカル順位、Candidate Node連続順位、Actual Node連続順位
- role、inlink、true VOT、declared VOT
- 個人経済条件、buyer価値G_b、seller必要補償R_s
- official payment、official compensation、effective payment、effective compensation、satisfaction
- nonparticipatingの予測・実績時間影響、payment balance、限定整合検査

**限定自動検査結果**

- 233/233行pass、fail 0
- nonparticipating順位保護fail 0
- role別金銭契約fail 0
- payment balance fail 0
- 到着・通過・順位差分の算術不一致0
- 順位列整合fail 0

**限定の明記**

この自動検査は、明確な算術関係と既確定契約の確認である。全セルの経済的・交通工学的意味を網羅的に判断したものではない。

**人間がT順に横並び表を確認した範囲**

- 第1群: 第1〜第9取引
- 第2群: 第10〜第18取引
- 第3群: 第19〜第27取引
- 合計27取引、T=15〜253

この27取引で確認した範囲:

- Baseline AとActual Aについて、保存値・再計算上の明確な矛盾なし
- Candidate PとActual Pの明確な不一致なし
- Candidate Node連続順位とActual順位の明確な不一致なし
- buyer経済条件は全buyerで適合
- sellerへの必要補償は支給
- payment balance成立
- nonparticipating順位保護成立
- 明確な保存値・算術・role契約上の矛盾なし

残り36取引を無条件にすべて人間レビューする方針は採用しなかった。

### 16.9 同一inlink複数buyer・seller取引の全63取引横断抽出

T順レビュー後に、詳細診断63取引全体へ次の追加条件を適用した。

**追加確認条件**

- 同一取引・同一inlinkにbuyerが2台以上
- または、同一取引・同一inlinkにsellerが2台以上

この条件では、buyerとsellerが同じinlinkに1台ずついるだけの取引は対象にしない。

**集計結果**

- 63取引全体の該当: 1取引
- 第1〜第3群の27取引内の該当: 0取引
- 残り36取引内の該当: 1取引
- 同一inlink複数buyer取引: 1取引
- 同一inlink複数seller取引: 0取引

**唯一の該当取引**

- T=367、Node=west_intersection
- buyer 3台、seller 1台、nonparticipating 0台
- buyerのinlink: `west_south_to_west_intersection`
- buyer: `veh_ws_94:1`、`veh_ws_95:1`、`veh_ws_96:1`

この1取引を追加で人間が横並びレビューした。

**人間によるレビュー済み取引**

- T順の先行27取引
- 追加条件該当T=367の1取引
- 合計28取引

**残る35取引の位置づけ**

- 今回の追加確認条件には該当しない
- 現時点では追加の人間レビュー対象外
- 「人間レビュー未完了の35取引」と位置づけない
- 別の明確な疑問または追加条件が生じた場合に、review CSVから再抽出する

### 16.10 T=367の同一inlink buyer 3台取引と全参加referenceとの比較

#### 取引構成

- T=367、Node=west_intersection
- buyer 3台、seller 1台、nonparticipating 0台

**Baseline順**

1. `veh_wn_123:1`、seller
2. `veh_ws_94:1`、buyer
3. `veh_ws_95:1`、buyer
4. `veh_ws_96:1`、buyer

**Candidate順**

1. `veh_ws_94:1`、buyer
2. `veh_ws_95:1`、buyer
3. `veh_ws_96:1`、buyer
4. `veh_wn_123:1`、seller

buyer 3台は同じinlink `west_south_to_west_intersection`。同一inlink内の相対順は `veh_ws_94:1` → `veh_ws_95:1` → `veh_ws_96:1` で、BaselineとCandidateの両方で維持された。

#### 横並び結果（party別）

**`veh_ws_94:1`**

- role=buyer
- Baseline A=375、Actual A=375
- Baseline P=377、Candidate P=376、Actual P=376
- Baselineローカル順位=2、Candidateローカル順位=1
- Candidate Node連続順位=216、Actual Node通過順位=216
- 期待時間短縮=1、G_b=0.9883854144118044
- official payment=0、satisfaction=satisfied

**`veh_ws_95:1`**

- role=buyer
- Baseline A=377、Actual A=376
- Baseline P=379、Candidate P=377、Actual P=377
- Baselineローカル順位=3、Candidateローカル順位=2
- Candidate Node連続順位=217、Actual Node通過順位=217
- 期待時間短縮=2、G_b=0.5540288683520574
- official payment=0、satisfaction=satisfied

**`veh_ws_96:1`**

- role=buyer
- Baseline A=379、Actual A=377
- Baseline P=383、Candidate P=378、Actual P=378
- Baselineローカル順位=4、Candidateローカル順位=3
- Candidate Node連続順位=218、Actual Node通過順位=218
- 期待時間短縮=5、G_b=8.795254834296866
- official payment=0、satisfaction=satisfied

**`veh_wn_123:1`**

- role=seller、inlink=`west_north_to_west_intersection`
- Baseline A=373、Actual A=373
- Baselineローカル順位=1、Candidateローカル順位=4
- Baseline P=381、Candidate P=380、Actual P=380
- expected delay=0、R_s=0
- official compensation=0、satisfaction=satisfied

**重要な意味**

- sellerはローカル順位では1位から4位へ後退したが、Candidate PはBaseline Pより1 timestep早い
- 順位後退が時間的損失を必ず生むわけではない（expected delay=0、R_s=0）
- buyer 3台のofficial paymentも0、payment total=0、compensation total=0、payment balance成立

**本取引の確認結果**

- 同一inlink内のbuyer順序逆転なし
- buyer 3台はBaseline順位2・3・4からCandidate順位1・2・3へ移動
- Candidate P=Actual P、Candidate Node連続順位=Actual順位
- buyer全3台でpasses_positive_buyer_value_condition
- 全4行limited check pass
- 明確な保存値・算術・role契約上の矛盾なし

#### 全参加referenceとの比較

比較値の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md` の **## 15. 修正後の西側複数buyer成立取引5件** を参照する。旧実装の誤ったclearance処理下のT=310観察を比較値に使用しない。比較値の5取引は、詳細設計第4巻の修正後正本である。

**全参加reference**（西側交差点・同一inlink上の複数buyerを含む成立取引5取引）

- T=310: buyer 2、seller 1
- T=316: buyer 3、seller 1
- T=331: buyer 3、seller 1
- T=338: buyer 2、seller 1
- T=344: buyer 4、seller 1

全5取引で次を確認済みである: west_intersection、buyerは同一inlink上、Candidateでも同一inlink内相対順を維持、production FIFO inspection合格、診断側の再比較でもFIFO違反0。

**nonparticipating約20％混入trial**

- 同じ条件に該当する成立取引は1取引（T=367、buyer 3台、同一inlink内相対順維持）

**比較結果**

- 全参加reference: 5取引
- nonparticipating約20％混入: 1取引

今回の2 trial間では5取引から1取引へ減少したが、ゼロにはならなかった。

#### 比較の限定付き解釈

**当初の予想**

nonparticipating Vehicleが同一inlinkのparticipating prefixを途中で遮断するため、同一inlink複数buyer取引は発生しにくくなると予想した。

**今回の結果**

- 全参加reference=5取引、nonparticipating約20％混入=1取引
- 今回の比較では減少したが、T=367でbuyer 3台の取引が成立し、ゼロにはならなかった

**限定付き解釈**

- nonparticipatingは同一inlinkのparticipating prefixを途中で停止させるため、複数buyer候補を減らす方向へ作用し得る
- しかし、参加属性の変更により他の取引の成立・不成立、順位確定、実World交通状態も連鎖的に変化する
- 別の時点では、同一inlink上にparticipating Vehicleが連続して並び、複数buyerとして成立する条件が生じ得る
- 発生はnonparticipating率だけでは決まらない。到着時刻、inlink上の物理順、参加車両の連続配置、VOT、Baseline P、Candidate P、seller必要補償額、既往の順位確定、交通状態などの具体的な組合せに依存する
- 利用者の表現でいう「車両間の偶然の巡り合わせ」の影響を受ける。研究記録では「偶然」だけで終わらせず、上記の構成要因を併記する
- **各条件1 trial** のため、一般則や統計的傾向とはしない
- 「nonparticipatingを約20％にすると必ず5分の1になる」とは結論づけない
- 「nonparticipating率に対して単調に減少する」とも結論づけない
- 複数seedまたは複数nonparticipating率の感度分析なしに単調性を評価しない

#### 今回の分割追記状態

§16.6の記録時点に加え、今回までにメモ記録が完了した範囲:

- trial設計
- trial全体結果
- 63取引抽出
- nonparticipating順位保護
- payment balance
- 取引別review CSV
- 人間レビュー28取引
- 同一inlink追加条件抽出
- T=367横並びレビュー
- 全参加reference 5取引対1取引の比較
- 限定付き解釈

メモへの後続追記として残る範囲:

- difference=1境界候補反証
- 3 Visitから4候補の正確な構造
- difference=1の限定付き結論
- §16全体の最新再開地点
- 進捗メモへの短い要約

### 16.11 difference=1境界候補の疑問とproduction原典

検索用の問い（境界候補・不当除外の疑い）: 最後のbuyerの到着が権利保有車両の通過直前になる候補がないのではないか。権利保有車両のBaseline Pと最後のbuyerのBaseline Aの差が1（**difference=1**、**P−A=1**、**差1**）にならないのではないか。**difference=1**候補が実装で**不当除外**されているのではないか（**実装ミス**）。

#### 選択済み63取引でのdifference分布

選択済み63取引について、次を計算した。

difference = 権利保有車両のBaseline P − 選択候補の**最後のbuyer**のBaseline A

- difference=2: 47取引
- difference=4: 16取引
- difference=1: 0取引
- difference=3: 0取引

#### 成立130取引全体でのdifference分布

- difference=2: 103取引
- difference=4: 17取引
- difference=6: 10取引
- difference=1: 0取引

#### 疑問

正式仕様では、Baseline Aが権利保有車両のBaseline Pより1 timestep以上前であればcandidate Visitになり得る。すなわち、**difference=1**は許容されるはずなのに、選択された成立取引には1件も現れなかった。

#### 検討中に生じた誤説明と訂正

**誤説明**: Baseline Aが2 timestep刻みだからdifference=1が発生しない可能性がある。

**訂正**:

- 東側交差点のVehicle departureは各方向とも毎timestepである
- departure間隔だけではdifferenceが2・4に限定される理由を説明できない
- この仮説は撤回した

#### production原典: candidate Visit形成

条件（権利保有車両のBaseline Pを `p` とする）:

- `baseline_arrival_timestep <= p - 1`

実装:

```text
if baseline_arrival_timestep > p - 1:
    continue
```

したがって、**difference=1**のVisitは **candidate_visits** へ正式に入る。

#### buyer候補形成契約（prefix・同一inlink・nonparticipating）

- 権利保有車両とは**別inlink**がbuyer候補の対象
- 各inlinkの物理先頭から連続するparticipating Visitをprefixとして扱う
- **nonparticipating**が現れた位置で、そのinlinkのparticipating **prefix停止**
- 空prefixから最大prefixまでの各prefix長を候補化する
- 複数inlinkのprefixを組み合わせる
- **difference=1**そのものを理由にbuyer候補から排除する条件はない

#### candidate選択順

1. economically feasibleな候補だけを残す
2. surplus最大の候補を残す
3. 同率ならbuyer数最大
4. さらに同率なら固定局所乱数で選ぶ

### 16.12 difference=1全候補診断

**診断スクリプト**

- `research_scripts/diagnose_tvt_mp_nonparticipating_20_boundary_difference_one_candidates.py`

**出力directory**

- `research_outputs/trial/tvt_mp_two_cross_intersections_downstream_spillback_extended_south_pulse_seed_1_nonparticipation_seed_3_boundary_difference_one_diagnostic/`

**出力CSV**

- `difference_one_candidate_audit.csv`

**診断範囲**

- decision T=0〜599、全対象Node
- candidate Visitが存在したdecision=233
- 成立・不成立を問わず、生成されたconcrete buyer candidateを追跡
- candidate形成、FIFO、Candidate局所計算、経済評価、最終選択を対応付けた

**段階別結果（difference=1・境界候補）**

| 段階 | 件数 |
|------|------|
| candidate_visits内のdifference=1 Visit | 44 |
| concrete buyer候補へ入った一意なdifference=1 Visit | 3 |
| difference=1を含むconcrete candidate | 4 |
| FIFO通過 | 4 |
| Candidate局所計算resolved | 4 |
| economic resultあり | 4 |
| economically feasible | 0 |
| maximum surplus候補 | 0 |
| final selected | 0 |

**4候補共通の不成立理由**

- `total_buyer_value_below_required_compensation`
- すなわち全4候補で **G < R**（**economically infeasible**）

**44 Visitの内訳**

- 40 Visit: 権利保有車両と**same inlink**（**同一inlink**）に属したため、buyer候補の対象外
- 1 Visit: **nonparticipating**であり、その位置でparticipating prefixが停止
- 3 Visit: 正式にbuyer候補へ入った

保存済みparticipating prefixとconcrete buyer集合の不一致: 0。**不当なcandidate欠落**: 0。

**重要な因果関係**

difference=1 Visitが存在しなかったのではない。**candidate_visits内に44** Visit存在した。そのうち一意なdifference=1 buyer Visitは3であり、**4 concrete candidate**が生成された。4候補はFIFOと局所計算を通過して経済評価へ到達したが、申告VOTと予測時間短縮から得られるbuyer価値Gがseller必要補償Rを下回った（**G < R**）ため、経済条件不成立となった。結果だけでなく、この原因を本節の正式記録とする。

### 16.13 3つの一意なVisitから4候補になる構造

「一意なdifference=1 buyer Visitが3つなのに、difference=1を含む候補が4つある」という疑問（**3 Visitから4候補が生成される理由**）を、曖昧さなく記録する。

異なるdecisionに属する3 Visitが相互に組み合わされたのではない。「3つのVisitがすべて別decisionに存在した」「バラバラの3 Visitから4候補が作られた」とは記録しない。

#### T=12 east_intersection

**権利保有車両**

- `veh_es_1:1`、Baseline P=19

同じdecisionにdifference=1のbuyer Visitが2台存在した。

1. `veh_ee_1:1` — Baseline A=18、difference=1
2. `veh_en_1:1` — Baseline A=18、difference=1

この2台はそれぞれbuyer候補になり、複数inlinkの**buyer prefix**組合せにより次の3候補が生成された。

**候補1** — buyers=`veh_ee_1:1`

- G=1.0442185618892235、R=2.2003144786876243、surplus=−1.1560959167984008

**候補2** — buyers=`veh_en_1:1`

- G=2.136995013982228、R=3.2445330405768478、surplus=−1.1075380265946198

**候補3** — buyers=`veh_ee_1:1`|`veh_en_1:1`

- G=2.1127160688803377、R=4.400628957375249、surplus=−2.287912888494911

#### T=227 west_intersection

**権利保有車両**

- `veh_ws_51:1`、Baseline P=235

**difference=1のbuyer Visit**

- `veh_wn_83:1` — Baseline A=234、difference=1

**生成された候補4** — buyers=`veh_wn_83:1`

- G=0.3075075394111136、R=0.41327156443610596、surplus=−0.10576402502499238

#### 正確な関係の要約

- **一意なdifference=1 buyer Visitは3**
- T=12の同一decisionに2 Visit存在した
- T=12では単独2候補と2 Visitを含む複数buyer候補1つを生成し、T=12で合計3候補
- T=227で1 Visitから1候補
- 全体で **4候補**

### 16.14 限定付き結論と最新再開地点

#### difference=1の限定付き結論

今回のtrialでは、difference=1を**不当に排除する実装ミスは確認されなかった**。

**根拠**

- candidate Visit形成はdifference=1を許容する
- difference=1 Visitはcandidate_visits内に44 Visit存在した
- 3 Visitは正式なbuyer候補になった
- それらを含む4 concrete candidateが生成された
- 4候補すべてFIFOを通過した
- 4候補すべてCandidate局所計算resolvedだった
- 4候補すべて経済評価へ到達した
- 4候補すべて **G < R** だった
- 不成立理由は `total_buyer_value_below_required_compensation` だった
- economically feasible候補が0だったため、surplus最大比較へ残らなかった
- final selected候補は0だった

したがって、成立130取引の最終選択候補にdifference=1が存在しなかった直接原因は、difference=1のbuyer候補が経済条件を満たさなかったことである。

**限定**

- 今回のnetwork、需要、seed、nonparticipating抽出、VOT実現値に対する結論である
- 一般にdifference=1候補が常に経済条件不成立になるとは結論づけない
- 他network、他seed、他VOT分布、他需要ではdifference=1候補が選択される可能性がある
- 「difference=1は構造的に成立不可能」とは記録しない

#### §16全体の記録完了状態

§16へ記録済み:

- trial設計
- trial全体結果
- 63取引抽出
- nonparticipating 24件の順位保護
- payment balance
- review CSV
- 人間レビュー28取引
- 同一inlink追加条件
- T=367
- 全参加reference 5取引対1取引
- difference=1境界反証
- 3 Visitから4候補の構造
- 限定付き結論

この時点で、チャット上で完了した今回の技術調査は§16へ記録済みである。

既存§16.6および§16.10末尾にある「後続追記予定」は、当時の分割記録状態として削除しない。ただし本§16.14において、現在はdifference=1を含む技術記録まで完了したことを明記する（進捗メモ `ORDER_EXCHANGE_PROGRESS_3.md` への要約追記は別作業・**未完了**）。

#### 最新再開地点

**完了**

- nonparticipating約20％混入trial設計・実行
- 機械的限定検査63取引・233行
- nonparticipating順位保護24/24
- payment balance 63/63
- T順27取引の横並びレビュー
- 同一inlink条件による全63取引抽出
- T=367の追加横並びレビュー
- 人間レビュー合計28取引
- 全参加reference 5取引対nonparticipating条件1取引の比較
- difference=1全候補反証

**残る35取引**

- 今回の同一inlink追加条件には該当しない
- 現時点では追加の人間レビュー対象外
- **未完了35取引とは位置づけない**
- 新たな明確な疑問または条件が生じた場合にreview CSVから再抽出する

**次の作業**

1. §16の独立確認
2. `ORDER_EXCHANGE_PROGRESS_3.md`へ短い再開用要約を別作業で追記
3. 作業ツリーと検証状態の整理
4. 文書・trial・診断を含む保存対象の確認
5. `document`を含むコミット名の検討
6. 文書保存後、複雑network検証へ進むか判断

#### 2026-10-20後日完了注記

- §16.1〜§16.14の全文通読と独立確認を完了した
- 主要な数値関係を、既存のTerminal結果、review CSV、difference=1診断結果、詳細設計第4巻§15の全参加reference記録と照合した
- 次の算術関係を確認した
  - 150 buyer + 193 seller + 24 nonparticipating = 367 party
  - Candidate PとActual Pの双方観測360 + Actual P未観測7 = 367 party
  - 83 buyer + 126 seller + 24 nonparticipating = 233 party
  - 44 buyer 1台取引 + 19複数buyer取引 = 63取引
  - 40 same-inlink対象外 + 1 nonparticipating prefix停止 + 3正式buyer候補 = difference=1 Visit 44
  - T=12の3候補 + T=227の1候補 = difference=1を含む4候補
  - T順27取引 + T=367の追加1取引 = 人間レビュー28取引
  - 63取引 - 28取引 = 今回の追加条件に該当しない35取引
- §16に記録した主要数値、T=367のparty別情報、difference=1の因果関係、全参加reference 5取引対nonparticipating条件1取引の比較に、**独立確認上の矛盾は確認されなかった**
- `ORDER_EXCHANGE_PROGRESS_3.md` 末尾への短い再開用要約の追記も完了した
- 進捗メモ末尾の次の節が、現在の最新再開地点である

  `# nonparticipating約20％混入trial・順位保護・difference=1境界反証・同一inlink複数buyer比較完了（2026-10-20）`

§16.6、§16.10末尾、§16.14内にある「後続追記予定」「進捗メモ要約は未完了」「次の作業1・2」は、それぞれの作成時点における分割記録状態として削除しない。ただし、それらは現在の未完了事項ではなく、本後日完了注記によって完了済みへ更新された。

**現在の次の作業**

1. 作業ツリーと保存対象ファイルを確認する
2. trial・診断スクリプトの検証状態を整理する
3. 保存対象を確定する
4. `document`を含むコミット名を検討する
5. コミット結果と残存変更を確認する
6. pushはコミット確認後の別指示で行う
7. 文書保存後、複雑network検証へ進むか判断する

### 16.15 西側・東側NodeのC順位連続性と2回目Visitの順位台帳登録確認（2026-10-21）

本節（2026-10-21）は、nonparticipating約20％混入trialの評価終了時点における **C順位（連続）**（`assigned_rank`）と **順位台帳**（**rank ledger**）の整合を確認した記録である。`actual_node_passage_rank` の全件連続性監査ではない。

検索用の問いの例: **C順位が1から最後まで連続しているか**。**C順位に数字の抜けがないか**（**欠番**）。**二つ目の交差点**へ来るVehicleにもC順位が付いているか。**西側交差点**通過後に**東側交差点**へ来るVehicleの順位。**2回目Visit**が順位台帳から**欠落**していないか（**未登録**・**欠落**0）。

#### 確認目的

- ある対象Nodeについて、**C順位**（連続）が1から最終確定順位まで**欠番**なく連続しているか
- 同じC順位が複数Visitへ**重複**していないか
- 同じ **VisitKey** へ複数のC順位が割り当てられていないか
- **西側交差点**通過後に**東側交差点**へ向かう、対象交差点Visitが**2回目Visit**となるVehicleについても、東側Nodeの順位台帳へ漏れなく登録されているか
- **Visit ID=1** と **Visit ID=2** が混同されていないか
- 評価終了時点でC順位未確定のVisitが、消失せず未確定集合として保持されているか

#### 検証方法

- 成立取引のpartyだけを保存した `tvt_mp_visits.csv` では、trade scope外Visit、baseline fallback確定Visit、先行確定Visitなどが含まれないため、Node全体のC順位連続性確認には使用しなかった
- nonparticipating約20％混入trialを、既存研究出力を上書きせず、研究出力を新規保存しない方法で再実行した
- simulation終了時のWorldにあるNode別順位台帳を直接監査した
- 対象属性: `world.order_control_tvt_rank_states_by_node_name`
- 各Nodeの `OrderControlTvtNodeRankState.export_state()` から `confirmed_visits`、`undetermined_visits`、`assigned_rank`、`vehicle_name`、`visit_id` を取得した
- 検査項目: 最小・最大C順位、1から最大までの欠番、C順位重複、VisitKey重複、想定範囲外順位、`confirmed_visits` の保存順と `assigned_rank` 順の一致、`k_confirmed()` と確定Visit件数の一致、期待Visit集合と確定済み・未確定・未登録Visit集合の照合
- productionコード、trialスクリプト、診断スクリプト、研究出力は変更していない

#### rank ledger（順位台帳）の意味

**rank ledger** は対象Nodeごとに次を保持する。

- どのVisitのC順位が確定したか
- 各Visitへ何位を割り当てたか（`assigned_rank`）
- まだC順位未確定の登録済みVisitはどれか

管理単位はVehicle単体ではなく **VisitKey** `(vehicle_name, visit_id)` である。同一Vehicleの1つ目の対象交差点Visitと **2回目Visit**（**複数交差点**）を区別できる。

#### 西側交差点の需要構成

西側交差点へ向けて発生させたVehicleは合計 **251台**。

| 発生元 | 台数 |
|--------|------|
| `west_north` | 150台 |
| `west_south` | 101台 |
| 合計 | **251台** |

**`west_north`**

- T=15〜114に各timestep 1台（100台）
- T=115〜219は発生なし
- T=220〜269に各timestep 1台（50台）
- 合計150台、同一timestepでの複数台発生なし

**`west_south`**

- T=15〜113の奇数timestepに各1台（50台）
- T=115〜219は発生なし
- T=220〜320の偶数timestepに各1台（51台）
- 合計101台、同一timestepでの複数台発生なし

このnetworkでは西側交差点へ向かうVehicleは西側通過後に同交差点へ戻らないため、**西側交差点**については1 Vehicleにつき対象Visitは最大1回である。

#### 西側交差点のC順位結果

評価終了時点: `world_T=600`、Node=`west_intersection`。

| 項目 | 結果 |
|------|------|
| `k_confirmed` | 251 |
| confirmed Visit | 251 |
| unique VisitKey | 251 |
| unique assigned rank | 251 |
| 最小C順位 | 1 |
| 最大C順位 | 251 |
| 欠番 | 0 |
| C順位重複 | 0 |
| VisitKey重複 | 0 |
| 想定範囲外順位 | 0 |
| export保存順とassigned rank順の一致 | True |
| undetermined Visit | 0 |
| `assigned_rank_sequence_is_continuous` | True |

西側交差点へ向けて発生させた **251台** と、C順位確定Visit 251件が一致した。

**限定付き結論（西側）**: 北側・南側から発生させた251台すべてについて、**C順位1〜251** が1 Visitにつき1つ、欠番・重複なく確定した。確認したのはC順位（`assigned_rank`）であり、251台すべての実Node通過完了をこの結果だけから結論づけない。

#### 西側交差点の最後の成立取引

- 意思決定時刻 T=367、Node=`west_intersection`
- buyer 3台、seller 1台、nonparticipating 0台

当事者（C順位と **VisitKey**）:

- C順位216: `veh_ws_94:1`、buyer
- C順位217: `veh_ws_95:1`、buyer
- C順位218: `veh_ws_96:1`、buyer
- C順位219: `veh_wn_123:1`、seller

この取引以後にもC順位220〜251の32 Visitが確定しているが、西側交差点でT=367より後に成立したTVT取引はない。「C順位220〜251が実際に通過済み」とは、本順位台帳確認だけからは記録しない。

#### 東側交差点の期待Visit集合

**Visit ID=1** — 東側で発生し、東側交差点が最初の対象交差点となるVehicle

- `east_north`: 100台
- `east_outer`: 100台
- `east_south`: 100台
- 合計 **300** Visit

**Visit ID=2** — 西側北側から発生し、西側交差点通過後に東側交差点へ進むVehicle

- orig=`west_north`、dest=`east_outer`、planned_movement=`left`
- **99台**（東側交差点では **Visit ID=2**）

東側交差点の期待Visit合計: Visit ID=1が300 + Visit ID=2が99 = **399 Visit**。

次のVehicleは東側交差点へ進まない: `west_north → west_south` 51台、`west_south → west_outer` 101台。

#### 東側交差点の順位台帳結果

評価終了時点: `world_T=600`、Node=`east_intersection`。

| 区分 | Visit ID=1 | Visit ID=2 | 合計 |
|------|------------|------------|------|
| 期待 | 300 | 99 | **399** |
| confirmed | 240 | **76 confirmed** | **316 confirmed** |
| undetermined | 60 | **23 undetermined** | **83 undetermined** |

照合:

- Visit ID=1: 240 confirmed + 60 undetermined = 300 expected
- Visit ID=2: **76 confirmed + 23 undetermined = 99 expected**
- 全体: **316 confirmed + 83 undetermined = 399 expected**

欠落・想定外:

- expected Visit ID=1の未登録・欠落=0
- expected Visit ID=2の未登録・欠落=0
- 想定外のconfirmed Visit=0
- 想定外のundetermined Visit=0

西側交差点通過後に東側交差点へ向かう99台すべてが、東側Nodeの順位台帳へ **Visit ID=2** として登録されていた（C順位確定済み76、登録済みだがC順位未確定23、**未登録・欠落=0**）。

#### 東側交差点の確定済みC順位連続性

- `k_confirmed=316`
- 最小C順位=1、最大C順位=316
- unique assigned rank=316
- 欠番=0、C順位重複=0、VisitKey重複=0、想定範囲外順位=0
- export保存順とassigned rank順の一致=True
- `assigned_rank_sequence_is_continuous=True`

東側交差点で評価終了時点までに確定したC順位は **1〜316** まで欠番・重複なく連続している。未確定83 Visitに対して、確定済みC順位列の途中へ予約順位や穴を設けていない。

**未確定83 Visitの意味**

未確定83 Visitは消失・未登録ではない。評価終了時点までにC順位が確定しなかったため、順位台帳の `undetermined_visits` として保持されている。将来の順位付与を実際に継続実行して確認したわけではないため、「未確定83 Visitは必ず317位以降へ確定する」「評価期間を延長すれば全件確定する」とは断定しない。

#### 限定付き結論

- **西側交差点**では、期待Vehicle **251台** とC順位確定Visit 251件が一致し、C順位1〜251は欠番・重複なしだった
- **東側交差点**では、期待 **399 Visit** の全件が、確定316または未確定83として順位台帳に存在した
- 東側で確定済みのC順位1〜316は欠番・重複なしだった
- 西側通過後に東側へ進む2回目Visit 99件は、確定76、未確定23として全件登録され、未登録・欠落0だった
- **Visit ID=1** と **Visit ID=2** の期待集合との不一致はなかった
- 同一Vehicleの複数対象交差点Visitを、VisitKeyにより区別して管理できていた
- **複数交差点**を通るVehicleについても、東側Nodeの順位台帳登録とC順位確定済み部分の連続性に明確な不整合は確認されなかった

**限定**

- 確認したのはC順位である `assigned_rank`。`actual_node_passage_rank` の全件連続性監査ではない
- C順位確定は実Node通過完了と同義ではない
- 東側の未確定83 Visitについて、将来の最終C順位までは確認していない
- 今回のnetwork、需要、seed、nonparticipating抽出、評価終了時点T=600に対する結果である

#### 最新再開地点

**今回追加で完了**

- 西側交差点のC順位1〜251の連続性確認
- 西側期待Vehicle 251台との照合
- 東側交差点の期待399 Visitとの照合
- 東側C順位1〜316の連続性確認
- Visit ID=2の99件について、確定76・未確定23・未登録0の確認
- 複数交差点Visitの順位台帳登録確認

**次の作業**

1. 本§16.15の独立確認
2. `ORDER_EXCHANGE_PROGRESS_3.md`へ短い再開用要約を別作業で追記
3. 必要なら今回の監査を再実行可能な診断スクリプトとして保存するか判断
4. 保存する場合は、既存trialを変更せず新規診断スクリプトとする
5. 記録・検証完了後、複雑network検証へ進むか判断する

#### 再実行可能な順位台帳診断の作成と本体実行完了

Terminalへ貼り付けた一時監査だけで終わらせず、再実行可能な新規診断スクリプトを作成した。

- 新規ファイル: `research_scripts/diagnose_tvt_mp_nonparticipating_20_node_rank_ledger_continuity.py`
- 既存trialの `main()` は、既存出力directory拒否と研究出力書込みを行うため使用しない
- trialのWorld構築・Vehicle追加・simulation実行経路だけを再利用する
- 研究CSVを書き出さない。`research_outputs` を新規作成・上書きしない
- simulationは1回だけ実行する。追加World.copyは行わない
- spillback observation hookは `run_simulation_once()` 内の `finally` で **1回だけ** 復元する
- Python recursion limitは `main()` の `finally` で復元する
- **二重restore解消**: 実装前独立確認で `main()` の `finally` にも `restore` があり二重実行となる構造を発見し、`main()` 側の余分な `restore_real_world_spillback_observation()` を削除した（restore関数の冪等性には依存しない）
- 出力は標準出力だけである

**静的検証**

- `py_compile` 成功
- `--static-validate-only` 成功
- 出力: `Static contract validation passed.`

**本体実行**

- nonparticipating約20％混入trialを630 timestep実行
- simulation終了時 `world_T=600`
- 実行時間は出力上、約1737秒（約29分）
- 終了コード0
- 最終出力: `final_overall_status=passed`、`Node rank ledger continuity diagnostic passed.`

**西側再現結果**

- expected=251、confirmed=251、undetermined=0
- missing_unregistered=0、unexpected_confirmed=0、unexpected_undetermined=0
- rank min=1、rank max=251
- missing ranks=0、duplicate ranks=0、duplicate VisitKeys=0
- **west continuity=True**

**東側再現結果**

- Visit ID=1: expected=300、confirmed=240、undetermined=60、missing=0
- Visit ID=2: expected=99、confirmed=76、undetermined=23、missing=0
- 全体: expected=399、confirmed=316、undetermined=83
- unexpected confirmed=0、unexpected undetermined=0
- rank min=1、rank max=316
- missing ranks=0、duplicate ranks=0、duplicate VisitKeys=0
- **east continuity=True**

**結論**

- §16.15へ記録した一時監査結果は、新規診断スクリプトの本体実行でも再現された
- 西側・東側とも、確定済みC順位の連続性監査に合格した
- 東側の **Visit ID=2** についても、期待99件が確定76・未確定23として全件登録され、欠落0だった
- 確認対象は `assigned_rank` であり、`actual_node_passage_rank` の全件監査ではない
- production、trial、既存診断、研究出力は変更していない

#### 最新再開地点（診断スクリプト本体実行後）

**完了**

- 順位台帳監査の診断スクリプト化判断は完了
- 新規診断スクリプトのstatic validationと本体実行は完了

**次の作業**

1. `ORDER_EXCHANGE_PROGRESS_3.md`へ短い完了要約を別作業で追記する
2. 保存対象と作業ツリーを確認する
3. `document`を含むコミット名を検討する
4. pushはコミット確認後の別指示で行う
5. 保存後、複雑network検証へ進むか判断する

## 17. 4交差点複雑network検証、baseline進路不一致（baseline route mismatch）、および到着時進路・通過時進路の二field設計（2026-10-22）

### 17.1 本節の位置づけと旧契約との関係

本節は、**4交差点**・**複雑network**（2×2格子の中央4十字路交差点＋外周8 OD）におけるTVT-MP全参加trialの結果、**600台**版実行時の **baseline進路不一致**（**baseline route mismatch**）、原因調査、および **実装未完了** の修正設計を記録する。

検索用キーワード: 4交差点、複雑network、baseline route mismatch、baseline進路不一致、到着時進路、通過時進路、route_next_link再選択、baseline_passage_route_next_link_name、physical passage route、T−1以前のC順位確定済み先行Visit、過去formal route fallback、非拘束後続Vehicle、DETERMINISTIC_VIRTUAL_ROUTE、TVT検討不可、unresolved candidate passages、実装未完了。

**旧契約（当時の設計記録として維持）**

第5巻内の12台中央交差点trial記録（§17「candidate予測とactual結果」付近、行番号は版により変動）には、次の旧記述が残っている。

- 同一baseline仮想計算の同一Visitでは、Node到着時に決まった`route_next_link`に従って通過する。
- 到着記録の`route_next_link_name`と通過時のlive `route_next_link`の一致検査は、この同一Visit内の整合性検査である。

上記は **当時の設計記録** である。本節では削除・書換えしない。

**4交差点network検証による見直し**

4交差点・長時間・多経路・長い終端待機条件下では、UXsim通常機能による **route_next_link再選択** が起こり、到着時にcollectorへ保存した進路と、物理通過直前のlive outlinkが一致しない事例が確認された。その結果、未確定かつsnapshot登録済みVisit向けの「到着時進路＝通過時進路」前提と、到着記録とlive outlinkの一致検査は、現行production契約と矛盾する。

**最新契約の参照先**

到着時進路と **baseline物理通過時進路**（**physical passage route**）を分離し、Visit区分別の進路優先規則を適用する設計の正本は **本節（§17）** である。旧記述は歴史的経緯の参照用とし、実装・再開時は本節を優先する。

### 17.2 4交差点複雑networkの設計

**topology**

- 中央4つの十字路交差点を **2×2格子** に配置
- 周囲に **8つの外周OD Node**
- 合計 **12 Node**
- 方向別 **24 Link**
- **中央4 Node** のみTVT-MP対象（`order_control_type=time_value`）
- 全Link **200 m**
- 自由流速度 **60 km/h** 相当
- **単車線**
- **UXsim既定容量**
- **signalなし**
- **specified_routeなし**
- **taxi modeなし**
- TVT対象Nodeでの **trip-endなし**
- network構造上のループは禁止しない
- 同一Node再訪を今回の必須条件にはしない

**trialスクリプト（ファイル名は変更せず維持）**

- `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_all_participating_trial.py`
- 新規trialは **現在のproduction** `run_tvt_mp_driver` を呼び出す。古いdriverのtrial側複製ではない。
- spillback観測wrapperはbaseline fork中に無効化され、元のproduction driverとLink.updateへ戻る。wrapperが経路不整合の原因である証拠はない。

**需要の経緯**

- 初回は主OD **8種類**、基礎需要400台＋pulse100台＝ **500台**、評価 **T=0〜449**、internal TSIZE **480**、実World終了 **T=450**
- 初回500台trialで、内部方向別8 Linkのうち次の2 Linkが **最大Vehicle数0**（未使用）だった。
  - `northeast_intersection_to_northwest_intersection`
  - `southwest_intersection_to_northwest_intersection`
- 上記を直接利用する主ODを各50台追加した。
  - `north_east_od` → `west_north_od`
  - `south_west_od` → `north_west_od`
- 既存8主ODとpulse需要（`west_north_od`→`east_north_od`、`north_west_od`→`south_west_od`、各50台、T=160..258 step 2）は維持

**修正後需要・評価（600台版、trialスクリプト上の確定条件）**

| 項目 | 値 |
|------|-----|
| 主OD数 | 10 |
| 基礎需要 | 500台 |
| pulse需要 | 100台 |
| Vehicle総数 | 600台 |
| 参加 | 全車 `participates_in_order_exchange=True` |
| 評価期間 | T=0〜899 |
| internal TSIZE | 930 |
| 実World終了 | T=900 |
| horizon | 30 |
| clearance | 1 |
| candidate上限 | 10 |
| TRAFFIC_SEED | 0 |
| VOT_SEED | 1 |

**scenario・出力（600台版）**

- scenario名: `tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_trial`
- 出力directory: `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_initial`
- 500台版出力 `…_seed_1_initial`（評価449・500台）は上書きしない

### 17.3 初回500台trial（評価T=0〜449）の結果

初回500台・評価T=0〜449のtrialは **正常終了** した。主要結果は次のとおり（当該runの`run_summary.txt`等に基づく観察事実）。

- 12 Node、24 Link、500台
- 4対象Nodeすべてで取引成立
- 成立 **227** 取引
- Node別取引数: `northwest_intersection` 56、`northeast_intersection` 29、`southwest_intersection` 88、`southeast_intersection` 54
- buyer延べ274、seller延べ336
- Candidate PとActual Pの双方観測 **603**
- Candidate P=Actual P **603**、不一致 **0**
- Actual P未観測 **7**
- Visit ID件数: Visit ID 1が463、Visit ID 2が396、Visit ID 3が **84**
- 最大Visit ID **3**
- 内部Link最大Vehicle数 **38**
- trip完了 **324/500**、trip未完了 **176/500**
- 実行時間約 **738秒**（約12分18秒）

内部8方向Linkのうち、次の2方向は最大Vehicle数 **0** だった（取引当事者CSVとspillback要約の双方で未使用）。

- `northeast_intersection_to_northwest_intersection`
- `southwest_intersection_to_northwest_intersection`

`north_east_od` → `west_south_od` について、**確認可能な取引当事者** は `northeast_intersection` → `southeast_intersection` → `southwest_intersection` の南回りを使用していた。これは全50台の完全経路監査ではなく、取引当事者に限定した確認である。全車両について断定した結果ではない。

### 17.4 600台・評価900 timestep版の停止（正式結果としない）

`py_compile` 成功、`--static-validate-only` 成功後、600台版の本体simulationを実行した。実Worldの **T≈600** でbaseline fork内に停止した。

| 項目 | 値 |
|------|-----|
| Node | `northwest_intersection` |
| Vehicle | `veh_wn_se_base_042` |
| Visit ID | 1 |
| collector到着時 `route_next_link_name` | `northwest_intersection_to_southwest_intersection` |
| 停止箇所 | `uxsim/order_control_tvt_mp_physical_transfer.py` の `_copy_validated_baseline_rank_fields()` |
| 例外 | `RuntimeError: Node northwest_intersection: vehicle veh_wn_se_base_042 visit_id 1 baseline field route_next_link_name is missing or inconsistent; got 'northwest_intersection_to_southwest_intersection'.` |

例外メッセージには **live outlink名は含まれない**。例外時のlive outlinkが具体的にどのLinkだったかは **未確認** である。

**本異常終了runは正式trial結果として扱わない。** 研究出力directoryは生成途中であっても、完走・検証済みのbaselineとして採用しない。

### 17.5 原因（確認済み事実と推測）

**確認済み事実（production原典に基づく）**

- VehicleがLink終端（`x == link.length`）にいる場合、`Vehicle.update()` から `route_next_link_choice()` が呼ばれる
- Nodeを通過できずLink終端で待機すると、後続timestepでも `route_next_link_choice()` が呼ばれ、**route_next_link再選択** が起こり得る
- `hard_deterministic_mode=False` では、現在の `route_pref` に基づく確率選択である（研究条件として **Falseを維持**）
- baseline collectorの既存 `route_next_link_name` は、snapshot時既到着ならsnapshot時点、snapshot後にbaseline内で到着したなら **到着時点** に一度保存される
- 待機中の再選択では collector の `route_next_link_name` は **更新されない**
- baseline物理通過成功時には `baseline_passage_timestep` だけが保存され、実際に通過に使用したoutlink名は **保存されない**
- 未確定かつsnapshot登録済みVisitでは、到着時 `route_next_link_name` と現在のlive outlinkの **一致を要求** していた（`_copy_validated_baseline_rank_fields()`）
- そのため、到着後の待機中に進路が変化すると、**物理通過前** に不一致として停止する（**baseline route mismatch**）
- spillback観測wrapperが原因である証拠はない
- 新規trialは現在のproduction TVT-MP driverを使用している

**推測（断定しない）**

- 500台・評価449版で同種の経路再選択が **一度も起きなかったとは断定しない**
- 600台・評価900・複数経路・長時間spillback待機により、終端待機中の再選択が表面化した **可能性** がある。500台版で再選択がなかったことは確認していない

### 17.6 OrderControlBaselineVisitRecordの二field設計

**到着時進路（既存field）: `route_next_link_name`**

- snapshot時既到着ならsnapshot時点の進路
- snapshot後にbaseline仮想World内で到着したなら到着時点の進路
- 到着済みVisitが最低限持つbaseline進路情報
- **通過時進路で上書きしない**

**baseline物理通過時進路（新規field候補）: `baseline_passage_route_next_link_name`**

- baseline仮想Worldで当該Visitが対象Nodeを **物理通過** した際に使用した `outlink.name`
- baseline horizon内に物理通過できたVisitだけが持つ
- 未通過なら `None`
- 途中の **route_next_link再選択** 履歴は保存しない
- **物理通過成功後にだけ** 保存する

`baseline_passage_timestep` と `baseline_passage_route_next_link_name` は、**同じ物理通過事実** に由来する値として **同時保存** する。

**保存API（推奨）**

既存の `apply_baseline_passage_timestep(record, baseline_passage_timestep)` を、次へ置き換える設計とする。

```text
apply_baseline_passage_result(
    record,
    baseline_passage_timestep,
    baseline_passage_route_next_link_name,
)
```

保証する性質:

- 通過 **成功後** にだけ呼ぶ（prepareでは通過時進路を書かない）
- skip、clearance stop、容量不足、入口空間不足では呼ばない
- 到着時 `route_next_link_name` を上書きしない
- 二重適用を拒否する
- 通過時刻だけ、または通過時進路だけが存在する **部分記録** を重大不整合として拒否する

成功経路は少なくとも次に到達させる: TVT-MP confirmed / unconfirmed（`_transfer_one_vehicle_between_links`）、FCFS clearance、BATCH service queue（pendingに移動時のoutlink名を保持し、成功分だけapply）。

### 17.7 TVT検討可否（変更しない）

今回の経路field追加によって、**TVT検討可否の既存条件は変更しない**。

- candidate visits（最大trade scope候補に必要な全Visit）について `baseline_passage_timestep` が揃う → TVT候補検討へ進む
- 必要な `baseline_passage_timestep` が揃わない → TVTを検討しない → candidate局所仮想計算を行わない → baseline順位でC順位を確定する（**TVT検討不可** / **unresolved candidate passages**）

`baseline_passage_route_next_link_name` を、TVT検討可否の **新しい追加条件にしない**。

ただし、`baseline_passage_timestep` があるのに通過時進路がない、またはその逆は、正常なunresolvedではなく **コード不整合** として停止する。情報完備の候補集合では、同じ成功applyから通過時進路も揃う構造にする。

### 17.8 拘束Visitの進路優先規則（今回baselineの意思決定窓内）

対象には次を含む。

- trade scope内Visit
- trade scope外の意思決定窓内Visit
- 現在Tで既到着として先行確定されるVisit
- 現在Tでleading nonparticipatingとして先行確定されるVisit

進路優先順:

1. 今回baselineの `baseline_passage_route_next_link_name`
2. 通過時進路がなければ今回baselineの `route_next_link_name`

両方なければ不整合として停止する。**DETERMINISTIC_VIRTUAL_ROUTEは使用しない。**

現在Tで **新たにC順位と正式進路を確定** するVisitの `formal_route_next_link_name` も、同じ優先順（通過時進路があるのに到着時進路を正式進路として保存してはいけない）。

### 17.9 T−1以前にC順位確定済みの先行Visit（局所仮想計算用）

対象は **順位台帳の全履歴ではない**。次をすべて満たすVisitに限定する。

- 検討時点Tで対象Nodeへのinlink上にいる
- 対象Nodeをまだ実通過していない
- T−1以前にC順位確定済み
- 今回の局所順位列で、既到着先行確定Visitおよびleading nonparticipating先行確定Visitを含む意思決定窓内Visitより **前** に位置する

局所仮想計算用進路の優先順:

1. 今回baselineの通過時進路
2. なければ今回baselineの到着時進路
3. 今回baselineで両方得られなければ、rank ledgerに保存済みの過去の `formal_route_next_link_name`（**過去formal route fallback**）

3番目は **rank ledgerへの更新ではない**。今回の局所仮想計算に必要な拘束進路を補う **読み取りfallback** である。別baselineのlive routeを過去進路へ拘束する意味でもない。

**T−1以前のrank ledger entryは、今回baselineの結果で上書きしない。**

実装上は、既存のpartition 1（`k_confirmed_before` prefix、collector snapshotが存在するVisitのみ）がこの集合に対応する。すでに実通過済みでinlink上にいない古いVisitは処理対象に含めない。

### 17.10 FCFS処理される後続の非拘束Vehicle（専用3段階）

**非拘束後続Vehicle** のみ、次の専用規則を用いる（意図した確定仕様）。

1. `baseline_passage_route_next_link_name`
2. なければ `route_next_link_name`（baseline到着時進路）
3. 両方なければ既存の **DETERMINISTIC_VIRTUAL_ROUTE**（容量・入口空間を満たすoutlinkをID順に並べ、`real_vehicle_id % acceptable outlink数`）

**DETERMINISTIC_VIRTUAL_ROUTE** の選択アルゴリズム自体は変更しない。拘束Vehicleには適用しない。

### 17.11 実World・別baseline・局所仮想計算

**実World**

- formal routeへ拘束しない
- UXsimのlive `route_next_link` を使用する
- `hard_deterministic_mode=False` を維持する

**各baseline仮想World**

- そのWorld内でUXsimが進路選択・再選択する
- 実World進路へ固定しない
- 過去baseline進路へ固定しない
- 到着後の待機中の再選択を許容する

**続く局所仮想計算**

- 今回baselineから優先規則で選ばれた進路を **拘束Vehicle** へ固定適用する
- **非拘束後続Vehicle** だけは§17.10の3段階を用いる

**過去から引き継ぐもの**: 確定 **C順位** のみ。過去baselineの進路を別baselineのlive `route_next_link` として引き継がない。

### 17.12 不整合検査の移動（単なる削除ではない）

- 未通過候補形成時に、到着時進路と現在のlive outlinkの **一致を要求しない**
- live outlinkが対象Nodeの有効なoutlinkであること、VisitKey・Node・inlink・到着時刻・tiebreaker等の既存整合性検査は **維持** する
- 通過成功時に、実際に使用した `outlink.name` を通過時進路として保存する
- 局所仮想計算では、選択された正式進路とlive進路の整合性検査（binding transfer等）を **維持** する
- rank ledger確定後のformal route上書きを **拒否** する（既存契約）

### 17.13 名称・enum（設計上）

| 名称 | 役割 |
|------|------|
| `route_next_link_name` | 到着時進路（上書きしない） |
| `baseline_passage_route_next_link_name` | baseline物理通過時進路 |
| `formal_route_next_link_name` | rank ledger上の確定時正式進路 |
| `BASELINE_PHYSICAL_PASSAGE_ROUTE`（新規route origin候補） | 通過時fieldを採用したbinding/final rankの由来 |
| `SNAPSHOT_ROUTE_ALREADY_DECIDED` | snapshot時既到着の到着時進路由来（維持） |
| `BASELINE_TARGET_NODE_ARRIVAL_ROUTE` | baseline内到着の到着時進路由来（維持） |
| `RANK_LEDGER_FORMAL_ROUTE` | T−1先行Visitの3段階fallbackの台帳読み取り（台帳更新ではない） |
| `DETERMINISTIC_VIRTUAL_ROUTE` | 非拘束後続のみ、到着時進路も無い場合 |

### 17.14 設計上のproduction変更対象と変更しない処理順

**変更対象（報告済み）**

- `uxsim/order_control_baseline_collector.py`
- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`
- `uxsim/order_control_tvt_arrived_undetermined_confirmation.py`
- `uxsim/order_control_tvt_leading_nonparticipating_confirmation.py`
- `uxsim/order_control_tvt_mp_local_binding_rank_sequence.py`
- `uxsim/order_control_tvt_mp_final_rank.py`
- `uxsim/order_control_tvt_mp_final_consistency_validation.py`
- `uxsim/order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`
- 関連unit test

**変更しない既存処理順（例）**

到着済み確認 → inlink物理先頭確認 → clearance → clearance未充足時の当該Node処理終了 → 通常物理制約 → 一時スキップ → 次timestep再評価

**変更しない意味**

C順位、baseline passage timestep、candidate passage timestep、actual passage、payment、compensation、transaction selection、`hard_deterministic_mode`、`specified_route`、taxi、trip-end、BATCHの順位・形成契約

### 17.15 未確定事項・実装後検証

**未確定**

- 600台trial例外時のlive outlink名は未確認
- 500台trialで同種の経路再選択がなかったとは断定しない
- research outputの `predicted_route_next_link_name`、`formal_route_next_link_name`、局所仮想計算で実際に拘束した進路の対応は、**実装時に原典確認** する
- **production実装は未着手**（本節記録時点）
- unit test追加・更新は未着手
- 600台trial再実行は未実施
- nonparticipating条件の4交差点trialは、全参加600台版が正常完了した後に行う

**実装後の検証順（予定）**

1. collectorの同時保存・部分記録拒否・到着時field非上書きのunit test
2. 未確定候補が到着時/live不一致だけでは停止しないこと
3. Visit区分別優先順・台帳非更新・非拘束3段階
4. 既存関連回帰test
5. 小規模integration
6. 4交差点600台・T=0〜899の再実行

#### 最新再開地点（4交差点baseline進路設計確定後）

**完了**

- 4交差点500台trial完走結果の記録
- 600台版停止と原因の整理
- 到着時進路と通過時進路の二field設計確定
- Visit区分別進路優先規則・TVT検討可否非変更の確定
- 設計・反証レビュー（実装前）

**次の作業**

1. 本節（§17）と `ORDER_EXCHANGE_PROGRESS_3.md` の進捗節を読む
2. 確定設計に基づきproductionとunit testを実装する（Cursorには実装のみを依頼し、検証はTerminalで行う）
3. `py_compile`、unit test、static validation、simulationはユーザーがTerminalで実行する
4. Git操作はユーザーがTerminalで行う
5. 600台trial再実行後、nonparticipating版4交差点trialを検討する

**本節が、4交差点複雑networkにおけるbaseline進路契約の最新正本である。**

## 18. baseline物理通過時進路のproduction実装、局所仮想計算の初期拘束進路修正、および4交差点600台trial完走（2026-10-22）

本節は、§17で確定した到着時進路・通過時進路の二field設計について **production実装完了** 後の事実、関連 **unit test完了** 結果、**candidate local virtual calculation** における **initial arrived binding Vehicle** 修正、および **4交差点600台trial** の正式完走を記録する。

全取引・全候補診断、横並び表示、`arrival_tiebreaker` 追加は本節では記録しない（別指示で §19 とする）。

### 18.1 到着時進路と物理通過時進路の二field production実装

`OrderControlBaselineVisitRecord` に次のfieldを追加した。

- `baseline_passage_route_next_link_name: str | None`

既存field `route_next_link_name` は **到着時進路**（baseline到着時進路）として維持する。

新field `baseline_passage_route_next_link_name` は、そのbaseline仮想Worldで当該Visitが対象Nodeを **物理通過** する際に実際に使用した `outlink.name` である（**baseline physical passage route** / **通過時進路**）。

設計上の区別:

| field | 意味 |
|-------|------|
| `route_next_link_name` | baseline到着時進路（**到着時進路**） |
| `baseline_passage_route_next_link_name` | baseline物理通過時進路（**通過時進路**） |

- 到着時進路は通過時進路で上書きしない
- 途中の `route_next_link` 再選択履歴は保存しない
- 通過時進路は物理通過成功後にだけ保存する
- 未通過Visitの通過時進路は `None`

collectorのplain dict出力にも新fieldを含めた。対象:

- `get_baseline_visit_snapshot()`
- `export_node_baseline_visits()`
- `_visit_record_to_plain_dict()`

### 18.2 passage結果保存API（`apply_baseline_passage_result`）

既存API `apply_baseline_passage_timestep()` を廃止し、次へ置き換えた。

```text
apply_baseline_passage_result(
    record,
    baseline_passage_timestep,
    baseline_passage_route_next_link_name,
)
```

このAPIは、通過時刻と通過時進路を、同じ物理通過事実に由来する値として **同時保存** する。**partial passage record**（片側だけの記録）は拒否する。

拒否する例:

- boolまたは無効なpassage timestep
- 空文字列または非文字列の通過時進路
- `baseline_passage_timestep` だけが存在する部分記録
- `baseline_passage_route_next_link_name` だけが存在する部分記録
- 二重apply

到着時 `route_next_link_name` は変更しない。

次の物理通過成功経路を新APIへ接続した。

- TVT-MP confirmed passage
- TVT-MP unconfirmed passage
- 通常merge
- generic baseline fork
- FCFS clearance
- BATCH

BATCHでは、apply時に `vehicle.route_next_link` を読み直していない。物理移動へ実際に使用した `outlink.name` をpending recordとともに保持し、成功後に保存した。

次の場合はpassage結果を保存しない。

- 物理通過失敗
- 一時skip
- clearance stop
- inlink物理先頭ではない
- 容量不足
- 入口空間不足

baseline passage timestepの計算式と意味は変更していない。

### 18.3 baseline到着時進路とlive進路の一致検査変更（baseline route mismatch / baseline進路不一致）

未確定baseline Visitについて、次の完全一致要求を **削除** した。

```text
baseline到着時 route_next_link_name == 現在の live vehicle.route_next_link.name
```

削除理由:

baseline仮想Worldでは、VehicleがNode終端で待機している間も、UXsim通常機能による `route_next_link` 再選択が起こり得る。到着時進路と、実際の物理通過時進路が異なることは正常に発生し得る。

維持した整合性検査:

- VisitKey
- Node名
- Vehicle名
- `vehicle_id`
- inlink
- `baseline_arrival_timestep`
- `arrival_tiebreaker`
- 到着時 `route_next_link_name` が有効な非空文字列であること
- live outlinkが `None` ではないこと
- live outlinkが対象Nodeの登録outlinkであること

物理通過には、そのtimestepのlive outlinkを使用する。通過成功後、その `outlink.name` を `baseline_passage_route_next_link_name` へ保存する。

この変更は一致検査を単純に弱めたものではない。正式進路として使用する値の取得時点を、到着時から **実際の物理通過成功時** へ移したものである。

### 18.4 Visit区分別の進路優先規則

今回baselineで扱う意思決定窓内拘束Visit:

- trade scope内Visit
- trade scope外の意思決定窓内Visit
- 現在Tで既到着として先行確定されるVisit
- 現在Tでleading nonparticipatingとして先行確定されるVisit

**局所仮想計算用進路** および **現在Tで新規確定するformal route** の優先順:

1. `baseline_passage_route_next_link_name`（baseline通過時進路）
2. それがなければ `route_next_link_name`（baseline到着時進路）

両方なければ不整合として停止する。拘束Visitへ `DETERMINISTIC_VIRTUAL_ROUTE` は適用しない。

**T−1以前にC順位確定済みの先行Visit**（partition 1対象に限定）の局所仮想計算用進路:

1. 今回baselineの通過時進路
2. 今回baselineの到着時進路
3. 今回baselineで両方得られなければ、rank ledgerに保存済みの過去 `formal_route_next_link_name`

3番目は、今回の局所仮想計算に必要な拘束進路を補う **読取りfallback** である。rank ledgerの更新・確定済みVisitの再確定・過去進路の `Vehicle.route_next_link` への代入・別baseline仮想Worldの進路拘束を意味しない。

**FCFS処理される後続の非拘束Vehicle**（3段階）:

1. baseline通過時進路
2. baseline到着時進路
3. 両方なければ既存 `DETERMINISTIC_VIRTUAL_ROUTE`

新しいroute origin:

- 拘束側: `OrderControlTvtMpLocalBindingRouteOrigin.BASELINE_PHYSICAL_PASSAGE_ROUTE`
- 非拘束側: `OrderControlTvtMpUnboundRouteClassification.BASELINE_PHYSICAL_PASSAGE_ROUTE`

### 18.5 TVT検討可否は変更していない

`baseline_passage_route_next_link_name` の追加によって、TVT検討可否の既存条件は変更していない。

引き続き、candidate visits（最大trade scope候補に必要な全Visit）について `baseline_passage_timestep` が揃う場合だけTVT候補検討へ進む。必要なbaseline passage timestepが揃わない場合は、TVTを検討せず、candidate局所仮想計算を行わず、baseline順位でC順位を確定する。

`baseline_passage_route_next_link_name` は新しいunresolved条件ではない。ただし次の片側記録は正常なunresolvedではなく、production内部不整合として停止する。

- `baseline_passage_timestep` あり、通過時進路なし
- 通過時進路あり、`baseline_passage_timestep` なし

### 18.6 実World・baseline・局所仮想計算の契約

**実World**

- UXsimのlive `route_next_link` を使用する
- formal routeへ拘束しない
- baseline通過時進路へ拘束しない
- `hard_deterministic_mode=False` を維持する

**各baseline仮想World**

- そのWorld内の交通状態に基づきUXsimが進路を選択・再選択する
- 実Worldの進路へ固定しない
- 過去baselineの進路へ固定しない
- Node終端待機中の再選択を許容する

**続くcandidate局所仮想計算**

- binding Visitに保存された正式進路を拘束Vehicleへ固定適用する
- 非拘束後続Vehicleだけが専用3段階fallbackを使用する

過去から引き継ぐものは確定C順位である。過去baselineの進路は、別baselineのlive進路として引き継がない。

### 18.7 実装後の検証（unit test完了）

**py_compile**: 変更productionおよび関連testについて成功。

主なunit test（いずれも成功）:

| 領域 | 結果 |
|------|------|
| baseline collector tests | 成功 |
| baseline collector UXsim connection tests | 成功 |
| TVT-MP physical transfer | 82 tests passed |
| local binding rank sequence | 49 tests passed |
| final rank | 50 tests passed |
| unbound FCFS transfer | 28 tests passed |
| candidate local virtual calculation | 二field実装後 85 tests passed → 初期拘束進路修正後 **90 tests passed** |
| local virtual calculation set | 41 tests passed |
| arrived undetermined confirmation | 40 tests passed |
| leading nonparticipating confirmation | 33 tests passed |
| final consistency validation | 57 tests passed |
| candidate visit set | 22 tests passed |
| inlink candidate physical order | 25 tests passed |
| candidate binding transfer | 初期拘束進路修正後 21 tests passed |

4交差点600台trialのstatic contract validationも成功した。

検証中に、今回のproduction実装とは別の既存テスト問題を確認・修正した（productionは変更していない）。

1. 古いBATCH単一Visit契約を期待したテストを、現在の複数Visit契約へ更新。登録済みVehicle名でも指定VisitKeyがsnapshot固定集合外なら `prepare_baseline_passage_recording()` は `None` を返し物理通過を許可し、collectorに保存済みの別Visitは変更しない。
2. `order_control_batch_service_queue` は `deque` である。空確認を `queue == []` から `len(queue) == 0` に変更。
3. 複数の物理通過テストで、Vehicleの正式Visit IDとsnapshot取得時Visit IDのfixture参照ミスを修正。
4. 到着時進路とlive進路の不一致を `RuntimeError` として期待していた旧テストを、新契約に合わせて成功テストへ分離（到着時進路保持・live outlinkで物理通過・通過時進路へlive outlink名保存・passage timestep保存）。
5. 新route origin追加に伴い、enum全件列挙テストへ `baseline_physical_passage_route` を追加。
6. 到着時進路だけを前提とした旧エラーメッセージ期待を、「baseline passage route または arrival route の両方欠損」を表す新期待へ更新。

### 18.8 2回目の600台trial停止（binding route mismatch）

baseline通過時進路修正後に600台trialを再実行した。前回の **baseline route mismatch** は解消した。

しかし実World T≈600の **candidate local virtual calculation** で次の例外が発生した。

| 項目 | 値 |
|------|-----|
| Node | `northeast_intersection` |
| Vehicle | `veh_ne_wn_base_032` |
| 局所コピーVehicleのlive `route_next_link` | `northeast_intersection_to_northwest_intersection` |
| binding route | `northeast_intersection_to_southeast_intersection` |

例外（要旨）: live `route_next_link` が binding route と一致しない（**binding route mismatch**）。

この異常終了runは正式trial結果としない。出力ディレクトリは履歴保存のため次へリネーム済み。

`research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_failed_before_initial_binding_route_fix`

### 18.9 candidate局所仮想計算の初期拘束進路適用漏れ（initial arrived binding Vehicle / stale live route）

**原因**

局所仮想計算中に新たに対象Nodeへ到着する拘束Vehicleには、既存の `_apply_current_target_binding_route()` によりbinding進路が適用されていた。

一方、局所仮想計算 **開始時点** で既に `target_node.incoming_vehicles` に入っている拘束Vehicleにはbinding進路が適用されていなかった。処理順ではoffset 0でbinding passage scanがVehicle advanceより先に行われるため、開始時点で到着済みの拘束Vehicleはコピー元の **stale live route** を保持したままscanへ入り、binding routeとの一致検査で停止した。

**修正**

`initialize_tvt_mp_candidate_local_virtual_calculation_state()` で初期化検証完了後、stateを返す前に、開始時点で既に対象Nodeへ到着済みの拘束Vehicleへbinding進路を一度適用した（`apply_initial_arrived_binding_routes`）。

対象条件:

- `binding_visit_local_vehicle_pairs` に含まれる
- current VisitKeyがbinding Visitと一致する
- `target_node.incoming_vehicles` に存在する
- 対象inlink上にいる
- binding routeが対象Nodeのlocal World登録outlinkである
- 局所計算で未通過

複数Vehicleは全件検証後に明示的なループで進路を代入する。一件でも検証失敗した場合、他Vehicleへ部分適用しない。

未到着拘束Vehicleは初期化時に変更せず、既存どおり新規到着時にbinding進路を適用する。非拘束Vehicleへbinding進路を適用しない。実World、baseline collector、rank ledgerは変更しない。

binding transfer直前の一致検査（局所Vehicleのlive `route_next_link` == binding Visitから与えられた拘束進路）は **削除していない**。拘束進路適用後の適用漏れ・予期しない上書きを検出する重大不整合検査として維持する。

追加unit test: initial arrived binding Vehicleがbinding outlinkを使用、初期化後の意図的route破損で一致検査拒否、未到着binding Vehicleの新規到着時適用、非拘束Vehicle非変更、複数Vehicle時の検証失敗で部分適用しない。

### 18.10 4交差点600台trial正式完走

初期拘束進路修正後、600台・評価T=0〜899版を再実行し、正常完了した。

正式出力先:

`research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_initial`

主な結果:

| 項目 | 値 |
|------|-----|
| World.T after simulation | 900 |
| trip完了 | 600台中600台、incomplete 0 |
| 成立取引 | 307件 |
| northwest_intersection | 124 |
| northeast_intersection | 48 |
| southwest_intersection | 91 |
| southeast_intersection | 44 |
| buyer Visit | 361 |
| seller Visit | 486 |
| Candidate PとActual Pの双方観測 | 847 |
| Candidate P=Actual P | 842 |
| Candidate P!=Actual P | 5 |
| actual unobserved | 0 |
| 全4 Node undetermined Visit | 0 |
| Visit ID 1〜8件数 | 600, 600, 162, 12, 6, 6, 1, 1（最大Visit ID 8） |
| 内部Link最大Vehicle数 | 38 |
| `northeast_intersection_to_northwest_intersection` | 最大38台、entrance blocked 370 timestep |
| `northwest_intersection_to_southwest_intersection` | 最大34台、entrance blocked 107 timestep |
| 実行時間 | 約2028秒（約33分48秒） |

### 18.11 Candidate PとActual Pの不一致（Candidate P Actual P mismatch / route mismatch）

**Vehicle単位847件**

| 区分 | 件数 |
|------|------|
| route一致・passage一致 | 840 |
| route一致・passage不一致 | 2 |
| route不一致・passage一致 | 2 |
| route不一致・passage不一致 | 3 |

**取引単位307件**

| 区分 | 取引数 |
|------|--------|
| route mismatchなし・passage mismatchなし | 302 |
| route mismatchなし・passage mismatchあり | 0 |
| route mismatchあり・passage mismatchなし | 2 |
| route mismatchあり・passage mismatchあり | 3 |

passage mismatchを含む3取引: T=600・T=619・T=661、いずれも `northeast_intersection`。3取引すべてで少なくとも1台のpredicted routeとactual routeが異なった。

route mismatchがあってもpassage時刻が一致した取引が2件あるため、**route mismatchはpassage mismatchの十分条件ではない**。今回のtrialでは、passage mismatchがある全3取引にroute mismatchが含まれたが、直接因果は未確定である。

assigned rank順序違反はこの3取引から確認されていない。実Worldはformal routeへ拘束されないため、candidate予測とactual実績が分岐した可能性がある。現時点ではproduction欠陥と断定しない。

### 18.12 §18の最新状態（記録日: 2026-10-22）

- baseline物理通過時進路の **production実装完了**
- 関連 **unit test完了**
- **initial arrived binding Vehicle** へのbinding進路適用（**stale live route** 対策）完了
- 関連 **unit test完了**
- **4交差点600台trial** 全参加・評価T=0〜899で正常完走
- **Candidate P Actual P mismatch** 5 Visit・passage mismatch関連3取引を確認
- 不一致は即座にproduction欠陥とは判断していない
- 全取引・全候補診断は別の **§19** で記録予定
- 横並び形式と同着順位監査も別の **§19** で記録予定
- nonparticipating 4交差点trialは未着手
- Git commit・pushは未実施

## 19. 4交差点600台trialの全取引・全候補診断、横並び表示契約、および同着順位監査（2026-10-22）

本節は、§18で正常完走した **4交差点600台trial** に対し、**all transactions** と **all candidates**（**considered candidates**）を1回のsimulationからread-only収集する診断、**横並び**表示の正式契約、**同着順位**監査用field追加、および **runtime validation** 停止と **validation修正完了** までを記録する。

### 19.1 全取引・全候補診断を必要とした理由

4交差点600台全参加trialは正常完了した。成立取引307件、buyer Visit 361件、seller Visit 486件について、production標準出力には baseline／candidate／actual passage、assigned rank、actual passage rank、formal／predicted／actual route、VOT、payment、compensation、realized value 等が保存されていた。

一方、既存 `tvt_mp_visits.csv` には横並びレビューに必要な次が **保存されていなかった**。

- **baseline arrival**（`baseline_arrival_timestep`）
- **actual arrival**（`actual_arrival_timestep`）
- **baseline_arrival_tiebreaker**
- 同着順位監査用 **vehicle_id**

baseline arrivalは各意思決定時点のbaseline collectorに存在する。actual arrivalは実World実行中に取得できる。simulation終了後の標準CSVだけから到着時刻を通過時刻等で **推測・逆算してはならない**。

そこで、既存 selected transaction fundamentals 診断方式を4交差点600台trialへ移植し、simulation実行中に必要情報をread-only保存する診断を作成した。

### 19.2 新規診断スクリプト

| 項目 | 内容 |
|------|------|
| スクリプト | `research_scripts/diagnose_tvt_mp_four_cross_intersections_all_transactions_and_candidates.py` |
| 目的 | 元trialと同じ600台simulationを **1回だけ** 実行し、通常処理中の正式objectをread-only保存（取引・候補ごとの再実行なし） |
| 制約 | production・元trial・既存診断を変更しない。元trialの `main()` は呼ばない |
| 出力先 | `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_all_transactions_and_candidates_diagnostic` |
| 既存dir | 存在時は上書き・削除・再利用せず停止 |

### 19.3 情報捕捉方法

成立取引および **considered candidates** の情報は、実Worldに対する `run_tvt_mp_driver()` の返却結果から保存する。元関数を一度呼び、その直後に正式driver結果をread-onlyで読む。

保存対象の例: candidate visit set、baseline fork result、baseline collector、right-of-entry selection、concrete buyer candidate、local virtual calculation、general trade rank、economic evaluation、candidate selection、payment and compensation、final rank、predicted traffic observation。

**baseline arrival**: 各意思決定時点のbaseline collector snapshotから取得。

**actual arrival**: `Vehicle.record_order_control_node_arrival()` をread-only wrapper化。key `(node_name, vehicle_name, visit_id)`、値は実Worldで当該Visitが **最初に** 対象Nodeへ到着した `World.T`。`vehicle.W` と `GATE.real_world` のobject identityを確認。baseline fork・candidate局所Worldの到着は記録しない。元関数を先に一度だけ呼んでから観測値を保存。全hookは `try/finally` で復元。

### 19.4 成立取引と全候補の保存範囲

- **established transaction parties**: 全成立取引の取引内全party
- **all candidates**: selected／not selected を問わず、driver結果に正式に存在する全候補（FIFO等で局所計算objectに無い候補は診断側で再構成しない）

候補保存項目の例: buyers／sellers／nonparticipating、candidate評価順、candidate identity、baseline arrival、baseline／candidate passage、baseline／candidate順位、binding補助順位、predicted route、inlink、VOT、経済record、G/R/surplus、feasible／infeasible、**feasible not selected**、unresolved、selection reason。

不成立候補について推測・新規計算しないもの: actual arrival、actual passage、actual rank、actual route、payment、compensation、仮想payment／compensation。未解決候補で candidate passage が `None` のとき、baseline passageで補完しない。

### 19.5 固定出力ファイル（7ファイル）

1. `all_established_transactions_summary.csv`（1成立取引1行）
2. `all_established_transaction_parties.csv`（1party1行、全成立取引）
3. `all_considered_candidates_summary.csv`（1候補1行、selected含む）
4. `all_considered_candidate_parties.csv`（1候補1party1行、不成立含む）
5. `special_established_transaction_parties.csv`（特殊成立取引の全party。元の全party CSVは削除・縮小しない）
6. `diagnostic_summary.txt`
7. `manifest.json`

### 19.6 初回診断の成功結果

- py_compile成功
- `--static-validate-only` 成功
- 600台simulation正常完了
- 新規診断出力先へ固定7ファイルを書き出し

**成立取引**

| 項目 | 値 |
|------|-----|
| established transactions | 307 |
| buyer visits | 361 |
| seller visits | 486 |
| nonparticipating visits | 0 |
| multiple buyer | 48 |
| multiple seller | 152 |
| multiple buyer and seller | 15 |
| multiple buyer or seller | 185 |
| same inlink multiple buyer | 1 |
| same inlink multiple seller | 3 |
| same inlink multiple buyer and seller | 0 |
| route mismatch | 5 |
| passage mismatch | 3 |
| route and passage mismatch | 3 |
| special transactions | 188 |

**全検討候補（considered candidates）**

| 項目 | 値 |
|------|-----|
| considered candidates | 1251 |
| resolved | 1251 |
| unresolved | 0 |
| economically feasible | 649 |
| economically infeasible | 602 |
| selected | 307 |
| not selected | 944 |
| feasible not selected | 342 |
| multiple buyer（候補） | 502 |
| multiple seller（候補） | 489 |
| same inlink multiple buyer（候補） | 34 |
| same inlink multiple seller（候補） | 5 |

infeasibility reasons: `buyer_nonpositive_value` 118、`total_buyer_value_below_required_compensation` 506。

selection reasons: `economically_infeasible` 602、`feasible_not_selected` 342、`selected` 307。

**出力行数**

| ファイル | 行数 |
|----------|------|
| all_established_transactions_summary.csv | 307 |
| all_established_transaction_parties.csv | 847 |
| all_considered_candidates_summary.csv | 1251 |
| all_considered_candidate_parties.csv | 3698 |
| special_established_transaction_parties.csv | 609 |
| special成立取引 unique | 188 |
| special CSVの `tvt_decision_timestep` 欠損 | 0 |

### 19.7 特殊成立取引の抽出条件

`special_established_transaction_parties.csv` は次のいずれかを満たす成立取引の **全party** を含める。

- **multiple buyer**（2 Visit以上）
- **multiple seller**（2 Visit以上）
- **same inlink multiple buyer**
- **same inlink multiple seller**
- 取引内に predicted route mismatch と candidate／actual passage mismatch の **両方**

初回: 複数buyerまたは複数seller 185取引、routeかつpassage mismatch 3取引、重複0、special 188取引。

### 19.8 横並び表示の正式契約

今後の **横並び** は次とする。

- 表見出しに **tvt_decision_timestep**（TVT意思決定時点T）、対象Node、candidate identityを明記
- **1行1Visit**、縦軸に取引当事者全員（権利保有車両含む）、横軸に各Visitの属性と結果
- 当事者の一部だけを抜き出さない
- **表示順は `baseline_local_rank` 昇順**

横軸に含める項目（要旨）: role、VisitKey、inlink、right-of-entry；baseline／actual arrival と tiebreaker・vehicle_id；baseline／candidate／actual passage；baseline_local_rank、post_trade_local_rank、assigned C rank、actual passage rank、binding補助順位；formal／predicted／actual route；VOT、経済条件、payment、compensation、realized、satisfaction。

項目を縦軸・Vehicleを横軸に置く形式は、今回の正式 **横並び** ではない。

### 19.9 baseline順位とtrade scope外Visit（rank欠番）

`baseline_local_rank` は成立取引partyだけで圧縮した順位 **ではない**。`candidate_visits` 全体の保存順における正式順位である。**trade scope外Visit** が含まれ得るため、成立取引partyだけを表示すると **rank欠番** が正常に生じる。

例（candidate visits全体 1=trade scope外、2=seller、3=trade scope外、4=buyer、5=seller）→ 横並びpartyは rank 2・4・5。**2・4・5を1・2・3へ圧縮・再計算してはいけない**。trade scope外Visitを成立取引 **party row** へ追加しない。

`baseline_order_visit_keys` は candidate_visits全体の順序。`transaction["parties"]` は trade-scope当事者のみ。両者を同一視しない（後述 **runtime validation** 修正の要点）。

### 19.10 同着順位監査（baseline_arrival_tiebreaker・vehicle_id）

初回party CSVには `baseline_arrival_timestep` はあったが、`baseline_arrival_tiebreaker` と `vehicle_id` が不足していた。例: T=189で `baseline_arrival_timestep=199` のsellerが2 Visit—到着時刻だけでは正式baseline順位の根拠を説明できない。

追加field:

| field | 正式取得元 |
|-------|------------|
| `baseline_arrival_tiebreaker` | 同意思決定のbaseline collector snapshotの `arrival_tiebreaker` |
| `vehicle_id` | 同snapshotの `vehicle_id`（candidate traffic observationの `vehicle_id` と一致を検査） |

同着順位監査用の組:

`(baseline_arrival_timestep, baseline_arrival_tiebreaker, vehicle_id, baseline_local_rank)`

表示順は引き続き `baseline_local_rank` 昇順。tiebreakerやvehicle_idで診断側が順位を **再計算・再ソートしない**（順位根拠の監査表示用）。

追加対象: `all_established_transaction_parties.csv`、`all_considered_candidate_parties.csv`、`special_established_transaction_parties.csv`。

更新後: py_compile成功、`--static-validate-only` 成功。初回診断出力は履歴としてリネーム:

`..._all_transactions_and_candidates_diagnostic_before_tiebreaker_fields`

### 19.11 更新版診断のruntime validation停止（診断停止・simulation本体正常完了）

tiebreaker／vehicle_id追加後の更新版診断を再実行。**600台simulation本体は正常完了**した。停止したのはsimulation後の診断 **runtime validation**。

```
RuntimeError: T=46 southwest_intersection:
baseline_order visit veh_nw_sw_base_002:2 has no party row.
```

停止箇所: `_validate_established_transaction_baseline_ranks(transaction)`。

原因: validationが次の2集合を誤って同一視した。

- **A** `transaction["baseline_order_visit_keys"]` — candidate_visits全体の保存順（**trade scope外Visit** を含み得る）
- **B** `transaction["parties"]` — 成立取引のtrade-scope当事者のみ（trade scope外を含まない）

誤った要求: partyの `baseline_local_rank` が1から連続；`baseline_order_visit_keys` の全Visitに **party row** が存在すること。

T=46の `veh_nw_sw_base_002:2` は正常な **trade scope外Visit** の可能性が高い。**productionまたはsimulation本体の異常ではない**。

### 19.12 runtime validation修正（validation修正完了）

`_validate_established_transaction_baseline_ranks()` を修正。

**削除した誤契約**

- party rankが `1..len(parties)` で連続
- `baseline_order_visit_keys` の全Visitにparty row必須

**修正後の検査**

1. `baseline_order_visit_keys` がtuple、重複なし
2. party VisitKey重複なし
3. 各party VisitKeyが `baseline_order_visit_keys` に存在
4. party `baseline_local_rank` は正のint（bool拒否）
5. `baseline_order_visit_keys` の1始まり正式位置と保存済みrankが一致
6. partyを `baseline_local_rank` 昇順に並べたときrankが **厳密増加**（連続性は要求しない）
7. trade scope外Visitにparty rowがないことをエラーにしない

`baseline_local_rank` を再計算・圧縮・上書きしない。表示順・tiebreaker／vehicle_id保存契約は維持。候補当事者側に同種の連続性要求は **存在せず変更不要**。

修正後: py_compile成功、`--static-validate-only` 成功。出力ディレクトリは NOT_FOUND（不完全出力なし）。**修正後の更新版600台診断simulation再実行は未開始**（**診断再実行未完了**）。

### 19.13 初回抽出した同一inlink複数buyer・seller取引

**same inlink multiple seller（3取引）**

1. T=189、`northeast_intersection`、candidate index=1、buyer `veh_en_sw_base_032:1`、seller `veh_se_ne_base_024:2` と `veh_se_ne_base_025:2`
2. T=217、同上パターン、buyer `veh_en_sw_base_034:1`、seller `veh_se_ne_base_032:2`・`033:2`
3. T=241、buyer `veh_en_sw_base_036:1`、seller `038:2`・`039:2`・`040:2`

**same inlink multiple buyer（1取引）**

4. T=275、`northwest_intersection`、candidate index=4、buyer `veh_ne_wn_base_008:2` と `veh_ne_ws_base_008:2`（inlink `northeast_intersection_to_northwest_intersection`）

T=189の正式横並びレビューは、tiebreaker／vehicle_idを含む更新版正式出力が未生成のため **未完了**。

### 19.14 §19の最新状態（記録日: 2026-10-22）

**完了**

- 全成立取引・全検討候補を収集する診断スクリプト作成
- 初回 py_compile／static validation／600台診断simulation正常完了／固定7出力生成
- 成立307・全候補1251・special188を保存
- same inlink multiple buyer 1・same inlink multiple seller 3を抽出
- 横並び正式形式確定、`baseline_arrival_tiebreaker`・`vehicle_id` 追加
- 更新後 py_compile／static validation成功、更新版 **simulation本体正常完了**
- baseline rank **validation** 原因確定、trade scope外による **rank欠番** 許容修正、修正後 py_compile／static validation成功
- 不完全出力ディレクトリなしを確認

**未完了**

- 修正後の更新版600台診断simulation **再実行**（正式7ファイル生成）
- T=189・217・241・275、T=600・619・661の正式横並びレビュー
- **feasible not selected** 候補の抽出レビュー
- `ORDER_EXCHANGE_PROGRESS_3.md` への今回進捗反映
- nonparticipating 4交差点trial
- Git commit・push

**次の作業**

1. 修正後の更新版600台診断simulationを1回実行する
2. tiebreaker／vehicle_idを含む正式出力を確認する
3. T=189・217・241・275の横並びレビュー
4. T=600・619・661の横並びレビュー
5. 必要に応じて feasible not selected 候補を抽出する
6. 検証結果を§19と進捗メモへ追記する
7. Git commit・push
8. nonparticipating 4交差点trialへ進む

### 19.15 validation修正後の更新版診断正常完了と同着順位監査

**validation修正後**、次の診断スクリプトを再実行した。

`research_scripts/diagnose_tvt_mp_four_cross_intersections_all_transactions_and_candidates.py`

600台simulation本体は正常完了した。終了後の **runtime validation正常通過** も確認した。**更新版診断正常完了** として、**正式7ファイル** を次の正式出力先へ生成した。

`research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_all_transactions_and_candidates_diagnostic`

今回の正常完了により、次を確認した。

- **trade scope外Visit** による `baseline_local_rank` **rank欠番** を正常に許容できた
- 各partyの保存済み `baseline_local_rank` と `baseline_order_visit_keys` 内の正式位置との一致検査は維持できた
- `baseline_local_rank` を再計算・圧縮・上書きしていない
- simulation本体と diagnostic runtime validation の双方が完了した
- 不完全出力ではなく **正式7ファイル** を生成できた

**固定7ファイル**（すべて存在）

1. `all_established_transactions_summary.csv`
2. `all_established_transaction_parties.csv`
3. `all_considered_candidates_summary.csv`
4. `all_considered_candidate_parties.csv`
5. `special_established_transaction_parties.csv`
6. `diagnostic_summary.txt`
7. `manifest.json`

**party CSVの行数と追加field**

| ファイル | 行数 | `baseline_arrival_tiebreaker` | `vehicle_id` |
|----------|------|-------------------------------|--------------|
| `all_established_transaction_parties.csv` | 847 | あり | あり |
| `all_considered_candidate_parties.csv` | 3698 | あり | あり |
| `special_established_transaction_parties.csv` | 609 | あり | あり |

成立取引party 847行について、`baseline_arrival_tiebreaker` 欠損 **0件**、`vehicle_id` 欠損 **0件**。全成立取引partyで **同着順位** 監査に必要な次の組を確認可能になった。

`(baseline_arrival_timestep, baseline_arrival_tiebreaker, vehicle_id, baseline_local_rank)`

**T=189の同着順位監査**

T=189、`northeast_intersection` の成立取引で、`baseline_arrival_timestep=199` のsellerが2 Visit存在した。

| Visit | baseline_arrival_timestep | baseline_arrival_tiebreaker | vehicle_id | baseline_local_rank |
|-------|---------------------------|-----------------------------|------------|---------------------|
| `veh_wn_en_base_012:2` | 199 | 0.1906589774700369 | 118 | **3** |
| `veh_se_ne_base_025:2` | 199 | 0.6234657220942288 | 245 | **4** |

両Visitはbaseline到着時刻が同じである。`arrival_tiebreaker` が小さい `veh_wn_en_base_012:2` が **baseline_local_rank 3**、`arrival_tiebreaker` が大きい `veh_se_ne_base_025:2` が **baseline_local_rank 4** となっている。したがって、この2 Visitの正式baseline順位は `arrival_tiebreaker` によって説明できる。

今回の2 Visitでは `arrival_tiebreaker` が異なるため、`vehicle_id` による追加tie-breakは使用されていない。`vehicle_id` は `arrival_tiebreaker` まで同一の場合の追加順位根拠を監査できるよう、引き続き横並び表示へ保持する。

診断側で `arrival_tiebreaker` または `vehicle_id` を使って順位を再計算したものではない。productionが保存した `baseline_local_rank` を表示し、その順位根拠をsnapshot値で監査した結果である。

#### 最新状態（§19.15、記録日: 2026-10-22）

**完了**

- validation修正後の更新版600台診断simulation正常完了
- diagnostic runtime validation正常通過
- 正式7ファイル生成
- party CSVへ `baseline_arrival_tiebreaker` と `vehicle_id` を保存
- 成立取引party 847行で両fieldの欠損0
- T=189の同着seller 2 Visitについて順位根拠を確認
- trade scope外Visitによるrank欠番を許容しつつ、正式baseline位置との一致検査を維持

**未完了**

- T=189取引全当事者の正式 **横並びレビュー未完了**
- T=217、241、275の同一inlink取引の正式横並びレビュー
- T=600、619、661の進路・時刻不一致取引の正式横並びレビュー
- feasible not selected候補の抽出レビュー
- `ORDER_EXCHANGE_PROGRESS_3.md` への今回完了結果の反映
- nonparticipating版4交差点trial
- Git commit・push

**次の作業**

1. `ORDER_EXCHANGE_PROGRESS_3.md` へ今回の正常完了結果を反映する
2. T=189から正式横並びレビューを再開する
3. T=217、241、275を確認する
4. T=600、619、661を確認する
5. 必要に応じて feasible not selected 候補を抽出する
6. レビュー結果を§19と進捗メモへ追記する
7. Git commit・push
8. nonparticipating版4交差点trialへ進む

### 19.16 Candidate／Actual通過時刻差の規模、T=600差異の原因、および局所予測誤差として維持する設計判断

**記録日: 2026-10-24。** 本小節は、4交差点600台全参加trialにおける **Candidate passage Actual passage 不一致** の全体集計、**T=600** 成立取引の原因確定、関連診断の整理、**baseline passageとCandidate passageの混同訂正**、および **現行方式維持**（**production変更なし**）の設計判断を、§19.1〜§19.15を当時の記録として残したうえでの **最新状態** として記録する。

#### 19.16.1 Candidate passageとActual passageの全体集計（847 Visit）

比較対象は、**Candidate passage** と **Actual passage** の双方を観測できた成立取引partyである。件数は **847 Visit**（§19.15の成立取引party行数と一致）。

| 区分 | 件数 | 比率 |
|------|------|------|
| 一致 | **842一致** | 約99.41% |
| **5不一致** | 5 Visit | 約0.59% |

5 Visitは **3成立取引** に属する。成立取引307件に対する該当取引率は約0.98%である。

**差の定義（Actual minus Candidate）**

```
actual_minus_candidate_passage_timesteps
    = actual_passage_timestep - candidate_passage_timestep
```

符号の意味:

- **正**: Actualの方がCandidate予測より遅い
- **負**: Actualの方がCandidate予測より早い
- **0**: 一致

今回の不一致分布（**Candidate passage Actual passage 不一致** 5件のみ）:

| actual_minus_candidate | 件数 |
|------------------------|------|
| **+1 timestep** | **4件** |
| **+4 timestep** | **1件** |
| 負方向 | 0 Visit |
| 最大絶対差 | 4 timestep |

今回観測された不一致は、すべてActualがCandidateより遅い方向であった。ただし、次の理由から **一般的な一方向バイアスとは断定しない**。

- 不一致は **5不一致** のみである
- **selected** された成立取引partyだけの集計である
- Candidateが遅めに予測した候補は、経済評価と候補選択を経て成立取引へ現れにくい可能性がある（選択バイアス）
- 現行 **局所仮想計算の誤差** は、進路別 **entry space**、容量、**clearance**、**車列伝播** によって、早める方向にも遅める方向にも作用し得る

**不一致5 Visitの一覧**

1. **T=600**、`northeast_intersection` — `veh_wn_en_base_042:2`（seller）— Candidate 608 / Actual 609 / Actual−Candidate **+1** — predicted routeとactual routeは一致 — **unsatisfied**
2. **T=600**、`northeast_intersection` — `veh_ne_wn_base_034:1`（buyer）— Candidate 606 / Actual 607 / **+1** — predicted: `northeast_intersection_to_southeast_intersection` / actual: `northeast_intersection_to_northwest_intersection` — **satisfied**
3. **T=619**、`northeast_intersection` — `veh_ne_wn_base_039:1`（seller）— Candidate 625 / Actual 629 / **+4** — predicted: northwest / actual: southeast — **unsatisfied**
4. **T=661**、`northeast_intersection` — `veh_ne_wn_base_042:3`（seller）— Candidate 670 / Actual 671 / **+1** — predicted routeとactual routeは一致 — **unsatisfied**
5. **T=661**、`northeast_intersection` — `veh_ne_ws_base_047:1`（buyer）— Candidate 668 / Actual 669 / **+1** — predicted: southeast / actual: northwest — **satisfied**

**T=619横並び確認済み（既存記録との関係）:** 本ファイル §18.11 に、passage mismatchを含む3取引（T=600・T=619・T=661）の言及がある。**T=619横並び確認済み** は、別作業記録上 **正式横並びレビュー既実施** とする。§19.1〜§19.15内にT=619専用の横並び全文は見当たらないため、次を明記する。**T=619の正式横並びレビューは既実施との作業記録がある。詳細参照先の整理は未完了であり、未確認へ戻すものではない。** T=600事例の機構（**進路先取り**、**binding進路**）をT=619・661の原因へ **自動的に一般化しない**。

**T=661確認状況:** §19.1〜§19.15および §18.11 ではT=661はpassage mismatch関連3取引の一つとして言及されるのみで、**T=661** 専用の正式横並びレビュー記録は本巻内で **見つからなかった**。したがって **T=661の横並び詳細確認は未完了** として残す（必要ならT=661だけを再確認する）。

#### 19.16.2 T=600成立取引の横並び確認

| 項目 | 内容 |
|------|------|
| 意思決定T | **T=600** |
| Node | `northeast_intersection` |
| candidate identity | `T=600\|northeast_intersection\|index=1\|veh_ne_wn_base_034:1` |

**buyer `veh_ne_wn_base_034:1`**

| 項目 | baseline | Candidate | Actual |
|------|----------|-----------|--------|
| passage | 609 | **Candidate passage T=606** | **Actual passage T=607** |
| 短縮（baseline比） | — | 3 timestep | 2 timestep |
| route | — | predicted: southeast | actual: northwest |
| rank | assigned 208 / actual passage 208 | — | **satisfied** |

**seller `veh_wn_en_base_042:2`**

| 項目 | baseline | Candidate | Actual |
|------|----------|-----------|--------|
| passage | 607 | 608 | 609 |
| 遅延（baseline比） | — | 1 timestep | 2 timestep |
| route | predicted＝actual: `northeast_intersection_to_east_north_od` | — | — |
| rank | assigned 209 / actual passage 209 | — | **unsatisfied**（1 timestep分の補償のみ、実現遅延2 timestep） |

buyerとsellerのC順位・A順位の相対順は一致している。したがって順位制御の逆転失敗ではなく、**Candidate予測誤差** としての **Candidate passage** と **Actual passage** の時刻差である。

#### 19.16.3 T=600実World時系列診断

| 項目 | 内容 |
|------|------|
| スクリプト | `research_scripts/diagnose_tvt_mp_four_cross_intersections_t600_route_divergence_trace.py` |
| 正式出力先 | `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_all_participating_600_vehicle_eval_900_timestep_seed_1_t600_route_divergence_trace` |

実WorldのT=598〜610について、対象buyer・sellerと対象Nodeの物理通過状態をread-onlyで記録した。

**buyer `veh_ne_wn_base_034:1`**

- T=606のNode通過走査時点では対象Nodeへ未到着。`inlink.vehicles`には存在、inlink物理先頭、`in_target_incoming_before_attempt=False`
- current link: `north_east_od_to_northeast_intersection`、position x: 196.66666666666666
- live routeは未生成。**clearance**、容量、**entry space** の通過判定へはまだ進んでいない
- T=606中に対象Nodeへ到着、**T=607** に通過

**seller `veh_wn_en_base_042:2`**

- T=608に **clearance** 未充足、T=609に通過

実World内では、buyerのT=607通過後にclearance履歴が更新され、sellerがT=608にclearance未充足となった。ただし、この実World診断だけでは、CandidateでbuyerがT=606に通過しActualではT=607になった **根本原因** までは説明できなかった。

診断作成中の停止要因は **production異常ではなく診断wrapper**（`route_next_link` 未生成時の直接参照、wrapper signature不一致、hook対象Worldの限定不足）であった。修正後、simulationとruntime validationは正常完了した。

#### 19.16.4 Candidate／Actual paired trace（common origin・after_timestep）

| 項目 | 内容 |
|------|------|
| スクリプト | `research_scripts/diagnose_tvt_mp_four_cross_intersections_t600_candidate_actual_paired_trace.py` |
| 正式出力先 | `research_outputs/trial/..._t600_candidate_actual_paired_trace` |
| 旧出力（比較phase修正前） | `..._t600_candidate_actual_paired_trace_before_common_origin_phase_fix` |

旧出力のT=600 **before_node_passage** 差を正式なfirst divergenceとして **使用してはいけない**（**before_node_passage比較無効**）。Candidate側は実Worldコピー後の局所計算内処理、Actual側は全Link更新・全Node更新・先行 `northwest_intersection` のtransfer完了後であり、同じWorld.Tでも同じ処理時点ではなかった。

**修正後の正式比較phase**

1. **common origin** — Candidate: `real_world.copy()` 直後・**binding進路**適用前。Actual: T=600 driver入口・original driver呼出前。
2. **after_timestep** — Candidate: virtual timestepのadvanceとoutlink boundary完了後。Actual: real timestep全体完了後、次timestep driver入口で直前状態として保存。

**common origin** 確認: Vehicle 67、Node 1、Link 8、unexpected common origin difference **0件**。CandidateとActualのコピー開始状態は一致。

Candidate局所計算と実Worldでは、開始後の対象inlink上流端への新規流入などが異なり得る。これは **局所仮想計算** の設計上正常な差である。ただし、設計上正常であることと、後続の車列・容量・到着・通過時刻へ因果的に寄与し得ることは別である。設計上正常な差を、正常であるだけを理由に **Candidate予測誤差** の原因候補から機械的に除外してはならない。

#### 19.16.5 baseline passageとCandidate passageの混同訂正（`veh_ne_wn_base_032:1`）

先行Visit **`veh_ne_wn_base_032:1`** について、当初Candidate局所計算での通過T=601を **baseline passage T=601** と誤認した。これは誤りである（**baseline passageとCandidate passageの混同訂正**）。

T=600 baseline collectorの正式snapshot（短時間mode出力 `t600_baseline_target_snapshot.json` を正本）:

| field | 値 |
|-------|-----|
| vehicle_name | `veh_ne_wn_base_032` |
| visit_id | 1 |
| visit_key | `veh_ne_wn_base_032:1` |
| baseline_arrival_timestep | 595 |
| arrival_tiebreaker | 0.4269186398497614 |
| **baseline到着時進路** `route_next_link_name` | `northeast_intersection_to_northwest_intersection` |
| **baseline passage T=602** `baseline_passage_timestep` | 602 |
| **baseline物理通過時進路** `baseline_passage_route_next_link_name` | `northeast_intersection_to_southeast_intersection` |

正しい整理:

- baseline仮想Worldの到着時進路は **northwest**（**baseline到着時進路**）
- baseline仮想WorldはT=601の **route choice** でsoutheastへ変更
- baseline仮想WorldはT=602にsoutheast方向へ物理通過（**baseline物理通過時進路**）
- Candidate局所計算はbaseline物理通過時進路southeastを **binding進路** として引き継ぐ
- Candidate局所計算では **Candidate passage T=601** にsoutheast方向へ物理通過
- 実WorldはT=601までにsoutheastへ進路変更し、T=602にsoutheast方向へ物理通過

**baseline passage T=602** とActual passage T=602は、この先行Visitについて一致している。Candidate局所計算だけがT=601に1 timestep早く通過した。`veh_ne_wn_base_032:1` のbaseline passageとActual passageを不一致とみなす中間解釈は **訂正済み** とする。

#### 19.16.6 baseline route choice正式確認

| 項目 | 内容 |
|------|------|
| スクリプト | `research_scripts/diagnose_tvt_mp_four_cross_intersections_t600_baseline_actual_route_choice_trace.py` |
| 短時間mode | `--stop-after-t600-baseline` |
| 短時間mode出力先 | `research_outputs/trial/..._t600_baseline_route_choice_early_stop` |

baseline内の対象Visit **route choice**（`veh_ne_wn_base_032:1`）:

| world.T | route_next_link_before | route_next_link_after | route_changed |
|---------|------------------------|----------------------|---------------|
| 600 | northwest | northwest | False |
| 601 | northwest | southeast | True |

条件: specified routeなし、homogeneous_DUO、`hard_deterministic_mode=False`、`links_prefer`／`links_avoid`なし、4 outlinkのroute preferenceは空または0相当、normalized probability各0.25、uniform RNG selection。`W.rng`は各route choice呼出しで変化、`order_control_rng`は変化していない。

完全実行modeには baseline passage T=601 という誤った固定期待値が残っている（診断validationのみ、**production影響なし**）。短時間modeでは固定期待値を使わず正式snapshot取得まで **完了**。

#### 19.16.7 T=600 Candidate **進路先取り**誤差（**future route information**）

T=600 Candidate局所計算では、拘束Visitについて **baseline物理通過時進路** を局所計算開始時から **binding進路** として適用する。

先行Visit `veh_ne_wn_base_032:1`:

- baseline開始時／到着時進路: northwest
- baseline物理通過時進路: southeast（T=601 **route choice** で変更、T=602物理通過）

Candidate局所計算はsoutheastを開始時からbindingし、T=601に **entry space** が利用可能な状態で物理通過する。

baseline／Actualでは、T=601のNode通過走査時点ではnorthwest方向。northwest方向の **entry space** 不足（`veh_ne_ws_base_031` が入口、`entry_open=False`）によりT=601には通過できず、T=601中にsoutheastへ進路変更、T=602に通過する。

Candidate局所計算では、baselineで将来の物理通過時に使用する進路を開始時から固定したことで **進路変更を1 timestep先取り** した。この先行Visitの1 timestep差が **車列伝播** し、後続のCandidate／Actual passage差へ波及した。

| Visit | Candidate passage | Actual passage |
|-------|-------------------|----------------|
| `veh_ne_wn_base_032:1` | 601 | 602 |
| `veh_ne_ws_base_032:1` | 602 | 603 |
| `veh_ne_wn_base_033:1` | 603 | 604 |
| `veh_ne_ws_base_033:1` | 604 | 605 |
| buyer `veh_ne_wn_base_034:1` | 606 | 607 |
| seller `veh_wn_en_base_042:2` | 608 | 609 |

buyerのT=607通過後、sellerはT=608にclearance未充足、T=609に通過。このT=600事例では、**baseline物理通過時進路** の開始時適用がCandidate passageを **早める方向**へ作用した。

Actual側の入口空間不足だけをCandidate／Actual差の **唯一の根本原因** とみなす中間解釈は **使用してはいけない**（先取り誤差と車列伝播の方が本事例の確定原因である）。

#### 19.16.8 誤差の方向性（局所仮想計算の近似）

**binding進路**／**future route information** の近似は、コード構造上一方向にだけ作用するとは限らない。

- **早める方向**: baseline物理通過時進路の入口が早い時点でも開いている一方、到着時またはlive進路側は塞がっている → **進路先取り**
- **遅める方向**: live進路側は早く開いている一方、baseline物理通過時進路側は早い時点では塞がっている → 将来進路へ最初から拘束され待たされる

対象Visit自身の差は後続Vehicle・**clearance**・容量へ波及するため、取引全体への符号は単純ではない。今回の成立取引partyではActualが遅い方向だけが5件観測されたが、§19.16.1と同様、一般的な一方向バイアスとは断定しない。

#### 19.16.9 確定した設計判断（**現行方式維持**・**production変更なし**）

局所仮想計算を完全に正確にすることはできず、TVT-MP研究で構築した予測機構には複数の **Candidate予測誤差**（**局所仮想計算の誤差**）が不可避に含まれる。**baseline物理通過時進路** をCandidate局所計算開始時から **binding進路** として適用することで生じる **進路先取り** または進路固定誤差は、そのうちの一つと位置付ける。

この誤差を除去するには、baseline内の進路変更時刻・変更前後の全履歴・Node通過走査との前後関係・Candidate側での時刻同期再生・複数回進路変更の再生などが必要になる。しかし **進路変更履歴再生は実装しない** という現時点の方針である。追加すると実装・保存・計算負荷が増え、baselineとCandidateの交通状態が異なる中でbaseline時刻どおりに進路変更を再生するという **別種の人工的仮定** が入り、別の近似誤差を生む。

**採用する確定方針**

- **productionを変更しない**
- Candidate局所仮想計算の **現行方式維持**
- baseline物理通過時進路を開始時からbinding進路として適用する契約を維持
- baseline進路変更履歴の再生機構は追加しない
- 本現象を局所仮想計算の予測誤差要因として扱い、発生頻度・符号・差の大きさ・**車列伝播**・取引feasibility・支払・補償・満足度への影響を研究結果として分析・提示する

これは「誤差が存在しない」または「誤差が必ず小さい」とみなす判断ではない。完全再現のために実装を複雑化するより、現行機構の誤差を定量化して研究結果として示す方が現実的である、という判断である。

#### 19.16.10 診断中の訂正事項（中間解釈の禁止）

最終結論として **使用してはいけない** 誤った中間解釈:

- Candidate T=601通過をbaseline passage T=601とみなす
- `veh_ne_wn_base_032:1` のbaseline passageとActual passageを不一致とみなす
- Actual側の入口空間不足だけをCandidate／Actual差の根本原因とみなす
- T=600中に実Worldだけで対象inlink上流端へ流入したVehicleを「交差点通過Vehicle」と表現する
- 局所仮想計算の上流流入差を、設計上正常であることだけを理由に因果候補から除外する
- phaseの異なるT=600 before_node_passage差を正式first divergenceとみなす

正しい整理は §19.16.5〜§19.16.7 に記載。**正式比較は common origin と after_timestep で行う。**

#### 19.16.11 完了事項（本小節まで）

- T=189、217、241、275の同一inlink複数当事者取引の横並びレビュー
- T=275で `northwest_intersection` のA順位が1〜440で連続し、最終順位440が実通過Visit数440と一致することを確認
- **T=600** 取引の横並びレビュー
- T=600実World時系列診断
- T=600 Candidate／Actual paired trace、**common origin** 比較phaseの修正、Vehicle 67・Node 1・Link 8の一致確認
- T=600 baseline collector正式snapshot取得、**baseline到着時進路**と**baseline物理通過時進路**の分離確認
- Candidate局所計算の1 timestep **進路先取り**原因の確定
- **Candidate passage Actual passage 不一致** の全体集計（**847 Visit**、**842一致**、**5不一致**）
- **現行方式維持**の設計判断

T=619: §19.16.1のとおり、未確認へ戻さない。**T=661確認状況**: 横並び詳細は未完了（§19.16.1）。

#### 19.16.12 未完了事項

- baseline／Actual route choice診断の完全実行modeに残る誤った固定期待値601の整理（production影響なし。短時間modeによる正式snapshot取得は完了）
- **feasible not selected未完了** — 候補の抽出レビュー
- Candidate／Actual passage差5件について必要な範囲で分析結果を整理
- 今回追加した診断スクリプトのGit対象判断
- Git commit・push
- **nonparticipating車両20%を含む4交差点ネットワークtrial** の設計・実行・診断（次の主作業）

**T=661成立取引（未完了作業には含めない — 意図的に追加横並び検証しない判断）**

- T=661成立取引の **追加横並び検証は行わない**（検証済みとは記録しない。「検証しない」判断と「検証済み」を混同しない）
- T=661ではCandidate passageとActual passageが1 timestep異なるbuyer・sellerが確認されている
- T=661専用の正式横並びレビューを **実施済みとは扱わない**。T=661の差異原因は **未確定**（T=600の **進路先取り** 誤差をT=661へ自動一般化しない）
- 全体では **847 Visit** 中 **842一致**・**5不一致**であり、**T=600** では誤差機構を具体的に確認済み。全参加4交差点trialの検証は現時点で区切る
- 追加の個別原因分析より、**nonparticipating車両20%** を含む4交差点trialへ進むことを優先する
- 将来、研究結果の解釈上必要になった場合に限りT=661へ戻る

（production修正および進路変更履歴再生の実装は、本小節の **確定方針により実装しない** ため、未完了事項には含めない。）

#### 19.16.13 最新再開地点（作業順）

1. `ORDER_EXCHANGE_PROGRESS_3.md` へ、T=661追加検証を行わずnonparticipating車両20%の4交差点trialへ進む判断を別作業として反映する
2. 進捗メモの追記をTerminalで独立確認する
3. baseline／Actual route choice診断の完全実行modeに残る誤った固定期待値601を整理する
4. 今回追加した診断スクリプトのGit対象を整理する
5. 必要な文書・診断修正を完了してGit commit・pushする
6. nonparticipating車両20%を含む4交差点ネットワークtrialの既存仕様・スクリプト・出力要件を確認する
7. 既存のproductionと全参加trialを変更せず、nonparticipating 20% trialの実行準備へ進む
8. trial実行後、nonparticipatingを含む候補形成、取引成立、順位、予測対実績、外部効果を診断する
9. feasible not selected候補の抽出レビューとCandidate／Actual passage差5件の追加分析は、nonparticipating trialの検証優先度と合わせて再配置する

## 23. 4交差点nonparticipating 20％ trial・T=382取引の初回到着訂正、物理一致、通過差、および順位確定源確認完了（2026-10-26）

本節は、4つの十字路交差点を含む medium grid network の **nonparticipating 20% trial**（Vehicle 総数 600 台、participating 480 台、nonparticipating 120 台、nonparticipation seed 3）において、**T=382** の **northwest_intersection** で成立した **1 取引の 4 party** を対象に実施した一連の read-only 反証確認の **最新技術正本** である。production、既存 trial、全参加 trial は変更していない。診断スクリプトの追加と read-only hook による確認のみである。旧診断が報告していた Actual arrival 差は交通現象ではなく診断記録上の誤りであったこと、T=382 取引 4 party の Baseline 初回到着と Actual 初回到着の全件一致、nonparticipating Visit の Candidate／Actual passage 差 1 timestep の原因、後続 decision における新規 C 順位の正式確定源までを本節で確定する。

**検索語（本節）:** T=382、northwest_intersection、4交差点、nonparticipating 20％、初回Actual arrival、Actual arrival上書き、再登録、record_order_control_node_arrival、arrival_time、Baseline arrival、Candidate passage、Actual passage、first divergence、物理一致、T=402、一時skip、entry space、clearance、C順位183、Actual通過順位177、selected=False、Baseline fallback、leading nonparticipating、順位確定源、旧診断訂正、完了、再開地点。

### 23.1 対象 trial と対象取引

- **trial script:** `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_trial.py`
- **scenario:** `tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900`
- **既存 trial 出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_initial`
- **対象 decision:** T=382
- **対象 Node:** `northwest_intersection`

**対象 4 party:**

| # | Visit | role | formal inlink | assigned C rank |
|---:|---|---|---|---:|
| 1 | `veh_sw_nw_base_037:2` | seller | `southwest_intersection_to_northwest_intersection` | 175 |
| 2 | `veh_nw_sw_base_047:1` | seller | `north_west_od_to_northwest_intersection` | 177 |
| 3 | `veh_wn_se_base_024:1` | nonparticipating | `west_north_od_to_northwest_intersection` | 176 |
| 4 | `veh_en_sw_base_025:2` | buyer | `northeast_intersection_to_northwest_intersection` | 174 |

**T=382 selected Candidate:**

- selected=True
- selected_candidate_evaluation_index=2
- buyer=`veh_en_sw_base_025:2`

**T=382 で新規確定した Node 連続 C 順位:**

- `veh_en_sw_base_025:2` = C174
- `veh_sw_nw_base_037:2` = C175
- `veh_wn_se_base_024:1` = C176
- `veh_nw_sw_base_047:1` = C177

### 23.2 旧 Actual arrival 値の誤り

**旧診断:** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py`

旧診断が Actual arrival として表示していた値（**正式な初回 Actual arrival ではない**）:

| Visit | 旧診断の Actual arrival 列 |
|---|---:|
| `veh_sw_nw_base_037:2` | T=395 |
| `veh_nw_sw_base_047:1` | T=407 |
| `veh_wn_se_base_024:1` | T=403 |
| `veh_en_sw_base_025:2` | T=397 |

**原因:** production の `Vehicle.record_order_control_node_arrival()` は、同一 Visit について `current_visit["arrival_time"]` が `None` のときだけ初回到着時刻を設定する。以降の再呼出しでは production の `arrival_time` は初回値を維持する。旧 `rank_and_passage_trace` の wrapper は production 呼出し後に `GATE.actual_arrivals[(vehicle.name, visit_id)] = vehicle.W.T` と **無条件上書き** していたため、初回到着ではなく **最後に** `record_order_control_node_arrival()` が再呼出しされた timestep が旧診断の Actual arrival 列に残った。これは production の到着記録欠陥ではなく、**旧診断の観測・保存方法の欠陥** である。

旧診断スクリプトと旧出力は削除しない。上記 4 値を正式な Actual arrival として今後使用してはならない。

### 23.3 正式な初回 Actual arrival

新診断では、production 呼出し後の `current_visit["arrival_time"]` を読み、Node 名・Vehicle 名・Visit ID を key として **初回値だけ** を保存した。同一 Visit の後続再呼出しでは初回値を上書きせず、production の `arrival_time` が初回値を維持していることを検証した。

| Visit | Baseline arrival | 正式な初回 Actual arrival | Actual−Baseline |
|---|---:|---:|---:|
| `veh_sw_nw_base_037:2` | 388 | 388 | 0 |
| `veh_nw_sw_base_047:1` | 390 | 390 | 0 |
| `veh_wn_se_base_024:1` | 392 | 392 | 0 |
| `veh_en_sw_base_025:2` | 394 | 394 | 0 |

**到着メソッド呼出し監査:**

| Visit | 呼出し回数 | 初回記録 T | 後続再呼出し T |
|---|---:|---:|---|
| `veh_sw_nw_base_037:2` | 8 | 388 | 389〜395 |
| `veh_nw_sw_base_047:1` | 18 | 390 | 391〜407 |
| `veh_wn_se_base_024:1` | 12 | 392 | 393〜403 |
| `veh_en_sw_base_025:2` | 4 | 394 | 395〜397 |

全後続再呼出しで production `arrival_time` は初回値を維持した。旧診断で到着差とされた 7、17、11、3 timestep は **交通予測誤差ではない**。4 party すべてについて、T=382 baseline fork の Baseline arrival と Actual 実 World の正式な初回 arrival は一致した。

### 23.4 Baseline と Actual の物理状態比較

**比較した系列:**

1. T=382 baseline fork
2. Actual 実 World
3. Actual T=382〜407 の `northwest_intersection` で selected された Candidate の正式結果

**追跡 phase:** `common_origin`、`before_link_update`、`after_link_update`、`before_node_transfer`、`after_node_transfer`、`after_vehicle_update`、`after_timestep`

**対象 4 Vehicle の主な field:** `current_link_name`、`physical_index`、`leader_vehicle_name`、`follower_vehicle_name`、`position_x`、`speed_v`、`move_remain`、`x_next`、`in_incoming`、`route_next_link_name`

**対象 4 inlink の主な項目:** Vehicle 数、Vehicle 順、position 順、speed 順、cum departure、capacity out

**結果:**

- `t382_baseline_actual_first_differences.csv` はデータ行 0 件
- `t382_baseline_actual_front_vehicles.csv` はデータ行 0 件
- 対象 4 Vehicle について first divergence なし
- 対象 4 inlink についても比較可能範囲で差なし

**first divergence の定義:** 同一 timestep・同一 phase の Baseline と Actual について、対象 Vehicle または対象 inlink の物理状態が **最初に** 異なった時点と field。今回は first divergence は存在しなかった。

**結論:** T=382 から各対象 Visit の正式な初回 Node 到着まで、対象 Vehicle の inlink 上の物理進展について Baseline fork と Actual 実 World の差は確認されなかった。

### 23.5 T=392 後続 selected decision の位置付け

T=392 に `northwest_intersection` で別の selected Candidate が成立した。

- selected=True
- selected_candidate_evaluation_index=5
- buyers: `veh_wn_en_base_025:1`、`veh_nw_sw_base_048:1`、`veh_wn_se_base_025:1`

**T=392 で新規確定した C 順位:**

- `veh_wn_en_base_025:1` = C179
- `veh_nw_sw_base_048:1` = C180
- `veh_wn_se_base_025:1` = C181
- `veh_en_sw_base_026:2` = C182
- `veh_sw_nw_base_039:2` = C183
- `veh_sw_nw_base_040:2` = C184

処理順上、T=392 driver は T=392 の Link・Node・Vehicle 更新より **前** に実行される。対象 nonparticipating Visit `veh_wn_se_base_024:1` は、その後の T=392 内の走行処理で正式到着した。したがって **T=392 の後続 decision は、同 Visit の T=392 初回到着時刻を変えた原因ではない**。一方、T=392 decision で確定した C182〜C184 等は、その後の Node 通過走査へ影響し得る。この区別を維持する。

### 23.6 T=402〜404 の nonparticipating 通過差

**対象 nonparticipating Visit:** `veh_wn_se_base_024:1`（assigned C rank=176）

**正式時刻:**

- Baseline arrival=T=392
- Actual first arrival=T=392
- Baseline passage=T=404
- Candidate passage=T=403
- Actual passage=T=404

Candidate T=403 対 Actual T=404 の 1 timestep 差は、**到着予測差ではない**。

**T=402 の正式な C 順位走査:**

- **C176**（対象 nonparticipating Visit）: 到着済み、clearance 充足、outlink 入口空間不足、一時 skip
- **C177**: outlink 入口空間不足、一時 skip
- **C178**: T=400 に通過済み
- **C179〜C181**: T=402 時点の incoming snapshot に不在（未到着、物理通過走査対象外）
- **C182**: outlink 入口空間不足、一時 skip
- **C183** `veh_sw_nw_base_039:2`: 別 inlink から通過可能、T=402 に通過

**T=403:** 対象 nonparticipating Visit の entry space は利用可能だが clearance 未充足。TVT-MP 拘束順位列走査契約により、その時刻の対象 Node 通過処理を終了。対象 Visit は通過しない。

**T=404:** clearance 充足。対象 Visit が Actual 通過順位 178 で通過。

**結論:** Candidate／Actual passage 差 1 timestep は、到着誤差ではなく、T=402 の入口空間不足による一時 skip、別 inlink の C183 Visit 通過、その後の T=403 clearance 未充足によって発生した。

### 23.7 C 順位と Actual 通過順位の区別

**`veh_sw_nw_base_039:2`:**

- T=392 で新規確定
- assigned Node 連続 C 順位=**183**
- Actual Node 連続通過順位=**177**
- Actual passage=T=402

C 順位 183 と Actual 通過順位 177 は **異なる概念** である。C 順位は rank ledger 上で確認された拘束順位。Actual 通過順位は実 World で対象 Node を物理通過した順序。診断の `wrapped_move()` が通過時に保存した `assigned_rank` は Actual 通過順位ではなく、通過時点の rank ledger 上の C 順位である。`KNOWN_LATER_CONFIRMATIONS` では `veh_sw_nw_base_039:2` の `assigned_rank` を 177 ではなく **183** とする。

**`veh_wn_en_base_025:1`:**

- T=392 で新規確定
- assigned C 順位=179
- Actual passage=T=406

この Visit では C 順位と Actual 通過順位が偶然ともに 179 だが、**概念は同一ではない**。

### 23.8 selected=False の新規 C 順位確定源

T=382〜407 の `northwest_intersection` decision は **26 件**。selected Candidate が成立したのは T=382 と T=392 のみ。それ以外は selected=False。ただし **selected=False は「順位を何も確定しない」という意味ではない**。selected=False は、取引による順位変更案が採用されなかったことを意味する。

正式な診断により、次の 3 件の確定源を確認した。

| decision | Visit | 参加属性 | selected | assigned C | confirmation source | final_rank_status | finalization_source |
|---:|---|---|---|---:|---|---|---|
| T=390 | `veh_sw_nw_base_038:2` | participating | False | 178 | `baseline_fallback_final_rank` | `baseline_fallback_ranks` | `baseline` |
| T=404 | `veh_sw_nw_base_041:2` | participating | False | 185 | `baseline_fallback_final_rank` | `baseline_fallback_ranks` | `baseline` |
| T=406 | `veh_nw_sw_base_049:1` | nonparticipating | False | 186 | `leading_nonparticipating_confirmation` | （leading 列） | （leading 列） |

1〜2 は非技術的には、取引案は採用されなかったが Baseline 予測順で順位を確定した。3 は意思決定窓の先頭 nonparticipating Visit として先行確定された。T=390、T=404、T=406 のいずれも production の正式な順位確定経路と整合した。**既確定 Visit へ新しい C 順位を再付与した事例ではない**。

### 23.9 診断スクリプトと正式出力

**1.** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_baseline_actual_inlink_arrival_divergence.py`

- 主目的: T=382 baseline fork と Actual 実 World の物理比較、Actual 初回 arrival 記録、arrival 再登録監査、T=382〜407 selected Candidate 記録、driver 前後 rank ledger 差、first divergence、前方 Vehicle、新規 C 順位

**正式出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_t382_baseline_actual_inlink_arrival_divergence`

**出力ファイル:** `t382_actual_arrival_registration_calls.csv`、`t382_baseline_actual_arrival_divergence_summary.txt`、`t382_baseline_actual_first_differences.csv`、`t382_baseline_actual_front_vehicles.csv`、`t382_baseline_actual_target_inlink_snapshots.csv`、`t382_baseline_actual_target_inlink_vehicle_snapshots.csv`、`t382_baseline_actual_target_vehicle_snapshots.csv`、`t382_to_t407_newly_confirmed_ranks.csv`、`t382_to_t407_selected_candidate_parties.csv`、`t382_to_t407_selected_decisions.csv`、`manifest.json`

**主要行数:** arrival registration calls=42、first differences=0、front vehicles=0、target inlink snapshots=944、target inlink Vehicle snapshots=25,840、target Vehicle snapshots=944、newly confirmed ranks=13、selected Candidate parties=24、selected decisions=26

**2.** `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_rank_confirmation_sources.py`

- 主目的: selected=False で新規 C 順位を得た 3 Visit について、正式 upstream result object から確定源を判定

**正式出力 directory:** `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_rank_confirmation_sources`

**出力:** `rank_confirmation_sources.csv`、`rank_confirmation_sources_summary.txt`、`manifest.json`

T=406 driver 完了後、対象 3 Visit を全件記録して早期終了した。

### 23.10 診断実装中に発見・修正した事項

production の問題と診断実装の問題を混同しない。今回、診断側で発見・修正した事項:

- selected party 全件保存の間接呼出しを static validation が認識しなかった
- `current_visit.get("arrival_time")` を Subscript 形式だけの static validation が認識しなかった
- `GATE.actual_arrivals` 等の `ast.Attribute` を `ast.Name` だけで検査していた
- dynamic arrival 情報 `GATE.party_arrival_by_vehicle` を `ast.Name` だけで検査していた
- C 順位 183 と Actual 通過順位 177 を混同した期待値
- `World.VEHICLES` 辞書を直接反復して Vehicle object と誤認した
- built-in `getattr` を `ast.Attribute` として検査した static validation 誤判定
- `wrapped_driver` 内の original driver 呼出しをコード上 1 か所へ統合

上記は新規診断または static validation の問題であり、production の交通処理異常ではない。

### 23.11 production 評価

今回の確認範囲で、production について次を確認した。

- Visit 単位の初回 `arrival_time` を正しく保存する
- 同一 Visit の再登録呼出しで `arrival_time` を変更しない
- T=382 baseline fork の arrival 予測が対象 4 Visit すべてで Actual 初回 arrival と一致
- selected Candidate による C 順位確定
- selected=False 時の Baseline fallback 順位確定
- leading nonparticipating 先行確定
- 既確定 C 順位を後続 decision で上書きしない
- 通常物理制約で一時 skip し、後続 Visit を試す
- clearance 未充足時にその timestep の Node 走査を終了する
- C 順位と Actual 通過順位を別管理する

今回の範囲では、production 変更が必要な欠陥は確認されなかった。

### 23.12 今回維持される取引評価

| Visit | role | Baseline passage | Candidate passage | Actual passage |
|---|---|---:|---:|---:|
| `veh_en_sw_base_025:2` | buyer | 408 | 398 | 398 |
| `veh_sw_nw_base_037:2` | seller | 396 | 396 | 396 |
| `veh_wn_se_base_024:1` | nonparticipating | 404 | 403 | 404 |
| `veh_nw_sw_base_047:1` | seller | 398 | 408 | 408 |

**解釈:** buyer は予測どおり 10 timestep 短縮。seller `veh_sw_nw_base_037:2` は遅延なし。seller `veh_nw_sw_base_047:1` は予測どおり 10 timestep 遅延。buyer と seller の Candidate passage は Actual passage と一致。buyer と seller は全員 satisfied。nonparticipating だけ Candidate T=403 に対して Actual T=404。nonparticipating の 1 timestep 差は到着差ではなく、到着後の物理通過過程による。既存の支払・補償・満足度評価は変更しない。

### 23.13 完了判断

今回の T=382 取引について、次を完了とする。

- 4 party 初回 arrival の正式確認
- 旧到着差の誤記録原因特定
- Baseline／Actual 物理比較
- first divergence 確認
- selected Candidate 記録
- 新規 C 順位記録
- T=402〜404 の nonparticipating 通過差確認
- C 順位と Actual 通過順位の区別
- selected=False での新規順位確定源確認
- production と診断問題の切り分け
- production 変更不要判断

今回の T=382 取引周辺の一連の確認は、現時点で **完了** とする。

### 23.14 未完了事項と次の作業

今回の T=382 取引確認そのものには未完了の技術確認を残さない。研究全体として次は別作業として残る。

- 旧 `rank_and_passage_trace.py` を Git 上で修正するか、歴史的診断として残し最新正本参照を付けるかの整理
- 今回追加した 2 診断スクリプトと正式出力の Git 対象判断
- 詳細設計メモと新しい進捗第 4 巻の保存
- commit・push
- 4 交差点 nonparticipating 20% trial に関する次の研究分析へ進むかの判断

進捗メモについては、`ORDER_EXCHANGE_PROGRESS_3.md` が 6,708 行に達しており、今回の確認完了を境界として `ORDER_EXCHANGE_PROGRESS_4.md` を新規作成する予定である。本作業では `ORDER_EXCHANGE_PROGRESS_3.md` も `ORDER_EXCHANGE_PROGRESS_4.md` も編集しない。

### 23.15 最新参照先と古い記録の扱い

第 5 巻内に、旧診断の T=395、T=407、T=403、T=397 を正式な Actual arrival として記載した箇所が **将来** 存在する場合は、古い本文を削除せず、当時の診断結果であること、同一 Visit 再登録時の無条件上書きによる値であり初回 Actual arrival ではなかったこと、最新正本として **本 §23** を参照することを追記する。本追記時点（2026-10-26）では、第 5 巻本文に上記 4 値を正式 arrival として記載した箇所は見当たらなかったため、既存節への個別訂正注記は追加していない。今回の追記以外の古い節を大規模に書換えない。

旧 `rank_and_passage_trace.py` の扱い、eval_1000 延長、成立取引全体の inlink・最大当事者・nonparticipating 構成、T=392 最大取引監査、T=392 buyer 到着差、T=457 の C 順位と Actual 通過順の逆転については、**§23.14 に列挙した未完了のうち該当する事項の後続状態を本 §24 に記録する**。§23.14 の文言は歴史的記録として残し、最新参照先は **本 §24**（とくに §24.2、§24.15、§24.17）とする。

## 24. 4交差点nonparticipating 20％ trialの成立取引構成、最大当事者取引、同一inlink、および物理通過順監査（2026-10-27）

### 24.1 検証目的と対象trial

- 対象は 4 交差点 nonparticipating 20% trial
- Vehicle 600 台
- participating 480 台
- nonparticipating 120 台
- 評価期間 T=0..899
- internal TSIZE=930
- traffic seed 0
- VOT seed 1
- nonparticipation seed 3
- 成立取引 228 件
- buyer Visit 263
- seller Visit 324
- nonparticipating Visit 39
- 成立取引 party 合計 626
- 今回の検証は production を変更せず、read-only 診断で実施した

今回の目的は、個別 T=382 取引だけでなく、成立取引全体の構成、正式 inlink、最大当事者取引、nonparticipating を含む特殊構成、および **C 順位**（assigned rank）と **Actual 通過順位**（actual node passage rank）の関係を確認することである。

### 24.2 旧T=382 rank-and-passage診断の修正

対象: `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py`

- 旧診断は同一 Visit の arrival 再登録ごとに `World.T` で `GATE.actual_arrivals` を上書きしていた
- 修正版は production が保存した `current_visit["arrival_time"]` を **original method 呼出し後**に読む
- key 未登録時だけ初回値を保存
- 再登録時は上書きせず、production `arrival_time` が初回値を維持していることを照合
- T=382 対象 4 party の正式初回 Actual arrival:
  - `veh_sw_nw_base_037:2` = 388
  - `veh_nw_sw_base_047:1` = 390
  - `veh_wn_se_base_024:1` = 392
  - `veh_en_sw_base_025:2` = 394
- 旧値 395、407、403、397 は正式初回 arrival ではない
- static validation が `current_visit.get("arrival_time")` を誤認識した問題も修正した
- **runtime の `wrapped_arrival` 本体**と **static validation** を区別して記録する（到着記録の正本は runtime 修正、AST 検査の正本は static 修正）

### 24.3 eval_1000延長診断と全600台trip完了

- 元 trial の production や正式 trial は変更していない
- 診断専用 World だけを 100 timestep 延長
- diagnostic evaluation T=0..999
- internal TSIZE=1030
- simulation 後 World.T=1000
- 詳細な T=382 周辺 trace は T=382..408 のまま
- `completed_trip_count`=600
- `incomplete_vehicle_count`=0
- `incomplete_vehicle_names`=[]
- 元の eval_900 終了時に未完了だった 3 台も完走した
- 延長後も成立取引数等は eval_900 と同じだった:
  - transaction 228
  - buyer Visit 263
  - seller Visit 324
  - nonparticipating Visit 39
  - Candidate と Actual の両方を観測 626
  - passage 一致 611
  - passage 不一致 15
  - Actual passage 未観測 0
- T=900..999 に新しい成立取引は増えなかった
- 出力 directory 名を eval_1000 として eval_900 結果と区別した

対象出力 directory: `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_1000_timestep_seed_1_nonparticipation_seed_3_t382_rank_and_passage_trace`

### 24.4 成立取引228件の正式inlink全件診断

対象診断: `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py`

正式 inlink 取得元:

- selected Candidate の保存済み traffic observation record の `inlink_name`
- binding visit の `inlink_name`
- Vehicle 名、OD 名、現在 Link、終端状態から推測していない

確認値:

- 成立取引 228
- party 626
- buyer 263
- seller 324
- nonparticipating 39
- 複数 buyer 取引 32
- 複数 seller 取引 83
- nonparticipating 含有取引 37
- 最大当事者数 6
- 最大 6 当事者取引 1 件

同一 inlink 分類:

- 同一 inlink に複数 buyer がいる成立取引は 1 件
- 同一 inlink に複数 seller がいる成立取引は 2 件
- 重複を除く該当取引は T=226 と T=392 の 2 件
- buyer または seller と nonparticipating が同一 inlink にいる成立取引は 0 件
- buyer と nonparticipating 同一 inlink は 0 件
- seller と nonparticipating 同一 inlink は 0 件

正式出力 directory: `research_outputs/trial/tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_established_party_inlinks`

### 24.5 最大6当事者取引T=392の構造

- T=392
- `northwest_intersection`
- selected Candidate evaluation index 5
- buyer 3
- seller 3
- nonparticipating 0
- trade scope 6

Baseline 局所順位順:

1. `veh_en_sw_base_026:2` seller
2. `veh_sw_nw_base_039:2` seller
3. `veh_sw_nw_base_040:2` seller
4. `veh_wn_en_base_025:1` buyer
5. `veh_nw_sw_base_048:1` buyer
6. `veh_wn_se_base_025:1` buyer

Candidate 局所順位順:

1. `veh_wn_en_base_025:1` buyer
2. `veh_nw_sw_base_048:1` buyer
3. `veh_wn_se_base_025:1` buyer
4. `veh_en_sw_base_026:2` seller
5. `veh_sw_nw_base_039:2` seller
6. `veh_sw_nw_base_040:2` seller

同一 inlink:

- seller `veh_sw_nw_base_039:2` と `veh_sw_nw_base_040:2`: `southwest_intersection_to_northwest_intersection`
- buyer `veh_wn_en_base_025:1` と `veh_wn_se_base_025:1`: `west_north_od_to_northwest_intersection`

Vehicle 名中の `wn_en` 等は OD 組合せを表し、走行中の正式 inlink を表すものではない。正式 inlink は selected Candidate の保存済み `inlink_name` を使う。

### 24.6 T=392最大取引の交通・順位横並び正本

| Visit | role | formal inlink | Baseline arrival | Actual first arrival | Baseline passage | Candidate passage | Actual passage | Baseline local rank | Candidate local rank | assigned C rank | Actual node passage rank |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `veh_en_sw_base_026:2` | seller | northeast_intersection_to_northwest_intersection | 398 | 398 | 412 | 420 | 420 | 1 | 4 | 182 | 186 |
| `veh_sw_nw_base_039:2` | seller | southwest_intersection_to_northwest_intersection | 400 | 400 | 402 | 402 | 402 | 2 | 5 | 183 | 177 |
| `veh_sw_nw_base_040:2` | seller | southwest_intersection_to_northwest_intersection | 402 | 402 | 406 | 410 | 410 | 3 | 6 | 184 | 181 |
| `veh_wn_en_base_025:1` | buyer | west_north_od_to_northwest_intersection | 404 | 404 | 410 | 406 | 406 | 4 | 1 | 179 | 179 |
| `veh_nw_sw_base_048:1` | buyer | north_west_od_to_northwest_intersection | 408 | 408 | 416 | 412 | 412 | 5 | 2 | 180 | 182 |
| `veh_wn_se_base_025:1` | buyer | west_north_od_to_northwest_intersection | 410 | 406 | 420 | 416 | 416 | 6 | 3 | 181 | 184 |

- Candidate passage と Actual passage は 6 台全件一致
- **C 順位**（assigned rank）と **Actual 通過順位**（actual node passage rank）は別概念
- C 順位差合計（rank difference total）は 0
- C 順位と Actual 通過順位の個別不一致だけで production 欠陥と判断しない

### 24.7 T=392最大取引の経済条件

| Visit | role | declared VOT | G_b / R_s | payment / compensation | realized gain | satisfaction |
|---|---|---:|---:|---:|---:|---|
| `veh_wn_en_base_025:1` | buyer | 0.18457821807591362 | G_b=0.7383128723036545 | payment=0.5223440098669386 | 0.21596886243671587 | satisfied |
| `veh_nw_sw_base_048:1` | buyer | 0.4697501221448203 | G_b=1.8790004885792813 | payment=1.3293614219186634 | 0.5496390666606179 | satisfied |
| `veh_wn_se_base_025:1` | buyer | 0.5177082253347336 | G_b=2.0708329013389344 | payment=1.4650796458075128 | 0.6057532555314216 | satisfied |
| `veh_en_sw_base_026:2` | seller | 0.18888373867285319 | R_s=1.5110699093828255 | compensation=1.5110699093828255 | 0 | satisfied |
| `veh_sw_nw_base_039:2` | seller | 1.7810814861898907 | R_s=0 | compensation=0 | 0 | satisfied |
| `veh_sw_nw_base_040:2` | seller | 0.45142879205257236 | R_s=1.8057151682102894 | compensation=1.8057151682102894 | 0 | satisfied |

取引全体:

- total_G=4.688146262221871
- total_R=3.316785077593115
- surplus=1.3713611846287557
- total official payment=3.3167850775931145
- total official compensation=3.316785077593115
- balance difference=-4.440892098500626e-16
- buyer satisfied 3、unsatisfied 0
- seller satisfied 3、unsatisfied 0
- buyer realized gain total=1.3713611846287552
- seller realized gain total=0

seller `veh_sw_nw_base_039:2` の R_s=0 は、申告 VOT が 0 だからではない。Baseline passage と Candidate passage がともに T=402 で、予測遅延が 0 timestep であるため R_s=0 である。nonparticipating の VOT 欄が空であることと混同しない。

保存済み正式値の範囲で矛盾は確認されなかった。production 全体の完全な正当性証明ではない。

対象診断: `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py`

### 24.8 T=392 buyer到着差の原因

対象: `veh_wn_se_base_025:1`

- Baseline arrival=410
- Actual first arrival=406
- Actual−Baseline=−4
- Baseline passage=420
- Candidate passage=416
- Actual passage=416

記録:

- Actual 406 は production `arrival_time` の初回値から取得したものであり、診断辞書の上書き値ではない
- Baseline 410 は T=392 collector snapshot と Baseline fork 内の到着観測の双方に基づく
- T=392 common origin で対象 Vehicle と対象 inlink `west_north_od_to_northwest_intersection` の物理状態は一致
- 最初の単純 field 差は assigned_rank だったが、これは物理状態差ではない
- Actual 実 World には選択された T=392 取引の C 順位 C179〜C184 が登録される
- 取引判断用 Baseline fork には、その取引結果を遡って登録しない
- T=392 時点では位置、速度、physical index（inlink の先頭は physical index 0、先頭から 2 台目は physical index 1）、leader、follower、車列順は一致
- 最初の確認済み物理差は T=406 の `after_node_transfer` phase

直接確認した時系列:

- 同一 inlink 前方 buyer `veh_wn_en_base_025:1`:
  - Baseline local rank 4、Candidate local rank 1
  - Baseline passage 410、Candidate passage 406、Actual passage 406
- Actual では前方 buyer が T=406 に通過
- 後続の `veh_wn_se_base_025:1` がその inlink の先頭（physical index 0）になり、T=406 に正式到着
- Baseline では前方 buyer が T=410 まで残るため、対象 buyer の arrival は T=410
- したがって、arrival 差は診断エラーではなく、同一 inlink 前方 buyer の取引による早期通過が後続 buyer の先頭化を早めた物理的効果である
- production arrival 記録欠陥ではない
- この確認範囲では production 変更不要

対象診断: `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py`

### 24.9 nonparticipatingを含む成立取引37件の構成監査

- nonparticipating を含む成立取引=37
- buyer または seller が欠ける成立取引=0
- buyer 0・seller あり・nonparticipating あり=0
- seller 0・buyer あり・nonparticipating あり=0
- buyer 0・seller 0・nonparticipating のみ=0
- 全 37 件で buyer 1 件以上かつ seller 1 件以上
- buyer と seller は必ずセットで存在する正式候補条件を全件で満たした
- production 候補形成のこの契約に矛盾なし

### 24.10 nonparticipating含有取引の最大当事者数

- nonparticipating を含む 37 件に限定した最大 trade scope=4
- 最大 4 当事者取引=13 件

構成別:

- B1・S2・N1 = 9 件
- B2・S1・N1 = 2 件（T=172 `northwest_intersection`、T=232 `northwest_intersection`）
- B1・S1・N2 = 2 件（T=150 `northwest_intersection`、T=457 `northwest_intersection`）

| T | Node | buyer数 | seller数 | nonparticipating数 |
|---:|---|---:|---:|---:|
| 64 | northeast_intersection | 1 | 2 | 1 |
| 64 | northwest_intersection | 1 | 2 | 1 |
| 124 | northeast_intersection | 1 | 2 | 1 |
| 133 | northwest_intersection | 1 | 2 | 1 |
| 150 | northwest_intersection | 1 | 1 | 2 |
| 172 | northwest_intersection | 2 | 1 | 1 |
| 183 | northeast_intersection | 1 | 2 | 1 |
| 232 | northwest_intersection | 2 | 1 | 1 |
| 364 | northwest_intersection | 1 | 2 | 1 |
| 382 | northwest_intersection | 1 | 2 | 1 |
| 420 | northwest_intersection | 1 | 2 | 1 |
| 457 | northwest_intersection | 1 | 1 | 2 |
| 683 | northwest_intersection | 1 | 2 | 1 |

### 24.11 B1・S1・N2のT=150取引

| Visit | role | formal inlink | Baseline passage | Candidate passage | Actual passage | Baseline local rank | Candidate local rank | assigned C rank | Actual node passage rank | 経済（該当時） |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `veh_wn_en_base_010:1` | seller | west_north_od_to_northwest_intersection | 164 | 169 | 169 | 1 | 4 | 73 | 73 | declared VOT 0.03636473732976284; R_s=0.1818236866488142; compensation 同額; satisfied |
| `veh_sw_nw_base_014:2` | nonparticipating | southwest_intersection_to_northwest_intersection | 166 | 165 | 165 | 2 | 2 | 71 | 71 | — |
| `veh_en_sw_base_010:2` | nonparticipating | northeast_intersection_to_northwest_intersection | 168 | 167 | 167 | 3 | 3 | 72 | 72 | — |
| `veh_nw_sw_base_022:1` | buyer | north_west_od_to_northwest_intersection | 170 | 163 | 163 | 4 | 1 | 70 | 70 | declared VOT 0.25825455928608954; G_b=1.8077819150026269; payment=0.1818236866488142; realized gain=1.6259582283538125; satisfied |

取引全体: Candidate／Actual passage 全 4 件一致。2 nonparticipating の局所順位維持。C 順位と Actual 順位全 4 件一致。payment と compensation 一致。buyer、seller とも satisfied。rank difference total=0。

### 24.12 B1・S1・N2のT=457取引

| Visit | role | formal inlink | Baseline passage | Candidate passage | Actual passage | Baseline local rank | Candidate local rank | assigned C rank | Actual node passage rank | 経済（該当時） |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `veh_wn_se_base_029:1` | seller | west_north_od_to_northwest_intersection | 471 | 477 | 477 | 1 | 4 | 215 | 215 | R_s=1.3473322342780971; satisfied |
| `veh_nw_sw_pulse_004:1` | nonparticipating | north_west_od_to_northwest_intersection | 475 | 475 | 475 | 2 | 2 | 213 | 214 | — |
| `veh_sw_nw_base_050:2` | nonparticipating | southwest_intersection_to_northwest_intersection | 473 | 472 | 472 | 3 | 3 | 214 | 213 | — |
| `veh_ne_ws_base_012:2` | buyer | northeast_intersection_to_northwest_intersection | 477 | 470 | 470 | 4 | 1 | 212 | 212 | G_b=8.06619113354825; payment=1.3473322342780971; realized gain=6.718858899270153; satisfied |

取引全体: Candidate／Actual passage 全 4 件一致。2 nonparticipating の取引内局所順位は維持。2 nonparticipating の Actual 通過順だけが C 順位と逆（C213 が Actual 214、C214 が Actual 213）。rank difference は +1 と −1 で相殺し rank difference total=0。payment と compensation 一致。buyer、seller とも satisfied。

### 24.13 T=457のC213／C214通過順逆転の正式理由

対象診断: `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py`

対象 nonparticipating:

- C213 `veh_nw_sw_pulse_004:1`（assigned C rank 213、Actual node passage rank 214、Candidate／Actual passage T=475）
- C214 `veh_sw_nw_base_050:2`（assigned C rank 214、Actual node passage rank 213、Candidate／Actual passage T=472）

正式時系列（timestep を省略して理由を混同しない）:

**T=472**

- C213 を先に判定
- Candidate 判定=`outlink_entry_space_unavailable`（進路先 Link 入口空間不足／outlink entry space unavailable）
- Actual 判定=`outlink_entry_space_unavailable`
- clearance 未充足ではない。通常物理制約による一時 skip
- Node 走査は終了しない
- 後続 C214 へ走査継続
- C214 は Candidate／Actual 双方で passed
- C214 が T=472 に通過。Actual node passage rank=213

**T=473**

- C213 は Candidate／Actual 双方で `clearance_not_satisfied`
- この T=473 の Node 走査は終了する
- **T=472 の通過順逆転を発生させた理由ではない**（T=472 では clearance 未充足ではなく入口空間不足の一時 skip だった）

**T=474**

- C213 は Candidate／Actual 双方で `outlink_entry_space_unavailable`（通常物理制約による一時 skip）

**T=475**

- C213 は Candidate／Actual 双方で passed
- C213 が T=475 に通過。Actual node passage rank=214

重要な解釈:

- **C 順位**は拘束された走査優先順位である
- **Actual node passage rank**は実際の物理通過順である
- C 順位は、通常物理制約を無視して強制通過させる順位ではない
- C213 は先に判定されたが、T=472 に進路先 Link 入口空間不足（outlink entry space unavailable）で一時 skip された
- C214 は通過可能だったため後続試行で先に通過した
- Candidate 局所仮想計算と Actual 実 World が T=472〜475 の各時刻で同じ正式判定となった
- そのため C 順位と Actual 通過順位は逆転した一方、Candidate passage と Actual passage は全 4 party で一致した
- 設計どおりの挙動であり、今回の確認範囲では production 欠陥は確認されなかった
- ある条件を外した場合の反実仮想は未証明

### 24.14 production評価

今回の全確認をまとめる。

確認済み:

- 初回 Actual arrival 保存
- 再登録時の上書き防止
- eval_1000 で全 600 台完走
- 成立取引 228 件・party 626 件の正式 inlink 取得
- 正式 candidate 形成で buyer と seller が全成立取引に存在
- nonparticipating 含有 37 件でも buyer と seller の必須条件を全件充足
- selected Candidate の最大 6 当事者取引
- 同一 inlink 複数 buyer／seller
- buyer／seller と nonparticipating の同一 inlink 共存 0 件
- C 順位と Actual 通過順位の区別
- 通常物理制約で一時 skip し後続 Visit を試す契約
- clearance 未充足で当該 timestep の Node 走査終了
- Candidate 局所仮想計算と Actual 実 World の判定一致事例（T=457 等）
- 支払・補償の収支一致
- buyer／seller 満足度

今回の確認範囲では production 変更が必要な欠陥は確認されなかった。

ただし:

- 全 production の完全な正当性証明ではない
- 反実仮想を実行していない因果は断定しない
- 保存済み正式値と診断範囲に基づく評価である

### 24.15 新規・修正診断

| # | スクリプト | 目的 | 実行確認 |
|---:|---|---|---|
| 1 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t382_rank_and_passage_trace.py` | 初回 Actual arrival 修正、eval_1000 延長、全 600 台完走、T=382 rank／passage trace | py_compile 成功、static contract ok、simulation 正常完了、output directory 作成成功 |
| 2 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_established_party_inlinks.py` | 成立取引 228 件・party 626 件の正式 inlink と same-inlink 分類 | 同左 |
| 3 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_maximum_party_transaction_review.py` | 最大 6 当事者取引の交通・順位・経済横並び監査 | 同左 |
| 4 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t392_veh_wn_se_base_025_arrival_divergence.py` | T=392 buyer の Baseline arrival 410／Actual arrival 406 の物理原因追跡 | 同左 |
| 5 | `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_t457_nonparticipating_passage_order_trace.py` | T=457 の C213／C214 通過順逆転と Candidate／Actual 判定一致の正式確認 | 同左 |

### 24.16 Git対象と未完了事項

現時点で確定していること:

- 上記 5 診断は今回作業に直接関係する未追跡ファイル
- research_outputs は Git 管理済みファイルが 0 件という既存確認がある
- diagnostic output は再生成可能であり、現時点では Git 対象外候補
- `diagnostics/order_control.zip` は既存未追跡で今回対象外
- single intersection／two intersections 関連未追跡スクリプトは今回対象外
- Git の最終採否、stage、commit、push はまだ行っていない
- Git 操作は利用者が Terminal で実行する
- メモを含む commit 名には `document` を含める

完了済み（文書・検証の一部）:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md` への §24 追記完了
- `ORDER_EXCHANGE_PROGRESS_4.md` への §7〜§9 追記完了
- 今回対象 5 診断の py_compile 一括再確認: 完了（すべて成功）
- 今回対象 5 診断の static validation 一括再確認: 完了（5 本すべて `static contract ok`）
- 2 メモの記載内容の独立確認および発見事項の修正: 完了
  - 詳細設計第 5 巻 §24 と進捗第 4 巻 §7〜§9 を Terminal で独立確認
  - §24.10 の T=382 構成を B1・S2・N1 へ訂正
  - §24.16 の古い状態記述と重複項目を修正
  - 進捗第 4 巻の診断本数と Git 候補を今回の 5 診断＋2 メモへ訂正
  - T=472 の入口空間不足と T=473 の clearance 未充足が明確に区別されていることを確認

未完了:

- 5 診断の最終 Git 採否
- research_outputs を Git 対象外とする最終確認
- Git 差分と status の確認
- 対象 7 ファイルだけの stage（5 診断＋2 メモ）
- staged diff の確認
- commit
- commit 後の status と最新 commit 確認
- 別指示で push
- push 後の status と最新 commit 確認

### 24.17 最新参照先と古い記録

- T=382 初回 arrival の最新正本は §23 と本 §24.2
- 成立取引全体の正式 inlink・最大当事者・nonparticipating 構成の最新正本は本 §24
- T=392 arrival 差の最新正本は §24.8
- T=457 C 順位／Actual 順位逆転の最新正本は §24.13
- 古い出力や旧診断の値を削除せず、必要に応じて当時の診断結果であることと最新参照先を追記する
- Vehicle 名中の `wn_en` 等は OD 組合せを表し、走行中の正式 inlink を表すものではない
- 正式 inlink は selected Candidate の保存済み `inlink_name` を使う

### 24.18 完了判断と次の作業

完了とする技術確認:

- T=382 旧診断の初回 arrival 修正
- eval_1000 全車完走
- 成立取引全件の inlink 分類
- 最大 6 当事者取引監査
- T=392 arrival 差原因
- nonparticipating 含有取引の buyer／seller 必須条件
- 同一 inlink participant＋nonparticipating 0 件
- nonparticipating 含有最大 4 当事者取引 13 件
- T=150／T=457 の B1・S1・N2 確認
- T=457 通過順逆転原因

次作業:

1. `git status` と差分を確認する
2. research_outputs を Git 対象外とする最終確認を行う
3. 今回対象 7 ファイルだけを Git 対象として選別する（5 診断＋2 メモ）
4. `research_outputs`、`diagnostics/order_control.zip`、single intersection／two intersections 関連未追跡ファイルを stage しない
5. 対象 7 ファイルだけを stage する
6. `git diff --cached` で staged 内容を確認する
7. `document` を含む commit 名を確定する
8. commit する
9. commit 後の status と最新 commit を確認する
10. 別指示で push する
11. push 後の status と最新 commit を確認する
12. その後、次の研究分析テーマを決める

研究分析上の次テーマは、上記 Git 完了後に決める。今回完了した確認を、明確な新証拠なしに未完了へ戻さない。

## 25. N=5 Candidate Visit数上限trialの実作動検証、T=392取引差、C184／C185連続性、および対象inlink未進入Visitの扱い（2026-10-28）

本節は、**Candidate Visit数上限**を **N=10** から **N=5**（**trade_scope上限**）へ切り替えた独立 **N=5** trial について、正式object・正式CSV・診断出力に基づく技術正本を記す。推測と診断実装の修正は区別する。**production** および既存 **N=10** trial・既存出力は変更していない。**research_outputs** は再生成可能な診断出力であり、現時点の Git 対象とは確定していない。診断スクリプトの Git 採否も未確定である。

### 25.1 検証目的と変更範囲

- 既存 production、既存 N=10 trial、既存 N=10 出力を変更せず、同じ 600 台、同じ network、同じ seed、同じ nonparticipation seed、同じ評価条件で **Candidate Visit数上限** だけを **N=5** へ変更した独立 trial を作成した。
- 目的は、N=10 の T=392 **最大6当事者取引** が N=5 で消えるか、全成立取引が 5 当事者以下になるか、**N=5** 境界事例、**上限外Visit** の後続順位処理、buyer・seller 必須条件、C 順位連続性を確認することだった。
- N=5 包括 trial は既に全 600 台完走済みであり、今回の追加診断は T=392、T=401、T=404、T=407 周辺の因果関係を深掘りした。
- **production 変更は行っていない。**

### 25.2 N=5 trialの独立性と基本条件

| 項目 | 値 |
|------|-----|
| scenario | `tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_600_vehicle_eval_900` |
| 車両数 | 600 |
| simulation duration | 930 |
| evaluation end | 899 |
| max Candidate Visit count | **N=5** |
| nonparticipating | 20% |
| seed | 1 |
| nonparticipation seed | 3 |

- 既存 **N=10** trial との差は **Candidate Visit数上限** のみである。
- N=5 trial の production 相当出力は既存の T=900 正式 CSV として保存済みである（正式object）。
- 専用診断の simulation 終了時刻（診断ごとに別 output directory、既存出力は上書きしない）:
  - T=392 最大当事者取引レビュー: T=430 まで
  - C184／C185 順位ギャップ: T=404 まで
  - T=392／T=401 物理順（C184）: T=401 まで
  - `veh_sw_nw_base_041` 実World所在: T=407 まで（Actual northwest **arrival** 観測のため）

### 25.3 T=392におけるP−1上限前6 Visits

**P−1適格列**（Baseline local rank 順）の上限前 6 件。`candidate_visits` は先頭 5 件のみ。**6 件目は正式に Candidate外（上限）。**

| # | VisitKey | formal inlink | Baseline arrival | Baseline passage | N=5 Candidate | selected role | Cand. local rank | Cand. passage | Actual arrival | Actual passage | Node C rank | C rank 確定 |
|---|----------|---------------|------------------|------------------|---------------|---------------|------------------|---------------|----------------|----------------|-------------|-------------|
| 1 | veh_en_sw_base_026:2 | northeast_intersection_to_northwest_intersection | 398 | 412 | 内 | seller | 2 | 416 | 398 | 416 | 180 | T=392 selected Candidate |
| 2 | veh_sw_nw_base_039:2 | southwest_intersection_to_northwest_intersection | 400 | 402 | 内 | seller | 3 | 402 | 400 | 402 | 181 | T=392 selected Candidate |
| 3 | veh_sw_nw_base_040:2 | southwest_intersection_to_northwest_intersection | 402 | 406 | 内 | seller | 4 | 406 | 402 | 406 | 182 | T=392 selected Candidate |
| 4 | veh_wn_en_base_025:1 | west_north_od_to_northwest_intersection | 404 | 410 | 内 | seller | 5 | 410 | 404 | 410 | 183 | T=392 selected Candidate |
| 5 | veh_nw_sw_base_048:1 | north_west_od_to_northwest_intersection | 408 | 416 | 内 | buyer | 1 | 412 | 408 | 412 | 179 | T=392 selected Candidate |
| 6 | veh_wn_se_base_025:1 | west_north_od_to_northwest_intersection | 410 | 420 | **上限外** | Candidate対象外 | 対象外 | 対象外 | 410 | 420 | T=392 なし → **185** | T=404 初回、source **baseline** / **baseline_fallback_ranks** |

- 上限前 P−1 適格件数は **6 件**。
- N=5 **selected trade scope** は buyer 1、seller 4、nonparticipating 0 の 5 当事者。
- buyer・seller 双方が存在する正式 Candidate である。

### 25.4 N=10とN=5のselected取引比較

**N=10** T=392 selected 取引（§24 正本、正式 CSV）:

- evaluation index **5**、**6 当事者**
- buyer: veh_wn_en_base_025:1, veh_nw_sw_base_048:1, veh_wn_se_base_025:1
- seller: veh_en_sw_base_026:2, veh_sw_nw_base_039:2, veh_sw_nw_base_040:2
- Candidate 順位: 1 veh_wn_en_base_025:1, 2 veh_nw_sw_base_048:1, 3 veh_wn_se_base_025:1, 4 veh_en_sw_base_026:2, 5 veh_sw_nw_base_039:2, 6 veh_sw_nw_base_040:2
- total_G = 4.6881462622218702, total_R = 3.3167850775931149, surplus = 1.3713611846287553

**N=5** T=392 selected 取引（正式 CSV）:

- evaluation index **2**、**5 当事者**
- buyer: veh_nw_sw_base_048:1
- seller: veh_en_sw_base_026:2, veh_sw_nw_base_039:2, veh_sw_nw_base_040:2, veh_wn_en_base_025:1
- Candidate 順位: 1 veh_nw_sw_base_048:1, 2 veh_en_sw_base_026:2, 3 veh_sw_nw_base_039:2, 4 veh_sw_nw_base_040:2, 5 veh_wn_en_base_025:1
- total_G = 1.8790004885792813, total_R = 0.7555349546914127, surplus = 1.1234655338878686

差:

- N=10 surplus − N=5 surplus = **0.2478956507408867**
- N=10 surplus / N=5 surplus ≈ **1.2206526531**（N=10 の余剰は N=5 より約 **22.1%** 大きい）
- N=5 でも正の余剰を持つ **別の 5 当事者取引** が成立した。

`veh_sw_nw_base_039:2` と `veh_sw_nw_base_040:2` は **N=5 でも N=10 でも seller**（buyer ではない）。N=5 では両車の Candidate passage は Baseline passage と同じ（039: 402→402、040: 406→406）。

### 25.5 N=5 selected取引の経済評価

**buyer** veh_nw_sw_base_048:1: Baseline passage 416, Candidate passage 412, predicted saving 4 timestep, declared VOT/s 0.4697501221448203, **G_b = 1.8790004885792813**

**seller** veh_en_sw_base_026:2: 412→416, delay 4, VOT/s 0.18888373867285319, **R_s = 0.7555349546914127**

**seller** veh_sw_nw_base_039:2: 402→402, delay 0, **R_s = 0.0**

**seller** veh_sw_nw_base_040:2: 406→406, delay 0, **R_s = 0.0**

**seller** veh_wn_en_base_025:1: 410→410, delay 0, **R_s = 0.0**

selected 取引: total_G = 1.8790004885792813, total_R = 0.7555349546914127, surplus = **1.1234655338878686**（payment balance 満足）。Actual 観測済み当事者 5 件。selected Candidate の C 順位は **C179〜C183**。

### 25.6 N=5 considered Candidatesとselected Candidateの最大余剰

- T=392、northwest_intersection の N=5 **considered Candidate** は **11 件**（診断・正式object）。
- selected Candidate は evaluation index **2**、余剰 **1.1234655338878685** 前後。
- 経済的に feasible な別 Candidate（index **3**）の余剰は約 **0.0560632380**。
- selected index 2 は **feasible Candidate 中で厳密に最大** の余剰。
- ただし「全不成立 Candidate より余剰が厳密に大きい」は成立しない: index 6、10、11 にも同程度の余剰 **1.1234655338878685** 前後があるが、**buyer_nonpositive_value** 等により **feasible ではない**。
- 正確な結論: **selected Candidate は feasible Candidate の中で一意に最大余剰**（全 Candidate 中の最大余剰値への「並び」はあるが feasible ではない）。

不成立例（診断正本）:

- **A** index 1: buyer のみ veh_wn_en_base_025:1、seller 3、total_G = 0.7383128723036545, total_R = 1.8057151682102894, surplus = **-1.0674022959066349**、reason **total_buyer_value_below_required_compensation**（seller veh_sw_nw_base_040:2 の遅延が大きい）。
- **B** index 8: buyer 2（veh_sw_nw_base_039:2, veh_sw_nw_base_040:2）、seller 1、順位上前進するが passage 同じ、G_b = 0、R_s = 0、**buyer_nonpositive_value** で不成立。

### 25.7 上限外Visit veh_wn_se_base_025:1 の後続順位確定

当初仮説（推測）: T=393 以降 **selected Candidate buyer** となり **C184** を譲り **C185** になった。

**正式検証結果（反証）:**

- T=393〜404 に **selected Candidate buyer ではない**（診断: rank gap / maximum party review）。
- **`veh_wn_se_base_025:1` は T=393〜404 に selected Candidate の当事者でもなかった**（buyer に限らない）。
- **selected role は観測されていない**。
- この Visit が **seller** または **nonparticipating** として selected Candidate へ参加した事実もない。
- したがって、後続 **selected 取引** の当事者として順位を譲ったという説明は成立しない。
- T=404 に **right-of-entry**、**selected Candidate なし**、**baseline fallback** で **C185**。
- **C184** と **C185** は同一 decision ではない。

当初仮説が反証された理由は、T=404 まで **buyer ではなかった**ことに加え、**selected Candidate 当事者自体でなかった**こと（seller／nonparticipating としての selected 参加もない）まで含む。C184 は別 Visit（§25.8）が別 decision で取得したものであり、本 Visit が selected 取引の当事者として順位を後続へ譲った因果はない。

**C185** veh_wn_se_base_025:1: 初回 T=404、official source **baseline_fallback**、finalization_source **baseline**、final_rank_status **baseline_fallback_ranks**、T=404 final local rank 1、formal route next link northwest_intersection_to_southwest_intersection（baseline_physical_passage_route）、T=404 Baseline arrival 410 / passage 420、formal inlink west_north_od_to_northwest_intersection。

### 25.8 C184取得Visitの特定

- **C184** 取得 Visit: **veh_sw_nw_base_041:2**、初回 **T=401**、source **baseline_fallback**、finalization_source **baseline**、final_rank_status **baseline_fallback_ranks**。
- **C185** は **T=404**（別 decision）。Node 単位の C 順位に欠番なし。

T=401 Candidate Visits 正式順: 1 veh_sw_nw_base_041:2, 2 veh_wn_se_base_025:1, 3 veh_nw_sw_base_049:1。

T=401: **right-of-entry** = veh_sw_nw_base_041:2、selected Candidate なし、driver 前 undetermined → driver 後 **C184**；veh_wn_se_base_025:1 は T=401 終了後も未確定（**baseline fallback** で ROE 側のみ確定）。

### 25.9 veh_sw_nw_base_041:2のT=392実World所在

**T=392 driver 直前実World**（診断 `..._veh_sw_nw_base_041_real_world_location` 正本）:

- Vehicle veh_sw_nw_base_041、vehicle ID **407**
- current Link: **south_west_od_to_southwest_intersection**（start **south_west_od**、end **southwest_intersection**）
- physical index **1**、vehicle count **20**、x **195.0**、speed **0.0**
- leader veh_sw_es_base_041、follower veh_sw_es_base_042
- current Visit Node **southwest_intersection**、Visit ID **1**（**Northwest 向けではない**）
- current Visit inlink: south_west_od_to_southwest_intersection、earliest arrival **282**
- Northwest rank ledger: **absent**、C 順位なし
- link_position_class: **B_upstream_to_target_inlink_start**（対象 inlink へ正式接続可能）

**T=392 formal snapshot**（fork_result / collector）:

- Visit **veh_sw_nw_base_041:2** は Vehicle 上未登録
- collector に Vehicle 名なし、VisitKey なし、inlink physical order なし、**candidate_visits** なし
- **Candidate外** 直接理由: **not_in_snapshot_fixed_visit_set**（**snapshot固定Visit集合** 外）

T=392 対象 inlink `southwest_intersection_to_northwest_intersection` の physical order（正式）: veh_sw_nw_base_037:2, veh_sw_nw_base_038:2, veh_sw_nw_base_039:2, veh_sw_nw_base_040:2。**041:2 は未存在**のため、T=392 で 039／040 の「後方」は断定しない。

**Link 遷移**: T=397 driver 前に対象 inlink 上で初確認。before south_west_od_to_southwest_intersection → after southwest_intersection_to_northwest_intersection、continuous **True**、進入時 Visit Node **northwest_intersection**、Visit ID **2**。

**T=401 formal**: inlink 上記、physical index **2**、前方 039:2・040:2、Baseline arrival **407**、passage **414**、ROE **True**、Cand. local rank **1**、driver 後 **C184**。

**Actual arrival T=407**（hook 正本）、current Link 対象 inlink、Visit northwest ID 2。**T=401 Baseline arrival 407 と一致。**

**因果（正式objectの整合）:**

- T=392 は Southwest 向け Visit 1 の途中で **Northwest 向け Visit 2 未登録** → **snapshot固定Visit集合**・Baseline 予測対象外（予測の見落としではない）。
- T=397 までに対象 inlink 進入・Visit 2 登録。
- T=401 Baseline arrival **407**、B（veh_wn_se_base_025:1）Baseline **410** より早く **right-of-entry** → **C184**；B は T=404 に **C185**。

### 25.10 対象inlink未進入将来VisitをCandidateへ含めない理由

研究上の位置付け（利用者確定、**production 変更なし**）:

- 意思決定時点で **対象inlink未進入** の **将来Visit** を Candidate 形成に含めない。
- 将来その inlink へ進入するとは限らず、進路は対象 Node 到達まで未確定の場合がある。TVT・他 Node 順位で進入時刻も変わり得る。
- 未進入 **将来Visit** を候補化すると、未確定進路・進入時刻に依存した順位取引となり、局所仮想計算の不確実性と計算量が増える。
- **snapshot固定Visit集合** に載り、対象 inlink 物理順へ登録可能な Visit だけを対象とする現行方式を維持する（コード欠陥ではなく局所化）。
- このため T=392 未登録の A が後続 decision で B より先に C 順位を得ることはあり得る。Node 単位 C 順位は decision をまたいで連続する。

### 25.11 N=5検証のproduction評価

- **Candidate Visit数上限 N=5** は実作動した（6 件目は **Candidate外**、先頭 5 件のみ `candidate_visits`）。
- **上限外Visit** は消失せず後続で評価・確定（例: veh_wn_se_base_025:1 → **C185**）。
- C179〜C183 の後 **C184**（veh_sw_nw_base_041:2）、**C185**（上限外 Visit）。上書き・重複・欠番なし。
- buyer≥1、seller≥1 の正式 Candidate 維持。buyer のみ seller なしの成立 Candidate は確認されず。成立取引は最大 5 当事者。
- **production 変更は不要。N=5 trial は上限 N の実作動検証として成功。**

### 25.12 新規診断と診断実装上の修正事項

| スクリプト | 役割 |
|-----------|------|
| `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_trial.py` | N=5 包括 trial |
| `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_maximum_party_transaction_review.py` | T=392 最大当事者・considered / selected・T=430 |
| `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t404_c184_c185_rank_gap.py` | C184／C185 イベント・source 分類・T=404 |
| `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_t401_c184_physical_order.py` | T=392／T=401 inlink 物理順・P−1・仮説 |
| `research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_t392_veh_sw_nw_base_041_real_world_location.py` | T=392 実World・Link 遷移・T=407 Actual arrival |

診断側修正（**production 欠陥ではない**）:

- driver **後** rank state で P−1 列を復元 → T=392 確定 5 件除外の誤り → **driver 前** rank membership snapshot
- T=430 停止と research output API 非呼出し → 既存 T=900 正式 CSV との read-only 結合
- 正式 CSV の role 別空欄を None 扱い
- C184/C185: BASELINE + selected_candidate_ranks vs **baseline_fallback_ranks** 区別
- 物理順診断: mutable rank state 廃止、pre/post plain snapshot；T=392 A が **snapshot** 外は formal inlink 空欄を正式結果
- Baseline World **再帰上限**引上げ
- current Visit: **`node` object → `node.name`**（`node_name` キーは無い）
- Link 遷移: **前 Link の end_node** 保存（start 誤保存の修正）
- 実World所在: sim **T=407**（Actual **arrival**）
- static validation: helper 委譲・`current_visit` 偽 field・pre snapshot getattr を AST で正しく検査
- 重要箇所は Cursor 報告を鵜呑みにせず Terminal で独立確認

### 25.13 完了判断

完了として記録する技術確認:

- N=5 全 600 台完走、成立取引≤5 当事者
- T=392 で N=10 最大 6 当事者取引消失、N=5 で別 5 当事者取引成立
- N=10 余剰 > N=5 余剰、N=5 selected は **feasible 中最大余剰**
- P−1 上限前 6・先頭 5 適用、**上限外Visit** 後続確定
- **C184**／**C185** 取得者・時刻・**baseline fallback**、C 連続性
- veh_sw_nw_base_041:2 の T=392 実World・Visit 2 未登録・T=397 inlink 進入・T=401 Baseline 407・T=407 Actual 407・A が B より先に **C184**
- **対象inlink未進入将来Visit** を Candidate に含めない研究理由
- **production 変更不要**

**以上をもって、N=5 Candidate Visit数上限trialの実作動検証は成就した。**

### 25.14 未完了事項と次のdeparture plus 1 trial

**A. 偶数到着時刻**

- 対象周辺の Baseline／Actual arrival・passage が **偶数** に集中（N=10 でも確認）。Arrival hook で raw arrival_time が 398, 400, 402… の整数偶数であることは確認済み（診断丸めではない）。
- 出発位相 vs 2 timestep 周期（車両更新・Link・Node）は **未確定**。

**B. departure plus 1 trial（当時の記録: 未作成・未実行）**

推奨: `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial.py`
変更は全 600 台 **departure time +1 timestep** のみ。固定: 車両数・OD・進路・VOT・participation・seed・nonparticipation seed・**N=5**・network・TVT・需要間隔の相対関係。比較: 旧 T=392 ↔ 新 T=393 の Visit 集合・roles・Candidate 順・経済値・arrival/passage +1・C 順位・奇偶。読み方: 全 +1 で奇数化→出発位相主因；+1 でも偶数→2 timestep 周期；混在→相互作用。**本 §25 執筆時点では未作成・未実行。**

本 B は当時の履歴である。その後、予備 **departure plus 1** trial と aligned **departure shift** 0〜3 trial を作成・実行し、shift 0／3 の最初の成立取引分岐を **arrival tiebreaker** 割当て変化まで確認した。**最新正本は §26。** 予備 plus 1 は evaluation end 899／TSIZE 930 のままなので、全期間比較の最終正本には使わない。

**C. Git（未完了）**

- N=5 trial・診断・本メモの Git 採否未確定、**research_outputs** 採否未確定、stage/commit/push 未実施（利用者が Terminal で実行、commit 名に **document**）。

### 25.15 最新参照先と古い記録の扱い

- **N=5 Candidate Visit数上限** 検証の最新正本: **本 §25**
- N=10 T=392 **最大6当事者取引**: §24.5〜§24.8
- N=5 T=392 selected 比較: 本 §25.3〜§25.6
- **C184**／**C185**: 本 §25.7〜§25.9
- **対象inlink未進入**・**将来Visit**: 本 §25.10
- **次作業**・**departure plus 1**: 本 §25.14 は当時の記録。最新の **departure shift** 0〜3 検証、**arrival tiebreaker** 原因、**production変更未採用**、研究運用は **§26**
- §24.18 の「次作業」は当時の記録；N=5 上限検証の完了判断は **§25.13〜§25.15**
- **departure shift 0〜3**・**arrival tiebreaker**・**同着順位**・**時間平行移動**: **§26**
- **production据置き**と研究運用（**T=0開始**、signalized UXsim／FCFS／BATCH／TVT-MP、複数 seed）: **§26.14〜§26.17**
- 最新再開地点: 進捗第4巻の新しい最新節（§15）
- 古い §24 記述は削除せず歴史として残す
- 本 §25 の古い未完了記述は削除せず、最新参照先を §26 とする

---

## 26. departure shift 0〜3平行移動trial、成立取引差、arrival tiebreaker割当て変化、および方式比較上の扱い（2026-10-29）

本 §26 は、**departure shift** 0〜3 の **時間平行移動** trial、aligned 成立取引差、**arrival tiebreaker** による **同着順位** 反転、FCFS／BATCH／TVT-MP への影響範囲、**production変更未採用**、および研究運用方針に関する**最新の技術的正本**である。

§25.14 の「**departure plus 1** trial は未作成・未実行」は当時の履歴である。本節がその後の作成・実行・原因分析を上書きする。古い記述は削除しない。N=5 Candidate Visit数上限の実作動検証そのものの正本は引き続き **§25**。最新再開地点は進捗第4巻 **§15**。

**検索語:** arrival tiebreaker、fixed tiebreaker、同着順位、departure shift、時間平行移動、T=0開始、偶数時刻、偶奇依存、FCFS、BATCH、TVT-MP、signalized UXsim、乱数消費順、W.rng、order_control_rng、common random numbers、決定論的tiebreaker、乱数源分離、production変更未採用、未完了、最新再開地点。

本節では、**正式確認**、**推測**、**利用者確定方針**、**未確定**を区別する。推測を正式確認として扱わない。

### 26.1 実験目的と維持条件

既存 **N=5** Candidate Visit数上限 trial を **departure shift** 0 とした。全 600 台の departure timestep だけを一律に +1、+2、+3 した trial を作成・実行した。

維持した条件:

- Vehicle 名
- Vehicle 順序
- OD
- VOT
- participation
- nonparticipating 120 台
- seed
- network
- Candidate Visit数上限 **N=5**
- clearance
- baseline horizon

aligned 比較のため、evaluation end、internal TSIZE、expected World.T も shift 分だけ後方へ移動した。

目的:

- 旧 T=392 周辺で Baseline／Actual arrival・passage が **偶数時刻** へ集中していた原因の検証
- **時間平行移動** に対する simulation 結果の不変性の検証

**production は変更していない。**

### 26.2 shift別条件とaligned timestep

| shift | departure shift | evaluation end | internal TSIZE | World.T |
|------:|----------------:|---------------:|---------------:|--------:|
| 0 | 0 | 899 | 930 | 900 |
| 1 | 1 | 900 | 931 | 901 |
| 2 | 2 | 901 | 932 | 902 |
| 3 | 3 | 902 | 933 | 903 |

**aligned timestep の定義:**

aligned timestep = actual timestep − departure shift

旧 T=0..899 は、shift s の actual T=s..(899+s) に対応する。比較キーは aligned timestep である。

### 26.3 trialスクリプトと実行結果

**予備 shift 1 trial:**

`research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_plus_1_trial.py`

予備 shift 1 は evaluation end **899**、TSIZE **930** のままだった。評価窓を shift と一緒に動かしていないため、**全期間比較の最終正本には使わない。**

**aligned shift 1／2／3 共通 trial:**

`research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_candidate_limit_5_departure_shift_trial.py`

CLI `--shift 1|2|3`。shift 0 は既存 N=5 trial を用いる。shift 0 を本共通スクリプトへ渡すことは拒否する。出力名に aligned を含め、予備 plus 1 出力と衝突させない。

**aligned trial の実行結果（正式確認）:**

| shift | 成立取引数 | 完走 | 未完走 |
|------:|----------:|-----:|-------:|
| 0 | 226 | 600 | 0 |
| 1 | 230 | 598 | 2 |
| 2 | 226 | 600 | 0 |
| 3 | 228 | 600 | 0 |

未完走台数は、**正式評価終了時点の trip completion** である。shift 1 の未完走 2 台を、TVT 順位未確定や内部 Link 残存と**断定しない**。原因は本節では未確定である。

### 26.4 shift 0／2の完全一致

正式 CSV の aligned 比較 T=0〜899 で、shift 0 と shift 2 について次が完全一致した（**正式確認**）。

- 成立取引数 226 件
- aligned decision timestep
- Node
- buyers_sorted
- buyer count
- seller count
- nonparticipating count
- trade scope count
- buyer official payment total
- seller official compensation total

総数だけでなく、**226 件の transaction signature が完全一致した。**

ただし、shift 0 と shift 2 の一致が次のどちらかは **未確定** である。

- 実質的な 2 timestep 周期または乱数消費順の構造的一致
- 今回の条件における偶然的一致

**shift 0／3 の原因分析だけから、shift 0／2 一致を周期と断定しない。**

### 26.5 T=0固有説と単純偶奇説の反証

マクロ比較結果（正式確認）:

- shift 0 = shift 2
- shift 0 ≠ shift 1
- shift 0 ≠ shift 3
- shift 1 ≠ shift 2
- shift 1 ≠ shift 3
- shift 2 ≠ shift 3

最初の aligned 成立取引分岐:

| 比較 | 最初の aligned 分岐 |
|------|---------------------|
| shift 0 対 shift 1 | aligned T=621 |
| shift 0 対 shift 2 | 分岐なし |
| shift 0 対 shift 3 | aligned T=602 |
| shift 1 対 shift 2 | aligned T=621 |
| shift 1 対 shift 3 | aligned T=602 |
| shift 2 対 shift 3 | aligned T=602 |

したがって:

- shift 0 だけが特殊で、shift 1／2／3 が一致するという「**T=0固有説**」は**成立しなかった**。
- shift 0＝shift 2、shift 1＝shift 3 となる「単純な絶対時刻**偶奇依存**説」も**成立しなかった**。
- shift 量によって別の有効な **arrival tiebreaker** 実現が発生し得る。

### 26.6 旧T=392対shifted T=392+shift

少なくとも shift 0 の T=392 と shift 1 の T=393 について、次が完全一致した（**正式確認**）。

- Node
- Candidate Visit集合
- buyer／seller role
- trade scope
- C 順位
- Actual passage rank
- payment／compensation
- Baseline／Candidate／Actual passage は全 5 Visits で +1
- 旧偶数 passage は新 trial で奇数へ反転

この局所結果から、時刻が常に **偶数時刻** へ強制される仕組みではないことは確認された。

ただし、全期間では **arrival tiebreaker** 割当て差によって成立取引が変わったため、「全 simulation が単純な +1 **時間平行移動**」とは**結論しない**。

### 26.7 shift 0／3最初の分岐診断

診断:

`research_scripts/diagnose_tvt_mp_four_cross_intersections_nonparticipating_20_candidate_limit_5_departure_shift_0_3_first_divergence_t602_t605.py`

対象:

- shift 0 actual T=602
- shift 3 actual T=605
- aligned T=602
- `northeast_intersection`

最初の成立取引差（**正式確認**）:

**shift 0:**

- selected Candidate なし
- selection status: `no_economically_feasible_candidate`

**shift 3:**

- selected Candidate あり
- buyer: `veh_wn_en_base_041:2`
- seller: `veh_ne_ws_base_031:1`
- buyer 1
- seller 1
- nonparticipating 0
- trade scope 2
- total_G = 5.7009177956295645
- total_R = 0.0
- surplus = 5.7009177956295645

**公式支払・公式補償 0.0 と Candidate economic evaluation の total_G／total_R／surplus は別の値である。** 診断途中で両者を混同して total_G 等へ 0.0 を要求した runtime 期待値は、**診断側バグとして修正済み**であり、**production 欠陥ではない**。

### 26.8 Candidate Visit集合と順位

両 shift で Candidate Visit集合は同一だった。

- `veh_wn_en_base_041:2`
- `veh_ne_ws_base_031:1`

両 Visit の aligned Baseline arrival は **608** だった（**同着**）。

しかし正式順は反転した。

**shift 0:**

1. `veh_wn_en_base_041:2`
2. `veh_ne_ws_base_031:1`

**shift 3:**

1. `veh_ne_ws_base_031:1`
2. `veh_wn_en_base_041:2`

right-of-entry も反転した。

- shift 0: `veh_wn_en_base_041:2`
- shift 3: `veh_ne_ws_base_031:1`

最初の分岐層: `candidate_visit_order_divergence`

詳細原因: `arrival_tiebreaker_assignment_divergence`

### 26.9 正式Baseline alignment sort key

production 原典で、resolved Visit は次の key で sort される。

```
(
    baseline_arrival_timestep,
    arrival_tiebreaker,
    vehicle_id,
)
```

原典: `uxsim/order_control_tvt_baseline_alignment.py`

- `_resolved_visit_sort_key()`
- `resolved_visits.sort(key=_resolved_visit_sort_key)`

aligned 比較では arrival だけを shift 補正する。内部比較用 tuple は次である。

```
(
    aligned_sort_arrival_timestep,
    arrival_tiebreaker,
    vehicle_id,
)
```

`aligned_sort_arrival_timestep` = `baseline_arrival_timestep` − shift。値は collector snapshot の正式 field から取得し、Vehicle 名から推測しない。

各 shift の正式 Candidate 順は、この sort key で再構築した順と一致した。

- `formal_candidate_order_matches_sort_key` = True

したがって、Candidate Visit 順位形成が sort key 契約に反した事実はない。**同着順位** の反転は、sort 実装欠陥ではなく、入力となる **arrival tiebreaker** の大小反転で説明できる。

### 26.10 tiebreaker実値

**shift 0:**

`veh_wn_en_base_041:2`

- aligned arrival 608
- arrival_tiebreaker 0.15385491114815542
- vehicle_id 408
- sort key: `(608, 0.15385491114815542, 408)`

`veh_ne_ws_base_031:1`

- aligned arrival 608
- arrival_tiebreaker 0.3309686535605816
- vehicle_id 303
- sort key: `(608, 0.3309686535605816, 303)`

よって shift 0 では:

`veh_wn_en_base_041:2` < `veh_ne_ws_base_031:1`

**shift 3:**

`veh_wn_en_base_041:2`

- aligned arrival 608
- arrival_tiebreaker 0.4920934727576123
- vehicle_id 408
- sort key: `(608, 0.4920934727576123, 408)`

`veh_ne_ws_base_031:1`

- aligned arrival 608
- arrival_tiebreaker 0.12907910374092646
- vehicle_id 303
- sort key: `(608, 0.12907910374092646, 303)`

よって shift 3 では:

`veh_ne_ws_base_031:1` < `veh_wn_en_base_041:2`

**正式確認:**

- aligned arrival は同一
- Vehicle ID は shift 間で同一
- **arrival tiebreaker** の値が shift 間で変化
- tiebreaker の大小関係が反転
- Vehicle ID 比較まで到達していない
- 正式 sort key に従って Candidate 順が反転した
- Candidate 順実装が sort key に反したのではない
- 別 simulation 間で **arrival tiebreaker** の乱数割当てが **時間平行移動** 不変でないことが直接原因

### 26.11 fixed tiebreakerの意味

**fixed tiebreaker** は、同一 simulation 内の同一 Visit について一度付与後に固定され、上書きされないという意味である。別 simulation 間で、同じ Vehicle・Node・Visit へ同じ乱数値が保証されるという意味ではない。

生成源:

- 初回 Node 訪問: `W.rng.random()`
- 再訪: `W.order_control_rng.random()`

**departure shift** によって到着イベントと乱数消費先の対応が変化し、別の有効な tiebreaker 実現が発生し得る。

今回の直接原因は、正式 snapshot 値で確認した tiebreaker 大小反転である。**乱数消費順** のどのイベント差が最初に割当てをずらしたかまでは、今回の診断では追跡していない（**未確定**）。乱数消費順の推測だけで結論づけない。

### 26.12 FCFS／BATCH／TVTへの影響範囲

**arrival tiebreaker** は TVT 専用ではない。少なくとも次で利用される。

**FCFS:**

- `Vehicle.get_order_control_fcfs_rank_key()`
- key: `(arrival_time, arrival_tiebreaker, vehicle_id)`

**BATCH:**

- `Vehicle.get_order_control_batch_trigger_rank_key()`
- key: `(arrival_time, arrival_tiebreaker, vehicle_id)`
- Level 2 mimic World へ arrival tiebreaker を複製する処理あり

**TVT:**

- Baseline alignment
- Candidate Visit 形成
- Candidate local FCFS transfer
- snapshot／collector
- local binding rank sequence
- physical transfer
- Candidate local World への状態と `order_control_rng` state の保存・復元

保存・複製先:

- `order_control_current_visit`
- legacy `order_control_node_arrival_tiebreakers`
- baseline snapshot
- baseline collector
- Candidate local state
- Level 2 reference／mimic Vehicle

したがって、tiebreaker 生成の変更は TVT-MP 局所の問題ではなく、FCFS／BATCH／TVT 全体の **同着順位** 契約に波及する。

### 26.13 W.rng共有による追加影響

初回 **arrival tiebreaker** は共通の `W.rng` を消費する。`W.rng` は tiebreaker 以外にも少なくとも次で使用される。

- Vehicle color
- route／outlink choice
- outlink shuffle
- merge 時の Vehicle 選択
- OD 生成補助
- analyzer 抽出・描画補助

したがって、制御方式や経路の違いによって **arrival tiebreaker** の生成回数・順序が変わると、後続の `W.rng` 位置も変化する可能性がある（**推測として記録。今回は未実測**）。

これにより、FCFS／BATCH／TVT-MP 間で、方式そのものの効果と **乱数消費順** 差が混在する可能性がある。

ただし、今回の診断で**直接確認したのは arrival tiebreaker の大小反転まで**であり、後続 route choice 等への波及を実測したわけではない。推測と正式確認を混同しない。

### 26.14 production変更の判断（利用者確定）

**利用者確定事項:**

- 現時点では production を変更しない（**production変更未採用**）。
- **決定論的tiebreaker** 化または **乱数源分離** は未採用・未実装。
- 安全に変更する場合、FCFS、BATCH、TVT、再訪 Visit、snapshot、collector、仮想 World、Level 2、乱数列互換性、既存実験再現性を一括検証する必要がある。
- 単純な局所置換ではなく、中規模以上の独立設計変更・回帰検証課題として扱う。
- 初回 tiebreaker 用の `W.rng.random()` 呼出しを単純に削除すると、後続の共通 `W.rng` 列をずらす可能性がある。

現時点では、これらのために production 変更へ進まない。

### 26.15 研究運用方針（利用者確定）

主たる比較対象:

- **signalized UXsim**
- **FCFS**
- **BATCH**
- **TVT-MP**

すべてで次を統一する。

- simulation 開始 **T=0開始**
- 同一 departure schedule
- 同一 Vehicle 生成順
- 同一 OD
- 同一 VOT
- 同一 participation 設定
- 同一 network
- 同一 seed 条件
- 同一評価期間

**T=0開始** は departure 位相の不要な差を避けるために採用する。

ただし、方式間で交通状態、経路、Node 到着イベント順が変われば、tiebreaker の乱数割当てと `W.rng` **乱数消費順** が変わる可能性は残る。したがって、T=0 統一は必要な実験統制だが、方式間乱数対応を完全に保証するものではない。

### 26.16 研究価値と統計評価

**利用者確定方針:**

- **決定論的tiebreaker** 化または **乱数源分離** を行わなくても、平均的な方式性能を評価する研究価値は維持できる。
- ただし、単一 seed での小さな数値差や個別順位・個別取引の差を、方式固有の決定論的効果として厳密に解釈する力は弱くなる。
- 主結論は複数 seed でも安定する集計指標を中心とする。
- 複数 seed で平均、分散、方式間差の不確実性を評価する。
- 同じ seed 番号を方式間で使っても、**乱数消費順** が方式間でずれ得るため、厳密な **common random numbers** の対応が保証されたとは扱わない。
- paired 分析を使う場合は、乱数ストリーム対応が別途確認されていることを条件とする。
- 対応が確認できない間は、方式ごとの独立反復に近い解釈を採用する。
- 個別順位・個別取引の因果分析では **arrival tiebreaker** 依存を明示する。

「必要 seed 数が必ず減る」「何 seed あれば十分」等は現時点で確定していないため、固定数を正本として記載しない。

### 26.17 shift trialの研究上の位置付け

- **departure shift** trial は signalized UXsim／FCFS／BATCH／TVT-MP の**主性能比較には使用しない**。
- **時間平行移動**、**偶数時刻** 集中、**arrival tiebreaker** 割当て依存を調べた感度・反証試験として扱う。
- shift 0、1、2、3 はいずれも、それぞれの simulation 内では正式 sort key に従う**有効な simulation 結果**である。
- 異なる shift の結果差は、直ちに一方が誤りであることを意味しない。
- ただし、departure 位相以外の交通条件を比較したい trial へ tiebreaker 実現差が混入するため、主性能比較には適さない。

### 26.18 未確定事項

**未確定:**

- shift 0 と shift 2 の完全一致が偶然か、2 timestep 構造によるものか
- **arrival tiebreaker** の乱数割当てが最初にずれた正確なイベント
- FCFS／BATCH／TVT 間で、tiebreaker 用乱数消費差が route choice 等へ与える実測影響
- **決定論的tiebreaker** 化の具体設計
- tiebreaker 専用乱数源への **乱数源分離** 設計
- 既存実験との後方互換方針
- paired 統計を可能にする **common random numbers** 設計
- production 変更の採否と実施時期

これらは現在の研究を停止する必須作業ではない。現時点では、これらのために production 変更へ進まない。

### 26.19 診断実装上の修正

今回の診断における修正履歴（いずれも **production 欠陥ではなく診断側の修正**）:

- seller raw passage を shift 補正せず比較していた問題を修正し、aligned seller passage を追加
- target buyer Candidate 件数差を selection 差と誤分類する問題を修正し、candidate local calculation 差へ分類
- Candidate 対応を evaluation index ではなく buyers_sorted＋trade_scope で対応
- 公式支払 0 と Candidate 経済値 0 を混同した runtime 期待値を修正
- Baseline alignment 正式 sort key を snapshot の arrival、tiebreaker、vehicle_id から再構築
- 正式 Candidate 順との一致を独立確認
- static validation の文字列全文検索を AST 検査へ変更
- 既存診断出力は削除せず、`_before_tiebreaker_sort_key_review` の suffix を付けて退避
- 重要確認は Terminal 原典・正式 CSV・正式 snapshot により独立確認した

### 26.20 旧§25記録への最新参照

- N=5 Candidate Visit数上限検証: **§25**（変更しない）
- §25.14 の「**departure plus 1** trial は未作成・未実行」: 当時の履歴。最新は本 **§26**
- **departure shift** 0〜3 検証: 本 **§26**
- **arrival tiebreaker** 原因: 本 **§26.8〜§26.11**
- **production据置き**と研究運用: 本 **§26.14〜§26.17**
- **未完了**: 本 **§26.18**
- 最新再開地点: 進捗第4巻 **§15**

### 26.21 将来のarrival tiebreaker改修候補の目的と非採用状態

本 §26.21〜§26.34 は、将来 **arrival tiebreaker** の **決定論的tiebreaker** 化または **乱数源分離** を再検討するときの技術的叩き台である。影響範囲、設計候補、未決事項、**回帰試験**、**移行手順**、採用判断条件を、後日そのまま設計検討を再開できる詳細度で記録する。

**これは production 変更の採用決定ではない。**

明記する状態:

- **未採用**
- **未実装**
- **production変更未採用**
- production 変更へ進む承認ではない
- 推奨案も現時点では最終確定ではない
- 実装前に改めて production 原典、既存試験、方式間比較条件を再調査する
- 現在の研究を停止する必須作業ではない
- 利用者の明示判断なしに実装へ進まない

本節は仕様確定ではなく、将来設計再開用の**候補記録**である。既存 §26.14〜§26.18 の production 据置き、研究運用、未確定事項を覆さない。§26.19 の診断修正履歴も維持する。

**目的（改修を将来検討する場合の狙い。現時点では未達）:**

- 同じ Vehicle・Node・Visit に対し、比較対象 simulation 間で対応可能な **arrival tiebreaker** を与える
- arrival tiebreaker 用の乱数消費が、**route choice**、**merge**、outlink shuffle 等の一般交通乱数列をずらすことを防ぐ
- **FCFS**／**BATCH**／**TVT-MP** 間の同着順位比較をより解釈可能にする
- **departure shift** や制御方式差による乱数消費順変化を、方式性能差から可能な範囲で分離する
- paired 分析または **common random numbers** を将来利用できる基盤候補を作る

**検索語:** arrival tiebreaker、deterministic tiebreaker、決定論的tiebreaker、dedicated RNG、乱数源分離、legacy mode、deterministic Visit key mode、stable Vehicle identity、Visit ID、Node identity、common random numbers、FCFS、BATCH、TVT-MP、Level 2 mimic、Candidate local World、World copy、W.rng、order_control_rng、route choice、merge、backward compatibility、後方互換、regression test、回帰試験、migration、移行手順、未採用、未実装、production変更未採用、最新再開地点。

本節では **候補**、**必要条件**、**未決事項**、**採用条件**、**推測** を区別する。候補を採用決定として扱わない。

### 26.22 現行契約と改修対象

現行 production の正式契約（§26.9〜§26.13 の確認結果を含む）:

**arrival 順位 key:**

```
(
    arrival_time または baseline_arrival_timestep,
    arrival_tiebreaker,
    vehicle_id,
)
```

**初回 Node 訪問:**

`arrival_tiebreaker = W.rng.random()`

**再訪:**

`arrival_tiebreaker = W.order_control_rng.random()`

**fixed の意味:**

- 同一 simulation 内の同一 Visit で、付与後に上書きしない
- 別 simulation 間で同一値を保証しない

**利用箇所:**

- **FCFS**
- **BATCH** trigger
- TVT Baseline alignment
- TVT Candidate Visit 形成
- TVT Candidate local FCFS 処理

**保存・複製先:**

- `order_control_current_visit`
- legacy `order_control_node_arrival_tiebreakers`
- baseline snapshot
- baseline collector
- local binding rank sequence
- Candidate local state
- **Level 2 mimic** Vehicle
- **World copy**
- `order_control_rng` state 保存・復元

現行結果の再現性は、この契約と乱数消費順に依存する。改修は上記の生成・保存・複製・利用すべてを対象候補とする。部分置換だけでは **後方互換** と方式間整合を保証できない。

### 26.23 改修案A：Visit単位の決定論的tiebreaker

**候補**（未採用・未確定）。**deterministic Visit key mode** の中核。

**候補入力:**

- order-control tiebreaker 用の基準 seed
- Vehicle の安定した識別子（**stable Vehicle identity**）
- Node の安定した識別子（**Node identity**）
- **Visit ID**
- 必要なら scenario namespace または network namespace

**概念的な入力 tuple:**

```
(
    tiebreaker_seed,
    stable_vehicle_id,
    stable_node_id_or_name,
    visit_id,
)
```

この tuple から安定したハッシュを生成し、0 以上 1 未満の数へ変換する。

Python 組込み `hash()` は、プロセス間で値が変わり得るため**使用しない**。

**候補ハッシュ:** 標準ライブラリ `hashlib` の SHA-256 または BLAKE2b。どちらを採用するかは **未決事項**。

**実装候補例（概念。アルゴリズム・digest 長・byte order・直列化形式は未確定）:**

1. 各入力を型と境界が曖昧にならない形で UTF-8 bytes へ直列化
2. 安定ハッシュを計算
3. digest の先頭 8 bytes 等を unsigned integer へ変換
4. `2**64` 等で除算して 0 以上 1 未満へ正規化

入力が衝突しない直列化契約が**必要条件**である。悪い例は、単純な文字列連結で区切りが曖昧になるもの（例: `"12"+"3"` と `"1"+"23"`）。

**必要条件:**

- 同一入力なら別 process・別 World・別方式でも同一値
- 異なる Visit ID なら別入力
- Node 再訪を Visit ID で区別
- simulation timestep を入力へ含めない
- departure time を入力へ含めない
- FCFS／BATCH／TVT-MP で同じ Visit identity を使う場合は同じ値
- 値は有限数
- 0 以上 1 未満
- bool を数値として受け入れない

**stable Vehicle identity:**

- 現在の `Vehicle.id` を使用できるのは、方式間で Vehicle 生成順が同一に固定される場合に限る
- Vehicle 生成順が変わり得る研究へ拡張する場合は、安定した Vehicle 名または明示的 research vehicle key を検討する
- Vehicle 名を使う場合は、重複名の自動 rename や名称変更の影響を調査する必要がある

**Node identity:**

- Node 名を使う場合は、方式間・network 間で名称契約を固定する必要がある

**この案の利点:**

- Visit ごとの値が乱数消費順に依存しない
- 同一 Visit の方式間対応を作りやすい
- 未使用 Visit の tiebreaker を生成しても、他 Visit の値へ影響しない
- departure shift で値が変わらない
- **common random numbers** の設計に適する

**欠点・リスク:**

- 既存全結果と同着順位が変わり得る（**後方互換** ではない）
- ハッシュ仕様が新しい研究契約になる
- Vehicle／Node／Visit identity の安定性を保証する必要がある
- legacy 結果との完全互換ではない
- 決定論化により、同じ Visit が常に同じ優先傾向を持つ
- seed 反復時の分散を得るには tiebreaker seed を seed ごとに変える必要がある

### 26.24 改修案B：tiebreaker専用順次RNGへの乱数源分離

**候補**（未採用・未確定）。**dedicated RNG** による **乱数源分離**。

- `W.rng` から arrival tiebreaker 生成を分離
- `W.order_control_rng` とは別に、arrival_tiebreaker 専用 RNG を追加
- 例: `W.order_control_arrival_tiebreaker_rng`
- seed は World `random_seed` から `SeedSequence.spawn` 等で独立生成する案

**利点:**

- tiebreaker 消費が **route choice** 等の `W.rng` へ波及しない
- 現行の一様乱数値という性質を維持しやすい
- 実装は決定論的 Visit hash より単純な可能性がある

**重大な限界:**

- 順次 RNG なので、方式間で Visit 到着イベントの順序・件数が変われば、同一 Visit へ割り当てられる値は変わる
- departure shift 問題のうち、`W.rng` 後続列への波及は抑えられるが、方式間の同一 Visit tiebreaker 対応は保証できない
- strict **common random numbers** には不十分

したがって、この案は「一般交通乱数列からの分離」には有効だが、「同一 Visit への同一 tiebreaker 保証」には**不十分**である。案 A の代替ではなく、用途が異なる候補として扱う。

### 26.25 改修案C：方式・用途別乱数ストリーム分離

**候補**（未採用・未確定）。UXsim 全体の用途別 **乱数源分離**。

少なくとも次の乱数ストリームを分ける案:

- Vehicle 外観・描画用
- **route**／outlink **choice** 用
- **merge** selection 用
- arrival tiebreaker 用
- order-control 再訪用
- OD 生成補助用
- analyzer 抽出・描画用

既存 UXsim 全体へ大きく影響するため、今回の TVT-MP 研究内で直ちに実施する案ではない。

**利点:**

- 一用途の乱数消費差が他用途へ伝播しにくくなる
- 方式差の因果解釈を改善できる

**欠点:**

- UXsim 全体の再現性契約が変わる
- seed API、**World copy**、serialization、diagnostic、既存 test へ広範な変更が必要
- upstream UXsim との互換性や保守負担が増える
- 全用途を完全に分離しないと、残った共有 stream から波及する可能性がある

案 C は案 A／B より広い **migration** 課題である。TVT-MP 局所の決定論的 Visit key より先に実施しない。

### 26.26 legacy互換モードと新モードの切替案

将来の移行候補として、モード切替を記録する。名称は **未確定**。

**例:**

- `arrival_tiebreaker_mode="legacy_sequential"`（**legacy mode**）
- `arrival_tiebreaker_mode="dedicated_rng"`（**dedicated RNG**）
- `arrival_tiebreaker_mode="deterministic_visit_key"`（**deterministic Visit key mode**）

**legacy mode:**

- 初回は `W.rng.random()`
- 再訪は `W.order_control_rng.random()`
- 既存結果との互換性を優先

**dedicated RNG mode:**

- 専用順次 RNG
- `W.rng` への波及を防ぐ
- Visit 対応は保証しない

**deterministic Visit key mode:**

- seed＋stable Vehicle＋Node＋Visit ID
- 同一 Visit 対応を優先

**必要な互換条件（必要条件。採用時の契約候補）:**

- default 変更を直ちに行わない
- 既存研究出力には使用 mode を manifest へ保存
- World object に mode と seed 契約を保持
- 仮想 World と real World で mode を一致させる
- **World copy** 後に mode が失われない
- **legacy mode** の回帰結果を既存正式結果と比較する
- mode の異なる run を同一条件として混在させない

### 26.27 初回Visit・再訪Visit・仮想Worldの統一契約

設計課題（**未決事項** を含む）:

- 初回 Visit だけ決定論化し、再訪を順次 RNG のまま残すと、Visit 種別で比較契約が異なる
- 原則として初回・再訪を同じ Visit identity 契約で扱う方が一貫性が高い（候補方針。最終確定ではない）
- Visit ID は Node 訪問の開始時点で確定している必要がある
- tiebreaker 生成時点で Vehicle ID、Node、Visit ID が利用可能かを production 原典で再確認する
- `current_visit` 生成と arrival 記録の順序を確認する
- baseline 仮想 World で既存 Visit の tiebreaker を再生成してはならない
- real World snapshot からコピー済みの Visit は正式値を継承する
- **Candidate local World** 内で新しく到着する Visit について、real World と同じ決定論的関数を使うか、仮想専用 namespace を使うかは **未確定**
- Candidate ごとに仮想到着順が違っても、同じ Vehicle・Node・Visit identity なら同じ tiebreaker を与える方が Candidate 比較の乱数差を減らせる
- ただし、仮想 World の Visit ID が real World 将来 Visit とどう対応するかを検証する必要がある

### 26.28 FCFS／BATCH／TVT-MP共通契約

改修する場合、方式ごとに別 tiebreaker を使う案ではなく、原則として共通 Visit tiebreaker 契約を検討する（候補方針。最終確定ではない）。

**理由:**

- FCFS 対 BATCH 対 TVT-MP の比較で、同じ Visit の同着順位を対応させるため
- TVT だけ決定論化すると、公平な方式比較が損なわれる可能性があるため

**共通確認対象:**

**FCFS:**

- `incoming_vehicles` の候補 sort
- `get_order_control_fcfs_rank_key()`

**BATCH:**

- trigger candidate sort
- `get_order_control_batch_trigger_rank_key()`
- Level 0／1／2
- **Level 2 mimic** Vehicle への複製
- batch 固定後の順位契約

**TVT-MP:**

- Baseline alignment
- Candidate Visit set
- Candidate local unbound FCFS transfer
- local binding rank sequence
- physical transfer
- final rank
- actual passage observation
- snapshot／collector
- real World／baseline World／**Candidate local World**

**signalized UXsim:**

- arrival tiebreaker を直接使わない場合でも、共通 `W.rng` 消費の変化による **route choice** 等への影響を確認する
- signalized 方式との比較時に需要・Vehicle 属性・seed 契約を揃える

### 26.29 common random numbersと方式間比較

現行では、同じ seed 番号でも方式間の乱数消費順が異なるため、厳密な **common random numbers** 対応を保証しない（§26.16 の利用者確定方針と一致）。

**決定論的tiebreaker** を採用した場合、同じ Visit identity には同じ tiebreaker を与えられる。ただし、方式により経路が変わり、その Visit 自体が存在しない場合は対応対象も存在しない。

**common random numbers** 成立には、tiebreaker 以外にも少なくとも次の対応が必要になり得る。

- **route choice** random variate
- **merge** selection random variate
- OD generation
- participation assignment
- VOT assignment
- signal timing に乱数がある場合はその乱数

tiebreaker だけを決定論化しても、simulation 全体の **common random numbers** が完成するわけではない。

paired 分析を採用する場合は、どの確率変数が方式間で対応しているかを明示する。

### 26.30 実装影響範囲と変更候補箇所

ファイル名と機能単位で、少なくとも次を将来調査対象として記録する。これは**完全な影響範囲一覧ではない**。実装前に再度 grep と原典確認を行う。

`uxsim/uxsim.py`

- World RNG 初期化
- Vehicle current Visit 生成
- arrival 記録
- 初回／再訪 tiebreaker 生成
- FCFS rank key
- BATCH trigger rank key
- **World copy** または scenario copy に関係する処理

`uxsim/order_control_baseline_snapshot.py`

- arrived／not-yet-arrived Visit の snapshot
- `arrival_tiebreaker` field
- current Visit との整合性

`uxsim/order_control_baseline_collector.py`

- Visit 登録
- baseline arrival 記録
- passage 前の tiebreaker 存在検査
- plain snapshot export

`uxsim/order_control_tvt_baseline_alignment.py`

- resolved Visit sort key
- unresolved／unregistered Visit 処理

`uxsim/order_control_tvt_candidate_visit_set.py`

- Candidate Visit への tiebreaker 転送
- P−1 人口形成
- Candidate 正式順

`uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py`

- **Candidate local World** の current Visit
- tiebreaker 複製
- `order_control_rng` state 保存・復元
- 仮想新規到着

`uxsim/order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`

- Candidate local FCFS sort key

`uxsim/order_control_tvt_mp_local_binding_rank_sequence.py`

- collector snapshot からの tiebreaker 読取り

`uxsim/order_control_tvt_mp_physical_transfer.py`

- `arrival_tiebreaker` 検証
- physical transfer key

`uxsim/order_control_batch_level_2_reference.py`

- **Level 2 mimic** Vehicle への legacy arrival 辞書／current Visit 複製
- Level 2 仮想 World の順位再現

関連 test、trial、diagnostic、manifest、設計メモも対象とする。

### 26.31 回帰試験・反証試験・受入条件

将来改修時に必要な **回帰試験**（**regression test**）と受入条件。mode により期待条件を分ける。

**A. 単体試験:**

- 同じ入力 tuple から常に同じ決定論的値
- process 再起動後も同じ
- 入力要素が 1 つ違えば別値となること
- 値域 0 以上 1 未満
- bool、None、不正 Visit ID を拒否
- collision が検出可能な test 範囲で重複しない
- mode 設定の型・値検査

**B. Visit 契約試験:**

- 初回 Visit
- 再訪 Visit
- 同一 Node 再訪
- trip-end 除外条件
- not-yet-arrived Visit
- snapshot 済み Visit
- 仮想 World で新規到着する Visit
- **World copy** 前後

**C. FCFS 試験:**

- 同着 2 台
- tiebreaker 順
- tiebreaker 完全同値時の Vehicle ID fallback
- mode 別の既知順位

**D. BATCH 試験:**

- trigger 候補同着
- batch 固定前後
- Level 0／1／2
- mimic World と real World の対応
- Level 2 unresolved 時の fallback

**E. TVT-MP 試験:**

- Baseline alignment
- Candidate Visit 集合
- Candidate Visit 順
- right-of-entry
- Candidate local FCFS
- selected Candidate
- final C rank
- Actual passage
- nonparticipating あり／なし
- Candidate 上限 N=5／N=10

**F. 時間平行移動試験:**

- departure shift 0／1／2／3
- aligned arrival
- 同一 Visit tiebreaker
- aligned Candidate 順
- aligned transaction signature
- 評価窓も shift 分後方移動
- 終了境界を除いた共通範囲比較

**legacy mode の期待:**

- 現行正式結果を可能な範囲で維持
- shift 間で同一 tiebreaker を要求しない

**deterministic Visit mode の期待:**

- 同一 Visit identity の tiebreaker が shift 間で一致
- aligned arrival が同一なら同着順位が一致
- Candidate 順と right-of-entry が shift 間で一致
- 少なくとも今回の shift 0／3 T=602 事例で順位反転が消える

**G. 方式間比較試験:**

- signalized UXsim
- FCFS
- BATCH
- TVT-MP
- 同じ Vehicle・Node・Visit identity が存在する場合の tiebreaker 一致
- 経路が変わり Visit が存在しない場合は対応対象外
- mode と seed を manifest へ保存

**H. RNG 非干渉試験:**

- deterministic Visit mode で tiebreaker 生成が `W.rng` state を変えない
- dedicated RNG mode で `W.rng` state を変えない
- legacy mode では現行どおりの消費を確認
- **route choice**、**merge**、outlink shuffle 等の `W.rng` state 差を検査
- analyzer／描画の乱数消費を simulation 結果乱数から分離するかは別設計判断

**I. 再現性試験:**

- 同一 seed・同一 mode・同一 scenario の再実行一致
- manifest から mode と seed 契約を復元可能
- old output と new output を混同しない

### 26.32 移行手順と段階的実装案

将来採用する場合の段階案（**migration**／**移行手順**）。一度に全てを変更せず、段階ごとに commit、検証、メモ更新を行う。

**調査段階:**

1. 現行生成・保存・複製・利用箇所を再 grep
2. Visit ID 確定時点を原典確認
3. **World copy**、baseline World、**Candidate local World**、**Level 2 mimic** を確認
4. 既存 test と正式 trial の再現基準を固定
5. 変更前の複数 seed baseline を保存

**設計段階:**

6. mode API を決定
7. **stable Vehicle identity** を決定
8. seed・hash・直列化仕様を決定
9. **legacy mode** 互換方針（**後方互換**）を決定
10. manifest 記録仕様を決定
11. **common random numbers** の対象範囲を決定

**実装段階:**

12. 純粋な tiebreaker 生成 helper
13. World 設定と seed 保持
14. current Visit への適用
15. snapshot／collector
16. FCFS／BATCH
17. TVT-MP
18. Level 2／仮想 World
19. manifest／diagnostic

**検証段階:**

20. 単体試験
21. **legacy mode** 回帰
22. deterministic mode shift trial
23. FCFS／BATCH／TVT-MP 比較
24. 複数 seed
25. 性能・再現性・後方互換評価

**採用判断:**

26. 既存正式結果を legacy として維持するか
27. 新しい研究結果だけ新 mode を使うか
28. default を変更するか
29. 論文上で mode 差をどう説明するか

### 26.33 設計上の未決事項と採用判断条件

**未決事項:**

- **stable Vehicle identity**
- **Node identity**
- Visit ID の方式間対応
- hash アルゴリズム
- byte 直列化
- seed namespace
- first visit と revisit の統一
- virtual Visit の namespace
- mode の default
- **legacy mode** の維持期間
- manifest schema
- **route choice** 等の乱数源分離範囲
- upstream UXsim との互換性
- performance cost
- collision リスクと検査
- old trial の再実行要否
- 論文の実験条件を途中で変更する可否

**採用条件候補**（すべて満たすまで production 変更しない）:

- FCFS／BATCH／TVT-MP で共通契約を実装できる
- **legacy mode** で既存研究を再現できる、または再現不能差を説明できる
- deterministic mode で今回の shift 0／3 順位反転が解消する
- tiebreaker 生成が `W.rng` の後続交通乱数列を変えない
- 仮想 World と real World で整合する
- **Level 2 mimic** で整合する
- 複数 seed 結果が安定する
- 実装・保守コストに対して研究上の改善が十分大きい
- 利用者が production 変更を明示決定する

### 26.34 将来再開時の調査手順

将来、改修検討を再開するときの検索・確認手順。

**検索語:**

- `arrival_tiebreaker`
- `order_control_node_arrival_tiebreakers`
- `order_control_rng`
- `W.rng.random`
- `get_order_control_fcfs_rank_key`
- `get_order_control_batch_trigger_rank_key`
- `_resolved_visit_sort_key`
- `record_order_control_node_arrival`
- `baseline_visit_snapshot`
- `get_baseline_visit_snapshot`
- Candidate local World
- Level 2 mimic
- deterministic tiebreaker
- random stream separation
- common random numbers

**再開手順:**

1. 本 §26.21〜§26.34 を読む
2. §26.8〜§26.13 の正式原因を再確認
3. 進捗第4巻 §15 の現在地を確認
4. production と test の最新状態を grep・原典確認
5. 現在の branch と既存変更を確認
6. legacy 結果の再現基準を固定
7. 改修を採用するか利用者判断
8. 採用後にのみ詳細仕様を確定
9. 実装前に詳細設計メモと進捗メモを更新
10. Cursor には編集・実装に必要な調査だけを行わせる
11. py_compile、static validation、simulation、Git は Terminal で実行
12. production 変更へ自動的に進まない

**最新再開地点** は進捗第4巻 **§15** のままである。本 §26.21〜§26.34 は将来改修の叩き台であり、現在の必須作業ではない。

## 27. 6×6 grid高需要TVT-MPスケーリング検証・FCFS対照分析（2026-10-31）

本節は、既存 §26 の arrival tiebreaker 検討とは独立した論点として、6×6 grid 高需要条件下での TVT-MP 実行可能性・交通状態・計算量の事前検証、および同一 network・需要・評価期間における FCFS 対照 trial の結果を正式に記録する。§26 本文は変更していない。

### 27.1 作業範囲

本節で記録する対象は次のとおりである。

- 1,000 台 TVT-MP 短期 benchmark
- 5,000 台 TVT-MP early scaling benchmark
- 同一 network・需要・評価期間の 5,000 台 FCFS 対照 trial
- Link 理論収容力と T=599 時点の局所的飽和
- 最大当事者数取引
- 計算時間上の制約
- 現時点の研究判断
- 未完了事項（§27.16）
- 将来の再開手順（§27.17）

### 27.2 この節の位置づけ

- これは**正式な方式性能比較ではない**。
- 1,000 台と 5,000 台について、実行可能性・交通状態・計算量を確認する**事前検証**である。
- 5,000 台 FCFS trial は、入口目詰まりが network・需要条件に由来するかを**集計的に**確認する対照 trial である。
- 同じ seed 番号でも制御方式により乱数消費順が変わり得るため、FCFS と TVT-MP の **Vehicle 単位 paired 比較ではない**。
- **production は変更していない**。
- **5,000 台全車完走 TVT-MP trial** と **10,000 台 TVT-MP trial** は**実行していない**。

### 27.3 実行した新規スクリプト

いずれも既存 production および既存 trial を変更せず、**新規別スクリプト**として作成・実行した。

1. `research_scripts/run_tvt_mp_6x6_grid_high_demand_1000_vehicle_short_benchmark.py`
2. `research_scripts/run_tvt_mp_6x6_grid_high_demand_5000_vehicle_early_scaling_benchmark.py`
3. `research_scripts/run_fcfs_6x6_grid_high_demand_5000_vehicle_eval_600_comparison_trial.py`

正式出力は `research_outputs/trial/` 配下の各 scenario 名 directory に保存した。本節では数値と解釈のみを記録し、出力ファイル本文はここへ転載しない。

### 27.4 共通 network・需要条件

- 6×6 内部 grid
- 内部 Node 36
- 外部 OD Node 24
- 総 Node 60
- 内部 directed Link 120
- OD connector directed Link 48
- 総 Link 168
- 単車線（`number_of_lanes = 1`）
- merge priority 1
- 内部 Link 長 400 m
- OD connector 長 300 m
- free-flow speed 20 m/s
- jam density 0.2 台/m
- traffic / random seed 0
- demand generation seed 42
- VOT seed 1（**TVT-MP のみ**）
- 最小 OD Manhattan distance 5
- free route choice
- `specified_route` 不使用
- departure T=0〜500
- 全参加（TVT-MP）
- TVT-MP clearance 1
- FCFS clearance 1（内部 36 Node のみ FCFS）
- TVT-MP baseline horizon 30
- TVT-MP Candidate Visit 数上限 **N=10** を trial 側で明示設定

**N=10** は production の暗黙 default に依存せず、研究標準設定として各 TVT-MP trial スクリプトが明示した。

### 27.5 Link 理論収容力

production 原典（UXsim `Link` / `addLink`）から確認した事実:

- UXsim Link の既定 jam density は 0.2 台/m
- 単車線、`DELTAN = 1`
- `delta = 1 / jam density = 5` m/台
- 内部 Link 400 m の理論収容台数は **80 台**
- connector 300 m の理論収容台数は **60 台**
- 内部 120 Link 合計の理論収容は **9,600 台**
- connector 48 Link 合計の理論収容は **2,880 台**
- 全 168 Link 合計の理論収容台数は **12,480 台**

したがって、5,000 台という総台数そのものは全 Link 理論収容 12,480 台を**超えていない**。

ただしこれは全 Link が均等に jam density まで埋まることを前提とする理論値であり、経路偏在、入口交差点処理能力、下流空間不足、局所的 spillback とは**区別する**。

### 27.6 1,000 台 TVT-MP 短期 benchmark

**条件:**

- Vehicle 1,000 台
- departure T=0〜500
- evaluation T=0〜999
- evaluation end 999
- internal TSIZE 1030
- World.T after simulation 1000
- TVT-MP Node 36
- N=10
- baseline horizon 30
- clearance 1
- recursion limit 50,000

**結果:**

- completed 1,000 / incomplete 0
- 成立取引 1,078 件
- `exec_simulation_seconds = 7620.127332167001`
- `seconds_per_evaluation_timestep = 7.6201273321670016`
- final output total bytes = 1,749,859
- transaction CSV 1,078 行と manifest transaction 数 1,078 件が一致
- Node 別取引数合計 1,078 件
- vehicle CSV 1,000 行と manifest Vehicle 数 1,000 台が一致

6×6 grid、36 TVT-MP Node、1,000 台、N=10 で production 例外なく完了し、**全車完走**と正式 research output 生成が確認された。

### 27.7 1,000 台 trial の最大当事者取引

- 最大 trade scope Visit 数は **4**
- 最大 4 当事者取引は **28 件**
- 構成は buyer 1＋seller 3、buyer 2＋seller 2、buyer 3＋seller 1
- 全参加 trial のため nonparticipating は 0
- N=10 上限には到達していない

**代表例**（最大 4 当事者取引のうち buyer 実現価値合計が最大）:

- decision T=421、Node `g_2_3`、buyer 2、seller 2

当事者:

| 役割 | Visit |
|------|-------|
| buyer | `veh_709:4`, `veh_364:7` |
| seller | `veh_547:5`, `veh_696:4` |

Baseline passage: `veh_547:5` T=431、`veh_696:4` T=433、`veh_709:4` T=435、`veh_364:7` T=437。

Candidate・Actual passage: C197 `veh_709:4` buyer T=431、C198 `veh_364:7` buyer T=433、C199 `veh_547:5` seller T=435、C200 `veh_696:4` seller T=437。

経済値: buyer 実現時間短縮価値合計 = 28.5218776672919、seller 必要補償合計 = 0.6592801312154991、buyer 公式支払合計 = 0.6592801312154991、seller 公式補償合計 = 0.6592801312154991、buyer 実現利得合計 = 27.8625975360764、seller 実現利得合計 = 0。

全 4 当事者 satisfied。Candidate passage と Actual passage、assigned rank と Actual passage rank、predicted route・actual route・formal route が一致した。

**predicted route** は「Candidate 仮想 World が自由に新規決定した進路」と単純化せず、**Candidate 評価で使用された予測上の進路**であり、原則として baseline 物理通過時に得られた進路を Candidate 計算へ適用する（現在時点 T より前に順位確定済みの Visit 等は別扱い）という現行契約に沿う。

### 27.8 5,000 台 TVT-MP early scaling benchmark

**条件:**

- Vehicle 5,000 台
- departure T=0〜500
- evaluation T=0〜599（evaluation end 599）
- internal TSIZE 630
- World.T after simulation 600
- TVT-MP Node 36、N=10、baseline horizon 30、clearance 1
- recursion limit 50,000
- T=501〜599 の 99 timestep を、最後の予定 departure T=500 より後の**観測期間**とした
- **全車完走は要求しない** early scaling benchmark

**結果（Vehicle state）:**

- completed / end = 576
- run = 3,339
- wait = 1,085
- not completed = 4,424
- `scheduled_departure_reached_count = 5,000`
- `scheduled_departure_not_reached_count = 0`

`scheduled_departure_reached_count` は予定 departure time が evaluation end 以下である Vehicle 数であり、**実際に network へ進入したことの直接指標ではない**。

**成立取引:**

- 2,381 件
- transaction CSV 2,381 行、manifest transactions 2,381 件、Node 別取引数合計 2,381 件が一致

**出力・時間:**

- `exec_simulation_seconds = 79685.76344854198`
- `seconds_per_evaluation_timestep = 132.80960574756998`
- output total bytes = 4,628,323

1,000 台 benchmark の 7.6201273321670016 秒/timestep に対し、保存済み wall-time 値では **17.428790879509066 倍/timestep** であった。evaluation 範囲と交通状態が異なるため、この倍率を厳密な Vehicle 台数スケーリング則とは扱わない。

### 27.9 5,000 台 TVT-MP 実行時間の注意

実行時間について、次を明記する（断定を避ける）。

- 実行開始後、Mac が複数回ログイン画面になった。
- 途中確認時に Python process は `R+`、CPU 約 99%、累積 CPU 時間が増加しており、**計算自体は継続**していた。
- 途中から `caffeinate -i -w <PID>` を適用し、以後のアイドルスリープを防止した。
- スクリプト保存値の `exec_simulation_seconds` は **79685.76344854198**。
- UXsim 進行表示の最終 computation time は約 **114,362 秒**だった。
- スクリプトの `perf_counter` 値、UXsim 側 computation time、Mac の sleep／screen lock の関係は**今回検証していない**。
- 79685.763 秒を**純粋な CPU 時間**と断定しない。
- FCFS との保存値比（約 **23,349 倍**）を、再現可能な**純粋 CPU 計算量比**として採用しない。
- ただし **TVT-MP が FCFS より桁違いに重い**という定性的結論は維持する。

今後 Mac で長時間 trial を実行するときは、**実行開始時から** `caffeinate` を併用してアイドルスリープを防止する運用とする。

### 27.10 5,000 台 trial の最大当事者取引

- 最大 trade scope Visit 数は **7**
- 該当取引は **2 件**
- N=10 上限には到達していない

**取引 1**（T=301、Node `g_4_5`、buyer 1、seller 6、`ex_post_feasible`、buyer・seller 全 7 Visit の Actual passage 観測済み）:

- buyer `veh_962:2`: VOT 0.7496440206182547、Baseline T=326、Candidate/Actual T=319、7 秒短縮、realized time value 5.247508144327783、official payment 4.57848957698266、realized gain 0.6690185673451232、satisfied
- seller `veh_1423:1`: 3 秒遅延、realized delay loss 2.3319674423068752、compensation 2.3319674423068752、realized gain 0
- seller `veh_841:4`: 1 秒遅延、realized delay loss 2.2465221346757844、compensation 2.2465221346757844、realized gain 0
- seller `veh_824:6`、`veh_444:5`、`veh_100:7`: Baseline と Actual 同一、actual delay 0、`trivially_satisfied_nonpositive_actual_delay`
- seller `veh_350:7`: Baseline T=322、Candidate/Actual T=321、seller だが Actual では 1 秒早く通過、official compensation 0、realized gain 0.31359974220990344、`trivially_satisfied_nonpositive_actual_delay`

取引全体: buyer actual declared time saving value total 5.247508144327783、seller actual required compensation total 4.57848957698266、buyer official payment total 4.57848957698266、seller official compensation total 4.57848957698266、buyer realized gain total 0.6690185673451232、seller realized gain total 0.31359974220990344、**全 7 当事者 satisfied**。

全 7 Visit で Candidate passage timestep と Actual passage timestep は一致。一方 assigned rank と Actual node passage rank は完全一致ではなく、**moved earlier 4、rank exact 1、moved later 2、rank difference total 4**。各当事者の通過時刻予測が一致していても、当事者外 Visit を含む Node 全体順位では挿入・前後関係差が生じ得る。

**取引 2**（T=598、Node `g_2_1`、buyer 6、seller 1、`evaluation_unavailable`）:

- buyer 6 Visit、seller 1 Visit の全 7 Visit が evaluation end まで Actual passage 未観測
- actual 経済値、Actual 順位、実現利得は評価不能
- 公式支払・補償は 0
- Candidate 予測上の取引として成立しているが、**実現効果の評価には使用できない**

### 27.11 5,000 台 TVT-MP の Link 収容状態（T=599）

**内部 Link（120 本、理論収容 9,600 台）:** Vehicle 2,101 台、aggregate occupancy 0.21885416666666666、100%以上 0、90%以上 6、75%以上 18、50%以上 26。

**外部→内部 connector（24 本、理論収容 1,440 台）:** Vehicle 1,224 台、aggregate occupancy **0.85**、100%以上 0、90%以上 **13**、75%以上 22、50%以上 22。

**内部→外部 connector（24 本）:** Vehicle 14 台、aggregate occupancy 0.009722222222222222、50%以上 0。

**全 Link:** Vehicle 3,339 台、aggregate occupancy 0.2675480769230769、100%以上 0、90%以上 19、75%以上 40、50%以上 48。

代表的な高収容流入 connector: `bottom_4_to_g_5_4` 58/60、`right_0_to_g_0_5` 57/60、`left_0_to_g_0_0` 56/60、`left_5_to_g_5_0` 56/60、`top_0_to_g_0_0` 56/60。

ネットワーク全体が満杯なのではなく、**外部→内部 connector** とその直後の一部内部 Link が**局所的に**高収容となった。

### 27.12 FCFS 同条件対照 trial

**条件:** Vehicle 5,000 台、departure T=0〜500、simulation T=0〜599、`TMAX = 600`、内部 36 Node を FCFS、clearance 1。その他 network・需要は TVT-MP 5,000 台 benchmark と同じ。**正式な方式性能比較ではない。Vehicle 単位 paired 比較ではない。**

**Vehicle state:** end = 513、run = 3,285、wait = 1,202、not completed = 4,487。

**Link 収容:**

| 区分 | Vehicle 数 | aggregate occupancy | 90%以上 Link |
|------|------------|---------------------|--------------|
| 内部 Link | 2,009 | 0.20927083333333332 | 8 |
| 外部→内部 connector | 1,258 | 0.8736111111111111 | 12 |
| 内部→外部 connector | 18 | 0.0125 | — |
| 全 Link | 3,285 | 0.26322115384615385 | 20 |

**timing（保存値）:** finalize 14.852459417073987 秒、`exec_simulation` 3.4127832499798387 秒、seconds per evaluation timestep 0.005687972083299731、`pre_manifest_script_total` 18.329434458049946 秒、final script total 18.330203082994558 秒。

### 27.13 TVT-MP と FCFS の集計比較

**FCFS − TVT-MP（reference）:**

- completed = **−63**
- run = **−54**
- wait = **+117**
- 外部→内部 connector aggregate occupancy = **+0.023611111111111138**
- 外部→内部 connector の 90%以上 Link 数 = **−1**
- 内部 Link aggregate occupancy = **−0.009583333333333333**

**解釈:**

- FCFS でも外部→内部 connector が **87.36%** まで埋まり、wait **1,202 台**が発生した。
- 入口 connector 高収容と大量 wait は **TVT-MP 固有ではない**。
- 主因は、5,000 台を T=0〜500 へ投入した**高需要条件**と、単車線 6×6 network の入口・交差点処理能力である可能性が高い。
- TVT-MP は FCFS より completed **63 台多く**、wait **117 台少なく**、外部→内部 connector 上が **34 台少なく**、内部 Link 上が **92 台多かった**。
- 短期集計では TVT-MP が入口目詰まりを**特に悪化させた証拠はない**。むしろ TVT-MP が入口から内部へやや多く送り込んだように見える。
- 乱数消費順と route choice が方式間で変わり得るため、**TVT-MP の正式な性能優位とは結論しない**。

### 27.14 計算量に関する暫定原因

FCFS では同じ 5,000 台・600 timestep の traffic update が約 **3.41 秒**で完了した。TVT-MP の長時間化を**交通渋滞そのものだけ**では説明できない。

TVT-MP では 36 Node で反復的に次を行う: full World の Baseline 複製、baseline horizon 30 の仮想計算、Candidate Visit 集合形成、最大 N=10 の Candidate 検討、Candidate 局所仮想計算、経済評価と順位確定。

現時点ではこれらの反復が極端な計算量の**主因である可能性が高い**。詳細 profile は**未実施**であり、特定関数や処理を正式なボトルネックと断定しない。**production の最適化や近似化は未採用・未実装**である。

### 27.15 現時点の設計判断

- **production は変更しない**。
- **5,000 台全車完走 TVT-MP trial** へ直進しない。
- **10,000 台 TVT-MP trial** へ進まない。
- 5,000 台条件は、入口側を強く過飽和にする**高需要ストレス条件**としては有用である。
- 通常需要の方式性能を代表する条件としては**過大な可能性**がある。
- 5,000 台という総台数より、**T=0〜500 への集中投入**が重要な要因である。
- 同じ 5,000 台でも departure 期間を延長すれば、入口飽和を緩和できる可能性がある。
- **1,000 台 trial と同じ平均投入強度**（vehicles per timestep）を保った条件設計を、将来の方式比較前に検討する。
- 1,000 台 trial は departure T=0〜500 であり、平均投入強度は**概ね 2 台/timestep** である。
- 5,000 台を同じ平均投入強度 2 台/timestep へ揃えるなら、departure 期間は**概ね 2,500 timestep** となる（算術上の換算。実行済み条件ではない）。
- 上記は**将来条件の候補**であり、departure 期間延長 trial は**未作成・未実行**である。
- **次の優先対象は未決定**である。候補は次のとおり（いずれかへ自動的に進まない）。
  - 台数を調整した中間規模 trial
  - 5,000 台の departure 期間延長 trial
  - TVT-MP 計算量 profile
- **利用者判断前に**、上記候補のいずれかへ自動的に進まない。
- arrival tiebreaker 等の production 改修（§26）は、本節のスケーリング結論と**独立**して扱う。

### 27.16 未完了事項

**区別（現時点の確定事項）:**

- **profiling は未実施**である。
- **ボトルネックは未確定**である。
- **production 最適化は未採用・未実装**である。
- **5,000 台全車完走 trial** と **10,000 台 trial** へ**直進しない**（§27.15 の設計判断）。

**既存の未完了項目（維持）:**

- 5,000 台・**全車完走**を要求する正式 TVT-MP trial
- 10,000 台 TVT-MP trial（既存 FCFS 高需要 test 想定条件）
- TVT-MP 内部処理の詳細 **profiling** とボトルネック特定
- `perf_counter`、UXsim computation time、Mac sleep／lock の関係の独立検証
- FCFS と TVT-MP の**正式な方式性能比較**（common random numbers、paired 設計を含む）
- 5,000 台条件の**需要緩和版**（departure window 延長等）での再 benchmark
- 保存済み 79685 秒を再現可能なベンチマーク CPU 時間として登録すること

**追加の未完了項目:**

- 台数を調整した中間規模 trial
- 複数 seed による確認
- signalized UXsim の同一短期条件対照
- BATCH の同一短期条件対照
- full World copy の実行回数と所要時間
- Baseline 計算の実行回数と所要時間
- Candidate 形成数
- Candidate 局所仮想計算の実行回数と所要時間
- Node 別計算負荷
- timestep 別計算負荷
- 交通状態と計算負荷の関係
- 計算量改善方針
- production 最適化の採否
- 通常需要条件と高需要ストレス条件の正式な区別
- 論文での実験条件の位置づけ

### 27.17 将来の再開手順

1. 本 **§27** を読む。
2. 進捗第4巻の最新再開地点 **§17** を読む（**§16** は 2026-10-31 の歴史的記録）。**§16 執筆時点では §17 未追記**だった場合は各 trial 出力を正本とする。
3. 1,000 台 TVT-MP、5,000 台 TVT-MP、5,000 台 FCFS の `manifest.json` と `run_summary.txt` を確認する。
4. execution time の**時計差**（`perf_counter`、UXsim computation time 等）と **Mac sleep 条件**を再確認する（§27.9）。
5. 次の対象を、**台数調整**、**departure 期間延長**、**計算量 profile** から**利用者が決定**する（§27.15。未決定のまま自動進行しない）。
6. **production 変更を前提にしない**。
7. 計算量 profile を行う場合は、最初に **read-only な診断計画**を作る（production 改修を含めない）。
8. 長時間 trial は **Terminal** で実行し、**開始時から**アイドルスリープ防止を行う。標準例:

   ```text
   caffeinate -i python <trial_script.py>
   ```

   **既に実行中の process へ後付け**する場合**だけ**、次を用いる（開始時標準と混同しない）:

   ```text
   caffeinate -i -w <PID>
   ```

9. Cursor には、編集・実装に**不可欠な調査だけ**を行わせる。
10. **py_compile**、**static validation**、**simulation**、**grep**、**Git 操作**は Cursor に任せず **Terminal** で行う。
11. 詳細設計正本と進捗メモの**双方への反映要否**を、節目ごとに確認する。
12. §26（arrival tiebreaker）と本節（スケーリング）の論点を混同しない。
13. production・既存 trial を変更せず、必要なら **新規 research_scripts** を追加する。
14. 結果を本設計正本 §27 または進捗メモへ追記する際、本節の「非 paired 比較」「非正式性能比較」の位置づけを維持する。

**検索語（本 §27 へ到達するための目安）:**

- 6×6 grid
- high demand
- 5000 vehicles
- 1000 vehicles
- scaling benchmark
- entry connector saturation
- external to internal connector
- wait vehicles
- FCFS comparison
- TVT-MP runtime
- World copy
- Baseline computation
- Candidate local computation
- over-saturated demand
- departure 0 500
- 計算量
- 入口目詰まり
- 外部リンク渋滞
- 高需要ストレス条件
- 未完了
- production変更なし

**最新（2026-11-01）:** 3,000 台 FCFS 需要条件選定・TMAX=5000 完走確認の設計正本は **§28**。進捗第4巻の最新再開地点は **§17**（本 §27 は 5,000 台スケーリングの歴史的記録として維持）。

---

## 28. 3,000台・全Link 200m・60km/h条件のFCFS需要選定と完走期間検証（2026-11-01）

**検索語（本 §28 へ到達するための目安）:** 3,000台、3台/timestep、2.5台/timestep、200m Link、60km/h、capacity_in、capacity_out、臨界密度、FCFS完走確認、TMAX=5000、最終完走時刻、需要条件選定、通常需要、準高需要、高需要、入口飽和、内部Link混雑、TVT-MP評価期間、departure 999、completion check、vehicle plan digest。

### 28.1 作業の目的と位置づけ

- 直前の **5,000 台・departure T=0〜500** 条件（高需要ストレス条件）は、外部→内部 connector の局所飽和と大量 **wait** が発生しており、**通常需要**の研究代表条件としては投入集中が過大な可能性があった（§27 参照。本節では改めて位置づけのみ）。
- **3,000 台 TVT-MP trial** へ直進せず、計算の軽い **FCFS** で、(1) 道路条件、(2) 投入率、(3) departure 終了時の交通状態、(4) **全車完走時刻**（**TMAX=5000** completion check）を順に確認した。
- **production**、既存 trial、既存 test、既存出力は変更せず、すべて **新規別スクリプト** と **新規別出力 directory** で検証した。
- 今回の目的は **TVT-MP の性能優劣**を測ることではなく、将来の **3,000 台 TVT-MP trial** に用いる **需要条件**、**evaluation end**、**internal TSIZE**、**観測期間**、**計算量見積り**の基礎条件を決めることである。
- **3,000 台 TVT-MP 本体**は、**まだ作成も実行もしていない**。

### 28.2 当初の3,000台・2.5台/timestep条件（400m / 300m / 20m/s）

**スクリプト:** `research_scripts/run_fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial.py`

**出力 directory:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial_seed_0_demand_seed_42`

**条件:**

| 項目 | 値 |
|------|-----|
| Vehicle 数 | 3,000 台 |
| departure | T=0〜1,200 |
| evaluation end | T=1,200 |
| TMAX | 1,201 |
| World.T after simulation | 1,201 |
| 名目平均投入率 | **2.5 台/timestep** |
| 24 外部 OD Node 完全均等仮定 | **0.1041667 台/timestep・Node** |
| OD 配分 | OD 抽選により各 Node 均等ではない |
| 内部 Link 長 | 400 m |
| OD connector 長 | 300 m |
| free-flow speed | 20 m/s |
| jam density | 0.2 台/m |
| capacity_in / capacity_out | **未指定** |
| FCFS | 内部 36 Node、clearance 1 |
| random seed | 0 |
| demand generation seed | 42 |
| 最小 OD Manhattan distance | 5 |
| 経路 | free route choice、specified_route 不使用 |
| 観測 | **全車完走を要求しない**。T=1,200 投入終了時点 |

**結果（T=1,200）:**

- state: **end 1,702** / **run 1,297** / **wait 1**
- not completed: 1,298
- 内部 Link: 1,223 台、aggregate occupancy **0.12739583333333335**
- 外部→内部 connector: 53 台、occupancy **0.03680555555555556**
- 内部→外部 connector: 21 台、occupancy **0.014583333333333334**
- 全 Link: 1,297 台、occupancy **0.10392628205128206**
- 90% 以上: 0 本 / 75% 以上: 1 本 / 50% 以上: 8 本
- 最大 Link: **h_4_4_3**、70 台 / 80 台、occupancy **0.875**
- exec_simulation_seconds: **2.8749280829215422**
- final_script_total_seconds: 約 **17.4947**

**解釈（条件→結果）:**

- **5,000 台集中投入**のような **入口 connector 飽和**・大量 **wait** は発生しなかった（wait **1 台**）。
- **内部 Link** に局所混雑（最大 occupancy 0.875）。
- 道路条件が研究本番候補（**200 m / 60 km/h**）へ未調整のため **正式採用せず**。

### 28.3 道路条件の再検討（全 Link 200m・60km/h・capacity_in/out 未指定）

**採用した研究本番候補:** 全 **168 directed Link** **200 m**、**60 km/h**（16.666… m/s）、κ=0.2、τ=1、単車線、merge 1、FCFS clearance 1、**capacity_in/out 未指定**。

**jam-density 理論収容:** 40 台/Link；内部 4,800；各 connector 方向 960；合計 **6,720 台**。

**capacity_in/out 判断:** FD 容量と別の **Link 境界制約**。均質 Link へ **1,500 台/h** を一律設定すると **人工ゲート**解釈となり FCFS 競合と混在。**参考値として保持**、今回 **trial では未設定**。**production 変更なし**。

### 28.4 FD容量・臨界密度・occupancy の意味

**条件:** u=16.6666666667 m/s、κ=0.2 台/m、τ=1 s、**w=5 m/s**。

**FD 容量:** q_max = u·w·κ/(u+w) ≈ **0.7692307692 台/s** ≈ **2769.230769 台/h**。q=k·v；自由流 q=k·u。

**臨界密度:** k* = q_max/u ≈ **0.04615384615 台/m** ≈ **46.15384615 台/km**（≈21.67 m/台）。

**200 m Link:** 臨界密度相当 ≈ **9.230769 台**（整数 snapshot では **≥10 台**で臨界密度相当以上と集計）。jam-density 40 台に対し臨界密度 ≈ **23.0769% occupancy**。**90% occupancy = 36/40** は臨界密度を超える **強い滞留**。

**集計方針:** 臨界密度相当以上、50%、75%、90% を分離。**snapshot Vehicle 数のみ**で動的状態を完全断定しない。

**capacity_in/out 未指定時の診断上 UXsim 自動値:** ≈**1.538461538 台/s**（2×q_max）。trial は **明示設定していない**。

### 28.5 2.5台/timestep・新道路条件 pretrial（T=1,200）

**スクリプト:** `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial.py`

**出力:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial_seed_0_demand_seed_42`

**結果:** end 1,599 / run 1,400 / wait 1；内部 Link **1,331 台**、occupancy **0.27729166666666666**；外部→内部 connector **54 台**、occupancy **0.05625**；内部→外部 connector **15 台**、occupancy **0.015625**；全 Link **1,400 台**、occupancy **0.20833333333333334**。

**Link 閾値集計（T=1,200）:**

- **内部 Link:** 臨界密度相当以上 **46 本** / 50% 以上 **30 本** / 75% 以上 **19 本** / 90% 以上 **1 本** / 100% 以上 **0 本**
- **外部→内部 connector:** 臨界密度相当以上 **0 本** / 50% 以上 **0 本** / 75% 以上 **0 本** / 90% 以上 **0 本**
- **内部→外部 connector:** 臨界密度相当以上 **0 本** / 50% 以上 **0 本** / 75% 以上 **0 本** / 90% 以上 **0 本**

**整合:** 1,599 + 1,400 + 1 = 3,000；1,331 + 54 + 15 = 1,400（run 数＝全 Link 上 Vehicle 数）。

最大 Link **h_5_1_2** 0.9；exec **3.1263249160256237 s**；final 約 **17.6753 s**。

**解釈:** **入口余裕**（wait 1）を維持しながら **内部Link** に広範な混雑が形成された。**入口飽和・大量 wait なし**。**TVT-MP 評価期間**候補として有望 → **3 台/timestep** も比較。

### 28.6 3台/timestep条件を選ぶための需要設計

- 3,000 台を **1,000 simulation timestep**（時刻 0,1,…,999）へ投入：**departure T=0〜999**。
- 名目平均投入率 **3,000/1,000 = 3 台/timestep**。
- 24 外部 OD Node へ完全均等配分した場合の名目 **3/24 = 0.125 台/timestep・Node**（**実 OD は random sampling で非均等**）。
- **departure time は乱数抽選しない**。3,000 台を T=0 から T=999 まで等間隔配置。使用式:

```text
departure_time = DEPARTURE_START + (
    (DEPARTURE_END - DEPARTURE_START)
    * len(plans)
    / max(NUM_VEHICLES - 1, 1)
)
```

- 最初の Vehicle **0**、最後 **999**。隣接間隔 **999/2999 ≈ 0.33311 timestep**。
- OD 抽選順序・組合せ・seed・最小 Manhattan distance 等は維持。**T=0〜1,200 版**とは **vehicle_plan_sha256 不一致**。**T=999 pretrial** と **TMAX=5000 completion check** では **digest 一致**（§28.10）。

### 28.7 3台/timestep・T=999 pretrial

**スクリプト:** `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_evaluation_t999_pretrial.py`

**出力 directory:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_evaluation_t999_pretrial_seed_0_demand_seed_42`

**条件:** 3,000 台、departure T=0〜999、evaluation end **T=999**、TMAX=1,000、World.T=1,000、名目 **3 台/timestep**、全 Link **200 m**、**60 km/h**、**capacity_in/out 未指定**、**全車完走を要求しない**。

**結果（T=999）:**

- end **1,059** / run **1,940** / wait **1** / not completed **1,941**
- 平均速度（T=999 付近）**1.7 m/s**
- 内部 Link **1,731 台**、occupancy **0.360625**
- 外部→内部 **200 台**、occupancy **0.20833333333333334**
- 内部→外部 **9 台**、occupancy **0.009375**
- 全 Link **1,940 台**、occupancy **0.28869047619047616**
- **臨界密度以上:** 内部 **59** / 外部→内部 **9** / 全 **68**
- **50% 以上:** 内部 **44** / 外部→内部 **4** / 全 **48**
- **75% 以上:** 内部 **30** / 外部→内部 **0** / 全 **30**
- **90% 以上:** 内部 **5** / connector **0** / 全 **5**
- **100% 以上:** **0 本**

**上位 Link（例）:** h_0_5_4・v_3_2_0 **38 台（0.95）**；v_4_3_0・v_4_5_2 **37 台（0.925）**；v_5_4_2 **36 台（0.9）**；**0.875** の内部 Link 複数。

**実行時間:** exec_simulation **2.7421296659158543 s**；seconds_per_simulated_timestep **0.0027421296659158544**；final_script_total 約 **17.2802 s**。

**整合:** 1,059+1,940+1=3,000；1,731+200+9=1,940（run＝全 Link 上 Vehicle 数）。

**解釈（条件→結果）:**

- **2.5 台/timestep**（§28.5）より **内部Link混雑**が明確に強い（occupancy 0.361 vs 0.277）。
- **外部→内部 connector** にも混雑が現れたが **wait 1 台**。**入口外大量待機**ではない（connector **75%/90% 以上 0 本**）。
- 内部 120 本中 **59 本（≈49.2%）** が **臨界密度**相当以上；**44 本（≈36.7%）** が **50% 以上**；**30 本（25%）** が **75% 以上**；**5 本（≈4.2%）** が **90% 以上**。
- **100% Link**・**大量 wait** はなく、**強い混雑**だが network 破綻ではない。
- **TVT-MP** の交差点競合・順位交換を十分発生させうる **主たる需要候補**（§28.8）。

### 28.8 2.5台/timestep と 3台/timestep の比較

| 指標 | 2.5 台/timestep（T=1,200） | 3 台/timestep（T=999） |
|------|---------------------------|------------------------|
| end | 1,599 | 1,059 |
| run | 1,400 | 1,940 |
| wait | 1 | 1 |
| 内部 occupancy | 0.27729166666666666 | 0.360625 |
| 外部→内部 occupancy | 0.05625 | 0.20833333333333334 |
| 内部 臨界密度以上 | 46 本 | 59 本 |
| 外部→内部 臨界密度以上 | 0 本 | 9 本 |
| 全 Link 50% 以上 | 30 本 | 48 本 |
| 全 Link 75% 以上 | 19 本 | 30 本 |
| 全 Link 90% 以上 | 1 本 | 5 本 |
| 全 Link 100% 以上 | 0 本 | 0 本 |

**留保:** **2.5 台/timestep** は **T=1,200**、**3 台/timestep** は **T=999** という、それぞれの **departure 終了時点**の比較である。**同一絶対時刻**の比較ではない。今回の目的は投入終了時の network 蓄積状態を比較することなので、この比較目的には適合する。**正式な旅行時間・性能優劣比較には使用しない**。

**判断:** **3 台/timestep** を主候補；**2.5** は感度分析；**5,000 集中**はストレス；需要分類名 **未確定**（**強い混雑**は明記）。

### 28.9 TMAX=5000 FCFS完走確認 trial

**スクリプト:** `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check.py`

**出力 directory:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check_seed_0_demand_seed_42`

**目的:** T=999 の departure 終了 snapshot は **既存 T=999 pretrial 出力を正本**（**再取得・分割 exec・hook なし**）。**1 回**の `exec_simulation()` で **T=0〜4,999** を実行し、**全車正常完走成否**と **最終完走時刻**を測定。**TVT-MP 性能比較ではない**。

**固定条件:** departure T=0〜999、TMAX=**5,000**、final observation **T=4,999**、World.T=**5,000**；Vehicle plan は T=999 pretrial と同一；200 m / 60 km/h；**capacity_in/out 未指定**。

**production 原典（正常完走）:** `state=="end"` かつ `arrival_time≥0`（timestep 整数）。**abort**（`arrival_time=-1`）は完走に含めない。`exec_simulation` は **TSIZE−1 まで進行**（早期終了しない）。

**結果（T=4,999）:**

- state **end 3,000**；normally completed **3,000**；not normally completed **0**
- all_vehicles_normally_completed_by_final_observation=**True**
- completion_status=**all_vehicles_normally_completed_by_t4999**
- latest_observed_completion_timestep=**last_vehicle_completion_timestep=2,296**
- post_departure_clearance_timesteps=**2,296−999=1,297**
- last_completion_vehicle_count=**1**；last completion vehicle=**veh_2818**
- abort_count=**0**
- 全 Link 上 Vehicle **0**（内部・connector 各 0）；**臨界密度以上・50%/75%/90%/100% 以上すべて 0 本**

**実行時間:** exec_simulation **5.314151040976867 s**；seconds_per_simulated_timestep **0.0010628302081953733**；final_script_total 約 **20.2047 s**。

**進行（コンソール目安）:** T=600: 1,205 台・1.7 m/s；T=1,200: 1,680 台・1.5 m/s；T=1,800: 522 台・4.3 m/s；T=2,400 表示 0 台—**実最終完走 T=2,296**；T=2,297〜4,999 は **空 network** を進行。

### 28.10 Vehicle plan 同一性

**SHA-256:** `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`（T=999 pretrial ≡ completion check）。

### 28.11 現時点の正式な設計判断

**採用候補（将来の 3,000 台 TVT-MP trial の需要・道路）:** 3,000 台、departure **T=0〜999**、名目 **3 台/timestep**（24 外部 OD 完全均等仮定 **0.125 台/timestep・Node**、**実配分非均等**）、全 Link **200 m**、**60 km/h**、κ=0.2、τ=1、**capacity_in/out 未指定**、単車線、merge priority 1、min OD Manhattan distance 5、free route choice、random seed 0 / demand generation seed 42。

**FCFS 事前検証と将来 TVT-MP 制御の区別:**

- 今回の **4 本の FCFS 事前 trial** では、内部 **36 Node** を **FCFS**、**clearance 1** として、上記 **道路・需要条件**下の交通状態と **FCFS 完走時刻**（§28.9）を実測した。
- **将来の 3,000 台 TVT-MP trial** では、内部 **36 Node** を **TVT-MP 制御対象**とする候補である。**TVT-MP でも clearance 1 を維持する候補**である。
- **3,000 台 TVT-MP 本体**は **未作成・未実行**である。**正式 evaluation end**、**internal TSIZE**、**VOT 付与**、**VOT seed** は **未決定**である。
- **FCFS による事前検証で道路・需要条件を選定したこと**は、将来の TVT-MP trial でも **内部 36 Node を FCFS にする**という意味 **ではない**。

**需要の位置づけ:** **3 台/timestep** を **主候補**；**2.5 台/timestep** は **感度分析候補**；**5,000 台集中**は **ストレス条件**；**通常需要/準高需要/高需要** の名称は **未確定**（**強い混雑**は明記）。**3,000 台 TVT-MP 本体は未作成・未実行**。

**道路:** **1,500 台/h** を Link 境界へ **設定しない**。FD 容量 ≈**0.76923 台/s**。実 network 処理能力は Node 競合・clearance・下流空間・経路集中等を含み **FD 容量そのものと一致しない**。**1,500 台/h** は **参考値**として残す。

### 28.12 TVT-MP 評価期間への含意

- FCFS **最終完走 T=2,296**。departure 終了 **T=999** から **1,297 timestep** で交通解消。
- 将来 **TVT-MP evaluation end** は **少なくとも T=2,296 を考慮**する必要がある。
- **FCFS 最終完走時刻を evaluation end へそのまま採用しない**（TVT-MP では順位変更・乱数消費順・baseline/candidate・通過時刻が変わり得る）。
- **baseline horizon 30** と評価余裕を要検討。
- **3,000 台・強混雑**を T=2,296 以上まで **TVT-MP 全実行**するのは **高リスク**（§27: 1,000 台 TVT-MP 1,000 timestep 約 **7,620 s**、5,000 台 TVT-MP T=599 約 **79,685 s**）。
- **profiling** または **短期 benchmark** を先行する可能性が高い。**正式 evaluation end / internal TSIZE は未決定**。**3,000 台 TVT-MP 本体へ自動進行しない**。

### 28.13 実装・検証中に修正した軽微事項

- 200 m / 60 km/h 版 **static validation** に旧契約値（400 m / 300 m 等）が一部残っていたため、**200 m 契約へ限定修正**した。
- `_critical_density_vehicle_count_for_length` が同一内容で **重複定義**されていたため、**1 定義へ整理**した。
- 説明文 **空白欠落**（whenall、link).It、singleexec_simulation、400 m/ 300 m、all_vehicles_normally_completed_by_final_observationis False）を **スクリプト側で限定修正**した。
- static validation の **禁止文字列検査**が検査コード自身を **自己検出**したため、禁止パターンを **実行時 `+` 連結**で組み立てる方式へ修正した。
- これらは **説明文または検証コードの修正**であり、**既に生成済みの数値結果**、Vehicle plan、Link 集計、**最終完走時刻**には影響しない。
- **既存出力**は実行証跡として **変更・再生成していない**。
- completion-check 等のスクリプト修正後、**py_compile は通過**した（作業ログ上）。
- **既存出力 directory がある**ため、修正後の **static validation** は **上書き防止契約**との衝突を避けて **再実行していない場合がある**。
- 各 trial は **実行前**の static validation を通過している。

### 28.14 出力ファイルと再開時参照先

**スクリプト:**

1. `research_scripts/run_fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial.py`
2. `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial.py`
3. `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_evaluation_t999_pretrial.py`
4. `research_scripts/run_fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check.py`

**主要出力 directory（`research_outputs/trial/` 配下）:**

- `fcfs_6x6_grid_3000_vehicle_departure_1200_evaluation_t1200_pretrial_seed_0_demand_seed_42`
- `fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_1200_evaluation_t1200_pretrial_seed_0_demand_seed_42`
- `fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_evaluation_t999_pretrial_seed_0_demand_seed_42`
- `fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check_seed_0_demand_seed_42`

**各 directory 主要ファイル:** `link_occupancy_at_t*.csv`、`vehicle_state_summary.csv`、`vehicle_plan_audit.json`、`manifest.json`、`run_summary.txt`

### 28.15 未完了事項と次の作業

**未作成・未実行:** 3,000 台 **TVT-MP 本体** trial、3,000 台 **TVT-MP 短期 benchmark**、3,000 台条件の **TVT-MP profiling**、**正式 evaluation end**、**正式 internal TSIZE**、TVT-MP 用 **VOT 付与と VOT seed 確認**、TVT-MP 出力、3,000 台条件の TVT-MP 結果、**複数 seed** 検証。

**次の作業:** 3,000 台 TVT-MP 本体へ **直進しない**。先に **計算量 profile** か **短期 benchmark** かを **利用者判断**する。判断材料: FCFS **最終完走 T=2,296**、T=999 時 **run 1,940 台**、内部 Link **59 本**が **臨界密度**以上、全 Link **90% 以上 5 本**、§27 の **1,000 台 TVT-MP 1,000 timestep 約 7,620 s**、**5,000 台 TVT-MP T=599 約 79,685 s**。**production 最適化・arrival tiebreaker 改修・乱数源分離へ自動進行しない**。

**利用者へ明示する判断:** profiling 先行か／短期 benchmark の evaluation end／正式 TVT-MP evaluation end／internal TSIZE／全車完走 trial か限定 benchmark か／baseline horizon 30 を含む余裕／複数 seed のタイミング。

**歴史的注記（§28 執筆時点の未完了記述との関係）:** 上記 §28.11・§28.15 は **2026-11-01 前半**（FCFS 需要選定完了時点）の記録である。**その後**、§28 で採用候補とした 3,000 台・departure T=0〜999・全 Link 200 m・60 km/h・capacity_in/out 未指定条件について、3,000 台 **TVT-MP** の短期 benchmark、profiling、Candidate **共有直列化** production 最適化、最適化前後 **完全一致**再検証まで実施した。**最新の設計正本は §29**（本 §28 の過去記録は削除・改番しない）。

---

## 29. 3,000台TVT-MP計算量診断とCandidate共有直列化production最適化（2026-11-01）

**検索語（本 §29 へ到達するための目安）:** 3,000台TVT-MP、短期benchmark、T=0〜299、profiling、T=96、World.copy、dill、pickle、直列化、復元、Candidate局所仮想計算、FIFO True候補、共有直列化、Candidate独立性、RNG不変、production最適化、完全一致、CSV完全一致、3.84倍、73.98%削減、816取引、200m Link、60km/h、N=10、baseline horizon 30、計算時間短縮、ボトルネック、Python可読性。

### 29.1 作業の目的と位置づけ

- §28 で採用候補とした **3,000 台**、departure **T=0〜999**、全 Link **200 m**、**60 km/h**、**capacity_in/out 未指定**の条件について、3,000 台 **TVT-MP 本体**（長期 evaluation）へ **直進せず**、通常実行の **短期 benchmark** を先行した。
- **profiling** とは「**なぜ重いか**を調べる診断」、**短期 benchmark** とは「**どの程度重いか**を通常 `exec_simulation` で測る trial」と区別した。
- 最初に **通常実行**で計算規模を測り、重いことが確認された場合 **だけ**、最短範囲の profiling へ進む方針を採用した。
- 今回の系列は **研究評価（TVT-MP の優劣断定）** ではなく、長時間 trial を **現実的な wall-clock** で実行できるようにするための **計算量診断・production 最適化**である。
- 既存 production を **推測で**最適化せず、**通常 benchmark → 単一 timestep profiling → 共有直列化 A/B 診断 → production 実装 → 関連 test → T=0〜299 全体再検証 → CSV 独立比較**の順で進めた。
- **Python 初心者**が後から **処理順**（入力検証 → 直列化 → 復元 → 局所状態構築 → 局所仮想計算）を追える **可読性**を必須条件とし、高度で巧妙な短縮実装や **暗黙的 cache**（global cache、World 属性 cache、timestep またぎ cache）は採用しなかった。

### 29.2 最適化前T=0〜299短期benchmark

**スクリプト:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark.py`

**scenario / 出力 directory:** `tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark_candidate_limit_10_seed_0_vot_seed_1`（`research_outputs/trial/` 配下）

**条件（§28 採用候補道路・需要に TVT-MP 制御・VOT を付与）:**

| 項目 | 値 |
|------|-----|
| Vehicle 数 | 3,000 台 |
| departure | T=0〜999（名目 **3 台/timestep**） |
| demand generation seed | 42 |
| traffic seed | 0 |
| VOT seed | 1 |
| 全車参加 | はい |
| true VOT = declared VOT | はい |
| evaluation | **T=0〜299** |
| simulated evaluation timestep 数 | **300** |
| baseline horizon steps | **30** |
| internal TSIZE | **330** |
| simulation 後 World.T | **300** |
| Link | 全 **168** 本 **200 m** |
| free-flow speed | **60 km/h**（16.666… m/s） |
| jam density | **0.2 台/m** |
| reaction time | **1 s** |
| capacity_in / capacity_out | **未指定** |
| TVT-MP 対象 | 内部 **36 Node** のみ |
| clearance | **1** |
| Candidate Visit 数上限 **N** | **10** |
| 経路 | free route choice、specified_route 不使用 |
| Python recursion limit | **50,000** |
| profiling | **なし** |
| `world.exec_simulation()` | **1 回** |
| 全車完走 | **要求しない** |
| transaction_count ≥ 1 | **一般契約として要求しない** |

**結果（構造化集計・manifest 正本）:**

- **transactions:** **816** 件
- **Vehicle state:** end **318** / home **2,099** / run **580** / wait **3**（合計 **3,000**）
- **completed:** 318 / **not completed:** 2,682
- **scheduled departure reached:** **898** / **not reached:** **2,102**
- **vehicles on network（run/wait）:** **583**
- **internal Link 上 Vehicle:** **517** / **OD connector 上 Vehicle:** **63**
- **Link 上 Vehicle 合計 517+63=580** は **run** 数と一致（wait **3** は Link 上に載らない）
- **exec_simulation_seconds:** **6295.571890000021**
- **seconds_per_evaluation_timestep:** **20.985239633333403**
- **final_script_total_seconds:** **6310.222256791894**
- **output directory total bytes:** **1,613,662**
- **wall-clock 目安:** T=0〜299 のみで約 **1 時間 44 分 56 秒**
- 既存 **1,000 台** TVT-MP benchmark の 1 timestep 当たり時間に対し **per_timestep_runtime_ratio ≈ 2.7539**（参考比較。厳密なスケーリング法則ではない）

**Vehicle plan digest（SHA-256）:** `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`

- **FCFS** T=999 pretrial / TMAX=5000 completion check（§28.10）と **完全一致**した。
- Vehicle 数、departure time、OD 生成順序、Origin、Destination、demand seed、生成式が同一である。
- FCFS 出力には **VOT がない**ため、FCFS との比較は **Vehicle plan digest** に限定する。

**解釈（条件→結果→判断）:**

- T=0〜299 は departure T=999 までの **交通立ち上がり期間**であり、T=999 付近の **強混雑**を代表 **しない**（§28.7 の T=999 snapshot とは別段階）。
- それでも約 **1 時間 45 分**を要したため、T=599、T=999、T=2,296 以上へ **直進**するのは **高リスク**と判断した。
- **単純比例**による長期実行時間の断定は **禁止**した（§27・§28.12 と整合）。

### 29.3 progress表示の留保

- 初回 benchmark では **`show_progress_deltat=100`** を設定した。
- UXsim の progress 設定は **実 World** だけでなく、Baseline / Candidate 用に **複製された仮想 World** にも引き継がれ、同じ **T=100、T=200、T=300** の表示が **多数**出た。
- これは **実 World** が同一時刻で停止したことを意味 **せず**、**複数の仮想 World** が同じ表示時刻へ到達したためである（表示回数 ≈ 実 World 1 回 + 当該 timestep の Baseline/Candidate 複製数に比例しうる）。
- 表示された **computation time** は UXsim 内部の累積情報であり、**正式な区間別 timing** ではない。
- 後の **再検証 trial**（§29.10）では **`show_progress_deltat=600`** へ戻した（evaluation T=0〜299 では通常 **T=0** と **終了時**のみの表示）。**交通・TVT-MP 条件は同一**で、**進捗表示量だけ**の変更である。
- **`INTERVAL_TIMING_AVAILABLE=False`** を維持した。
- **`exec_simulation` 分割**、**user_function**、**hook**、**per-timestep timing CSV** は **追加していない**。

### 29.4 departure分類898台と実状態901台の差

**現象:**

- **`scheduled_departure_reached_count`** は Vehicle plan 上の連続 **`departure_time`** について **`departure_time <= 299`** を判定し、**898** 台だった。
- **実状態**では **end + run + wait = 318 + 580 + 3 = 901** 台が evaluation end 時点で **home 以外の進行状態**（end/run/wait）または **network 関連状態**として観測される（reached 定義は **plan 上の連続値**、実状態集計は **UXsim state**）。

**差の 3 台（plan departure_time）:**

| Vehicle | departure_time（plan 連続値） |
|---------|-------------------------------|
| veh_898 | 299.133711237079 |
| veh_899 | 299.4668222740914 |
| veh_900 | 299.7999333111037 |

**原因（処理順・production 原典）:**

- UXsim production では **`departure_time_is_time_step` が False** の場合、実 World の departure timestep は
  **`int(departure_time / DELTAT)`**
  により **切り捨て**られる。
- **`DELTAT=1`** なので上記 3 台は plan 上は **> 299** だが、実 World では **departure timestep 299** となり、**T=299** で home から **wait** へ移った（§29.2 の wait **3** と整合）。

**結論:**

- **898 対 901** は **不整合ではなく**、
  - **Vehicle plan 上の連続値分類**（`departure_time <= EVALUATION_END_TIMESTEP`）
  - **UXsim 内部の整数 departure timestep**
  の **定義差**である。
- **`scheduled_departure_reached_count`** は **実際に network へ進入した台数**を **直接意味しない**。
- **実状態の評価**には **`vehicle_state_counts`**、Link 上 Vehicle 数、completed 等を用いる。
- **production** および **Vehicle plan 生成式**は **変更していない**。

### 29.5 最短profiling設計

**診断スクリプト:** `diagnostics/order_control/tvt_mp_3000_vehicle_t96_single_timestep_profile.py`

**出力 directory:** `research_outputs/diagnostic/tvt_mp_3000_vehicle_t96_single_timestep_profile_seed_0_vot_seed_1`

**設計方針:**

- 過去に **全 World baseline 基盤**の profiling 実績があったが、**現在の TVT-MP 全体**（Candidate 局所仮想計算・FIFO 検査・N=10 等）を網羅したもの **ではなかった**。
- 過去 profiling を **全面レビュー**するのではなく、**既知の cProfile 測定方法だけ**を再利用し、**現在の TVT-MP** を **最短範囲**で profile した。
- 既存 **816 取引**について、**単一 timestep** で取引数が最多だった **T=96** の **8 取引**を **代表時刻**とした。
- **T=0〜95** は profiler **なし**で通常実行。
- **T=96 の 1 timestep だけ**を **cProfile** で囲んだ。
- **T=0〜99 全体**、**T=0〜299 全体**を profile **しなかった**（wall-clock の総量推定に cProfile 秒数を **使わない**方針）。
- **cProfile の秒数自体**は通常性能値として **使わず**、**累積時間（cumtime）** と **自己時間（tottime）** の **主要因特定**だけを使用した。

**profiling 結果（T=96 の 1 timestep、cProfile 全体）:**

| 項目 | 値 |
|------|-----|
| cProfile 計測区間 wall-clock 目安 | **126.189 s**（**T=0〜299 全体の exec 時間ではない**） |
| function calls | **642,089,037** calls（**545,284,990** primitive calls） |
| `run_tvt_mp_driver` | 約 **126.155 s**（支配） |
| **`World.copy()`** | **18 回**、累積約 **125.663 s** |
| **`dill.dumps()`** | **18 回**、累積約 **124.324 s** |
| **`dill.loads()`** | **18 回**、累積約 **1.331 s** |
| Baseline fork | **`World.copy()` 1 回**、累積約 **7.22 s** |
| Candidate **局所状態構築** | **17 Candidate**、累積約 **118.72 s** |
| Candidate **局所仮想前進** | **17 Candidate**、**215** virtual timestep、累積約 **0.198 s** |
| Vehicle.update、Node.transfer、route 処理、経済評価等 | **支配的でなかった** |

**結論（ボトルネック）:**

- 当該 timestep における CPU 時間の **ほぼ全体**が、**Candidate ごとの全 World 複製**に伴う **`dill` 直列化（dumps）** へ集中していた。
- **Candidate 仮想交通計算そのもの**は **非常に軽かった**。
- 最適化対象は **Candidate 数削減**、**horizon 短縮**、**取引ロジック** **ではなく**、**同一 real World snapshot の重複 `dill.dumps`** であると **確定**した。

### 29.6 FIFO True Candidateの意味

- **FIFO True Candidate** とは、同一 inlink 内の **物理的な先後関係を壊さず**、**Candidate 局所仮想計算**へ進める候補である。
- **FIFO False Candidate** は、同一 inlink 内の **追越し**等を生じうるため、重い **局所仮想計算**へ **進めない**（production の FIFO 検査契約）。
- **T=96** では **FIFO True Candidate が 17 件**存在した（profiling 時の inspection set）。
- **従来（最適化前）**は、この **17 件それぞれ**について **全 World** の **`dill.dumps` + `dill.loads`**（実装経路では **`World.copy()`** 起点）を行っていた。

### 29.7 共有直列化A/B診断

**診断スクリプト:** `diagnostics/order_control/tvt_mp_candidate_shared_serialization_ab.py`

**出力 directory:** `research_outputs/diagnostic/tvt_mp_candidate_shared_serialization_ab_seed_0_vot_seed_1_t96`

**比較方式:**

| 方式 | 内容 |
|------|------|
| **A（現行方式）** | FIFO True Candidate **ごと**に **`World.copy()`** → Candidate **ごと**に **`dill.dumps` + `dill.loads`** 相当 |
| **B（共有直列化）** | Candidate 集合の開始時に **`dill.dumps(real_W)` を 1 回** → Candidate **ごと**に **同じ bytes** から **`dill.loads`** → 各 Candidate は **独立した local World**（**local World 自体は共有しない**） |

**公正性（A/B 同一前提）:**

- 同じ **real_W snapshot**、同じ **FIFO inspection set**、同じ **rank state**、同じ **baseline fork result**
- **A→B** と **B→A** の **両順序**で実行
- 各条件前に **`gc.collect()`**
- **cProfile なし**、**production 未変更**（診断内のみ）

**wall-clock 結果（Candidate 局所状態構築部分の比較）:**

| round | A (s) | B (s) | speedup (A/B) | 短縮 (s) |
|-------|-------|-------|---------------|----------|
| 1 | 25.468520540976897 | 3.2518680000212044 | **7.831966285473711** | 22.216652540955693 |
| 2 | 25.87662420910783 | 3.1868181669851765 | **8.119893528028891** | 22.689806042122655 |
| **平均** | **25.672572375042364** | **3.2193430835031904** | **7.9744754470549495** | — |

**B 内訳（参考）:**

- **1 回の dumps:** round1 **1.3902505000587553 s** / round2 **1.4084241670789197 s**
- **17 回の loads:** round1 **1.7823060839436948 s** / round2 **1.7016391650540754 s**

**正確性（A/B 一致監査）:**

- **Candidate 結果完全一致**、**first difference なし**
- **17 local World** すべて **real_W と別 object**
- Candidate 間で **World、Node、Link、Vehicle、registry** が **別 object**、**mutation 漏れなし**
- **real_W 不変**、**traffic RNG 不変**、**order-control RNG 不変**、**shared bytes 不変**
- **A** は **17 dumps + 17 loads** 相当、**B** は **1 dumps + 17 loads**
- 判定: **`promising_for_production_design_review`**、`shared_serialization_candidate_is_promising=True`

**数値の混同禁止:** 本節の **約 7.97 倍**は **T=96・Candidate 集合部分**の A/B。**T=0〜299 全体**の通常 exec 短縮（§29.10 の **約 3.84 倍**）とは **別尺度**である。

### 29.8 production実装

**変更 production（本最適化の範囲）:**

1. `uxsim/order_control_tvt_mp_candidate_local_state.py`
2. `uxsim/order_control_tvt_mp_local_virtual_calculation_set.py`

**追加した主要関数（明示的 API）:**

- **`serialize_tvt_mp_candidate_real_world_snapshot(real_W)`** — real World を **1 回** `dill.dumps` し **bytes** を返す（入力検証付き）
- **`build_tvt_mp_candidate_local_state_from_serialized_world(...)`** — **同じ bytes** から **1 回** `pickle.loads` し、**独立 local World** 上で Candidate 局所状態を構築
- 共通 **private helper**（入力検証、独立 local World 確認、copy または restore 済み World から Candidate 局所状態を生成）

**処理順（`evaluate_tvt_mp_candidate_local_virtual_calculations` 内）:**

1. **real_W**、FIFO 結果、rank state、baseline 整合を **検証**
2. **FIFO True Candidate が 1 件以上**ある場合 **だけ** **real_W を 1 回 `dill.dumps`**
3. serialized **bytes** を **evaluate 関数の local 変数**として保持（**global / World 属性に置かない**）
4. **Node 順・Candidate 順**を **従来どおり**走査
5. **FIFO True Candidate ごと**に **`pickle.loads` を 1 回**
6. Candidate **ごと**に **独立 local World** を生成
7. **従来と同じ helper**、**局所仮想計算**、**結果生成**を実行
8. **evaluate 呼出し終了時**に bytes を **持ち越さない**（次 timestep へ cache しない）

**明記（変更しないもの・直列化しない条件）:**

- **FIFO True Candidate 0 件**では **直列化しない**
- **normal-not-generated** では **直列化しない**
- **FIFO False Candidate だけ**なら **直列化しない**
- **global cache なし**、**World 属性 cache なし**、**timestep またぎ cache なし**、**Candidate 間 local World 共有なし**
- **`World.copy()` 自体**は **変更していない**（単独 builder・baseline fork は従来経路）
- **baseline World copy**は **変更していない**
- 単独呼出しの既存 **`build_tvt_mp_candidate_local_state()`** は **従来どおり `World.copy()` を 1 回**行う
- **Candidate 形成、FIFO 検査、N、horizon、経済評価、rank、passage、RNG 処理**は **変更していない**

**Python 可読性（設計制約）:**

- bytes **生成位置**、**使用範囲**、**loads 位置**を **名前付き関数**と **中間変数**で明示
- 高度な cache class、descriptor、暗黙的状態共有を **使用していない**

### 29.9 production test

**変更 test:**

1. `tests_order_control_tvt_mp_candidate_local_state.py`
2. `tests_order_control_tvt_mp_local_virtual_calculation_set.py`

**追加・更新した主な検証:**

- serialize が **bytes** を返す；**real_W・traffic RNG・order-control RNG 不変**
- **同じ bytes から 2 回復元**した World が **独立**（Node、Link、Vehicle、registry **別 object**、**mutation 非漏洩**）
- **real vehicle ID 写像一致**、**bytes 不変**、**非 bytes 拒否**、**stale timestep** は loads 前に拒否
- **既存 copy builder 互換性**
- **FIFO True 2 件** → serialize **1 回**、復元 **2 回**；**FIFO True 1 + False 1** → 復元 **1 回**；**FIFO True 0 件** → serialize **なし**；**normal-not-generated** → serialize **なし**
- **2 件目 Candidate 例外**時も **1 件目 local World** と **real_W** を維持
- **Node 順・Candidate 順・identity 順**、resolved/unresolved mix **維持**

**実行結果（作業ログ上、関連 suite）:**

| test モジュール | 結果 |
|----------------|------|
| Candidate local state | **25 passed** |
| Candidate local calculation set | **41 passed** |
| Candidate local virtual calculation | **90 passed** |
| Candidate outlink boundary | **22 passed** |
| Candidate unbound FCFS transfer | **28 passed** |
| Candidate virtual time | **13 passed** |
| TVT-MP driver | **31 passed** |
| **関連合計** | **250 passed** |

- 同じ主要 test 2 本を **誤って 2 回**実行したが、**2 回とも成功**した。
- その後、test 結果文字列を Terminal へ **貼り付け**たため **zsh** が `PASS` 等を **コマンド**として解釈したが、**コード、test 結果、Git 状態**には **影響しなかった**（作業ログ）。

### 29.10 最適化後T=0〜299全体再検証

**スクリプト:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation.py`

**scenario / 出力 directory:** `tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation_candidate_limit_10_seed_0_vot_seed_1`

**条件:**

- **最適化前 benchmark（§29.2）と同一**（道路・需要・VOT・N=10・baseline horizon 30・evaluation T=0〜299 等）
- **`show_progress_deltat` のみ 100 → 600**（§29.3）。**交通・TVT-MP 条件は同一**
- **profiling なし**、**`exec_simulation` 1 回**
- 最適化前結果は **スクリプト内定数 `REFERENCE_PRE_OPTIMIZATION_BENCHMARK`** と比較（**既存 output を runtime 読込みしない**）

**研究結果（構造化集計・一致判定）:**

- **transactions 816**
- **state:** end 318 / home 2,099 / run 580 / wait 3
- **scheduled reached 898** / **not reached 2,102**
- **internal Link Vehicle 517** / **OD connector Vehicle 63**
- **Vehicle plan digest 一致**
- **`research_result_equality_checks passed=True`**

**性能（T=0〜299 全体・通常 exec、同一 Mac 上の 2 回実行比較）:**

| 指標 | 最適化前 | 最適化後 |
|------|----------|----------|
| exec_simulation (s) | **6295.571890000021** | **1637.9535257919924** |
| seconds / eval timestep | **20.985239633333403** | **5.459845085973308** |
| final_script_total (s) | **6310.222256791894** | **1652.2862650000025** |

- **speedup（reference/current）:** **3.8435595338127504** 倍
- **短縮:** **4657.618364208029 s**（約 **77 分 38 秒**）
- **runtime reduction:** **73.9824506111392%**
- **wall-clock 目安（最適化後）:** 約 **27 分 18 秒**

**正確性を維持できる理由（要約）:** 各 FIFO True Candidate は **従来と同様に独立 local World** を **`loads` で復元**するだけであり、**real_W snapshot の bytes 化を 1 回に集約**した。**Candidate 形成・FIFO・経済・rank・RNG** は未変更。**A/B** と **250 test** と **本再検証**で一致を確認（§29.11 参照）。

### 29.11 CSV全内容の独立完全一致確認

**方法:** スクリプト内の構造化 equality に加え、**Terminal 上**で最適化前後の出力 CSV を **独立比較**した（**scenario_name 列のみ除外**、**行順維持**、それ以外の **全列・全行 exact equality**）。

| ファイル | 行数（前/後） | 比較結果 |
|----------|---------------|----------|
| `tvt_mp_transactions.csv` | 816 / 816 | **完全一致** |
| `tvt_mp_visits.csv` | 1,927 / 1,927 | **完全一致** |
| `tvt_mp_vehicles.csv` | 877 / 877 | **完全一致** |
| `tvt_mp_nodes.csv` | 36 / 36 | **完全一致** |
| `tvt_mp_scenario.csv` | 1 / 1 | **完全一致** |
| `vehicle_vot.csv` | 3,000 / 3,000 | **完全一致** |

**結論:** **`all normalized CSV contents identical=True`**

したがって、**取引・Visit・Vehicle・Node・scenario 集計・VOT** の研究出力 **内容**が最適化前後で **完全一致**した（**ファイル全体 SHA-256** は scenario_name を含むため **一致を要求しない**）。

### 29.12 正確性の最終判断

- **共有直列化 production 最適化**は、**現在の検証範囲**で **研究結果を変更しない**。
- **同一 real_W snapshot** の **重複 `dill.dumps`** を **1 回**へ集約しただけであり、各 Candidate は **従来どおり独立 World** を **`loads` で得る**。
- **T=96 A/B** を **A→B、B→A** 両順序で実行し、**完全一致**した（§29.7）。
- **Candidate 独立性、real_W 不変、両 RNG 不変**を確認した。
- **関連 test 250 件**が成功した（§29.9）。
- **T=0〜299 通常実行**で **主要集計**が一致した（§29.10）。
- **6 種類 CSV** について **scenario_name 以外**の **全行・全列**が完全一致した（§29.11）。
- 以上により、**追加の同規模完全一致 trial を直ちに要求せず**、**production 最適化を受入れてよい**と判断した。
- **将来の長期 trial** や **別 seed** 結果は **追加の回帰確認**として利用 **できる**が、**今回の実装受入れの前提**とは **しない**。

### 29.13 残る留保

- **性能値**は **同じ Mac 上**の **2 回の通常実行**比較であり、**外部負荷**や **OS 状態**の影響を **完全には除外していない**。
- ただし **約 3.84 倍**、**73.98% 削減**という差は **大きく**、**profiling**（§29.5）および **A/B 診断**（§29.7、**約 7.97 倍**は **T=96 部分**）の **原因分析**とも **整合**する。
- **T=0〜299** は **交通立ち上がり期間**であり、T=999 付近や **交通解消まで**の計算時間を **代表しない**。
- 最適化後でも T=0〜299 に **約 27 分**かかる。
- **T=999** や **T=2,296** までの実行時間を **単純比例で断定しない**。
- **Baseline World copy** は **今回の最適化対象外**（§29.5 profiling で Baseline 約 7.22 s は残存しうる）。
- Candidate **1 件**の場合も **dumps 1 回・loads 1 回**で、従来の **copy 1 回**と **ほぼ同等の構造**である。
- **FIFO True Candidate が多い**意思決定ほど **短縮効果が大きい**。
- **shared bytes** の **memory 使用量**は今回の **主要課題ではない**が、**長期 trial** で **memory pressure** が生じないかは **実行時に観察可能**。
- production の **他の最適化**、**最小局所 World 構築**、**近似化**、**Candidate 削減**、**N 変更**は **行っていない**。

### 29.14 作成・変更したファイル

**新規 research scripts:**

1. `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark.py`
2. `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation.py`

**新規 diagnostics:**

1. `diagnostics/order_control/tvt_mp_3000_vehicle_t96_single_timestep_profile.py`
2. `diagnostics/order_control/tvt_mp_candidate_shared_serialization_ab.py`

**変更 production:**

1. `uxsim/order_control_tvt_mp_candidate_local_state.py`
2. `uxsim/order_control_tvt_mp_local_virtual_calculation_set.py`

**変更 test:**

1. `tests_order_control_tvt_mp_candidate_local_state.py`
2. `tests_order_control_tvt_mp_local_virtual_calculation_set.py`

**主要出力 directory:**

- `research_outputs/trial/tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_short_benchmark_candidate_limit_10_seed_0_vot_seed_1`
- `research_outputs/diagnostic/tvt_mp_3000_vehicle_t96_single_timestep_profile_seed_0_vot_seed_1`
- `research_outputs/diagnostic/tvt_mp_candidate_shared_serialization_ab_seed_0_vot_seed_1_t96`
- `research_outputs/trial/tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_300_timestep_shared_serialization_validation_candidate_limit_10_seed_0_vot_seed_1`

**失敗履歴（診断のみ）:**

- **A/B 診断初回**は **`infer_order_control_eligible_nodes()` 欠落**により **`g_0_0` が `eligible=False`** として停止した。
- 原因確認後、**全 Link 作成後・`set_order_control_for_nodes` 前**に **`infer_order_control_eligible_nodes()`** を **追加**した。
- 失敗時 output directory は Terminal で内容確認後 **削除**し、**再実行**した。
- **production 結果**には **影響しない**（診断スクリプト修正のみ）。

### 29.15 現時点の確定事項と次の作業

**確定事項:**

- **共有直列化 production 最適化**は **受入れてよい**（§29.12）。
- **T=0〜299** で **研究結果完全一致**（§29.10・§29.11）。
- **通常実行** 約 **3.8435595338127504 倍**高速化、実行時間 **約 73.9824506111392% 削減**（**T=0〜299 全体**）。
- **profiling** や **A/B 診断**の **追加反復は不要**（原因特定・promising 判定済み）。
- **同じ完全一致 trial をもう 1 回直ちに行う必要はない**。

**次の作業:**

- 今回の **script、diagnostic、production、test、出力、メモ**を **commit・push** する（進捗 **§18.11**）。
- その後、**最適化後の計算時間**を前提に、**3,000 台 TVT-MP** の **次の実行範囲**を **利用者判断**する。
- **T=599**、**T=999**、**正式 evaluation end**、**internal TSIZE**、**全車完走 trial** のいずれへ進むかは **未決定**。
- **FCFS 最終完走 T=2,296** を **TVT-MP evaluation end へ自動採用しない**（§28.12 維持）。
- **長期 trial** へ進む前に、最適化後の **T=0〜299 実績 5.459845085973308 s/timestep** と、**後半混雑**による **非線形増加**可能性を考慮する。
- **追加の production 高速化**へ **自動的に進まない**。
- **arrival tiebreaker**、**乱数源分離**、**Candidate 削減**、**近似化**へ **自動的に進まない**。
- **次の重要判断**は、**正式な 3,000 台 TVT-MP をどこまで実行するか**である。

**歴史的注記（§29.15 執筆時点との関係）:** 上記 §29.15 の「次の作業」（commit・push、evaluation end 未決定等）は **2026-11-01 後半**（共有直列化受入れ・T=0〜299 完全一致時点）の記録である。**その後**、3,000 台 **departure-end observation trial（T=999）**、正式 CSV の **横並び事後監査不足**の確認、**production 大規模監査拡張案の不採用**、**full-run audit helper** の新規作成と **12 台 / 600 台 20% nonparticipating** 検証、**3,000 台・20% nonparticipating・全車完走・交通解消** 長期本番スクリプト作成まで進んだ。**最新の設計正本は §30**（本 §29 の過去記録は削除・改番しない）。

---

## 30. 長時間trialの事後監査出力とfull-run audit helper（2026-11-02）

**検索語（本 §30 へ到達するための目安）:** 横並び表示、事後分析、監査出力、長時間trial、full-run audit helper、同一inlink、到着時刻、actual node arrival、baseline arrival、局所順位、baseline local rank、post-trade local rank、Node累積連続順位、assigned rank、actual node passage rank、binding sequence auxiliary rank、経済条件、G_b、R_s、P_b、C_s、nonparticipating 20%、全車完走、交通解消、T=999、departure-end、3,000台、production監査拡張不採用、diagnostic再利用、inlink_name、FIFO、same-inlink、safety cap T=5000、正式10ファイル。

### 30.1 T=999・3,000台departure-end trial

**スクリプト:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_1000_timestep_departure_end_trial.py`

**scenario / output directory:** `tvt_mp_6x6_grid_3000_vehicle_200m_60kph_eval_1000_timestep_departure_end_candidate_limit_10_seed_0_vot_seed_1`（`research_outputs/trial/` 配下）

**条件:**

| 項目 | 値 |
|------|-----|
| Vehicle 数 | **3,000** 台 |
| 参加 | **全車 participating** |
| departure | **T=0〜999** |
| evaluation | **T=0〜999** |
| internal TSIZE | **1030**（999 + baseline horizon 30 + 1） |
| simulation 後 World.T | **1000** |
| Candidate Visit 数上限 **N** | **10** |
| baseline horizon | **30** |
| Link | 全 **168** 本 **200 m** |
| free-flow speed | **60 km/h**（60/3.6 m/s） |
| capacity_in / capacity_out | **未指定** |
| production | **Candidate 共有直列化**最適化を使用 |
| 全車完走・交通解消 | **要求しない**（**departure-end observation trial**） |

**結果（manifest・run_summary 正本）:**

- **exec_simulation_seconds:** **23697.237107249908**（約 **6 時間 34 分 57 秒**）
- **1 evaluation timestep 平均:** **23.697237107249908 s/timestep**
- **transactions:** **3579**
- **Vehicle state:** end **1273** / run **1726** / wait **1** / home **0**（合計 **3000**）
- **未完走（end 以外）:** **1727** 台相当（run+wait）
- **scheduled departure reached:** **3000** / **not reached:** **0**
- **internal grid Link 上 Vehicle:** **1565**
- **OD connector 上 Vehicle:** **161**
- **Link 上合計 1565+161=1726** は **run** 数 **1726** と一致
- **Vehicle plan SHA-256:** `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`
- transaction 数は **manifest**、**tvt_mp_transactions.csv**、**Node 別合計**のすべてで **3579** 件
- **Vehicle state counts 合計**は **3000**
- **正式出力 8 ファイル**を保存（研究 CSV 5 + vehicle_vot + manifest + run_summary）

**性能上の観察（条件→結果→判断）:**

- T=0〜299 **最適化後** trial では約 **5.46 s/timestep**（§29.10）
- **T=0〜999** では約 **23.70 s/timestep**（非線形に重い）
- 後半混雑、**Candidate World 復元**、**pickle load**、**GC** 負荷により **単純比例**で見積もれない
- **T=600** 表示後も **CPU 約 100%** で計算継続しており、**停止ではなかった**
- **`SHOW_PROGRESS_DELTAT=600`** のため、**T=600 以降**は完了まで **新しい実 World 進捗表示がなかった**
- **T=999** 時点で **1727 台未完走**であり、**交通解消には遠かった**

**区分（混同禁止）:** 本 trial は **正常終了した departure-end observation** であり、**全車完走 trial ではない**（§30.8 の full completion trial とは別物）。

### 30.2 T=999出力の監査性不足（横並び事後分析）

**T=999 正式 CSV**（`tvt_mp_transactions.csv` / `tvt_mp_visits.csv` 等）には、従来の **横並び事後分析**に必要な次が **不足**していた。

- 取引成立時の **inlink_name**
- **baseline arrival**（decision 内 baseline 到着 timestep）
- **actual node arrival**（実 World 初回到着）
- **baseline local rank** / **post-trade local rank**
- **Node 累積連続順位**（**assigned_rank**）と **actual node passage rank** の **完全な横並び**
- **buyer 別 G_b** / **seller 別 R_s**
- **同一 inlink** 上の **buyer / seller / nonparticipating** 構成

**保存されていたもの:** baseline / Candidate / **actual passage**、実現結果、既存正式列の **経済評価**・**Node 別集計** 等。

**結論:** 従来 CSV **だけ**から **完全な横並び事後監査**を再現 **できない**。

**禁止（監査契約）:**

- 既存出力を **後付け推測・補完しない**
- **passage 時刻**から **actual arrival を逆算しない**
- **baseline arrival** を **actual arrival** として **流用しない**

**T=999 出力が有効な用途:**

- transaction 数、Vehicle 状態、Node 別集計
- passage・経済評価の **既存正式列**
- **実行性能**、**departure-end 時点の交通状態**

### 30.3 過剰なproduction監査拡張の不採用

**経緯:** 正式監査出力のため、**production と test の 13 ファイル**へ **約 2112 行**を追加する案を **一度実装**した。

**案に含まれていた主な変更:**

- **actual arrival** の production 保存
- **Candidate arrival status**
- **CommonFrozenInput** の大幅拡張
- **buyer / seller economic frozen 型**
- **TradeWait** の大幅拡張
- **transaction audit / visit audit** の **production writer**
- 多数の **test fixture** 更新

**不採用理由:** 既存 **横並び diagnostic** を再利用する目的に対し **変更範囲が過大**で、既存 fixture 基盤へ **広く波及**した。

**破棄:**

- 未 commit 変更は **`git restore`** で破棄
- **production** と **test** を commit **`f323820`** の状態へ復元
- 破棄前 patch: **`/tmp/tvt_mp_audit_overdesign_backup.patch`**（約 **116 KB**、**一時退避**。**正式設計ではない**。再採用を前提にしない）

**確定判断:**

- **production へ大規模監査基盤を追加しない**
- 既存 **diagnostic** で確立済みの **横並び取得方法**を **再利用**する
- **production を変更しない外部 helper** 方式を採用
- **Candidate arrival** の新規 production 基盤は **今回追加しない**
- **timestep 単位 physical trace** は **長期本番 trial** では保存しない
- **成立取引**と **trade-scope Visit** だけを保存する

**最新参照:** 採用方式は **§30.4**（`research_scripts/tvt_mp_full_run_audit_helper.py`）。

### 30.4 最小full-run audit helper

**新規 helper:** `research_scripts/tvt_mp_full_run_audit_helper.py`

**公開 API:**

- `install_tvt_mp_full_run_audit(real_world)`
- `finalize_tvt_mp_full_run_audit(real_world, research_output_bundle)`
- `write_tvt_mp_full_run_audit_csv(audit_result, output_directory)`

**static validation:** `validate_tvt_mp_full_run_audit_helper_static_contract()`

**方式（production 非変更）:**

- 既存 **横並び diagnostic** で用いた **保存済み result chain** を読み取る（**diagnostic module は import しない** — trial script 副作用のため）
- **TVT-MP driver** の **成立取引**結果を **hook** で捕捉
- `Vehicle.record_order_control_node_arrival()` の **正常処理後**に、**実 World のみ**を対象として Visit 単位の **actual node arrival** を保存
- **key:** `(node_name, vehicle_name, visit_id)`
- **同一 Visit の再登録:** 最初に保存した到着 timestep を **維持**し、**現在 World.T とは再比較しない**（production は初回 `arrival_time` を保持するため）
- **baseline World** / **Candidate local World** は **`vehicle.W` の同一性**により **除外**
- **passage から actual arrival を逆算しない** / **baseline arrival を actual arrival へ流用しない**
- **Vehicle 名 prefix から inlink を推測しない**（**binding_visit.inlink_name** を使用）
- **live World、Vehicle、Node、Link** を最終 audit result に **保持しない**
- **physical trace** や **全 timestep 履歴**を保存しない
- **finalize 後**に hook を **外す**

**新規監査 CSV（正式出力に追加）:**

- `tvt_mp_transaction_audit.csv`
- `tvt_mp_visit_audit.csv`

**transaction audit の主要情報:** decision timestep、Node、Candidate identity、right-of-entry Visit、buyer / seller / nonparticipating Visit 集合、baseline order、Candidate order、total G / total R、surplus、FIFO 結果、**同一 inlink 最大** party / buyer / seller / nonparticipating 数、ex-post evaluation status 等。

**visit audit の主要情報:** VisitKey、role、**inlink_name**、formal route、**baseline arrival**、**actual node arrival**、arrival tiebreaker、**baseline local rank**、**post-trade local rank**、**assigned_rank**（Node 累積連続 C 順位）、**actual node passage rank**、baseline / Candidate / **actual passage**、declared / true VOT、**buyer G_b**、**seller R_s**、**payment P_b**、**compensation C_s**、realized gain / delay loss、satisfaction、**binding sequence auxiliary rank**、**same-inlink FIFO preserved** 等。

**局所順位と Node 順位の区別（検索・横並び用）:**

| 名称 | 意味 |
|------|------|
| **baseline_local_rank** | 当該 decision 内の **baseline 局所順位** |
| **post_trade_local_rank** | 当該 decision 内の **取引後局所順位** |
| **assigned_rank** | **Node 単位**の **累積連続 C 順位** |
| **actual_node_passage_rank** | **Node 単位**の **実通過連続順位** |
| **binding_sequence_auxiliary_rank** | binding sequence 上の **補助順位**（local rank や Node 累積順位 **とは別物**）。**同一 inlink FIFO** 注釈は diagnostic と同様 **補助順位**を用い、**post_trade_local_rank を FIFO 順序源にしない** |

**trial 接続順（契約）:** World 構築 → Vehicle plan → 参加設定 → `finalize_scenario` → **`install`（simulation 直前 1 回）** → simulation → **`build_tvt_mp_research_output`** → **`finalize`（bundle 直後 1 回）** → 既存正式 CSV → **同一 output directory** へ audit CSV。

### 30.5 監査helperの実動検証（audit validation）

#### 30.5.1 全参加 12 台

**スクリプト:** `research_scripts/run_tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation.py`

**scenario:** `tvt_mp_single_cross_intersection_12_vehicle_full_run_audit_validation_seed_1`

**結果:**

- **transactions = 2**
- **transaction audit rows = 2** / **visit audit rows = 8**
- **全 12 台完走**
- **audit validation passed**
- **production 変更なし**

#### 30.5.2 4 交差点・600 台・20% nonparticipating

**スクリプト:** `research_scripts/run_tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_full_run_audit_validation.py`

**scenario:** `tvt_mp_four_cross_intersections_grid_medium_nonparticipating_20_600_vehicle_eval_900_timestep_seed_1_nonparticipation_seed_3_full_run_audit_validation`

**結果:**

- **transactions = 228**
- **transaction audit rows = 228** / **visit audit rows = 626**
- **buyer rows = 263** / **seller rows = 324** / **nonparticipating rows = 39**
- **actual arrival saved rows = 626**
- **FIFO violation total = 0**
- **same-inlink maximum party count = 2**
- **audit CSV validation passed**
- **total runtime ≈ 1246.906 s**
- **production 変更なし**

**結論:** **全 participating** と **20% nonparticipating** の双方で、**監査 CSV だけ**から既存 **横並び事後分析**に必要な情報を取得できた（**audit validation 完了**）。**3,000 台 full completion trial の結果は未確定**（§30.8）。

### 30.6 同一inlink複数当事者の実例（横並び再構成）

**代表取引:** **T=392**、**northwest_intersection**

- **buyer 3** / **seller 3** / **trade-scope total 6**
- **same-inlink buyer 最大 2** / **same-inlink seller 最大 2**
- **FIFO violation 0**

**同一 inlink buyer（例）:** `west_north_od_to_northwest_intersection`

- `veh_wn_en_base_025:1`
- `veh_wn_se_base_025:1`

**同一 inlink seller（例）:** `southwest_intersection_to_northwest_intersection`

- `veh_sw_nw_base_039:2`
- `veh_sw_nw_base_040:2`

**監査 CSV から横並び再現できた項目:** baseline / actual arrival、baseline / Candidate / actual passage、baseline / post-trade local rank、assigned rank / actual passage rank、**G_b / R_s**、**P_b / C_s**、realized gain、satisfaction、**same-inlink FIFO**。

### 30.7 到着・通過時刻の奇偶確認（actual arrival 丸めの否定）

**T=392 代表取引:** 到着・通過時刻が **すべて偶数**であったため、helper が **偶数へ丸めている可能性**を確認した。

**600 台 audit output 全体:** baseline arrival または actual arrival に **奇数**を含む **成立取引が 136 件**存在。

**代表:** **T=41**、**northeast_intersection**

- seller arrivals: **47 / 47**（3 Visit）
- buyer arrival: **49 / 49**
- baseline passage: **51, 53, 55, 57**
- Candidate / actual passage: **52, 54, 56, 50**

**結論:** 監査 helper は **baseline arrival**、**actual arrival**、**baseline passage** を **偶数へ丸めていない**。

**構成上の観察（欠損ではない）:** 600 台 trial では、**同一 inlink に buyer または seller が複数**かつ **奇数到着を含む成立取引は 0 件**だった。これは **監査欠損**ではなく、**今回の成立取引集合の構成**上の結果である。

### 30.8 次回長期trial（3,000台・20% nonparticipating・全車完走・監査接続）

**新規本番スクリプト:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_trial.py`

**scenario / output directory:** `tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_candidate_limit_10_seed_0_vot_seed_1_nonparticipation_seed_3`

**条件（§30.1 の plan・道路・TVT-MP と整合、参加のみ変更）:**

| 項目 | 値 |
|------|-----|
| Vehicle | **3000** |
| participating / nonparticipating | **2400 / 600**（**20%**） |
| nonparticipation seed | **3**（4 交差点 20% trial と同型 **`random.Random(3).sample`** + plan 順維持） |
| departure | **T=0〜999** |
| traffic / demand / VOT seed | **0 / 42 / 1** |
| Vehicle plan SHA-256 | `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9`（**参加は plan digest に含めない**） |
| N / baseline horizon / clearance | **10 / 30 / 1** |
| 道路 | 全 Link **200 m**、**60 km/h**、capacity_in/out **未指定** |
| 実行 | **全車完走・交通解消**まで（**固定 evaluation end T=999 で終了しない**） |
| safety cap（最終 TVT decision 上限） | **T=5000** |
| internal TSIZE | **5031**（5000 + 30 + 1） |
| full-run audit helper | **接続**（§30.4 順序） |
| 想定 wall-clock | **約 12 時間**（**未確定**。単純比例禁止） |
| 実行運用 | **caffeinate**、**console log 保存**（記録上の運用；本メモは実行結果を確定しない） |

**終了条件（スクリプト契約）:**

- end **= 3000**、run **= 0**、wait **= 0**、home **= 0**
- **network 上 Vehicle = 0**、internal Link **= 0**、OD connector **= 0**
- **scheduled departure reached = 3000**
- **traffic clearance complete** / **full trip completion complete**
- 最終 **World.T** > 最終 **actual passage timestep**

**正式出力:** 従来 **8 ファイル** + 監査 CSV **2 本** = **10 ファイル**。

**スクリプト作成・検証（確定）:**

- 作成後 **py_compile** と **static validation** は **通過**
- **初回実行**は **`finalize_scenario()` 前**に **`world.TSIZE`** を参照する **`verify_network_runtime(world)`** により **simulation 開始前 AttributeError** で停止
- **原因:** **`World.TSIZE` は `finalize_scenario()` で初めて作成される**
- **修正:** finalize **前**の **`verify_network_runtime(world)` 呼出しのみ削除**。finalize **後**の **`TSIZE` 検証**と **`verify_network_runtime(world)` は維持**
- **修正後:** **py_compile** と **static validation** は **再度通過**

**現在（2026-11-02 記録時点）:**

- **修正版**の **3,000 台・20% nonparticipating・全車完走・交通解消・full-run audit** 長期 trial を **実行中**
- **正常終了結果は未確定**（最終 World.T、transaction 数、監査行数、実行時間、same-inlink 最大、FIFO、完走成否等は **確定事項として記載しない**）
- **完了後**に正式結果を **本 §30** および進捗 **§19** へ **追記**する

**歴史的参照:** §29.15 の「T=999 未決定」は **T=999 departure-end trial 実施前**の判断記録である。**T=999 trial 結果**は **§30.1**。**全車完走**は **§30.8**（**結果未確定**）。

**最新参照（確定結果）:** 3,000 台・20% nonparticipating **full-completion trial** の **確定結果**、および **FCFS・BATCH・TVT-MP・signalized UXsim** の **総合評価指標設計**の最新正本は **§31**（2026-11-03）。本 §30.8 の上記「実行中」「結果未確定」記述は **歴史的記録**として削除しない。

---

## 31. FCFS・BATCH・TVT-MP・signalized UXsimの総合評価指標と3,000台full-completion結果（2026-11-03）

**最新参照:** 3,000 台・20% nonparticipating full-completion trial の **確定数値**と **方式比較・評価指標**の設計正本は **本 §31**。§30.8 は **実行前・実行中**の歴史的記録（**結果未確定**の記述を含む）。

### 31.0 検索語

**検索語（本 §31 へ到達するための目安）:** AWT、AWWT、ACWT、ACWWT、waiting time、累積waiting time、Vehicle当たり、平均Visit数、FCFS比較、BATCH比較、TVT-MP比較、signalized UXsim比較、総旅行時間、平均旅行時間、総遅延、平均遅延、最終Vehicle完走時刻、makespan、Buyer、Seller、Nonparticipating、Satisfied、Unsatisfied、role別評価、3,000台、20% nonparticipating、full completion、traffic clearance、18時間、pickle.load、GC、高速化、last_vehicle_completion_timestep、conservative makespan、Vbar、true VOT、Seller unsatisfied、最終OD Link、earliest arrival time、actual intersection entry time。

### 31.1 3,000台・20% nonparticipating full-completion trialの確定結果

**実行スクリプト:** `research_scripts/run_tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_trial.py`

**scenario / output directory:** `tvt_mp_6x6_grid_3000_vehicle_nonparticipating_20_full_completion_audit_candidate_limit_10_seed_0_vot_seed_1_nonparticipation_seed_3`（`research_outputs/trial/` 配下）

**条件:**

| 項目 | 値 |
|------|-----|
| Vehicle | **3000** 台 |
| participating / nonparticipating | **2400 / 600**（**20%**） |
| nonparticipation seed | **3** |
| departure | **T=0〜999** |
| traffic seed | **0** |
| demand seed | **42** |
| VOT seed | **1** |
| Candidate Visit 数上限 **N** | **10** |
| baseline horizon | **30** |
| clearance | **1** |
| safety cap（最終 TVT decision 上限） | **T=5000** |
| internal TSIZE | **5031** |
| Vehicle plan SHA-256 | `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9` |
| full-run audit helper | **接続**（§30.4 順序） |
| 実行運用 | **caffeinate**、**console log 保存** |
| 実行目的 | **全車完走・交通解消**まで |

**確定結果:**

| 項目 | 値 |
|------|-----|
| final **World.T** | **2035** |
| evaluation end timestep | **2034** |
| final actual passage timestep | **1869** |
| final Vehicle state | home **0** / wait **0** / run **0** / end **3000** |
| full trip completion | **True** |
| traffic clearance | **True** |
| transaction count | **4298** |
| transaction audit rows | **4298** |
| visit audit rows | **11871** |
| buyer audit rows | **5013** |
| seller audit rows | **6170** |
| nonparticipating audit rows | **688** |
| actual arrival saved rows | **11871** |
| same-inlink maximum party count | **3** |
| same-inlink maximum buyer count | **3** |
| same-inlink maximum seller count | **3** |
| same-inlink maximum nonparticipating count | **2** |
| FIFO violation total | **0** |
| audit CSV validation | **passed** |
| exec_simulation seconds | **65093.892005** |
| final script total seconds | **65116.178632** |
| wall-clock 目安 | **約 18 時間 5 分** |
| seconds per real-world timestep | **31.987171** |
| output directory bytes | **12463559** |

**正式 10 ファイル:**

1. `tvt_mp_transactions.csv`
2. `tvt_mp_visits.csv`
3. `tvt_mp_vehicles.csv`
4. `tvt_mp_nodes.csv`
5. `tvt_mp_scenario.csv`
6. `tvt_mp_transaction_audit.csv`
7. `tvt_mp_visit_audit.csv`
8. `vehicle_vot.csv`
9. `manifest.json`
10. `run_summary.txt`

**区分:** 本節は **§30.8** で準備した同一 scenario の **正常終了・確定結果**である。§30.1 の **departure-end observation（T=999 固定終了）** とは **別 trial**。

### 31.2 FCFS full-completion結果との同条件性

**FCFS 比較対象 output directory:** `research_outputs/trial/fcfs_6x6_grid_3000_vehicle_all_links_200m_speed_60kph_departure_999_tmax_5000_completion_check_seed_0_demand_seed_42`

**原典確認済み条件:**

| 項目 | 値 |
|------|-----|
| Vehicle | **3000** 台 |
| departure | **T=0〜999** |
| Vehicle plan SHA-256 | `0b1fc2d2b084c3c5ce94d0ec0c476de4b2c60d40543f58f789dd644d1e3d71d9` |
| internal Link length | **200 m** |
| free-flow speed | **16.666666666666668 m/s**（**60 km/h**） |
| jam density | **0.2** |
| 全車正常完走 | **completed_count 3000** / **not_completed_count 0** |
| last_vehicle_completion_timestep | **2296** |
| world_t_after_simulation | **5000** |

**重要な区別:**

- FCFS の **World.T=5000** は **固定観測終了時刻**であり、**処理能力比較値ではない**。
- FCFS の **比較値**は **last_vehicle_completion_timestep=2296**。
- TVT-MP の **final World.T=2035** は、**全車完走・network 空**を確認した後、**評価終了処理**のために **closing timestep を 1 回実行した後**の値。
- TVT-MP では **T=2034** を実行する **前**に、すでに **全車完走・全 Link 空**だった。
- したがって、TVT-MP の **最終 Vehicle 完走**は **遅くとも T=2033**。
- TVT-MP の **個別 Vehicle 最終完走 timestep** は **今回の正式出力に独立保存されていない**。
- **exact** な最終 Vehicle 完走 timestep を **2033 と断定しない**。
- **保守的上限**として **「遅くとも T=2033」** と記録する。

**保守的 makespan 比較:**

| 方式 | 値 |
|------|-----|
| FCFS | **2296** |
| TVT-MP | **遅くとも 2033** |
| 差 | TVT-MP は **少なくとも 263 timestep 早い** |
| 保守的短縮率 | **(2296 − 2033) / 2296 ≈ 11.45%** |

**ただし（一般化禁止）:**

- この結果は **system makespan** の比較である。
- **飽和交通流率が 11.45% 向上した**と表現 **しない**。
- **常に TVT-MP が FCFS より高い処理能力を持つ**と一般化 **しない**。
- **最終 departure T=999 後だけ**の所要時間差から **20.3% 短縮**と評価する **旧解釈は不採用**。
- **理由:** T=999 までの **完走台数**、**残存台数**、**Vehicle 位置**、**queue**、**spillback 状態**が方式間で **異なり得る**ため、**最終 departure 後だけの時間差**は **同じ初期状態からの比較ではない**。

### 31.3 waiting timeの正式定義

各 **Vehicle**・各 **対象交差点 Visit i** について:

**earliest arrival time:** 他 Vehicle が存在しないと仮定した場合に、その Vehicle が **対象交差点へ進入できる最も早い時刻**。

**waiting time:**

\[
W_i = \text{actual intersection entry time}_i - \text{earliest arrival time}_i
\]

**意味:**

- **passive delay** を含む。
- TVT 取引により Seller が **自発的に引き受ける active delay** も含む。
- 一般的な **delay** に近いが、**能動的に受け入れた遅れ**を含むため **waiting time** という用語を **維持**する。

**重要:**

- **Waiting time** は **対象交差点へ進入するまで**の **inlink 上の queue**、**congestion**、**spillback** による遅れを **反映する**。
- **「Link 上の渋滞を表さない」**と記録 **しない**。
- 一方、**対象交差点を通過した後**の **最終 OD Link 走行**など、**独立した次の order-control Visit を形成しない区間**は、そのままでは **別 Visit の waiting time** として **計測されない**。
- したがって **waiting time だけ**で **trip 全体の負担**を **完全に置き換えない**。

### 31.4 AWT・AWWTの原定義

**最新参照（2026-11-04、不採用注記）:** 本節以下（§31.4〜§31.8）の **Visit 単位 AWT・AWWT** と **平均 Visit 数** による **ACWT・ACWWT 導出**は、**定義検討過程の歴史的記録**である。**network 全体**の最新定義は **§31.18**。**order-control Visit** は **全 Node・全 Link・全制御方式を網羅しない**ため、**network-wide ACWT・ACWWT には使用しない**。本節の数式を **最新定義として読まない**。

方式 **m** について、評価対象 Visit 総数を **Z_m** とする。

**Visit 単位 AWT:**

\[
\text{AWT}_m = \frac{1}{Z_m} \sum_i W_{m,i}
\]

**Visit 単位 AWWT:**

\[
\text{AWWT}_m = \frac{1}{Z_m} \sum_i C_i W_{m,i}
\]

**各記号:**

| 記号 | 意味 |
|------|------|
| **W_{m,i}** | 方式 **m** における Visit **i** の waiting time |
| **C_i** | Vehicle の **時間価値**（true VOT） |
| **Z_m** | 方式 **m** で評価対象となる **Visit 総数** |

**方針:** AWWT では **全方式に同じ true VOT** を使用する。TVT-MP の **nonparticipating Vehicle** にも **評価用 true VOT** を適用する。**申告 VOT** や **参加有無**によって総合評価の重みを **欠落させない**。

### 31.5 方式ごとのVisit数差という問題

FCFS、BATCH、TVT-MP、signalized UXsim では、**route choice** や **経路変化**により、各 Vehicle が OD 完遂までに経験する **Visit 数**が **異なり得る**。

**Visit 単位 AWT だけ**を比較すると、

- **1 Visit 当たり**の waiting time が **短い**方式、
- しかし **1 Vehicle 当たり**の Visit 数が **多い**方式、

を **過大評価**する可能性がある。

**当初の提案:** FCFS の平均 Visit 数を **10**、TVT-MP を **15** とした場合、

\[
\text{AWT}_{\text{FCFS}} \quad \text{vs.} \quad \text{AWT}_{\text{TVT}} \times (15 / 10)
\]

として比較する。

**本 §31 の方針:** この発想は **妥当**だが、FCFS 基準で補正した **独自指数**として提示するより、**Vehicle 当たり累積 waiting time** へ変換する **恒等式**として定義する方が **明確**である（§31.6・§31.7）。

### 31.6 ACWTの導出

方式 **m** について:

- Vehicle 数 **N**
- Visit 総数 **Z_m**
- Vehicle 当たり平均 Visit 数: **V̄_m = Z_m / N**
- Visit 単位 AWT: **AWT_m = (1 / Z_m) Σ_i W_{m,i}**

すると:

\[
\text{AWT}_m \times \bar{V}_m = \left(\frac{1}{Z_m} \sum_i W_{m,i}\right) \times \frac{Z_m}{N} = \frac{1}{N} \sum_i W_{m,i}
\]

これは **線形近似ではなく**、**同じ Visit 集合**と **同じ分母**を使用する限り **厳密な恒等式**である。

**正式名称候補:** Average Cumulative Waiting Time (per Vehicle)

**略称:** **ACWT**

**日本語:** Vehicle 当たり平均累積 waiting time

**定義:**

\[
\text{ACWT}_m = \frac{1}{N} \sum_z \sum_{i \in \text{Visits}_m(z)} W_{m,z,i}
\]

**同値:** **ACWT_m = AWT_m × V̄_m**

**単位:** seconds per Vehicle

**名称上の注意:**

- 「Average Cumulative Waiting Time per Vehicle」は **Average** と **per Vehicle** が **重複して見える**。
- 正式表記候補: **Average Cumulative Waiting Time (per Vehicle)**、略称 **ACWT** を維持。
- 名称は **現時点の有力候補**であり、論文本文への **最終採用前**に **既存用語との重複調査**を行う余地を残す。
- **指標の数理的定義**は名称確定前でも **固定可能**。

### 31.7 ACWWTの導出

**Visit 単位 AWWT:**

\[
\text{AWWT}_m = \frac{1}{Z_m} \sum_z \sum_{i \in \text{Visits}_m(z)} C_z W_{m,z,i}
\]

**平均 Visit 数:** **V̄_m = Z_m / N**

したがって:

\[
\text{AWWT}_m \times \bar{V}_m = \frac{1}{N} \sum_z C_z \sum_{i \in \text{Visits}_m(z)} W_{m,z,i}
\]

**正式名称候補:** Average Cumulative Weighted Waiting Time (per Vehicle)

**略称:** **ACWWT**

**日本語:** Vehicle 当たり平均累積 weighted waiting time

**定義:**

\[
\text{ACWWT}_m = \frac{1}{N} \sum_z C_z \sum_{i \in \text{Visits}_m(z)} W_{m,z,i}
\]

**同値:** **ACWWT_m = AWWT_m × V̄_m**

**単位:** VOT が money/second なら **money per Vehicle**。

**重要:**

- **ACWWT** は、各 Vehicle が **全 Visit** で経験した waiting time を **true VOT** で重み付けした **平均**。
- FCFS、BATCH、TVT-MP、signalized UXsim 間で **Vehicle 数 N が同じ**場合に **直接比較**する。
- FCFS 基準の **平均 Visit 数比を掛けた正規化値**は、比較上 **同値**でも **主表には採用しない**（§31.8）。
- 各方式の **Visit 単位 AWWT**、**平均 Visit 数**、**ACWWT 実値**を **直接示す**。

### 31.8 主表の構成

**最新参照（2026-11-04、不採用注記）:** 本節の **旧主表案**は **歴史的記録**である。**Visit 単位 AWT**、**平均 Visit 数**、**Visit 単位 AWWT** を network 全体の主表へ置く案は **不採用**。**最新主表**は **§31.18.9**。

**最終比較の主表**では、方式ごとに次を **直接示す**。

**列:**

- 方式
- Visit 単位 AWT
- 平均 Visit 数
- ACWT
- Visit 単位 AWWT
- ACWWT
- 平均旅行時間
- 総旅行時間
- 平均遅延
- 総遅延
- 最終 Vehicle 完走時刻
- 全車完走
- 交通解消

**行:**

- signalized UXsim
- FCFS
- BATCH
- TVT-MP

**禁止:** FCFS の平均 Visit 数を基準とした **比率補正値**を **主表**へ置かない。**各方式の実値**を直接示す。

**解釈:** Visit 単位 AWT・AWWT は **ACWT・ACWWT の構成要素**として表示する。**Visit 単位 AWT・AWWT だけ**で方式の **総合優劣**を **判定しない**。

### 31.9 ACWT・ACWWTと旅行時間・遅延の関係

全 Link が **200 m**、free-flow speed が **60 km/h** なので、**1 Link** の自由走行時間は:

\[
200 / (60 / 3.6) = 12 \text{ 秒}
\]

Vehicle **z** の実走行 Link 数を **L_z**、累積 waiting time を **CW_z** とすれば、**概念的には**:

\[
\text{TravelTime}_z \approx 12 L_z + \text{CW}_z
\]

という構造を **期待できる**。

**ただし**、これを **正式な旅行時間算定式**には **しない**。

**理由:** OD connector の扱い、trip 終端 Link、order-control 対象外 Node、離散 timestep、Link 内の走行状態、Visit 境界と trip 境界、clearance、route choice 等により、**12 L_z + CW_z** が **実旅行時間と完全一致**するとは **限らない**。

**正式方針:**

- **旅行時間**は **departure から trip end まで直接計測**。
- **実走行経路**の **自由走行時間**を **別に算出**。
- **総遅延**は **実旅行時間 − 実走行経路の自由走行時間** として **独立算出**。
- **ACWT** と **総遅延**の **一致・差**は **整合確認**に使う。
- **ACWT** が **Link 上の渋滞を一切表さない**とは **評価しない**（inlink 上の渋滞・queue・spillback は **対象 Visit の waiting time** へ反映される）。
- **ただし**、**ACWT だけ**で **trip 全体の全負担**を **完全に代表させない**（§31.3・§31.13）。

### 31.10 当面採用する総合評価指標

**正式な中核指標:**

1. AWT
2. AWWT
3. 平均 Visit 数
4. ACWT
5. ACWWT
6. 平均旅行時間
7. 総旅行時間
8. 平均遅延
9. 総遅延
10. 最終 Vehicle 完走時刻
11. 全車完走
12. 交通解消

**Makespan** は **重要な補助指標**だが、AWT・AWWT・ACWT・ACWWT・旅行時間・遅延を **置き換えない**（§31.2 の **保守的 makespan** は **補助**）。

**当面保留:**

- Node 別 AWT・AWWT
- 時間帯別 AWT・AWWT
- 詳細な空間分布
- 時系列 throughput
- VOT 階層別詳細分析

これらは **方式差の原因分析**で必要になった場合に **のみ**追加する。**最初から正式出力要件**へ含め **ない**。

### 31.11 Buyer・Seller・Nonparticipating別評価

**Buyer:**

- TVT-MP で **buyer role** となった対象。
- FCFS より **AWWT** が **大幅に改善**することを **期待**。
- Buyer の **集計単位**を **role 付き Visit** にするか、**buyer 経験 Vehicle の trip 全体**にするかは **未確定**（§31.12）。

**Seller:**

- TVT-MP で **seller role** となった対象。
- **AWT・AWWT** の **悪化**を **できるだけ小さく抑える**ことを **期待**。
- 既存の **Seller Satisfied / Unsatisfied** 評価を **使用**。
- **Seller unsatisfied 率**を **必須指標**とする。
- **新しい補償込み NetLoss、NetBenefit** 等の **独自式は導入しない**。
- Seller 補償の十分性は **既存の事後 satisfaction 評価**で扱う。
- Seller の **集計単位**を **role 付き Visit** にするか、**seller 経験 Vehicle の trip 全体**にするかは **未確定**（§31.12）。

**Nonparticipating:**

- Buyer・Seller と異なり、**出発から trip end まで一貫した Vehicle 属性**。
- **600 台**を **Vehicle 単位**で評価。
- FCFS の **同一 Vehicle 集合**と比較。
- **Vehicle 単位 ACWT・ACWWT** が **不変または改善**することを **期待**。
- **総旅行時間・総遅延**も **同じ Vehicle 集合**で比較。
- **改善 Vehicle 数** / **不変 Vehicle 数** / **悪化 Vehicle 数** / **最大悪化量** を **最低限確認する候補**。

**全 Vehicle:**

- 全 **3000 台**について **ACWT・ACWWT**、**旅行時間**、**遅延**を比較。

### 31.12 Buyer・Seller集計単位の未確定事項

**確定:**

- Buyer・Seller 評価は **必要**。
- TVT-MP で付与された **role** を基準に FCFS 側と **対応付ける**。
- **Seller unsatisfied 率**は **必須**。
- **新規補償込み独自式**は **不要**。

**未確定:**

1. **Role-Visit 方式** — Buyer または Seller となった **各 Visit** を FCFS の対応 Visit と比較。取引の **直接効果**を測りやすい。**同じ Vehicle が複数回集計**される。
2. **Role 経験 Vehicle 方式** — Buyer または Seller を **経験した Vehicle の trip 全体**を比較。**downstream への波及**や **route 変更**を含む。**同一 Vehicle が buyer と seller の双方**を経験した場合の **分類規則**が必要。
3. **両方式の併記** — 情報量が増え、**過剰分析**になる可能性がある。

**方針:**

- 現時点で **いずれかへ固定しない**。
- **小規模の保存済み output**で **両方式を試算**。
- **結果の意味**、**重複**、**説明可能性**を確認してから **正式採用**を決める。
- **コード実装時**に **無断で一方へ固定しない**。

### 31.13 最終OD Linkと計測範囲

- **order-control 対象**の **内部 Node** へ向かう **inlink 上の渋滞**は、**actual entry time** の遅れとして **waiting time** へ **反映される**。
- **最後の内部交差点**を通過した後、**外部 OD Node** へ向かう **最終 Link** が **新しい対象 Node Visit を形成しない**場合、その **最終区間**は **別 Visit の waiting time** としては **計測されない**。
- したがって **ACWT・ACWWT だけ**で **trip 終端までの全所要時間**を **完全には表さない**。
- この問題を **補完**するため、**平均・総旅行時間**と **平均・総遅延**を **必須**とする（§31.10）。
- **最終 OD Link** を **新たな order-control Visit** として **人工的に追加**する方針は **現時点で採用しない**。
- **trip end までの旅行時間**を **直接計測**する方が **適切**。
- 将来必要なら **計測範囲の独立検証**を行う。

### 31.14 次の実装課題1: 評価指標算出基盤

**最新参照（2026-11-04）:** **最新実装方針**は **§31.18**。**Visit 単位指標を先に実装しない**。**`travel_time`**、**`traveled_route`**、**自由流経路時間**、**ACWT**、**ACWWT** を **先に検証**する（§31.18.11）。下記の Visit 単位必須リストは **検討過程の歴史的記録**であり、network-wide 算出の先行実装要件としては **不採用**。

今後、simulation 結果から次を **算出できるよう**コードを **追加・修正**する。

**必須:**

- Vehicle ごとの **全対象 Visit waiting time**
- **Visit 総数**
- Vehicle ごとの **Visit 数**
- 方式別 **平均 Visit 数**
- Visit 単位 **AWT**
- Visit 単位 **AWWT**
- **ACWT**
- **ACWWT**
- **departure timestep**
- **trip end timestep**
- **実旅行時間**
- **実走行 Link 数**または **実走行経路**
- **実走行経路の自由走行時間**
- **Vehicle 別遅延**
- **平均旅行時間** / **総旅行時間**
- **平均遅延** / **総遅延**
- **最終 Vehicle 完走 timestep**
- **全車完走・交通解消**
- **Nonparticipating 600 台**の **Vehicle 単位比較**
- **Seller Satisfied / Unsatisfied 率**

**実装前の必須調査:**

- UXsim **production** で既に保存される **departure**、**trip end**、**Link 通過履歴**、**route 履歴**
- FCFS、BATCH、TVT-MP、signalized UXsim で **共通利用可能な field**
- **earliest arrival** の **正式保存位置**
- **actual intersection entry** の **正式保存位置**
- **外部 OD Link** と **trip end** の扱い
- **revisit** の **Visit ID**
- 各手法で **Visit 対応付け**が可能か
- **最終 Vehicle 完走 timestep** を **今後の trial** で **正式保存**する方法

**禁止:**

- **定義確認前**の **production 変更**
- **trip end** を **推測**
- **実経路**を **Vehicle 名や OD 名から推測**
- **passage から arrival を逆算**
- FCFS 基準 **正規化値だけ**を保存して **原値を失う**
- **Node 別・時間帯別分析**を **最初から過剰に実装**

### 31.15 次の実装課題2: 約18時間実行の高速化

**確定した性能（§31.1）:**

| 項目 | 値 |
|------|-----|
| exec_simulation | **65093.892005 s** |
| final script total | **65116.178632 s** |
| wall-clock | **約 18 時間 5 分** |
| seconds / real-world timestep | **31.987171** |

**観測:**

- **T=600** 時点で **1114 台走行**、計算時間 **約 5447 s**
- **T=1200** 時点で **約 1386 台走行**、計算時間 **約 29804 s**
- **T=1800** 時点で **168 台走行**、計算時間 **約 60294 s**
- **交通混雑が大きい中盤**で **非線形**に重くなった。
- **13.5 時間**時点でも process は **R+**、CPU **約 80%**、演算継続。
- **30 秒観測**で CPU 累積時間が **約 23.9 s 増加**。
- **停止**、**sleep**、**deadlock** では **なかった**。
- **console log** が **約 5 時間更新されない区間**があった。
- **macOS sample** では主負荷が **`_pickle.load`** と **Python GC**。
- **pickle 復元**と **GC** が **大きな負荷**であることは **確認**。
- **正規の共有直列化復元**を **多数回**行っているのか、**想定外の反復経路**かは **実行中には未判定**。
- **py-spy** は macOS で **root** が必要。
- **sudo py-spy** は **Anaconda Python 3.13** process を認識できず、`Failed to find a python interpreter in the .data section` で **失敗**。
- **Python 関数単位**の **実行中 stack** は **取得できなかった**。

**高速化調査の原則:**

- **推測**で **production** を変更 **しない**。
- 前回の **過剰な監査 production 拡張**を **繰り返さない**（§30.3）。
- まず **再現可能な短縮 trial** または **限定 instrumentation** を作る。
- **計測候補:** pickle 復元 **回数** / **bytes** / **時間**、GC **回数** / **時間**、decision timestep 別 **Candidate 数**、Candidate **World 復元数**、Vehicle 数、**living 車両数**、World **serialized size**。
- **production 変更前**に **原因を独立確認**する。
- 既存の **共有直列化最適化**を **覆さない**（§29）。
- **最適化前後**で **取引結果**、**順位**、**passage**、**RNG**、**Vehicle state** の **完全一致**を確認する。
- **長時間本番 trial** を **原因不明のまま繰り返さない**。

### 31.16 次の作業順序

**最新参照（2026-11-04）:** **最新作業順序**は、**§31.18.11** の **単車両・無交通検証を最初に行う**。その後に **評価算出設計を確定**する。下記 1〜12 は **§31 初稿時点**の順序であり、network-wide 定義訂正後の再開順序としては **§31.18.11 および進捗 §21.9** を優先する。

1. **本 §31** と **進捗メモ**への記録
2. **Terminal** による **本文の独立確認**
3. **評価指標算出**に必要な **既存 field・履歴**の **読取り専用調査**
4. **ACWT・ACWWT・旅行時間・遅延・最終完走時刻**の **算出設計**
5. **Buyer・Seller 集計単位**を **小規模 output** で比較
6. **評価算出コード**の **最小実装**
7. **FCFS・BATCH・TVT-MP・signalized UXsim** で **共通定義**を検証
8. **高速化用**の **短縮再現 trial** または **限定 instrumentation** を設計
9. **pickle 復元・GC・Candidate 反復**の **原因計測**
10. **原因確定後**に **のみ** **最適化設計**
11. **小規模一致検証**
12. **必要時のみ** **長期 trial 再実行**

### 31.17 記述上の注意（混同禁止・未確定の明示）

**混同しないこと:**

- Visit 単位 **AWT・AWWT** vs Vehicle 単位累積 **ACWT・ACWWT**
- **総旅行時間** / **総遅延** / **makespan**
- Buyer・Seller の **role** vs Nonparticipating の **固定 Vehicle 属性**
- **Seller satisfaction** vs **金銭補償込みの新規独自指標**

**確定事項として書かないこと:**

- **ACWT**、**ACWWT** という名称が **既存研究で未使用**であること
- Buyer・Seller の **正式集計単位**
- **12 L + cumulative waiting time** が旅行時間へ **厳密一致**すること
- TVT-MP が **一般に FCFS より常に 11.45% 優れる**こと
- **pickle 負荷**が **想定外反復**によると **確定**したこと
- **次の高速化方法**が **確定**したこと

### 31.18 ACWT・ACWWTの方式共通network定義への訂正

**最新正本:** **network 全体**の **ACWT・ACWWT** は **本 §31.18**。§31.4〜§31.8 の Visit 数による導出は **採用前の検討過程**として残し、**network 全体の正式定義としては不採用**。

#### 31.18.1 旧定義を訂正する理由

§31.4〜§31.8 では、**order-control Visit** を単位とする AWT・AWWT と平均 Visit 数から、

\[
\text{ACWT} = \text{Visit 単位 AWT} \times \text{平均 Visit 数}
\]

\[
\text{ACWWT} = \text{Visit 単位 AWWT} \times \text{平均 Visit 数}
\]

と導出した。

この恒等式は、対象とする **waiting event 集合を漏れなく網羅する Visit 集合**については **数理的に正しい**。

しかし、現在の UXsim における **order-control Visit** は、TVT-MP・BATCH 等の **order-control 対象 Node への訪問**を表す **内部概念**である。

次の区間・訪問を **必ずしも網羅しない**。

- **order-control 対象外 Node**
- **external Node**
- UXsim の **自動 route choice** により経路途中で通過する **external Node**
- 最後の内部交差点から destination の external Node へ向かう **最終 Link**
- **signalized UXsim** 等、order-control Visit を **同じ形で生成しない**制御方式

したがって、**order-control Visit 数を使う ACWT・ACWWT** は、**network 全体を表す方式共通指標にならない**。

特に、**signalized UXsim、FCFS、BATCH、TVT-MP が Node ごとに混在する network** でも、ACWT・ACWWT は **同じ定義で計算できなければならない**。

**確定判断:**

- **order-control Visit 数**を **network 全体の ACWT・ACWWT 算出に使わない**
- **平均 Visit 数**を **network 全体の経路長や自由流所要時間の代替に使わない**
- §31.4〜§31.8 の Visit 数による導出は、**採用前の検討過程**として残す
- **network 全体の正式定義としては不採用**
- **最新定義は本 §31.18 を正本**とする

#### 31.18.2 UXsimのNode通過時間に関する原典確認

**原典:** `uxsim/uxsim.py`、`Node._transfer_one_vehicle_between_links()`

**確認した処理:**

- 通過を許可された **同じ `W.T` 内**で Vehicle を **inlink から outlink へ移す**
- outlink 進入時に、`vehicle.link_arrival_time = W.T * DELTAT` とする
- Vehicle を outlink の **x=0** へ置く
- inlink で残った **`move_remain`** を outlink へ **引き継ぐ**
- 次の式で同じ timestep 内の残余移動距離を outlink 側へ換算する

\[
x_{\text{next}} = \text{vehicle.move\_remain} \times \text{outlink.u} / \text{inlink.u}
\]

- Vehicle を **同じ timestep 内**で outlink 上の **`x_next` まで進める**
- **Node 自体に物理的長さや固定通過時間を設定していない**
- **無信号、無競合、capacity 制約なし、clearance 制約なし**なら、Node 境界で **固定 1 timestep を追加しない構造**である
- **signal、clearance、下流入口空間不足、capacity、priority** 等により transfer できず待つ時間は **実旅行時間へ含まれる**

**ただし:**

- UXsim の離散 timestep 境界に **オフバイワンがないこと**は、**単車両・無交通・複数 Link の最小 trial** で **実作動確認する**
- **原典読解だけ**で **数値的一致を未検証のまま断定しない**

#### 31.18.3 実旅行時間

Vehicle **z** の実旅行時間を、

\[
\text{TT}_z = t_z^{(\text{trip end})} - t_z^{(\text{departure})}
\]

とする。

UXsim では `Vehicle.end_trip()` で、

- `arrival_time = W.T`
- `travel_time = (arrival_time - departure_time) * DELTAT`

を保存する。

**TT_z** には、出発から trip end までの **全経過時間**が含まれる。少なくとも次を含む。

- 起点で network へ進入できず待つ時間
- Link 上の自由走行
- Link 上の queue、congestion、spillback
- signal 待ち
- FCFS、BATCH、TVT-MP 等による Node passage 待ち
- clearance 待ち
- 下流 Link 入口空間不足
- capacity 制約
- priority 待ち
- 最終 OD Link 走行
- trip end までの全経過時間

#### 31.18.4 同一実走行経路の最短旅行時間

Vehicle **z** の実走行経路を **actual_route_z** とする。

同じ実走行経路を、**他 Vehicle なし**、**待機なし**、**signal・priority・capacity 等による追加待ちなし**で走った場合の **UXsim 上の最短旅行時間**を、

\[
T_{\min,z}
\]

と定義する。

**一般形:**

\[
T_{\min,z} = \sum_{\text{link} \in \text{actual\_route}_z} \frac{\text{length}_{\text{link}}}{\text{free\_flow\_speed}_{\text{link}}}
\]

Node 自体に **固定通過時間がない**ことを原典確認したため、原則として **Link 自由流時間の合計**を用いる。

今回の **全 Link 200 m、free-flow speed 60 km/h** 条件では、

\[
200 / (60 / 3.6) = 12 \text{ 秒}
\]

なので、

\[
T_{\min,z} = 12 \times \text{actual traveled Link count}_z
\]

と **簡約できる**。

**ただし正式実装では固定値 12 を直接使わず**、各実走行 Link について **length / free_flow_speed** を合計する。

**理由:**

- 将来の **異質 Link** へ対応できる
- Link 長・速度条件の変更に耐える
- **signalized UXsim、FCFS、BATCH、TVT-MP、混在 network** へ共通適用できる

**実走行経路の正本:**

- `Vehicle.traveled_route()`
- `Vehicle.log_t_link`
- 実際に通過した **Link object 列**

**禁止:**

- Vehicle 名や OD 名から経路を **推測しない**
- order-control Visit 数から Link 数を **推測しない**
- **Link 数 = Visit 数 + 1** のような **固定補正式を使わない**
- **external Node が中継地点にならないと仮定しない**

**最新参照（2026-11-04、不採用注記）:** 本節の **Σ(length/u)** および **T_{\min,z} = Σ length/u** は **定義検討過程の歴史的記録**である。**CASE 1〜3** では解析和だけでは **UXsim 最短旅行時間**と一致せず、**1 + Σ(length/u)** は **CASE 4** で **反証**された。**正式 T_{\min,z}** は **§31.18.12** の **reference replay**（**uxsim_reference_minimum_trip_time_s**）。本節を **最新定義として読まない**。

#### 31.18.5 Vehicle単位の累積waiting time

Vehicle **z** の **network 全体**における累積 waiting time を、

\[
\text{CW}_z = \text{TT}_z - T_{\min,z}
\]

と定義する。

**意味:**

- 同じ実走行経路を自由流で完遂する最短時間を超えて、実際に追加で要した **全時間**
- **passive delay** を含む
- TVT-MP で Seller が取引により自発的に受け入れた **active delay** も含む
- **signal、FCFS、BATCH、TVT-MP、capacity、queue、spillback** 等による追加時間を **制御方式に依存せず含む**
- **external Node、途中の external Node、最終 OD Link、order-control 対象外 Node** も実旅行時間と実走行経路に含まれるため **欠落しない**

この **CW_z** は、数理的には **actual-route-conditioned delay** と同じ時間量である。

ただし、本研究では **active delay も含む**ことを明示するため、**waiting time** という用語を **維持**する。

#### 31.18.6 ACWTの最新定義

全 Vehicle 数を **N** とする。

**ACWT:**

\[
\text{ACWT} = \frac{1}{N} \sum_z \text{CW}_z = \frac{1}{N} \sum_z \bigl(\text{TT}_z - T_{\min,z}\bigr)
\]

**正式名称候補:** Average Cumulative Waiting Time (per Vehicle)

**日本語:** Vehicle 当たり平均累積 waiting time

**位置付け:**

- **passive delay と active delay を含む Vehicle 当たり平均遅延**
- **特別な独立性能指標ではない**
- 最重要指標 **ACWWT** を定義・解釈するための **前段となる基礎時間量**
- **全方式共通の network-wide 指標**
- **order-control Visit、TVT role、Node の制御方式に依存しない**

§31.6 の Visit 数による ACWT 導出は **network 全体の最新定義として不採用**。**本 §31.18.6 を最新正本**とする。

#### 31.18.7 ACWWTの最新定義

Vehicle **z** の true VOT を **C_z** とする。

**ACWWT:**

\[
\text{ACWWT} = \frac{1}{N} \sum_z C_z \text{CW}_z = \frac{1}{N} \sum_z C_z \bigl(\text{TT}_z - T_{\min,z}\bigr)
\]

**位置付け:**

- 各 Vehicle の **network 全体の累積 waiting time** を **true VOT** で重み付け
- 本研究の方式比較における **最重要指標**
- **high-VOT Vehicle** の時間損失をより大きく評価
- **signalized UXsim、FCFS、BATCH、TVT-MP、混在 network** へ **同じ式**を適用
- TVT-MP の **nonparticipating Vehicle にも true VOT を適用**
- **申告 VOT の有無**や **取引参加状態**によって評価対象から **除外しない**

§31.7 の Visit 数による ACWWT 導出は **network 全体の最新定義として不採用**。**本 §31.18.7 を最新正本**とする。

#### 31.18.8 Visit概念の今後の用途

**order-control Visit** は次の用途に **限定**する。

- TVT-MP 取引形成
- BATCH 形成
- baseline / Candidate / actual passage 比較
- Buyer / Seller role 評価
- Node 単位順位
- transaction audit
- 取引の直接効果分析

**order-control Visit を次には使わない。**

- network 全体 ACWT の母集団
- network 全体 ACWWT の母集団
- network 全体の経路長
- 自由流所要時間
- travel time
- route-conditioned delay
- signalized UXsim を含む共通総合評価の分母

**Visit 単位 AWT・AWWT:**

- **network 全体の中核指標から外す**
- 単一 Node、取引直接効果、Buyer・Seller 評価等で必要になった場合の **補助分析候補**
- **現時点では正式実装を保留**
- Node 別・時間帯別詳細分析と同様、**必要になった場合だけ追加**

#### 31.18.9 主表の訂正

§31.8 の旧主表案は **歴史的検討として残す**が、**最新主表から次を外す**。

- Visit 単位 AWT
- 平均 Visit 数
- Visit 単位 AWWT

**最新主表の候補列:**

- 方式
- 平均実走行 Link 数
- 平均実走行経路自由流時間
- 平均旅行時間
- 総旅行時間
- ACWT
- ACWWT
- VOT 加重累積 waiting time 総量
- 最終 Vehicle 完走時刻
- 全車完走
- 交通解消

**行:**

- signalized UXsim
- FCFS
- BATCH
- TVT-MP
- 必要に応じて **混在制御 network**

**重要:**

- **ACWT は平均遅延と同じ時間量**なので、**平均遅延を別の独立列として重複表示しない**
- **総累積 waiting time** は **N × ACWT**
- ACWWT に対応する総量は **N × ACWWT**
- **平均旅行時間**は **経路長差と waiting time の双方**を含む
- **平均実走行 Link 数**と **平均自由流時間**は **経路差を説明する補助値**

#### 31.18.10 Role別評価との分離

**Network-wide ACWT・ACWWT:**

- **全 Vehicle**、または **固定 Vehicle 集合**について計算する

**Nonparticipating:**

- 出発から trip end まで **固定された Vehicle 属性**
- 同じ **600 台**について FCFS と TVT-MP の ACWT・ACWWT を計算できる

**Buyer・Seller:**

- 固定 Vehicle 属性ではなく **取引ごとの Visit role**
- **network-wide ACWT・ACWWT の定義へ混入しない**
- **Role-Visit 方式**か **role 経験 Vehicle 方式**かは **引き続き未確定**
- **Seller unsatisfied 率は必須**
- **新規補償込み独自式は導入しない**

#### 31.18.11 実装前の最小検証

正式実装前に、**単車両・無交通の最小 trial** で次を確認する。

**最低限:**

- 1 Link
- 複数 Link
- 内部 Node 通過
- external Node を途中経由
- 最終 OD Link
- 全 Link 同一長・速度
- 必要なら異質 Link 長・速度

**確認:**

- `Vehicle.travel_time`
- `Vehicle.traveled_route()` の Link 列
- **Σ length / free_flow_speed**
- Node 通過による **固定追加時間の有無**
- timestep 境界の **off-by-one**
- **trip end 時刻**
- **CW_z** が **0** または **UXsim 離散処理上の期待値**になること
- **`Vehicle.departure_time`**
- **`Vehicle.traveled_route(include_departure_time=True)`** で得られる **予定出発時刻**
- **`Vehicle.log_t_link`** に記録された **最初の Link 進入時刻**
- **予定出発時刻**と **最初の Link 進入時刻**の **差**
- **起点で network へ直ちに進入できる無交通条件**では、その差が **0** または **UXsim の離散処理上の期待値**になること
- **起点で network へ進入できず待つ条件**では、その **待ち時間**が **`Vehicle.travel_time`** および **`CW_z`** へ **含まれる**こと

**起点流入待ち（理由）:**

- `Vehicle.end_trip()` の **`travel_time`** は **`arrival_time − departure_time`** で計算される
- したがって、**予定出発後**に **最初の Link へ入るまでの待ち時間**も **実旅行時間**へ **含まれる**
- **ACWT・ACWWT** の **方式共通 network 定義**では、この **起点流入待ちを欠落させてはならない**
- **単車両・無交通 trial** で、**予定出発時刻**、**最初の Link 進入時刻**、**trip end 時刻**の **境界関係**を **実作動確認**する

この検証前に、**T_{min,z} = Σ length/u** が **数値的に完全一致する**と **確定事項として扱わない**。

**最新参照（2026-11-04）:** 本節で列挙した **単車両・無交通最小検証は完了**した。**詳細結果**は **§31.18.12**。**全 5 ケース合格**。**次の課題**は **reference replay helper** と **route signature / cache** 設計（§31.18.12.9）。

#### 31.18.12 単車両・無交通reference replayによるT_min,z実作動検証

**最新正本（T_{\min,z}）:** 本 **§31.18.12**。**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`（**production・tests 非変更**、**output file なし**、**console 検証**）。

##### 31.18.12.1 検証目的

方式共通 **network-wide** 累積 waiting time の基礎式:

\[
\text{CW}_z = \text{TT}_z - T_{\min,z}
\]

について、**T_{\min,z}** を **どのように算定すべきか**を **実作動検証**した。

**確認対象:**

- `Vehicle.travel_time`
- `Vehicle.traveled_route()`
- `Vehicle.log_t_link`
- `departure_time`
- **最初の Link 進入時刻**
- **trip end 時刻**
- **Node 通過**
- **external Node 中継**
- **最終 OD Link**
- **異質 Link**
- **起点流入待ち**
- **timestep 境界**
- **`move_remain`**
- **浮動小数点境界**

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`

**変更禁止（実施）:** **production**、**tests**、**既存 research script** は **変更していない**。**output file** は **生成せず**、**console 上**で検証した。

##### 31.18.12.2 初回仮説とCASE 1による反証

**初回仮説:**

\[
T_{\min,z} = \sum (\text{length} / \text{free\_flow\_speed})
\]

**CASE 1:**

- **1 Link**
- length **200 m**、free-flow speed **60/3.6 m/s**
- **解析的自由流時間 12 秒**
- **departure_time T=0**
- **first Link entry T=1**（秒表記は log / traveled_route 上の観測）
- **trip end T=13**
- **`Vehicle.travel_time` = 13 秒**

単純な **Σ(length/u)=12 秒** を使うと、

\[
\text{CW}_z = 13 - 12 = 1 \text{ 秒}
\]

となった。

この **1 秒**は **混雑**や **Node 通過待ち**ではなく、UXsim の **処理順**により、**予定出発 T=0** の Vehicle が **T=0 末尾**に **home から wait** へ移り、**T=1** の **`Node.generate()`** で **最初の Link** へ進入する **起点流入境界**として生じた。

したがって、**Σ(length/u) だけ**では **UXsim 上の最小旅行時間**を **常に表せない**。

##### 31.18.12.3 第二仮説とCASE 4による反証

**CASE 1〜3** の結果から、一時的に次を仮定した。

\[
T_{\min,z} = 1 \text{ 秒} + \sum (\text{length}/u)
\]

しかし **CASE 4** で **反証**された。

**CASE 4:**

- **3 Link**
- Link 1: length **120 m**、speed **10 m/s**、解析時間 **12 秒**
- Link 2: length **200 m**、speed **20 m/s**、解析時間 **10 秒**
- Link 3: length **300 m**、speed **15 m/s**、解析時間 **20 秒**
- **Σ(length/u)=42 秒**
- departure **T=0**
- first Link entry **T=1**
- Link 2 entry **T=13**
- Link 3 entry **T=23**
- trip end **T=42**
- **`Vehicle.travel_time`=42 秒**

したがって、

\[
1 + \sum(\text{length}/u) = 43 \text{ 秒}
\]

ではなく、**実際の無交通旅行時間**は **42 秒**だった。

**不採用:**

\[
T_{\min,z} = 1 + \sum(\text{length}/u)
\]

という **一般式**は **採用しない**。

##### 31.18.12.4 CASE 4 trajectoryによる原因確認

**CASE 4** の **trajectory trace**（`--case4-trajectory-trace`）では次を確認した。

- **T=1** で **l1** へ進入し、**同じ timestep 内**に **x=10 m** まで進行
- **T=13** で **l2** へ進入し、**同じ timestep 内**に **x=20 m** まで進行
- **T=23** で **l3** へ進入し、**同じ timestep 内**に **x=15 m** まで進行
- **T=42** で **l3 終端**へ到達し、**同じ timestep** に **trip end**
- **Node 自体**に **固定通過時間はない**
- **Link 進入 timestep 内の移動**、**move_remain**、**速度比換算**、**trip-end 境界**、**浮動小数点表現**が **UXsim 上の最短旅行時間**へ **影響**する

**重要:**

- **起点流入境界 1 秒**を **常に**解析自由流時間へ **加算してはならない**
- **Node 数**や **Link 数**ごとの **固定補正**も **行わない**
- **解析式**で UXsim の **離散時間挙動**を **完全再現しようとしない**

##### 31.18.12.5 正式なT_min,z定義

Vehicle **z** の **正式な T_{\min,z}** は、次の **UXsim reference replay** によって求める。

**reference World 条件:**

- 実 World で Vehicle **z** が **実際に通過したものと同一の Link 列**
- **同じ Link 順序**
- 各 Link の **length**、**free_flow_speed**、**jam_density**、**number_of_lanes**
- **同じ DELTAT**、**同じ DELTAN**
- **Vehicle 1 台**、**departure timestep 0**
- **route を明示的に固定**
- **他 Vehicle なし**
- **signal なし**、**order-control なし**、**Node capacity なし**
- **capacity_in / capacity_out** による **追加待ちなし**
- **user_function なし**、**congestion なし**

この reference World における **`Vehicle.travel_time`** を **uxsim_reference_minimum_trip_time_s** とし、**正式な T_{\min,z}** とする。

\[
T_{\min,z} = \text{uxsim\_reference\_minimum\_trip\_time\_s}(\text{actual\_route}_z)
\]

\[
\text{CW}_z = \text{TT}_z - T_{\min,z}
\]

**解析値** **Σ(length / free_flow_speed)** は **参考値**として **保持してよい**が、**正式な T_{\min,z} として使用しない**。

##### 31.18.12.6 Route signature

将来の本実装では、Vehicle ごとに reference World を **個別実行せず**、**同一経路条件**を **route signature** でまとめる。

**route signature 候補:**

- **Link 名の順序**
- 各 Link の **length**
- 各 Link の **free_flow_speed**
- 各 Link の **jam_density**
- 各 Link の **number_of_lanes**
- **DELTAT**
- **DELTAN**

**同一 signature** の Vehicle は **同じ reference replay 結果**を **共有**する。

**留保（未確定）:**

- 現在の **検証 script** では **memory 上**に signature を **表示しただけ**
- **永続 cache** は **未実装**
- 本実装の **cache key 構成**は **まだ最終確定していない**
- reference World が **実 World の最小旅行時間**に **影響する全条件**を **保持しているか**、**実装前**に **追加確認**する
- **不要な制御属性**を signature へ **混入させない**
- **最小旅行時間**へ **影響する属性**を **欠落させない**

**最新参照（2026-11-04）:** **route signature 候補属性**の **感度検証**は **§31.18.13** で **完了**。**現時点**の **物理的必須属性**は **Link 順序**、**length**、**free_flow_speed**、**DELTAT**。**最新 cache key 候補**は **§31.18.13.10**。**最終 cache 設計**は **未完了**（本節の **候補リスト**は **検討過程の歴史的記録**として **残す**）。

##### 31.18.12.7 5ケースの確定結果

| CASE | 概要 | analytical Σ(length/u) | replay T_{\min,z} | actual TT_z | CW_z | 結果 |
|------|------|------------------------|-------------------|-------------|------|------|
| **1** | 1 Link | **12 s** | **13 s** | **13 s** | **0 s** | **PASS** |
| **2** | 3 Link・内部 Node | **36 s** | **37 s** | **37 s** | **0 s** | **PASS**（Node 通過ごとの固定追加時間 **なし**） |
| **3** | external 途中経由・3 Link | **36 s** | **37 s** | **37 s** | **0 s** | **PASS**（intermediate external 前後・**最終 OD Link**・**traveled_route() 3 Link**） |
| **4** | 異質 3 Link | **42 s** | **42 s** | **42 s** | **0 s** | **PASS**（**1+Σ** を **反証**） |
| **5** | capacity_in 起点待ち・1 Link | **12 s** | **13 s** | **17 s** | **4 s** | **PASS** |

**CASE 5 補足:**

- **scheduled departure T=0**、**actual first Link entry T=5**、**reference first Link entry T=1**
- **additional origin wait = 4 秒**（**起点 vertical queue 待ち**が **CW_z** へ **含まれる**）

**全体:** **All cases passed**（検証 script 実行結果）。

##### 31.18.12.8 ACWT・ACWWTへの反映

**最新定義:**

\[
\text{TT}_z = \text{実 World の Vehicle.travel\_time}
\]

\[
T_{\min,z} = \text{同一実走行経路の UXsim reference replay における Vehicle.travel\_time}
\]

\[
\text{CW}_z = \text{TT}_z - T_{\min,z}
\]

\[
\text{ACWT} = \frac{1}{N} \sum_z \text{CW}_z
\]

\[
\text{ACWWT} = \frac{1}{N} \sum_z C_z \text{CW}_z
\]

**位置付け:**

- **ACWT** は **active delay** を含む **Vehicle 当たり平均遅延**
- **ACWT** は **ACWWT** の **前段**となる **基礎時間量**
- **ACWWT** が **方式比較の最重要指標**
- **signalized UXsim、FCFS、BATCH、TVT-MP、混在 network** へ **共通適用**
- **order-control Visit 数**は **使わない**
- **external Node、中継 external、最終 OD Link、order-control 対象外 Node** も **欠落しない**

##### 31.18.12.9 次の実装課題

1. **検証 script** の **static validation**、**全 5 ケース**、**failure history** を **正本化**（本 **§31.18.12**）
2. **route signature** に必要な **Link・World 属性**を **読取り専用**で **確定**

**最新注記（2026-11-04）:** **route signature 候補属性**の **感度検証**（**CASE 6A〜6E-2**）は **完了**（**§31.18.13**）。**次**は **float key**、**audit identity**、**DELTAN=1 validation**、**reference 標準条件**、**cache lifecycle** の **設計**（**§31.18.13.11**）。

3. **reference replay helper** の **設計**
4. **memory cache** の **key・value・lifecycle** 設計
5. 実 World **Vehicle ごと**の **actual route 抽出**
6. **route signature ごと**の **reference replay**
7. Vehicle ごとの **TT_z、T_{\min,z}、CW_z** 算出
8. 全 Vehicle の **ACWT** 算出
9. **true VOT** を使った **ACWWT** 算出
10. **Nonparticipating 固定 600 台**の **ACWT・ACWWT** 算出
11. **FCFS、BATCH、TVT-MP、signalized UXsim** **共通検証**
12. **小規模 trial** で **manual 再計算**と **一致確認**
13. **その後**に **3,000 台 output** へ **適用**
14. **評価指標実装後**に **高速化調査**へ進む

**禁止:**

- **Σ(length/u)** を **正式 T_{\min,z}** として **使用**
- **1 + Σ(length/u)** を **正式 T_{\min,z}** として **使用**
- **Visit 数**から **T_{\min,z}** を **推測**
- Vehicle ごとに **無条件**で **reference replay** を **重複実行**
- **route signature 検証前**に **cache** を **production** へ **実装**
- **production** を **直接変更**して **定義検証**を **省略**

#### 31.18.13 Reference replay route signature属性感度検証

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`（**CASE 1〜5** は **変更なし**。**console のみ**、**file 出力なし**）。

##### 31.18.13.1 目的

**同一実走行経路**の **無交通 UXsim reference replay** を **route signature 単位**で **共有**するため、**物理的 T_{\min,z}** へ **必要な属性**と **不要な属性**を **分離**した。

**追加した感度 CASE:**

- **CASE 6A:** jam_density
- **CASE 6B:** number_of_lanes
- **CASE 6C:** Link 名
- **CASE 6D:** DELTAT
- **CASE 6E-1:** DELTAN 変更、**REACTION_TIME 固定**
- **CASE 6E-2:** DELTAN 変更、**DELTAT 固定**

**全体:** **All cases passed**（**CASE 1〜5** も **再合格**）。

##### 31.18.13.2 共通検証条件

感度 CASE では **原則**として次を使用した。

- **3 Link 直列**
- 各 Link **length = 200 m**
- 各 Link **free_flow_speed = 60/3.6 m/s**
- **Vehicle 1 台**、**departure timestep = 0**、**route 固定**
- **他 Vehicle なし**、**congestion なし**
- **signal なし**、**order-control なし**、**Node flow_capacity なし**、**user_function なし**
- **file 出力なし**

**capacity 経由影響**を **除外**する CASE では、

\[
\text{NON\_BINDING\_CAPACITY} = 1000000.0
\]

を **capacity_in** と **capacity_out** へ **明示的に設定**した。

これにより、

- **自由走行・離散時間境界**への **直接影響**
- **capacity 経由**の **間接影響**

を **分離**した。

##### 31.18.13.3 CASE 6A: jam_density

**変更:** jam_density = **0.05**、**0.12**、**0.45**（Link ごと）

**固定:** **length**、**free_flow_speed**、**number_of_lanes = 1**、**DELTAN = 1**、**REACTION_TIME = 1**、**DELTAT = 1**、**Link 順序**、**route**、**非拘束 capacity**

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **37 s** |
| reference replay | **37 s** |
| CW_z | **0 s** |
| CASE 2 との差 | **0 s** |
| 判定 | **PASS** |

**限定的結論:** **単車両**、**leader なし**、**capacity 非拘束**の reference replay では、**jam_density** は **物理的 T_{\min,z}** を **変えなかった**。**jam_density** は **派生 capacity** へ **影響し得る**ため、reference World では **capacity_in / out** を **非拘束値**へ **固定**する。**この条件**では **jam_density** を **物理 cache key** へ **含める必要はない**。

##### 31.18.13.4 CASE 6B: number_of_lanes

**変更:** number_of_lanes = **2**、**3**、**2**（Link ごと）

**固定:** **length**、**free_flow_speed**、**jam_density**、**DELTAT = 1**、**DELTAN = 1**、**route**、**非拘束 capacity**、**Vehicle 1 台**（**leader なし**）

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **37 s** |
| reference replay | **37 s** |
| CW_z | **0 s** |
| CASE 2 との差 | **0 s** |
| 判定 | **PASS** |

**限定的結論:** **単車両**、**leader なし**、**capacity 非拘束**の reference replay では、**number_of_lanes** は **物理的 T_{\min,z}** を **変えなかった**。**number_of_lanes** は **capacity** や **leader spacing** へ **影響し得る**が、**今回の reference World** では **それらを除外**している。**この条件**では **number_of_lanes** を **物理 cache key** へ **含める必要はない**。

##### 31.18.13.5 CASE 6C: Link名

**変更:** **l1、l2、l3** を使わず、**link_alpha**、**link_beta**、**link_gamma** へ変更。**物理条件**は **CASE 2** と **同一**（**CASE 6C** は **UXsim 既定 capacity**、**NON_BINDING_CAPACITY なし**）。

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **37 s** |
| reference replay | **37 s** |
| CW_z | **0 s** |
| CASE 2 との差 | **0 s** |
| 判定 | **PASS** |

**結論:**

- **Link 名**は **物理的 T_{\min,z}** へ **影響しない**
- **Link 名**は **物理 cache key** の **必須属性ではない**

**ただし** Link 名は **監査情報**として **有用:**

- **route 対応確認**
- **debug**
- **cache 衝突診断**
- **人間による経路確認**
- **出力監査**

したがって **物理 signature** と **audit identity** を **分離**する。

##### 31.18.13.6 CASE 6D: DELTAT

**変更:** **DELTAN = 1** を維持、**REACTION_TIME = 0.5 s**、**DELTAT = 0.5 s**

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **36 s** |
| 同一 DELTAT の reference replay | **36 s** |
| CW_z | **0 s** |
| DELTAT = 1 の **診断 reference**（**CW_z に不使用**） | **37 s** |
| 判定 | **PASS** |

**結論:**

- **DELTAT** は **物理的 T_{\min,z}** へ **影響する**
- **actual World** と **reference World** で **DELTAT** を **一致**させる **必要がある**
- **DELTAT** は **物理 cache key** の **必須属性**

**DELTAT** が **異なる reference 結果**を **CW_z 算出**へ **使用してはならない**。

##### 31.18.13.7 CASE 6E-1: DELTAN変更、REACTION_TIME固定

**条件:** **DELTAN = 2**、**REACTION_TIME = 1 s**、**DELTAT = 2 s**

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **36 s** |
| reference replay | **36 s** |
| CW_z | **0 s** |
| 判定 | **PASS** |

**解釈:**

- **REACTION_TIME 固定**で **DELTAN** を変えたため **DELTAT も変化**した
- **この結果**を **DELTAN 単独**の効果として **読まない**
- **DELTAN 単独影響**は **CASE 6E-2** で **確認**する

##### 31.18.13.8 CASE 6E-2: DELTAN変更、DELTAT固定

**条件:** **DELTAN = 2**、**REACTION_TIME = 0.5 s**、**DELTAT = 1 s**、**capacity_in / out 非拘束**

**結果:**

| 量 | 値 |
|----|-----|
| actual travel_time | **37 s** |
| reference replay | **37 s** |
| CW_z | **0 s** |
| CASE 2 との差 | **0 s** |
| 判定 | **PASS** |

**限定的結論:** **単車両**、**leader なし**、**capacity 非拘束**、**DELTAT 固定**の条件では、**DELTAN** は **物理的 T_{\min,z}** を **変えなかった**。

**ただし** **DELTAN** は **platoon size** であり、**capacity check** や **leader spacing** へ **影響し得る**。**一般的な signature** から **完全に除外**できるかは **未確定**。

**本研究**では **FCFS・BATCH・TVT-MP** が **DELTAN = 1** を **要求**するため、**当面**は次とする。

- **評価対象 World** の **DELTAN = 1** を **前提条件**として **検証**
- **reference World** も **DELTAN = 1**
- **DELTAN** を **可変一般化しない**
- **cache key 最小化**のため **無断で除外**するのではなく、**World 前提条件**として **固定**する

##### 31.18.13.9 属性分類

**1. 物理的 T_{\min,z} に必須と確認済み:**

- **Link 順序**
- 各 Link の **length**
- 各 Link の **free_flow_speed**
- **DELTAT**

**2. 今回の reference 条件では物理的 T_{\min,z} を変えなかった:**

- **jam_density**
- **number_of_lanes**
- **Link 名**
- **DELTAN**（**DELTAT 固定・単車両・capacity 非拘束**に **限定**）

**3. Reference World で待ち要因除外のため固定:**

- **capacity_in = NON_BINDING_CAPACITY**
- **capacity_out = NON_BINDING_CAPACITY**
- **signal なし**、**order-control なし**、**Node flow_capacity なし**
- **Node user_function なし**、**Link user_function なし**
- **Vehicle 1 台**、**route 固定**

**4. 物理計算には不要だが監査・cache 識別に有用:**

- **Link 名列**

**5. 未確定:**

- **production 用 cache key** の **最終形式**
- **float 値**の **正規化または丸め**
- **cache lifecycle**
- **Link 名**を **物理 key** と **別 audit field** へ持つ **具体的方法**
- **DELTAN** を **1 以外**へ **一般化**する場合の **扱い**

##### 31.18.13.10 物理cache key候補

**現時点の有力候補:**

```
(
    DELTAT,
    (
        (length_1, free_flow_speed_1),
        (length_2, free_flow_speed_2),
        ...
    ),
)
```

**重要:**

- **Link 順序**を **維持**する
- **Link 名**を **物理値**として **扱わない**
- **float** を **無断で丸めない**
- **actual World** から取得した **length** と **free_flow_speed** の **値**を **使用**する
- **production 実装前**に、**float key** の **安定性**を **検討**する
- **DELTAN = 1** を **World 前提条件**として **独立検証**する
- **Link 名列**は **audit identity** として **別保持**する **候補**

**本小節**で **cache** を **実装しない**。

**最新参照（2026-11-04）:** **float 安全性**と **物理識別値**の **検証**は **§31.18.14** で **完了**。**数値**は **丸めず**、**actual World** の **float** を **そのまま**使用する。**speed** は **`link.u`** を **使用**する（**`free_flow_speed` 表示値だけ**に **依存しない**）。**Link 名**は **audit identity** へ **分離**。**最新候補**は **§31.18.14.10**。**production 実装**は **未着手**。

##### 31.18.13.11 次の作業

1. **float 値**を **物理 cache key** へ使う **方法**を **確定**

**最新注記（2026-11-04）:** **float key**（**物理識別値**）の **検証**は **完了**（**§31.18.14**）。**次**は **audit identity**、**DELTAN=1 validation**、**reference 標準条件**、**共有辞書**の **所有者・存続範囲・保存値** の **設計**（**§31.18.14.12**）。

2. **audit identity** としての **Link 名列**の **保持方法**を **確定**
3. **DELTAN = 1 前提**の **validation 方法**を **確定**
4. **reference World 標準条件**を **確定**
5. **cache key**、**cache value**、**cache lifecycle** を **設計**
6. **reference replay helper** を **設計**
7. **小規模 route signature 重複 case** で **cache hit** を **検証**
8. **Vehicle 別 CW_z** 算出
9. **ACWT** 算出
10. **ACWWT** 算出
11. **Nonparticipating 固定 600 台**
12. **4 方式共通検証**
13. **小規模 manual 一致確認**
14. **3,000 台 output** 適用
15. **その後**に **高速化調査**

**禁止:**

- **jam_density** や **number_of_lanes** を **根拠なく物理 key** へ **追加**
- **Link 名**を **物理属性**として **扱う**
- **DELTAT** を **key** から **落とす**
- **float 値**を **根拠なく丸める**
- **DELTAN 一般化**を **検証なし**に **採用**
- **reference World** へ **capacity 待ち**を **残す**
- **cache 設計前**に **production** へ **実装**

#### 31.18.14 同一走行条件の物理識別値とfloat安全性の検証

**検証スクリプト:** `research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`（**CASE 1〜6** **変更なし**。**CASE 7A〜7G** **追加**。**console のみ**）。

##### 31.18.14.1 目的

**同じ走行条件**の **reference replay 結果**を **安全に共有**するため、次を **実作動確認**した。

- **同じ数値条件**を **同一条件**として **扱える**こと
- **異なる Link 順序**を **別条件**として **扱える**こと
- **異なる DELTAT** を **別条件**として **扱える**こと
- **微小に異なる length** を **別条件**として **扱える**こと
- **Python** が **実際に同じ float** として **保持した値**は **同一条件**として **扱う**こと
- **Link 名**を **物理条件**から **分離**できること
- **実際の移動計算**に用いる **`link.u`** を **使用**すること
- **数値**を **無断で丸めない**こと

**追加 CASE:** **7A** 同じ数値、**7B** Link 名のみ、**7C** Link 順序、**7D** DELTAT、**7E** length 微小差、**7F** speed 微小差、**7G** **`link.u`** と **速度変更**

**既存 CASE 1〜6** も **再合格**。**全体:** **All cases passed**

##### 31.18.14.2 正式な物理識別値候補

**同一評価処理内**で **reference replay 結果**を **共有**するための **物理識別値候補:**

```python
physical_route_key = (
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

**意味:**

- **第 1 要素**は **実 World** の **DELTAT**
- **第 2 要素**は **実走行順**を **維持**した **Link 物理条件列**
- 各 Link について **length** と **`link.u`** を **保持**
- **Link 順序**を **変更しない**
- **Link 名**を **物理識別値**へ **含めない**
- **`round`** を **使用しない**
- **表示用文字列**を **正式な識別値**として **使用しない**

**hash 可能な tuple** として、**同一評価処理内**の **memory 辞書**の **key 候補**とする。**永続保存形式**は **未確定**。

##### 31.18.14.3 CASE 7A: 同じ数値

**条件:** **DELTAT=1**、**3 Link**、各 **length=200**、各 **u=60/3.6**。**同じ数値**を **別 object** から **2 本作る**。

**結果:** **物理識別値同一**、**hash 同一**、**1 つ目**で **辞書保存**した値を **2 つ目**で **取得**、**entry 数=1**、**PASS**

**結論:** **同じ数値条件**は **安全に同一条件**として **扱える**。

##### 31.18.14.4 CASE 7B: Link名だけ異なる

**比較:** **l1/l2/l3** と **link_alpha/link_beta/link_gamma**。**length・u・DELTAT・順序**は **同一**。

**結果:** **物理識別値同一**、**hash 同一**、**辞書 entry=1**、**Link 名列は異なる**、**PASS**

**結論:**

- **Link 名**は **物理 T_{\min,z}** を **区別**するためには **不要**
- **物理条件**が **完全に同じ**なら **reference replay 結果**を **共有**できる
- **Link 名列**は **経路対応確認・監査・debug・人間向け表示**のため **別保持**

**確認用 Link 名列候補:**

```python
route_audit_identity = tuple(
    link.name
    for link in actual_route_links
)
```

**物理識別値**と **確認用 Link 名列**を **混同しない**。

##### 31.18.14.5 CASE 7C: Link順序

**比較:**

- 経路 1: **(120, 10)**、**(200, 20)**、**(300, 15)**
- 経路 2: **(200, 20)**、**(120, 10)**、**(300, 15)**

**結果:** **物理識別値異なる**、**hash 異なる**、**辞書 entry=2**、**PASS**

**結論:** **同じ Link 物理条件の集合**でも **通過順序**が **異なれば別条件**。**Link 順序**を **必ず維持**する。

##### 31.18.14.6 CASE 7D: DELTAT

**比較:** **DELTAT=1.0** と **0.5**（**Link 条件同一**）

**結果:** **物理識別値異なる**、**hash 異なる**、**辞書 entry=2**、**PASS**

**結論:** **DELTAT** が **異なる reference replay 結果**を **共有してはならない**。**DELTAT** は **物理識別値の必須要素**。

##### 31.18.14.7 CASE 7E: lengthの微小差

**比較:** **length=200.0** と **200.00000000000003**

**結果:** **Python 保持 float は異なる**、**正式物理識別値は異なる**、**hash 異なる**、**辞書 entry=2**、**PASS**

**診断:** **`round(length, 10)`** では **両方 200.0** となった。

**結論:** **無断の丸め**は **異なる物理条件**を **同じものへ潰す**。**length** を **正式識別値**へ入れる際は **`round` しない**。**actual World** の **float** を **そのまま**使用する。

##### 31.18.14.8 CASE 7F: speedの微小差

**比較:** **u=60/3.6** と **u=(60/3.6)+1e-15**

**実測:** **両方** **16.666666666666668** として **保持**。**物理識別値同一**、**hash 同一**、**辞書 entry=1**、**PASS**

**結論:**

- **10 進表記**上の **式が違う**だけで **別条件**と **判断しない**
- **Python** が **実際に保持した float** に **従う**
- **同じ float** なら **同一条件**、**異なる float** なら **別条件**
- **表示文字列の見た目**で **判断しない**

##### 31.18.14.9 CASE 7G: link.u

**検証用 World** の **Link**（**simulation なし**）。

**変更前:** **free_flow_speed=16.666666666666668**、**u=16.666666666666668**

**`change_free_flow_speed(10.0)` 後:** **free_flow_speed=10.0**、**u=10.0**

**結果:** **変更前後**で **物理識別値異なる**、**hash 異なる**、**辞書 entry=2**、**PASS**

**結論:**

- **自由走行**は **`link.u`** を **使用**
- **物理識別値**も **`link.u`** を **使用**
- **`change_free_flow_speed()`** は **`free_flow_speed`** と **`u`** を **同時更新**

##### 31.18.14.10 確定方針

**物理識別値:** **DELTAT**、**Link 順序**、各 Link の **length**、各 Link の **`u`**

**使用方法:** **Python tuple**、**memory 辞書 key**、**float そのまま**、**round しない**、**文字列化しない**

**別保持:** **Link 名列**は **audit identity**、**物理識別値へ混入しない**

**前提:** **DELTAN=1**、**reference World 標準条件**は **§31.18.13**、**同一評価処理内のみ**、**永続・別 process 共有は未検証**、**production 未実装**

##### 31.18.14.11 未確定事項

- **辞書**の **所有者**（**関数 / 評価処理**）
- **生成・破棄**タイミング
- **保存値**の **構造**
- **同一物理識別値**に **複数 Link 名列**が **対応**した場合の **監査記録**
- **duplicate route 数**、**reuse 回数**等の **軽量 counter**
- **failure 時**の **診断情報**
- **production 実装場所**
- **reference replay helper** との **責務分離**

##### 31.18.14.12 次の作業

1. **Link 名列**を **audit identity** として **保持**する **具体的方法**を **確定**
2. **DELTAN=1 前提**の **validation 方法**を **確定**
3. **reference World 標準条件**を **確定**
4. **同一評価処理内** **共有辞書**の **所有者**と **存続範囲**を **設計**
5. **保存値**の **構造**を **設計**
6. **軽量 counter** を **設計**
7. **failure 時診断**を **設計**
8. **reference replay helper** を **設計**
9. **重複経路**を含む **小規模 case** で **共有動作**を **検証**
10. **Vehicle 別 CW_z** 算出
11. **ACWT** 算出
12. **ACWWT** 算出
13. **Nonparticipating 固定 600 台**
14. **4 方式共通検証**
15. **小規模 manual 一致確認**
16. **3,000 台 output** 適用
17. **その後**に **高速化調査**

**禁止:**

- **float** を **`round`**
- **decimal 文字列**を **正式物理識別値**にする
- **Link 名**を **物理値**として **扱う**
- **Link 順序**を **失う集合型**
- **DELTAT** を **省略**
- **`free_flow_speed` 表示値だけ**を参照し **`link.u`** を **無視**
- **同一評価処理を越えて** **無検証再利用**
- **設計確定前**の **production 実装**

**最新参照（2026-11-04）:** **Link 名 audit identity** の **保持設計**は **§31.18.15** で **確定**。**次**は **実装前設計 2/4** の **DELTAN=1 validation**。**production 実装**は **未着手**。

#### 31.18.15 Link名列をaudit identityとして保持する設計

**位置付け:** **実装前設計 1/4**。**production コードは実装しない**。**CASE 7B**（**§31.18.14.4**）を前提とする。

##### 31.18.15.1 目的

**1 つの physical_route_key** に **複数の route_audit_identity** が対応するとき、**Link 名列**を **失わず**、**重複登録せず**、**最初に観測した順序**で **保持**する。

**physical_route_key** は **reference replay 結果を共有できるか**を判断する値である。**route_audit_identity** は、**どの実走行 Link 列**がその結果を利用したかを **後から確認**する値である。**両者を混同しない**。

##### 31.18.15.2 物理識別値とaudit identityの分離

**物理識別値候補**（**§31.18.14.2**、**変更しない**）:

```python
physical_route_key = (
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

**Link 名を physical_route_key へ追加しない。**

**理由:**

- **Link 名**が違っても **物理条件**が同じなら、**同じ reference replay 結果**を **共有**できる（**CASE 7B**）
- **Link 名**を **物理識別値**へ入れると、**物理的に同じ経路条件**の **再利用**を **不必要に妨げる**
- **Link 名**は **計算条件**ではなく **監査情報**である

##### 31.18.15.3 route_audit_identityの形式

**候補として確定:**

```python
route_audit_identity = tuple(
    str(link.name)
    for link in actual_route_links
)
```

**要件:**

- **実走行順**を **維持**する
- **list** ではなく **tuple** として **保持**する
- **Link 名**を **文字列**として **明示**する
- **名前を並べ替えない**
- **set** へ **変換しない**
- **同じ Link 名**が経路内で **複数回**現れる場合も、**出現順**と **回数**を **保持**する
- **Vehicle 名**、**OD 名**、**Visit 数**から **Link 名列**を **推測しない**
- **`Vehicle.traveled_route()`** から得た **実走行 Link 列**を **正本**とする

##### 31.18.15.4 1つの物理識別値に対する複数Link名列

**概念上の対応:**

```text
physical_route_key
    ->
ordered unique route_audit_identity collection
```

**要件:**

- **最初に観測した順序**を **維持**する
- **同じ route_audit_identity** を **重複登録しない**
- **異なる route_audit_identity** は **すべて保持**する
- **順序を失う単純な set だけ**を **正本にしない**
- **重複確認**を速くする必要があっても、**表示順**を保持する構造を **別に持つ**
- 将来の実装は、**初学者が追える明示的な形**を採る

**現時点の有力な概念構造**（**コードは未実装**）:

```python
audit_identities_by_physical_key = {
    physical_route_key: [
        route_audit_identity_1,
        route_audit_identity_2,
    ]
}
```

##### 31.18.15.5 重複判定と観測順序

**同じ physical_route_key** の **登録済み Link 名列**に、今回の **route_audit_identity** と **完全一致**する **tuple** がある場合:

- **新規追加しない**
- **重複回数**は、将来の **軽量 counter** で数える **候補**とする（**counter 自体は今回実装しない**。**4/4** で扱う）

**完全一致しない**場合:

- **新しい route_audit_identity** として **末尾**へ **追加**する
- **最初に観測した順序**を **維持**する

**同一 Link 名列**の判定に、次を **使わない**。

- **部分一致**
- **Link 名集合**の一致
- **先頭だけ**、または **末尾だけ**の一致

**Link 名列が違うだけ**で、**別の reference replay** を **無条件に実行しない**。

##### 31.18.15.6 Vehicleとの対応

各 **Vehicle** の算出時に、将来 **最低限**次を **対応付けられる**ようにする。

- **Vehicle 名**
- **physical_route_key**
- **route_audit_identity**
- **reference replay 最短旅行時間**

**今回確定するのは、Vehicle ごとの算出時に physical_route_key と route_audit_identity の両方を得られることだけ**である。

**全 Vehicle 名**を、物理識別値ごとの確認記録へ **無制限に重複保存するか**は、**実装前設計 4/4** で決める。**今回は決めない**。

##### 31.18.15.7 将来の確認出力

各 **physical_route_key** について、将来 **最低限**次を **表示できる**ようにする。

- **物理識別値**
- **対応する異なる Link 名列の数**
- **各 Link 名列**
- **最初に観測した順序**
- **同じ Link 名列の重複利用回数**
- **reference replay 結果を共有したこと**

**具体的な出力ファイル形式**は **今回決定しない**。

##### 31.18.15.8 不整合候補

次は **不整合**または **設計違反**として扱う **候補**とする。

- **実走行 Link 列**が **空**
- **Link 名**が **None**
- **physical_route_key** 作成に使った Link 列と、**route_audit_identity** 作成に使った Link 列の **長さが異なる**
- **両者が別の Link 列**から作成された
- **Link 順序**を失った
- **Link 名列**を **physical_route_key** へ **混入**した
- **Link 名列が異なるだけ**で **別の reference replay** を **無条件に実行**した

**どの不整合を即時停止にするか**は、**failure 診断設計**（**4/4** に含む）で **最終確定**する。**今回は確定しない**。

##### 31.18.15.9 未実装事項

次は **今回実装しない**。

- **production 用の共有辞書**
- **reference replay helper**
- **Vehicle 別 CW_z**
- **ACWT**
- **ACWWT**
- **CSV 出力**
- **永続保存**
- **別 process 間共有**
- **全 Vehicle 名の保持方法**
- **counter**
- **failure 時の最終例外設計**

##### 31.18.15.10 残りの実装前設計

**実装前設計 1/4 は本節で完了**した。**残りは 3 つ**である。

- **2/4** **DELTAN=1 前提**の **validation 方法**（**未着手**、**次の作業**）
- **3/4** **reference World** の **標準条件**（**未着手**）
- **4/4** **同一評価処理内**で結果を共有する仕組みの **所有者・存続範囲・保存内容・確認記録**（**未着手**）

**2/4 以降の設計・実装・検証には、本節では進まない。**

**最新参照（2026-11-04）:** **DELTAN=1 validation** の **設計**は **§31.18.16** で **確定**。**実装前設計 2/4 完了**。**残り 2 つ**。**次**は **3/4 reference World 標準条件**。**production 実装**は **未着手**。

#### 31.18.16 DELTAN=1前提のvalidation設計

**位置付け:** **実装前設計 2/4**。**production コードは実装しない**。**3/4 以降**の **reference World 全標準条件**、**共有辞書**、**helper 実装**には **進まない**。

**原典（`uxsim/uxsim.py` の `World.__init__`）:**

- **`W.DELTAN = deltan`** として **引数をそのまま保持**する
- **`W.DELTAT = W.REACTION_TIME * W.DELTAN`**
- 引数注釈は **`deltan: int = 5`** だが、**実行時に型や値 1 を検査しない**
- したがって **World 生成時点**では、**DELTAN が整数 1 であることは保証されない**

**原典（`_validate_order_control_deltan`）:**

- **`isinstance(deltan, int)`** かつ **`bool` ではない** かつ **`deltan == 1`** を要求する
- **`Node` 作成時**に **`order_control_type != "none"`** のときだけ呼ぶ
- **signalized UXsim** など **order-control を使わない World** では **呼ばれない**

##### 31.18.16.1 目的

**FCFS、BATCH、TVT-MP** は **個別 Vehicle object** を制御するため、**DELTAN=1** を前提とする。**評価対象 World** と **reference World** の両方を **DELTAN=1** に限定し、**1 以外の World** へ **ACWT・ACWWT 評価**を **適用しない**。

**DELTAN** を **物理識別値**へ追加して **可変一般化しない**。**評価処理全体の前提条件**として **固定**する。

**CASE 6E-2**（**§31.18.13.8**）では、**DELTAT を同じに保った単車両・非拘束条件**で **最短旅行時間は変わらなかった**。ただし **DELTAN** は **platoon size** であり、**capacity 判定**や **Vehicle 表現**へ **影響し得る**。**一般化してよいとは確認していない**。

##### 31.18.16.2 評価処理入口での実World確認

**ACWT・ACWWT 評価処理の開始時**に、評価対象の **実 World** について **一度だけ**次を確認する。

```text
W.DELTAN == 1
```

**1 でなければ**、次へ **進まない**。

- **Vehicle 別経路抽出**
- **reference replay**
- **CW_z**
- **ACWT**
- **ACWWT**

**各 Vehicle、各経路、各 reference replay** で **同じ確認を繰り返さない**。

**理由:**

- **DELTAN** は評価処理中に変化しない **World 設定**
- **評価開始時**に保証できる **不変条件**
- **Vehicle ごとの繰り返し**は不要
- **後段の原因不明エラー**より、**入口で停止**する

##### 31.18.16.3 型と値の厳密確認

**World 生成**は型を **実行時保証しない**（**§31.18.16** 冒頭の原典）。したがって **評価処理側**で、値と型を **自分で確認**する。

**不適合**として扱う。

- **1 以外の整数**
- **0**
- **負数**
- **None**
- **文字列の `"1"`**
- **`1.0` など、整数設定として保証できない型**
- **`True`**（**`bool` は `int` の派生型**であり、**有効な DELTAN=1 として受け入れない**）

**推奨判定の趣旨**（**今回は実装しない**）:

```text
type(W.DELTAN) is int
and W.DELTAN == 1
```

**`isinstance` だけ**では **`True`** を **int** とみなす。**`type(...) is int`** は **`bool` を除外**する。これは既存 **`_validate_order_control_deltan`** が **`bool` を別拒否**する趣旨と揃う。

**不適合時の診断**へ、最低限次を含める。

- **World 名**
- **実際の `W.DELTAN`**
- **実際の型**
- **要求値 1**
- **ACWT・ACWWT の reference replay 評価**では **DELTAN=1** が必要な理由
- **DELTAN=1** で **World を再構築**する必要があること

##### 31.18.16.4 Reference Worldの確認

**実 World:**

- **評価処理の入口**で **一度**確認する
- **不適合**なら **評価全体を開始しない**

**Reference World:**

- **構築直後**、**replay 開始前**に **一度**確認する
- **DELTAN=1** であることを確認する
- **実 World の DELTAN を無条件にコピーしない**
- **標準条件**として **明示的に 1** を設定する
- **1 以外**なら、その **reference replay を実行しない**

**reference World の他の標準条件**（capacity、signal、DELTAT の作り方など）は **3/4** で扱う。**今回確定するのは DELTAN=1 の確認だけ**である。

##### 31.18.16.5 DELTAT一致確認との分離

**DELTAN=1** であっても、**実 World** と **reference World** の **DELTAT** が一致するとは限らない。**`DELTAT = REACTION_TIME × DELTAN`** であり、**REACTION_TIME** が違えば **DELTAT** も違う（**§31.18.13.6**、**CASE 6D**）。

**混同しない。**

- **両 World がそれぞれ DELTAN=1** であること
- **`reference_W.DELTAT == real_W.DELTAT`** であること

**DELTAT 一致**は、**reference World 構築後**に確認する **候補**とする。**一致確認の具体的な構築方法と標準条件**は **3/4** で確定する。

**2/4 の未完了事項:** **DELTAN=1 の確認だけでは十分ではない**。**DELTAT 一致確認**も **別途必要**である。

##### 31.18.16.6 不適合時の停止

**DELTAN 不適合**は、**警告だけで続行しない**。

**理由:**

- **評価方式間**の比較前提が崩れる
- **個別 Vehicle** を前提とする **FCFS、BATCH、TVT-MP** と整合しない
- **reference replay 結果**の意味が変わる可能性がある
- **誤った ACWT・ACWWT** を生成するより、**評価開始前に停止**する

将来の production 実装では、説明を含む **`ValueError`** または **専用の明示的エラー**を **候補**とする。**最終的な例外型とメッセージ形式**は **4/4** の **failure 診断設計**で確定する。

##### 31.18.16.7 既存order-control validationとの関係

既存の **`_validate_order_control_deltan`** があっても、**ACWT・ACWWT 評価処理側の入口確認を省略しない**。

**理由:**

- **signalized UXsim** など、**order-control を使わない比較方式**も評価対象である
- **reference replay** は **order-control なし**で構築する
- **ACWT・ACWWT** は **制御方式に依存しない共通評価**である
- **既存 validation** が **呼ばれない World** があり得る

**同じ helper を再利用するか、評価専用 helper を分けるか**は、**production 実装場所**の設計時に決める。**今回、production helper は作成しない**。

##### 31.18.16.8 将来の処理順序

将来の評価処理の **順序候補:**

1. 評価対象 World が **全車完走済み**であることを確認
2. **評価対象 Vehicle 集合**を確定
3. **実 World** の **DELTAN=1** を確認
4. 実 World の必要な **時間設定**を取得
5. 各 Vehicle の **実走行経路**を抽出
6. **reference World** を構築
7. **reference World** の **DELTAN=1** を確認
8. 実 World と reference World の **DELTAT 一致**を確認
9. **reference replay** を実行
10. **CW_z、ACWT、ACWWT** を算出

**全車完走確認**や **Vehicle 集合確定**との **最終順序**は **4/4** で再確認する。

**今回確定する核心:**

- **replay 開始前**に **両 World** の **DELTAN=1** を保証する
- **不適合なら停止**する

##### 31.18.16.9 将来の確認記録

将来の確認記録として、最低限次を残す **候補**とする。

- **real_world_deltan**
- **reference_world_deltan**
- **deltan_validation_passed**
- **validation 実施回数**
- **不適合時**の **World 名**と **実値**

**保存場所、出力形式、counter の詳細**は **4/4** で確定する。**通常成功時**に **Vehicle ごとの重複記録**は **行わない**。

##### 31.18.16.10 未実装事項

次は **今回実装しない**。

- **production validation helper**
- **reference World 構築**
- **DELTAT 一致 helper**
- **tests**
- **research validation script**
- **counter**
- **CSV 出力**
- **failure 時の最終例外**
- **ACWT・ACWWT 算出**

##### 31.18.16.11 残りの実装前設計

**実装前設計 2/4 は本節で完了**した。**残りは 2 つ**である。

- **3/4** **reference World** の **標準条件**（**未着手**、**次の作業**）
- **4/4** **同一評価処理内**で結果を共有する仕組みの **所有者・存続範囲・保存内容・確認記録**（**未着手**）

**3/4 以降の設計・実装・検証 script 作成には、本節では進まない。**

**最新参照（2026-11-04）:** **reference World 標準条件**の **設計**は **§31.18.17** で **確定**。**実装前設計 3/4 完了**。**残り 1 つ**。**次**は **4/4**。**production 実装**は **未着手**。

#### 31.18.17 Reference World標準条件設計

**位置付け:** **実装前設計 3/4**。**production コードは実装しない**。**4/4** の共有の仕組み、**helper 実装**、**検証 script 作成**には **進まない**。

**検証 script で合格済みの World 設定**（`research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py` の `_make_world`）を、出力抑制と randomness の基準にする。

- **`random_seed=0`**
- **`hard_deterministic_mode=True`**（UXsim 既定は **False**。物理 key へは **含めない**）
- **`print_mode=0`**、**`save_mode=0`**、**`show_mode=0`**、**`show_progress=0`**
- **`vehicle_logging_timestep_interval`** は **渡していない**。UXsim 既定は **1**（**`-1` は logging 無効**）。**`traveled_route()`** を失わないため **1 を維持**する
- 経路固定は **`Vehicle.enforce_route()`**。出発は **timestep 0**、**`departure_time_is_time_step=1`**
- **`NON_BINDING_CAPACITY = 1000000.0`**

**UXsim `Link` 既定:** **`jam_density=0.2`**、**`number_of_lanes=1`**、**`merge_priority=1`**、**`signal_group=[0]`**。**Node** の **`signal=[0]`** は無信号。

##### 31.18.17.1 目的

**reference World** は、実 World の **交通状態**や **制御**を再現する World ではない。

目的は次の **1 点**だけである。

- **実走行 Link 物理条件列**を、**余計な待ちなし**で UXsim 上に再現し、その経路の **UXsim 最短旅行時間**（**`Vehicle.travel_time`**）を取得する

**再現しないもの:**

- 実 World の **他 Vehicle**、**congestion**、**queue**、**spillback**
- **signal 待ち**、**FCFS**、**BATCH**、**TVT-MP**、**priority 待ち**
- **Node flow capacity 待ち**、**Link capacity 待ち**
- **user_function** による動的変更
- **route choice** による別経路選択

**正式 T_{\min,z}** は、この replay の **`travel_time`** である。**Σ(length/u)** でも **1+Σ(length/u)** でも求めない（**§31.18.12**）。

##### 31.18.17.2 World時間条件

**明示する。**

- **DELTAN = 1**
- **REACTION_TIME = real_W.DELTAT**
- したがって **reference_W.DELTAT = real_W.DELTAT**

**理由:** UXsim では **`DELTAT = REACTION_TIME × DELTAN`**（**§31.18.16**）。**DELTAN を 1 に固定**し、**REACTION_TIME** へ **実 World の DELTAT** を置けば、同じ **DELTAT** を作れる。**実 World の REACTION_TIME をそのままコピーしない**。

**構築直後**に、次を **別々に**確認する。

- **`type(reference_W.DELTAN) is int`**
- **`reference_W.DELTAN == 1`**
- **`reference_W.DELTAT == real_W.DELTAT`**

**DELTAT** は **float** なので、**厳密一致**を基本候補とする。両方とも **同じ実 World の値**から作るため、通常は **同じ float** になる。**最終的な比較方法と failure message** は **4/4** で確定する。

##### 31.18.17.3 Node標準条件

実走行 Link 数を **n** とすると、**n+1 個**の Node を **直列**に作る。

- **起点 Node 1 個**
- **Link 境界 Node n-1 個**
- **終点 Node 1 個**
- **分岐なし**、**合流なし**
- **signal なし**（**`signal=[0]`**）
- **flow_capacity なし**
- **`order_control_type="none"`**、**`order_control_eligible=False`**
- **user_function なし**

**Node 名**は reference World 内部の一意な連番を候補とする。例: **`reference_node_0`** … **`reference_node_n`**。

**実 World の Node 名や Node 制御属性はコピーしない。** **T_{\min,z}** に必要なのは **実走行 Link の物理条件列**である。実 World の Node 制御は **待ち要因**なので持ち込まない。直列化で **route choice の曖昧さ**を除く。

##### 31.18.17.4 Link標準条件

各実走行 Link について、**同じ順序**で reference Link を **1 本ずつ**作る。

**実 World から引き継ぐ物理値:**

- **`length = float(real_link.length)`**
- **`free_flow_speed = float(real_link.u)`**

**speed** は **`real_link.free_flow_speed` ではなく `real_link.u`** から取る（**§31.18.14.9**）。**float を round しない**。**Link 順序を変えない**。

**reference World 側で標準化する値:**

- **`number_of_lanes = 1`**
- **`jam_density = 0.2`**（UXsim 既定の正の標準値）
- **`jam_density_per_lane = None`**
- **`merge_priority = 1`**
- **`signal_group`** は無信号と整合する既定 **`[0]`**
- **`capacity_in = 1000000.0`**、**`capacity_out = 1000000.0`**（**`NON_BINDING_CAPACITY`**）
- **`user_function = None`**
- **attribute**、**user_attribute** は設定しない

**非拘束 capacity** は Vehicle 1 台の流入・流出を制約しない。**infinity は使わない**。**実 World の capacity_in / out はコピーしない**。

**jam_density と車線数をコピーしない理由:** **CASE 6A** では、単車両・leader なし・capacity 非拘束で **jam_density** は **T_{\min,z}** を変えなかった。**CASE 6B** では同条件で **number_of_lanes** も変えなかった（**§31.18.13**）。単純で安定した標準値へ固定する。

検証 script の現行 reference builder は、感度確認のため **jam_density** と **number_of_lanes** を経路から写す場合がある。**正式な標準条件**は、それらを写さず **上記の固定値**とする。

##### 31.18.17.5 Link名とaudit identity

**Reference Link 名**は、内部で一意な連番を候補とする。例: **`reference_link_0`** … **`reference_link_{n-1}`**。

**実 World の Link 名を reference Link 名としてコピーする必要はない。** 実 World の Link 名列は、確定済みの **`route_audit_identity`** として **別保持**する（**§31.18.15**）。

**CASE 6C** と **CASE 7B** で、Link 名は物理的 **T_{\min,z}** を変えなかった。内部名と監査用の実 World 名を分離し、同名の反復や自動 rename の曖昧さを避ける。

##### 31.18.17.6 Vehicle標準条件

**Vehicle は 1 台だけ**作る。

- **departure timestep = 0**
- **`mode = "single_trip"`**
- 起点は **`reference_node_0`**、終点は **`reference_node_n`**
- **route** を reference Link 列へ **明示的に固定**
- **user_function なし**、**他 Vehicle なし**
- **taxi mode なし**、**trip-end の特殊処理なし**
- **order-control 参加属性**を持ち込まない
- **true VOT**、**申告 VOT**、**Buyer**、**Seller**、**Nonparticipating** 等の評価属性を持ち込まない

必要なのは **同一物理経路の最短旅行時間**だけである。取引属性や制御方式は **T_{\min,z}** へ不要である。route choice の結果へ依存せず、実走行 Link 順序を直接再現する。

##### 31.18.17.7 Route固定

Reference Vehicle は、構築した reference Link 列を **順番どおり**通るよう **明示的に固定**する。

- **分岐のない直列 network** でも route を **明示的に固定**する
- **自動 route choice** の結果へ **依存しない**
- Link 順序が実 World の **actual_route_links** と **完全に対応**する
- 固定後に、**route Link 数**と **reference Link 数**が一致することを確認する **候補**とする

公開 API の基本候補は、検証 script で使用済みの **`enforce_route()`** である。**production helper の具体実装は今回行わない。**

##### 31.18.17.8 実行時間上限

Reference Vehicle が完走できる **十分な実行時間**を設定する。

**Σ(length/u)** は正式 **T_{\min,z}** には使わない。**実行時間上限の見積り**には使ってよい。

**保守的候補の趣旨:**

```text
reference_tmax
=
analytical_free_flow_time
+
(n + 2) * real_W.DELTAT
+
fixed_margin_seconds
```

- **analytical_free_flow_time = Σ(length / u)**
- **n** は Link 数
- **fixed_margin_seconds** の候補は **60 秒**

この上限は **T_{\min,z} の算定式ではない**。完走のための実行可能時間を確保するだけである。上限までに完走しなければ、値を推測して続行しない。**未完走は明示的な失敗**とする。同じ処理内で **無制限に延長しない**。

検証 script の小さい CASE は固定 **tmax=600 秒**で完走している。**正式な標準**は上の保守的上限とする。**最終的な式と余裕値**は、実装時の小規模検証で確認する。**未完走なら停止**する方針は、今回確定する。

##### 31.18.17.9 実行後の合格条件

replay 完了後に、最低限次を確認する **候補**とする。

- Reference Vehicle の **state** が **end**
- **arrival_time** が有効
- **travel_time** が **0 以上**
- **`traveled_route()`** の Link 数が期待数と一致
- reference route の **length 列**と **u 列**が **physical_route_key** と一致
- **reference_W.DELTAN == 1**
- **reference_W.DELTAT == real_W.DELTAT**
- **他 Vehicle が存在しない**
- **signal**、**order-control**、**Node flow_capacity**、**user_function** が存在しない
- **capacity 待ち**が発生していない
- **route 固定どおり**完走した

どこまでを毎回確認し、どこまでを構築時保証へ委ねるかは **4/4** で最終整理する。

**基本方針:** 構築時に保証した不変条件を、Vehicle の各 timestep で繰り返し確認しない。**replay 完了後**に、重大な結果整合性だけを確認する。

##### 31.18.17.10 空経路と不正Link値

**actual_route_links** が空なら、reference World を **構築しない**。物理識別値を作れず、経路を定義できず、**T_{\min,z}** を算出できない。**空経路を 0 秒として扱わない。** 不整合として停止する候補とする。即時停止の最終例外形式は **4/4** で確定する。

構築前に、各 Link について次を確認する **候補**とする。

- **length** が有限の数値かつ **length > 0**
- **u** が有限の数値かつ **u > 0**
- Link object が **None** でない

**NaN**、**infinity**、**0**、**負数**は受け入れない。不正値のまま World を作ると、未完走や曖昧な結果を招く。型と値の最終 helper、例外型、message は **4/4** で確定する。

##### 31.18.17.11 Randomness

次により、経路・交通上の不確実性を除く。

- **Vehicle 1 台**
- **分岐なし**、**合流なし**
- **route 固定**
- **signal なし**、**order-control なし**、**user_function なし**

この条件では、**random seed が T_{\min,z} へ影響しない**構造とする。World へ seed を指定する場合は、検証 script と同じ **固定値 0** を候補とする。

**`hard_deterministic_mode`:** route 固定、単車両、分岐・合流なしなら、物理結果の追加条件としては不要である。**実 World からコピーしない。** 物理結果へ不要な設定を **physical_route_key** へ追加しない。

**推奨:** 検証 script で合格済みの設定を基準にする。**`random_seed=0`**。**`hard_deterministic_mode=True`**。どちらも **physical_route_key へ含めない**。

##### 31.18.17.12 Loggingと出力抑制

reference World は内部計算用であり、通常の研究 output を生成しない。

- **print_mode**、**save_mode**、**show_mode**、**show_progress** を抑制する（検証 script と同じ **0**）
- **画像を作らない**、**CSV を書かない**、**output directory を作らない**
- console へ通常進行を大量表示しない

**`Vehicle.travel_time`** と **`traveled_route()`** を取得できる最低限の記録は維持する。

**`vehicle_logging_timestep_interval`** は **1** とする。UXsim 既定であり、検証 script はこれを上書きしていない。**`-1` で logging を無効化しない。**

##### 31.18.17.13 実Worldから持ち込まない属性

次を実 World から **コピーしない**。

- **signal** 設定、**signal phase**
- **Node flow_capacity**
- **order_control_type**、**order_control_eligible**、**batch_size**、**transaction_case**、**TVT-MP 設定**
- **Link capacity_in / out**、**merge_priority**、**signal_group**
- **jam_density**、**jam_density_per_lane**、**number_of_lanes**
- **route_choice_penalty**、**user_function**
- Vehicle の **VOT**、**申告値**、**participating 状態**、**Buyer / Seller 等の role**
- **actual departure time**
- **他 Vehicle**、実 World の **混雑**、**queue**、**Link 上位置**

**物理的に引き継ぐのは次だけ**とする。

- **Link 順序**
- 各 Link の **length**
- 各 Link の **u**
- **real_W.DELTAT**

**Link 名列**は物理条件ではなく、**audit identity** として別保持する。

##### 31.18.17.14 未実装事項

次は **今回実装しない**。

- **production reference World builder**
- **replay helper**
- **validation helper**
- **tests**
- **research validation script**
- **結果共有の仕組み**
- **counter**
- **failure 時の最終例外**
- **CSV**
- **Vehicle 別 CW_z**
- **ACWT**
- **ACWWT**

##### 31.18.17.15 残りの実装前設計

**実装前設計 3/4 は本節で完了**した。**残りは 1 つ**である。

- **4/4** **同一評価処理内**で結果を共有する仕組みの **所有者・存続範囲・保存内容・確認記録**（**未着手**、**次の作業**）

**4/4 の設計・実装・検証 script 作成には、本節では進まない。**

**最新参照（2026-11-04）:** **reference replay 結果共有**の **設計**は **§31.18.18** で **確定**。**実装前設計 4/4 完了**。**4 つすべて完了**。**production 実装**は **未着手**。**次**は **4 設計の独立確認**、**commit・push**、**実装場所候補の読取り専用調査**。

#### 31.18.18 同一評価処理内のreference replay結果共有設計

**位置付け:** **実装前設計 4/4**。**production class、helper、tests、検証 script は作らない。**

**原典:** `Vehicle.end_trip()` は **state を end** にし、**`travel_time = (arrival_time - departure_time) × DELTAT`** とする。実走行 Link 列の正本は **`traveled_route()`** である。正式 **T_{\min,z}** は、この **travel_time** を reference replay で取った値である（**§31.18.12**、**§31.18.14**、**§31.18.17**）。

##### 31.18.18.1 目的

同じ物理的走行条件の複数 Vehicle について、**reference replay を Vehicle ごとに繰り返さない**。結果を **別の評価実行へ持ち越さない**。どの経路が同じ結果を使ったかを確認でき、共有回数と新規計算回数を残す。不整合時は、誤った **ACWT・ACWWT** を出さず **停止**する。

##### 31.18.18.2 所有者と存続範囲

共有結果は、**ACWT・ACWWT を 1 回算出する評価処理**が所有する。

- 評価処理の入口で、**局所的な評価 context** を **1 個**作る
- その context に、共有結果と確認記録を置く
- context は **その評価処理の中だけ**で受け渡す
- **module-level global cache** は使わない
- **World の恒久属性**にしない

**有効範囲**は、その評価処理の **開始から終了まで**である。終了後は memory 上の共有結果を破棄する。次の評価は **空から**始める。別 process、file、serialize、pickle、CSV 再読込へは持ち越さない。同じ実 World を再評価する場合も、**新しい評価処理**として作り直す。

**理由:** World や Link 属性が変わった可能性を無視しない。古い結果の混入を防ぎ、再現性と監査を優先する。初期実装を単純にする。

**class 名と配置**は production 実装時に決める。**今回 class は作らない。**

##### 31.18.18.3 物理識別値

共有判断には **§31.18.14** の物理識別値を使う。

```python
physical_route_key = (
    float(real_W.DELTAT),
    tuple(
        (
            float(link.length),
            float(link.u),
        )
        for link in actual_route_links
    ),
)
```

**Link 順序を維持**する。**float を丸めない**。**Link 名を含めない**。**DELTAT を含める**。**set** も **文字列 key** も使わない。実走行 Link 列から作る。

**DELTAN** は key へ追加しない。評価処理入口で **DELTAN=1** を前提として保証する（**§31.18.16**）。

##### 31.18.18.4 保存するreference結果

1 つの **physical_route_key** について、最低限次を保存する候補とする。

- **uxsim_reference_minimum_trip_time_s**
- **analytical_route_free_flow_time_s**（診断用）
- **reference_route_link_count**
- **reference_world_deltat**
- **reference_world_deltan**
- **reference_vehicle_state**
- **reference_vehicle_arrival_time**
- **reference_vehicle_travel_time**
- **reference_validation_passed**

**正式な T_{\min,z}** として使うのは **uxsim_reference_minimum_trip_time_s** だけである。解析自由流時間は診断用であり、正式値にしない。

**Reference World、Vehicle、Node、Link の object** は、評価処理全体の共有値として **保持し続けない**。完了後に数値と確認情報を取り出し、World object は破棄できる状態にする。大量の終了済み simulation object を残さない。

##### 31.18.18.5 Audit identityの保存

1 つの物理識別値に、複数の **route_audit_identity** を保持する（**§31.18.15**）。

```python
audit_identities_by_physical_key = {
    physical_route_key: [
        route_audit_identity_1,
        route_audit_identity_2,
    ]
}
```

**最初の観測順**を維持する。**完全一致**する Link 名列は重複登録しない。異なる列はすべて残す。**set だけを正本にしない**。Link 名が違うだけでは replay をやり直さない。

重複確認を速くする必要が出た場合は、表示順の **list** と所属確認用の **set** を併用する候補とする。初期実装は可読性を優先し、実測で必要になるまで最適化しない。

##### 31.18.18.6 Vehicle別評価record

Vehicle ごとの最終 record には、最低限次を対応付ける候補とする。

- **vehicle_name**
- **physical_route_key**
- **route_audit_identity**
- **actual_travel_time_s**
- **uxsim_reference_minimum_trip_time_s**
- **cumulative_waiting_time_s**
- **true_vot**
- **weighted_cumulative_waiting_time**
- **participation 区分**
- 必要なら **比較方式名**

```text
cumulative_waiting_time_s
=
actual_travel_time_s
-
uxsim_reference_minimum_trip_time_s

weighted_cumulative_waiting_time
=
true_vot
×
cumulative_waiting_time_s
```

**true VOT** の単位と時間単位は一致させる。単位変換の最終は **ACWWT 実装時**に確認する。**Buyer・Seller** の取引 role 評価とは分離する。participation 区分は、方式間で同じ固定 Vehicle 集合を比較するために使う。

物理識別値ごとの summary へ、**全 Vehicle 名を無制限に重複保存しない**。Vehicle 名は Vehicle 別 record に置き、summary は **件数**を基本とする。

##### 31.18.18.7 軽量counter

評価処理ごとに、最低限次を記録する候補とする。

- **evaluated_vehicle_count**
- **unique_physical_route_count**
- **reference_replay_run_count**
- **reference_reuse_count**
- **unique_audit_identity_count**
- **duplicate_audit_identity_observation_count**
- **validation_failure_count**
- **incomplete_vehicle_count**
- **negative_cumulative_waiting_time_count**
- **near_zero_negative_cumulative_waiting_time_count**

期待する関係は、**reference_replay_run_count == unique_physical_route_count** である。評価対象だけを数えるとき、**evaluated_vehicle_count == reference_replay_run_count + reference_reuse_count** とする。対象外や失敗を除く場合は、その内訳を別に残す。

counter は確認用であり、物理結果を変えない。Vehicle ごとの大量 console 出力はしない。

##### 31.18.18.8 共有処理順序

1. Vehicle の実走行 Link 列を取得する
2. **physical_route_key** を作る
3. **route_audit_identity** を作る
4. audit identity を対応表へ登録する
5. 物理識別値が未登録かを見る
6. 未登録なら reference replay を **1 回**実行する
7. **合格結果だけ**を共有結果へ保存する
8. **reference_replay_run_count** を増やす
9. 登録済みなら保存済み結果を使う
10. **reference_reuse_count** を増やす
11. 実 travel_time と **T_{\min,z}** から **CW_z** を算出する
12. Vehicle 別 record を作る

replay が失敗した場合、失敗結果を成功として登録しない。不完全な値を共有しない。曖昧なまま継続しない。**評価全体を停止**する候補とする。

##### 31.18.18.9 評価対象Vehicle集合

基本対象は、評価対象 World で **完走**した Vehicle である。**state が end**、**travel_time が有効**、**traveled_route() が空でない**。

未完走は通常平均へ混ぜない。黙って除外せず、**incomplete_vehicle_count** と、Vehicle 名・状態を診断へ残す候補とする。

**本研究の正式評価**は **全車完走**を原則とする。未完走があるとき、正式な **ACWT・ACWWT** を確定値として出さない。長期 trial を交通解消・全車完走まで実行する方針と揃える。

##### 31.18.18.10 負のCW_z

同一物理条件の reference replay には余計な待ちがないため、通常は **CW_z >= 0** を期待する。float や境界差によるごく小さい負値は無視しない。

**負値を無条件に 0 へ丸めない。** 小さい負値と実質的な不整合を区別する。許容値を根拠なく決めない。実装時の小規模検証で観測してから許容範囲を決める。許容内でも元値を監査用に残す候補とする。明確な負値は、reference 条件または経路対応の不整合として停止する。

今回確定するのは、**無断で 0 にしない**ことと、**negative_cumulative_waiting_time_count** を記録することである。最終許容値は小規模実装検証後に決める。

##### 31.18.18.11 Validation実施範囲

**毎回確認する。**

- 入口の **real_W.DELTAN** が厳密な int の 1
- 評価対象 Vehicle の完走
- 実走行 Link 列が空でない
- length と u が有限かつ正
- 新規 reference World の **DELTAN=1**
- 実 World と reference World の **DELTAT 一致**
- reference Vehicle の完走
- reference route の Link 数、length 列、u 列の一致
- reference travel_time が有効

**構築時に一度保証し、各 timestep では繰り返さない。**

- Node が直列
- signal なし、order-control なし、Node flow capacity なし、user_function なし
- Vehicle 1 台
- capacity_in / out が非拘束
- route 固定

保存済み結果を再利用するとき、reference World を再確認しない。保存値の **validation_passed が True** であることだけを確認する候補とする。

##### 31.18.18.12 停止対象

次は警告だけで続行せず、評価を停止する候補とする。

- **real_W.DELTAN** または **reference_W.DELTAN** が厳密な int の 1 ではない
- **DELTAT** 不一致
- actual route が空
- length または u が NaN、infinity、0、負数
- reference Vehicle が未完走
- reference route 不一致
- reference travel_time が無効
- 物理識別値と audit identity を別 Link 列から作成した
- 保存済み value が未検証
- 同じ物理識別値へ異なる reference 最短時間を登録しようとした
- 明確な負の **CW_z**
- 未完走がある状態で正式結果を確定しようとした

初期実装の例外は、原因を明示した **ValueError** または **RuntimeError** を候補とする。入力・前提の不適合は **ValueError**、replay 後の重大不整合は **RuntimeError** とする。専用例外 class は、必要性が明確になるまで作らない。

##### 31.18.18.13 Failure診断

停止時の message には、原因に関係する範囲で次を含める。

- evaluation stage、World 名、Vehicle 名
- physical_route_key、route_audit_identity
- Link index、Link 名、length、u
- 両 World の DELTAT と DELTAN
- actual travel_time、reference travel_time、CW_z
- 期待値または満たすべき条件

無関係な項目をすべての失敗へ大量表示しない。

##### 31.18.18.14 成功時の確認記録

通常成功時は、Vehicle ごとの大量 console 出力をしない。評価終了時の summary で、最低限次を確認できるようにする。

- evaluated_vehicle_count
- unique_physical_route_count
- reference_replay_run_count
- reference_reuse_count
- unique_audit_identity_count
- duplicate_audit_identity_observation_count
- incomplete_vehicle_count
- validation_failure_count
- negative_cumulative_waiting_time_count
- **ACWT**、**ACWWT**
- Nonparticipating 固定集合の Vehicle 数、その **ACWT** と **ACWWT**

CSV 列やファイル名は、実装時に既存 output 構造を調査して決める。**今回ファイル形式は確定しない。**

##### 31.18.18.15 保存期間

共有結果、audit identity、counter は、**評価処理の終了まで**保持する。終了後は、外部参照が残らない限り破棄する。World へ恒久保存せず、次回評価へ持ち越さない。

Vehicle 別の最終 record や summary を研究 output へ保存するかは、**ACWT・ACWWT 出力設計**で決める。今回確定するのは、**共有用の途中結果を永続保存しない**ことだけである。

##### 31.18.18.16 直列実装

初期実装は、1 つの評価処理を **直列**で行う。同時更新、lock、multiprocessing 共有、process-global 状態は扱わない。正しさと監査を先にする。並列化は、正しい直列実装と、小規模および 3,000 台評価の後の高速化課題とする。

##### 31.18.18.17 実装場所候補

制御方式に依存しない評価機能として、**TVT-MP 固有の取引処理の内部へ埋め込まない**。

候補は、新しい評価専用 module、analyzer 側の明示的な評価 helper、research 評価専用 module である。

求める条件は、FCFS、BATCH、TVT-MP、signalized UXsim への共通適用、order-control Visit へ依存しないこと、simulation 本体へ不要な状態を足さないこと、通常実行と評価処理の分離、初学者が追える構造である。

最終配置は、production 既存構造の **読取り専用調査**の後に決める。**今回ファイルは作らない。**

##### 31.18.18.18 4つの実装前設計の統合

実装時は、次を **1 つの評価処理**として統合する。分離したまま実装漏れを起こさない。

- **1/4:** 物理識別値と audit identity を分離し、同じ物理条件へ複数 Link 名列を対応させる
- **2/4:** 両 World の **DELTAN=1** を保証し、不適合なら停止する
- **3/4:** reference World を標準条件で構築し、引き継ぐ物理量は Link 順序、length、u、DELTAT だけにする
- **4/4:** 同一評価処理内で共有し、新規物理条件だけ replay し、既存条件は保存結果を使う。audit identity、counter、failure 診断を保持する

##### 31.18.18.19 実装前設計完了後の順序

**実装前設計 4/4 は本節で完了**した。**1/4 から 4/4 まですべて完了**した。**直ちに production 実装へ進まない。**

1. 4 つの設計記録を独立確認する
2. メモ 2 本を **commit・push** する
3. production 内の実装場所候補を **読取り専用**で調査する
4. reference replay helper と評価 context の具体設計
5. 変更影響範囲を報告する
6. 小規模な別 trial または検証 script で共有動作を検証する
7. その後に production 実装判断
8. Vehicle 別 **CW_z**
9. **ACWT**
10. **ACWWT**
11. Nonparticipating 固定 600 台
12. 4 方式共通検証
13. manual 一致
14. 3,000 台 output
15. 高速化

**次の段階**は、**4 設計の独立確認**、**commit・push**、**実装場所候補の読取り専用調査**である。

**最新参照（2026-11-04）:** **4 方式共通評価**の **実装場所**、**変更範囲**、**小規模検証方法**の **読取り専用調査**は **§31.18.19** で **完了**。**signalized UXsim、FCFS、BATCH、TVT-MP** へ **共通適用**する。**いずれか 1 方式の専用処理へ配置しない。** **独立した方式共通評価 module** が **有力**。**既存 validation script** を **拡張**する。**production 実装**は **未着手**。**次**は **具体的な部品設計**。

#### 31.18.19 4方式共通評価の実装場所・変更範囲・小規模検証方法の読取り専用調査

**位置付け:** **調査 1/3〜3/3 すべて完了**。**production ファイルは作成しない。** 本評価は **TVT-MP 専用ではない**。

##### 31.18.19.1 調査目的と4方式共通性

**対象方式:**

- **signalized UXsim**
- **FCFS**
- **BATCH**
- **TVT-MP**

**目的:** 4 方式を **同じ network-wide 累積 waiting time 定義**で比較する。方式ごとに異なる delay 定義を使わない。方式固有の制御記録に依存しない。同じ Vehicle 集合について公平に比較する。**Nonparticipating 固定集合**にも同じ定義を使う。

TVT-MP の評価研究で必要になった機能であるが、**TVT-MP だけへ適用する機能ではない。**

**禁止:**

- TVT-MP 専用評価として位置付ける
- TVT-MP の取引処理、FCFS 専用処理、BATCH 専用処理、signalized UXsim 専用処理へ埋め込む
- 方式ごとに別の ACWT・ACWWT 算定処理を持つ
- **order-control Visit** の存在を前提とする
- Buyer、Seller、Nonparticipating 等の **TVT-MP 固有 role** を、全 Vehicle 共通評価の **必須入力**にする

**共通評価の入口**は、4 方式の **完走済み World** を **同じ形**で受け取れるものとする。方式固有情報は、共通の **CW_z、ACWT、ACWWT** を算出した **後**に、必要な部分集合や比較区分へ付加する。

##### 31.18.19.2 Analyzerと既存評価の確認

**原典確認済み（`uxsim/analyzer.py`）:**

- UXsim の既存結果分析は **`Analyzer`** に集約されている
- **`Analyzer`** は **World への参照**を保持する
- **`Analyzer.__init__`** は **`out{W.name}` directory** を作成する
- **`basic_analysis()`** は既存の **OD 単位 free travel time** を用いて delay を算出する
- **`vehicle_trip_to_pandas()`** は Vehicle 名、起終点、出発時刻、最終状態、**travel_time**、平均速度、走行距離を出力する
- **`vehicle_groups_to_pandas()`** も既存 **OD free travel time** を用いる

**今回確定した同一実走行経路 reference replay による T_{\min,z}** は、既存 Analyzer の delay 計算とは **異なる**。**既存 Analyzer の delay 値を ACWT・ACWWT の正式値として流用しない。**

##### 31.18.19.3 World・Analyzer接続の確認

- 通常の World では **finalize 時**に **`Analyzer(W)`** が作成される
- **`create_analyzer=False`** を使えば、内部仮想 World には Analyzer を作らないことができる
- **reference World** は内部計算用であり、**Analyzer を必要としない**
- reference World で Analyzer を作ることにより、**不要な output directory を作成すべきではない**
- reference World は **4 方式の共通評価の内部**で使う補助 World であり、**いずれか 1 方式の Analyzer ではない**

**`uxsim.py`:**

- **simulation 本体**である
- order-control 関連の production module を一部 import する
- 今回の ACWT・ACWWT 評価は **simulation 進行処理ではなく、完走後の方式共通評価**である
- **simulation 本体へ直接埋め込む必要はない**
- 4 方式のどの World も、**simulation 終了後**に **同じ評価処理**へ渡す構造が望ましい
- **simulation 進行中の方式固有制御**と、**完走後の方式共通評価**を **分離**する

**package 公開（`uxsim/__init__.py`）:**

- **`uxsim.py`、`utils.py`、`analyzer.py`、`scenario_reader_writer.py`** を公開している
- 新しい評価機能を **`from uxsim import *`** で直ちに公開する必要があるかは **未確定**
- 初期の小規模検証前に公開窓口を変更する必要はない
- 4 方式の共通利用に適した公開方法は、小規模検証と正式 test 成立後に判断する

**tests:**

- 一般 UXsim の tests は **`from uxsim import *`** または **`import uxsim`** を用いる
- Analyzer の **`basic_analysis()`** 等を既存 World から呼ぶ形が多い
- order-control、TVT-MP、BATCH、FCFS 名を含む専用 test file は、今回の検索範囲では **存在しなかった**
- 今回の研究機能は、まず **`research_scripts` の独立検証**で確認してきた
- 将来の正式 test は、特定方式名ではなく **方式共通評価**であることが分かる名前にする

**validation script:**

- **`research_scripts`** 内の **`validate_*.py`** は、現時点では **`validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`** だけである
- この script には **CASE 1〜7** までの reference replay 基礎検証が集約されている
- 既存 CASE を保護したまま、共有動作の小規模検証を追加するのが自然である
- 検証対象は TVT-MP だけではなく、**4 方式へ共通する reference replay 評価基盤**である

##### 31.18.19.4 既存研究moduleと方式共通性

**`uxsim` 直下**には order-control および TVT-MP 専用 module が多数ある。これらは特定制御方式の処理を担う。

今回の ACWT・ACWWT は **4 方式へ共通適用**する。いずれか 1 方式の専用 module へ入れると、方式共通性を失う。

**依存しないもの:**

- TVT-MP の取引 Visit、Buyer、Seller、payment、compensation、Candidate
- FCFS の順位処理
- BATCH のバッチ形成や **t_trigger**
- signalized UXsim の signal phase や信号制御記録

**共通入力:** 完走済み World、**`Vehicle.travel_time`**、**`Vehicle.traveled_route()`**、Link 物理条件、**true VOT** 等。

##### 31.18.19.5 採用する実装場所候補

**採用候補:** signalized UXsim、FCFS、BATCH、TVT-MP の **4 方式に共通する独立評価 module** を **`uxsim` 直下へ新設**する。

**ファイル名の有力候補:** **`uxsim/network_wide_waiting_time_evaluation.py`**

**名称の要件:**

- TVT-MP、order-control、FCFS、BATCH、signal の固有名を使わない
- ACWT・ACWWT と **network-wide waiting time 評価**であることが分かる
- reference replay だけに狭すぎず、Vehicle 別結果と集計結果も扱える
- 初学者が目的を理解しやすい
- **4 方式の共通評価**であることが分かる

**正式なファイル名**は、具体設計時に最終確定する。**今回ファイルは作らない。**

**独立 module を採用する理由:**

- 4 方式へ共通適用でき、同じ入口と同じ定義で評価できる
- simulation 本体から分離できる
- いずれか 1 方式の制御処理、order-control Visit、TVT-MP の取引 role へ依存しない
- Analyzer の既存 delay 定義と混同しない
- reference World の生成と実行を明示的に隔離できる
- output directory の自動作成を避けられる
- 小規模検証後に公開方法を決められる
- 方式ごとの重複実装を避けられる

##### 31.18.19.6 不採用とする配置

**`uxsim/uxsim.py` へ直接実装しない。** simulation 本体を大きくし、完走後評価と進行処理を混在させる。方式共通の補助評価のために core へ状態を足す必要はない。4 方式の進行処理と評価後処理の境界が曖昧になる。

**`uxsim/analyzer.py` へ直接実装しない。** Analyzer 生成時に output directory を作る。既存 delay 定義と今回の reference replay 定義が異なる。reference World 自体に Analyzer を作らない方針と整合しない。Analyzer の責務を大きく増やし、既存 delay と ACWT・ACWWT を混同する危険がある。

**将来:** 独立 module の安定後に、Analyzer から呼び出す **薄い窓口**を追加する可能性は残す。**初期実装では行わない。**

**いずれか 1 方式の専用 module へ実装しない。** 対象は TVT-MP 専用、FCFS 専用、BATCH 専用、signalized UXsim 専用、order-control 共通処理のうち signalized UXsim へ適用できない場所である。ACWT・ACWWT は 4 方式の公平な共通比較指標であり、どの方式でも同じ **`Vehicle.travel_time`** と実走行経路から算出する。方式固有処理へ入れると、他方式で別実装が必要になり、定義差や計算差を生む。

**`research_scripts` だけへ正式実装しない。** 最終的には 4 方式へ共通適用する再利用可能な評価機能である。research script だけでは重複実装を招き、Vehicle 別 **CW_z**、**ACWT**、**ACWWT** の一貫性を保証しにくい。方式ごとの trial script へ個別実装すると公平比較を損なう。

**ただし:** production 実装前の **検証場所**として **`research_scripts` を使用する。**

##### 31.18.19.7 変更範囲候補

**初期の production 実装で変更する候補:**

1. 新規の **4 方式共通評価 module**
2. 新機能専用の **test file**
3. 必要な場合だけ **package 公開用の最小変更**
4. 詳細設計メモ
5. 進捗メモ

**初期段階では変更しない候補:**

- **`uxsim/uxsim.py`**、**`uxsim/analyzer.py`**
- signalized UXsim の信号制御、FCFS 制御、BATCH 制御、TVT-MP 制御・取引処理、order-control module
- 既存 research output writer、既存 trial script、既存評価値、既存 Analyzer の delay
- World の恒久属性

**公開用の `__init__.py` 変更は、小規模検証前には行わない。** 独立 module を直接 import して検証できる。安定後に 4 方式からの利用方法を確定してから公開窓口を判断する。**4 方式の各 trial へ同じ評価コードをコピーしない。**

##### 31.18.19.8 部品構成候補

新しい独立 module 内で、将来次の責務を分ける候補とする。**class、dataclass、function 名は次の具体設計で確定する。今回 production file は作成しない。**

**入力前提の確認:** 実 World の完走、**DELTAN=1**、Vehicle 状態、実走行経路、Link 値。4 方式共通で必要な入力だけを確認する。方式固有制御の存在を必須条件にしない。

**実走行経路の識別:** **physical_route_key**、**route_audit_identity**。4 方式で同じ作成方法を使う。

**reference World の構築:** 標準条件（**§31.18.17**）。直列 Node と Link、Vehicle 1 台、route 固定、実行時間上限。実 World の方式固有制御を持ち込まない。

**reference replay の実行と確認:** 完走、route 一致、DELTAT 一致、有効な travel_time。評価対象方式に関係なく同じ検査を行う。

**評価処理内の結果共有:** 新規物理条件だけ replay。合格結果だけ保存。audit identity、counter。4 方式間で同じ共有規則を使う。

**Vehicle 別評価 record の共通部分:** actual travel time、**T_{\min,z}**、**CW_z**、true VOT、重み付き値、participation 区分。

**方式固有情報:** 共通結果へ **後から付加**する。共通計算の成立条件にしない。signalized UXsim では取引 role がなくても評価可能。FCFS、BATCH でも TVT-MP 固有 field がなくても評価可能。TVT-MP では必要に応じて role 等を別列として追加可能。

**集計 summary:** **ACWT**、**ACWWT**、Nonparticipating 固定集合、replay 実行回数、再利用回数、failure count、方式名、評価対象 Vehicle 集合の識別情報。

##### 31.18.19.9 小規模検証方法

production 実装前に、既存の次の script を拡張する方針を **採用候補**とする。

**`research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`**

**理由:** CASE 1〜7 の原典検証が既にある。reference replay の定義、属性感度、識別値安全性が同じ場所にある。既存 CASE を回帰確認できる。新しい検証結果を同じ console-only 方針で確認できる。file 出力を発生させない。production 変更前に設計の欠陥を発見できる。検証内容は 4 方式共通の評価基盤であり、特定方式の trial に依存しない。

**新規の別 validation script を作る案は現時点で不採用**とする。基礎検証が分散し、CASE 1〜7 との関係が追いにくくなり、同じ helper や条件を重複定義しやすい。

**ただし:** script が過度に大きくなり、目的が追えなくなる場合には分割を再検討する。分割する場合も、**方式別ではなく機能別**に分ける。

##### 31.18.19.10 CASE 8系列候補

既存 CASE 1〜7 を変更せず、将来 **CASE 8 系列**として次を追加する候補とする。具体的な CASE 数と統合方法は具体設計段階で絞り込む。無意味に CASE を増やさない。**CASE 8K** が他 CASE へ統合できる場合は、独立 CASE にしなくてよい。

- **8A:** 同じ物理経路、同じ Link 名列の複数 Vehicle。replay は 1 回。2 台目以降は同じ結果を使う
- **8B:** 同じ物理経路、異なる Link 名列。replay は 1 回。audit identity は複数保持
- **8C:** 異なる Link 順序。replay は別々に実行
- **8D:** 異なる DELTAT。同じ評価処理内では混在させない。別 World または別評価として扱う
- **8E:** 1 台に起点待ち。同じ **T_{\min,z}** を使い、待ち時間だけ **CW_z** へ反映
- **8F:** DELTAN 不適合。replay 開始前に停止
- **8G:** 空経路、未完走、不正 Link 値のいずれか。正式結果を出さず停止
- **8H:** counters。評価 Vehicle 数、一意な物理経路数、replay 実行数、再利用数、audit identity 数の関係
- **8I:** 同一評価を 2 回実行。2 回目は空の共有状態から開始。前回結果を持ち越さない
- **8J:** Reference World object が評価終了後の共有結果へ保持されていないこと
- **8K:** 4 方式を模した完走済み World または等価な方式ラベル。方式固有の制御記録がなくても共通評価が成立する。同じ物理条件と旅行時間なら、方式名により計算式が変わらない。方式名は集計・監査用であり、**T_{\min,z}** 算定を変えない

##### 31.18.19.11 tests方針

検証 script で共有動作が合格するまで、**正式 tests は追加しない。**

検証合格後の候補:

- 新機能専用の test file を作る
- 既存の一般テストファイルへ散在させない
- test 名は方式共通評価であることを示す
- TVT-MP、FCFS、BATCH、signal の固有名を使わない
- 小さな World で短時間に完了する
- file 出力を行わない
- 既存 Analyzer を必要としない
- 4 方式へ同じ入口を使用できることを確認する

**test file 名の候補:** **`tests/test_network_wide_waiting_time_evaluation.py`**

正式名は production module 名と合わせて決定する。

##### 31.18.19.12 package公開方針

**初期の小規模検証:** 新 module を直接 import する。**`uxsim/__init__.py` を変更しない。**

**production 機能が安定した後:** 4 方式の共通評価として一般利用するなら **`uxsim/__init__.py`** から公開する可能性。Analyzer から薄い窓口を追加する可能性。research 用途だけなら明示的 import を維持する可能性。

**公開方法によって 4 方式のうち一部だけが利用可能になる構造にしない。** 共通 module を正本とし、方式別の薄い呼出し口を作る場合も計算本体を複製しない。

公開方法は、検証後の判断事項として残す。

##### 31.18.19.13 調査1/3〜3/3の結論

**1/3 実装場所:** 4 方式共通の独立評価 module が有力。Analyzer、simulation 本体、いずれか 1 方式の専用処理へ直接入れない。

**2/3 変更範囲:** 新 module を中心に小さくする。既存機能の変更を避ける。公開窓口は検証後に判断する。正式 test は共有動作検証後に追加する。方式別の重複実装を作らない。

**3/3 小規模検証:** 既存 validation script を拡張する。CASE 1〜7 を保護する。同一条件の共有、異条件の分離、audit identity、counter、失敗停止、評価間非持越しを確認する。signalized UXsim、FCFS、BATCH、TVT-MP で共通利用できることも確認する。

##### 31.18.19.14 次の段階

**調査 1/3〜3/3 は完了**した。**直ちに production 実装へ進まない。**

1. 今回の調査結果を独立確認する
2. メモ 2 本を **commit・push** する
3. 4 方式共通 module の class、record、summary、helper の具体設計
4. 変更影響範囲を確定する
5. 既存 validation script への **CASE 8** 追加設計
6. 小規模検証用実装
7. **py_compile**、static validation、CASE 1〜8 実行
8. 検証合格後に production 実装判断
9. 正式 tests
10. 公開方法
11. Vehicle 別 **CW_z**
12. **ACWT**
13. **ACWWT**
14. Nonparticipating 固定 600 台
15. signalized UXsim、FCFS、BATCH、TVT-MP の **4 方式共通検証**
16. manual 一致
17. 3,000 台 output
18. 高速化

**最新参照（2026-11-04）:** **4 方式共通評価**の **production 具体設計**は **§31.18.20** で **完了**。**production 実装開始まで残り 2 工程**。**次**は **2/3 CASE 8 小規模検証**。**production 未実装**。

**最新契約（2026-11-04）:** **`true_vot_per_second`**、**`evaluation_cohort`**、**timestep 差を正本とする CW_z**、**Analyzer なし reference 専用 runner**、**同一 Vehicle plan の 4 方式 paired 比較**は **§31.18.22**。**追加確認 4/4 完了**。**§31.18.22** は **production 実装前の最終統合契約**として **歴史的に有効**。**production 実装後の現行状態**は **§31.18.23** を **優先**する。

#### 31.18.20 4方式共通network-wide waiting time評価のproduction具体設計

**位置付け:** production 実装開始までの **固定工程 1/3**。**今回ファイルは作らない。** 新しい工程区分は追加しない。

**固定工程:**

- **1/3 具体設計:** 本節で完了
- **2/3 CASE 8 小規模検証:** 次
- **3/3** 検証結果の確認と production 実装可否判断
- **その後** production 実装開始

##### 31.18.20.1 目的と固定工程

本機能は **signalized UXsim、FCFS、BATCH、TVT-MP** の **4 方式共通**である。完走済み World を **同じ入口**で受け取り、**同じ式**と **同じ検査**で Vehicle 別 **CW_z**、**ACWT**、**ACWWT** を算出する。

**禁止:**

- 方式ごとに別の計算本体を作る
- TVT-MP の Visit、Buyer、Seller、Candidate を共通評価の必須入力にする
- FCFS 順位、BATCH 形成、signal phase を共通評価の必須入力にする
- 方式名によって **T_{\min,z}** や **CW_z** の計算方法を変える

方式固有情報は、共通結果の算出 **後**に比較区分として付加する。

##### 31.18.20.2 production moduleと公開入口

**正式候補:** **`uxsim/network_wide_waiting_time_evaluation.py`**

**理由:** 4 方式共通である。TVT-MP や order-control の固有名を含まない。Vehicle 別累積 waiting time と集計値を扱うことが分かる。reference replay だけでなく、入力検査、共有、Vehicle 別 record、summary も扱える。

**主要入口の候補名:** **`evaluate_network_wide_waiting_time`**

**入力候補:**

- **real_world**
- **method_name**
- **true_vot_by_vehicle_name**
- **participation_by_vehicle_name**
- optional **evaluated_vehicle_names**

**戻り値候補:** 評価全体の結果 object（**§31.18.20.3** の **NetworkWideWaitingTimeEvaluationResult**）

**要件:**

- 完走済み World を受け取る
- World を変更しない
- simulation を再実行しない
- 評価処理ごとに新しい局所 context を作る
- file を書かない
- console へ Vehicle ごとの大量表示をしない
- 4 方式で同じ入口を使う
- **method_name** は監査・集計用であり、計算式を変えない

初期実装では **`uxsim/__init__.py` から公開しない。** 新 module から明示的に import する。公開方法は小規模検証後に判断する。

##### 31.18.20.3 データ構造

初学者が追えるよう、責務ごとに分ける。高度な汎用 framework にはしない。

**PhysicalRouteKey** は、型 alias または明示的 tuple とする。

```text
(
    float(real_W.DELTAT),
    (
        (float(link.length), float(link.u)),
        ...
    ),
)
```

Link 順序を維持する。**round しない。** Link 名を含めない。**DELTAN を含めない。** 文字列化しない。

**RouteAuditIdentity** は **`tuple(str(link.name) for link in actual_route_links)`** である。実走行順と同名 Link の反復を維持する。physical key と分離する。

**ReferenceReplayResult** の保存候補:

- physical_route_key
- minimum_trip_time_s（正式 **T_{\min,z}**。単位は秒）
- analytical_free_flow_time_s（診断用。単位は秒。正式値ではない）
- reference_route_link_count
- reference_world_deltat（秒）
- reference_world_deltan
- reference_vehicle_arrival_time
- reference_vehicle_travel_time（秒）
- validation_passed

**保存しない:** Reference の World、Vehicle、Node、Link の object。

**VehicleWaitingTimeRecord** の保存候補:

- vehicle_name
- method_name
- physical_route_key
- route_audit_identity
- actual_travel_time_s（秒。実 World の **`Vehicle.travel_time`**）
- minimum_trip_time_s（秒）
- cumulative_waiting_time_s（秒）
- true_vot（単位は **§31.18.20.7**。未確定の換算を推測しない）
- weighted_cumulative_waiting_time（**true_vot × CW_z**。単位は true VOT と秒の積）
- participation_category

**EvaluationCounters** の候補:

- evaluated_vehicle_count
- unique_physical_route_count
- reference_replay_run_count
- reference_reuse_count
- unique_audit_identity_count
- duplicate_audit_identity_observation_count
- incomplete_vehicle_count
- validation_failure_count
- negative_cumulative_waiting_time_count
- near_zero_negative_cumulative_waiting_time_count

**NetworkWideWaitingTimeSummary** の候補:

- method_name
- vehicle_count
- total_cumulative_waiting_time_s
- average_cumulative_waiting_time_s（**ACWT**。秒）
- total_weighted_cumulative_waiting_time
- average_weighted_cumulative_waiting_time（**ACWWT**）
- participation 区分別の台数、**ACWT**、**ACWWT**
- counters

**NetworkWideWaitingTimeEvaluationResult** の候補:

- vehicle_records
- summary
- reference_results_by_physical_key
- audit_identities_by_physical_key
- counters

返却後に必要な監査情報だけを含める。**Reference World object を含めない。**

##### 31.18.20.4 評価context

評価処理中だけ存在する局所 context を使う。

**保持候補:**

- reference_results_by_physical_key
- audit_identities_by_physical_key
- counters
- vehicle_records
- real_world の DELTAT
- method_name

**要件:** 1 回の評価ごとに新規作成する。module global にしない。World 属性へ保存しない。次回評価へ持ち越さない。file へ保存しない。初期実装は直列である。

**推奨:** 責務と不変条件が多いため、**小さな内部 context dataclass** を候補とする。高度な抽象化や汎用 framework にはしない。初学者が処理順を追える構造にする。入口関数内のばらばらな広域変数にはしない。

##### 31.18.20.5 helper責務

名前は分かりやすさを優先する。

- **`_validate_real_world_for_network_wide_waiting_time`:** **DELTAN** が厳密な int の 1、評価対象 Vehicle が存在する、全対象 Vehicle が完走、必要な World 時間値が有効
- **`_collect_evaluated_vehicles`:** 既定は全 Vehicle。optional 指定がある場合はその集合。存在しない Vehicle 名を黙って無視しない。入力順または World 内の安定した順序を維持する
- **`_get_actual_route_links`:** **`traveled_route()`** を正本とする。空経路を拒否する。Link が None でない。length と u が有限かつ正
- **`_build_physical_route_key`**
- **`_build_route_audit_identity`:** 両者は同じ actual_route_links から連続して作り、別 Link 列を使わない
- **`_register_route_audit_identity`:** 最初の観測順を維持する。完全一致は重複追加しない。counter を更新する
- **`_compute_reference_tmax`:** **Σ(length/u) + (Link 数 + 2) × DELTAT + 60 秒**。docstring に、これは **T_{\min,z} の算定式ではない**と明記する
- **`_build_reference_world`:** 標準条件は **§31.18.17**。**`create_analyzer=False`**。引き継ぐ物理量は Link 順序、length、u、DELTAT だけ
- **`_run_reference_replay`:** World 構築、route 固定、simulation、完走確認、route 一致、DELTAT 一致、travel_time 取得、**ReferenceReplayResult** 作成
- **`_get_or_run_reference_replay`:** 未登録なら replay。合格結果だけ保存。登録済みなら再利用。counter を更新する
- **`_build_vehicle_waiting_time_record`**
- **`_build_network_wide_waiting_time_summary`**
- **`evaluate_network_wide_waiting_time`:** 公開入口

##### 31.18.20.6 処理順序

1. 入口引数を確認する
2. real World の前提を確認する
3. 評価対象 Vehicle 集合を確定する
4. 新しい評価 context を作成する
5. Vehicle を安定した順序で 1 台ずつ処理する
6. actual route links を取得する
7. physical key と audit identity を同じ Link 列から作成する
8. audit identity を登録する
9. reference 結果を新規計算または再利用する
10. actual travel time と **T_{\min,z}** から **CW_z** を計算する
11. true VOT と単位を確認する
12. weighted cumulative waiting time を計算する
13. Vehicle record を追加する
14. 全 Vehicle 処理後に counter 整合を確認する
15. summary を作成する
16. 評価結果 object を返す

失敗した replay 結果は共有結果へ登録しない。途中失敗時に暫定 **ACWT・ACWWT** を正式結果として返さない。

##### 31.18.20.7 CW_z・ACWT・ACWWT

**§31.18.12.8** の式を再確認する。時間は UXsim の **`Vehicle.travel_time`** と同じく **秒**である。

```text
CW_z
=
actual_travel_time_s
-
uxsim_reference_minimum_trip_time_s

ACWT
=
sum(CW_z)
/
evaluated_vehicle_count

weighted_CW_z
=
true_VOT_z
×
CW_z

ACWWT
=
sum(weighted_CW_z)
/
evaluated_vehicle_count
```

**C_z** は **true VOT** である。**declared VOT は使わない。** nonparticipating Vehicle にも true VOT を用いる。方式名や role によって式を変えない。Buyer、Seller 等の部分集合は共通値算出後に抽出する。負の **CW_z** を無断で 0 へ変更しない。

**単位:** **§31.18.12.8** は **ACWWT = (1/N) Σ C_z CW_z** と書く。**CW_z** は秒である。**C_z の正式単位**と、時給などを秒へ換算する契約は、この節では一つの数値契約として再掲されていない。**今回は推測しない。** 最終換算は未確定事項とする（**§31.18.20.14**）。実装時に、既存研究契約の単位を読取り専用で確定してから weighted 値を正式比較に使う。

##### 31.18.20.8 participation区分

**基本区分の候補:**

- **participating**
- **nonparticipating**
- **unspecified**

**要件:**

- signalized UXsim、FCFS、BATCH でも同じ Vehicle 集合を対応付けられる
- TVT-MP の World 内 field だけに依存しない
- 方式比較用の外部 mapping を入口で受け取れる
- mapping が不足した Vehicle は **unspecified** とし、黙って participating にしない
- nonparticipating 固定集合の比較が可能

Buyer、Seller、Satisfied、Unsatisfied 等は、共通評価 record の基本区分とは分離する。

##### 31.18.20.9 停止条件

次は警告継続ではなく停止する。

- real World の DELTAN 不適合
- 評価対象 Vehicle 名が存在しない
- 対象 Vehicle が未完走
- actual route が空
- length または u が不正
- reference World の DELTAN 不適合
- DELTAT 不一致
- reference Vehicle 未完走
- reference route 不一致
- reference travel_time 不正
- 保存済み reference 結果が未検証
- 同じ physical key へ異なる正式最短時間を登録しようとした
- true VOT が不足または不正
- 明確な負の **CW_z**
- counter 整合違反

**ValueError 候補:** 入力、型、値、前提条件の違反。

**RuntimeError 候補:** replay 後の不整合、保存結果の矛盾、counter 矛盾。

専用例外 class は初期実装では作らない。

##### 31.18.20.10 結果共有の整合条件

処理終了時に最低限確認する。

- **reference_replay_run_count == unique_physical_route_count**
- **evaluated_vehicle_count == reference_replay_run_count + reference_reuse_count**
- vehicle record 数 == evaluated_vehicle_count
- 各 physical key に検証済み reference 結果が 1 件
- 各 Vehicle record の **T_{\min,z}** が対応する reference 結果と一致
- audit identity が対応する physical key に登録済み
- Reference World object が返却結果に含まれていない
- **validation_failure_count == 0** でなければ正式 summary を返さない

##### 31.18.20.11 CASE 8小規模検証設計

CASE を増やしすぎず、次の **6 群**へ整理する。既存 CASE 1〜7 は変更しない。

**CASE 8A 同一物理条件の共有:** 複数 Vehicle、同じ physical key、同じ Link 名列。replay は 1 回。残りは再利用。counter 整合を確認する。

**CASE 8B 同じ物理条件・異なる Link 名列:** physical key は同一。audit identity は複数。replay は 1 回。観測順を維持する。同じ audit identity は重複追加しない。

**CASE 8C 異なる物理条件の分離:** Link 順序、length、u、DELTAT の違いをこの群で個別確認する。異なる physical key、別 replay、誤共有なし。DELTAT 違いは別 World または別評価とし、1 つの real World 評価内へ異なる World 設定を混在させない。

**CASE 8D CW_z と起点待ち:** 同じ物理経路。起点待ちなしとあり。同じ **T_{\min,z}**。待ちありだけ **CW_z** が増加する。既存 CASE 5 と整合する。

**CASE 8E 停止条件:** 独立した小項目として、DELTAN 不適合、空経路、未完走、length 不正、u 不正、true VOT 不足または不正を確認する。いずれも replay または summary 確定前に停止し、暫定正式結果を返さない。

**CASE 8F 評価間の非持越しと object 非保持:** 同じ評価を 2 回実行する。各評価で新 context。2 回目は空から開始する。1 回目の保存結果を使わない。返却結果に Reference World object を含めない。file 出力なし。

**4 方式共通性**は独立 CASE にしない。**CASE 8A または 8F** へ統合する。**method_name** に **signalized_uxsim**、**fcfs**、**batch**、**tvt_mp** を順に使う。method_name により **T_{\min,z}** と **CW_z** の式を変えない。方式固有 field がなくても共通評価できる。

##### 31.18.20.12 CASE 8実装範囲

**2/3** の小規模検証では、**production module をまだ作らない。**

既存 validation script 内へ、production 候補と同じ責務分離を持つ **検証用の限定実装**を追加する。

- 将来 production へそのままコピーする前提にしない
- 検証用 helper であることを明示する
- CASE 1〜7 を変更しない
- file を書かない。console-only
- **`--static-validate-only`** を維持する
- World 構築なしの static validation を維持する
- CASE 8 実行時だけ必要な World を作る
- production import を追加しない
- tests を変更しない

**2/3 完了時の合格条件:**

- py_compile 成功
- static validation 成功
- CASE 1〜8 全合格
- All cases passed
- 既存 CASE 1〜7 の結果不変
- production 変更なし
- file 出力なし

##### 31.18.20.13 変更影響範囲

**1/3（今回）** で変更するのはメモ 2 本だけである。

**2/3** で変更する予定:

- **`research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`**
- 必要なメモ更新

**2/3 では変更しない:**

- uxsim production、tests、**`uxsim/__init__.py`**、**analyzer.py**、**uxsim.py**
- 各方式の制御 module、trial scripts、research outputs

**3/3** の判断後、production 実装が承認された場合の候補:

- 新規 **`uxsim/network_wide_waiting_time_evaluation.py`**
- 新規専用 test
- 必要なら後段で **`uxsim/__init__.py`**
- メモ 2 本

##### 31.18.20.14 未確定事項

- package 公開方式
- Analyzer からの薄い呼出し口
- 正式 test の詳細
- CSV 列とファイル名
- 既存 research output への統合
- 負の **CW_z** の最終許容値
- 3,000 台での性能最適化
- 並列化
- **true VOT（C_z）の正式単位**と秒換算。**§31.18.12.8** は積の平均までを定め、単位契約は再掲されていない。推測しない

##### 31.18.20.15 production実装までの残り工程

**1/3 具体設計は本節で完了**した。残りは次だけである。新しい工程は追加しない。

- **2/3:** CASE 8 の限定実装、py_compile、static validation、CASE 1〜8 実行、結果記録（**次**）
- **3/3:** 検証結果の独立確認、production 実装可否判断。問題がなければ production 実装開始。問題があれば CASE 8 で判明した問題だけを修正して再確認
- **その後:** production 実装開始

**最新契約（2026-11-04）:** 本節 **§31.18.20** の **`true_vot`**、**`participation_category`**、秒差中心の **CW_z**、**`near_zero_negative_cumulative_waiting_time_count`**、reference runner 未確定は、**§31.18.22** で **読み替え**。**§31.18.22** は **production 実装前の最終契約**として **有効**。**production 実装・検証完了後**は **§31.18.23** を **優先**する。

#### 31.18.22 production実装前追加確認4項目の最終統合契約

**位置付け:** production 実装前に残っていた **追加確認 4 項目**を **すべて確定**し、**§31.18.20** の曖昧点を **統合**する。**新しい工程区分は追加しない**。**本節執筆時点では production 実装にはまだ着手しない**（**現行の実装・検証完了**は **§31.18.23** を **優先**する）。

##### 31.18.22.1 目的と追加確認4/4完了

**追加確認 4 項目（すべて確定）:**

1. **Analyzer なし reference World** には **基準走行専用 runner** が必要
2. **true VOT** の正式単位は **`true_vot_per_second`**
3. **4 方式比較**は **同一 Vehicle plan** による **paired 比較**
4. **負の CW_z** は **整数 timestep 差**を **正本**として判定

**production 実装前の追加確認:** **4/4 完了**。**残件 0**。

**原典確認（読取り専用）:**

- **`World.finalize_scenario(create_analyzer=False)`** の docstring（**`uxsim/uxsim.py`**）
- **`Vehicle.end_trip()`** の **`arrival_time`**、**`travel_time`**（timestep 表記）
- **`Vehicle.record_log()`** の **`W.analyzer`** 書込み
- **`simulation_terminated()`** の **`W.analyzer.basic_analysis()`**
- TVT-MP 系の **`true_vot_per_second`**（**`Vehicle.vot_true`** から取得する契約。**`uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`**、**`uxsim/order_control_tvt_mp_actual_passage.py`** 等）
- CASE 8 検証 script の **Analyzer なし loop**（**production へ無条件コピーしない**旨の確認用）

##### 31.18.22.2 AnalyzerなしReference World専用runner

**UXsim の正式制約（`finalize_scenario(create_analyzer=False)`）:**

- **`W.analyzer` 自体を作成しない**
- **通常の `exec_simulation()`** は **`W.analyzer` の存在**を前提とする
- **`Vehicle.record_log()`** は **`W.analyzer.average_speed`** 等へ書き込む
- **`simulation_terminated()`** も **`W.analyzer.basic_analysis()`** を呼ぶ
- したがって **`create_analyzer=False`** で finalize した World を **通常の `exec_simulation()`** で実行しては **ならない**
- **`create_analyzer=False`** は、**Analyzer へアクセスしない専用 loop** を持つ **内部 virtual World** 用（**Level 2 mimic World** も同方式）

**production reference World の正式方針:**

- **`create_analyzer=False`** を使用する
- **通常の `exec_simulation()`** を **呼ばない**
- **reference World 専用 runner** を **方式共通評価 module**（**`uxsim/network_wide_waiting_time_evaluation.py`** 候補）内に実装する
- 専用 runner は **一本道、Vehicle 1 台、route 固定、信号なし、order-control なし、他 Vehicle なし** の **限定条件だけ**を扱う
- **汎用 simulation runner** として設計しない
- FCFS、BATCH、TVT-MP、signalized UXsim の **方式固有処理**を再現しない
- **実 World の交通状態**を再現しない
- **`T_{\min,z}`** 取得に必要な **物理走行だけ**を実行する

**Reference World 専用 runner の主要更新順序（通常 `exec_simulation()` との横並びで一致）:**

1. **`Link.update()`**
2. **`Node.generate()`**
3. **`Node.update()`**
4. **`Node.transfer()`**
5. **`Vehicle.carfollow()`**
6. **living Vehicle の `Vehicle.update()`**
7. 必要な **route search** と **route preference 更新**
8. **`World.TIME`** 更新
9. **`user_function` 確認**（標準 reference World では **`None`**）

**明記:**

- CASE 8 の **検証用 loop** を **無条件に production へコピーしない**
- production 専用 runner の **責務と限定条件**を docstring で明示する
- 通常 **`exec_simulation()`** との **対応**を docstring に記載する
- 通常 **`exec_simulation()`** の変更に **自動追従しない複製 loop** であることを認識する
- production 実装後に **専用 test** で **主要順序と結果**を固定する
- **reference World 標準条件外**の World へ専用 runner を **適用しない**
- **Analyzer を避ける目的**で **通常 World** の実行方法を **変更しない**

**必要な logging:**

- **`traveled_route()`** 取得に必要な **最小限の記録**を維持する
- **Analyzer への書込み**は行わない
- **output directory** を作らない
- **CSV、画像、通常研究 output** を作らない
- reference Vehicle の **arrival timestep**、**travel_time**、**route** だけを取得する

##### 31.18.22.3 true_vot_per_secondの正式単位契約

**原典:** TVT-MP 処理では **`local_vehicle.vot_true`** を **`true_vot_per_second`** として扱い、**timestep 差 × DELTAT** で秒差を作ったうえで **`true_vot_per_second` を直接乗じる**。**`/3600` 等の時給→秒換算は行わない**。

**検証内容（原典で確認した処理）:**

- **`true_vot_per_second`** として **`vot_true`** を取得
- **`None`、bool、非数値、非有限値、負値**を拒否
- **0 以上の有限な Python int または float** を受け入れ、**float へ変換**して保存
- **追加の 3600 除算**や **時給から秒単位への換算**は **行わない**

**正式 field 名:**

- **`true_vot`** ではなく **`true_vot_per_second`**

**入口 mapping 候補:** **`true_vot_per_second_by_vehicle_name`**

**Vehicle 別重み付き値:**

```text
weighted_cumulative_waiting_time
=
cumulative_waiting_time_seconds
*
true_vot_per_second
```

**ACWWT:**

```text
ACWWT
=
sum(weighted_cumulative_waiting_time)
/
evaluated_vehicle_count
```

**要件:**

- **`vot_declared`** を **使用しない**
- **nonparticipating Vehicle** にも **`true_vot_per_second`** を適用する
- **4 方式**で **同じ true VOT 台帳**を使う
- **方式名や role** によって式を **変えない**
- **`true_vot_per_second` が不足**する Vehicle があれば **停止**する
- **bool** を受け入れない。**NaN、infinity、負値**を受け入れない。**0** は受け入れる
- production コード内で **追加の `/3600`** を **行わない**

**§31.18.20** の **`true_vot`** 表記は、本契約により **`true_vot_per_second`** へ **読み替える**（**§31.18.20.7**、**§31.18.20.14** の未確定記述は **解消**）。

##### 31.18.22.4 同一Vehicle planによる4方式paired比較

**4 方式比較**は、**同一 replication 内**で **同一の生成済み Vehicle plan** を使う **paired 比較**とする。

**対象方式:** signalized UXsim、FCFS、BATCH、TVT-MP。

**将来、統計分布に基づいて Vehicle を生成する場合も、次の順序:**

1. **1 つの replication** について **Vehicle plan を 1 回**生成する
2. **同じ生成済み Vehicle plan** を **4 方式**へ投入する
3. **方式だけ**を変更する
4. **同一 replication 内**で **Vehicle 単位の paired 比較**を行う
5. **複数 replication** でも、**各 replication 内**の **paired 構造**を維持する

**採用しない:** 方式ごとに **別々の需要標本**を生成して **主比較**する案（方式効果と需要標本差が混在するため）。

**同一 replication 内の Vehicle 対応 key:** **`vehicle_name`**

**監査 metadata（CW_z の式を変えない。同一標本の確認用）:**

- **`vehicle_plan_digest`**
- **`demand_generation_seed`**
- **true VOT 生成 seed**
- **cohort assignment seed**
- 必要に応じて **replication identifier**
- 必要に応じて **需要分布設定**

**production 評価入口の正式候補（更新）:**

- **`real_world`**
- **`method_name`**
- **`evaluated_vehicle_names`**
- **`true_vot_per_second_by_vehicle_name`**
- **`evaluation_cohort_by_vehicle_name`**
- optional **`vehicle_plan_digest`**
- optional **comparison metadata**

**評価開始前に確認:**

- **`evaluated_vehicle_names`** に **重複がない**
- 指定された **全 Vehicle 名**が **対象 World に存在**する
- **正式な全 Vehicle 比較**では **World 側**と **評価対象名集合**が **一致**する
- **全評価 Vehicle** に **`true_vot_per_second`** がある
- **全評価 Vehicle** に **evaluation cohort** がある
- **4 方式比較**時に **`vehicle_plan_digest`** が利用可能なら **一致**する
- **`method_name`** は **監査用**であり **計算式を変更しない**

##### 31.18.22.5 TVT-MP nonparticipating比較cohort

**participating / nonparticipating** は **TVT-MP** における **制度上の状態**であり、FCFS、BATCH、signalized UXsim へ **制度上そのまま適用**するもの **ではない**。

**4.1 評価用比較 cohort**

**正式候補 field:** **`evaluation_cohort`**

**例:**

- **`tvt_participating_cohort`**
- **`tvt_nonparticipating_cohort`**

**意味:**

- TVT-MP で **participating** または **nonparticipating** へ割り当てた **Vehicle 集合**
- **他方式**では、**同じ Vehicle** の performance を **抽出するための比較 cohort**
- FCFS 等の Vehicle を **制度上 nonparticipating** と **呼ぶものではない**

**例:** TVT-MP で **nonparticipating** に割り当てた **600 台**について、**同じ Vehicle 名**の 600 台を signalized UXsim、FCFS、BATCH、TVT-MP で比較する。

**4.2 方式固有の参加状態**

必要な場合は **別 field:** **`method_specific_participation_status`**

**値の例:**

- TVT-MP: **participating** または **nonparticipating**
- 他方式: **`not_applicable`**

**共通 CW_z、ACWT、ACWWT 算出**では、**方式固有 field** を **必須入力にしない**。

**§31.18.20** の **`participation_category`**（participating / nonparticipating / unspecified）は、最新契約では **`evaluation_cohort`** へ **置き換える**。

**`unspecified`:**

- **汎用的な単独評価**では許容 **候補**を残せる
- **正式な 4 方式 paired 比較**では **認めない**
- **正式比較**で cohort mapping が **不足**する場合は **停止**する

##### 31.18.22.6 整数timestep差を正本とするCW_z

**UXsim 原典（`Vehicle.end_trip`）:**

```text
arrival_time = World.T   （timestep 表記）

travel_time
=
(arrival_time - departure_time)
*
DELTAT
```

**`departure_time`** も **timestep 表記**である（**`uxsim.py`** の TODO コメントと整合）。

**CW_z の正本は秒 float 差ではなく、整数 timestep 差**とする。

```text
actual_trip_timesteps
=
actual_arrival_timestep
-
actual_departure_timestep

reference_minimum_trip_timesteps
=
reference_arrival_timestep
-
reference_departure_timestep

cumulative_waiting_time_timesteps
=
actual_trip_timesteps
-
reference_minimum_trip_timesteps

cumulative_waiting_time_seconds
=
cumulative_waiting_time_timesteps
*
real_world.DELTAT
```

**要件:**

- **actual** と **reference** の **DELTAT** は **一致済み**であること
- **actual** と **reference** の各 **arrival / departure timestep** は **厳密な non-bool int** として検証する **候補**
- **`cumulative_waiting_time_timesteps` が負**なら **停止**する
- **浮動小数点 tolerance** を **設けない**
- **小さい負値を 0 へ丸めない**
- **負値を警告だけで継続しない**
- **`near_zero_negative_cumulative_waiting_time_count`** は **正式設計から削除**する
- **`negative_cumulative_waiting_time_count`** は **failure 診断用**に残せるが、**正式結果**には **負値を含めない**
- **秒値**は **整数 timestep 差の検証後**に算出する

**整合確認:**

```text
actual_travel_time_s
==
actual_trip_timesteps * DELTAT

minimum_trip_time_s
==
reference_minimum_trip_timesteps * DELTAT

cumulative_waiting_time_s
==
cumulative_waiting_time_timesteps * DELTAT
```

**float 秒値**の比較では、**両辺を同じ整数 timestep と同じ DELTAT から作る**。既存 **`Vehicle.travel_time`** も **整合確認**に使う。

##### 31.18.22.7 Vehicle別recordの最新field

**VehicleWaitingTimeRecord（最新候補）:**

- **`vehicle_name`**
- **`method_name`**
- **`physical_route_key`**
- **`route_audit_identity`**
- **`actual_departure_timestep`**
- **`actual_arrival_timestep`**
- **`actual_trip_timesteps`**
- **`reference_departure_timestep`**
- **`reference_arrival_timestep`**
- **`reference_minimum_trip_timesteps`**
- **`cumulative_waiting_time_timesteps`**
- **`actual_travel_time_s`**
- **`minimum_trip_time_s`**
- **`cumulative_waiting_time_s`**
- **`true_vot_per_second`**
- **`weighted_cumulative_waiting_time`**
- **`evaluation_cohort`**
- optional **`method_specific_participation_status`**

**ReferenceReplayResult** には **`reference_vehicle_arrival_time`**、**`reference_vehicle_travel_time`**（秒）に加え、production では **timestep 列**を **明示保存**する **候補**とする。

##### 31.18.22.8 §31.18.20からの修正事項

| §31.18.20 の概念 | 最新契約（§31.18.22） |
|---|---|
| **`true_vot`** | **`true_vot_per_second`** |
| **`participation_category`** | **`evaluation_cohort`**（＋ optional **`method_specific_participation_status`**） |
| 秒 **travel time 直接差**中心の **CW_z** | **整数 timestep 差**を正本とする **CW_z** |
| **`near_zero_negative_cumulative_waiting_time_count`** | **廃止** |
| reference runner **未確定** | **Analyzer なし reference 専用 runner** |
| 4 方式比較の Vehicle 対応 | **同一生成済み Vehicle plan** の **paired 比較**＋ **digest 等**の監査 |

**§31.18.20** の本文は **削除・改番しない**。**歴史的記録**として残し、**最新参照**で **§31.18.22** を **優先**する。

##### 31.18.22.9 production実装へ進む条件

**追加確認 4 項目はすべて確定**した。

1. reference 専用 runner
2. **`true_vot_per_second`**
3. paired Vehicle plan と TVT-MP 比較 cohort
4. **timestep 差**を正本とする **CW_z**

**production 実装前の追加確認:** **4/4 完了**。**残件 0**。

**CASE 8** 小規模検証 script と本契約の **整合**は、**独立確認**の対象とする（**script 本体は今回変更しない**）。

##### 31.18.22.10 次の作業

**新しい工程区分は追加しない。**

1. **本統合記録**の **独立確認**
2. **CASE 8 検証 script**、**具体設計メモ**、**進捗メモ**を **まとめて commit・push**
3. **その後** **production 実装開始**

**production 実装の初期変更範囲:**

- 新規 **`uxsim/network_wide_waiting_time_evaluation.py`**
- 新規 **`tests/test_network_wide_waiting_time_evaluation.py`**
- 必要な **メモ更新**

**初期 production 実装では変更しない:**

- **`uxsim/uxsim.py`**
- **`uxsim/analyzer.py`**
- **`uxsim/__init__.py`**
- 各方式の **制御処理**
- 既存 **trial script**
- 既存 **research output writer**

**最新参照（2026-11-04、production 実装・独立検証完了）:** **4 方式共通 network-wide ACWT・ACWWT** の **production module** と **専用 test** は **§31.18.23**。**§31.18.22** は **実装前の最終契約**として **維持**する。**現行の実装内容・検証結果・未実装事項**は **§31.18.23** を **優先**する。

#### 31.18.23 network-wide ACWT・ACWWT production moduleと専用testの実装・独立検証完了

**位置付け:** **§31.18.22** で確定した **production 実装前の最終統合契約**に基づき、**方式共通評価 module** と **専用 test** を **新規作成**し、利用者による **Terminal 独立確認**まで **完了**した。**§31.18.22 の計算式・Reference World 条件・timestep 正本・true VOT 単位・evaluation cohort 契約は変更していない**。**新しい設計追加は行わない**。**実装済みコードと検証済み事実**を記録する。

**§31.18.22 との関係:** **§31.18.22** は **production 着手前**の **最新正本**であった。**本節**は **実装後**の **最新正本**である。**矛盾時**は **§31.18.22 の契約を維持**し、**実装が §31.18.22 と一致した**ことを **独立検証**で **確認**した。**§31.18.20** 以前の **`true_vot`** / **`participation_category`** 読み替えは **§31.18.22** のまま **有効**。

##### 31.18.23.1 実装範囲

**新規作成のみ**（既存 production・test・trial・validation script・制御処理は **変更なし**）。

- **`uxsim/network_wide_waiting_time_evaluation.py`**（**1,407 行**）
- **`tests/test_network_wide_waiting_time_evaluation.py`**（**933 行**）
- **合計 2,340 行**

**行数が大きい理由:** **network-wide waiting time**、**CW_z**、**ACWT**、**ACWWT**、**Reference replay**、**Reference World**、**Reference 専用 runner**、入力 **validation**、**physical_route_key**、**route_audit_identity**、**true_vot_per_second**、**evaluation_cohort** 集計、**counter 整合**、**simulation object 非保持**、異常停止、**専用 test** の正常系・異常系を、**短縮や高度な Python 技巧より処理順序の明示**で記述したためである。**Python 初心者向け可読性**を **研究用コードの正しさ**と **並列**に **優先**した。

**初期公開:** **`uxsim/__init__.py` からは公開しない**（**package 公開**は **未実装**）。

##### 31.18.23.2 新規ファイル

| ファイル | 役割 |
|---|---|
| `uxsim/network_wide_waiting_time_evaluation.py` | **4 方式共通** **production 実装** |
| `tests/test_network_wide_waiting_time_evaluation.py` | **公開入口契約**の **専用 test**（**51 件**） |

**最終 diff 確認時点:** **tracked 変更なし**。**新規未追跡**は **上記 2 ファイルのみ**（メモ更新前）。

##### 31.18.23.3 公開入口

**関数:** **`evaluate_network_wide_waiting_time`**

**対象方式（監査用 `method_name`、計算式は共通）:**

- **`signalized_uxsim`**
- **`fcfs`**
- **`batch`**
- **`tvt_mp`**

**主な引数:**

- **`real_world`**
- **`method_name`**
- **`evaluated_vehicle_names`**
- **`true_vot_per_second_by_vehicle_name`**
- **`evaluation_cohort_by_vehicle_name`**
- **optional** **`method_specific_participation_status_by_vehicle_name`**
- **optional** **`vehicle_plan_digest`**
- **optional** **`comparison_metadata`**

**基本契約（実装済み）:**

- **完走済み real World** のみ評価
- **real World を変更しない**
- **real World の simulation を再実行しない**
- **評価ごとに新しい局所 `_EvaluationContext`**
- **module global の可変 cache なし**
- **World へ評価状態を保存しない**
- **file 出力なし**
- **大量 console 出力なし**
- **Reference replay** は **同一評価内**の **physical_route_key** 共有のみ
- **正式結果に simulation object を保持しない**

**Vehicle 処理順:** **`evaluated_vehicle_names` の順**。**cohort 集計順**も **初出順**。

##### 31.18.23.4 dataclassと内部context

**公開・返却用（frozen dataclass 等）:**

- **`ReferenceReplayResult`**
- **`VehicleWaitingTimeRecord`**
- **`EvaluationCounters`**
- **`CohortWaitingTimeSummary`**
- **`NetworkWideWaitingTimeSummary`**
- **`NetworkWideWaitingTimeEvaluationResult`**

**内部のみ:** **`_EvaluationContext`**（**呼出しごとに新規**。**module global・real World・次回評価へ保存しない**）。

**返却の安全化（技巧のためではなく契約のため）:**

- **frozen dataclass**
- **tuple**
- **`MappingProxyType`**（**Reference 結果辞書**、**audit identity 辞書**、**comparison_metadata** の **トップレベル変更防止**）

##### 31.18.23.5 入力validation

**ValueError（代表）:** **DELTAN** が **厳密な Python int の 1** でない（**`True` 拒否**）、**DELTAT** 不正、**method_name** 不正、**evaluated_vehicle_names** 空・重複・不存在、**true_vot_per_second** 不足・**None**・**bool**・非数値・非有限・負、**evaluation_cohort** 不足・空文字、**optional status** 指定時の不足、**未完走**、**空 route**、**Link** 不正、**length** / **link.u** 不正、**timestep** が **non-bool int** でない、**actual arrival < departure**。

**RuntimeError（代表）:** **Reference** 未完走、**route** と **physical key** 不一致、**未検証 Reference**、**DELTAT** 不一致、**負の cumulative waiting timesteps**、**counter** / **summary** / **cohort** 矛盾、**simulation object 混入**。

**途中失敗:** **暫定 summary や部分正式結果を返さない**。

##### 31.18.23.6 physical_route_key

```text
(
    float(DELTAT),
    (
        (float(link.length), float(link.u)),
        ...
    ),
)
```

- **`Vehicle.traveled_route()`** を **actual route 正本**
- **順序維持**、**float 丸めなし**、**Link 名・DELTAN・文字列 key・set 不使用**
- **speed は `link.u`**

##### 31.18.23.7 route_audit_identity

```text
(str(link.name), ...)
```

- **同一 actual route** から構築
- **初出順**、**完全一致 tuple の重複登録なし**
- **Link 名のみ異なる**場合も **Reference replay は再実行しない**

##### 31.18.23.8 Reference replay共有

- **同一評価内**、**同一 physical_route_key** で **Reference replay 1 回**
- **2 台目以降**は **検証済み `ReferenceReplayResult` を再利用**
- **失敗した Reference** は **共有 dict へ保存しない**
- **評価間非持越し**（**global cache なし**）

**counter（正常終了時整合）:** **`evaluated_vehicle_count`**、**`unique_physical_route_count`**、**`reference_replay_run_count`**、**`reference_reuse_count`**、**`unique_audit_identity_count`**、**`duplicate_audit_identity_observation_count`** 等（**§31.18.22** と同型）。**`reference_reuse_count = evaluated − unique physical`** 等を **終了時に検証**。

##### 31.18.23.9 Reference World条件

**§31.18.22** / **§31.18.17** と **一致**（実装済み）。

- **`finalize_scenario(create_analyzer=False)`**
- **`DELTAN=1`**、**`REACTION_TIME=real_world.DELTAT`**
- **`random_seed=0`**、**`hard_deterministic_mode=True`**
- **print/save/show/show_progress=0**
- **直列 Node n+1**、**signal=[0]**、**order_control なし**、**flow_capacity なし**
- **Link:** **lanes=1**、**jam_density=0.2**、**capacity_in/out=1000000.0**、**内部名 reference_link_***
- **Vehicle 1 台**、**departure timestep=0**、**enforce_route**

**引き継がないもの:** 信号・各方式制御・実 World 混雑・他 Vehicle・actual departure 等（**§31.18.22** 同様）。

##### 31.18.23.10 Reference専用runner

**通常 `exec_simulation()` は使用しない**（**Analyzer なし World** の **UXsim 正式制約**。**§31.18.22.2** の **原典確認結果**と **一致**）。

**限定条件:** 一本道、**Vehicle 1 台**、route 固定、信号なし、order-control なし、他 Vehicle なし、**user_function なし**、**Reference replay 専用**。

**主要更新順序（現行 `exec_simulation()` 原典と独立照合済み）:**

1. **`Link.update()`**
2. **`Node.generate()`**
3. **`Node.update()`**
4. **`Node.transfer()`**
5. **`Vehicle.carfollow()`**
6. **living Vehicle の `Vehicle.update()`**
7. **route search** と **route preference 更新**
8. **`World.TIME` 更新**

**除外:** TVT-MP driver、downstream boundary observer、progress、World **user_function**、**simulation_terminated()**、**Analyzer.basic_analysis()** 等。

**ループ範囲:** **`T=0` から `TSIZE-1`**（通常 **`exec_simulation()`** と **同じ実処理対象**）。**Reference Vehicle が `end` になった timestep で停止**。**off-by-one 修正は不要**（独立確認済み）。

**完走上限（T_min,z 算定式ではない）:**

```text
sum(length / u) + (link_count + 2) * DELTAT + 60.0  [秒]
```

##### 31.18.23.11 Reference専用logging

**誤解を避ける正確な記述:**

- **「`log_t_link` だけを残す」ではない**
- **UXsim 本体の通常 Vehicle 走行記録と `log_t_link` を維持**する **Reference 専用 `record_log`** へ **差し替え**
- **`Vehicle.update()`** から **安全に呼べる**（**`create_analyzer=False`** の **Reference World** 用）
- **除外するのは Analyzer への average_speed 関連書込みのみ**

**維持する主な記録:**

- **`log_t`**, **`log_state`**, **`log_link`**, **`log_x`**, **`log_s`**, **`log_v`**, **`log_lane`**, **`log_t_link`**

**除外:**

- **`W.analyzer.average_speed_count`**
- **`W.analyzer.average_speed`**

**理由:** **`Vehicle.traveled_route()`** は **`log_t_link`** を使用する（**UXsim 原典独立確認**）。**本体 `record_log()`** に **近い明示的処理**とした。

##### 31.18.23.12 timestepを正本とするCW_z、ACWT、ACWWT

**§31.18.22.6 と一致**（実装済み）。

```text
cumulative_waiting_time_timesteps
=
(actual_arrival_timestep - actual_departure_timestep)
-
(reference_arrival_timestep - reference_departure_timestep)

cumulative_waiting_time_seconds
=
cumulative_waiting_time_timesteps * real_world.DELTAT
```

- **負の timestep 差** → **RuntimeError**（**tolerance なし**、**0 へ丸めない**）
- **`near_zero_negative_cumulative_waiting_time_count` は作らない**
- **`Vehicle.travel_time`** は **整合確認**のみ（**差分の正本にしない**）

**true VOT:** **`true_vot_per_second`**。**秒値へ直接乗算**。**3600 換算なし**。**0 許容**。

**ACWT / ACWWT:** 全体は **`evaluated_vehicle_count`** を分母。**cohort 別平均**は **その cohort の Vehicle 数**を分母。

##### 31.18.23.13 evaluation cohort集計

- **`evaluation_cohort`:** TVT-MP で割り当てた集合を **他方式でも同じ Vehicle 名**で追跡（例: **`tvt_participating_cohort`**、**`tvt_nonparticipating_cohort`**）
- **`method_specific_participation_status`:** **任意**（共通式の **必須入力にしない**）
- **summary:** 全体＋**cohort 別**（**vehicle_count**、**total/average CW**、**total/average weighted**）
- **cohort 順:** **`evaluated_vehicle_names` 初出順**

**nonparticipating 固定 Vehicle 集合**の **正式 4 方式比較**は **本節の scope 外**（**未実装**）。

##### 31.18.23.14 simulation object非保持

**正式結果に含めない:** Reference World/Vehicle/Node/Link、**Analyzer**、**real World**、actual Vehicle/Link、**`_EvaluationContext`**。

**返却前検査:** **dataclass**、**Mapping**、**list**、**tuple** を辿り、**World / Vehicle / Node / Link / Analyzer** があれば **RuntimeError**。**id による循環検出**（**短縮のためではなく混入防止契約**）。

##### 31.18.23.15 専用testの対象

**ファイル:** **`tests/test_network_wide_waiting_time_evaluation.py`**

**件数:** **51 passed**（**16.02 s**、利用者 **pytest -q**）

**カバー（代表）:** Reference **共有**、**Link 名のみ差**、**audit identity**、**physical key 分離**（順序・length・u・**DELTAT**）、**CW_z=0**、**起点待ち 4 s**、**負 CW_z 停止**、**未検証 Reference 非包含**、**4 方式同一計算**、**true VOT**、**cohort**、入力 **validation**、**評価間非持越し**、**global cache なし**、**side effect なし**、**CASE 8 主要契約**（**script 実行はしない**）。

##### 31.18.23.16 独立確認結果

**利用者 Terminal 確認（Cursor 外）:**

| 確認 | 結果 |
|---|---|
| **変更範囲** | tracked 変更なし。**新規未追跡 2 ファイルのみ**（メモ更新前） |
| **`python -m py_compile`**（上記 2 module） | **成功** |
| **`pytest -q` 専用 test** | **51 passed**, **16.02 s** |
| **CASE 1〜8 validation script** | **All cases passed.** |

##### 31.18.23.17 UXsim原典との照合結果

**利用者が `Vehicle.traveled_route()`、`Vehicle.record_log()`、`World.finalize_scenario()`、`World.exec_simulation()` を独立確認:**

1. **`traveled_route()`** は **`log_t_link`** を使用
2. **`record_log()`** の **Analyzer 依存**は主に **average_speed** 書込み
3. **`create_analyzer=False`** では **`W.analyzer` 属性を作らない**
4. **Analyzer なし World** を **通常 `exec_simulation()`** で実行しては **ならない**
5. **Reference 専用 runner** の更新順序は **現行 exec_simulation()** と **一致**
6. **両者とも `T=0`〜`TSIZE-1`** を実処理対象
7. **`end` で停止**する現方式に **off-by-one 修正不要**

##### 31.18.23.18 Python初心者向け可読性の確認

**独立評価:** **if / for / while / 中間変数**中心。**Vehicle 1 台処理**、**Reference World 構築**、**runner 更新順**、**CW_z 計算**、**集計**、**異常停止**、**test の準備→実行→期待**が **追える**。

**局所的に高度:** **`MappingProxyType`**、**再帰的 simulation object 検査**、**循環 id 検出** → **安全契約のため**。**短縮再構成は行わない**。

##### 31.18.23.19 CASE 8歴史的記述の扱い

**`research_scripts/validate_uxsim_single_vehicle_network_wide_waiting_time_basis.py`** の **CASE 8 summary** に **`Production implementation has not started.`** が **残る**。

- **CASE 8 script 作成時点**の **歴史的表示**
- **今回 script は変更しない**（**CASE 1〜8 回帰**維持）
- **現行状態**は **本 §31.18.23** および **進捗 §21.9.12** を **優先**

##### 31.18.23.20 未実装事項

**本節完了範囲外（完了扱いしない）:**

- **`uxsim/__init__.py` package 公開**
- **Analyzer 薄い呼出し口**
- **CSV / JSON / DataFrame**、**research output 統合**
- **既存 trial 組込み**
- **3,000 台**からの **ACWT・ACWWT 正式算出**
- **signalized UXsim / FCFS / BATCH / TVT-MP の正式 4 方式比較**
- **nonparticipating 固定 Vehicle 集合**の **正式 4 方式比較**
- **performance 最適化**、**並列化**、**persistent cache**

##### 31.18.23.21 次の再開地点

1. **メモ更新後**、利用者が **対象 4 ファイル**（**2 code + 2 memo**）を **Terminal で確認**
2. **`py_compile`**
3. **専用 pytest**
4. **CASE 1〜8 回帰**
5. **`git diff`**
6. **`git add`**
7. **cached diff 確認**
8. **`commit`**（**document を含む**。メッセージは **利用者が diff 確認後に確定**）
9. **commit 結果・最新 commit・残存変更**
10. **別指示で push**
11. **push 後 status・最新 commit・local/remote 一致**

**commit 候補（利用者確定）:**

- `uxsim/network_wide_waiting_time_evaluation.py`
- `tests/test_network_wide_waiting_time_evaluation.py`
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_5.md`
- `ORDER_EXCHANGE_PROGRESS_4.md`
