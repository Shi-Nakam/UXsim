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
