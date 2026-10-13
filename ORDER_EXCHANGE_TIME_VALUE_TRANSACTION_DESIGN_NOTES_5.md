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
