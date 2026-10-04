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

## TVT-MP確定順位の物理通過接続 完全実装前仕様を確定（2026-09-29）

正式な仕様は、詳細設計第4巻「TVT-MP確定順位の物理通過接続 完全実装前仕様」を参照する。入力は、同じ第4巻の「TVT-MP確定順位の物理通過接続 設計判断」である。TVT 物理通過、明示 mode、空の到着列で台帳を要求しない処理の Python とテストは作業中であり、まだ保存していない。登録前凍結コピーの Python 実装は、まだ行っていない。

- 設計判断を、関数名、引数、呼出し順、テスト契約まで具体化した。
- 正式な新規 module は `uxsim/order_control_tvt_mp_physical_transfer.py` である。
- `Node.transfer` は、FCFS、BATCH の次に、`time_value` かつ eligible の TVT 物理通過を置く。
- 公開関数は `transfer_tvt_mp_passage_attempts(node)` である。戻り値は `None` である。
- 通常合流 helper は `Node._transfer_normal_merge(self, allowed_vehicles=None, enforce_order_control_clearance=False)` である。
- 1 台移動 helper は `Node._transfer_one_vehicle_between_links(self, vehicle, inlink, outlink)` である。
- 終了処理は `Node._finish_node_transfer(self)` であり、`Node.transfer` の正常経路で 1 回だけ呼ぶ。
- 実 World は最新の確定群だけを使う。未確定は通常群へ落とさず、`RuntimeError` である。
- TVT 順位適用 baseline fork は、凍結台帳の過去確定群を先に試し、過去確定群の clearance で終了しなければ開始時の通常群を通常合流する。
- TVT 順位適用 baseline fork の通常 baseline 群にも order-control clearance を適用する。汎用 baseline fork には適用しない。
- 通常群の選択順は、既存の通常合流のままである。
- 通常群の clearance 未充足で、その時刻の通常群処理を終了する。
- 通常群の通過成功後も、order-control clearance 履歴を更新する。
- 通常の信号交差点では、信号設定上の全赤時間によって clearance を確保する。
- UXsim の自動付与に依存せず、全赤時間を明示的に設定する。
- TVT、FCFS、BATCH では order-control clearance を使う。
- order-control clearance の条件は strict greater-than である。
- clearance 設定値0でも、別 inlink への切替は同一 timestep 内に許されない。
- clearance 設定値0では、最短で次の timestep に通過できる。
- clearance 設定値1では、最短で次の次の timestep に通過できる。
- clearance 設定値1では、間の 1 timestep を確実に空ける。
- 「clearanceなし」という表現は、order-control clearance 設定値0を指す語として使わない。
- 既存名に `no_clearance` を含む関数とテストは、名称を変更しない。名称だけから clearance 設定値0と同じ意味だと推測しない。
- 研究評価の基本方式は、安全のための clearance ありである。
- 研究評価で使う clearance 値は、各実験設定に従う。本訂正で新しい数値は決めない。
- 既存 candidate 局所仮想計算との整合確認により、通常 baseline 群の clearance 契約を修正した。
- これは新しい利用者判断ではない。
- 実進路は `Vehicle.route_next_link` である。formal route は強制しない。
- 正常な TVT 通過候補では `route_next_link` は必ず存在する。
- `route_next_link is None` は一時スキップではなく `RuntimeError` である。
- formal route を代替進路として使用しない。
- 次時刻まで待って自然解消する状態として扱わない。
- 目的地到着、trip abort、局所仮想計算の下流境界等とは契約を分ける。
- 物理先頭、容量、入口空間不足は一時スキップする。clearance 未充足だけ、その時刻を終了する。
- collector は通過 1 回につき prepare と apply を 1 回行う。observer は `Node.transfer` の外のままである。
- 通過済み Visit 集合と `confirmed_at_timestep` は追加しない。
- actual passage と actual outcome は未実装のままである。
- 新規専用テストは `tests_order_control_tvt_mp_physical_transfer.py` の 34 件である。空の到着列で台帳を要求しない 1 件を、未保存の専用テストへ追加済みである。
- 既存のソース検査 2 件だけ、TVT 物理通過を呼ぶ契約へ更新する。FCFS、BATCH、通常 Node、正式サンプルは現行結果を維持する。
- baseline fork には、汎用 fork と TVT 順位適用 fork の 2 種類がある。
- collector の明示 bool で区別する。正式属性名は `apply_copied_tvt_confirmed_ranks` である。既定値は `False` である。
- 汎用 fork は、従来の通常合流を維持する。Node 別順位台帳を要求しない。
- TVT 順位適用 fork だけが、T-1 以前の確定順位を物理適用する。必要な Node 別順位台帳の欠如は `RuntimeError` である。
- Node 別順位台帳の有無から、fork 種別を推測しない。
- この仕様不足は、実装後の既存 baseline 回帰で判明した。代表例外は `RuntimeError: Node junction: TVT rank ledger is missing.` である。
- 失敗した既存回帰は、`tests_order_control_baseline_driver.py`、`tests_order_control_tvt_baseline_fork_alignment.py`、`tests_order_control_tvt_mp_evaluation_end.py` の一部である。
- 既存 baseline テストの期待値は変更していない。
- 明示 mode により、既存の引数なし constructor と 2 つの公開 baseline API の後方互換を維持する。
- collector と baseline driver の既存テストへ追加する mode 契約は、専用テスト 34 件へ含めない。関係回帰として別に記録する。
- TVT 順位適用 baseline API へ渡された順位台帳を、T の未確定登録前に独立複製する。
- 複製を fork World へ明示接続する。
- T の未確定登録は元台帳だけへ適用する。
- fork には T の新規登録を混ぜない。
- 正常 driver 経路と baseline API 単独経路の双方を同じ契約にする。
- この不足は fork alignment 回帰で判明した。
- 既存テストの期待値は変更していない。
- 独立性テスト `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` は、`tests_order_control_tvt_baseline_driver_registration.py` へ置く。専用テスト 34 件には含めない。
- Python 実装は作業中で未保存である。登録前凍結コピーの接続は、まだ実装していない。
- 利用者判断が必要な事項は残っていない。これは制度変更ではない。既存の汎用 baseline API と、TVT 順位台帳登録付き baseline API を共存させ、呼出し側台帳を fork と共有しない技術的接続である。
- 今回の文書修正では、Python とテストは変更していない。作業開始前からの未保存差分は残っている。

## 最新の再開地点

1. 今回の文書修正を Terminal で限定確認する。
2. Python とテストの作業開始前からの未保存差分が、今回の文書作業で変化していないことを確認する。
3. `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` で、対象 Node 検査のあと、登録前に `copy.deepcopy` し、fork World へ接続する。
4. 時刻 T の未確定登録は、元の呼出し側 mapping だけへ適用する。
5. `tests_order_control_tvt_baseline_driver_registration.py` へ `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` を追加する。専用テスト 34 件には含めない。
6. fork alignment と baseline driver registration を再実行する。既存期待値は、失敗を隠すために変えない。
7. 専用テスト 34 件、FCFS、BATCH、正式サンプルを再実行する。
8. 実装結果を第4巻と進捗第3巻へ記録する。
9. 差分と回帰結果を独立確認してから commit する。

上記の再開地点は履歴として残す。実装、独立確認、回帰結果は、本巻末尾の「TVT-MP確定順位の物理通過接続を実装・独立確認・検証（2026-09-29）」と、詳細設計第4巻の「TVT-MP確定順位の物理通過接続 実装・独立確認・検証結果」を参照する。

## TVT-MP確定順位の物理通過接続を実装・独立確認・検証（2026-09-29）

正式な記録は、詳細設計第4巻「TVT-MP確定順位の物理通過接続 実装・独立確認・検証結果」を参照する。入力は、同じ第4巻の完全実装前仕様と設計判断である。それらは履歴として残し、削除も短縮もしない。

最新の保存済み・push 済みコミットは `cc0cafa` である。本節の本番、テスト、文書はまだ Git 保存していない。`diagnostics/order_control.zip` は未追跡のままである。

完全実装前仕様どおり実装した。実装中に判明した仕様不足は、明示 mode、空の incoming snapshot、登録前凍結コピー、テスト fixture の直接配置で解消した。既存の期待値や assert は、失敗を回避するために変更していない。

実装した本番 4 ファイル:

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_driver.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`

変更・新規作成したテスト 7 ファイル:

- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_mp_evaluation_end.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

- `Node.transfer` は、FCFS、BATCH、TVT、通常合流の順である。FCFS と BATCH は早期 return のままで、関数本体は変更していない。
- TVT は time_value 分岐の中で局所 import し、`transfer_tvt_mp_passage_attempts(node)` のあと、正常時だけ `_finish_node_transfer()` を 1 回呼ぶ。例外時は終了処理へ到達しない。
- Node private helper は、`_transfer_one_vehicle_between_links`、`_transfer_normal_merge`、`_finish_node_transfer` である。clearance helper は `_order_control_clearance_blocks_passage` である。
- 実 World、TVT 順位適用 baseline fork、汎用 baseline fork を、順位台帳を読む前に 3 分類する。台帳の有無から種別を推測しない。
- collector の明示 bool は `apply_copied_tvt_confirmed_ranks` である。既定値は False である。非 bool は `ValueError` である。汎用 API は False、TVT 用 API は True を明示する。
- TVT 用 API は、呼出し側台帳を登録前に検査し、`copy.deepcopy(dict(rank_states_by_node_name))` で独立複製して fork World へ接続する。時刻 T の未確定 Visit は元台帳だけへ登録する。fork へ混ぜない。fork 側 mapping と Node 別台帳は元側と共有しない。
- 空の incoming snapshot では、実 World と TVT 順位適用 fork でも台帳を要求せず正常 return する。到着候補が 1 台以上あれば、Node 別台帳を要求する。
- 実 World は最新確定順位を使う。TVT 順位適用 fork は、凍結コピーの T-1 以前の確定順位を使う。過去確定群のあと、固定 snapshot の通常 baseline 群を処理する。通常 baseline 群にも order-control clearance を適用する。汎用 fork は台帳を読まず、従来の通常合流で、order-control clearance を適用しない。
- clearance は strict greater-than である。設定値 0 では、別 inlink は同一 timestep に通れず、最短で次の timestep である。設定値 1 では、次の timestep には通れず、最短で次の次の timestep であり、間の 1 timestep を空ける。
- 実進路は `route_next_link` である。formal route は強制しない。正常な TVT 通過候補で `route_next_link is None` なら `RuntimeError` である。一時スキップではない。
- 物理先頭、容量、入口空間不足は一時スキップである。clearance 未充足だけ、その時刻の後続を終える。
- collector は通過 1 回につき prepare と apply を 1 回行う。downstream boundary observer は直接呼ばない。actual passage と actual outcome は未実装である。
- テスト準備が、台帳の無い `junction_a` を実際に通過させていた。本番は緩めず、2 つのテスト fixture だけを直接配置へ修正した。helper は `_place_vehicle_on_inlink_with_new_order_control_visit` である。`vehicle_a` を進める間だけ `vehicle_b` を `x=0` へ退避し、その後 `x=180` へ戻した。Visit は `begin_order_control_visit_on_link_entry()` で作り、Visit ID は巻き戻していない。
- 専用物理通過テストは 34 件である。mode と登録前凍結コピーの関係テストは 34 件に含めない。
- 中核 7 ファイルは `253 passed in 19.69s` である。内訳は、物理通過 34、baseline collector 35、baseline driver 71、TVT baseline registration 35、fork alignment 25、TVT-MP driver 31、evaluation end 22 である。
- FCFS 関係は 73 件成功である。BATCH の残り単体は 293 件成功である。
- 正式サンプルは保存済み数値と一致した。completed trips は 735 / 810、average speed は 11.7 m/s、total travel time は 119475.0 s、average travel time は 162.6 s、average delay は 62.6 s、delay ratio は 0.385、total distance traveled は 1632250.0 m である。
- 変更・新規作成した本番とテスト 11 ファイルの `py_compile` は成功した。`git diff --check` も成功した。
- Terminal で、1 台移動、clearance、通常合流、終了処理、`Node.transfer`、TVT 物理通過、collector mode、`_prepare_baseline_fork`、登録前凍結コピーを直接確認した。完全実装前仕様と一致した。重大不整合と一時スキップは分離されている。
- 未解決失敗はない。仕様衝突はない。利用者判断が必要な事項はない。まだ Git 保存していない。

## 最新の再開地点

1. 第4巻と進捗第3巻の実装結果記録を Terminal で分割確認する。
2. 本番・テスト・文書の最終差分を確認する。
3. 関係回帰結果と変更ファイルを最終確認する。
4. 文書 2 ファイルを含む全実装対象を stage する。
5. `diagnostics/order_control.zip` は stage しない。
6. `git diff --cached --check` と `git diff --cached --stat` を確認する。
7. commit 名に document は必須ではない。今回は実装コミットである。
8. commit と push を分離する。
9. 保存後、actual passage・actual outcome の設計へ進む。

上記は 2026-09-29 時点の履歴である。2026-09-30 の診断結果は、本巻「TVT-MP単一decision timestep診断（2026-09-30）」と、詳細設計第4巻「TVT-MP単一decision timestep診断・通常ケースと境界ケースの比較（2026-09-30）」を参照する。trade_scope 全 Visit の観測と nonparticipating の予測・実績の最新仕様は、詳細設計第4巻「TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）」と、本巻末尾の最新再開地点を参照する。

## TVT-MP単一decision timestep診断（2026-09-30）

詳細は、詳細設計第4巻「TVT-MP単一decision timestep診断・通常ケースと境界ケースの比較（2026-09-30）」を参照する。本節は作業再開用の要約である。

- 診断ファイル `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` を作成済みである。2026-09-30 時点では Git 未追跡である。
- **診断ファイルの Git 状態（最新）**: 上記「2026-09-30 時点では Git 未追跡」は、診断作成直後の過去状態である。診断ファイル `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` は、その後コミット `f8d4529` に含めて保存済みである。同コミットはリモートブランチ `feature/intersection-order-control` へ push 済みである。最新の再開地点では、診断ファイルを未追跡ファイルとして扱わない。`diagnostics/order_control.zip` だけは、引き続き既存の未追跡ファイルであり stage しない。
- 診断作成時点では、本番コード・既存テスト・既存設計文書は変更していない。今回の文書反映で第4巻と進捗第3巻のみ更新する。
- Stage 1〜3 の全 assert は成功した。本物の `run_tvt_mp_driver` を入口から atomic apply まで確認した。
- **通常ケース（Stage 2）**: nonparticipating C は required 完了前に binding 通過した（offset 4 / vt 14）。これは一般保証ではない。
- **境界ケース（Stage 3）**: C は binding 未通過（出現回数 0、最終 skip `OUTLINK_ENTRY_SPACE_UNAVAILABLE`）。D・A・B の required 完了で resolved。economic feasible、selection、payment、final rank、validation、atomic apply まで成功。現行仕様どおりの正常終了である。
- Stage 2 と Stage 3 の保存済み処理件数比較（診断 §38）を完了した。Node・候補件数は同じでも、Stage 3 は total simulated step が +3、temporary skip が +22 多い。
- 利用者 Terminal で driver 壁時計を 5 回測定済み（Stage 2 平均 0.03266 秒、Stage 3 平均 0.05870 秒、平均比約 1.80）。別実行では比約 1.50。時間差を C 未通過だけへ帰属できない。
- 方式 A・B・C の追加負荷は未測定である。採否は未決定である。この2行は診断完了時点の過去記録である。方式 A・B・C は正式名称として採用しない。
- 次の作業: 方式 A・B・C を比較可能な形で定義し、追加計算部分だけを診断すること。stage 別 timing または World.copy 単体 timing の取得方法も未確定である。この次作業は、後続の完全実装前仕様によって置き換わった過去の再開項目である。

## 最新の再開地点（2026-09-30）

この再開地点は、診断完了直後の過去の再開地点である。当時は追加継続方式が未確定だった。選択候補だけの追加計算や、方式 A・B・C の定義は、ここで予定されていた未確定作業であり、第一実装の採用方針ではない。

1. 詳細設計第4巻「TVT-MP単一decision timestep診断・通常ケースと境界ケースの比較（2026-09-30）」を確認する。
2. 本巻「TVT-MP単一decision timestep診断（2026-09-30）」を確認する。
3. 診断スクリプト `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` を実行し、§38 の集計を再確認する（未追跡のままである）。
4. 方式 A・B・C の定義と、追加 virtual timestep・binding scan・World copy の見積もり方を設計する（本番実装はまだ行わない）。
5. `diagnostics/order_control.zip` は stage しない。
6. 文書 2 ファイルを commit する場合は `document` を commit 名に含める。
7. commit と push を分離する。

上記 3. の「未追跡のままである」は、診断完了直後の当時の再開項目である。診断ファイルの最新 Git 状態は、直前の「TVT-MP単一decision timestep診断（2026-09-30）」節の「診断ファイルの Git 状態（最新）」を参照する。

最新の採用方針と再開地点は、本巻末尾の「trade_scope全Visit観測の完全実装前仕様（2026-09-30）」を参照する。

## trade_scope全Visit観測の完全実装前仕様（2026-09-30）

詳細は、詳細設計第4巻「TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）」である。本節はその再開用要約である。本番実装はまだ行っていない。

- 直前の「方式 A・B・C の定義」と「選択候補だけの追加計算」は、診断完了時点の未確定な再開地点である。正式名称ではない。
- 再計算方式は第一実装では採用しない。選択候補の決定後に、decision timestep T から新しい local World を copy して選択候補だけをやり直す方式である。重複計算が生じるためである。
- selection 後の live state 再開方式も第一実装では採用しない。FIFO True 候補ごとの live World を selection まで保持すると、大規模実験でピーク RAM が増えるためである。
- 採用方針は、各 FIFO True candidate の最初の candidate local loop を、trade_scope 内の buyer・seller・nonparticipating 全員の candidate passage が観測されるか、既存 horizon 末尾まで、同じ local World と同じ state のまま続けることである。追加 World copy は作らない。
- economic required は buyer・seller の `required_passage_records` のままである。traffic observation は別 record である。`resolved` は buyer・seller 完了の意味のままである。`finished` は全員観測または horizon 末尾である。
- nonparticipating の予測価値は、`(baseline passage - candidate passage) × DELTAT × true VOT` である。正は短縮、負は遅延である。未観測なら金額は `None` である。支払・補償・選択には入れない。
- actual outcome は buyer・seller・nonparticipating 共通の frozen record とし、成立時 record とは別に `order_exchange_log` へ追加する。actual passage 基盤は未実装である。
- buyer・seller の事後評価は、同じ取引の buyer・seller の actual passage が揃った時点で始める。nonparticipating の actual passage は待たない。未観測でも正式支払・正式補償は変えない。
- Stage 2 では追加 timestep は無い。C が buyer・seller 完了前に通過しているか、nonparticipating がいないためである。
- Stage 3 では、buyer・seller 完了の offset 5 のあと、C が未通過なら offset 6 以降を同じ local World で続ける。C の candidate passage は未実行のため未確定である。

反証レビューと Terminal 独立確認（2026-09-30）の反映要約。詳細は詳細設計第4巻最新節を参照する。BLOCKER は無かった。

- IMPORTANT 1: economic evaluation は `resolved=True` ↔ `stop_reason=RESOLVED`、`resolved=False` ↔ `HORIZON_EXHAUSTED_UNRESOLVED` を要求する。buyer・seller 完了かつ nonparticipating だけ horizon 未観測でも `resolved=True`、`stop_reason=RESOLVED`、`unresolved_reasons=()` を維持する。nonparticipating 未観測は traffic observation の `UNOBSERVED_AT_HORIZON` で表す。
- IMPORTANT 2: traffic observation の true VOT は decision 時点の candidate local World 作成時に凍結する。result 作成時や actual 評価時に live `Vehicle.vot_true` を読み直さない。成立時 record の true VOT は現行どおり atomic apply で凍結する。
- IMPORTANT 3: actual passage observation、取引全体 ex-post evaluation、Vehicle 別 role 評価または外部効果を分離する。`WAITING_FOR_ACTUAL_PASSAGE` は frozen `order_exchange_log` record にしない。待ちは World 側 registry。
- offset 定義: `virtual_timestep = baseline_timestep_T + offset`（offset は 0 始まり）。Stage 3 例は第4巻 §4.1。
- Stage 3 offset 6 の正式診断は、本番終了条件を変更しないまま現行 one-timestep API では行えない。診断拡張単独は本番変更前の正式検証にならない（第4巻 §10.1）。
- candidate `("B","D")` について、C が nonparticipating であること以外、buyer・seller 完了 offset と offset 5 時点の C 状態は反証レビュー時点で未確認のまま残す。

## 最新の再開地点

診断ファイル `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` はコミット `f8d4529` に含めて保存済みであり、リモートブランチ `feature/intersection-order-control` へ push 済みである。本再開地点では、診断ファイルを未追跡ファイルとして扱わない。`diagnostics/order_control.zip` だけは、引き続き既存の未追跡ファイルであり stage しない。

反証レビューは完了済みである。本番実装はまだ行っていない。

1. 詳細設計第4巻「TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）」を確認する（反証レビュー反映後の最新版）。
2. 本巻「trade_scope全Visit観測の完全実装前仕様（2026-09-30）」を確認する。
3. 診断節は過去記録として残っていることを確認する。方式 A・B・C は正式名称ではない。
4. 過去の再開項目として「完全実装前仕様に対する反証レビューと、Stage 3 の offset 6 以降を見る診断拡張」は履歴に残す。反証レビューにより、Stage 3 offset 6 以降の診断拡張を本番終了条件実装なしで先行することは正式検証にならないと判明した。
5. 次作業は、完全実装前仕様の残る型・state 不変条件を詰め、本番終了条件実装と診断拡張を同一実装段階で行うための実装計画を作成する。
6. 本番実装はまだ行わない。
7. `diagnostics/order_control.zip` は stage しない。
8. 文書を commit する場合は commit 名に `document` を含める。実装前仕様を表すために `complete` は使わない。
9. commit と push を分離する。

上記「最新の再開地点」は、**trade_scope 全 Visit 観測の本番実装前**（2026-09-30 反証レビュー直後）の履歴である。削除しない。2026-10-01 完了分の最新参照先は、本巻末尾の「TVT-MP trade_scope全Visit観測 実装完了要約（2026-10-01）」と「最新の再開地点（2026-10-01）」、および詳細設計第4巻「TVT-MP trade_scope全Visit観測 実装・検証結果（2026-10-01）」である。

## TVT-MP trade_scope全Visit観測 実装完了要約（2026-10-01）

詳細は、詳細設計第4巻「TVT-MP trade_scope全Visit観測 実装・検証結果（2026-10-01）」を参照する。本節は再開用要約である。

### 保存済み実装コミット（push 済み）

- `c0b4484` — trade-scope traffic observation 型と初期化
- `93fbdc9` — passage 時刻・価値の record 提案
- `f9f0f4e` — required passage と trade-scope 観測の joint 記録、完了時刻
- `b0ba281` — 最終 temporary-skip と clearance scan-stop context
- `37c1ea6` — 観測完了・final result・Stage 3 offset 6 診断 assert

**最新コミットは `37c1ea6` で、リモートへ push 済みである。**

### 実装済み（candidate predicted）

- 各 FIFO True candidate の trade_scope 内 buyer・seller・nonparticipating の **candidate passage 観測**
- 予測時間差・凍結 true VOT による **予測符号付き価値**
- temporary skip 最終理由・clearance scan-stop context
- economic required 完了時刻と **trade_scope 全 Visit 完了時刻**
- horizon 未観測 `UNOBSERVED_AT_HORIZON`
- final result への **frozen** `traffic_observation_records` と完了 offset / vt
- 終了条件: buyer・seller 完了で `resolved`、trade_scope 全員観測（または horizon 末尾）で `finished`

### Stage 3（実測・診断 assert 済み）

- candidate `("D",)`: offset 5 で resolved・economic required 完了、**finished=False**（C 未通過）。offset 6 / vt 16 で C 通過、`final_offset=6`、trade_scope 完了。
- candidate `("B","D")`: `final_offset=6`、economic required と trade_scope 完了は **6/16**。C は offset 5 / vt 15 で `OBSERVED`。selected は **引き続き `("B","D")`**。
- **economic 以降（selection・payment・final rank・validation・atomic apply）は不変。**

### 検証（保存済み）

- 関連 8 テストファイル: **334 passed**
- Stage 2・Stage 3 診断: **exit 0**、`Stage 3 counterexample asserts: PASS`
- FCFS・BATCH: **366 passed**
- UXsim 正式サンプル: 保存済み数値と一致（completed trips 735/810、average speed 11.7 m/s 等。第4巻 §13.3）
- `py_compile` 成功、`git diff --check` 成功

### 未実装（actual 系）

- actual passage 基盤、World 側 registry、actual observation record、ex-post evaluation、Vehicle 別評価、nonparticipating actual 外部効果、評価終了時 actual 未観測確定、実験出力・集計

### 直前の再開地点との関係

- 本巻「trade_scope全Visit観測の完全実装前仕様（2026-09-30）」およびその直後の「最新の再開地点」にあった **「本番実装はまだ行わない」** は、当時の正式記録として **削除しない**。
- 上記コミット列により、**candidate predicted traffic observation と新終了条件は実装済み**である。過去の再開地点は、実装前・診断先行不可の **履歴** として残す。

## 最新の再開地点（2026-10-01）

**本節が、trade_scope 全 Visit candidate 観測実装後の最新再開地点である。** 2026-09-30 の「本番実装はまだ行わない」再開項目は履歴として残す（上節「直前の再開地点との関係」）。

診断ファイル `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` はコミット `37c1ea6` に含めて保存済みであり、リモートへ push 済みである。`diagnostics/order_control.zip` は **未追跡のまま stage しない**。

### 今回の作業（文書）

1. 詳細設計第4巻「TVT-MP trade_scope全Visit観測 実装・検証結果（2026-10-01）」と、本巻本節を **差分確認して保存**する。
2. **actual passage・World 側 registry へ直ちに本番実装へ進まない。**
3. 文書保存後の再開地点は、**actual passage 基盤の詳細実装前設計**（第4巻完全実装前仕様 §7・進捗第3巻 actual 未実装節）を確認することから始める。

### Git（文書のみ）

1. 文書 2 ファイル（本巻と第4巻）を stage する。`diagnostics/order_control.zip` は stage しない。
2. `git diff --cached --check` と `git diff --cached --stat` を確認する。
3. commit 名に **`document` を含める**。
4. **commit と push を分離**する。

# TVT-MP actual passage基盤 実装項目1完了要約（2026-10-02）

**詳細設計第4巻**「TVT-MP actual passage基盤 実装項目1の確定設計・実装・検証結果（2026-10-02）」を **正式参照先**とする。本節は再開用要約である。

- コミット **`4dc4862`** で実装項目1を実装し **push 済み**
- actual 用型、mutable registry、World 空 registry 初期化、専用テストを完了
- **3 組 9 field** の共通 passage 差分を確定（`baseline_minus_candidate_*`、`baseline_minus_actual_*`、`candidate_minus_actual_*`）
- fuzzy な prediction error 名称を避け、**引き算の向きを field 名で明示**
- role 別指標は共通 field から **後続評価層で導出**（observation record へ重複保存しない）
- 支払、補償、参考金額、事後成立判定は **`declared_vot_per_second`**
- 共通 time value は **`true_vot_per_second`**（研究・観測用）
- actual observation と role 別評価は **別層**
- 交通動作と既存 log は **未変更**

### 検証結果（保存済み）

- 専用テスト: **15 passed**
- TVT-MP 関連 9 ファイル: **349 passed**（334 + 15）
- FCFS・BATCH: **366 passed**
- candidate local calculation と atomic apply 限定回帰: **116 passed**（第4巻本節）
- `py_compile` 成功
- `git diff --check` 成功

### リポジトリ状態

- `diagnostics/order_control.zip` は **未追跡のまま stage しない**
- actual 系全体の残りは、現時点の基準で **実装項目 7 つ**、**仕上げ項目 2 つ**

### 直前の再開地点との関係

- 本巻「未実装（actual 系）」「actual passage 基盤へ直ちに本番実装へ進まない」（2026-10-01 再開地点）は **当時の記録として削除しない**
- candidate predicted は `e12a24c` / trade_scope 観測コミット列で完了済みの履歴として残す
- **最新の actual passage 基盤状態**は、本節および第4巻 2026-10-02 節で上書き参照する

## 最新の再開地点（2026-10-02）

**本節が、actual passage 基盤実装項目1完了後の最新再開地点である。**

- HEAD と `origin/feature/intersection-order-control` は **`4dc4862` で一致**
- **次は実装項目2:**「atomic apply 成功後の registry 一括登録」

### 実装開始前に読取り専用で確認する対象

- atomic apply の proposal、validation、**commit 境界**
- 成立時 log record
- selected candidate **traffic observation**
- buyer・seller の **true VOT 正本**
- nonparticipating の **true VOT 正本**
- apply 失敗時の **非反映契約**（registry へ何も残さない）

### 実装項目2の範囲制限

- 範囲を **atomic apply 登録だけ**に限定する
- Node.transfer、evaluation end、buyer・seller 完了通知、ex-post evaluation、Vehicle 別 role 評価、実験出力へ **接続しない**

### 作業運用

- Cursor には **Git 操作をさせない**
- **commit と push を分離**する
- 文書コミット名には **`document` を含める**
- `diagnostics/order_control.zip` を **stage しない**

2026-10-01 の「最新の再開地点」は trade_scope candidate 観測完了後の **履歴**として残す。actual passage の最新参照は **本節（2026-10-02）** と第4巻同日内節とする。

# TVT-MP actual passage基盤 実装項目2 完全実装前設計要約（2026-10-02）

**詳細設計第4巻**「TVT-MP actual passage基盤 実装項目2 完全実装前設計（2026-10-02）」を **正式参照先**とする。本節は実装前の再開用要約である。直前の「実装項目1完了要約」と「最新の再開地点（2026-10-02）」は、実装項目1完了時点の記録として残す。

- 実装項目1は `4dc4862`、文書更新は `2e31227` まで push 済み
- HEAD と origin は `2e31227` で一致
- 実装項目2は atomic apply 成功後の registry 一括登録
- proposal を全件 prepare し、commit 前に重複検査
- 完成済み replacement dict を prepare
- 既存 rank、money、log commit 後に registry を一括反映
- buyer・seller は成立時 record の検査済み true VOT
- nonparticipating は candidate observation の凍結 true VOT
- live true VOT を再読取しない
- candidate observation status: **buyer・seller は `OBSERVED` 必須**（`UNOBSERVED_AT_HORIZON` は prepare で拒否）、**nonparticipating は `OBSERVED` または `UNOBSERVED_AT_HORIZON`**（registry 全体として両 status を扱うが、全 role が両方を取り得る意味ではない）
- `buyers_sorted` を VisitKey tuple へ訂正
- apply 失敗時は registry を含む全状態不変
- 実装対象 4 ファイル（`order_control_tvt_mp_actual_passage.py`、`order_control_tvt_mp_atomic_apply.py`、両専用テスト）
- Node.transfer 以降へ接続しない
- Cursor 調査後、Terminal 原典確認を行い **BLOCKER なし**、利用者判断事項なしと判断した

## 最新の再開地点（2026-10-02・実装項目2設計確定後）

**本節が、実装項目2の完全実装前設計確定後の最新再開地点である。** 同日の実装項目1完了後の再開地点は履歴として残す。

- 次は第4巻の実装項目2完全実装前設計に基づくコード実装
- 実装範囲は atomic apply registry 登録だけ
- 変更予定 4 ファイルは上節のとおり
- Git 操作は利用者が Terminal で行う
- 実装後は専用テスト、atomic apply 回帰、TVT-MP 関連回帰、FCFS・BATCH 回帰、`py_compile`、`git diff --check` を順に確認
- `diagnostics/order_control.zip` を stage しない
- commit と push を分離する
- 実装結果は第4巻と進捗第3巻の双方へ追記する

# TVT-MP actual passage基盤 実装項目2 実装完了要約（2026-10-02）

詳細設計第4巻の同日実装結果節（「TVT-MP actual passage基盤 実装項目2 実装・検証結果（2026-10-02）」）を正式参照先として、次を記録する。

- atomic apply成功後のregistry一括登録を実装
- buyers_sortedをVisitKey tupleへ訂正
- buyer・seller・nonparticipating全件をproposal化
- buyer・sellerは成立時recordの検査済みtrue VOT
- nonparticipatingはcandidate observationの凍結true VOT
- buyer・sellerはOBSERVED必須
- nonparticipatingはOBSERVEDまたはUNOBSERVED_AT_HORIZON
- 全Node proposalをcommit前に重複検査
- replacement dictをprepare
- rank、money、log commit後にregistryを一括反映
- 失敗時はrank、money、log、registry、registry dict objectを変更しない
- Node.transfer以降へ未接続
- 検証:
  - 67 passed
  - TVT-MP既存関連354 passed
  - 合計421 passed
  - FCFS・BATCH 366 passed
  - py_compile成功
  - git diff --check成功
- 変更はコード・テスト4ファイル
- diagnostics/order_control.zipは未追跡のまま

## 最新の再開地点（2026-10-02・実装項目2完了後）

**本節が、実装項目2完了後の最新再開地点である。** 同日の実装項目2設計確定後の再開地点は履歴として残す。

- 実装項目2のコードは現在未コミット
- 検証と独立確認は完了
- 次にコード4ファイルをstage、確認、commit、pushする
- コード保存後、この実装結果文書を別のdocumentコミットとして保存する
- commitとpushを分離する
- diagnostics/order_control.zipをstageしない
- コード保存と文書保存が終わるまで実装項目3へ進まない

# TVT-MP actual passage基盤 実装項目3 完全実装前設計要約（2026-10-02）

正式参照先は、詳細設計第4巻の同日節「TVT-MP actual passage基盤 実装項目3 完全実装前設計（2026-10-02）」である。

- 実WorldのTVT物理通過成功をactual passageの正本とする
- prepareを物理移動前に行う
- 物理移動、clearance更新、prepared observation commitの順
- entryなしの確定Visitは正常に無視
- baseline forkではactual observationを行わない
- frozen recordをVehicle logとWaitEntryへ同一objectとして保存
- WaitEntryをOBSERVEDへ遷移し、entryは削除しない
- 3組9 field
- Candidate未観測nonparticipatingのcandidate系はNone
- buyer・seller完了通知以降は後続項目
- 変更予定4ファイル
- Terminal独立確認済み
- BLOCKERなし
- 利用者判断事項なし

## 最新の再開地点（2026-10-02・実装項目3設計確定後）

**本節が、実装項目3の完全実装前設計確定後の最新再開地点である。** 同日の実装項目2完了後の再開地点は履歴として残す。

- 次は第4巻の実装項目3完全実装前設計に基づくコード実装
- コード実装前設計は文書保存・push後に使用する
- 実装対象4ファイル
- Node.transfer、atomic apply、evaluation end、TradeWaitを変更しない
- 実装後は専用テスト、物理通過回帰、TVT-MP回帰、FCFS・BATCH回帰、py_compile、git diff --checkを確認
- Git操作は利用者がTerminalで行う
- commitとpushを分離する
- diagnostics/order_control.zipをstageしない
- 実装結果は第4巻と進捗第3巻の双方へ追記する

# TVT-MP actual passage基盤 実装項目3 実装完了要約（2026-10-02）

正式参照先は、詳細設計第4巻の同日節「TVT-MP actual passage基盤 実装項目3 実装・検証結果（2026-10-02）」である。

- 実WorldのTVT物理通過成功にactual passage observationを接続
- prepareは物理移動前
- 物理移動、clearance更新、commitの順
- entryなしの確定Visitは正常に無視
- baseline forkでは非実行
- frozen recordをVehicle logとWaitEntryへ同じobjectとして保存
- statusをACTUAL_PASSAGE_OBSERVEDへ変更
- entryはregistryへ残す
- 3組9 field
- candidate未観測nonparticipatingのcandidate系はNone
- TradeWaitと完了通知以降へ未接続
- 検証:
  - 69 passed
  - TVT-MP関連474 passed
  - FCFS・BATCH 366 passed
  - py_compile成功
  - git diff --check成功
- 変更はコード・テスト4ファイル
- diagnostics/order_control.zipは未追跡のまま

## 最新の再開地点（2026-10-02・実装項目3完了後）

**本節が、実装項目3完了後の最新再開地点である。** 同日の実装項目3設計確定後の再開地点は履歴として残す。

- 実装項目3のコードは現在未コミット
- 検証と独立確認は完了
- 次にコード4ファイルをstage、確認、commit、pushする
- コード保存後、この実装結果文書を別のdocumentコミットとして保存する
- commitとpushを分離する
- diagnostics/order_control.zipをstageしない
- コード保存と文書保存が終わるまで実装項目4へ進まない

## 文献ポジショニング第一段階の正式採用に関する参照注記（2026-10-02）

本節は詳細な文献採点メモではない。直前の「最新の再開地点（2026-10-02・実装項目3完了後）」を変更しない。本節の後に新しい実装側の最新再開地点は作らない。新しい実装フェーズまたは実装項目は設けない。

- 別系統の文献ポジショニング作業で、第一段階最終案が正式採用された。
- 第二段階へ進める状態になった。
- 第二段階の具体的作業はまだ未開始である。
- 第二段階で前提条件を収集し、第三段階で構造的前提依存性を比較する。
- 詳細参照先：
  - `ORDER_EXCHANGE_LITERATURE_FIRST_STAGE_SCORING_AND_POSITIONING.md`
  - `ORDER_EXCHANGE_LITERATURE_POSITIONING_FRAMEWORK.md`
  - `ORDER_EXCHANGE_PROGRESS.md` の2026-10-02文献節
- 直前の「最新の再開地点（2026-10-02・実装項目3完了後）」は、実装項目3のコード・文書保存前に記録された歴史的再開地点として残す。その後、実装項目3コードは `5d46781`（`implement and test TVT-MP actual passage observation after physical transfer`）で、実装項目3文書は `05d18df`（`document TVT-MP actual passage observation implementation and verification`）で、それぞれ保存・push済みとなった。現在のHEADと `origin/feature/intersection-order-control` は `05d18df` で一致している。したがって、実装項目3について追加のstage、commit、pushは不要である。
- 現在の実装側再開作業は、今回の文献文書4ファイルの保存・push完了後にactual系実装項目4へ進むことである。実装項目4の具体的仕様は本節では新たに決めない。
- 文献調査の再開地点と実装作業の再開地点を引き続き区別する。
- 本節の補足によって、直前の歴史的再開節を削除・置換・改変しない。
- actual系実装項目4は、今回の文献文書4ファイルの保存・push完了後に別チャットで再開予定である。
- 文献側の採用判断は、actual passage実装項目3の設計・実装結果を変更しない。
- 詳細設計第4巻への追記は不要である。
- 本節追加により、新しい実装フェーズまたは実装項目を設けない。

# TVT-MP正式候補のseller非空契約 訂正設計要約（2026-10-03）

正式参照先:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md`
  - 「TVT-MP正式候補のseller非空契約 訂正注記（2026-10-03）」
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
  - 「TVT-MP正式候補のseller非空契約 完全実装前訂正設計（2026-10-03）」

actual passage実装項目4の設計調査中に、過去の設計記録と一部テストがseller 0件のselected candidateを正常扱いしている誤りを発見した。

最新の正式契約:

- 正式TVT候補はbuyer 1件以上かつseller 1件以上
- 正式候補には実際の順位変換がある
- buyer 0件・seller 0件は順位変換がないため候補として生成しない
- buyer 1件以上・seller 0件も制度上あり得ず、正式候補として生成しない
- seller 1件以上で補償額が0となるケースは正常
- 補償額0でもseller roleとseller recordを維持する

正常な公開生成経路では、参加するright-of-entry Visitがbuyer候補から除外され、trade scope内の参加する非buyerとしてsellerになる。このため、正常な順位生成アルゴリズムはsellerを1件以上保証している。

発見した問題は、`OrderControlTvtMpGeneralTradeRankResult`のconstructorが、`sellers_sorted=()`を許容していることである。

本番コードの正本修正:

- `uxsim/order_control_tvt_mp_general_trade_rank.py`
- `OrderControlTvtMpGeneralTradeRankResult.__init__`
- `sellers_sorted`を非空必須にする
- 空の`sellers_sorted`を直接constructorへ渡した場合は`ValueError`

次は変更しない。

- 正常な順位生成アルゴリズム
- concrete buyer candidate set
- seller分類
- FIFO検査
- binding rank sequence
- economic evaluation式
- candidate selection基準
- payment・compensation式
- final rank
- final consistency validation
- atomic apply
- actual passage実装項目1〜3

economic evaluation以降へ、seller件数の同じ検査を重複追加しない。

テスト訂正:

- seller 0件を正常なselected candidateとして使うテストを削除または訂正
- general trade-rank constructorの空seller受理テストを`ValueError`拒否テストへ変更
- 他目的の正常fixtureにはsellerを1件以上追加
- 別の異常を検査するfixtureでもsellerを追加し、本来の例外理由を維持
- fallback、`NO_SELECTED_CANDIDATE`、`NO_VISITS_TO_CONFIRM`、空Nodeの空seller money列は維持
- seller economic recordが存在するのにcompensation recordだけが欠ける意図的な不一致fixtureは維持
- sellerが存在して補償額だけが0となるテストは維持

変更予定:

本番コード1ファイル:

- `uxsim/order_control_tvt_mp_general_trade_rank.py`

テスト8ファイル:

- `tests_order_control_tvt_mp_general_trade_rank.py`
- `tests_order_control_tvt_mp_local_binding_rank_sequence.py`
- `tests_order_control_tvt_mp_local_virtual_calculation_set.py`
- `tests_order_control_tvt_mp_economic_evaluation.py`
- `tests_order_control_tvt_mp_candidate_selection.py`
- `tests_order_control_tvt_mp_payment_and_compensation.py`
- `tests_order_control_tvt_mp_final_consistency_validation.py`
- `tests_order_control_tvt_mp_atomic_apply.py`

actual passage実装項目1〜3へのコード上の影響はない。

actual passage実装項目4では、次を前提にする。

- `TradeWait.buyer_visit_keys`は1件以上
- `TradeWait.seller_visit_keys`も1件以上
- seller VisitKeyが空のTradeWaitは正常な成立取引ではない

本訂正のコード、テスト、文書を保存・pushするまで、actual passage実装項目4は再開しない。

Terminal独立確認済み。

BLOCKERなし。
利用者判断事項なし。

## 最新の再開地点（2026-10-03・seller非空契約訂正設計確定後）

**本節が、seller非空契約の完全実装前訂正設計確定後の最新再開地点である。**

現在の状態:

- 詳細設計第3巻へ訂正注記を追記済み
- 詳細設計第4巻へ完全実装前訂正設計を追記済み
- 進捗第3巻への本要約を追記中
- Pythonコードとテストは未変更
- actual passage実装項目4は一時停止中

次の作業:

1. 文書3ファイルの差分をTerminalで独立確認する
2. 文書3ファイルだけをstageする
3. commit名に`document`を含めてcommitする
4. commit結果、最新コミット、残存変更を確認する
5. 別の指示でpushする
6. push後にHEADとoriginの一致を確認する
7. 第4巻の完全実装前訂正設計に基づき、本番コード1ファイルとテスト8ファイルを修正する

コード修正時の制約:

- `sellers_sorted`を非空必須にする本番修正だけを行う
- 後段本番部品へseller件数検査を重複追加しない
- 正常な順位生成アルゴリズムを変更しない
- FIFOの件数・index契約を変更しない
- candidateを間引かない
- 新しいstatusや除外理由fieldを追加しない
- actual passage実装項目1〜3を変更しない
- sellerが存在し補償額0となる正常契約を維持する

実装後に確認するもの:

- 変更対象の本番1ファイルとテスト8ファイル
- general trade rankからatomic applyまでのTVT-MP関連回帰
- actual passage実装項目1〜3の回帰
- FIFO回帰
- final rank回帰
- FCFS・BATCH回帰
- py_compile
- git diff --check

Git運用:

- Git操作は利用者がTerminalで行う
- CursorにGit操作をさせない
- commitとpushを分離する
- diagnostics/order_control.zipをstageしない

# TVT-MP正式候補のseller非空契約 実装・検証完了要約（2026-10-03）

正式参照先:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md`
  - 「TVT-MP正式候補のseller非空契約 訂正実装完了注記（2026-10-03）」

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
  - 「TVT-MP正式候補のseller非空契約 実装・検証結果（2026-10-03）」

## 正式契約

正式なTVT候補は、必ず次を満たす。

- buyer 1件以上
- seller 1件以上
- 実際の順位変換あり

次は正式候補として生成しない。

- buyer 0件・seller 0件
- buyer 1件以上・seller 0件

一方、sellerが1件以上存在し、補償額が0となることは正常である。

補償額0でも、seller role、seller economic record、seller compensation record、金額0の個別取引履歴を維持する。

## 本番実装結果

変更した本番コードは次の1ファイルだけである。

- `uxsim/order_control_tvt_mp_general_trade_rank.py`

対象:

- `OrderControlTvtMpGeneralTradeRankResult.__init__`

変更:

- `sellers_sorted`の`allow_empty=True`を`allow_empty=False`へ変更

これにより、seller 0件の正式general trade-rank resultを生成できなくした。

空の`sellers_sorted`を直接constructorへ渡した場合は`ValueError`となる。

## 重複検査を追加しなかった範囲

次の本番部品へseller件数検査を追加していない。

- FIFO inspection
- local binding rank sequence
- local virtual calculation
- economic evaluation
- candidate selection
- payment and compensation
- final rank
- final consistency validation
- atomic apply
- actual passage registry
- actual passage observation
- physical transfer

正式result生成時に保証済みの不変条件を、後段で重複検証しない方針を維持した。

## テスト訂正

次の8テストファイルを修正した。

- `tests_order_control_tvt_mp_general_trade_rank.py`
- `tests_order_control_tvt_mp_local_binding_rank_sequence.py`
- `tests_order_control_tvt_mp_local_virtual_calculation_set.py`
- `tests_order_control_tvt_mp_economic_evaluation.py`
- `tests_order_control_tvt_mp_candidate_selection.py`
- `tests_order_control_tvt_mp_payment_and_compensation.py`
- `tests_order_control_tvt_mp_final_consistency_validation.py`
- `tests_order_control_tvt_mp_atomic_apply.py`

主な訂正:

- 空seller constructor受理テストを`ValueError`拒否テストへ変更
- 正常fixtureをbuyer 1件以上・seller 1件以上へ変更
- seller 0件のselected candidateを正常扱いするテストを削除
- 別の異常を検査するfixtureへsellerを追加
- seller件数比較を0件対2件から1件対2件へ変更
- atomic applyのseller VisitKeyを保存済みseller economic recordから取得
- 複数selected Nodeのfixtureにもsellerを追加

削除した誤った正常テスト:

- `test_zero_sellers_gives_zero_payments`
- `test_branch1_zero_sellers_is_normal`
- `test_zero_sellers_writes_only_the_buyer_row`

## 維持した正常ケース

sellerが存在し、次が0となる正常ケースは維持した。

- required compensation
- compensation amount
- `total_required_compensation_R`
- buyer payment

次のテストも維持した。

- `test_r_equals_zero_gives_zero_payments`
- `test_zero_payment_and_zero_compensation_still_write_rows`

fallback、候補なし、`NO_VISITS_TO_CONFIRM`、空Node、意図的な破損入力の空seller列も維持した。

正常なselected candidateとしてseller 0件を使用するfixtureは除去済みである。

## 本番順位生成の再監査

atomic applyのfixture訂正中に、本番general trade-rankを再監査した。

確認した契約:

- trade scopeはbaseline順位の先頭から最後のbuyerまで
- buyer、seller、nonparticipatingがtrade scopeを分割
- nonparticipatingはbaseline順位を維持
- sellerはbaseline順位より後退
- trade scope外Visitはbaseline順位を維持
- buyerは固定順位を除いた先頭側の空き順位へ配置
- sellerは残りの空き順位へ配置

本番順位交換アルゴリズムの欠陥は確認されなかった。

## 検証結果

- 最終状態のTVT-MP統合回帰13ファイル: 624 passed
- FCFSコア回帰: 24 passed
- BATCHコア回帰: 360 passed
- 重複しない最終確認対象: 合計1,008 passed
- 変更対象9ファイルの`py_compile`: 成功
- `git diff --check`: 成功

TVT-MP候補外FCFS transferの18件は、624件のTVT-MP統合回帰に含まれる。

UXsim正式サンプルは、今回の小規模なresult constructor契約訂正では再実行していない。

## actual passageへの影響

actual passage実装項目1〜3の本番コードは変更していない。

関連回帰は成功した。

actual passage実装項目4では、次を前提とする。

- `TradeWait.buyer_visit_keys`は1件以上
- `TradeWait.seller_visit_keys`も1件以上
- seller VisitKeyが空のTradeWaitは正常な成立取引ではない

BLOCKERはない。
利用者判断事項も残っていない。

## 最新の再開地点（2026-10-03・seller非空契約実装検証完了後）

**本節が、seller非空契約の実装・検証完了後の最新再開地点である。**

現在の状態:

- seller非空契約の本番コード修正済み
- テストfixture訂正済み
- TVT-MP統合回帰624件成功
- FCFSコア24件成功
- BATCHコア360件成功
- 重複しない合計1,008件成功
- py_compile成功
- git diff --check成功
- 詳細設計第3巻へ実装完了注記を追記済み
- 詳細設計第4巻へ実装・検証結果を追記済み
- actual passage実装項目4はまだ再開していない

次の作業:

1. 文書3ファイル、コード1ファイル、テスト8ファイルの差分をTerminalで独立確認する
2. 変更12ファイルだけをstageする
3. `diagnostics/order_control.zip`をstageしない
4. 実装と文書を同一保存単位でcommitする
5. commit結果、最新コミット、残存変更を確認する
6. 別の指示でpushする
7. push後にHEADとoriginの一致を確認する
8. 新しい作業としてactual passage実装項目4へ戻る

保存対象:

文書3ファイル:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_3.md`
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
- `ORDER_EXCHANGE_PROGRESS_3.md`

本番コード1ファイル:

- `uxsim/order_control_tvt_mp_general_trade_rank.py`

テスト8ファイル:

- `tests_order_control_tvt_mp_general_trade_rank.py`
- `tests_order_control_tvt_mp_local_binding_rank_sequence.py`
- `tests_order_control_tvt_mp_local_virtual_calculation_set.py`
- `tests_order_control_tvt_mp_economic_evaluation.py`
- `tests_order_control_tvt_mp_candidate_selection.py`
- `tests_order_control_tvt_mp_payment_and_compensation.py`
- `tests_order_control_tvt_mp_final_consistency_validation.py`
- `tests_order_control_tvt_mp_atomic_apply.py`

Git運用:

- Git操作は利用者がTerminalで行う
- CursorにGit操作をさせない
- commitとpushを分離する
- commit名に`document`を含める
- `diagnostics/order_control.zip`をstageしない

## 文献ポジショニング第二段階の比較方法と記録様式に関する参照注記（2026-10-03）

本節は詳細な文献台帳ではない。直前の「最新の再開地点（2026-10-03・seller非空契約実装検証完了後）」を変更しない。本節の後に新しい実装側の最新再開地点は作らない。新しい実装フェーズまたは実装項目は設けない。actual passage実装項目4の内容を変更しない。

- 別系統の文献ポジショニング作業で、第二段階の比較方法と記録様式を具体化した。
- 第一段階採点は変更していない。
- 新しい原論文事実は追加認定していない。
- 第二段階の具体的な論文比較、全文確認、書誌固定、台帳記入は未開始である。
- 文献調査の次作業は、必要な原論文、全文資料、書誌、出典箇所の固定と、Lin・Jabari系列への台帳初回適用である。
- 詳細参照先：
  - `ORDER_EXCHANGE_LITERATURE_FIRST_STAGE_SCORING_AND_POSITIONING.md` の§20
  - `ORDER_EXCHANGE_LITERATURE_POSITIONING_FRAMEWORK.md` の§5B
- 直前の「最新の再開地点（2026-10-03・seller非空契約実装検証完了後）」は、実装側の最新再開地点として残す。
- 文献調査の再開地点と実装作業の再開地点を引き続き区別する。
- 本節の補足によって、直前の実装側再開節を削除・置換・改変しない。
- 文献側の様式具体化は、seller非空契約の実装結果およびactual passage実装項目4の設計を変更しない。
- 詳細設計第3巻・第4巻への追記は不要である。
- 本節追加により、新しい実装フェーズまたは実装項目を設けない。

# TVT-MP actual passage基盤 実装項目4 完全実装前設計要約（2026-10-03）

正式参照先:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
- 「TVT-MP actual passage基盤 実装項目4 完全実装前設計（2026-10-03）」

## 目的

取引に参加したbuyerとsellerが全員、実際に交差点を通過した時点を検出する。

全員がそろった最初の1回だけ、その取引を
「事後評価を開始できる状態」
として通知する。

nonparticipatingの通過完了は待たない。

今回は通知境界までを実装し、buyer・sellerの役割別事後評価、nonparticipatingの外部効果評価、集計、実験出力は後続項目へ残す。

## 完了条件

正式取引は必ず次を満たす。

- buyer 1件以上
- seller 1件以上

空buyer集合または空seller集合を自動完了として扱わない。

buyer_visit_keysとseller_visit_keysに含まれる全Visitについて、個別actual passage observationがcommit済みであることを完了条件とする。

各対象Visitでは、次がそろっていることを要求する。

- actual passage観測済み状態
- actual passage observation record

今回通過するVisitは、今回のcommit後に観測済みになるものとして判定する。

nonparticipating_visit_keysは完了条件に含めない。

## 通知の意味

完了通知は、

「buyerとsellerのactual passageが全てそろい、後続の事後評価を開始できる状態になった」

ことを示す。

この実装項目では事後評価計算自体を開始しない。

初回完了時だけTradeWaitを後続接続可能な結果として返す。

次の場合は通知しない。

- buyerまたはsellerに未通過Visitが残る
- 同一取引について既に通知済み

nonparticipatingだけが未通過であっても、buyer・sellerが全員完了し、まだ通知されていなければ、初回完了通知を返す。

nonparticipatingが後から通過しても再通知しない。

## 処理の骨格

1. 個別actual passage observationをprepareする
2. 該当TradeWaitとbuyer・seller entryを確認する
3. 今回の通過を反映すればbuyer・seller全員が完了するか判定する
4. 車両の物理移動が成功する
5. 個別actual passage observationをcommitする
6. 初回完了の場合だけcompletion flagをTrueにする
7. 初回完了したTradeWaitを返す
8. 未完了または通知済みの場合は完了通知を返さない

重大な不整合を物理移動後に初めて発見しないよう、完了判定に必要な確認は物理移動前に行う。

prepare段階では、liveなVehicle log、WaitEntry、TradeWaitを変更しない。

物理移動が失敗またはskipされた場合は、個別観測も完了通知も反映しない。

## 既存基盤

OrderControlTvtMpActualPassageTradeWaitには既に次がある。

- buyer_visit_keys
- seller_visit_keys
- nonparticipating_visit_keys
- buyer_seller_actual_passage_completion_notified

取引は次の保存情報から特定する。

- tvt_decision_timestep
- node_name
- buyers_sorted

新しい逆引きregistryは追加しない。

## 重複通知防止

buyer_seller_actual_passage_completion_notifiedがFalseであり、今回初めてbuyer・seller全員完了となる場合だけ、Trueへ更新する。

既にTrueの場合は再通知しない。

同一取引のnonparticipatingが後から通過しても再通知しない。

## 破損入力

少なくとも次を正常状態として扱わない。

- transaction keyに対応するTradeWaitがない
- TradeWaitとWaitEntryの取引identityが一致しない
- buyer_visit_keysが空
- seller_visit_keysが空
- buyerまたはsellerのWaitEntryがない
- roleとrole別VisitKey列が一致しない
- 同じVisitKeyが複数roleへ重複している
- 観測済み状態なのにrecordがない
- 未観測状態なのにrecordが存在する
- completion flagがTrueなのにbuyer・seller全員完了ではない

登録時に保証済みの不変条件を無制限に重複検証せず、今回の通知処理に必要な重大不整合だけを確認する。

## 変更予定ファイル

本番:

- `uxsim/order_control_tvt_mp_actual_passage.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`

テスト:

- `tests_order_control_tvt_mp_actual_passage.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

変更しない予定:

- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_atomic_apply.py`
- economic evaluation
- candidate selection
- payment and compensation
- final rank
- final consistency validation
- seller非空契約
- diagnostics

## テスト方針

正常ケース:

- buyer 1件・seller 1件
- buyer複数・seller 1件
- buyer 1件・seller複数
- buyer複数・seller複数
- buyerが最後に通過
- sellerが最後に通過
- nonparticipatingが未通過でも通知
- nonparticipatingが先に通過済み
- 通知済み取引でnonparticipatingが後から通過
- 最後の1台より前は通知しない
- 初回通知時だけflagがTrue
- 個別recordとcompletion flagを同じ成功commitで反映

異常ケース:

- 空buyer
- 空seller
- TradeWait欠落
- WaitEntry欠落
- role不一致
- transaction identity不一致
- 状態とrecordの不一致
- flagの不整合
- VisitKey重複
- prepare失敗時のlive state不変

既存の空buyerまたは空seller fixtureは、正常取引ではなく型単体または破損入力であることを明確にする。

## 検証計画

- actual passage専用テスト
- physical transfer専用テスト
- atomic apply回帰
- final consistency validation回帰
- final rank回帰
- FIFO回帰
- TVT-MP関連回帰
- FCFS・BATCHコア回帰
- py_compile
- git diff --check

UXsim正式サンプルは、実装規模と回帰結果を確認後に再実行要否を判断する。

BLOCKERなし。
利用者判断事項なし。

## 最新の再開地点（2026-10-03・actual passage実装項目4設計確定後）

**本節が、actual passage実装項目4のコード実装前における最新再開地点である。**

現在の状態:

- 文献調査第二段階のメモ化はコミット`5492e19`で保存・push済み
- actual passage実装項目1〜3は実装・検証・保存済み
- seller非空契約はコミット`c03ae41`で実装・検証・保存済み
- 実装項目4の完全実装前設計を詳細設計第4巻へ追記済み
- Pythonコードとテストは未変更
- 実装項目4の事後評価計算はまだ開始しない
- BLOCKERなし
- 利用者判断事項なし

次の作業:

1. 詳細設計第4巻と進捗第3巻の差分をTerminalで独立確認する
2. 文書2ファイルだけをstageする
3. commit名に`document`を含めてcommitする
4. commit結果、最新コミット、残存変更を確認する
5. 別指示でpushする
6. push後にHEADとoriginの一致を確認する
7. 完全実装前設計に基づき、実装項目4のコードと専用テストを実装する

Git運用:

- Git操作は利用者がTerminalで行う
- CursorにGit操作をさせない
- commitとpushを分離する
- `diagnostics/order_control.zip`をstageしない

実装開始時の予定変更ファイル:

- `uxsim/order_control_tvt_mp_actual_passage.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`
- `tests_order_control_tvt_mp_actual_passage.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

実装開始時も、役割別事後評価、evaluation end、未観測確定、実験出力へ範囲を広げない。

# TVT-MP buyer・seller actual passage初回通知 実装・検証完了要約（2026-10-03）

正式参照先:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
- 「TVT-MP buyer・seller actual passage初回通知 実装・検証結果（2026-10-03）」

## 完了したこと

取引に参加したbuyerとsellerが全員、実際に交差点を通過したことを検出し、全員がそろった最初の1回だけ、その取引を

「事後評価を開始できる状態」

として通知する仕組みを実装した。

nonparticipatingの通過完了は待たない。

buyer・seller全員がそろう前には通知しない。

一度通知した取引は、nonparticipatingが後から通過しても再通知しない。

今回完成したのは通知境界までである。

buyer・sellerの役割別事後評価、nonparticipatingの外部効果評価、集計、実験出力はまだ開始していない。

## 本番変更

変更した本番コードは次の1ファイルだけである。

- `uxsim/order_control_tvt_mp_actual_passage.py`

次の本番コードは変更していない。

- `uxsim/order_control_tvt_mp_physical_transfer.py`
- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_atomic_apply.py`
- economic evaluation
- candidate selection
- payment and compensation
- final rank
- final consistency validation
- seller非空契約

physical transfer本番コードは、車両の物理移動成功後に既存のactual passage commitを呼んでいるため、新たな接続変更を必要としなかった。

## 初回通知条件

次をすべて満たした場合だけ、初回通知を行う。

- buyer全員のactual passageが観測済み
- seller全員のactual passageが観測済み
- 各buyer・seller Visitにactual passage observation recordが存在
- `buyer_seller_actual_passage_completion_notified`がFalse

commit時に次を同じ成功処理で反映する。

- Vehicle logへのactual observation追加
- WaitEntryへの同じrecord objectの保存
- WaitEntryの観測済み状態への更新
- TradeWaitの通知済みflag更新

初回通知時だけ対象TradeWaitを返す。

次の場合は通知を返さない。

- buyerまたはsellerに未通過Visitが残る
- 既に通知済み
- 今回の通過によって初回通知条件が成立しない

事後評価計算は実行しない。

## nonparticipatingの扱い

nonparticipatingはbuyer・seller全員通過の判定に含めない。

buyer・sellerが全員通過済みであれば、nonparticipatingが未通過でも初回通知する。

通知済み取引でnonparticipatingが後から通過しても再通知しない。

buyer・sellerが全員通過済みなのに通知済みflagがFalseの破損状態を、nonparticipatingの通過によって暗黙修復しない。

## 通知済み状態の整合

通知済みflagがTrueの場合、今回の通過前からbuyer・seller全員が観測済みであることを要求する。

flagがTrueなのにbuyerまたはsellerに未通過Visitが残る場合は、破損状態として拒否する。

今回の通過後なら全員がそろう場合でも、通過前からflagがTrueであることを正常扱いしない。

## 正式TradeWaitの整合

正常なTradeWaitでは、次を必須とする。

- buyer Visitが1件以上
- seller Visitが1件以上
- buyer、seller、nonparticipatingの各role列に重複がない
- role列間にVisitKeyの重複がない
- role別VisitKeyが全て`all_visit_keys`に存在する
- `all_visit_keys`の全Visitが、いずれか1つのroleに分類されている

空buyer集合または空seller集合を、自動的な全員通過として扱わない。

nonparticipatingはrole列の整合対象だが、buyer・seller全員通過の判定には含めない。

## 原子性

prepare段階では、次を変更しない。

- Vehicle log
- WaitEntry
- TradeWait
- 通知済みflag
- registry内部dict

prepareで重大な不整合が見つかった場合は、物理移動前に停止する。

物理移動成功後のcommitで、個別actual passage記録と初回通知状態をまとめて反映する。

skip、容量不足、入口空間不足、clearance停止、prepare失敗では、個別actual passageも通知済みflagも更新しない。

## 維持した既存契約

次は変更していない。

- actual passage observation record
- 3組9 field
- baseline minus candidateの保存済み値
- baseline minus actualの計算
- candidate minus actualの計算
- true VOTの保存値利用
- actual passage timestep
- actual route
- Vehicle log
- WaitEntryへの同一record object保存
- WaitEntryの状態遷移
- 二重観測拒否
- 正式支払額
- 正式補償額
- physical transferの戻り値契約
- Node.transferの処理契約

## テスト変更

変更したテストは次の2ファイルである。

- `tests_order_control_tvt_mp_actual_passage.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

正常なテスト取引を、buyerとsellerが各1件以上存在する正式TradeWaitへ変更した。

物理通過テストでも、WaitEntryだけでなく、対応するbuyer・seller・必要なnonparticipatingとTradeWaitを登録するようにした。

既存の実通過時刻、経路、3組9 field、true VOT、二重観測拒否、clearance、entryなし正常通過の検査は維持した。

## 主な正常系確認

- buyer 1件・seller 1件
- buyer先行では通知しない
- seller先行では通知しない
- buyerが最後に通過したとき初回通知
- sellerが最後に通過したとき初回通知
- buyer複数
- seller複数
- buyer・seller双方が複数
- 全員がそろうまで通知しない
- nonparticipatingが未通過でも通知
- nonparticipatingが先に通過済みでも通知条件は変わらない
- 通知後のnonparticipating通過で再通知しない
- prepare段階のlive state不変
- 個別actual recordと通知済みflagを同じ成功commitで反映
- baseline forkではactual passageもflagも変更しない
- skip、容量不足、clearance停止ではactual passageもflagも変更しない

## 主な異常系確認

- TradeWait欠落
- 空buyer列
- 空seller列
- buyerまたはsellerのWaitEntry欠落
- role不一致
- role列内重複
- role列間重複
- `all_visit_keys`重複
- role列と`all_visit_keys`の不一致
- role未分類VisitKey
- transaction identity不一致
- 観測済み状態なのにrecordなし
- 待機状態なのにrecordあり
- flagがTrueなのにbuyerまたはseller未通過
- buyer・seller全員観測済みなのにflagがFalseのままnonparticipatingが通過
- prepare失敗時のlive state不変

## 検証結果

actual passageとphysical transferの専用テスト:

- 107 passed

最終状態のTVT-MP統合回帰13ファイル:

- 662 passed

FCFS・BATCHコア回帰:

- 384 passed

重複しない最終確認対象の合計:

- 1,046 passed

その他:

- 変更対象3ファイルの`py_compile`成功
- `git diff --check`成功
- UXsim正式サンプルは今回再実行していない

## 今回実装しなかったもの

- buyerのactual時間短縮評価
- sellerのactual遅延評価
- nonparticipatingのactual外部効果評価
- ex-post効用計算
- 正式支払額または正式補償額の再計算
- evaluation end
- 未観測確定
- 実験出力
- 集計
- グラフ
- 初回通知されたTradeWaitの後続評価への接続

BLOCKERなし。

利用者判断事項なし。

## 最新の再開地点（2026-10-03・buyer・seller actual passage初回通知実装検証後）

**本節が、buyer・seller actual passage初回通知の実装・検証後における最新再開地点である。**

現在の状態:

- branchは`feature/intersection-order-control`
- 実装開始時の基点はコミット`54c396d`
- buyer・seller actual passage初回通知を実装済み
- actual passage専用・物理通過専用テスト107件成功
- TVT-MP統合回帰662件成功
- FCFS・BATCHコア回帰384件成功
- 重複しない合計1,046件成功
- 変更対象3ファイルのpy_compile成功
- git diff --check成功
- 詳細設計第4巻へ実装・検証結果を追記済み
- 本番physical transferコードは変更していない
- 事後評価計算は未着手
- BLOCKERなし
- 利用者判断事項なし

保存対象:

文書2ファイル:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
- `ORDER_EXCHANGE_PROGRESS_3.md`

本番コード1ファイル:

- `uxsim/order_control_tvt_mp_actual_passage.py`

テスト2ファイル:

- `tests_order_control_tvt_mp_actual_passage.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

次の作業:

1. 文書2ファイル、コード1ファイル、テスト2ファイルの差分をTerminalで独立確認する
2. 保存対象5ファイルだけをstageする
3. `diagnostics/order_control.zip`をstageしない
4. 実装、テスト、文書を同一保存単位でcommitする
5. commit名に`document`を含める
6. commit結果、最新コミット、残存変更を確認する
7. 別指示でpushする
8. push後にHEADとoriginの一致を確認する
9. 後続の事後評価設計へ進む前に、その正式範囲と依存関係を確認する

Git運用:

- Git操作は利用者がTerminalで行う
- CursorにGit操作をさせない
- commitとpushを分離する
- `diagnostics/order_control.zip`を変更、展開、削除、stageしない

## TVT-MP全role一括実績評価・順位分析・集計の完全実装前全体設計を確定（2026-10-04）

正式な技術詳細の参照先:

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md`
- 「TVT-MP 全role一括実績評価・順位分析・集計 完全実装前全体設計（2026-10-04）」

本節は進捗記録である。詳細設計第4巻末尾の新節（約615行）をそのまま複製しない。進捗第3巻だけを読んでも、現在地、主要方針、未実装範囲、次の再開手順を誤らない程度の具体性を残す。

今回の作業は文書追記のみである。コード、テスト、診断は変更していない。

### 1. 現在地

- actual passage実装項目1から4は実装・検証・文書化・保存済みである。
- buyer・seller全員のactual passageがそろった最初の1回だけ通知する仕組みまで実装済みである。
- 事後評価計算、評価終了時未観測確定、実通過順位、集計、実験出力は未実装である。
- 今回はコードやテストを変更せず、後続実装全体の設計を詳細設計第4巻へ記録した。
- 旧来の項目5、6、7、8という分割は、今後の正式実装単位としてまだ確定していない。

### 2. 全role一括実績評価方式

- buyer、seller、nonparticipatingのactual passageを評価期間中に収集する。
- 評価終了時に未観測を確定した後、全roleを同じ最終評価工程で扱う。
- roleごとに評価時点を変えるのではなく、追加評価項目だけを変える。
- buyer・sellerには金銭、参考金額、実績利得、満足理由分類を追加する。
- nonparticipatingは全role共通のactual observationから実績評価する。
- 候補選択、正式支払、正式補償、selected candidate、final rankをやり直さない。

### 3. buyer・seller初回通知

- 実装済み通知は維持する。削除、無効化、コメントアウトをしない。
- buyer・seller全員が観測済みとなり、参考支払額・参考補償額を計算可能になったことを示す目印である。
- nonparticipatingを待たずに通知する既存契約は維持する。
- 通知は最終実績評価を直ちに開始する命令ではない。
- 現在使用されていないTradeWait戻り値を、即時評価へ接続しない。
- 最終評価は評価終了時に一括して行う。

### 4. 保存結果の三層構造

次の三層を区別する。

1. 全role共通のactual passage observation record
2. buyer・seller個別追加評価record
3. 取引全体評価record

次も記録する。

- 現在のactual passage observation recordを観測事実の正本とする。
- baseline、candidate、actualの通過時刻と3組9 fieldを維持する。
- 未観測を0にしない。
- 成立時recordを変更しない。
- buyer・seller個別追加評価には、取引別の正式金額、参考金額、実績利得、満足理由分類を扱う。
- 取引全体評価には、事後成立・事後不成立・未観測による評価不能、参考金額、不成立理由を扱う。
- 正式な型名、field名、保存場所、APIは未確定である。

### 5. nonparticipating

- nonparticipating専用のrole固有追加recordは原則として作らない。
- nonparticipating取引別実績利得は、共通recordのbaseline_minus_actual_time_valueである。
- 正はbaselineより早い、0は同時刻、負はbaselineより遅い。
- 未観測なら実績利得を計算しない。
- 支払、補償、参考金額、事後成立判定には含めない。
- nonparticipating Vehicleは走行中一貫してnonparticipatingである。
- 参加Vehicleは取引ごとにbuyerまたはsellerになり得るが、走行中にnonparticipatingへ変更しない。

### 6. buyer・sellerの実績利得と満足理由分類

buyer取引別実績利得:

```
= true VOTによる実績時間節約価値
  - その取引の正式支払額
```

seller取引別実績利得:

```
= その取引の正式補償額
  - true VOTによる実績遅延損失
```

満足理由分類（確定名称）:

buyer:

- 実績時間節約が0以下 → 自明な不満足（割り算しない）
- 実績時間節約が正で、1秒当たり正式支払額がtrue VOT超過 → 価格面から不満足
- 実績時間節約が正で、1秒当たり正式支払額がtrue VOT以下 → 価格面でも満足

seller:

- 実績遅延が0以下 → 自明な満足（割り算しない）
- 実績遅延が正で、1秒当たり正式補償額がtrue VOT未満 → 補償面でも不満足
- 実績遅延が正で、1秒当たり正式補償額がtrue VOT以上 → 補償面から満足

最終判定:

- 実績利得0以上は満足、0未満は不満足（0は満足）
- 割り算は理由分類に使う。分母が0以下なら割り算しない

### 7. 取引全体の事後評価

- buyer・seller全員が観測済みの場合だけ評価可能である。
- buyerが1人でも実績節約価値0以下なら事後不成立である（条件は0未満ではなく0以下）。
- buyer全体の実績節約価値がseller全体の実績要求補償総額未満なら事後不成立である。
- 事後不成立なら参考支払・参考補償を全員0とする。正式支払・正式補償は変更しない。
- buyerまたはsellerに未観測がある場合は、事後不成立ではなく評価不能である。
- 評価不能の場合は、参考金額、実績利得、満足分類を計算しない。

### 8. 予測と実績の比較母集団

- baseline、candidate、actualの三つを区別する。
- 時刻差・時間価値差は、actualと比較対象の予測の双方が観測済みのVisitだけで比較する。
- 未観測を誤差0または最大誤差として混ぜない。
- 未観測は、対象数、観測済み数、未観測数、観測率として別に評価する。
- candidateでは観測済みだがactualでは未観測だった件数も集計候補である。
- 一般の通過時刻予測では完全一致率を中心指標にしない。
- 許容誤差を現時点で恣意的に定めない。
- 符号付き差、絶対差、平均、中央値、分位点、分布を用いる方向である。

### 9. Node連続順位と実績順位評価

- 順位評価の正本は、対象Nodeのorder-control対象Visitを順位台帳へ順次接続したNode別の連続順位である。
- buyer、seller、nonparticipatingを交通上同じ連続順位列で扱う。trade_scope内、candidate内局所順位だけ、registry登録Visitだけへ母集団を縮小しない。
- baseline_local_rank、post_trade_local_rank、ledger_assigned_rank、rank_changeの既存定義（候補内局所順位の予定順位変化）は変更しない。
- rank_change = baseline_local_rank - post_trade_local_rank（正は前進、0は不変、負は後退）。これは予定順位変化であり、Node連続順位上の実績順位変化とは別である。
- 実績順位変化は、Node別割当順位とNode別実通過順位を同じNode連続順位母集団で比較する（概念式: 割当順位 − 実通過順位。正は前進、0は一致、負は後退）。
- Node連続順位上で、先行Visitの追越し・後続Visitからの被追越し、何位前進・後退したか、割当どおり通過したかを評価する。
- 実通過順位は現在未保存である。同一timestep内の複数通過のため、通過成功時にNode別実通過順序の情報を残す必要がある（正式な保存方法は未確定）。
- 未観測VisitにはNode別実通過順位を推定しない。取引内で1位から順位を付け直す仕組みは作らない。
- 取引別集計では、取引関係のbuyer・seller・nonparticipatingについて、Node連続順位上の実績順位変化を抽出する。
- nonparticipatingについて、Node連続順位上の順位完全一致率、符号付き・絶対順位変化、前進・不変・後退割合を集計候補とする。

### 10. 進路

- 「candidate予測進路」という曖昧な一括名称を使わない。
- trade_scope内Visitでは、局所仮想計算で使用した保存済み進路、その進路の由来、実進路を区別する。
- 既存の進路由来は、RANK_LEDGER_FORMAL_ROUTE、SNAPSHOT_ROUTE_ALREADY_DECIDED、BASELINE_TARGET_NODE_ARRIVAL_ROUTEである。
- 後方unbound Vehicleには、SNAPSHOT_FIXED_ROUTE、BASELINE_ARRIVAL_ROUTE、DETERMINISTIC_VIRTUAL_ROUTEがある。
- 後方unbound Vehicleの仮想進路情報は局所計算の診断情報であり、採用取引の個別実績評価へ混ぜない。

### 11. Vehicle・OD旅行単位の到着順位

- TVTあり・なしで、Vehicle名、OD、設定上の出発時刻、出発順位、random seed、ネットワーク、変更対象以外のVehicle条件を固定する。
- VOTまたは参加状態による経由ルート、通過Node、混雑、到着時刻の変化は制度効果として許容する。
- 同一出発timestepは同着出発順位とする。
- 同一到着timestepは同着到着順位とする。
- Vehicle IDで同着間の順位差を作らない。Vehicle IDは安定表示順にだけ使用する。
- 未到着・trip abortには到着順位を推定しない。

中心指標:

```
TVTによる到着順位効果
= TVTなしの到着順位
  - TVTありの到着順位
```

- 正はTVTありで到着順位が早い、0は変化なし、負はTVTありで到着順位が遅い。
- 出発順位から到着順位への変化単独は、OD距離等の影響が強いため中心指標にしない。

### 12. Vehicle別・集合別評価

参加Vehicle:

```
Vehicle別総実績利得
= buyer取引別実績利得の合計
  + seller取引別実績利得の合計
```

nonparticipating Vehicle:

```
Vehicle別総実績利得
= 各対象Visitのbaseline_minus_actual_time_valueの合計
```

- 同一Vehicleのbuyer役割別、seller役割別、全参加役割合計を区別する。
- 個別Vehicleは総実績利得0以上を満足、0未満を不満足、0を満足と評価できる。
- 複数Vehicleの金額単位の実績利得も合計可能である。
- 複数Vehicleの合計は純利益・純損失または集合全体の総合判定と表現する。個人の心理的満足と混同しない。
- 正式定義未確定のwelfareとは呼ばない。

### 13. 集計と比較実験

集計単位:

- Vehicle別
- Vehicle×役割別
- 取引別
- Node別
- 実験条件別
- 必要なVehicle集合別

比較実験の必須要件:

- 他条件を固定し、対象VehicleのVOTだけを変える比較ができること。
- 他条件を固定し、対象Vehicleの参加・非参加だけを変える比較ができること。
- 経由ルートや通過Nodeが変わることは制度効果として許容する。
- buyer・seller比率、OD所要時間、時間価値、正式金額、実績利得、満足分類、順位、到着順位効果、他Vehicleへの波及などを後段集計候補とする。
- 順位変化はNode連続順位上で計算する。取引別・Vehicle別・Vehicle×役割別・Node別の各集計は、同じNode連続順位上の個別結果から導出する。
- 取引ごとに新しい順位体系を作らない。取引別集計はNode連続順位上の結果を取引関係Visitについて抽出する。
- 参加・非参加変更比較でも、Node連続順位上の実績順位変化を比較する。
- 集計項目は後から追加・削除しやすくする。後から復元できない個別情報を先に保存する。
- 出力列、ファイル形式、実験条件メタデータは未確定である。

### 14. 後続実装の依存順

候補となる依存順:

1. 成立時保存値と順位情報の引継ぎ
2. 実通過順序の記録
3. 評価終了時未観測確定
4. 取引全体評価
5. buyer・seller個別追加評価
6. 後段集計・実験出力

- 正式実装単位はまだ確定していない。
- 文書保存後に反証レビューと依存関係確認を行う。その後に最初の正式実装単位を決める。
- 短さや高度なPython技法より、明示的で初学者が追いやすい実装を優先する。

### 15. 変更しないもの

- candidate選択
- 成立時経済条件
- 正式支払
- 正式補償
- selected candidate
- final rank
- final consistency validation
- atomic applyの成立条件
- clearance
- 実World交通動作
- actual passage observation
- 3組9 field
- buyer・seller初回通知
- 過去の正式記録

### 16. 未確定事項

順位評価の正本をNode連続順位とする方針は確定済みである。trade_scope内順位かNode連続順位かは未確定事項ではない。

少なくとも次を未確定として記録する。

- 新しい型名、field名、field順序、Enum名
- 評価終了接続API
- 一括処理の原子性
- 再実行防止
- 取引全体評価recordの保存場所
- Node別実通過順序の正式な記録方法
- Node別実通過順位の評価終了時導出方法
- 集計API
- 実験出力の列・形式
- 実験条件メタデータ
- welfare
- true VOT分布
- true VOT=0の最終契約
- true VOTが取引ごとに変わる場合の累計1秒当たり指標

### 17. BLOCKERと利用者判断事項

- 現時点で文書化を妨げるBLOCKERはない。
- 今回の文書追記に必要な利用者判断事項は残っていない。
- §16の未確定事項は、後続詳細設計で扱う。未確定事項を暗黙に決めたことにしない。

### 18. 最新の再開地点

**本節が、TVT-MP全role一括実績評価・順位分析・集計の完全実装前全体設計確定後における最新再開地点である。**

直前の「最新の再開地点（2026-10-03・buyer・seller actual passage初回通知実装検証後）」は、actual passage項目4完了時点の記録として残す。実装全体の最新方針と再開手順は、本節§18を参照する。

次の手順:

1. 詳細設計第4巻の新節はTerminal独立確認済みである。
2. 今回の進捗第3巻追記後、両文書の整合をTerminalで独立確認する。
3. 文書だけを保存する。
4. コミット名には`document`を含める。
5. commit後に最新commit、残存変更、未追跡ファイルを確認する。
6. pushはcommit確認後の別指示で行う。
7. push後に後続実装全体の反証レビューと依存関係確認へ進む。
8. 反証レビュー後に、最初の正式実装単位を確定する。
9. コード、テスト、診断の変更はまだ開始しない。
