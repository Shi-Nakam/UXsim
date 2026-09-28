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

## TVT-MP評価期間とbaseline内部余白の方針を確定（2026-09-28）

正式な技術詳細は、詳細設計第4巻「TVT-MP評価期間・baseline内部余白・実World終了制御」を参照する。

- 評価対象が 10,000 timestep の場合、評価時刻は `T = 0` から `9999` である。
- `T = 9999` を含む全評価時刻で、通常どおり TVT-MP 形成を検討する。
- 終盤だけ driver をスキップしない。
- 終盤だけ baseline horizon を短縮しない。
- baseline 不足例外を握り潰さない。
- 意思決定窓の `6` と baseline horizon は独立した設定である。
- baseline horizon は 30、50 などを取り得る。
- 最終評価時刻においても、`baseline_horizon_steps + 1` 個の残り時刻数を確保する。
- 最終評価時刻自身を、残り時刻数の 1 個目に含める。
- `evaluation_end_timestep = evaluation_timestep_count - 1` である。
- 必要条件は、`internal_TSIZE - evaluation_end_timestep >= baseline_horizon_steps + 1` である。
- 同じ条件を評価 timestep 数で表すと、`internal_TSIZE >= evaluation_timestep_count + baseline_horizon_steps` である。
- 10,000 timestep、horizon 50 なら、`evaluation_end_timestep` は `9999`、`internal_TSIZE` は 10,050 以上である。
- `internal_TSIZE = 10049` は不足であり、10,050 なら十分である。
- 評価 timestep 数との比較では、内部 `TSIZE` は baseline horizon 分だけ長い。
- 「評価期間より horizon + 1 timestep 長くする」とは表現しない。
- 実 World の交通計算は `T = 9999` までであり、処理後の `World.T` は `10000` である。
- `T = 10000` 以降の実 World 交通計算は行わない。
- 内部余白は baseline fork だけが仮想計算に利用する。
- World の正式属性名は `order_control_tvt_evaluation_end_timestep` とする。
- 初期値 `None` では従来 UXsim の `TSIZE` 終了契約を使う。
- 評価終了後に `exec_simulation` を再度呼んでも、実 World を内部余白へ進めない。
- 評価終了時に `simulation_terminated` と `basic_analysis` を一度だけ実行する。
- baseline fork では、複製直後に fork 側の `order_control_tvt_evaluation_end_timestep` だけを `None` へ戻す。
- fork は従来どおり horizon 全体を計算し、fork 上で終了集計を実行しない。
- 評価終了時の未完了 Vehicle は未完了のまま扱い、将来の到着結果を補完しない。
- 時間に沿う研究出力は評価期間だけを対象とし、内部余白を含めない。
- 評価終了までに actual passage が判明しない TVT 結果は、失敗や 0 ではなく actual outcome 未観測として扱う。
- 正式支払額、正式補償額、成立時履歴は残す。
- 未観測の場合、実績時間節約、実績遅延、実績利得、満足評価は計算しない。
- 具体的な actual outcome の型名や field 名は後続実装時に決める。
- `Node.transfer` による物理通過順は、今回まだ変更しない。

## 最新の再開地点

1. 詳細設計第4巻と進捗第3巻を Terminal で限定確認する。
2. `git diff --check` と変更ファイルを確認する。
3. 文書 2 ファイルを commit する。
4. commit 名に `document` を含める。
5. commit と push を分離する。
6. 保存後、自動起動・評価終了制御の完全実装前仕様を作る。
7. その後に Python と専用テストを実装する。
8. `Node.transfer` による物理通過接続は、その後の別段階とする。

## TVT-MP自動起動・評価終了制御の完全実装前仕様を確定（2026-09-28）

正式な技術詳細は、詳細設計第4巻「TVT-MP自動起動・評価終了制御・fork制限解除 完全実装前仕様」を参照する。

- 詳細設計第4巻へ、TVT-MP 自動起動、実 World の評価終了制御、baseline fork の評価終了制限解除に関する完全実装前仕様を記録した。
- 利用者判断が必要な事項は解消済みである。
- World の正式属性は `order_control_tvt_evaluation_end_timestep` とする。
- 初期値は `None` とする。
- `None` の場合は、従来 UXsim の `TSIZE` 終了契約を使い、TVT-MP driver を自動起動しない。
- 10,000 timestep 評価では、評価終了時刻は `9999` とする。
- 評価終了時刻が設定されている場合だけ、各処理時刻で `run_tvt_mp_driver(W)` を 1 回自動起動する。
- driver は時刻ループの先頭、進捗表示、`Link.update`、`Node.generate`、`Node.transfer`、`Vehicle.update` より前に呼ぶ。
- `T = 0` と最終評価時刻を含む。
- driver 例外は捕捉せず、その時刻の交通計算へ進まない。
- `uxsim.py` では driver をファイル先頭で import せず、`exec_simulation` 内で局所 import する。
- 対象 Node の収集は driver だけが行い、`uxsim.py` へ重複実装しない。
- 対象 Node が 0 件の場合は、driver の既存完全 no-op を維持する。
- 対象 Node が 0 件なら、baseline horizon に対する内部余白を要求しない。
- 評価終了時刻の型、`bool`、負数、`TSIZE` 以上は交通計算前に `ValueError` とする。
- 対象 Node が 1 件以上の場合だけ、driver の共通設定検査で内部余白を検査する。
- 内部余白条件は `internal_TSIZE - evaluation_end_timestep >= baseline_horizon_steps + 1` である。
- 10,000 timestep、horizon 50 なら `internal_TSIZE` は 10,050 以上である。
- `internal_TSIZE = 10049` は不足である。
- 余白不足は driver 開始時刻の記録前に `ValueError` とする。
- baseline driver 側の既存余白検査も残す。
- 実 World は最終評価時刻を含めて処理し、処理後の `World.T` は評価終了時刻 `+ 1` となる。
- 評価終了到達時に既存 `simulation_terminated` を 1 回呼ぶ。
- `Analyzer.basic_analysis` も既存経路で 1 回実行する。
- 評価終了後に `exec_simulation` を再度呼んでも、交通計算も終了集計も行わず、正常終了コード `1` を返す。
- `check_simulation_ongoing` は、評価終了時刻の次の時刻で `False` を返す。
- 評価終了より前の分割実行では終了集計せず、その後再開できる。
- baseline fork は `World.copy` 直後に、fork 側だけ `order_control_tvt_evaluation_end_timestep = None` とする。
- fork 側の解除は `_validate_copied_fork` より前、collector 接続より前、baseline forward より前に行う。
- 実 World の評価終了時刻は変更しない。
- fork は既存の `horizon + 1` 契約を維持し、fork 上で終了集計を実行しない。
- 未完了 Vehicle は未完了のまま扱い、将来の到着結果を補完しない。
- actual outcome 未観測の型や field は今回実装しない。
- 新規専用テスト予定ファイルは `tests_order_control_tvt_mp_evaluation_end.py` とする。
- 実装対象は `uxsim/uxsim.py`、`uxsim/order_control_tvt_mp_driver.py`、`uxsim/order_control_baseline_driver.py`、新規専用テストである。
- `Node.transfer` による TVT 順位の物理利用は今回実装しない。
- actual passage、actual outcome、実績評価、満足評価、welfare、リンク分析の評価期間限定は未実装のままである。

## 最新の再開地点

1. 詳細設計第4巻と進捗第3巻を Terminal で限定確認する。
2. `git diff --check` と変更ファイルを確認する。
3. 文書 2 ファイルを commit する。
4. commit 名に `document` を含める。
5. commit 名に `complete` を使用しない。
6. commit と push を分離する。
7. 保存後、完全実装前仕様どおり Python と専用テストを実装する。
8. 実装後は Cursor 報告だけで完了判断せず、本番コード、専用テスト、差分、テスト結果を独立確認する。
9. `Node.transfer` による物理通過接続は、その後の別段階とする。

## TVT-MPをWorldから起動し評価終了時刻で止める接続を実装・独立確認（2026-09-28）

正式な技術詳細は、詳細設計第4巻「TVT-MP自動起動・評価終了制御・fork制限解除 完全実装前仕様」の §28 を参照する。

- 本番 3 ファイルと新規専用テストを実装した。
- World 属性 `order_control_tvt_evaluation_end_timestep` を追加した。初期値は `None` である。
- 評価終了時刻が設定された World だけで、各時刻に driver を起動する。
- driver は `Link.update` より前である。
- 最終評価時刻を含めて処理する。
- 評価終了後は実 World を内部余白へ進めない。
- 終了集計は一度だけである。
- fork 側だけ評価終了制限を解除する。
- 対象 Node が 1 件以上のときだけ内部余白を検査する。
- 対象 Node が 0 件なら余白は不要である。
- 専用テスト 22 件は成功した。直接実行は `22 tests passed`、pytest は `22 passed in 14.20s` である。
- 主要 5 ファイルは `179 passed in 19.11s` である。
- 関係テストは `994 passed in 26.16s` である。
- 変更・修正した 6 ファイルの `py_compile` は成功した。
- 正式サンプルは従来結果と一致した。completed trips は 735 / 810、average speed は 11.7 m/s である。
- 既存テスト 2 件を正式契約へ限定更新した。`exec_simulation` は条件付きで driver へ接続し、`Node.transfer` は TVT を扱わない。`downstream_boundary_result` は保存済み結果型への期待追随である。
- 未実装は、`Node.transfer` による TVT 順位の物理利用、actual passage、actual outcome、実績評価、満足評価、welfare、リンク分析の評価期間限定、対象外 Node の順位台帳削除である。

## 最新の再開地点

1. 第4巻と進捗第3巻を Terminal で限定確認する。
2. 実装・テスト 6 ファイルの変更範囲を確認する。
3. `git diff --check` を実行する。
4. 文書、実装、テストを同一保存単位で commit する。
5. commit 名に `document` を含める。
6. commit 名に `complete` を使用しない。
7. commit と push を分離する。
8. 保存後、`Node.transfer` による TVT 順位の物理利用へ進む前に、その完全実装前仕様を作成する。
9. 実装後は Cursor 報告だけで完了判断せず、独立確認する。

## TVT-MP確定順位の物理通過接続に関する設計判断を確定（2026-09-29）

正式な記録は、詳細設計第4巻「TVT-MP確定順位の物理通過接続 設計判断」を参照する。完全実装前仕様はまだ作成していない。

- TVT 順位は通過保証ではなく、通過試行機会の順位である。
- 実 World は、T の driver 完了後の最新確定順位を使う。
- 現在の `incoming_vehicles` だけを候補にする。
- 通過済み Visit 集合は追加しない。
- 実進路は `Vehicle.route_next_link` である。
- formal route を強制しない。
- 物理先頭、容量、入口空間不足は一時スキップする。
- clearance 未充足だけ、その時刻の対象 Node 処理を終了する。
- signal 判定を追加しない。
- baseline fork は、T-1 以前の確定順位を維持する。
- T の新順位を baseline へ混ぜない。
- fork copy 時点の台帳複製で区別する。
- `confirmed_at_timestep` は追加しない。
- baseline fork は、過去確定群を先に試す。
- その後、通常 baseline 群を既存の通常合流で処理する。
- 一時スキップした過去確定 Vehicle を通常群へ混ぜない。
- 到着列を一時差し替えない。
- 許可集合付き通常合流 helper を基本方針とする。
- collector と observer の一回性を維持する。
- actual passage と actual outcome は次段階である。
- 以前の、baseline fork では TVT 順位を使わないという中間整理は訂正した。
- 利用者判断が必要な事項は、現時点で残っていない。

## 最新の再開地点

1. 第4巻と進捗第3巻を Terminal で分割確認する。
2. `git diff --check` と変更ファイルを確認する。
3. 文書 2 ファイルを commit する。
4. commit 名に `document` を含める。
5. commit 名に `complete` を使用しない。
6. commit と push を分離する。
7. 保存後、この設計判断を基に完全実装前仕様を作成する。
8. 完全実装前仕様を保存してから Python と専用テストを実装する。
9. 実装後は本番コード、専用テスト、差分、回帰結果を独立確認する。
10. その後、actual passage・actual outcome の設計へ進む。
