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
