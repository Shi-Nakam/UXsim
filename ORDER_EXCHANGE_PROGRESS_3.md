# 交差点順序制御・進捗メモ 第3巻

記録開始日: 2026-09-28

## 第3巻への移行

- 進捗第2巻が長大化したため、第3巻へ移行した。
- 進捗第2巻は削除せず、atomic apply 実装、スモークテスト、predicted and actual outcome evaluation 仕様までの正式な過去記録として保存する。
- 以後の最新進捗は第3巻を参照する。
- 詳細設計の最新巻は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md` である。
- 過去の詳細設計は第1巻から第3巻を参照する。
- 移行時の最新保存済みコミットは `f616b71` である。

## 現在地

- baseline から atomic apply まで実装・検証済み。
- atomic apply 専用テスト 38 件成功。
- 独立確認の関連テスト 246 件成功。
- UXsim 正式サンプルは実装後も正常完走。
- predicted and actual outcome evaluation の詳細将来仕様は詳細設計第3巻へ保存済み。
- 現在は TVT-MP 上位 driver の設計段階である。
- 上位 driver は未実装である。

## 上位driver設計前調査で確認・採用した事項

- 正式処理順は、未確定 Visit 登録、既到着 Visit 確定、先頭非参加 Visit 確定、残りの TVT 検討である。
- `baseline_arrival_timestep <= T` の Visit を既到着として確定する。
- 後段失敗時も、正常完了済みの登録と先行確定を取り消さない。
- 順位台帳は World がシミュレーション中保持する。
- 参加情報の正本は `Vehicle.participates_in_order_exchange` である。
- 同一時刻 `T` では上位 driver を 1 回だけ実行する。
- TVT 対象 Node は World 設定から自動収集する。
- baseline horizon と TVT 候補数上限は全対象 Node 共通とする。
- 上位 driver 成功結果は atomic apply 結果だけを保持する。
- 次の実装段階は上位 driver 単体までとする。
- World 自動起動と `Node.transfer` による物理通過は後続段階とする。

## 未実装

- 上位 driver
- World 自動起動
- 物理通過接続
- actual passage
- actual outcome
- 事後評価実装
- 満足評価

## 未確定

- driver 関数名
- 成功結果型名
- World 属性名
- TVT 対象 Node 判定属性
- 設定属性名
- 二重実行時の例外種別
- 空対象時の具体的な成功結果
- 新規ファイル名
- `uxsim.py` を driver 単体実装時点で変更するか

## 次の再開地点

1. 新しい 2 ファイルを Terminal で限定確認する。
2. 旧詳細設計第3巻と旧進捗第2巻へ移行先を短く追記する。
3. `git diff --check` を実行する。
4. 文書 4 ファイルだけが変更されていることを確認する。
5. commit 名に `document` を含めて commit する。
6. commit と push を分ける。
7. 保存後、詳細設計第4巻で上位 driver 完全実装前仕様を作成する。

## TVT-MP上位driverの完全実装前仕様を確定（2026-09-28）

正式な技術詳細は、詳細設計第4巻「TVT-MP上位driver・完全実装前仕様」を参照する。

- 詳細設計第4巻へ、上位driverの完全実装前仕様を記録した。
- 公開関数名は `run_tvt_mp_driver` とする。
- 成功結果型は `OrderControlTvtMpDriverResult` とする。
- 公開入力は `real_W` の位置引数1つとする。
- 成功結果は `atomic_apply_set_result` だけを保持する。
- TVT対象Nodeが0件の場合は `atomic_apply_set_result=None` とする。
- TVT対象Nodeが0件の場合は、World、順位台帳、Vehicle、driver開始時刻を一切変更しない正常no-opとする。
- 対象Nodeが引き続き0件なら、同じ実時刻Tに再度呼ばれても再び正常no-opとする。
- TVT対象Nodeが1件以上の場合は、同一時刻の二重実行と時刻逆行を共通設定より先に検査する。すべての検査に通過した後、16段開始前にdriver開始時刻を記録する。
- 対象Nodeが1件以上ある同じTでの再実行は拒否する。
- 順位台帳はWorldが保持し、実行ごとに作り直さない。
- TVT対象Nodeは `order_control_type == "time_value"` かつ `order_control_eligible is True` のNodeを、World登録順に収集する。
- 参加情報の正本は `Vehicle.participates_in_order_exchange` とする。
- declared VOT=0を不参加扱いしない。
- baseline horizonの共通初期値は6とする。
- TVT候補Visit数上限は暗黙の既定値を置かず、World初期値をNoneとする。
- TVT対象Nodeが1件以上ある場合、候補数上限はbool以外のPython intかつ1以上を明示設定する。
- TVT対象Nodeが0件の場合、候補数上限がNoneでも正常no-opとする。
- 完成済み16段を明示的な順序で呼び、最後にatomic applyを全Node一括で1回呼ぶ。
- 正常な取引不成立、fallback、NO_VISITS_TO_CONFIRMはdriverの正常成功になり得る。
- 後段例外時も、正常完了済みの未確定Visit登録、既到着Visit確定、先頭非参加Visit確定は取り消さない。
- 上位driver単体の実装では、World自動起動とNode.transferによる物理通過接続を行わない。
- 本番予定ファイルは `uxsim/order_control_tvt_mp_driver.py` とする。
- 専用テスト予定ファイルは `tests_order_control_tvt_mp_driver.py` とする。
- `uxsim/uxsim.py` はWorld属性の初期化だけを変更予定とする。
- 実装では短さや高度なPython技法より、初学者が16段の流れを追える明示的な構造を優先する。
- 利用者判断が必要な事項は解消済みである。
- 対象から外れたNodeの順位台帳を削除する時期だけは将来課題として残し、今回の実装では削除しない。

## 最新の再開地点

1. 詳細設計第4巻と進捗第3巻をTerminalで限定確認する。
2. `git diff --check`を実行する。
3. 変更対象が第4巻と進捗第3巻だけであることを確認する。
4. 文書をcommitする。
5. commit名には `document` を含める。
6. commitとpushを分ける。
7. 保存後、上位driver本番と専用テストを実装する。
8. 実装対象は、新規本番、新規専用テスト、World属性初期化の3ファイルとする。

## TVT-MP上位driverを実装・独立確認（2026-09-28）

正式な契約は、詳細設計第4巻「TVT-MP上位driver・完全実装前仕様」を参照する。本節はその実装と独立確認の記録である。

- 上位driver本体 `uxsim/order_control_tvt_mp_driver.py` と専用テスト `tests_order_control_tvt_mp_driver.py` を実装した。
- 公開関数は `run_tvt_mp_driver(real_W)`、成功結果型は `OrderControlTvtMpDriverResult`、field は `atomic_apply_set_result` である。
- `uxsim/uxsim.py` の `World.__init__` へ、順位台帳、開始時刻、baseline horizon 初期値6、候補Visit数上限初期値 `None` の4属性を追加した。
- 完成済み16段を正式順に接続し、最後に atomic apply を全Node一括で1回呼ぶ。
- 対象Node 0件は、World、順位台帳、Vehicle、開始時刻を変更しない正常 no-op である。同じ `T` でも対象が0件なら再び no-op である。
- 対象Nodeが1件以上のときだけ、設定検査の前に同一 `T` と時刻逆行を拒否し、検査成功後に開始時刻を記録する。以後の例外では開始時刻を戻さない。
- 順位台帳は World が保持し、実行ごとに作り直さない。
- 参加表は2段目成功後に、`Vehicle.participates_in_order_exchange` から構築する。declared VOT=0 では判断しない。
- 専用テストは定義、`TESTS` 登録、pytest 収集がいずれも31件である。実部品統合テストを1件追加した。
- `test_real_sixteen_stages_reach_atomic_apply_on_quiet_junction` では、driver 内の16部品を monkeypatch せず、本物の部品で atomic apply まで到達する。経路は `NO_VISITS_TO_CONFIRM` である。
- 専用テストは全31件成功した。直接実行は `31 tests passed` である。
- `tests_order_control_tvt_baseline_fork_alignment.py` と専用テストをまとめて実行し、56 passed in 14.57s である。
- baseline から atomic apply、driver までの関係回帰は 940 passed in 20.22s である。失敗はない。
- `Node.transfer` による物理通過順は、まだ検証対象外である。
- 本番、`uxsim.py`、専用テスト、期待 field を直した既存テストの py_compile は成功した。
- `python demos_and_examples/example_00en_simple.py` は1200秒まで正常完走した。completed trips は 735 / 810、average speed は 11.7 m/s である。正式サンプルは driver を直接呼ばない。
- `tests_order_control_tvt_baseline_fork_alignment.py` の期待 field 集合へ `downstream_boundary_result` を追加した。
- これは今回の回帰ではない。保存済みコミット `c703d9b` の本番型に既にあった field が、既存テスト期待値から漏れていた追随漏れである。
- 未実装は、World 自動起動、`exec_simulation` 接続、`Node.transfer` による物理利用、actual passage、actual outcome、事後評価、満足評価、welfare、対象外 Node の台帳削除である。
- driver 単体では物理通過順は変わらない。

## 最新の再開地点

1. 第4巻と進捗第3巻を Terminal で限定確認する。
2. Python・テスト4ファイルの変更範囲を確認する。
3. `git diff --check` を実行する。
4. 文書、実装、テストを同一保存単位で commit する。
5. commit 名に `document` を含める。
6. commit と push を分離する。
7. 保存後、World から driver を自動起動する接続の設計へ進む。
8. `Node.transfer` による物理通過接続は、その後の別段階とする。
