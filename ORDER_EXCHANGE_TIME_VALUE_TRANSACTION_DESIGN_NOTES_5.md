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
