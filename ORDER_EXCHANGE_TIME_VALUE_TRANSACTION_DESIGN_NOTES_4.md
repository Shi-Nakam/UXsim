# 時間価値取引型交差点管理・詳細設計メモ 第4巻

記録開始日: 2026-09-28

# 1. 第4巻への移行

- 詳細設計第3巻が長大化し、限定検索と限定表示を常時必要とする状態になったため、第4巻へ移行した。
- 第3巻は削除・再構成せず、確定済みの正式な過去記録として保存する。
- 第4巻は、第3巻を要約して置き換えるものではない。
- atomic apply までの詳細設計、実装結果、検証結果、正式サンプルのスモークテスト、predicted and actual outcome evaluation の詳細仕様は、第3巻を正式参照先とする。
- 以後の上位 driver、World 起動接続、物理通過接続、actual passage 捕捉、actual outcome 実装は、第4巻を最新の詳細設計参照先とする。
- 移行時の最新保存済みコミットは `f616b71` である。
- 第4巻の開始時点では Python・テストへの未保存変更はない。
- 既存の未追跡 `diagnostics/order_control.zip` は研究コード変更ではなく、引き続き Git 対象外である。

# 2. 第4巻開始時点の実装済み範囲

次は実装・検証済みである。

- baseline collector
- baseline fork
- baseline fork alignment
- 既到着未確定 Visit の先行確定
- 先頭非参加 Visit の先行確定
- right-of-entry selection
- candidate visit set
- inlink physical order
- concrete buyer candidate set
- general trade rank
- FIFO inspection
- local binding rank sequence
- candidate local virtual calculation
- local virtual calculation set
- economic evaluation
- candidate selection
- payment・compensation
- final rank construction
- final consistency validation
- atomic apply

atomic apply:

- 全 Node を一括反映する。
- 順位、正式進路、buyer 支払累計、seller 受取累計、成立時履歴を反映する。
- 専用テスト 38 件成功。
- 独立確認の関連テスト 246 件成功。
- UXsim 正式サンプル `example_00en_simple.py` は、実装後も 1200 秒まで正常完走した。
- 正式サンプルは atomic apply を直接呼ぶ統合テストではなく、従来 UXsim 動作の回帰確認である。

# 3. 第4巻開始時点の未実装範囲

- TVT-MP 上位 driver
- World から上位 driver を自動起動する接続
- `Node.transfer` による順位台帳の物理利用
- actual passage の捕捉
- actual outcome record
- 実時間ベースの事後評価実装
- 実績利得
- 満足・不満足分類
- welfare
- 研究用統合シナリオと本格実験出力

# 4. VOTに関する最新確定事項

## declared VOT

- 申告値である。
- 0 を不正値として拒否しない。
- declared VOT=0 は有効である。
- 不参加の代理にしない。
- 不参加は `participates_in_order_exchange=False` で表す。
- buyer になるには、予想ベースの `G_b > 0` が必要である。
- declared VOT=0 なら、予想時間節約が正でも `G_b=0` なので、その Vehicle を buyer に含む候補は経済的に成立しない。
- declared VOT=0 の seller は正式 seller になり得る。
- 補償額 0 でも seller record を省略しない。

## true VOT

- 基本実験では論文・統計資料に基づく分布から設定する。
- 基本実験では `vot_declared=vot_true` とする。
- 採用する分布が 0 を取り得る場合は true VOT=0 を許容する。
- 採用する分布が 0 を取り得ない場合は true VOT=0 を許容しない方向で決める。
- 採用分布が未確定なので、true VOT=0 の最終契約も未確定である。
- 後続評価では成立時 record に保存された `true_vot_per_second` を使用する。
- 後続評価時の live `Vehicle.vot_true` を読み直さない。

詳細な事後評価仕様の正式参照先は、詳細設計第3巻の大見出し「TVT-MP actual passage・事後評価・役割別累計の将来仕様」である。

# 5. 上位driver設計前調査で確認済みの処理順

コード上の処理順は次である。

1. baseline fork を実行する。
2. baseline で確認された Visit を順位台帳へ未確定 Visit として登録する。
3. baseline collector 結果と順位台帳を Node 保存順で照合する。
4. baseline 開始時点 `T` までに到着している未確定 Visit を先行確定する。
5. 意思決定窓の先頭に連続する非参加 Visit を先行確定する。
6. 残りの意思決定窓内 Visit について TVT を検討する。
7. final consistency validation 成功後に atomic apply を全 Node 一括で 1 回呼ぶ。

既到着 Visit の条件:

```text
baseline_arrival_timestep <= baseline_timestep_T
```

baseline 開始の timestep 中に到着時刻が `T` となる Visit も含む。

意思決定窓:

```text
baseline_timestep_T
<
baseline_arrival_timestep
<=
baseline_timestep_T + 6
```

baseline horizon は最低 6 timestep とする。

# 6. 上位driverが呼ぶ予定の正式な部品順

1. `run_snapshot_fixed_baseline_fork_and_align_undetermined_visits`
2. `confirm_already_arrived_undetermined_visits`
3. `confirm_leading_nonparticipating_decision_window_visits`
4. `select_right_of_entry_decision_window_visits`
5. `build_tvt_candidate_visit_set`
6. `build_tvt_inlink_candidate_physical_orders`
7. `build_tvt_mp_concrete_buyer_candidate_sets`
8. `build_tvt_mp_general_trade_ranks`
9. `build_tvt_mp_fifo_inspection_results`
10. `evaluate_tvt_mp_candidate_local_virtual_calculations`
11. `evaluate_tvt_mp_candidate_economics`
12. `select_tvt_mp_candidates`
13. `calculate_tvt_mp_payments_and_compensations`
14. `build_tvt_mp_final_ranks`
15. `validate_tvt_mp_final_consistency`
16. `apply_tvt_mp_validated_result`

- 正常な取引不成立、fallback、`NO_VISITS_TO_CONFIRM`、空 Node は例外ではない。
- status に従って後段へ進める。
- 上位 driver が原因別の最終順位分岐を再実装しない。
- 例外は正常結果へ変換しない。
- 候補別 loop は `evaluate_tvt_mp_candidate_local_virtual_calculations` の内部に置かれている。
- 上位 driver は候補別 local World や candidate local state を保持しない。

# 7. 後段失敗時に残る状態

利用者確認済み方針として、後段で例外が発生しても、正常完了済みの次の処理は取り消さない。

- baseline 時の未確定 Visit 登録
- `baseline_arrival_timestep <= T` の既到着 Visit の順位と正式進路
- 意思決定窓先頭の連続する非参加 Visit の順位と正式進路

理由:

- 既到着 Visit と先頭非参加 Visit は、TVT 取引結果に依存せず先に順位確定できる。
- rollback を導入しない。
- 例外発生後は後続処理を停止する。
- 未処理 Visit の最終順位、金銭、成立時履歴は反映しない。
- atomic apply の一括性は、atomic apply 対象の最終順位、正式進路、金銭、成立時履歴に限る。

# 8. 順位台帳の所有方針

利用者確認済み方針:

- 交差点ごとの順位台帳は World がシミュレーション中ずっと保持する。
- 一度確定した Visit 順位を失わない。
- 各 TVT 対象 Node について `OrderControlTvtNodeRankState` を 1 つ保持する。
- 上位 driver 実行ごとに空の順位台帳を再作成しない。
- 上位 driver が順位を書き込み、後続の物理通過処理が同じ順位を読む。
- World 上の正式属性名と台帳管理 API は未確定である。

# 9. 参加・不参加情報の方針

利用者確認済み方針:

- 各 Visit の参加・不参加は、対応する live Vehicle の `participates_in_order_exchange` を正式な情報源とする。
- `True` は参加、`False` は不参加。
- bool 以外は不正。
- 上位 driver が、必要な VisitKey について `participates_by_visit_key` を構築する。
- 外部参加表と Vehicle 属性を二重管理しない。
- declared VOT=0 を不参加扱いしない。

# 10. 同一時刻の二重実行

利用者確認済み方針:

- 上位 driver は同じ `real_W.T` で 1 回だけ実行する。
- 同じ時刻の再実行は原則禁止する。
- World が最後に上位 driver を実行開始した timestep を保持する。
- 現在時刻と同じなら処理開始前に拒否する。
- 後段失敗前に未確定登録や先行確定が残る場合があるため、同じ時刻の再実行を許さない。
- 正式属性名と例外種別は未確定である。

# 11. TVT対象Nodeの方針

利用者確認済み方針:

- World 内で TVT 使用設定になっている Node を上位 driver が自動収集する。
- 実行ごとに `target_node_names` を外から手作業で渡さない。
- 安定した World 登録順を維持する。
- 対象 Node が 0 件なら何も変更せず正常な no-op とする。
- TVT 対象を示す正式属性と、空対象時の成功結果は未確定である。

# 12. 共通設定

利用者確認済み方針として、当面は全 TVT 対象 Node に共通の設定を使う。

- `baseline_horizon_steps`
- `max_tvt_candidate_visit_count`

`baseline_horizon_steps`:

- Python int
- bool 不可
- 6 以上

`max_tvt_candidate_visit_count`:

- Python int
- bool 不可
- 1 以上
- BATCH の `max_batch_size` または `N` とは別の TVT 専用設定

現段階では Node 別上書きを作らない。正式な保存場所と属性名は未確定である。

# 13. 成功結果の方針

利用者確認済み方針:

- 上位 driver 成功結果は atomic apply 成功結果だけを保持する。
- atomic apply 結果から保存済み参照連鎖を上流へたどれるため、途中結果を重複保持しない。
- live World、Node、Vehicle、順位台帳、mutable list、mutable dict を保持しない。
- 正常な取引不成立、fallback、`NO_VISITS_TO_CONFIRM` も、最後まで正常処理できれば上位 driver 成功である。
- 例外失敗は成功結果へ変換しない。
- 成功結果型と field の正式名称は未確定である。

# 14. 今回の実装範囲

利用者確認済み方針として、次の段階では上位 driver 単体までを実装する。

実装対象:

- 完成済み 16 段の正式呼出し
- World から必要状態と設定を取得
- 参加表を構築
- 同一 `T` の二重実行防止
- atomic apply まで接続
- 成功結果型
- 専用テスト

同時に実装しない:

- World の各 timestep からの自動起動
- `exec_simulation` への接続
- `Node.transfer` による物理通過
- actual passage
- actual outcome
- 事後評価
- 満足評価

上位 driver 単体を検証した後に、自動起動と物理通過接続を別段階で設計する。

# 15. 物理通過との境界

上位 driver 成功後に反映済み:

- 順位台帳
- 正式進路
- buyer 支払累計
- seller 受取累計
- 成立時履歴

まだ変わらない:

- Vehicle の物理位置
- Link 内の物理順
- `Node.transfer` が選ぶ通過順
- actual passage
- actual outcome

上位 driver だけでは、実際の車両通過順は変わらない。

# 16. 専用テストで固定すべき契約

最低限、次を固定する。

- 16 段を正式順に各 1 回呼ぶ
- target Node 保存順
- 空 Node を落とさない
- TVT 対象 Node 0 件の no-op
- selected、fallback、`NO_VISITS_TO_CONFIRM`
- 非参加あり
- seller 0 件
- 複数 Node
- atomic apply を最後に 1 回だけ呼ぶ
- 途中例外で後段を呼ばない
- 例外を成功へ変換しない
- 先行確定を rollback しない
- 同一 `T` 二重実行を開始前に拒否
- Vehicle 属性から参加表を作る
- declared VOT=0 を不参加扱いしない
- 候補 loop を driver へ再実装しない
- 成功後も物理通過順はまだ変わらない

# 17. 未確定事項

- 上位 driver 公開関数名
- 成功結果型名と field 名
- World 上の順位台帳属性名
- World 上の最終実行 timestep 属性名
- 共通設定の保存場所と属性名
- TVT 対象 Node の正式判定属性
- 対象 Node 追加・削除時の順位台帳管理 API
- TVT 対象 Node 0 件時の具体的な成功結果
- 同一 `T` 二重実行時の例外種別
- baseline で発見された Visit の Vehicle が live World に存在しない場合の扱い
- 新規本番・専用テストの正式ファイル名
- World 属性追加のために `uxsim.py` を上位 driver 単体の実装時点で変更するか
- 公開 API の位置引数と keyword-only 引数の境界
- driver の実行段階を診断用に保存するか

# 18. 採用しない方向

- Node 単位の上位 driver
- Node ごとの atomic apply
- driver 内で候補 loop や local World を直接管理
- driver 内で原因別最終順位分岐を再実装
- driver 内で金額を再計算
- driver 内で actual outcome を計算
- driver 実装と `Node.transfer` 変更を同時に行う
- 同一 `T` の無条件再実行
- driver 実行ごとに順位台帳を新規作成
- declared VOT=0 を不参加扱い
- 外部参加表と Vehicle 属性の二重管理
- 後段失敗時の先行確定 rollback

# 19. 次の再開地点

1. 第4巻の本節を Terminal で限定確認する。
2. 進捗第3巻を Terminal で限定確認する。
3. 旧巻へ移行注記を別作業で追記する。
4. `git diff --check` を実行する。
5. 文書 4 ファイルだけが変更されていることを確認する。
6. commit 名に `document` を含めて commit する。
7. commit と push を分ける。
8. 保存後、上位 driver 完全実装前仕様を第4巻へ作成する。
9. 正式関数名、型名、World 属性名、設定名、例外境界を確定する。
10. その後、上位 driver 本番と専用テストを実装する。

# TVT-MP上位driver・完全実装前仕様

記録日: 2026-09-28

本節は完全実装前仕様である。Python 実装と専用テストは未着手である。§1 から §19 の利用者確認済み方針は、実コードと衝突しない限り維持する。本節はそれを実装できる契約へ落とす。本節について、利用者判断が必要な事項は解消済みである。§25 に将来課題以外の未確定は残さない。

## 1. 目的と実装範囲

完成済みの TVT-MP 部品を、1つの入口から正式順に呼び、final consistency validation の成功後にだけ atomic apply まで進める。

今回の実装範囲:

- 上位 driver 単体
- 16段の順次接続
- World から対象 Node、順位台帳、共通設定を取得
- 必要な VisitKey の参加表を Vehicle 属性から構築
- TVT 対象 Node が1件以上のときの同一 `real_W.T` 二重実行防止
- 成功結果型
- 専用テスト

今回実装しない:

- `exec_simulation` からの自動起動
- `Node.transfer` の変更
- 物理通過順の制御
- actual passage
- actual outcome
- 実時間ベースの事後評価
- 満足評価

`Node.transfer` は `fcfs` と `batch` だけを特別扱いする。`time_value` は従来の合流処理のままである。driver 成功後も物理通過順は変わらない。

## 2. 正式予定ファイル

- 本番: `uxsim/order_control_tvt_mp_driver.py`
- 専用テスト: `tests_order_control_tvt_mp_driver.py`

既存の `order_control_tvt_mp_*.py` と `tests_order_control_tvt_mp_*.py` の命名に合わせる。`run_tvt_mp_driver` という公開関数は既存コードにない。

World の新しい属性を初期化するため、実装時に `uxsim/uxsim.py` の `World.__init__` だけを変更する。`exec_simulation` と `Node.transfer` は変更しない。

## 3. 公開型と公開API

公開関数:

```text
run_tvt_mp_driver(real_W) -> OrderControlTvtMpDriverResult
```

- 位置引数は `real_W` の1つだけである。
- keyword-only 引数は置かない。
- `target_node_names`、horizon、候補上限、参加表、順位台帳は公開引数にしない。World から読む。
- 比較した候補 `run_tvt_mp_order_control` と `run_tvt_mp_order_control_driver` は、既存の `run_snapshot_fixed_baseline_fork` より長い。処理は TVT-MP の1回の入口なので、`run_tvt_mp_driver` を正式名とする。

成功結果型は frozen dataclass `OrderControlTvtMpDriverResult` である。

field は1つ:

```text
atomic_apply_set_result: OrderControlTvtMpAtomicApplySetResult | None
```

- TVT 対象 Node が1件以上で、16段と atomic apply が成功した場合、16段目の `apply_tvt_mp_validated_result` が返した `OrderControlTvtMpAtomicApplySetResult` と同一 object を保持する。atomic apply 結果は driver への入力ではなく、16段目の戻り値である。
- 対象 Node が0件の場合は `None` である。atomic apply は呼ばない。別の no-op 型や status enum は作らない。
- live World、Node、Vehicle、順位台帳、mutable list、mutable dict は保持しない。
- 途中結果は重複保持しない。apply 結果の参照連鎖から上流へたどる。

## 4. Worldが保持する状態

`World.__init__` で次を作る。driver は属性の初回作成をしない。

| 属性 | 初期値 | 役割 |
| --- | --- | --- |
| `order_control_tvt_rank_states_by_node_name` | 空の `dict` | Node 名から `OrderControlTvtNodeRankState` への台帳。World が所有する |
| `order_control_tvt_driver_started_timestep` | `None` | TVT 対象 Node が1件以上の実行を受理した `real_W.T`。成功時刻ではない。対象0件の no-op では変更しない |
| `order_control_tvt_baseline_horizon_steps` | `6` | 全対象 Node 共通の baseline horizon |
| `order_control_tvt_max_candidate_visit_count` | `None` | 全 TVT 対象 Node 共通の候補 Visit 上限。初期値は `None`。TVT 専用であり BATCH の `max_batch_size` または `N` とは別である |

短い `tvt_rank_states_by_node_name` は採用しない。既存の `order_control_rng` と同じ `order_control_` 接頭辞にそろえる。

台帳 dict の値は `OrderControlTvtNodeRankState` である。driver は実行ごとに空 dict へ取り替えない。

`order_control_tvt_max_candidate_visit_count` は研究条件である。暗黙の既定値 10 などは置かない。設定忘れを暗黙値で隠さない。World 初期値は `None` のままとする。TVT 対象 Node が0件の no-op では、候補数上限が未設定でも正常に終える。正常な no-op は、World、順位台帳、Vehicle、`order_control_tvt_driver_started_timestep` のいずれも変更せず正常に処理を終えることである。TVT 対象 Node が1件以上ある場合は、候補数上限の明示設定を必須とする。検証の詳細は §6 である。

## 5. TVT対象Nodeの収集

既存の `Node.order_control_type` は `"none"`、`"fcfs"`、`"batch"`、`"time_value"` である。`time_value` を TVT 対象の正式値とする。この許容集合は変えない。

収集規則:

- `World.NODES` を登録順に走査する。`Node.__init__` は `W.NODES.append` で登録する。これが安定した登録順である。
- `order_control_type == "time_value"` かつ `order_control_eligible is True` の Node だけを対象にする。
- 名前は `node.name` である。Node 作成時に `NODES_NAME_DICT` が同名を拒否するため、通常の World では同名 Node は存在しない。収集結果に同名が現れた場合は、実行開始前に `RuntimeError` とする。
- `World.get_node` で集め直さない。登録順が list 側にある。
- 対象が0件なら §12 の no-op とする。
- 実行の公開引数で `target_node_names` を渡さない。

対象 Node の台帳が dict に無い場合、baseline を呼ぶ前に `OrderControlTvtNodeRankState(node_name)` を1つ作って同じ dict へ入れる。既にある場合は、その object の `node_name` が鍵と一致することを確認する。一致しなければ `RuntimeError` とする。

今回、対象から外れた Node の台帳は削除しない。追加・削除の管理 API は作らない。

## 6. 共通設定

全 TVT 対象 Node に同じ値を使う。Node 別上書きは作らない。BATCH の `batch_size`、`max_batch_size`、`N`、`order_control_batch_virtual_horizon` とは別名である。候補数上限は BATCH の `max_batch_size` または `N` とは別の TVT 専用設定である。

`order_control_tvt_baseline_horizon_steps`:

- Python `int`
- `bool` 不可
- 6 以上
- 意思決定窓 `T < baseline_arrival_timestep <= T + 6` を baseline が観測できる下限である
- 対象 Node が1件以上のとき、§7 手順8で検査する。開始時刻を記録する前に不正なら `ValueError`

`order_control_tvt_max_candidate_visit_count`:

- TVT 対象 Node が0件のときは、本属性が `None` でも §12 の no-op として扱う。16段開始前の候補上限検査は行わない。
- TVT 対象 Node が1件以上のときは、明示設定を必須とする。有効値は Python `int` で、`bool` は不可、1 以上である。
- 対象が1件以上で、`None`、`bool`、Python `int` 以外、または 0 以下なら、§7 手順8で `ValueError` とする。二重実行検査より後、開始時刻記録より前である。
- 暗黙の既定値 10 などは置かない。研究条件であり、設定忘れを暗黙値で隠さない。
- 全 TVT 対象 Node で共通の1値である。
- `build_tvt_candidate_visit_set` の keyword-only 引数 `max_tvt_candidate_visit_count` へ渡す。

## 7. 同一T二重実行防止

`World.T` はシミュレーションの整数 timestep である。`exec_simulation` は `for W.T in range(...)` で進める。

二重実行防止は、TVT 対象 Node が1件以上の実行にだけ適用する。対象 Node が0件の no-op では、開始時刻を変更しないため、同一 `T` 拒否も適用しない。同じ実時刻 `T` に再度呼ばれても、対象が引き続き0件なら、再び何も変更せず正常 no-op で返す。

手順:

1. `real_W` が `World` でなければ `ValueError`。live 状態はまだ変えない。
2. `real_W.T` が `bool` 以外の Python `int` でなければ `ValueError`。live 状態はまだ変えない。
3. §5 の規則で TVT 対象 Node を収集する。
4. 対象 Node が0件なら、`order_control_tvt_driver_started_timestep` を変更せず、§12 の正常 no-op として `OrderControlTvtMpDriverResult(atomic_apply_set_result=None)` を返す。以降の手順は行わない。
5. 対象 Node が1件以上なら、`order_control_tvt_driver_started_timestep` が `None` でも `int` でもなければ `RuntimeError`。この時点では開始時刻はまだ変えない。
6. 保存値が現在の `T` と同じなら、16段の処理開始前に `RuntimeError`。同じ時刻の再実行は、前回が成功でも途中例外でも拒否する。共通設定が不正でも、ここでは設定の `ValueError` より `RuntimeError` を先に投げる。
7. 保存値が `None` でなく、現在の `T` が保存値より小さい場合は `RuntimeError`。時刻が戻った実行は開始しない。開始時刻も更新しない。
8. 手順5から7を通過したあと、§6 の共通設定を検査する。不正なら 16段の処理開始前に `ValueError`。この時点では開始時刻はまだ変えない。
9. 手順8を通過した直後、baseline や台帳作成より前に `order_control_tvt_driver_started_timestep = real_W.T` を書く。
10. 手順9の後に例外が出ても、この値を戻さない。

同じ時刻で既に実行を開始した事実は、現在の設定値より先に確認する。二重実行でなければ、設定不正は開始時刻記録前の `ValueError` とする。初回実行で設定が不正なら `ValueError` となり、開始時刻は変更しない。設定を修正した後、同じ `T` の未開始の初回実行として再実行できる。手順9の後に台帳作成、baseline、先行確定、apply のいずれかが始まった失敗は、同じ `T` では再実行できない。

## 8. 順位台帳の生成・保持・整合確認

- World 初期化時の台帳は空 dict である。
- 対象0件の no-op では台帳を増やさない。
- 対象が1件以上なら、開始時刻を記録したあと、不足している対象 Node の `OrderControlTvtNodeRankState` を既存 dict へ追加する。
- 既存 object は捨てない。確定済み順位を消さない。
- 16段のうち台帳を受け取る段には、この同じ dict を渡す。
- 対象外の鍵が dict に残っていても、今回の対象へは渡した dict のまま参照する。既存部品は対象 Node の鍵を読む。
- 鍵の値が `OrderControlTvtNodeRankState` でない、または `node_name` が鍵と違う場合は `RuntimeError`。

## 9. 参加表の構築

正本は live `Vehicle.participates_in_order_exchange` である。`True` は参加、`False` は不参加である。declared VOT=0 では判断しない。外部から参加表を受けない。

構築時点は、2段目 `confirm_already_arrived_undetermined_visits` の成功後、3段目の直前である。

母集団は意思決定窓内 Visit だけである。3段目は、その VisitKey が `participates_by_visit_key` にあり、値が Python `bool` であることを要求する。4段目、7段目、8段目が読む VisitKey は、この窓から作られる候補であり、同じ表に含まれる。

取得経路:

- `arrived_confirmation_result.alignment_fork_result.alignment_results`
- 各 Node の `resolved_undetermined_visits`
- `baseline_timestep_T < baseline_arrival_timestep <= baseline_timestep_T + 6` の `visit_key`

`OrderControlTvtVisitKey` は `(vehicle_name, visit_id)` である。同じ Vehicle の複数 Visit は `visit_id` で区別する。Vehicle 名は `visit_key[0]` である。

`real_W.VEHICLES` は `OrderedDict[str, Vehicle]` である。各 vehicle name について次を確認する。

- `VEHICLES` にその名前が無い: `RuntimeError`
- 値が `Vehicle` でない: `RuntimeError`
- `participates_in_order_exchange` が無い: `RuntimeError`
- 値が Python `bool` でない: `RuntimeError`

意思決定窓の外の未確定 Visit までは表に入れない。後段が表に無い VisitKey を要求した場合は、既存部品の例外を包まず上へ出す。

## 10. 16段の正式呼出し順

公開関数内で、次を上から順に、通常の関数呼出しとして書く。関数 list の loop、`getattr`、decorator、plugin では呼ばない。

1. `run_snapshot_fixed_baseline_fork_and_align_undetermined_visits`
2. `confirm_already_arrived_undetermined_visits`
3. `confirm_leading_nonparticipating_decision_window_visits`
4. `select_right_of_entry_decision_window_visits`
5. `build_tvt_candidate_visit_set`
6. `build_tvt_inlink_candidate_physical_orders`
7. `build_tvt_mp_concrete_buyer_candidate_sets`
8. `build_tvt_mp_general_trade_ranks`
9. `build_tvt_mp_fifo_inspection_results`
10. `evaluate_tvt_mp_candidate_local_virtual_calculations`
11. `evaluate_tvt_mp_candidate_economics`
12. `select_tvt_mp_candidates`
13. `calculate_tvt_mp_payments_and_compensations`
14. `build_tvt_mp_final_ranks`
15. `validate_tvt_mp_final_consistency`
16. `apply_tvt_mp_validated_result`

対象 Node が0件のときは、この16段を1つも呼ばない。

ある段が例外を出したら、後段は呼ばない。例外を成功結果へ変換しない。

## 11. 各段階の正確な引数接続

台帳は常に `real_W.order_control_tvt_rank_states_by_node_name` である。参加表は §9 で作った dict である。

| 段 | 位置引数 | keyword-only | 主結果型 |
| --- | --- | --- | --- |
| 1 | `real_W` | `target_node_names`、`baseline_horizon_steps`、`rank_states_by_node_name` | `OrderControlTvtBaselineForkAlignmentResult` |
| 2 | 1段目の結果 | `rank_states_by_node_name`、`real_W` | `OrderControlTvtArrivedUndeterminedConfirmationResult` |
| 3 | 2段目の結果 | `rank_states_by_node_name`、`participates_by_visit_key`、`real_W` | `OrderControlTvtLeadingNonparticipatingConfirmationResult` |
| 4 | 3段目の結果 | `rank_states_by_node_name`、`participates_by_visit_key` | `OrderControlTvtRightOfEntrySelectionResult` |
| 5 | 4段目の結果 | `rank_states_by_node_name`、`max_tvt_candidate_visit_count` | `OrderControlTvtCandidateVisitSetResult` |
| 6 | 5段目の結果 | なし | `OrderControlTvtInlinkCandidatePhysicalOrderSetResult` |
| 7 | 6段目の結果 | `participates_by_visit_key` | `OrderControlTvtMpConcreteBuyerCandidateSetResult` |
| 8 | 7段目の結果 | `participates_by_visit_key` | `OrderControlTvtMpGeneralTradeRankSetResult` |
| 9 | 8段目の結果 | なし | `OrderControlTvtMpFifoInspectionSetResult` |
| 10 | `real_W`、9段目の結果 | `rank_states_by_node_name` | `OrderControlTvtMpLocalVirtualCalculationSetResult` |
| 11 | 10段目の結果、`real_W` | なし | `OrderControlTvtMpEconomicEvaluationSetResult` |
| 12 | 11段目の結果、`real_W` | なし | `OrderControlTvtMpCandidateSelectionSetResult` |
| 13 | 12段目の結果 | なし | `OrderControlTvtMpPaymentAndCompensationSetResult` |
| 14 | 13段目の結果 | なし | `OrderControlTvtMpFinalRankSetResult` |
| 15 | 14段目の結果 | なし | `OrderControlTvtMpFinalConsistencyValidationSetResult` |
| 16 | 15段目の結果、`real_W`、台帳 | なし。位置引数3つ | `OrderControlTvtMpAtomicApplySetResult` |

1段目の `target_node_names` は §5 で集めた名前の tuple である。horizon は World 属性である。候補上限は World 属性である。

6段目以降は、前段の frozen 結果だけを渡す段がある。collector、fork World、候補 loop の状態は driver が持ち直さない。10段目の内部が、FIFO を通過した候補ごとに binding sequence と local virtual calculation を実行する。

## 12. 正常な不成立・空結果

次は例外ではない。status に従い16段を最後まで呼ぶ。

- 正常な取引不成立
- fallback
- `NO_VISITS_TO_CONFIRM`
- 空 Node
- seller 0件
- 非参加 Visit があること

driver は最終順位の原因別分岐を再実装しない。金額も再計算しない。

対象 Node が0件の正式契約:

- 16段も atomic apply も呼ばない。
- baseline fork を実行しない。
- 新しい順位台帳を作らない。
- `order_control_tvt_max_candidate_visit_count` が `None` でも正常な no-op である。
- `order_control_tvt_driver_started_timestep` を変更しない。
- 同じ実時刻 `T` に再度呼ばれても、対象 Node が引き続き0件なら、再び何も変更せず正常 no-op とする。§7 の同一 `T` 拒否は適用しない。
- 「何も変更しない」とは、World、順位台帳、Vehicle、`order_control_tvt_driver_started_timestep` のいずれも変更しないことを意味する。
- 成功結果は `OrderControlTvtMpDriverResult(atomic_apply_set_result=None)` である。
- 専用 status は追加しない。

## 13. 後段失敗時の残存状態

対象 Node が1件以上の実行で、開始時刻を書いた後に例外が出ても、正常完了済みの次は取り消さない。

- baseline 登録が完了していれば、未確定 Visit 登録は残る。
- 2段目が完了していれば、`baseline_arrival_timestep <= T` の既到着 Visit の順位と正式進路は残る。baseline 開始 timestep 中に到着時刻が `T` の Visit も含む。
- 3段目が完了していれば、意思決定窓先頭の連続する非参加 Visit の順位と正式進路は残る。

残る理由は、これらが TVT の採否に依存せず先に確定できるからである。rollback はしない。

例外の段より後は実行しない。未処理 Visit の最終順位、`payment_paid`、`payment_received`、成立時履歴は、atomic apply が成功していない限り増えない。atomic apply の一括性は、apply 対象の最終順位、正式進路、金銭、成立時履歴に限る。

## 14. atomic applyとの接続

15段目が例外なく戻った場合だけ、16段目を1回呼ぶ。

```text
apply_tvt_mp_validated_result(
    validation_result,
    real_W,
    real_W.order_control_tvt_rank_states_by_node_name,
)
```

- validation 結果は同一 object のまま渡す。
- 台帳は同じ dict である。
- Node 単位の apply はしない。
- apply の例外は成功にしない。
- driver は順位、金額、履歴を再構築しない。

## 15. 成功結果

`run_tvt_mp_driver` が戻るのは、対象0件の no-op か、16段目が戻った場合だけである。

- 対象1件以上: `atomic_apply_set_result` は 16段目 `apply_tvt_mp_validated_result` の戻り値 `OrderControlTvtMpAtomicApplySetResult` そのもの。
- 対象0件: `atomic_apply_set_result` は `None`。同一 `T` への再呼出しでも、対象が0件のままなら再び同じ成功結果を返し得る。
- 正常な不成立、fallback、`NO_VISITS_TO_CONFIRM` も、apply まで終われば driver 成功である。
- 例外は結果 object にしない。

## 16. ValueErrorとRuntimeError

driver 自身が投げるもの:

`ValueError`:

- `real_W` が `World` でない
- `real_W.T` が Python `int` でない、または `bool`
- 対象 Node が1件以上で、§7 手順8の共通設定検査に反する。horizon または候補上限の型・値が §6 に反する
- 対象が1件以上で、候補上限が `None`、`bool`、Python `int` 以外、または 0 以下

`RuntimeError`:

- 対象 Node が1件以上の実行で、§7 手順6の同一 `T` の再実行。共通設定が不正でも、開始済みの同一 `T` ではこちらを先に投げる
- 対象 Node が1件以上の実行で、§7 手順7の現在の `T` が開始済み timestep より小さい
- 対象 Node が1件以上の実行で、§7 手順5の開始時刻属性の型が壊れている
- 対象 Node 名の重複
- 台帳の型または `node_name` の不一致
- 意思決定窓 Visit の Vehicle が `VEHICLES` に無い
- その値が `Vehicle` でない
- `participates_in_order_exchange` が無い、または `bool` でない

既存16段が出した `ValueError` と `RuntimeError` は、別例外へ包まない。原因のメッセージを失わない。

## 17. live状態の変更範囲

変わり得るもの:

- `order_control_tvt_driver_started_timestep`: 対象 Node が1件以上の実行を §7 手順9で受理したとき
- 順位台帳 dict: 不足 Node の新規台帳
- 台帳の中身: 未確定登録、既到着確定、先頭非参加確定、apply による最終順位と正式進路
- 成立した buyer の `payment_paid` と `order_exchange_log`
- 成立した seller の `payment_received` と `order_exchange_log`

変えないもの:

- Vehicle の物理位置
- Link 内の並び
- `Node.transfer` が選ぶ通過順
- `vot_declared`
- `vot_true`
- `participates_in_order_exchange`
- actual outcome
- `rng` と `order_control_rng`。候補選択は既存部品が `random_seed` から局所乱数を作る

対象0件の no-op では、live 状態は一切変えない。`order_control_tvt_driver_started_timestep` も変えない。

## 18. 不変性

変更しない入力と上流結果:

- 各段が返した frozen 結果を後から書き換えない
- 参加表は driver 内の一時 dict であり、Vehicle 属性へ書き戻さない
- declared VOT=0 を `participates_in_order_exchange` の変更に使わない

## 19. 可読性

- 16段は公開関数の中で、名前のある中間変数へ順に受ける。
- 参加表の構築、対象 Node の収集、対象0件 no-op の早期 return、対象1件以上向けの開始時刻型・二重実行検査、共通設定検査は、それぞれ小さい private 関数に分けてよい。検査順は §7 にそろえる。
- 動的な関数列、`getattr`、decorator、plugin、巨大な段階辞書、長い内包表記は使わない。
- コメントは、開始時刻を戻さない理由と、先行確定を取り消さない理由だけを短く書く。

## 20. 専用テスト契約

`tests_order_control_tvt_mp_driver.py` で、少なくとも次を固定する。

- 公開関数名が `run_tvt_mp_driver` である
- 成功型が `OrderControlTvtMpDriverResult` である
- 16段を正式順に各1回呼ぶ
- 対象 Node の登録順を維持する
- 空 Node を結果から落とさない
- 対象0件は no-op で、`atomic_apply_set_result is None`、baseline も apply も呼ばない。`order_control_tvt_driver_started_timestep` は変えない
- 対象0件で同一 `T` に2回呼んでも、2回とも何も変更せず正常 no-op である
- selected、fallback、`NO_VISITS_TO_CONFIRM`
- 非参加 Visit がある
- seller 0件
- 複数 Node
- atomic apply は最後に1回だけ
- 途中例外では後段を呼ばない
- 例外を成功へ変換しない
- 先行確定を rollback しない
- 対象1件以上のとき、同一 `T` の再実行を 16段開始前に拒否する
- 同一 `T` で開始済みかつ共通設定も不正な場合、二重実行 `RuntimeError` を設定 `ValueError` より優先する
- 初回実行で共通設定が不正なら `ValueError` となり、`order_control_tvt_driver_started_timestep` は変更しない
- 設定修正後、同じ `T` の未開始の初回実行として再実行できる
- 参加表は `Vehicle.participates_in_order_exchange` から作る
- declared VOT=0 を不参加にしない
- 候補 loop を driver が再実装しない
- 成功後も物理位置と `Node.transfer` の通過順は変わらない
- `exec_simulation` は driver を呼ばない

全段を通す World は、既存の部品テストの作り方を参考に、専用テスト内の小さな交差点として新しく組む。完成済みの atomic apply fixture は、凍結済み validation を apply へ直接渡すものであり、16段の入口テストにはそのまま使えない。

## 21. 既存回帰

driver 実装時に維持するもの:

- 既存16段の公開シグネチャ
- atomic apply の位置引数3つと全 Node 一括
- `Node.order_control_type` の許容値
- `Node.transfer` が `time_value` を特別扱いしないこと
- `exec_simulation` が driver を呼ばないこと
- UXsim 正式サンプルが TVT 設定を持たないこと

`uxsim.py` の変更は、新しい World 属性の初期化に限る。正式サンプルは対象 Node が0件の経路を自動起動しないので、属性追加だけでは TVT を実行しない。

## 22. 実装対象ファイル

- 新規 `uxsim/order_control_tvt_mp_driver.py`
- 新規 `tests_order_control_tvt_mp_driver.py`
- 変更 `uxsim/uxsim.py` の `World.__init__` のみ

既存の TVT 部品、atomic apply、`Node.transfer`、`exec_simulation` は変更しない。

## 23. 未実装範囲

- World の各 timestep からの自動起動
- `exec_simulation` への接続
- `Node.transfer` による順位台帳の物理利用
- actual passage
- actual outcome
- 事後評価
- 満足評価
- welfare
- 対象 Node の台帳を削除する API
- Node 別の horizon または候補上限

## 24. 反証して採用しない事項

- Node 単位の driver
- Node ごとの atomic apply
- driver 内の候補 loop と local World
- 原因別最終順位分岐の再実装
- driver 内の金額再計算
- driver 内の actual outcome
- driver と `Node.transfer` の同時変更
- 同一 `T` の無条件再実行
- 実行ごとの台帳新規作成
- declared VOT=0 を不参加にする
- 外部参加表と Vehicle 属性の二重管理
- 後段失敗時の先行確定 rollback
- 対象0件用の別成功型
- 16段の動的呼出し
- 後段例外を別例外で包むこと
- 到達段階名の診断属性

## 25. 未確定事項

### 利用者判断が必要な事項

本節の完全実装前仕様について、利用者判断が必要な事項は解消済みである。`order_control_tvt_max_candidate_visit_count` の契約は §4 と §6 で確定した。

### 完全実装前仕様として確定済みの名称と契約

本節に明記した次は、完全実装前仕様として確定済みである。

- 公開関数名 `run_tvt_mp_driver`
- 成功結果型 `OrderControlTvtMpDriverResult` と field `atomic_apply_set_result`
- World 属性名と初期値
- TVT 対象 Node 判定
- 対象0件 no-op
- 対象1件以上向けの二重実行防止と検査順
- 参加表の正本
- 16段の引数接続
- 例外を別例外へ包まないこと
- 診断属性を作らないこと

実装時には実コードとの最終照合を行う。これは別名や別契約へ再検討することを意味しない。明示的な実コード上の衝突が発見された場合だけ、実装を止めて報告する。

### 将来課題

次だけを将来課題として残す。

- 対象から外れた Node の順位台帳を、いつ削除するか。今回の実装では台帳削除機能を作らない。基本実験では TVT 対象 Node を途中変更しない想定である。

## 26. 次の再開地点

1. 第4巻の完全実装前仕様を Terminal で限定確認する。
2. 進捗第3巻へ仕様確定要約を追記する。
3. `git diff --check` と変更ファイル確認を行う。
4. 文書を commit する。
5. commit と push を分離する。
6. 保存後、上位 driver 本番と専用テストを実装する。

## 27. 実装・独立確認・検証結果（2026-09-28）

§1 から §26 は、実装前の正式仕様として残す。本節は、その仕様に従って実装し、独立確認した記録である。仕様の意味、名称、例外境界、処理順は変更していない。

### 実装ファイル

新規:

- `uxsim/order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_mp_driver.py`

既存変更:

- `uxsim/uxsim.py`。`World.__init__` への属性初期化だけ
- `tests_order_control_tvt_baseline_fork_alignment.py`。既存期待 field の追随漏れ1件だけ

`exec_simulation` と `Node.transfer` は変更していない。

### 公開API

公開関数は `run_tvt_mp_driver(real_W)` である。成功結果型は frozen dataclass `OrderControlTvtMpDriverResult` である。field は `atomic_apply_set_result` だけである。対象 Node が1件以上のとき、16段目 `apply_tvt_mp_validated_result` の戻り値と同一 object を保持する。

実装した処理:

- TVT 対象 Node を World 登録順で収集する
- 対象条件は `order_control_type == "time_value"` かつ `order_control_eligible is True`
- 対象 Node 0件の完全 no-op
- 対象 Node がある場合の同一 `T` 二重実行防止
- 時刻逆行の拒否
- 共通 baseline horizon の検査
- TVT 候補 Visit 数上限の検査
- World 所有の順位台帳の作成と再利用
- `Vehicle.participates_in_order_exchange` からの参加表構築
- 完成済み16段の明示的な順次呼出し
- final consistency validation 成功後の atomic apply 1回
- atomic apply 結果と同一 object を成功結果へ保存する
- 既存例外を別例外へ包まない
- 後段例外時に開始時刻と完了済み先行処理を rollback しない

### World属性

`uxsim/uxsim.py` の `World.__init__` へ次を追加した。

- `order_control_tvt_rank_states_by_node_name = {}`
- `order_control_tvt_driver_started_timestep = None`
- `order_control_tvt_baseline_horizon_steps = 6`
- `order_control_tvt_max_candidate_visit_count = None`

### 対象0件no-op

- 16段を呼ばない
- baseline fork を呼ばない
- atomic apply を呼ばない
- 順位台帳を追加しない
- driver 開始時刻を変更しない
- Vehicle を変更しない
- 候補数上限が `None` でも正常
- `atomic_apply_set_result` は `None`
- 同じ `T` で再度呼ばれても、対象が0件のままなら再び正常 no-op

### 二重実行

対象 Node が1件以上の場合の順序:

1. World と `T` を検査する
2. 対象 Node を収集する
3. `started_timestep` 型を検査する
4. 同一 `T` を拒否する
5. 時刻逆行を拒否する
6. 共通設定を検査する
7. 全検査成功後、16段開始前に開始時刻を記録する
8. 以後の例外でも開始時刻を戻さない

同一 `T` で開始済みかつ設定も不正なら、二重実行 `RuntimeError` を優先する。初回設定不正なら `ValueError` で、開始時刻は変更しない。設定修正後、同じ `T` の未開始の初回実行として再実行できる。

### 順位台帳

開始時刻の記録後に、不足している対象 Node へ `OrderControlTvtNodeRankState` を既存 dict へ追加する。既存 object は捨てない。型不一致と `node_name` 不一致は `RuntimeError` である。対象外 Node の台帳は削除しない。

### 参加表

- 2段目成功後、3段目前に構築する
- 意思決定窓 `T < arrival <= T + 6` の Visit だけを対象にする
- `VisitKey[0]` から Vehicle 名を取得する
- `Vehicle.participates_in_order_exchange` を正本とする
- declared VOT=0 では参加・不参加を判断しない
- Vehicle 欠落、型不正、属性欠落、bool 以外は `RuntimeError`

### 16段接続

完成済み16段を公開関数の中で、名前のある中間変数へ順に受ける。関数 list の loop、`getattr`、decorator は使っていない。atomic apply は最後に全 Node 一括で1回だけ呼ぶ。正常な取引不成立、fallback、`NO_VISITS_TO_CONFIRM` も、各段が成功すれば driver 成功である。

### 後段失敗

ある段が例外を出したら後段は呼ばない。例外を成功結果へ変換しない。既存部品の例外は包まない。開始時刻と、正常完了済みの未確定 Visit 登録、既到着 Visit 確定、先頭非参加 Visit 確定は戻さない。

### 既存テスト期待値修正

`tests_order_control_tvt_baseline_fork_alignment.py` の `test_does_not_modify_existing_result_types` について、`OrderControlBaselineForkResult` の期待 field 集合へ `downstream_boundary_result` を追加した。

原因:

- 保存済みコミット `c703d9b` の本番結果型には、既に `downstream_boundary_result` が存在した
- 同じ保存済みコミットのテスト期待値から同 field が漏れていた
- 今回の上位 driver 実装による本番型変更や回帰ではない
- 既存テスト期待値の追随漏れを修正した

### 独立確認

Cursor 報告だけでは完了判断していない。次を独立確認した。

- 新規 driver 本体
- 専用テスト
- `uxsim.py` の属性追加箇所
- baseline 結果型
- 失敗した既存テストの期待 field
- 保存済み `c703d9b` 時点の本番型と既存テスト期待値

### 専用テスト結果

- 定義済み test 関数: 31
- `TESTS` 登録: 31
- pytest 収集: 31
- 重複なし
- 登録漏れなし
- 未定義参照なし
- 全31件成功

専用テスト: `31 passed in 14.66s`

直接実行: `31 tests passed`

### 実部品統合テスト

追加テスト: `test_real_sixteen_stages_reach_atomic_apply_on_quiet_junction`

目的:

- monkeypatch した代替部品ではなく、本物の16部品が driver を介して連続動作することを確認する
- 最後の atomic apply まで正常に到達することを確認する
- 取引成立自体や物理通過順の変更を確認するテストではない

交通シナリオ:

- TVT 対象 Node は `junction` の1件
- `order_control_type="time_value"`
- `order_control_eligible=True`
- 単車線
- inlink と outlink を各1本
- Vehicle は `late_car` の1台
- 出発時刻は200秒
- 意思決定時刻は `T=15`
- baseline horizon は6
- TVT 候補 Visit 数上限は1
- `participates_in_order_exchange=True`
- `vot_declared=1.0`
- `vot_true=2.0`

この条件では、`late_car` は意思決定窓内へ入らない。

呼出し: `run_tvt_mp_driver(world)`

driver 内の16公開関数は monkeypatch しない。

確認内容:

- `atomic_apply_set_result` が `OrderControlTvtMpAtomicApplySetResult`
- `final_consistency_validation_set_result` から `final_rank_set_result` まで参照連鎖をたどれる
- Node 結果は1件
- `node_name` は `junction`
- `final_rank_status` は `NO_VISITS_TO_CONFIRM`
- `final_rank_visits` は空
- `order_control_tvt_driver_started_timestep` は現在の `T`
- World 内に `junction` の `OrderControlTvtNodeRankState` が存在
- rank state の `node_name` は `junction`
- `late_car` の参加設定と VOT は維持
- `late_car.link is None` であり、この時点では未出発
- `Node.transfer` による物理通過順はこのテストの確認対象ではない

### 回帰結果

修正対象を含む確認として、次の2ファイルをまとめて実行した。

- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_driver.py`

結果は `56 passed in 14.57s` である。

baseline から atomic apply、driver までの関係テスト一式は `940 passed in 20.22s` である。失敗はない。

### py_compile

次の4ファイルで成功した。

- `uxsim/order_control_tvt_mp_driver.py`
- `uxsim/uxsim.py`
- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`

### 正式サンプル

実行は `python demos_and_examples/example_00en_simple.py` である。

- 1200秒まで正常完走
- exception なし
- completed trips: 735 / 810
- average speed: 11.7 m/s
- total travel time: 119475.0 s
- average travel time: 162.6 s
- average delay: 62.6 s
- delay ratio: 0.385
- total distance traveled: 1632250.0 m

正式サンプルは driver を直接呼ばない。World 属性追加後も従来 UXsim の基本動作を壊していないことを確認する回帰テストである。`git diff --check` は問題なしである。

### 未実装範囲

次は未実装のままである。

- World の各 timestep からの自動起動
- `exec_simulation` への driver 接続
- `Node.transfer` による TVT 順位の物理利用
- actual passage
- actual outcome
- 実時間ベースの事後評価
- 満足評価
- welfare
- 対象外 Node の順位台帳削除

上位 driver 実装だけでは、実際の車両通過順はまだ変わらない。

### 次の再開地点

1. 第4巻と進捗第3巻を Terminal で限定確認する。
2. Python・テスト4ファイルの変更範囲を確認する。
3. `git diff --check` を実行する。
4. 文書、実装、テストを同一保存単位で commit する。
5. commit 名に `document` を含める。
6. commit と push を分離する。
7. 保存後、World から driver を自動起動する接続の設計へ進む。
8. `Node.transfer` による物理通過接続は、その後の別段階とする。

# TVT-MP評価期間・baseline内部余白・実World終了制御

記録日: 2026-09-28

本節は、TVT-MP の評価期間と baseline fork 用の内部余白を分け、実 World だけを評価終了時刻で正式終了する設計の記録である。方式Aを採用する。Python と専用テストは未着手である。属性名 `order_control_tvt_evaluation_end_timestep` は本節で正式名とする。

## 1. 評価期間の定義

評価対象が 10,000 timestep の場合、評価時刻は次である。

```text
T = 0, 1, ..., 9999
```

時刻の個数は 10,000 個である。最終評価時刻 `T = 9999` を含む全評価時刻で、通常どおり TVT-MP 形成を検討する。

終盤だけ次を行う方針は採用しない。

- TVT-MP driver の起動をスキップする
- baseline horizon を短縮する
- baseline 不足の例外を握り潰す
- 最終評価時刻付近の Visit を TVT 形成検討から除外する

## 2. 意思決定窓とbaseline horizonの区別

意思決定窓は次である。

```text
T < baseline_arrival_timestep <= T + 6
```

この `6` は意思決定窓の長さである。

baseline horizon は、全 World baseline fork を何 timestep 先まで進めるかである。意思決定窓とは独立して設定する。30 や 50 などを取り得る。

意思決定窓の `6` を理由に、baseline horizon を `6` へ固定しない。

## 3. horizon + 1の根拠

登録 Visit が 1 件以上ある baseline fork では、次を維持する。

```text
remaining_steps >= baseline_horizon_steps + 1
```

`+1` は、horizon 分の仮想交通計算の後も `fork_W.T` を `fork_W.TSIZE` 未満に保ち、fork 上で `simulation_terminated()` と `Analyzer.basic_analysis()` を実行しないための技術的余白である。

下流境界の観測に、追加で 1 timestep の交通計算が必要という意味ではない。

登録 Visit が 0 件の場合は baseline forward を行わない。既存契約どおり、余白検査も行わない。

## 4. 採用方式

方式Aを採用する。

World を作成する時点で、最終評価時刻において `baseline_horizon_steps + 1` 個の残り時刻数を確保できるよう、内部 `TSIZE` を設定する。最終評価時刻そのものを、残り時刻数の 1 個目に含める。実 World の交通計算は、評価終了時刻より後へ進めない。

評価 timestep 数を `evaluation_timestep_count`、最終評価時刻を `evaluation_end_timestep` とすると、次である。

```text
evaluation_end_timestep = evaluation_timestep_count - 1
```

最終評価時刻から必要な残り時刻数の条件は、次である。

```text
internal_TSIZE - evaluation_end_timestep >= baseline_horizon_steps + 1
```

したがって、内部 `TSIZE` の条件は、次である。

```text
internal_TSIZE >= evaluation_end_timestep + baseline_horizon_steps + 1
```

これを評価 timestep 数で表すと、次と同じである。

```text
internal_TSIZE >= evaluation_timestep_count + baseline_horizon_steps
```

誤解防止:

- 「評価期間より horizon + 1 timestep 長くする」とは書かない
- 評価 timestep 数との比較では、内部 `TSIZE` は baseline horizon 分だけ長い
- 最終評価時刻から数える残り時刻数は `baseline_horizon_steps + 1` 個である
- 最終評価時刻自身を残り時刻数の 1 個目に含める
- 意思決定窓の `6` は、この計算に使用しない
- baseline horizon が 30、50 などに変わっても同じ一般式を使う
- 実 World は評価終了時刻より後へ進めない

10,000 timestep、horizon 50 の例:

```text
evaluation_timestep_count = 10000
evaluation_end_timestep = 9999
baseline_horizon_steps = 50
```

必要条件は、次である。

```text
internal_TSIZE >= 9999 + 50 + 1
internal_TSIZE >= 10050
```

これは、次と同じである。

```text
internal_TSIZE >= 10000 + 50
internal_TSIZE >= 10050
```

`T = 9999` で baseline fork を 50 timestep 進めると、処理後の fork 時刻は次である。

```text
fork_W.T = 9999 + 50 = 10049
```

内部 `TSIZE` が 10,050 なら、次を満たす。

```text
fork_W.T < fork_W.TSIZE
10049 < 10050
```

したがって、fork 上で `simulation_terminated()` と `Analyzer.basic_analysis()` は実行されない。

不足境界:

内部 `TSIZE` が 10,049 の場合は不足である。

```text
internal_TSIZE - evaluation_end_timestep = 10049 - 9999 = 50
```

必要な残り時刻数は 51 個なので、次の必要条件を満たさない。

```text
50 >= 51  （不成立）
```

この場合は、既存契約どおり baseline 開始前に `ValueError` とする。

実 World の交通計算は `T = 9999` までである。`T = 9999` の処理後、実 World の `T` は `10000` である。`T = 10000` 以降の実 World 交通計算は行わない。

方式B、つまり実 World の `TSIZE` を評価期間ちょうどにし、`World.copy()` の後で fork だけ期間と配列を延長する方式は採用しない。

## 5. 評価終了時刻

World へ、最後に評価対象として交通計算と TVT-MP 形成検討を行う時刻を保存する。

正式属性名:

```text
order_control_tvt_evaluation_end_timestep
```

初期値は `None` である。`None` の場合は、従来 UXsim の `TSIZE` による終了契約を使う。対象 Node が 0 件でも、この属性が `None` なら従来どおり最後の内部時刻まで実行する。

設定する場合の値は次を満たす。

- Python の `int`
- `bool` 不可
- `0` 以上
- `TSIZE` 未満
- baseline horizon と内部 `TSIZE` の余白条件を満たす

`TSIZE` は `finalize_scenario()` で初めて決まる。`TSIZE` 未満であることと、余白条件は `World.__init__` では検査しない。`exec_simulation()` の開始時に検査する。余白条件は次である。

```text
TSIZE - order_control_tvt_evaluation_end_timestep >= baseline_horizon_steps + 1
```

不足は baseline の例外を隠さず、交通計算の前に `ValueError` とする。horizon を実行前に変えた場合も、その時点の horizon で検査する。

10,000 timestep 評価の値は `9999` である。10 timestep 評価の値は `9` である。

この属性は次で共通利用する。

- 実 World の交通計算終了
- TVT-MP driver の自動起動範囲
- 将来の actual outcome 未観測判定

baseline horizon とは別設定である。`TMAX` は秒、`TSIZE` は内部に処理可能な時刻数、この属性は最後に評価する時刻番号である。処理後の `World.T = 10000` は、最後に評価した時刻 `9999` そのものではない。

自動起動は、`T` がこの値以下の時刻で driver を呼ぶ。`T = 9999` も含む。

## 6. exec_simulationの終了制御

評価終了時刻が設定されている実 World では、次とする。

- `T` が評価終了時刻以下なら交通計算を行う
- 最終評価時刻も処理する
- 処理後、`World.T` は評価終了時刻 `+ 1` となる
- その時点で `simulation_terminated()` を一度だけ呼ぶ
- `Analyzer.basic_analysis()` も一度だけ実行する
- 以後、`exec_simulation()` を呼んでも交通計算を再開しない
- 内部余白期間へ実 World を進めない
- `check_simulation_ongoing()` は `False` を返す

専用の終了済み flag は追加しない。`World.finalized` はシナリオ準備済みを表す既存属性であり、評価終了済みには使わない。

評価終了済みの条件は次である。

```text
World.T > order_control_tvt_evaluation_end_timestep
```

10,000 timestep 評価では、`T = 9999` はまだこの条件を満たさないので処理する。処理後の `T = 10000` で条件を満たす。その後の `exec_simulation()` は、交通計算も終了集計も再度行わない。

評価終了より前の途中停止では終了集計しない。その後、最終評価時刻まで再開できる。

引数なしの `exec_simulation()` でも、要求終了が最終評価時刻より後でも、実 World の交通計算は最終評価時刻で打ち切る。`T` も `TSIZE` も、この打ち切りのために変更しない。

評価終了時刻が `None` なら、従来の `TSIZE` 終了処理を維持する。`T == TSIZE` のときだけ `simulation_terminated()` を呼ぶ既存契約は、この場合に残す。評価終了と `TSIZE` 終了が同時に真になる場合も、終了集計は 1 回だけにする。

`check_simulation_ongoing()` を更新するのは、`while` で区切って `exec_simulation()` を呼ぶ既存の使い方が、内部余白へ進まずに終われるようにするためである。

## 7. baseline forkの扱い

`World.copy()` は評価終了時刻属性も fork へコピーする。そのままでは fork も実 World の評価終了時刻で停止し、horizon の先へ進めない。停止時に fork 上の終了集計も走ってしまう。

baseline fork の複製直後に、fork 側だけ次とする。

```text
fork_W.order_control_tvt_evaluation_end_timestep = None
```

これにより次となる。

- 実 World は評価終了時刻で停止する
- fork は内部 `TSIZE` を使って horizon 全体を仮想計算する
- fork 上では従来の `TSIZE` 終了契約を使う
- baseline の `horizon + 1` 契約を維持する
- fork 上で終了集計を実行しない
- 実 World には影響しない

例として、`T = 9999`、horizon 50、内部 `TSIZE = 10050` の fork は 50 timestep 進み、処理後の `fork_W.T` は `10049` である。`10049 < 10050` なので、fork では `simulation_terminated()` を呼ばない。

fork 専用の `exec_simulation` 引数は追加しない。fork 実行中であることを示す既存の collector も、この停止判定には使わない。

この代入は、終盤だけ horizon を縮める処理ではない。余白不足の `ValueError` を消す処理でもない。

## 8. Analyzerと未完了Vehicle

評価終了時点の既存状態で `basic_analysis()` を実行する。新しい集計関数は作らない。呼び方は、処理後の `T` が評価終了時刻の次になったとき、既存の `simulation_terminated()` を 1 回呼ぶことである。

集計の扱い:

- 完了 Vehicle は完了 trip として集計する
- 未完了 Vehicle は完了 trip、旅行時間、遅延へ含めない
- 未完了 Vehicle を強制的に完了扱いにしない
- 評価終了後の到着時刻を補完しない
- 総走行距離など、既存基本集計が未完了 Vehicle を含む項目は既存契約を維持する

完了は、既存どおり `travel_time != -1` の Vehicle である。走行中、出発待ち、未出発は未完了のままである。中断 Vehicle の `travel_time` は `-1` なので完了に含めない。

総走行距離には未完了 Vehicle も含む。走行中は、その時点のリンク内位置も距離に入る。これは通常 UXsim の既存契約である。

評価終了後の内部余白は、実 World では未実行なので基本集計へ含めない。`basic_analysis()` は Vehicle の状態を見るため、未実行時刻の交通結果は基本集計へ混ざらない。

初回の OD 集計で `flag_od_analysis` が立つ。終了集計を再度呼んでも、旅行時間などの数値は再計算されない。`exec_simulation()` の経路では、評価終了後に `simulation_terminated()` を再呼び出ししない。

## 9. 研究出力の集計範囲

時間に沿って集計する研究出力は、評価期間だけを対象とする。

10,000 timestep 評価なら、対象は次である。

```text
T = 0, 1, ..., 9999
```

内部余白を研究結果へ含めない。

リンク旅行時間、流量、密度、速度などを将来使用する場合も、`TMAX` または内部 `TSIZE` 全体ではなく、評価期間へ限定する。

今回はリンク分析の範囲制御を実装しない。評価結果として使用する分析を、内部余白全体へ無条件に適用しない。

基本集計、その表示、OD 集計は評価終了時点の Vehicle 状態から得る。`link_analysis_coarse()`、累積配列を `TSIZE` 全体から読む処理、`TMAX` 全体の図は、長い内部期間のまま評価結果として使わない。`traveltime_actual` は内部 `TSIZE` 全体を初期値で持ち、未実行部分まで値が入ることがある。Edie 行列も `TMAX` 全体の大きさであり、車両軌跡がない後半は評価期間の観測ではない。

## 10. actual outcome未観測

`T = 9999` で成立または確定した TVT 結果は正式に記録する。

ただし、評価終了までに actual passage が判明しない場合は、次として扱う。

- 取引失敗ではない
- 事後不成立ではない
- 時間節約 0 ではない
- 実績遅延 0 ではない
- actual outcome 未観測

正式支払額、正式補償額、成立時履歴は残す。

未観測の場合は、実績時間節約、実績遅延、実績利得、満足評価を計算しない。

具体的な型名、field 名、status 名は actual outcome 実装時に決める。未観測の境界は `order_control_tvt_evaluation_end_timestep` より後である。処理後の `World.T` だけを、最後に観測した時刻とみなさない。

## 11. 維持する既存契約

次は維持する。

- baseline horizon を短縮しない
- `remaining_steps >= horizon + 1`
- fork 終了時は `fork_W.T < fork_W.TSIZE`
- fork 上で `simulation_terminated` と Analyzer を呼ばない
- Visit 0 件時の baseline forward 省略
- baseline 不足 `ValueError`
- 意思決定窓の `6` と baseline horizon を分離する
- `Node.transfer` の物理通過順は今回変更しない

## 12. 研究上の説明

対外的には、次のように区別する。

- 評価期間は 10,000 timestep である
- 評価時刻は `T = 0` から `9999` である
- 全評価時刻で TVT-MP 形成を検討する
- 最終評価時刻でも完全な baseline horizon を使う
- 内部 World には baseline 用の計算余白を持つ
- 実 World の交通観測は評価期間終了時点で打ち切る
- 評価終了後の車両結果は未観測である

内部 `TSIZE` が 10,000 より長くても、TVT-MP の評価期間は 10,000 timestep である。

## 13. 実装予定範囲

次の設計・実装段階で扱う。

- World 属性の追加
- `exec_simulation` の評価終了制御
- `check_simulation_ongoing` の評価終了制御
- 評価終了時の `simulation_terminated` 一回呼出し
- baseline fork 複製直後の評価終了制限解除
- TVT-MP driver の時刻ループ先頭での自動起動
- 専用テスト

今回まだ扱わない。

- `Node.transfer` による TVT 順位の物理利用
- actual passage
- actual outcome
- 満足評価
- welfare
- リンク分析の評価期間限定実装

## 14. 次の再開地点

1. 本節を Terminal で分割確認する。
2. 進捗第3巻へ短い要約を追記する。
3. `git diff --check` と変更ファイルを確認する。
4. 文書を commit する。
5. commit 名に `document` を含める。
6. commit と push を分離する。
7. 保存後、自動起動・評価終了制御の完全実装前仕様を作る。
8. その後に Python と専用テストを実装する。

# TVT-MP自動起動・評価終了制御・fork制限解除 完全実装前仕様

記録日: 2026-09-28

本節は完全実装前仕様である。Python と専用テストは未着手である。評価期間と内部余白の確定設計は、同じ第4巻の「TVT-MP評価期間・baseline内部余白・実World終了制御」を参照する。上位 driver の既存契約は「TVT-MP上位driver・完全実装前仕様」を参照する。本節は、その driver を時刻ループから一度だけ起動し、実 World を評価終了時刻で止め、baseline fork だけは horizon 全体を計算できるようにする。

本節について、利用者判断が必要な事項は残っていない。

## 1. 目的と実装範囲

評価対象が 10,000 timestep なら、`T = 0` から `9999` までの全時刻で TVT-MP 形成を通常どおり検討する。実 World の交通計算は `T = 9999` までである。処理後の `World.T` は `10000` である。`T = 10000` 以降の実 World 交通計算は行わない。

`T = 9999` の TVT 判断に使う baseline fork は、設定された baseline horizon 全体を計算できなければならない。内部 World にはその余白を確保する。fork 側だけ評価終了制限を外す。

今回の実装範囲:

- `order_control_tvt_evaluation_end_timestep` の初期化
- その値の型と `TSIZE` の検査
- 対象 Node が 1 件以上のときの内部余白検査
- `exec_simulation` の各処理時刻の先頭での driver 自動起動
- 実 World の評価終了制御
- `check_simulation_ongoing` の評価終了制御
- 評価終了時の `simulation_terminated()` 一回呼出し
- baseline fork 複製直後の評価終了制限解除
- 専用テスト

今回実装しないものは §24 に書く。`Node.transfer` による TVT 順位の物理利用は行わない。

## 2. 正式属性

正式属性名は `order_control_tvt_evaluation_end_timestep` である。

`World.__init__` の初期値は `None` である。既存の TVT 属性の並びに追加する。driver は属性の初回作成をしない。

意味:

- 最後に実 World の交通計算を行う時刻番号
- 最後に TVT-MP 形成を検討する時刻番号
- 10,000 timestep 評価なら `9999`
- 10 timestep 評価なら `9`
- `None` なら従来 UXsim の `TSIZE` 終了契約を使う。driver も自動起動しない

この属性は baseline horizon とは別である。`TMAX` は秒、`TSIZE` は内部に処理可能な時刻数、この属性は最後に評価する時刻番号である。

処理後の `World.T = 10000` は、最後に評価した時刻 `9999` そのものではない。

## 3. 設定値検査

`World.__init__` では `TSIZE` が未確定なので、ここでは検査しない。

`exec_simulation()` は、`finalize_scenario()` の後、交通計算の前に検査する。属性が `None` なら検査しない。

`None` 以外の有効値:

- `type(value) is int` である。`isinstance` は使わない。`bool` は不可である
- `0` 以上
- `TSIZE` 未満

不正なら `ValueError` とする。交通計算も driver も始めない。別例外で包まない。

`TSIZE` 以上を許すと、最終評価時刻が内部の処理可能範囲の外になる。`TSIZE - 1` は、余白条件を別に満たすなら型と範囲としては有効である。

## 4. 自動起動条件

自動起動の条件は、`order_control_tvt_evaluation_end_timestep` が `None` でないことだけである。

- `None` なら driver を呼ばない。従来の `exec_simulation()` のままである。公式サンプルと、この属性を設定しない既存テストはここを通る
- `None` でないなら、処理する各時刻で `run_tvt_mp_driver(W)` を 1 回呼ぶ
- 対象 Node が 0 件でも呼ぶ。no-op は driver 側の既存契約に任せる
- `uxsim.py` で対象 Node を再収集しない
- 自動起動の専用 flag は追加しない

この属性が未設定の World で、TVT 対象 Node があっても自動起動しない。その場合の driver 実行は、既存どおり手動呼出しである。評価実験で自動起動する World は、この属性を設定する。

## 5. driver呼出し位置

呼出し位置は、`exec_simulation()` の時刻ループに入った直後、`T == 0` の進捗見出しより前、最初の `Link.update()` より前である。

この位置である理由は、baseline fork が `World.copy()` の後に自分の `exec_simulation()` を `Link.update()` から始めるためである。実 World が先に `Link.update()` すると、fork 側で累積台数が二重に追加される。

順序:

1. `run_tvt_mp_driver(W)` を 1 回
2. 既存の `T == 0` 見出しと進捗表示
3. `Link.update()`
4. `Node.generate()` と `Node.update()`
5. `Node.transfer()`
6. `Vehicle.update()`
7. 経路更新
8. `World.user_function`

要件:

- 1 timestep につき 1 回
- 全 TVT 対象 Node を driver の 1 回で処理する。Node ごとに呼ばない
- `T = 0` でも呼ぶ
- 最終評価時刻でも呼ぶ
- 16 段の呼出しを `exec_simulation()` へ複製しない
- driver 例外のときは、その時刻の見出し表示も交通計算も始めない
- 例外を警告や fallback に変えない

`World.user_function` は車両移動の後なので、同じ時刻の TVT 判断には使わない。

## 6. 循環import回避

`uxsim.py` の先頭では driver を import しない。

`order_control_tvt_mp_driver.py` は実行時に `uxsim.uxsim` の `World` と `Vehicle` を `isinstance` で使う。`uxsim.py` の読込み中に driver を import すると、driver が読込み途中の `uxsim.uxsim` を import する循環になる。

正式方式は、`exec_simulation()` の中で、評価終了時刻が有効であり、まだ評価終了済みでないときだけ、時刻ループの前に 1 回だけ局所 import することである。

```text
from uxsim.order_control_tvt_mp_driver import run_tvt_mp_driver
```

この時点では `uxsim.py` の読込みは終わっている。import を時刻ループの中には置かない。評価終了時刻が `None` の実行では import しない。

driver 側の `World` と `Vehicle` の import は `TYPE_CHECKING` に移さない。実行時の型検査に必要である。接続専用の新しい helper ファイルは作らない。

## 7. exec_simulation終了制御

評価終了時刻が `None` のときは、既存の `end_ts` 計算、`T == TSIZE` の終了、再呼出し時の終了集計を変更しない。

評価終了時刻が有効なときの順序は次である。

1. 未確定なら `finalize_scenario()` を呼ぶ。
2. §3 の検査を行う。
3. `World.T > order_control_tvt_evaluation_end_timestep` なら、交通計算も `simulation_terminated()` も行わず、戻り値 `1` で戻る。
4. 既存どおり `until_t`、`duration_t2`、`duration_t`、引数なしから `end_ts` を決める。`end_ts > TSIZE` なら `TSIZE` に制限する既存処理は残す。
5. `end_ts` が評価終了時刻より大きいときは、評価終了時刻まで切り詰める。最終評価時刻は含む。
6. 切り詰め後に `end_ts < start_ts` なら、既存の `Exception` をそのまま使う。これは評価終了後の再呼出しではない。
7. 時刻ループを実行する。各時刻の先頭で §5 の driver を呼ぶ。
8. 既存どおりループ後に `World.T` を 1 進める。`T`、`TSIZE`、`TMAX` を評価終了のために書き換えない。
9. `World.T == TSIZE` なら、既存どおり `simulation_terminated()` を 1 回呼び、`1` を返す。
10. そうでなく `World.T == order_control_tvt_evaluation_end_timestep + 1` なら、`simulation_terminated()` を 1 回呼び、`1` を返す。
11. どちらでもなければ `0` を返す。終了集計はしない。

`TSIZE` 終了と評価終了が同じ呼出しで両方真になるときは、手順 9 だけが終了集計を呼ぶ。手順 10 は実行しない。集計は 1 回である。

終了後の再呼出しは手順 3 で戻る。成功を表す既存の終了コード `1` であり、例外にしない。内部 `TSIZE` へ到達していなくても、評価終了として扱う。

専用の終了済み flag は追加しない。`World.finalized` はシナリオ準備済みであり、評価終了済みには使わない。評価終了済みは次だけである。

```text
order_control_tvt_evaluation_end_timestep is not None
かつ
World.T > order_control_tvt_evaluation_end_timestep
```

既存引数の境界は、`DELTAT = 1` 秒、開始 `T = 0`、評価終了時刻 `9` で次のとおりである。

- 引数なし: 内部 `TSIZE` まで進まず、`T = 0` から `9` まで処理し、処理後は `T = 10` で終了集計する
- `until_t = 9`: `end_ts = 9` なので、同じく `T = 9` まで処理して終了集計する
- `until_t = 100`: いったん `end_ts = 100` になるが、評価終了時刻 `9` へ切り詰め、同じ終了になる
- `duration_t2 = 5`: 既存式の最終時刻は `4` である。`4` は評価終了時刻以下なので切り詰めない。処理後は `T = 5` であり、終了集計しない
- `duration_t`: 既存の古い式を維持したうえで、その `end_ts` が評価終了時刻を超えるときだけ切り詰める。`duration_t` と `duration_t2` の 1 時刻差は、今回埋めない

## 8. check_simulation_ongoing

`finalized == 0` のときは、既存どおり `True` を返す。

`finalized` 後に、評価終了時刻が `None` でないときは、その値が §3 の有効値でなければ `ValueError` とする。有効であり `World.T` が評価終了時刻より大きいときは `False` を返す。

それ以外は既存どおり `World.T <= TSIZE - 1` である。

したがって:

- `T = evaluation_end_timestep` では `True` である。最終評価時刻はまだ処理できる
- 処理後の `T = evaluation_end_timestep + 1` では `False` である
- `T` が `TSIZE` 以上なら、評価終了時刻が `None` でも既存どおり `False` である
- `while W.check_simulation_ongoing()` で `exec_simulation()` を分割しても、評価終了の次の時刻でループを抜ける

baseline fork は §10 でこの属性を `None` に戻す。fork 上の `check_simulation_ongoing()` は従来の `TSIZE` 判定だけになる。

## 9. 終了集計

評価終了へ到達した実 World では、既存の `simulation_terminated()` を 1 回だけ呼ぶ。この関数は表示の後に既存の `Analyzer.basic_analysis()` を呼ぶ。新しい集計関数は作らない。

終了後の `exec_simulation()` は、交通計算も `simulation_terminated()` も再度行わない。

`basic_analysis()` の初回は `flag_od_analysis` を立てる。仮に終了処理を重ねて呼んでも旅行時間などは再計算されないが、自動起動側はその重ね呼びをしない。

評価終了時刻が `None` で `T == TSIZE` になった既存経路は、現行 UXsim のとおり再呼出し時にも `simulation_terminated()` を呼ぶ。この既存動作は、属性が `None` のときだけ残す。

## 10. baseline fork制限解除

`World.copy()` は `order_control_tvt_evaluation_end_timestep` も fork へ写す。写したままでは、fork の `exec_simulation()` も実 World の評価終了時刻で止まり、その直後に fork 上の終了集計が走る。

解除場所は `order_control_baseline_driver.py` の `_prepare_baseline_fork()` である。`fork_W = real_W.copy()` の直後、`_validate_copied_fork()` より前、collector 接続より前、downstream observer 接続より前、baseline forward より前に、fork 側へ直接代入する。

```text
fork_W.order_control_tvt_evaluation_end_timestep = None
```

private helper は作らない。この 1 代入で足りる。

結果:

- `real_W` の属性は変わらない。pickle の複製だからである
- fork は従来の `TSIZE` 終了契約に戻る
- horizon は短縮しない
- 登録 Visit が 1 件以上のとき、`remaining_steps >= baseline_horizon_steps + 1` は維持する
- forward 後も `fork_W.T < fork_W.TSIZE` を維持する
- fork 上で `simulation_terminated()` と `Analyzer.basic_analysis()` を呼ばない
- 登録 Visit が 0 件のときは、既存どおり forward しない。余白検査もしない。代入だけは行う

例として、`T = 9999`、horizon 50、内部 `TSIZE = 10050` の fork は 50 timestep 進み、処理後の `fork_W.T` は `10049` である。`10049 < 10050` なので fork は終了集計しない。

fork 専用の `exec_simulation` 引数は追加しない。collector の有無で停止を判定しない。

代入そのものに新しい例外は作らない。すでに `None` でも `None` を代入するだけである。例外を握り潰さない、とは、この代入の周りで baseline の `ValueError` や `RuntimeError` を捕まえないという意味である。

## 11. 対象Node 0件

対象 Node の収集は、既存の `run_tvt_mp_driver()` だけが行う。

自動起動で driver が呼ばれ、対象 Node が 0 件なら、既存どおり完全 no-op である。World、順位台帳、Vehicle、driver 開始時刻を変更しない。同じ `T` で再び呼ばれても no-op である。

この経路では共通設定も内部余白も検査しない。評価終了時刻が設定されていても、対象 Node が 0 件なら horizon の長さを要求しない。交通計算の停止だけが有効になる。

対象 Node が 1 件以上の既存契約、つまり同一 `T` の拒否、時刻逆行の拒否、開始時刻の記録、16 段と atomic apply は変更しない。

自動起動がその時刻で driver を呼んだ後に、同じ実 World の同じ `T` で手動でもう一度呼ぶと、対象 Node が 1 件以上なら既存の `RuntimeError` になる。自動起動は 1 時刻に 1 回しか呼ばない。

## 12. driver例外

`exec_simulation()` は driver の例外を捕まえない。警告にしない。fallback しない。別例外で包まない。

driver が例外を出した時刻では、進捗見出し、`Link.update()`、`Node.generate()`、`Node.transfer()`、`Vehicle.update()` へ進まない。それより前の時刻で確定した状態は、既存の driver 契約のとおり残る。開始時刻を戻さない。

## 13. 分割exec_simulation

評価終了時刻より前で `until_t`、`duration_t`、`duration_t2` により止めたときは、終了集計しない。`check_simulation_ongoing()` は `True` のままなので、続きを実行できる。

続きの開始 `T` が評価終了時刻以下なら、その時刻でも driver を 1 回呼ぶ。同じ `T` を二度処理しない既存の時刻の進み方は維持する。

最終評価時刻を処理し終えて `World.T` が評価終了時刻の次になった呼出しだけが、終了集計を 1 回行う。その後の呼出しは §7 の手順 3 で止まる。

`while W.check_simulation_ongoing()` の分割実行は、評価終了の次の時刻で条件が `False` になり終了する。内部余白へは進まない。

## 14. baseline余白条件

最終評価時刻の残り時刻数は、同じ第4巻の採用方式のとおり次である。

```text
internal_TSIZE - evaluation_end_timestep >= baseline_horizon_steps + 1
```

同値の条件:

```text
internal_TSIZE >= evaluation_end_timestep + baseline_horizon_steps + 1
internal_TSIZE >= evaluation_timestep_count + baseline_horizon_steps
```

`evaluation_end_timestep = evaluation_timestep_count - 1` である。最終評価時刻自身を残り時刻数の 1 個目に含める。意思決定窓の `6` はこの式に使わない。horizon が 30 や 50 でも式は同じである。

10,000 timestep、horizon 50:

- `evaluation_timestep_count = 10000`
- `evaluation_end_timestep = 9999`
- `internal_TSIZE >= 10050`
- `internal_TSIZE = 10049` は不足である。残り時刻数は `10049 - 9999 = 50` であり、必要な 51 を満たさない
- `internal_TSIZE = 10050` なら十分である。`fork_W.T = 10049` となり `10049 < 10050` である

検査の分担:

- 型、`bool`、`0` 以上、`TSIZE` 未満は、`exec_simulation()` が属性を使う前に検査する。対象 Node の有無では分けない。停止位置そのものの検査だからである
- horizon に対する内部余白は、driver の `_require_common_settings()` に追加する。対象 Node が 1 件以上で、ここまで進んだときだけである。属性が `None` なら、この新しい余白検査はしない
- 既存の horizon 検査、候補 Visit 数上限の検査の後に余白を検査する。先に出た `ValueError` を、余白の例外で置き換えない
- 開始時刻を記録する前に検査する。不足なら開始時刻は変わらない
- baseline driver の `remaining_steps >= baseline_horizon_steps + 1` は削除しない。fork 側の契約として残す。driver の事前検査が成功しても、fork 側が不足なら既存の `ValueError` がそのまま出る。握り潰さない

余白検査を `exec_simulation()` へ置かない。対象 Node が 0 件の World に horizon 余白を強制せず、対象 Node の収集を `uxsim.py` へ複製しないためである。

不足は、確定済み World の `TSIZE` を実行中に伸ばして解消しない。`finalize_scenario()` は確定後の `TMAX` を伸ばさない。World を作り直す。

属性が有効なのに型不正のまま driver を手動で呼んだ場合も、対象 Node が 1 件以上なら、同じ余白検査の前に §3 と同じ条件で `ValueError` とする。手動呼出しは `exec_simulation()` の検査を通らないためである。条件は §3 と別にしない。

## 15. Analyzerと未完了Vehicle

評価終了時の `basic_analysis()` は、その時点の既存 Vehicle 状態を使う。

- 完了 Vehicle だけを完了 trip、旅行時間、遅延へ含める
- 未完了 Vehicle は未完了のままである。`travel_time != -1` にしない
- 将来の到着結果を補完しない
- 総走行距離など、既存基本集計が未完了 Vehicle を含む項目は既存契約のままである
- 内部余白は実 World では未実行なので、基本集計へ含めない

リンク配列全体、累積配列全体、`TMAX` 全体を読む分析の評価期間限定は、今回実装しない。それらを内部余白全体へ無条件に適用して、評価結果としない。

## 16. actual outcome未観測との将来接続

今回は actual outcome を実装しない。型名、field 名、status 名は決めない。

将来、`order_control_tvt_evaluation_end_timestep` より後を未観測の境界に使える。評価終了までに actual passage が記録されていない TVT 結果は、次として扱う。

- 取引失敗ではない
- 事後不成立ではない
- 時間節約 0 ではない
- 実績遅延 0 ではない
- actual outcome 未観測

正式支払額、正式補償額、成立時履歴は残す。未観測の場合は、実績時間節約、実績遅延、実績利得、満足評価を計算しない。

`T = 9999` で成立または確定した結果自体は残す。処理後の `World.T = 10000` を、最後に観測した時刻とみなさない。

## 17. live状態の変更範囲

変更する live 状態:

- `World.__init__` が `order_control_tvt_evaluation_end_timestep = None` を持つ
- 評価終了へ到達した実 World は、既存の `simulation_terminated()` により Analyzer の基本集計を 1 回持つ
- fork は複製直後に、自分の `order_control_tvt_evaluation_end_timestep` だけを `None` にする
- 対象 Node が 1 件以上の driver は、既存契約どおり開始時刻、順位台帳、atomic apply の対象状態を更新できる

変更しない live 状態:

- 評価終了のために `T`、`TIME`、`TSIZE`、`TMAX`、`finalized` を書き換えない。`T` は既存ループの +1 だけで進む
- 対象 Node 0 件の no-op は、既存どおり World、順位台帳、Vehicle、開始時刻を変えない
- `real_W` の評価終了時刻を、fork 解除で変えない
- `Node.transfer` の通過処理を変えない

## 18. 不変性

次は維持する。

- 上位 driver の公開関数は `run_tvt_mp_driver(real_W)` のままである
- 成功結果型と field は変更しない
- 16 段の順序と引数は変更しない
- 対象 Node 0 件の完全 no-op は変更しない
- 対象 Node が 1 件以上の同一 `T` 拒否、時刻逆行拒否、開始時刻を戻さない契約は変更しない
- baseline の `remaining_steps >= baseline_horizon_steps + 1` は変更しない
- Visit 0 件の forward 省略は変更しない
- fork 上で終了集計しない契約は変更しない
- 意思決定窓の `6` と baseline horizon は独立のままである
- 評価終了時刻が `None` の `exec_simulation()` と `check_simulation_ongoing()` は従来動作のままである

## 19. 例外境界

| 状態 | 例外 |
| --- | --- |
| 評価終了時刻の型が `int` でない | `ValueError` |
| `bool` | `ValueError` |
| 負数 | `ValueError` |
| `TSIZE` 以上 | `ValueError` |
| 対象 Node が 1 件以上で、最終評価時刻の残り時刻数が `baseline_horizon_steps + 1` 未満 | `ValueError` |
| 評価終了後の `exec_simulation()` 再呼出し | 例外にしない。戻り値 `1` |
| 評価終了前の不正な短い `until_t` や `duration_t` | 既存の `Exception` を維持する |
| driver の `ValueError` または `RuntimeError` | 包まずそのまま伝播する |
| fork 側の属性を `None` にする代入 | 新しい例外を作らない |
| baseline の余白不足 | 既存の `ValueError` を握り潰さない |

`exec_simulation()` は、これらの例外を別の型へ包まない。

## 20. 可読性

- 時刻ループの先頭で、driver を 1 行で呼ぶ
- 終了済み判定は、`exec_simulation()` と `check_simulation_ongoing()` が同じ条件を使う。条件式をそれぞれ別の意味にしない
- 16 段は driver の外へ複製しない
- 動的な関数リスト、`getattr`、decorator で段をつなげない
- 終了状態の機械は作らない。終了済み flag も追加しない
- fork の解除は直接代入 1 行である
- コメントは、最終評価時刻を処理に含めること、終了後の `T` がその次であること、fork だけ制限を外す理由に限る

## 21. 専用テスト契約

新規専用テストは `tests_order_control_tvt_mp_evaluation_end.py` とする。本番コードへテスト専用 flag や callback は追加しない。呼出し回数は、テスト側の monkeypatch で数えてよい。

最低限、次を固定する。

- 初期値は `None` である
- `bool`、負数、`TSIZE` 以上は `ValueError` である
- 10 timestep 評価では `T = 0` から `9` を処理する
- 停止後の `T` は `10` である
- `T = 9` でも driver を 1 回呼ぶ
- `T = 10` 以降の交通計算をしない
- 終了後の再実行で交通計算しない
- 終了集計を再度呼ばない
- 終了後の `check_simulation_ongoing()` は `False` である
- `T = 9` の時点では `check_simulation_ongoing()` は `True` である
- 評価終了より前の途中停止では終了集計せず、その後再開できる
- `T = 0` でも driver を呼ぶ
- 1 timestep につき driver 1 回である
- TVT 対象 Node が複数でも driver は 1 回である
- driver は `Link.update()` と `Node.transfer()` より前である
- driver 例外の時刻は交通計算しない
- baseline fork の評価終了時刻は `None` である
- `real_W` の評価終了時刻は fork 作成後も変わらない
- fork は評価終了時刻を越えて horizon 全体を計算する
- fork 上で `simulation_terminated()` と `basic_analysis()` を呼ばない
- horizon 30 または 50 で、意思決定窓の `6` とは別の値として forward する
- `internal_TSIZE` が必要下限なら成功する
- 必要下限より 1 小さいときは `ValueError` である
- 登録 Visit が 0 件のときは既存どおり forward しない
- 評価終了時刻が `None` なら、従来どおり `TSIZE` まで進み得る
- 完了 Vehicle だけが完了 trip と旅行時間に入る
- 未完了 Vehicle は完了 trip に入らない
- `Node.transfer` は TVT 順位をまだ物理利用しない

10,000 timestep の実シミュレーションは専用テストの必須実行にしない。10 timestep と、horizon 30 または 50 の小さい World で同じ式を固定する。`9999`、`10049`、`10050` の数値例は第4巻の契約として維持する。

## 22. 既存回帰

評価終了時刻の初期値が `None` なので、次は従来動作のままである。

- 既存の driver 専用テスト
- 既存の baseline driver テスト
- 既存の `exec_simulation()` テスト
- 公式サンプル `demos_and_examples/example_00en_simple.py`

既存テストファイルは、今回の契約と衝突しない限り変更しない。新しい期待は新規専用テストへ置く。

公式サンプルは driver を自動起動しない。完了 trip 数、平均速度、旅行時間、遅延、走行距離が従来と一致することを実装時の回帰とする。

## 23. 実装対象ファイル

変更するファイル:

- `uxsim/uxsim.py`
  - `World.__init__` の属性追加
  - `exec_simulation()` の検査、局所 import、自動起動、終了制御
  - `check_simulation_ongoing()` の評価終了判定
- `uxsim/order_control_tvt_mp_driver.py`
  - 対象 Node が 1 件以上で評価終了時刻が `None` でないときの余白検査だけ
  - 16 段の呼出し順は変更しない
- `uxsim/order_control_baseline_driver.py`
  - fork 複製直後の直接代入 1 行
- `tests_order_control_tvt_mp_evaluation_end.py`
  - 新規

変更しないファイル:

- `uxsim/analyzer.py`
- `Node.transfer`
- 既存の driver 専用テストと baseline 専用テスト。衝突がない限り
- 詳細設計の旧巻
- `diagnostics/order_control.zip`

実装後の記録は、詳細設計第4巻の本節の続きと、進捗第3巻の短い要約で行う。実装前の今回は、進捗第3巻を変更しない。

## 24. 未実装範囲

次は今回実装しない。

- `Node.transfer` による TVT 順位の物理利用
- actual passage
- actual outcome
- 実績評価
- 満足評価
- welfare
- リンク分析の評価期間限定
- 対象外 Node の順位台帳削除

`time_value` の物理通過は、今回の後も従来の合流処理のままである。

## 25. 採用しない方向

- 終盤だけ driver をスキップする
- 終盤だけ horizon を短縮する
- baseline 不足の `ValueError` を握り潰す
- 最終評価時刻付近の Visit を TVT 検討から除外する
- 実 World を内部余白まで進める
- 評価期間より horizon + 1 timestep 長い、と内部 `TSIZE` を説明する
- 評価 timestep 数に horizon + 1 を足した値を内部 `TSIZE` にする
- 意思決定窓の `6` を内部余白の計算に使う
- 終了済み専用 flag を追加する
- `World.finalized` を終了済みの意味に使う
- `uxsim.py` の先頭で driver を import する
- `uxsim.py` で対象 Node を再収集する
- 自動起動用の別設定を追加する
- 16 段を `exec_simulation()` へ複製する
- fork 専用の `exec_simulation` 引数を追加する
- `World.copy()` の後に fork の `TSIZE` や期間配列を伸ばす
- 未完了 Vehicle を完了扱いにする
- 評価終了後の到着時刻を補完する
- actual outcome の未観測を、失敗、事後不成立、時間節約 0、実績遅延 0 とする

## 26. 未確定事項

利用者判断が必要な事項は残っていない。

actual outcome の型名、field 名、status 名は、本節では意図して決めない。未実装範囲であり、本節の未確定事項にはしない。

## 27. 次の再開地点

1. 本節を Terminal で分割確認する。
2. 進捗第3巻へ短い要約を追記する。
3. `git diff --check` と変更ファイルを確認する。
4. 文書を commit する。
5. commit 名に `document` を含める。
6. commit と push を分離する。
7. 保存後、本節どおり Python と専用テストを実装する。
8. `Node.transfer` による物理通過接続は、その後の別段階とする。

## 28. 実装・独立確認・検証結果（2026-09-28）

本節は、直前の完全実装前仕様を実装し、Terminal で独立確認した結果である。§1 から §27 は実装前の正式仕様として残す。削除も短縮もしない。

### 実装ファイル

変更した本番ファイル:

- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_driver.py`
- `uxsim/order_control_baseline_driver.py`

新規専用テスト:

- `tests_order_control_tvt_mp_evaluation_end.py`

正式契約へ追随させた既存テスト:

- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`

### World属性

`uxsim/uxsim.py` の `World.__init__` へ次を追加した。

```text
order_control_tvt_evaluation_end_timestep = None
```

意味:

- 最後に実 World の交通計算を行う時刻番号
- 最後に TVT-MP 形成を検討する時刻番号
- 10,000 timestep 評価なら `9999`
- `None` なら従来 UXsim の `TSIZE` 終了契約
- `None` なら driver を自動起動しない

driver は属性を初回作成しない。

### 自動起動条件と位置

評価終了時刻が `None` でない実 World だけで自動起動する。各処理時刻の時刻ループ先頭で、`run_tvt_mp_driver(W)` を 1 回呼ぶ。

呼出し位置は次より前である。

- `T = 0` の進捗見出し
- `Link.update`
- `Node.generate`
- `Node.transfer`
- `Vehicle.update`
- `World.user_function`

`T = 0` と最終評価時刻を含む。複数 TVT 対象 Node でも、driver は 1 時刻に 1 回だけである。対象 Node の収集は driver だけが行う。`uxsim.py` へ対象判定を複製していない。driver の 16 段を `exec_simulation` へ複製していない。

`uxsim.py` のファイル先頭では driver を import していない。評価終了時刻が有効で、まだ終了済みでない実行だけ、`exec_simulation` 内で時刻ループ前に局所 import する。時刻ループ内で毎回 import しない。

### 評価終了制御

`finalize_scenario()` の後、交通計算と driver 起動の前に評価終了時刻を検査する。`None` 以外は、`type(value) is int`、`bool` 不可、`0` 以上、`TSIZE` 未満である。不正は `ValueError` である。不正時は交通計算も driver も始めない。同じ検査 helper を `exec_simulation`、`check_simulation_ongoing`、手動 driver 実行時の余白検査から利用する。

評価終了時刻を含めて交通計算する。10 timestep 評価、評価終了時刻 `9` の場合は、`T = 0` から `9` を処理し、処理後の `World.T` は `10` である。`T = 10` 以降へ進まない。

評価終了済みは、評価終了時刻が `None` でなく、`World.T` が評価終了時刻より大きいことで判断する。専用の終了済み flag は追加していない。評価終了のために `T`、`TIME`、`TSIZE`、`TMAX`、`finalized` は書き換えない。`T` は既存ループの +1 だけで進む。

評価終了時刻が `None` の場合は、従来の `TSIZE` 終了と再呼出し動作を維持する。

### check_simulation_ongoing

`finalized` 前は従来どおり `True` である。評価終了時刻そのものでは `True` である。評価終了時刻の次の時刻では `False` である。評価終了時刻が `None` なら、従来の `TSIZE` 判定だけを使う。

### 終了集計

評価終了到達時に、既存 `simulation_terminated()` を 1 回呼ぶ。その中の `Analyzer.basic_analysis()` も 1 回実行する。

評価終了後に `exec_simulation()` を再度呼んでも、交通計算しない。`simulation_terminated()` を再度呼ばない。`basic_analysis()` を再度呼ばない。`World.T` を進めない。例外にしない。戻り値は `1` である。

### baseline fork制限解除

`uxsim/order_control_baseline_driver.py` の `_prepare_baseline_fork()` で実装した。`fork_W = real_W.copy()` の直後に、fork 側だけ次を代入する。

```text
fork_W.order_control_tvt_evaluation_end_timestep = None
```

配置は `_validate_copied_fork`、collector 接続、downstream observer 接続、baseline forward より前である。`real_W` の評価終了時刻は変わらない。fork は従来の `TSIZE` 終了契約へ戻る。horizon を短縮しない。`remaining_steps >= baseline_horizon_steps + 1` を維持する。`fork_W.T < fork_W.TSIZE` を維持する。fork 上で `simulation_terminated()` と `Analyzer.basic_analysis()` を呼ばない。Visit 0 件時の forward 省略も維持する。

### 内部余白検査

対象 Node が 1 件以上で、評価終了時刻が設定されている場合だけ、上位 driver で事前検査する。検査順は、既存 baseline horizon 検査、既存候補数上限検査、新しい内部余白検査である。

```text
TSIZE - evaluation_end_timestep >= baseline_horizon_steps + 1
```

10 timestep 評価、評価終了時刻 `9`、horizon 30 の場合、`TSIZE = 40` なら成功、`TSIZE = 39` なら不足である。不足は driver 開始時刻記録前の `ValueError` である。不足時、`order_control_tvt_driver_started_timestep` は変わらない。意思決定窓の `6` は余白計算に使わない。baseline driver 側の既存余白検査も残す。

### 対象Node 0件

対象 Node が 0 件の場合は、driver の既存完全 no-op を維持する。World、順位台帳、Vehicle、driver 開始時刻を変更しない。共通設定を検査しない。baseline horizon に対する内部余白を要求しない。`exec_simulation` 側の評価終了時刻の型・範囲検査と、実 World の評価終了制御は有効である。

### driver例外

`exec_simulation` は driver 例外を捕捉しない。警告、fallback、正常結果、別例外へ変換しない。driver 例外が出た時刻では、`Link.update` その他の交通計算へ進まない。driver が記録済みの開始時刻や先行確定は rollback しない。

### 分割実行

評価終了より前の `duration_t2` 等の途中停止では終了集計しない。途中停止後は再開できる。`until_t` が評価終了時刻より後でも、評価終了時刻へ切り詰める。既存の `until_t`、`duration_t2`、`duration_t` の計算式は変更していない。`duration_t` の既存の 1 時刻差も今回変更していない。

### Analyzerと未完了Vehicle

`Analyzer` 本体は変更していない。評価終了時点の既存状態を `basic_analysis` で集計する。完了 Vehicle だけが完了 trip、旅行時間、遅延へ入る。未完了 Vehicle は未完了のままである。将来の到着結果を補完しない。総走行距離等は既存契約のままである。専用テストでは、総 trip 数 2、完了 trip 数 1 を確認した。内部余白は実 World で未実行なので、基本集計へ混ざらない。リンク配列全体を使う分析の評価期間限定は未実装である。

### 新規専用テスト

新規ファイルは `tests_order_control_tvt_mp_evaluation_end.py` である。定義済み test 関数、`TESTS` 登録、pytest 収集はいずれも 22 件である。重複、登録漏れ、未定義参照はない。

直接実行結果は `22 tests passed` である。pytest 結果は `22 passed in 14.20s` である。

記録する主要ケース:

- 属性初期値 `None`
- `None` では driver を自動起動しない
- `None` では従来 `TSIZE` 終了
- `bool`、負数、`TSIZE` 以上を `ValueError`
- 不正値では交通計算も driver も開始しない
- 10 timestep 評価は `T = 0` から `9`
- 処理後 `T = 10`
- `T = 0` と `T = 9` で driver を呼ぶ
- `T = 10` 以降へ進まない
- 終了後の再実行で再集計しない
- 分割実行と再開
- driver は `Link.update` と `Node.transfer` より前
- driver 例外時は交通計算しない
- 対象 Node 0 件では余白不要
- horizon 30 の必要下限と 1 不足
- 意思決定窓 `6` とは独立
- fork 側だけ評価終了制限を解除
- fork は horizon 50 を全量計算
- fork 上で終了集計しない
- Visit 0 件では forward しない
- 完了 Vehicle と未完了 Vehicle を区別
- `Node.transfer` は TVT 順位を物理利用しない

### 既存テスト更新

`tests_order_control_tvt_mp_driver.py` の旧テスト `test_exec_simulation_and_node_transfer_do_not_call_the_driver` は、`test_exec_simulation_connects_driver_but_node_transfer_does_not` へ更新した。今回の正式仕様により、`exec_simulation` は条件付きで `run_tvt_mp_driver` へ接続する。`Node.transfer` は `run_tvt_mp_driver`、`order_control_tvt`、`time_value` を扱わない契約を維持した。

`tests_order_control_tvt_baseline_driver_registration.py` の `test_fork_result_does_not_include_plan_or_rank_ledger_fields` の期待 field 集合へ `downstream_boundary_result` を追加した。保存済みコミット `f29996a` の `OrderControlBaselineForkResult` に、この field はすでに存在した。今回の実装は結果型を変更していない。既存テスト期待値の追随漏れである。

### 独立確認

Cursor 報告だけでは完了判断していない。次を Terminal で直接確認した。

- `uxsim.py` の World 属性
- 評価終了時刻検査 helper
- 評価終了済み判定 helper
- `exec_simulation` の局所 import
- driver 呼出し位置
- `end_ts` 切り詰め
- 終了集計の一回性
- `check_simulation_ongoing`
- driver の内部余白検査
- baseline fork 複製直後の制限解除
- 新規専用テスト 22 件の本文
- 既存テスト 2 件の変更本文
- 保存済み `f29996a` 時点の baseline 結果型

### 回帰結果

主要 5 テストファイルは `179 passed in 19.11s` である。baseline から atomic apply、自動起動・評価終了制御までの関係テスト全体は `994 passed in 26.16s` である。

### py_compile

変更・修正した 6 ファイルの `py_compile` は成功した。

### 正式サンプル

実行は `python demos_and_examples/example_00en_simple.py` である。

- 1200秒まで正常完走
- completed trips: 735 / 810
- average speed: 11.7 m/s
- total travel time: 119475.0 s
- average travel time: 162.6 s
- average delay: 62.6 s
- delay ratio: 0.385
- total distance traveled: 1632250.0 m

従来結果と一致した。`git diff --check` は問題なしである。

### 未実装範囲

- `Node.transfer` による TVT 順位の物理利用
- actual passage
- actual outcome
- 実績評価
- 満足評価
- welfare
- リンク分析の評価期間限定
- 対象外 Node の順位台帳削除

### 次の再開地点

1. 第4巻と進捗第3巻を Terminal で限定確認する。
2. 実装・テスト 6 ファイルの変更範囲を確認する。
3. `git diff --check` を実行する。
4. 文書、実装、テストを同一保存単位で commit する。
5. commit 名に `document` を含める。
6. commit 名に `complete` を使用しない。
7. commit と push を分離する。
8. 保存後、`Node.transfer` による TVT 順位の物理利用へ進む前に、その完全実装前仕様を作成する。
9. 実装後は Cursor 報告だけで完了判断せず、独立確認する。

# TVT-MP確定順位の物理通過接続 設計判断

記録日: 2026-09-29

## 1. 記録の目的と位置づけ

現在の TVT-MP は、順位、支払、補償、成立時履歴を確定できる。`Node.transfer` は、その順位をまだ実際の交通へ使っていない。

次段階では、`assigned_rank` を交差点の物理通過へ接続する。`assigned_rank` は、その順位で必ず通過できる保証ではない。その順位で通過を試す機会である。実際に通過できるかは、その時点の物理状態で決まる。

本節は、実コード調査と Terminal での独立確認によりまとまった設計判断の記録である。完全実装前仕様ではない。helper の正式名、新規 module の正式名、関数の正式引数、専用テストファイル名、完全な例外メッセージ、実装対象行は、ここでは決めない。

## 2. 通過試行機会の順位

TVT-MP の確定順位は、実際の通過結果を保証しない。

- `assigned_rank` 順に通過を試す。
- 現在通過できない Vehicle は順位を失わない。
- 正常な物理制約なら一時スキップする。
- 後続順位を試す。
- 次の timestep で再評価する。
- clearance 未充足だけ、その timestep の対象 Node 処理を終了する。

これは、「確実な時間短縮」ではなく、「時間短縮を試す権利・機会」という研究上の位置づけと整合する。

## 3. 実Worldの時刻内順序

各実 timestep は次の順である。

1. `run_tvt_mp_driver`
2. `Link.update`
3. `Node.generate` と `Node.update`
4. `Node.transfer`
5. `Vehicle.update`

前時刻の `Vehicle.update` で `incoming_vehicles` へ入った研究対象 Vehicle は、次時刻の driver で登録・確定される。driver 後から同じ時刻の `Node.transfer` 前まで、`incoming_vehicles` へ新しい Vehicle は追加されない。

## 4. 実Worldの候補集合

実 World では、時刻 T の driver 完了後の最新順位台帳を使う。

候補は、現在その Node の `incoming_vehicles` にいる Vehicle だけである。未到着 Vehicle は `incoming_vehicles` にいない。通過済み Vehicle は `incoming_vehicles` から削除済みである。

順位台帳全体を先頭から毎回走査しない。通過済み VisitKey 集合も追加しない。

参加・非参加では分けない。非参加 Vehicle も登録・確定され、順位に従って通過を試す。

実 World の識別は、`_order_control_baseline_collector is None` である。Node 別順位台帳を要求する。必要な Node 別順位台帳の欠如は `RuntimeError` である。台帳が有るか無いかから、baseline fork の種別を推測しない。

## 5. 台帳外・未確定Vehicleの独立確認

到着済み研究対象 Vehicle は snapshot 計画へ入り、順位台帳へ登録される。参加・非参加による登録除外はない。到着済み Visit の情報不整合は、黙って未確定へ残さず、driver を `ValueError` 等で失敗させる。

したがって、driver 正常成功後の実 World では、`Node.transfer` 直前の通過可能な研究対象 Vehicle は全件確定済みである。

正常成功後の台帳外・未確定 Vehicle による追越しや永久待機は発生しない。この現象への特別な fallback や待機規則は追加しない。

この全件確定は、実 World で driver が正常成功したあとの契約である。汎用 baseline fork は、TVT 確定群と通常 baseline 群への分類へ入らない。汎用 baseline fork に Node 別順位台帳が無いことは、未確定の重大不整合ではない。

## 6. VisitKeyとassigned_rank

現在 VisitKey は次である。

```text
(vehicle.name, current_visit["visit_id"])
```

候補を `assigned_rank` 昇順へ並べる。順位台帳の `assigned_rank` は確定リストの位置と一致し、同順位は既存の台帳検査が拒否する。二次キー、乱数、`merge_priority` は順位選択に使わない。

## 7. 実進路とformal route

物理通過時の outlink には、その時点の `Vehicle.route_next_link` を使う。

正常な TVT 通過候補では、`Vehicle.route_next_link` は必ず存在する。`None` の場合に formal route を代替進路として使わない。`None` の場合は、次時刻まで待たせず、通常 baseline 群へ fallback せず、重大不整合として `RuntimeError` にする。これは、実在する正常な交通現象への新しい制度判断ではない。万一の内部状態破損を、原因不明の永久待機にしないための防御である。

順位台帳の `formal_route_next_link_name` は、TVT 判断時の baseline 予測である。formal route を実 World へ強制しない。`Vehicle.route_next_link` を formal route へ上書きしない。formal route と実進路が異なっても、`route_next_link` が有効な Link である限り `RuntimeError` にしない。

順位、支払、補償、成立時履歴を再計算しない。formal route と実進路の差は、次段階の actual passage・actual outcome で予測差として記録する。

UXsim の最新経路選択により、ネットワーク上の実際の混雑を反映した進路選択を維持する。

## 8. 一時スキップ

次は正常な物理制約であり、例外にしない。一時スキップは、この一覧に限る。`route_next_link is None` は含めない。

- inlink 物理先頭でない
- Node 流量不足
- inlink 流出容量不足
- outlink 流入容量不足
- outlink 入口空間不足
- 既に `incoming_vehicles` からいなくなった

この場合、Vehicle を候補や順位台帳から削除しない。その時刻では後続順位を試す。次の timestep で再評価する。

## 9. clearance

交差点では、制御方式を問わず、安全のための clearance が必要である。実装の仕方は制御方式で異なる。

通常の信号交差点は `order_control_type="none"` を使う。青信号と次の青信号の間に、全赤時間を信号設定として明示する。UXsim が全赤時間を自動で足す、という意味ではない。grid 型ネットワークの研究評価でも、この全赤時間による clearance を基本方式とする。

TVT、FCFS、BATCH の交差点は、次の order-control clearance で、方向が切り替わるときの安全時間を確保する。

- `last_order_control_inlink`
- `last_order_control_entry_timestep`
- `order_control_clearance_timesteps`

直前通過 inlink と今回候補の inlink が異なる場合だけ、この order-control clearance を確認する。同一 inlink なら、order-control clearance 上の追加待機は不要である。`last_order_control_inlink` が `None` でも、order-control clearance 上は通過できる。

通過可能条件は、既存 FCFS、BATCH、局所仮想計算と同じである。

```text
W.T - last_order_control_entry_timestep > order_control_clearance_timesteps
```

この比較は strict greater-than である。直前の別 inlink の通過時刻を T とする。

- `order_control_clearance_timesteps=0` では、T の差は 0 であり、`0 > 0` は偽である。同じ timestep の別 inlink 通過は許されない。最短は T+1 であり、その差は 1 なので `1 > 0` が真になる。
- `order_control_clearance_timesteps=1` では、T+1 の差は 1 であり、`1 > 1` は偽である。最短は T+2 であり、その差は 2 なので `2 > 1` が真になる。間の 1 timestep を確実に空ける。

したがって clearance 設定値0は、同一 timestep 内の別 inlink 通過を許す方式ではない。次の timestep まで待たせる。order-control clearance について、「clearanceなし」という語は使わない。

研究評価の基本設定として採用する clearance 値は、本仕様で新しい数値を決めず、完全実装前仕様と各実験設定に従う。比較と回帰確認では、clearance 設定値0と clearance 設定値1の双方を確認できる。通常の信号交差点の全赤時間とは、実装方式が異なる。

未充足なら、その timestep の対象 Node 処理を終了する。後続順位と通常 baseline 群を処理しない。clearance 未充足は例外ではない。研究評価の基本方式は、安全のための clearance ありである。

## 10. signalとeligible

TVT 対象 Node は無信号を前提とする。TVT 物理通過へ `signal_phase`、`signal_group` の判定を追加しない。これは、TVT で clearance が不要という意味ではない。TVT は order-control clearance を使う。信号付き `time_value` Node への新規拒否検査も追加しない。

`order_control_type="none"` の信号交差点では、青と次の青の間に全赤時間を信号設定として置く。UXsim が全赤時間を自動で付けることには依存しない。この全赤時間と、TVT・FCFS・BATCH の order-control clearance は、安全のための clearance を別の方法で実現しているだけである。

`time_value` かつ `order_control_eligible=False` は、正常な研究実行では発生しない。TVT 物理通過を使う Node は次である。

```text
order_control_type == "time_value"
かつ
order_control_eligible is True
```

実行中の動的無効化への特別対処は追加しない。

## 11. baselineの意味

baseline には、性格の異なる 2 種類がある。どちらも同じ `_order_control_baseline_collector` を fork へ接続する。collector の有無だけでは、この 2 種類を区別できない。fork 側の順位台帳が空であることだけでも、区別できない。

1. TVT-MP の判断に使う baseline

`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` が作る。TVT 順位台帳を明示的に受け取る。

- T-1 までに決まった TVT 順位を引き継ぐ。
- 過去に順位確定済みの Vehicle を、その順位順で先に試す。
- その後に、順位未確定の通常 baseline Vehicle を処理する。
- 時刻 T の新しい TVT 順位は混ぜない。
- 過去の TVT も解除した完全通常交通には戻さない。

2. 交通予測や baseline 機能単独の検証に使う汎用 baseline

`run_snapshot_fixed_baseline_fork()` が作る。順位台帳を受け取らない正式な汎用 baseline API である。

- TVT 順位の物理適用を目的としない。
- baseline 交通の収集と、固定 horizon の前進を行う。
- `time_value` Node であっても、従来の通常合流で前進する。
- Node 別順位台帳を要求しない。

TVT 順位の物理適用は、TVT 順位台帳登録付き baseline API で作った fork だけで行う。汎用 baseline API は、従来の通常合流を維持する。

区別は、baseline を作成した公開 API 自身が collector へ明示する mode である。正式な属性名は `apply_copied_tvt_confirmed_ranks` である。`True` が TVT 順位適用 baseline fork、`False` が汎用 baseline fork である。既定値は `False` であり、既存の引数なし constructor は汎用 collector として従来どおり動く。

次は採用しない。

- Node 別順位台帳が無いなら汎用 baseline fork だと推測する。
- Node 別順位台帳があるなら TVT 順位適用 baseline fork だと推測する。
- 台帳が無い場合は、通常合流へ黙って fallback する。

TVT 順位適用 baseline fork でも、`World.copy()` は時刻 T の未確定登録より前である。そのため、copy 直後には Node 別順位台帳が存在しないことがある。台帳の有無は、fork 種別の印ではない。`World.copy()` だけでは、実 World 属性と別 object の引数 mapping は fork へ入らない。TVT 用 baseline API は、登録前にその mapping を独立複製して fork へ明示接続する。詳細は §12 である。

## 12. fork copy時点の凍結順位台帳

時刻 T の baseline fork は、T の新規未確定登録と確定処理より前に `World.copy()` される。確認済みの処理順は次である。

1. `World.copy()`
2. snapshot 登録計画作成
3. T の Visit を実 World 順位台帳へ未確定登録
4. fork collector へ登録
5. baseline forward
6. alignment
7. 到着済み Visit 確定
8. 先頭非参加 Visit 確定
9. 候補処理
10. final rank
11. atomic apply

正常な TVT-MP driver 経路では、baseline API へ渡す `rank_states_by_node_name` は、実 World の `order_control_tvt_rank_states_by_node_name` そのものである。driver は Node 別台帳を準備してから baseline 処理へ進む。したがって `World.copy()` は、実 World 属性の台帳を fork へ独立複製する。

TVT baseline API は、実 World 属性とは別 object の mapping を引数として受け取ることも正式に許している。この既存契約は削除しない。その場合、`World.copy()` が複製するのは実 World 属性であり、引数 mapping ではない。引数 mapping を fork へ接続しなければ、fork の `order_control_tvt_rank_states_by_node_name` は copy された空 dict のままであり、到着候補がある `Node.transfer` は `RuntimeError: Node junction: TVT rank ledger is missing.` になる。この不足は、fork alignment 回帰で判明した。既存テストの期待値は変更していない。

TVT 用 baseline API の正式な処理順は、`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` の中で次とする。

1. `_prepare_baseline_fork(..., apply_copied_tvt_confirmed_ranks=True)` で fork World を作る。
2. snapshot 登録計画を作る。
3. 呼出し側 `rank_states_by_node_name` について、対象 Node の欠如、型、`node_name` 不一致を、既存の登録前検査で確認する。
4. 時刻 T の未確定 Visit を登録する前の mapping を、標準ライブラリの `copy.deepcopy` で独立複製する。
5. 複製を `prepared.fork_W.order_control_tvt_rank_states_by_node_name` へ接続する。
6. `register_undetermined_visits_from_snapshot_plan` は、元の呼出し側 mapping だけへ適用する。
7. collector へ snapshot 計画を適用する。
8. baseline forward を行う。

時刻 T の未確定 Visit は、元の呼出し側台帳だけへ登録する。fork 側の独立複製には、時刻 T の新規未確定 Visit を追加しない。fork は、複製時点の T-1 以前の確定順位だけを物理適用する。fork 側で `is_confirmed()` が真の Visit は、T-1 以前に確定した Visit である。

fork 側の mapping と元の mapping は、同じ object ではない。各 Node の `OrderControlTvtNodeRankState` も、同じ object ではない。fork 側の処理が順位台帳を変更しても、元の呼出し側台帳へ伝播しない。元台帳の後続変更も fork へ伝播しない。正常な driver 経路と、baseline API 単独経路は、この同じ契約にする。

`OrderControlTvtNodeRankState` が保持するのは、Node 名の文字列、VisitKey の tuple、confirmed 順序の list、`assigned_rank` の dict、formal route 名の dict、未確定 VisitKey の set だけである。Vehicle、Node、Link、World 等の live object 参照は保持しない。`World.copy()` は pickle による独立複製である。順位台帳群は、安全に独立複製できる。

不正な mapping を複製したあとで曖昧な例外を出さない。対象 Node の欠如、型、`node_name` 不一致は、複製より前に、既存の登録前検査を再利用するか、責務が重複しない小さな検査 helper で確認する。登録時に保証済みの内容を、物理通過時に過剰に重複検査しない。物理通過が到着候補について行う既存の Node 別台帳検査は維持する。

`confirmed_at_timestep` 等の追加 field は不要である。登録前の独立複製が、T の新規未確定登録が fork へ混ざる前の境界である。

Node 別順位台帳の有無から、汎用 baseline fork と TVT 順位適用 baseline fork を推測しない。到着候補がある実 World または TVT 順位適用 baseline fork で、必要な Node 別順位台帳が欠けていれば `RuntimeError` である。通常合流へ黙って戻さない。到着列が 0 件なら、通過候補も確認すべき順位もなく、台帳を要求せず正常 return する。汎用 baseline fork は、この複製接続を行わず、順位台帳を要求しない。

## 13. baseline forkの候補2群

この 2 群は、TVT 順位適用 baseline fork だけに使う。識別は `collector.apply_copied_tvt_confirmed_ranks is True` である。汎用 baseline fork は、TVT 確定群と通常 baseline 群へ分類しない。

TVT 順位適用 baseline fork の `Node.transfer` 開始時点の `incoming_vehicles` を、開始時 snapshot として次の 2 群へ分ける。同じ Vehicle を両群へ入れない。

過去確定群:

- fork へ接続した登録前の独立複製で `is_confirmed()` が真
- T-1 以前に確定済み
- `assigned_rank` 順に先に通過を試す
- 時刻 T の新規未確定 Visit は、この複製に入っていない

通常 baseline 群:

- fork 側順位台帳で confirmed ではない
- T で初めて到着済みとなる Visit
- fork 前進中に将来到着する Visit
- 未確定 Visit
- 台帳外 Visit

通常 baseline 群は、`Node.transfer` 開始時の固定 snapshot とする。過去確定群の処理後に `incoming_vehicles` から作り直さない。作り直すと、一時スキップした過去確定 Vehicle が通常群へ混ざる。

## 14. baseline forkの共存処理

次の順は、TVT 順位適用 baseline fork だけである。汎用 baseline fork は、この分類と順位試行へ入らず、従来の通常合流で前進する。

TVT 順位適用 baseline fork では次の順に処理する。

1. 過去確定群を `assigned_rank` 順に一度ずつ試す。
2. 物理先頭、容量、入口空間不足なら一時スキップする。
3. 過去確定群で order-control clearance が未充足なら、通常 baseline 群を開始せず、その timestep の対象 Node 処理を終了する。
4. 過去確定群で clearance 終了しなかった場合は、開始時に固定した通常 baseline 群へ進む。車両の選択順は従来の通常合流である。通過前には、過去確定群と同じ order-control clearance を確認する。
5. 通常 baseline 群で order-control clearance が未充足なら、例外にせず、その時刻の通常群処理を終了する。後続の通常 baseline Vehicle は処理しない。

過去確定順位は、排他的な通行予約ではない。過去確定 Vehicle へ先に通過試行機会を与えたあと、物理条件により通れなかった場合でも、通常 baseline 群を処理してよい。

これは新しい制度規則ではない。既定の「通過試行機会順位」を、baseline fork へ適用したものである。

## 15. 通常baseline群と通常合流helper

`Node.incoming_vehicles` を一時的に差し替えない。例外時の live 状態破損を避けるためである。

通常合流処理を、処理してよい Vehicle 集合と、order-control clearance を適用するかを明示引数で受ける Node の private helper へ抽出する。完全実装前仕様の正式 signature は次である。

```text
Node._transfer_normal_merge(
    self,
    allowed_vehicles=None,
    enforce_order_control_clearance=False,
) -> None
```

`allowed_vehicles` を省略し、`enforce_order_control_clearance=False` のときは、現在の通常 Node の合流処理をそのまま維持する。この呼出しは order-control clearance を検査せず、通過後も order-control 用の clearance 履歴を更新しない。これは安全のための clearance が不要という意味ではない。通常の信号交差点では、信号設定として明示した全赤時間がその役割を担う。責務を分けるための引数である。

許可集合を指定した場合は、次のとおりとする。

- outlink 候補作成を許可集合だけに限定する。
- Vehicle 選択も許可集合だけに限定する。
- 一時スキップした過去確定 Vehicle を `merge_priority` や乱数の対象へ戻さない。
- 過去確定群が消費した最新容量を使う。
- 通常合流の `merge_priority`、hard deterministic、信号条件を維持する。
- TVT 順位適用 baseline fork の通常 baseline 群では `enforce_order_control_clearance=True` とする。選択順は通常合流のままである。clearance だけを、order-control 対象 Node の物理制約として適用する。
- 汎用 baseline fork は、許可集合を省略した `node._transfer_normal_merge()` を呼ぶ。`enforce_order_control_clearance` の既定値 `False` を用いる。order-control clearance は適用しない。通常の信号交差点の安全上の clearance は、従来どおり信号設定上の全赤時間が担う。

TVT 専用の信号判定は追加しない。`time_value` Node は無信号なので、通常 helper 内の既存信号条件は通過を止めない。TVT の安全時間は order-control clearance が担う。

## 16. 共通1台移動helper

今回触る通常合流と TVT 確定群の物理移動について、1 台の移動処理を責務の明確な helper として共有できる。

担当候補:

- baseline collector の prepare
- 累積台数
- `traveltime_actual`
- `link_arrival_time`
- capacity 減算
- inlink からの削除
- outlink への追加
- `Vehicle.link`
- `begin_order_control_visit_on_link_entry`
- `x`
- leader、follower、lane
- `move_remain`
- 移動直後の後続 trip 終了
- `incoming_vehicles` からの削除
- baseline collector の apply

担当しないもの:

- 候補順位
- 通過可否判定
- order-control clearance の判定
- order-control clearance 履歴の更新
- `merge_priority`
- actual passage
- actual outcome

1 台移動 helper は、order-control clearance 履歴を更新しない。TVT 確定群の順位走査と、`enforce_order_control_clearance=True` の通常合流 helper が、通過成功後に更新する。通常の信号交差点の全赤時間は、信号設定側で扱う。`order_control_type="none"` の通常合流は、この履歴を使わない。

FCFS と BATCH の移動処理は今回共通化しない。大規模リファクタリングを避ける。helper の正式な範囲と引数は、完全実装前仕様で確定する。

## 17. incoming_vehiclesの終了処理

通過成功 Vehicle は、移動時に `incoming_vehicles` から削除する。

一時スキップした Vehicle と通れなかった Vehicle は、処理終了時に `incoming_vehicles` を空にしてよい。FCFS と BATCH も、clearance 等で途中終了した後、`incoming_vehicles` を空にする。リンク終端に残った Vehicle は、同じ時刻の後段の `Vehicle.update` で再登録される。

TVT 処理も最後に次を行う。

- 各 inlink 先頭の trip 終了待ち Vehicle を既存どおり終了させる。
- `incoming_vehicles` を空にする。

この終了処理は、1 回の `Node.transfer` につき 1 回だけ行う。clearance で終了した場合も行う。

## 18. baseline collector

baseline fork の種別は、collector の明示 mode で区別する。正式な属性は `collector.apply_copied_tvt_confirmed_ranks` である。外部から読める通常属性とし、property や setter は追加しない。実装後に変更されることを前提としない設定値として扱う。

`False` は汎用 baseline fork である。コピー済み TVT 確定順位を物理適用しない。順位台帳の独立複製も行わない。`True` は TVT 順位台帳登録付き baseline fork である。TVT 用 baseline API が登録前に独立複製して fork へ接続した台帳の、T-1 以前の確定順位を物理適用する。既定値は `False` である。既存の引数なし constructor は、汎用 collector のままである。mode は順位台帳 object を保持しない。台帳の接続は、collector の mode 設定とは別の手順である。

collector の有無だけでは、2 種類の fork を区別しない。Node 別順位台帳の有無からも推測しない。

汎用 baseline fork でも、TVT 順位適用 baseline fork でも、通過成功時の到着・通過記録は維持する。TVT 順位適用 baseline fork では、過去確定群と通常 baseline 群の双方について、通過成功時だけ次を 1 回行う。汎用 baseline fork では、通常合流と 1 台移動 helper が同じ記録を維持する。mode は記録を止めない。

- `prepare_baseline_passage_recording`
- `apply_baseline_passage_timestep`

容量不足や入口空間不足では prepare しない。記録する Visit ID は、通過前の current Visit ID である。

実 outlink が baseline 登録時の `route_next_link_name` や formal route と異なっても、既存 collector 契約はその不一致を拒否しない。同じ Visit の通過を二重 apply すると、既存検査が拒否する。

## 19. downstream boundary observer

downstream boundary observer は、`exec_simulation` が `node.transfer()` の外側で扱う。

1. `capture_before_transfer`
2. `node.transfer`
3. `commit_after_transfer`
4. `finally` で `clear_pending`

TVT helper、通常合流 helper、1 台移動 helper から observer を直接呼ばない。observer を二重に起動しない。

## 20. 通過済みVisit

通過済み VisitKey 集合は追加しない。通過済み Vehicle は `incoming_vehicles` から削除される。

次の Node が制御対象なら、新しい `visit_id` で新 Visit が作られる。次 Node が対象外なら、`order_control_current_visit` は `None` になる。順位台帳の過去確定順位は履歴として残す。

## 21. 重大不整合と正常な物理制約

正常な物理制約は例外にしない。物理先頭でないこと、容量不足、入口空間不足、clearance 未充足は、ここへ含まれる。

重大不整合として `RuntimeError` にするのは、現在 Visit が無い場合、現在 Visit の Node や inlink が `Vehicle.link` と一致しない場合、および正常な TVT 通過候補で `route_next_link is None` の場合である。`None` は次時刻に自然解消する容量待ちではない。formal route との差、信号、台帳外、eligible の途中変更は、この例外にしない。目的地到着の trip 終了待ち、outlink が無い trip abort、taxi、`specified_route`、局所仮想計算の World 全体 copy で `route_next_link is None` を許容する確認は、今から対象 Node を通過する研究対象 Vehicle の契約ではない。

到着候補があるときの Node 別順位台帳の欠如は、実 World と TVT 順位適用 baseline fork では `RuntimeError` である。到着列が 0 件なら、台帳を要求せず正常 return する。汎用 baseline fork では要求しない。台帳が無いことは、汎用 baseline fork では正常である。引数 mapping が実 World 属性と別 object であること自体は、重大不整合ではない。TVT 用 API が登録前複製を fork へ接続する前に forward し、到着候補から台帳を読めないことが重大不整合である。`collector.apply_copied_tvt_confirmed_ranks` が `bool` でない場合も `RuntimeError` である。これは、台帳が無いことを見て通常合流へ戻す暗黙の fallback ではない。

## 22. 実装構造の基本方針

`Node.transfer` は、FCFS と BATCH の早期 return を維持する。`time_value` かつ `order_control_eligible is True` のときだけ、TVT 物理通過へ入って return する。それ以外は、許可集合を省略した通常合流 helper である。

TVT 物理通過は、順位台帳を取得する前に、次の 3 種類へ分ける。

1. collector が `None` なら実 World である。最新の確定順位を使い、Node 別順位台帳を要求する。開始時 snapshot の研究対象 Vehicle が未確定なら `RuntimeError` であり、通常 baseline 群へ fallback しない。
2. collector が `None` でなく、`apply_copied_tvt_confirmed_ranks is True` なら、TVT 順位適用 baseline fork である。凍結台帳の T-1 以前の確定順位を使う。Node 別順位台帳を要求する。過去確定群を `assigned_rank` 順に試し、clearance で終了していなければ、開始時の通常 baseline 群を `enforce_order_control_clearance=True` で通常合流する。
3. collector が `None` でなく、`apply_copied_tvt_confirmed_ranks is False` なら、汎用 baseline fork である。TVT 順位台帳を読まない。確定群と通常 baseline 群へ分類しない。`node._transfer_normal_merge()` を、既定の `enforce_order_control_clearance=False` で呼び、正常 return する。

終了処理は、どの正常経路でも `Node.transfer` が 1 回だけ行う。実 World と 2 種類の baseline fork で、`Node.transfer` の入口関数は分けない。見る順位台帳が違う。実 World は T の driver 完了後の最新台帳、TVT 順位適用 baseline fork は登録前に独立複製して fork へ接続した台帳である。汎用 baseline fork は順位台帳を見ない。局所仮想計算の拘束順位走査は呼ばない。formal route 不一致を例外にする契約と、通過済み集合を使う契約が、今回の実 World 方式と違うためである。

TVT 用 baseline API の台帳接続は、物理通過 module では行わない。`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` が、登録前に `copy.deepcopy` して fork World へ接続する。公開 signature は変えない。

新規 module に TVT 側の候補分けと順位試行を置くかは、完全実装前仕様で正式名とともに確定する。`uxsim.py` 先頭での import により循環 import を作らない。

## 23. テストで固定すべき契約

次を専用テストで固定する。テストファイル名は完全実装前仕様で決める。

- 実 World は、現在の `incoming_vehicles` だけを `assigned_rank` 順に試す。
- 通過済み Visit 集合を作らない。未到着の確定 Visit は候補にしない。
- 非参加 Vehicle も順位どおり試す。
- formal route と `route_next_link` が違っても、`route_next_link` を使い、台帳、金額、成立時履歴を変えない。
- 実 World の確定候補で `route_next_link is None` なら `RuntimeError` である。
- baseline fork の過去確定群で `route_next_link is None` なら `RuntimeError` である。
- baseline fork の通常 baseline 群でも、開始時 snapshot の分類時点で current Visit と `route_next_link` を検査する。正常な研究対象 Vehicle なら `route_next_link` は存在する。`None` なら `RuntimeError` である。通常合流 helper が `allowed_vehicles=None` の通常 Node で `None` を outlink 候補から外す契約とは別である。
- 物理先頭、容量、入口空間の不足は一時スキップし、後続を試す。`route_next_link is None` は一時スキップにしない。
- clearance 未充足では、その時刻の後続と通常 baseline 群を処理しない。
- 次時刻に再評価する。
- clearance 設定値0でも、同一 timestep 内の別 inlink 通過を許さない。
- clearance 設定値0は、次の timestep で通過可能になる。
- clearance 設定値1は、次の次の timestep で通過可能になる。
- 同一 inlink には、方向切替の order-control clearance を要求しない。
- 通常の信号交差点では、明示した全赤時間を使う。
- 既存名に `no_clearance` を含む比較・回帰確認用関数は、名称を理由に clearance 設定値0と同一視しない。関数名と実装は今回変更しない。
- baseline fork には、汎用 baseline fork と TVT 順位適用 baseline fork の 2 種類がある。
- collector の明示 mode `apply_copied_tvt_confirmed_ranks` で区別する。collector の有無だけでは区別しない。
- Node 別順位台帳の有無から fork 種別を推測しない。
- 汎用 baseline fork は、`time_value` Node でも TVT 順位台帳を要求せず、通常合流で前進する。
- TVT 順位適用 baseline fork だけが、コピー済みの T-1 以前の確定順位を物理適用する。
- TVT 順位適用 baseline fork で必要な Node 別順位台帳が欠けていれば `RuntimeError` である。
- 汎用 baseline fork で台帳が無いことは正常である。
- 既存の引数なし collector constructor は、既定値 `False` の汎用 collector として残す。
- TVT 順位適用 baseline fork は、登録前の独立複製にある T-1 以前の確定順位を使い、時刻 T の新規未確定 Visit を混ぜない。
- 正常な driver 経路では、`World.copy()` が実 World 属性の台帳を複製する。baseline API 単独利用では、引数 mapping が実 World 属性と別 object でもよい。
- TVT 用 baseline API は、その引数 mapping を登録前に独立複製し、fork World へ明示接続する。時刻 T の未確定登録は元台帳だけへ適用する。
- fork 側台帳と元台帳は、mapping も各 Node の rank state も object を共有しない。一方の後続変更は、他方へ伝播しない。
- この独立性は、専用テスト 34 件へ入れない。`tests_order_control_tvt_baseline_driver_registration.py` の `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` で固定する。
- 過去確定群を先に試し、一時スキップした過去確定 Vehicle を通常群へ混ぜない。
- 通常群は既存の `merge_priority` と hard deterministic を維持し、過去確定群が消費した容量を見る。
- 通常 baseline 群にも order-control clearance を適用する。
- 通常 baseline 群の clearance 未充足では、後続の通常群を処理しない。
- 通常 baseline 群の通過成功後に、order-control clearance 履歴を更新する。
- `order_control_type="none"` の通常合流では、order-control clearance 履歴を更新しない。
- 通常の信号交差点では、明示した全赤時間を含む信号設定を使う。UXsim の自動付与には依存しない。
- 過去確定群が通過した直後、別 inlink の通常群は同じ時刻に通過しない。
- 過去確定群と同じ inlink の通常群は、容量等を満たせば、order-control clearance 上の追加待機は不要である。
- 通常 baseline 群で 1 台通過した後、別 inlink の後続通常群へ order-control clearance を適用する。
- 比較と回帰確認では、clearance 設定値0と clearance 設定値1の双方を確認できる。
- 研究評価の基本方式は、安全のための clearance ありである。
- 研究評価で使う clearance 値は、実験設定に従う。本判断で新しい数値は決めない。
- collector は通過 1 回につき 1 回だけ更新する。
- observer は `node.transfer()` 1 回につき外側で 1 回のままである。
- trip 終了待ちは維持する。
- 通常 Node、FCFS、BATCH の現行結果は変えない。
- 登録 Visit 0 件では baseline forward しない。
- 過去の確定順位は解除しない。
- 評価終了と内部余白の契約を維持する。
- 局所 World だけが T の候補順位を使う。

## 24. actual passage・actual outcomeへの接続

今回は実装しない。物理通過成功の位置を一意にし、次段階で記録を追加できる構造にする。

次段階で扱うもの:

- buyer、seller、非参加の予定通過時刻と実通過時刻
- 評価終了時点で未通過なら、どの役割でも未観測
- formal route と実進路の差
- actual passage
- actual outcome
- buyer 価値
- seller 価値
- 同一 Vehicle の buyer 価値と seller 価値の合計
- buyer 回数
- seller 回数
- buyer 回数比率
- seller 回数比率
- buyer にも seller にもならない場合の比率は該当なし
- 非参加 Vehicle への外部効果
- 支払、受取、実現価値を含む累計利得

field 名、型名、status 名は今回決めない。

## 25. 採用しない方向

- 確定順位を、必ず通過できる保証として扱う。
- 順位台帳全体を毎時刻先頭から走査する。
- 通過済み VisitKey 集合を追加する。
- formal route を実進路へ強制する。
- formal route と実進路の差を `RuntimeError` にする。
- `route_next_link is None` を、次時刻に自然解消する一時的な容量待ちとして扱う。
- `route_next_link is None` の Vehicle を永久にスキップし続ける。
- formal route を `route_next_link` の代替として強制する。
- 順位、支払、補償、成立時履歴を、実進路の差を理由に再計算する。
- 正常成功後の台帳外・未確定 Vehicle への特別 fallback や永久待機対策を追加する。
- TVT 物理通過へ信号判定を追加する。
- 信号付き `time_value` Node を新規検査で拒否する。
- `order_control_eligible` の実行中変更への特別対処を追加する。
- baseline を、過去の TVT も消した完全通常交通へ戻す。
- T の新しい TVT 順位を baseline fork へ混ぜる。
- `confirmed_at_timestep` 等の確定時刻 field を追加する。
- `incoming_vehicles` を一時的に差し替えて通常合流を再利用する。
- FCFS と BATCH の移動処理を大規模に共通化する。
- 局所仮想計算の拘束順位走査を、実 World の `Node.transfer` から呼ぶ。
- actual passage と actual outcome を、この物理接続と同時に実装する。
- 通常 baseline 群を、order-control clearance を無視して通す。
- 通常 baseline 群の通過後に、order-control clearance 履歴を更新しない。
- `order_control_type="none"` だから、安全のための clearance も不要だと扱う。
- 通常の信号交差点の全赤時間を、UXsim が自動で追加すると仮定する。
- clearance 設定値0を、同一 timestep 内の別 inlink 通過を許す「clearanceなし」と解釈する。
- clearance 設定値1を、直後の次 timestep で通過可能と解釈する。
- 通常の信号交差点の全赤時間と、order-control clearance 設定値を、同じ内部機構として扱う。
- collector が存在する baseline fork を、すべて TVT 順位適用 fork とみなす。
- Node 別順位台帳が無いことを理由に、fork 種別を推測する。
- TVT 順位適用 fork の台帳欠如を、通常合流への暗黙 fallback で隠す。
- 汎用 baseline fork へ T-1 以前の TVT 順位を強制する。
- 既存 baseline 回帰の期待値を、失敗を隠すために変更する。
- 引数 mapping を fork World へそのまま代入して共有する。
- fork 側と元側で同じ `OrderControlTvtNodeRankState` object を共有する。
- 時刻 T の新規未確定 Visit を fork 側台帳へ混ぜる。
- 引数 mapping が実 World 属性と同一 object であることを必須にする。
- 実 World 属性と別 mapping を渡せる既存 baseline API 契約を削除する。
- 時刻 T の未確定登録のあとで台帳を複製する。

## 26. 以前の誤った中間整理と訂正

削除せず、訂正として残す。

誤った整理:

- baseline fork では TVT 順位を一切使わず、通常合流だけにする。
- collector が接続された fork では、TVT 物理通過を完全に無効化する。
- 物理接続の重要論点はすべて解決済みである。

訂正:

- TVT 順位適用 baseline fork は、T-1 以前の確定 TVT 順位を維持する。
- T の新しい TVT 順位は、その fork へ混ぜない。
- fork copy 時点の順位台帳複製は、T-1 以前の確定と、時刻 T の新しい確定を分ける。fork 種別の識別には使わない。
- 過去確定群を先に順位順で試し、その後に通常 baseline 群を処理する。
- 過去確定順位は通過保証や排他的予約ではなく、先に試行機会を与える順位である。
- 汎用 baseline fork は、この順位適用の対象ではない。従来の通常合流を維持する。
- 2 種類の fork は、collector の明示 mode で区別する。台帳の有無から推測しない。

## 27. 完全実装前仕様へ持ち越す事項

- helper の正式名
- 新規 module の正式名
- 関数の正式引数
- 専用テストファイル名
- 完全な例外メッセージ
- 実装対象行
- 完全実装前仕様の全文

本節の設計判断は、その仕様の入力である。仕様作成前に、この判断を別の制度へ戻さない。

## 28. 利用者判断が必要な事項

現時点では残っていない。

これは制度変更ではない。既存の汎用 baseline API と、TVT 順位台帳登録付き baseline API を、安全に共存させるための技術的識別である。

通過試行機会の意味、実 World の候補、実進路、一時スキップ、order-control clearance、信号設定上の全赤時間、eligible、baseline の意味、fork の凍結台帳、過去確定群と通常 baseline 群の順、許可集合と clearance 適用有無を分けた通常合流、到着列の終了処理、collector と observer の一回性、通過済み集合を作らないことは、本節で確定した。通常 baseline 群へ order-control clearance を適用する訂正は、既存の局所仮想計算との整合であり、新しい制度判断ではない。clearance 設定値0と clearance 設定値1の時系列は、既存の strict greater-than を文書化する訂正であり、新しい制度判断ではない。正常な TVT 通過候補で `route_next_link is None` を `RuntimeError` にする訂正は、正常系では `route_next_link` が存在するという確認に基づく防御であり、新しい制度判断ではない。汎用 baseline fork と TVT 順位適用 baseline fork を `apply_copied_tvt_confirmed_ranks` で区別する訂正も、新しい制度判断ではない。呼出し側の順位台帳を、時刻 T の未確定登録前に独立複製して fork へ接続する訂正も、新しい制度判断ではない。

fork 種別の識別不足は、TVT-MP 物理通過の実装後に、既存 baseline 回帰が失敗して判明した。代表例外は `RuntimeError: Node junction: TVT rank ledger is missing.` である。失敗した既存回帰は、`tests_order_control_baseline_driver.py`、`tests_order_control_tvt_baseline_fork_alignment.py`、`tests_order_control_tvt_mp_evaluation_end.py` の一部である。原因は、collector の存在だけで TVT 用 baseline fork と判断し、Node 別順位台帳が無い汎用 baseline fork を重大不整合として止めたことである。明示 mode と、到着列が空のときの台帳非要求は、未保存の Python へ入っている。汎用 baseline driver と evaluation end の当該失敗は、その未保存実装で解消している。

その後も、fork alignment の一部は同じ代表例外で失敗する。原因は、TVT baseline API が実 World 属性とは別の mapping を受け取れるのに、その mapping を登録前に fork へ独立複製して接続していないことである。既存テストの期待値は変更していない。既存 baseline テストが誤っているのではなく、登録前凍結コピーの明示接続が不足していた。利用者判断は残っていない。

## 29. 次の再開地点

1. 今回の文書修正を Terminal で限定確認する。
2. Python とテストの作業開始前からの未保存差分が、今回の文書作業で変化していないことを確認する。
3. `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` で、対象 Node 検査のあと、登録前に `copy.deepcopy` し、fork World へ接続する。
4. 時刻 T の未確定登録は、元の呼出し側 mapping だけへ適用する。
5. `tests_order_control_tvt_baseline_driver_registration.py` へ `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` を追加する。専用テスト 34 件には含めない。
6. fork alignment と baseline driver registration を再実行する。既存期待値は、失敗を隠すために変えない。
7. 専用テスト 34 件、FCFS、BATCH、正式サンプルを再実行する。
8. 実装結果を第4巻と進捗第3巻へ記録する。
9. 差分と回帰結果を独立確認してから commit する。

上記の再開地点は履歴として残す。実装、独立確認、回帰結果は、同じ第4巻の「TVT-MP確定順位の物理通過接続 実装・独立確認・検証結果」を参照する。

# TVT-MP確定順位の物理通過接続 完全実装前仕様

記録日: 2026-09-29

本節は完全実装前仕様である。正式な入力は、同じ第4巻の「TVT-MP確定順位の物理通過接続 設計判断」である。その節の制度判断は、本節で別の方式へ戻さない。TVT 物理通過、明示 mode、空の到着列で台帳を要求しない処理は、Python と専用テストとして作業中であり、まだ保存していない。本訂正は、TVT 順位適用 baseline API が、呼出し側の順位台帳を時刻 T の未確定登録前に独立複製して fork World へ明示接続する契約を記録する。この接続の Python 実装は、まだ行っていない。

## 1. 目的

TVT-MP は順位、支払、補償、成立時履歴を確定できる。`Node.transfer` は、その順位をまだ物理通過へ使っていない。

本仕様は、確定順位を実 World と baseline fork の通過試行へ接続する。`assigned_rank` は通過保証ではなく、通過を試す機会の順位である。actual passage、actual outcome、実績価値、満足度、welfare は、この接続の次の段階である。

## 2. 正式な実装範囲

- `time_value` かつ `order_control_eligible is True` の Node で、`Node.transfer` が TVT 物理通過を使う。
- 実 World、TVT 順位適用 baseline fork、汎用 baseline fork を、順位台帳を読む前に 3 分類する。
- 実 World は、その時刻の driver 完了後の最新順位台帳を使う。
- TVT 順位適用 baseline fork は、時刻 T の未確定登録前に独立複製して fork へ接続した順位台帳の、T-1 以前の確定順位を使う。正常な driver 経路では、その内容は、`World.copy()` が実 World 属性から複製する時点の台帳と同じである。
- 汎用 baseline fork は、コピー済み TVT 確定順位を物理適用せず、従来の通常合流で前進する。
- 区別は `collector.apply_copied_tvt_confirmed_ranks` である。collector の有無や、Node 別順位台帳の有無から推測しない。
- 候補は、その時点の `incoming_vehicles` だけである。
- 確定群は `assigned_rank` 順に一度ずつ試す。
- 実進路は `Vehicle.route_next_link` である。
- baseline fork では、clearance で終了していなければ、開始時に固定した通常 baseline 群を通常合流する。
- 通常 Node の合流は、許可集合を省略した private helper へ移す。結果は現行と同じにする。
- 1 台の物理移動は、通常合流と TVT 確定群で共有する。FCFS と BATCH は共有しない。

## 3. 非実装範囲

- actual passage
- actual outcome
- 実績評価、満足評価、welfare
- Vehicle 単位の buyer 回数、seller 回数、比率、価値の合算
- 非参加 Vehicle の外部効果集計
- signal 統合、複数車線への一般化
- `taxi`、`specified_route`、trip 終了 Vehicle の TVT 参加
- 対象外 Node の順位台帳削除
- 確定時刻 field
- 通過済み VisitKey 集合
- formal route の強制、順位や金額の再計算
- FCFS と BATCH の移動処理の共通化
- 局所仮想計算の拘束順位走査の変更

## 4. 通過試行機会順位

確定順位は、その順位で必ず通過できる保証ではない。

- `assigned_rank` 順に一度ずつ試す。
- 正常な物理制約で通れなければ、順位も台帳も消さない。
- その時刻では後続を試す。
- 次の timestep で再評価する。
- clearance 未充足だけ、その時刻の対象 Node 処理を終える。通常 baseline 群も処理しない。

## 5. 対象Node

TVT 物理通過へ入る Node は、次を同時に満たす。

```text
order_control_eligible is True
かつ
order_control_type == "time_value"
```

`eligible is True` は、`bool` の `True` だけである。真と評価される他の値では入らない。実行中に `eligible` を `False` へ戻す特別処理は追加しない。信号判定も追加しない。信号判定を追加しないことは、clearance が不要という意味ではない。TVT 対象 Node は order-control clearance を使う。

比較対象の通常の信号交差点は、`order_control_type="none"` と、青と次の青の間に明示した全赤時間を使う。UXsim が全赤時間を自動で付けることには依存しない。

## 6. Node.transferの分岐順

`Node.transfer` の順は次である。

1. `order_control_eligible` かつ `order_control_type == "fcfs"` なら、既存の `transfer_fcfs_clearance` を呼んで return する。
2. `order_control_eligible` かつ `order_control_type == "batch"` なら、既存の `transfer_batch` を呼んで return する。
3. `order_control_eligible is True` かつ `order_control_type == "time_value"` なら、`transfer_tvt_mp_passage_attempts(self)` を呼び、その後 `_finish_node_transfer` を 1 回呼んで return する。
4. それ以外は `_transfer_normal_merge()` を呼び、その後 `_finish_node_transfer` を 1 回呼ぶ。

FCFS と BATCH の本体は変更しない。FCFS と BATCH は通常合流 helper を通らない。

## 7. import方針

`uxsim.py` の先頭では、TVT 物理通過 module を import しない。`time_value` 分岐の中でだけ、次を局所 import する。

```text
from uxsim.order_control_tvt_mp_physical_transfer import (
    transfer_tvt_mp_passage_attempts,
)
```

物理通過 module の先頭では `uxsim.uxsim` を import しない。Node、Vehicle、Link は引数の object として使う。順位台帳型は `uxsim.order_control_tvt_node_rank_state` から import してよい。この module は `uxsim.py` を import しないので、循環 import にしない。登録前台帳の独立複製は、この module では行わない。`uxsim/order_control_baseline_driver.py` が、標準ライブラリの `copy.deepcopy` を使う。

## 8. 正式な新規module

正式ファイル名は `uxsim/order_control_tvt_mp_physical_transfer.py` である。

既存の `order_control_tvt_mp_` 接頭辞に合わせる。局所仮想計算の `order_control_tvt_mp_candidate_binding_transfer.py` とは別名である。中に置くのは、実 World と 2 種類の baseline fork の 3 分類、TVT 順位を適用する側の候補分類、順位順の試行、clearance による終了、TVT 順位適用 baseline fork の通常 baseline 群を通常合流 helper へ渡す処理である。汎用 baseline fork では、順位台帳を読まず、`node._transfer_normal_merge()` を既定引数で呼んで正常 return する。終了処理の本体は持たない。

## 9. 正式な関数一覧

| 場所 | 正式名 | 戻り値 |
| --- | --- | --- |
| 新規 module | `transfer_tvt_mp_passage_attempts(node)` | `None` |
| `Node` | `_transfer_one_vehicle_between_links(self, vehicle, inlink, outlink)` | `None` |
| `Node` | `_transfer_normal_merge(self, allowed_vehicles=None, enforce_order_control_clearance=False)` | `None` |
| `Node` | `_finish_node_transfer(self)` | `None` |
| `OrderControlBaselineCollector` | `__init__(self, apply_copied_tvt_confirmed_ranks=False)` | `None` |
| baseline driver | `_prepare_baseline_fork(real_W, *, target_node_names, baseline_horizon_steps, apply_copied_tvt_confirmed_ranks)` | `_BaselineForkPrepared` |

clearance で終了したことは、戻り値では返さない。`transfer_tvt_mp_passage_attempts` の内部で通常 baseline 群を呼ばなければ足りる。呼出し側の `Node.transfer` は、正常 return のあと必ず終了処理を 1 回行う。

`run_snapshot_fixed_baseline_fork()` と `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` の公開引数は変更しない。内部で、上の `_prepare_baseline_fork` へ明示 mode を渡す。TVT 用 API は、その後に登録前台帳を `copy.deepcopy` して fork World へ接続する。新しい公開関数は追加しない。対象 Node 検査は、既存の登録前検査を再利用するか、責務が重複しない小さな helper に限る。

## 10. 各関数の責務

`transfer_tvt_mp_passage_attempts` は、順位台帳を取得する前に、実 World、TVT 順位適用 baseline fork、汎用 baseline fork を分類する。実 World と TVT 順位適用 baseline fork では、開始時 snapshot の分類、確定群の順位順試行、一時スキップ、clearance 終了、TVT 順位適用 fork の通常 baseline 群の呼出しを行う。汎用 baseline fork では、順位台帳を読まず、確定群と通常 baseline 群へ分類せず、`node._transfer_normal_merge()` を既定の `enforce_order_control_clearance=False` で呼んで正常 return する。1 台移動、通常合流の選択、終了処理の本体は持たない。終了処理は、その正常 return のあと `Node.transfer` が 1 回だけ行う。

`_transfer_one_vehicle_between_links` は、呼出し側が通過可能と判断した 1 台を、指定した inlink から指定した outlink へ移す。順位、clearance、通過可否、`merge_priority`、経路選択、formal route、observer は扱わない。

`_transfer_normal_merge` は、現行の通常合流の outlink 試行と車両選択を行う。終了処理は行わない。`enforce_order_control_clearance=True` のときは、選んだ Vehicle を通す前に order-control clearance を検査する。未充足なら、その helper 全体を正常 return する。通過成功後は order-control clearance 履歴を更新する。`False` のときは order-control clearance を検査せず、その履歴も更新しない。`False` は、安全のための clearance が不要という意味ではない。通常の信号交差点では、信号設定上の全赤時間がその役割を担う。

`_finish_node_transfer` は、各 inlink 先頭の trip 終了待ちを既存どおり終了し、`incoming_vehicles` を空にする。

`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration` は、fork 作成と snapshot 計画のあと、登録前に呼出し側 mapping を独立複製して `prepared.fork_W.order_control_tvt_rank_states_by_node_name` へ接続する。時刻 T の未確定登録は、元の呼出し側 mapping だけへ適用する。fork 側の複製には、時刻 T の新規未確定 Visit を追加しない。汎用 API は、この複製接続を行わない。

## 11. 各関数の引数

`transfer_tvt_mp_passage_attempts(node)` の `node` は、対象の `Node` である。World は `node.W` から読む。

`_transfer_one_vehicle_between_links(self, vehicle, inlink, outlink)` は、移動する Vehicle、移動前の inlink、移動先 outlink を別引数で受ける。移動後に `vehicle.link` から inlink を取り直さない。

`_transfer_normal_merge(self, allowed_vehicles=None, enforce_order_control_clearance=False)` の `allowed_vehicles` は、`None` または Vehicle の tuple である。`None` は、現在の `incoming_vehicles` 全体を候補にする。tuple を指定したときは、その固定候補だけを対象にする。`enforce_order_control_clearance` は `bool` である。`False` が既定であり、標準 UXsim の通常合流が使う。`True` は baseline fork の通常 baseline 群が使う。意味は docstring に書く。

`_finish_node_transfer(self)` は引数を増やさない。

`OrderControlBaselineCollector.__init__(self, apply_copied_tvt_confirmed_ranks=False)` の既定値は `False` である。引数が Python の `bool` であることを検査する。`bool` 以外なら `ValueError` とする。`True` と `False` だけを受け付ける。`1`、`0`、`None`、文字列等を暗黙に `bool` へ変換しない。読取り属性名は `collector.apply_copied_tvt_confirmed_ranks` である。外部から読める通常属性とし、property や setter は追加しない。実装後に変更されることを前提としない設定値として扱う。既存の引数なし constructor は、汎用 collector として従来どおり動く。

`_prepare_baseline_fork(real_W, *, target_node_names, baseline_horizon_steps, apply_copied_tvt_confirmed_ranks)` の `apply_copied_tvt_confirmed_ranks` には既定値を付けない。引数が Python の `bool` であることを検査する。`bool` 以外なら `ValueError` とする。暗黙変換はしない。collector 作成は次である。fork へ接続する前に mode を確定する。順位台帳の独立複製は、この関数の引数にしない。TVT 用公開 API が、この関数の戻りを受け取ったあとで行う。

```text
collector = OrderControlBaselineCollector(
    apply_copied_tvt_confirmed_ranks=apply_copied_tvt_confirmed_ranks,
)
```

## 12. 各関数の戻り値

`transfer_tvt_mp_passage_attempts`、`_transfer_one_vehicle_between_links`、`_transfer_normal_merge`、`_finish_node_transfer`、`OrderControlBaselineCollector.__init__` は `None` である。`_prepare_baseline_fork` は、既存の `_BaselineForkPrepared` を返す。成功した台数や clearance 終了フラグは返さない。過去確定群の clearance 終了は、通常 baseline 群を呼ばないことで表現する。通常 baseline 群の clearance 終了は、`enforce_order_control_clearance=True` の helper が残りを処理せず正常 return することで表現する。汎用 baseline fork は、`_transfer_normal_merge()` の正常 return で表す。どの正常経路のあとでも、`Node.transfer` は終了処理を 1 回行う。

## 13. 実Worldとbaseline forkの識別

`transfer_tvt_mp_passage_attempts(node)` は、順位台帳を取得する前に、次の 3 種類を明示的に分類する。これは、台帳が無ければ通常合流へ戻る暗黙の fallback ではない。公開 baseline API が明示した fork 種別に基づく分岐である。

1. 実 World

`collector is None` である。

- TVT 順位を物理適用する。
- Node 別順位台帳を要求する。
- Node 別順位台帳の欠如は `RuntimeError` である。
- driver 正常成功後の最新確定順位を使う。
- snapshot 内の研究対象 Vehicle が未確定なら `RuntimeError` である。
- 通常 baseline 群へ fallback しない。

2. TVT 順位適用 baseline fork

`collector is not None` かつ `collector.apply_copied_tvt_confirmed_ranks is True` である。

- fork World へ明示接続した、登録前の独立複製を使う。
- T-1 以前の確定順位を物理適用する。
- 時刻 T の新規未確定 Visit は、この複製に入っていない。
- Node 別順位台帳を要求する。
- Node 別順位台帳の欠如は `RuntimeError` である。
- 過去確定群を `assigned_rank` 順に先に試す。
- 過去確定群の後に通常 baseline 群を処理する。
- 通常 baseline 群にも order-control clearance を適用する。

3. 汎用 baseline fork

`collector is not None` かつ `collector.apply_copied_tvt_confirmed_ranks is False` である。

- TVT 順位台帳を読まない。
- Node 別順位台帳を要求しない。
- TVT 確定群と通常 baseline 群への分類を行わない。
- `node._transfer_normal_merge()` を呼ぶ。
- `enforce_order_control_clearance` の既定値 `False` を用いる。
- order-control clearance を適用しない。
- 通常の信号交差点の安全上の clearance は、従来どおり信号設定上の全赤時間が担う。
- collector の到着・通過記録は、通常合流と 1 台移動 helper が維持する。
- `transfer_tvt_mp_passage_attempts(node)` は正常 return する。
- その後の `_finish_node_transfer()` は、`Node.transfer` 側が 1 回だけ行う。

`collector.apply_copied_tvt_confirmed_ranks` が `bool` でない場合は `RuntimeError` とする。`1`、`0`、`None`、文字列等を暗黙に `bool` へ変換しない。

collector の有無だけでは、2 種類の baseline fork を区別しない。Node 別順位台帳の有無からも推測しない。`World.copy()` だけでは、実 World 属性と別 object の引数 mapping は fork へ入らない。TVT 用 API が登録前複製を接続したあとの fork 属性が、物理通過の読む台帳である。台帳が無いことを、汎用 baseline fork の印にしない。

実 World の研究実行では、`_order_control_baseline_collector` は `None` のままである。baseline driver が fork へ collector を付ける既存契約は維持する。公開 API の引数は増やさない。mode は、その API が `_prepare_baseline_fork` へ渡す。

## 14. 順位台帳取得

順位台帳を読むのは、実 World と TVT 順位適用 baseline fork だけである。汎用 baseline fork は、この取得へ入らない。Node 別順位台帳を要求しない。台帳が無いことは、汎用 baseline fork では正常である。

到着列が 0 件のときは、通過候補も確認すべき順位もない。実 World と TVT 順位適用 baseline fork は、Node 別順位台帳を要求せず正常 return する。到着が 1 件以上あるときだけ、次を行う。

実 World と TVT 順位適用 baseline fork では、`node.W.order_control_tvt_rank_states_by_node_name` を読む。TVT 順位適用 fork のこの属性は、呼出し側 mapping そのものではなく、登録前の独立複製である。物理通過関数は、ここで台帳を複製しない。次は `RuntimeError` である。

- この属性の型が `dict` でない。
- `node.name` の台帳が無い。
- 台帳の型が `OrderControlTvtNodeRankState` でない。
- `rank_state.node_name` が `node.name` と違う。

物理通過関数は台帳を複製しない。確定も削除もしない。登録時に保証済みの mapping 型、Node 別型、`node_name` 一致を、ここで別契約として増やさない。到着候補があるときの欠如検査は維持する。TVT 順位適用 baseline fork の台帳欠如を、通常合流への暗黙 fallback で隠さない。

## 15. current Visit検査

確定群へ入れる前に、各 Vehicle で次を見る。

- `vehicle.order_control_current_visit` がある。
- `current_visit["node"] is node`。
- `current_visit["inlink"] is vehicle.link`。
- `vehicle.state == "run"`。
- `flag_waiting_for_trip_end` ではない。

最初の 4 件が壊れていれば `RuntimeError` である。trip 終了待ちは例外にせず、確定群にも通常群にも入れない。終了処理が、inlink 先頭の trip 終了待ちを既存どおり処理する。

current Visit 検査を通過し、確定群または通常 baseline 群の候補として残る Vehicle について、次を行う。

```text
outlink = vehicle.route_next_link
if outlink is None:
    raise RuntimeError(...)
```

例外メッセージには、`node.name`、`vehicle.name`、`route_next_link=None`、正常な TVT 通過候補には有効な outlink が必要であることを含める。この検査は、実 World の確定候補、baseline fork の過去確定群、baseline fork の通常 baseline 群に、開始時 snapshot の分類時点で同じように行う。`None` を一時スキップにしない。次時刻まで待たせない。通常 baseline 群へ fallback しない。formal route で補完しない。`route_next_link` を選び直さない。順位、支払、補償、成立時履歴は再計算しない。

## 16. VisitKey

```text
visit_key = (vehicle.name, current_visit["visit_id"])
```

`visit_id` は、`begin_order_control_visit_on_link_entry` を呼ぶ前の値である。通過後の新しい Visit は、この時刻の候補に使わない。

## 17. assigned_rank

確定群では `rank_state.assigned_rank(visit_key)` を使う。confirmed なのに `assigned_rank` が `None` なら `RuntimeError` である。同じ `assigned_rank` が候補内に 2 件あれば `RuntimeError` である。

並びは `assigned_rank` の昇順だけである。Vehicle id、乱数、`merge_priority` は使わない。

## 18. 実進路

確定群と通常 baseline 群の outlink は `vehicle.route_next_link` である。正常な TVT 通過候補では、これは必ず存在する。

- `None` なら `RuntimeError` である。§15 の分類時点で出す。formal route で補完しない。次時刻へ持ち越して解消を待たない。
- `None` でなく、`outlink.start_node is node` でない、または `node.outlinks` に登録されたその Link object でない場合も `RuntimeError` である。

通常合流 helper は、現行どおり `route_next_link` を使う。上書きしない。`allowed_vehicles=None` で通常 Node から呼ばれるときは、現行どおり `route_next_link is None` を outlink 候補から除外する。これは TVT 研究対象 Vehicle の契約ではない。

## 19. formal route

`formal_route_next_link_name` は、通過先の決定に使わない。差の検査も、この実装では追加しない。差があっても `RuntimeError` にしない。順位、支払、補償、成立時履歴は変更しない。差の記録は actual passage・actual outcome の段階である。

## 20. 実Worldの候補分類

collector が `None` のとき、開始時 snapshot の研究対象 Vehicle は全件確定群である。`is_confirmed(visit_key)` が偽なら `RuntimeError` である。通常 baseline 群へ fallback しない。分類時点で `route_next_link is None` なら、確定群へ入れる前に `RuntimeError` である。この分類は、汎用 baseline fork には適用しない。汎用 baseline fork は §13 の通常合流へ入る。

driver 正常成功後は、到着中の研究対象 Vehicle は確定済みである。この例外は、その契約が壊れたときだけ起きる。

## 21. baseline forkの候補2群

この 2 群は、`collector is not None` かつ `collector.apply_copied_tvt_confirmed_ranks is True` のときだけ作る。汎用 baseline fork は、開始時 snapshot をこの 2 群へ分けない。

TVT 順位適用 baseline fork では、開始時 snapshot を次へ分ける。同じ Vehicle は片方だけである。

- fork へ接続した登録前複製で `is_confirmed(visit_key)` が真なら過去確定群である。T-1 以前の確定である。時刻 T の新規未確定 Visit は、この複製に無い。
- それ以外は通常 baseline 群である。未確定、台帳外、T で初めて到着したもの、fork 前進中に到着したものがここへ入る。

通常 baseline 群は、開始時の tuple のまま保持する。過去確定群の後に `incoming_vehicles` から作り直さない。T で新しく到着した研究対象 Visit と、fork 前進中に到着した研究対象 Visit も、正常なら `route_next_link` を持つ。分類時点で current Visit と `route_next_link` を検査し、`None` なら通常群へ入れず `RuntimeError` である。

## 22. 候補snapshot

この snapshot は、実 World と TVT 順位適用 baseline fork だけで作る。汎用 baseline fork は、TVT 用の分類 snapshot を作らず、順位台帳も読まない。

実 World と TVT 順位適用 baseline fork では、`transfer_tvt_mp_passage_attempts` が 3 分類のあと `list(node.incoming_vehicles)` を 1 回作る。0 件なら、順位台帳を読まず正常 return する。1 件以上のときだけ順位台帳を読み、以後の分類と試行はこの list を使う。TVT 順位適用 fork が読む台帳は、登録前に fork World へ接続した独立複製である。

同じ Vehicle object が list に 2 回あれば、2 回目は無視する。例外にはしない。

分類の前に、trip 終了待ちを除く各 Vehicle へ §15 の current Visit 検査と `route_next_link` 検査を行う。`route_next_link is None` はこの時点で `RuntimeError` である。試行直前に、まだ `node.incoming_vehicles` にいるかを見る。いなければ、その 1 台だけをスキップする。

## 23. 確定群の並べ替え

確定群だけを、明示的な list にして `assigned_rank` 昇順で sort する。一度ずつ評価する。スキップしても list から削除しない。台帳からも削除しない。

## 24. 通過可否

評価直前に、次が全部真なら通過させる。

- まだ `incoming_vehicles` にいる。
- `vehicle.link is` 分類時の inlink。
- `inlink.vehicles` が空でない。
- `vehicle is inlink.vehicles[0]`。
- outlink 入口空間がある。条件は現行の通常合流と同じである。`len(outlink.vehicles) < outlink.number_of_lanes`、または入口側車両の `x` が `outlink.delta_per_lane * DELTAN` より大きい。
- `outlink.capacity_in_remain >= node.W.DELTAN`。
- `inlink.capacity_out_remain >= node.W.DELTAN`。
- `node.flow_capacity_remain >= node.W.DELTAN`。
- clearance が不要か、すでに満たされている。

`vehicle.link` が分類時の inlink と違う場合は、一時スキップにしない。§15 の Visit と link の対応が壊れているので `RuntimeError` である。`route_next_link is None` は、この通過可否の一時スキップではない。§15 の分類時点で既に `RuntimeError` である。

通常 baseline 群の選択順は §30 の通常合流である。`enforce_order_control_clearance=True` のとき、選ばれた Vehicle の通過前に、上と同じ order-control clearance を確認する。未充足は一時スキップではなく、その時刻の通常群処理の終了である。

## 25. 一時スキップ

次は `continue` である。例外にしない。台帳からも到着列からも、この理由では削除しない。

- もう `incoming_vehicles` にいない。
- 物理先頭でない。
- Node 流量不足。
- inlink 流出容量不足。
- outlink 流入容量不足。
- outlink 入口空間不足。

`route_next_link is None` は、この一覧に入れない。§15 の `RuntimeError` である。スキップした Vehicle は、同じ呼出しの通常 baseline 群へ入れない。

## 26. clearance

別 inlink のときだけ確認する。同一 inlink、または `last_order_control_inlink is None` なら不要である。

`last_order_control_inlink` と `last_order_control_entry_timestep` の片方だけが `None` なら `RuntimeError` である。

別 inlinkで、次が偽なら未充足である。

```text
node.W.T - node.last_order_control_entry_timestep
> node.order_control_clearance_timesteps
```

この比較は strict greater-than である。直前の別 inlink の通過時刻を T とする。

- `order_control_clearance_timesteps=0` では、T では通過できない。T+1 で通過できる。
- `order_control_clearance_timesteps=1` では、T+1 では通過できない。T+2 で通過できる。

したがって clearance 設定値0でも、同一 timestep 内の別 inlink 通過は禁止される。clearance 設定値1では、間の 1 timestep を確実に空ける。order-control clearance について、「clearanceなし」という語は使わない。

この order-control clearance は、実 World の TVT 確定群、baseline fork の過去確定群、baseline fork の通常 baseline 群に同じ条件で適用する。通常 baseline 群は、車両の選択順を通常合流のままにし、選んだ Vehicle を通す前にこの条件を確認する。

過去確定群で未充足なら、確定群の残りを見ない。通常 baseline 群も呼ばない。例外にはしない。関数は `None` で戻る。`Node.transfer` が終了処理を 1 回行う。

通常 baseline 群で未充足なら、例外にしない。その時刻の通常群処理を終了し、後続の通常 baseline Vehicle を処理しない。共通の終了処理へ進み、次時刻に再評価する。

通過成功の直後、移動前の inlink を `last_order_control_inlink` に入れ、`last_order_control_entry_timestep` を `node.W.T` にする。この更新は 1 台移動 helper の中では行わない。TVT 確定群の試行側と、`enforce_order_control_clearance=True` の通常合流 helper が、1 台移動 helper の正常 return の後に行う。一時スキップでは更新しない。

`order_control_type="none"` の標準の信号交差点では、この order-control clearance を使わない。信号設定として明示した全赤時間を使う。UXsim が全赤時間を自動で付けることには依存しない。この全赤時間と、order-control clearance 設定値0・1は、別の実装方式である。研究評価の基本方式は、安全のための clearance ありである。研究評価で使う clearance 値は、各実験設定に従う。本仕様で新しい数値は決めない。比較と回帰確認では、clearance 設定値0と clearance 設定値1の双方を確認できる。

## 27. 1台物理移動

`_transfer_one_vehicle_between_links` は次の順で行う。現行の通常合流の 1 台移動と同じ更新である。

1. 移動前の `current_visit["visit_id"]` を局所変数へ取る。現在 Visit が無ければ `None` とする。
2. collector が `None` でなければ `prepare_baseline_passage_recording` を呼ぶ。引数は車両名、その visit id、`node.name` である。
3. `inlink.cum_departure[-1]` と `outlink.cum_arrival[-1]` を `DELTAN` だけ増やす。
4. `inlink.traveltime_actual` を、現行と同じ範囲で更新する。
5. `vehicle.link_arrival_time` を `W.T * W.DELTAT` にする。
6. inlink 流出、outlink 流入を `DELTAN` だけ減らす。`flow_capacity` が `None` でなければ Node 流量も減らす。
7. `inlink.vehicles.popleft()`。
8. `outlink.vehicles_enter_log` へ記録する。
9. `vehicle.link = outlink`。
10. `vehicle.begin_order_control_visit_on_link_entry()`。
11. `x`、follower、leader、lane、`move_remain`、`v` を現行と同じ式で更新する。
12. 移動後の inlink 先頭が trip 終了待ちなら、その 1 台を `end_trip` する。
13. `outlink.vehicles.append(vehicle)`。
14. `incoming_vehicles` からその Vehicle を削除する。
15. prepare の戻りが `None` でなければ `apply_baseline_passage_timestep` を、現在の `W.T` で呼ぶ。

新しい rollback は作らない。prepare の後に移動が失敗した場合、現行の通常合流と同じく、そこまでの変更は戻さない。collector の例外は別の例外で包まない。

## 28. clearance状態更新

TVT 確定群と、baseline fork の通常 baseline 群は、通過成功後に order-control clearance 履歴を更新する。一時スキップでは更新しない。

`order_control_type="none"` の通常合流は、`enforce_order_control_clearance=False` であり、order-control clearance 履歴を更新しない。通常の信号交差点の全赤時間は、信号設定側で扱う。1 台移動 helper は、どちらの履歴も更新しない。

## 29. 通常baseline群

この呼出しは、TVT 順位適用 baseline fork だけである。汎用 baseline fork は、この許可集合を作らない。汎用 baseline fork の正式呼出しは `node._transfer_normal_merge()` であり、`enforce_order_control_clearance` は既定の `False` である。

TVT 順位適用 baseline fork で過去確定群の clearance 終了がなければ、開始時 tuple の通常 baseline 群を次で渡す。tuple が空なら呼ばない。

```text
node._transfer_normal_merge(
    allowed_vehicles=ordinary_baseline_vehicles,
    enforce_order_control_clearance=True,
)
```

実 World では、この helper を TVT 側から呼ばない。未確定は例外であり、通常群ではない。

## 30. 許可集合付き通常合流

`allowed_vehicles is None` のときは、現行の通常合流と同じく、その時点の `incoming_vehicles` 全体から outlink 候補を作る。

tuple のときは、その tuple に含まれる Vehicle だけから outlink 候補を作る。車両選択も、その tuple に含まれ、まだ `incoming_vehicles` にいる Vehicle だけである。

どちらも、現行と同じく次を維持する。

- outlink の車線数だけ試行を並べる。
- `hard_deterministic_mode` でなければ、その outlink 列を `W.rng.shuffle` する。
- `signal_phase` と `signal_group`、または `len(signal) <= 1`。
- `merge_priority`。合計が 0 なら一様にする。
- hard deterministic のときは、現行と同じ最大 priority の選択。
- 入口空間と容量は、試行時点の live 値。
- 1 台移動は `_transfer_one_vehicle_between_links`。

`time_value` Node は無信号であり、`signal` は `[0]` である。helper 内の既存信号条件は、その Node では通過を止めない。TVT 専用の信号条件は足さない。TVT の安全時間は order-control clearance が担う。

`enforce_order_control_clearance=True` のときは、選ばれた Vehicle の通過前に §26 の order-control clearance を確認する。同一 inlink、または `last_order_control_inlink is None` なら、order-control clearance 上は通過できる。別 inlink で未充足なら、helper は正常 return し、残りの許可集合を処理しない。通過成功後は、移動前 inlink と現在の `W.T` で clearance 履歴を更新する。その後の別 inlink は、同じ時刻にはこの条件を満たさない。同じ inlink の後続は、容量等を満たせば、order-control clearance 上の追加待機は不要である。履歴の片側だけが `None` なら `RuntimeError` である。

標準 UXsim の通常合流と、汎用 baseline fork からの正式呼出しは `node._transfer_normal_merge()` である。既定の `False` では、order-control clearance を検査せず、その履歴も更新しない。汎用 baseline fork で台帳が無いことは、この呼出しを選ぶ理由ではない。mode が `False` だから、この呼出しを選ぶ。`allowed_vehicles=None` のときは、現行どおり `route_next_link is None` の Vehicle を outlink 候補から除外する。通常合流 helper のこの一般契約は変えない。

`allowed_vehicles=ordinary_baseline_vehicles` で呼ぶときは、呼出し前に TVT 物理通過関数が、その tuple の `route_next_link` が全件有効であることを保証している。helper 内で `None` を容量待ちへ変えない。

許可集合の実装は、多重の内包表記にしない。outlink を明示的な loop で集め、`allowed_vehicles is None` のときの並びは、現行の `incoming_vehicles` 順と同じにする。

## 31. 通常Node回帰

許可集合を省略した通常 Node は、次を変えない。

- outlink 候補の生成順
- 車線数に応じた試行回数
- shuffle
- 信号判定
- `merge_priority`
- RNG の呼出し順
- hard deterministic
- 物理移動の更新
- collector 記録
- trip 終了処理
- `incoming_vehicles` の全消去
- order-control clearance 履歴を更新しないこと

通常の信号交差点では、次だけを維持する。

- order-control clearance 履歴を使わない。
- 信号設定として明示した全赤時間を使う。
- 全赤時間を、UXsim の自動付与へ依存しない。

order-control clearance を通常 Node へ重ねて追加しない。既存名に `no_clearance` を含む関数がある。名称は変更しない。本節の clearance 設定値0とは区別する。関数名と実装は今回変更しない。研究評価の基本方式は、安全のための clearance ありである。

固定 seed の正式サンプルの数値が変わることは、回帰失敗である。

## 32. incoming_vehicles終了処理

通過成功 Vehicle は、1 台移動 helper が到着列から削除する。

一時スキップした Vehicle と、通れなかった通常群 Vehicle は、到着列に残ってよい。`Node.transfer` の最後の `_finish_node_transfer` が、到着列を空にする。

FCFS と BATCH も、途中終了のあと到着列を空にする。リンク終端に残った Vehicle は、同じ時刻の後段の `Vehicle.update` が再登録する。TVT も同じである。

`_finish_node_transfer` を、TVT 分岐と通常分岐の両方で、正常 return のあと 1 回だけ呼ぶ。`_transfer_normal_merge` は呼ばない。TVT 関数も呼ばない。clearance 終了でも、通常群を処理したあとでも、この 1 回だけである。

例外が `transfer_tvt_mp_passage_attempts` または `_transfer_normal_merge` から出た場合は、終了処理を呼ばない。現行の FCFS が途中例外で最後の全消去へ到達しないことと同じである。新しい `try` / `finally` は足さない。

## 33. trip終了待ち

`_finish_node_transfer` は、現行の通常合流末尾と同じ loop である。各 inlink の各車線について、先頭が `flag_waiting_for_trip_end` なら `end_trip` し、そうでなければその車線の確認を終える。

1 台移動の直後に、移動した inlink の新しい先頭が trip 終了待ちなら、その場でも `end_trip` する。これは現行の通常合流と同じであり、終了処理とは別の 1 台である。終了処理を 2 回呼ぶことではない。

## 34. baseline collector

collector は、汎用 baseline fork と TVT 順位適用 baseline fork の両方で `None` でない。mode は `apply_copied_tvt_confirmed_ranks` で区別する。mode は順位台帳を保持しない。TVT 用 API が登録前複製を fork World へ接続する。通過成功時だけ、1 台移動 helper が prepare と apply を 1 回行う。容量不足や入口不足では prepare しない。汎用 baseline fork の通常合流でも、この記録は維持する。mode は記録を止めない。

prepare の `visit_id` は、`begin_order_control_visit_on_link_entry` より前の current Visit ID である。現在 Visit が無ければ、現行の通常合流と同じく `visit_id=None` を渡す。

実 outlink が登録済み `route_next_link_name` や formal route と違っても、一致検査は追加しない。同じ Visit の二重 apply は、既存 collector が拒否する。その例外は包まない。

## 35. downstream boundary observer

`exec_simulation` の外側を維持する。

1. `capture_before_transfer`
2. `node.transfer`
3. `commit_after_transfer`
4. `finally` で `clear_pending`

`transfer_tvt_mp_passage_attempts`、`_transfer_normal_merge`、`_transfer_one_vehicle_between_links`、`_finish_node_transfer` は observer を呼ばない。`Node.transfer` の中でも呼ばない。

## 36. 通過済みVisit

通過済み VisitKey 集合は作らない。通過した Vehicle は到着列から削除される。次 Node が制御対象なら、リンク進入時に新しい `visit_id` の Visit ができる。対象外なら `order_control_current_visit` は `None` になる。順位台帳の確定は履歴として残す。

## 37. 重大不整合

`RuntimeError` にするのは、次だけである。

- 到着候補がある実 World または TVT 順位適用 baseline fork で、順位台帳の型、欠如、`node_name` 不一致。到着列が 0 件のときは、ここへ入れない。汎用 baseline fork の台帳欠如は、ここへ入れない。
- `collector.apply_copied_tvt_confirmed_ranks` が `bool` でない。暗黙変換しない。
- 現在 Visit が無い。
- 現在 Visit の Node または inlink が、その Vehicle の現在 link と一致しない。
- `state` が `"run"` でない。ただし trip 終了待ちは §15 のとおり候補外であり、例外にしない。
- 実 World で、到着中の研究対象 Visit が confirmed でない。
- confirmed なのに `assigned_rank` が `None`。
- 同じ `assigned_rank` が確定群に 2 件ある。
- `route_next_link is None`。これは実 World の確定候補、baseline fork の過去確定群、baseline fork の通常 baseline 群で同じである。開始時分類で出す。
- `route_next_link` が別 Node の Link、または `node.outlinks` の登録 object でない。
- clearance 履歴の片側だけが `None`。これは TVT 確定群でも、`enforce_order_control_clearance=True` の通常 baseline 群でも同じである。

物理先頭でないこと、容量不足、入口空間不足、clearance 未充足は例外にしない。目的地到着の trip 終了待ち、outlink が無い trip abort、局所仮想計算が World 全体の copy で `route_next_link is None` を許容する確認は、この `RuntimeError` の対象ではない。

## 38. 例外型

TVT 物理通過が新しく出す例外は `RuntimeError` である。メッセージには `node.name` を含める。Vehicle が分かっているときは `vehicle.name` も含める。`route_next_link is None` のメッセージには、加えて `route_next_link=None` と、正常な TVT 通過候補には有効な outlink が必要であることを含める。`apply_copied_tvt_confirmed_ranks` が `bool` でないときも `RuntimeError` である。

`OrderControlBaselineCollector.__init__` と `_prepare_baseline_fork` は、`apply_copied_tvt_confirmed_ranks` が Python の `bool` でなければ `ValueError` とする。`1`、`0`、`None`、文字列等は変換しない。collector が既に出す `ValueError` や `RuntimeError` は、そのまま伝播する。

## 39. 例外時の変更状態

新しい rollback は作らない。例外より前に通過した Vehicle の移動、容量、台帳、支払は戻さない。終了処理は、例外が外へ出た呼出しでは実行されない。`incoming_vehicles` に残った Vehicle は、その時点の list のままである。

## 40. live状態の変更範囲

変更してよいのは、通過した Vehicle と、その inlink、outlink、Node の容量、累積、旅行時間、TVT 確定群または baseline 通常群の通過成功後の order-control clearance 履歴、到着列、trip 終了、baseline collector の通過時刻である。`order_control_type="none"` の通常合流は、order-control clearance 履歴を変更しない。

変更しないのは、順位台帳の確定と未確定、支払、補償、成立時履歴、`route_next_link`、formal route、`order_control_eligible`、`order_control_type`、評価終了時刻、observer の呼出しである。

## 41. 不変性

- 確定順位は、通過できなくても削除しない。
- 過去の確定を解除しない。
- T の新しい確定も、T の新規未確定 Visit も、fork の台帳へ書かない。fork 側台帳は登録前の独立複製であり、元台帳と object を共有しない。
- formal route を実進路へ上書きしない。
- `route_next_link is None` を formal route で補完しない。
- `route_next_link` を物理接続処理で選び直さない。
- `route_next_link is None` を待機状態へ変換しない。
- 到着列を別 list へ差し替えない。削除は、通過した 1 台と、最後の全消去だけである。
- FCFS と BATCH の関数本体を編集しない。
- `order_control_type="none"` の通常合流で、order-control clearance 履歴を更新しない。
- 通常の信号交差点の全赤時間を、UXsim の自動付与へ移さない。明示した信号設定のままとする。
- collector の有無だけで、2 種類の baseline fork を同一視しない。
- Node 別順位台帳の有無から、fork 種別を推測しない。
- 汎用 baseline fork へ、T-1 以前の TVT 順位を強制しない。
- TVT 順位適用 baseline fork の台帳欠如を、通常合流へ黙って戻さない。
- 既存 baseline 回帰の期待値を、失敗を隠すために変更しない。

## 42. driverとの関係

`Node.transfer` は `run_tvt_mp_driver` を呼ばない。driver は、これまでどおり `exec_simulation` の時刻先頭で動く。実 World の `Node.transfer` は、その戻りより後なので、最新の確定順位を読む。

driver、atomic apply、支払、final rank、順位台帳型は変更しない。

## 43. baseline forkとの関係

fork は、T の未確定登録と確定より前に copy される。既存の baseline driver はこの順を維持する。copy 直後の fork 属性は、実 World 属性の pickle 複製である。引数 mapping が実 World 属性と別 object なら、その pickle 複製には引数 mapping の台帳が入らない。その有無で fork 種別を決めない。

`_prepare_baseline_fork` の呼出し元は、次の 2 か所だけである。両方とも同じ `_prepare_baseline_fork` を使う。公開引数は変えない。

- `run_snapshot_fixed_baseline_fork()` は、`apply_copied_tvt_confirmed_ranks=False` を明示的に渡す。順位台帳の独立複製は行わない。
- `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` は、`apply_copied_tvt_confirmed_ranks=True` を明示的に渡す。

TVT 用 API の正式な内部順は次である。公開 signature は変えない。

1. `prepared = _prepare_baseline_fork(..., apply_copied_tvt_confirmed_ranks=True)`。
2. `plan = prepare_snapshot_fixed_visit_registration_plan(...)`。
3. `rank_states_by_node_name` の対象 Node 検査。欠如、型、`node_name` 不一致は、複製より前に既存の登録前検査で確認する。
4. 登録前台帳の独立複製。`frozen_rank_states_by_node_name = copy.deepcopy(dict(rank_states_by_node_name))`。
5. `prepared.fork_W.order_control_tvt_rank_states_by_node_name = frozen_rank_states_by_node_name`。
6. `register_undetermined_visits_from_snapshot_plan(plan, rank_states_by_node_name)`。元の呼出し側 mapping だけへ適用する。
7. `apply_snapshot_fixed_visit_registration_plan(plan, prepared.collector)`。
8. baseline forward。

時刻 T の未確定 Visit は、元の呼出し側台帳だけへ登録する。fork 側の独立複製には追加しない。fork 側 mapping と元 mapping は同じ object ではない。各 Node の rank state も同じ object ではない。fork 側の変更は元台帳へ伝播せず、元台帳の後続変更も fork へ伝播しない。正常な driver 経路と、baseline API 単独経路は、この同じ契約にする。

汎用 baseline fork の前進は、従来の通常合流である。TVT 順位台帳を読まない。TVT 順位適用 baseline fork の前進は、上の独立複製と、mode が `True` の collector を使う。T で元台帳へ追加された未確定 Visit と、その後の確定は、fork へ伝播しない。登録 Visit が 0 件のとき forward しない既存契約は維持する。horizon 全量と、fork で終了集計を呼ばない契約も維持する。

## 44. 局所仮想計算との関係

`scan_and_transfer_tvt_mp_binding_visits_at_current_timestep` は呼ばない。変更しない。

理由は、それが候補の拘束順位列専用であること、formal route の不一致を例外にすること、通過済み集合を使うこと、今回の実 World と baseline fork の契約と違うことである。

## 45. evaluation endとの関係

評価終了時刻、自動起動、実 World を内部余白へ進めないこと、終了集計を 1 回にすることは変更しない。fork は評価終了時刻を `None` にしたまま、horizon を計算する。

## 46. actual passage・actual outcomeへの接続点

接続点は、`_transfer_one_vehicle_between_links` が apply を終えた直後である。今回は、そこに記録関数を呼ばない。field 名、型名、status 名も決めない。

次段階では、通過前の VisitKey、実通過時刻、実 inlink、実 outlink、formal route との差を、この位置へ追加できる。未通過は未観測とする。

## 47. 実装対象ファイル

変更する。

- `uxsim/uxsim.py`。`Node.transfer` の分岐、3 つの private method だけである。FCFS と BATCH の関数本体は変更しない。
- `uxsim/order_control_baseline_collector.py`。`apply_copied_tvt_confirmed_ranks` の constructor 引数、型検査、読取り属性を追加する。既存の引数なし constructor は残す。
- `uxsim/order_control_baseline_driver.py`。`_prepare_baseline_fork` へ既定値のない `apply_copied_tvt_confirmed_ranks` を追加する。2 つの公開 API の引数は変えない。汎用 API は `False`、TVT 順位台帳登録付き API は `True` を明示的に渡す。TVT 用 API は、さらに登録前の `copy.deepcopy` を fork World へ接続し、未確定登録は元 mapping だけへ適用する。

新規作成する。

- `uxsim/order_control_tvt_mp_physical_transfer.py`
- `tests_order_control_tvt_mp_physical_transfer.py`

既存テストへ mode 契約を追加する。今回の文書作業では、これらのテストファイルは変更しない。

- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`。ここに `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` を追加する。登録前複製の独立性は、物理通過の専用テストではなく、TVT 用 baseline API の責務としてこのファイルで固定する。

必要な場合は、既存の baseline fork alignment テストに mode 確認を追加してよい。その追加も、専用テスト件数には含めない。fork alignment の既存期待値は、この接続を実装するまで変更しない。

既存テストは、次の 2 件だけ期待を更新する。どちらも、`Node.transfer` のソースに TVT 物理通過が無いことを検査している。実装後は、その検査が偽になる。

- `tests_order_control_tvt_mp_driver.py` の `test_exec_simulation_connects_driver_but_node_transfer_does_not`
- `tests_order_control_tvt_mp_evaluation_end.py` の `test_node_transfer_does_not_use_tvt_rank`

更新後の契約は、`Node.transfer` が `run_tvt_mp_driver` を呼ばないこと、`transfer_tvt_mp_passage_attempts` を `time_value` 分岐から呼ぶこと、である。driver を `Node.transfer` へ移す期待にはしない。

TVT-MP driver、atomic apply、支払、順位台帳型、局所仮想計算は変更しない。baseline collector と baseline driver は、上の明示 mode だけを変更する。既存の公開 baseline API は削除しない。

## 48. 新規専用テスト

正式ファイル名は `tests_order_control_tvt_mp_physical_transfer.py` である。

直接実行と pytest の両方で動かす。専用テスト件数は、このファイルの 34 件だけを指す。33 件へ空の到着列の 1 件を加えた件数である。collector、baseline driver、登録前複製の独立性は、関係回帰として別に記録し、この 34 件へ含めない。1 テストに複数の独立シナリオを詰め込まない。同じ通過を別テストで繰り返さないため、容量不足の種類は 1 テストの中の明示的な case 列とする。order-control clearance の別契約は、別の test 関数に分ける。clearance 設定値0と clearance 設定値1の off-by-one は、同じ test へまとめない。汎用 baseline fork と TVT 順位適用 baseline fork の契約も、別の test 関数に分ける。

## 49. test関数一覧

1. `test_time_value_branch_is_only_for_eligible_time_value`
2. `test_candidates_are_only_current_incoming_vehicles`
3. `test_does_not_retry_passed_or_unarrived_visits`
4. `test_attempts_follow_assigned_rank_not_baseline_order`
5. `test_nonparticipant_attempts_in_confirmed_rank`
6. `test_passage_uses_live_route_next_link_without_rewriting_ledger_or_payments`
7. `test_temporary_skip_tries_the_next_rank`
8. `test_clearance_ends_the_timestep_and_the_next_timestep_retries`
9. `test_clearance_zero_allows_different_inlink_only_from_next_timestep`
10. `test_clearance_one_requires_one_full_empty_timestep`
11. `test_finish_runs_once_and_ends_waiting_trips`
12. `test_broken_current_visit_or_unconfirmed_on_real_world_raises`
13. `test_fork_ledger_stays_at_pre_decision_confirms`
14. `test_fork_tries_past_confirmed_before_ordinary_group`
15. `test_skipped_past_confirmed_vehicle_is_excluded_from_ordinary_merge`
16. `test_clearance_stop_skips_ordinary_group`
17. `test_ordinary_group_keeps_merge_priority_and_hard_deterministic_choice`
18. `test_ordinary_group_sees_capacity_after_past_confirmed_passage`
19. `test_ordinary_group_stops_on_unmet_order_control_clearance`
20. `test_ordinary_passage_updates_order_control_clearance_history`
21. `test_same_inlink_ordinary_group_needs_no_extra_clearance_wait`
22. `test_different_inlink_after_passage_does_not_pass_in_the_same_timestep`
23. `test_ordinary_signal_node_does_not_update_order_control_clearance_history`
24. `test_collector_prepare_and_apply_once_per_passage`
25. `test_transfer_does_not_call_downstream_observer`
26. `test_zero_visits_skip_forward_and_fork_does_not_terminate`
27. `test_ordinary_node_merge_is_unchanged`
28. `test_fcfs_and_batch_return_before_tvt`
29. `test_route_next_link_none_is_runtime_error_for_tvt_candidate`
30. `test_generic_baseline_fork_uses_ordinary_merge_without_rank_ledger`
31. `test_tvt_rank_applying_baseline_fork_applies_copied_confirmed_ranks`
32. `test_tvt_rank_applying_baseline_fork_missing_node_ledger_is_runtime_error`
33. `test_empty_incoming_vehicles_do_not_require_rank_ledger`
34. `test_registry_matches_defined_functions`

`test_temporary_skip_tries_the_next_rank` は、物理先頭でない、Node 流量不足、inlink 流出不足、outlink 流入不足、入口空間不足を、別々の小さな case としてこの関数の中で確認する。それぞれで後続順位を試す。`route_next_link is None` はこの関数へ入れない。

`test_route_next_link_none_is_runtime_error_for_tvt_candidate` は、同じ分類検査を共有する 3 つの明示的な case である。実 World の確定候補、baseline fork の過去確定群、baseline fork の通常 baseline 群で、`route_next_link is None` なら `RuntimeError` であることを確認する。例外メッセージに Node 名と Vehicle 名が含まれること、Vehicle は通過していないこと、formal route へ上書きされていないこと、順位台帳、支払、補償、成立時履歴が変わらないことを確認する。

`test_clearance_ends_the_timestep_and_the_next_timestep_retries` は、clearance 未充足でその時刻を終え、次時刻に再評価することを確認する。clearance 設定値0と clearance 設定値1の off-by-one は、この 1 件だけでは固定しない。

`test_clearance_zero_allows_different_inlink_only_from_next_timestep` は、`order_control_clearance_timesteps=0` の別 inlink が、直前通過と同じ timestep では通れず、次の timestep で通れることを確認する。

`test_clearance_one_requires_one_full_empty_timestep` は、`order_control_clearance_timesteps=1` の別 inlink が、次の timestep では通れず、次の次の timestep で通れることを確認する。間の 1 timestep を空ける。同一 inlink には、この方向切替の待機を要求しない。

`test_fork_ledger_stays_at_pre_decision_confirms` は、copy 後に実 World へ確定を足しても fork 台帳が変わらないことと、T の新順位を baseline の通過へ使わないことを確認する。

`test_zero_visits_skip_forward_and_fork_does_not_terminate` は、登録 Visit 0 件で forward しないこと、horizon を計算する fork が終了集計を呼ばないこと、評価終了の内部余白契約を崩さないことを確認する。

`test_broken_current_visit_or_unconfirmed_on_real_world_raises` は、現在 Visit の欠如、Node または inlink の不一致、実 World の未確定を `RuntimeError` として確認する。容量不足を例外にしないことも確認する。

`test_ordinary_group_stops_on_unmet_order_control_clearance` は、通常 baseline 群の order-control clearance が未充足なら、後続の通常群を処理しないことを確認する。`test_clearance_stop_skips_ordinary_group` は、過去確定群の未充足で通常群を開始しないことを確認する。この 2 件は分けたままとする。

`test_ordinary_passage_updates_order_control_clearance_history` は、通常群の通過成功後に `last_order_control_inlink` と `last_order_control_entry_timestep` が更新されることを確認する。`test_same_inlink_ordinary_group_needs_no_extra_clearance_wait` は、過去確定群と同じ inlink の通常群が、容量等を満たせば order-control clearance 上の追加待機なしで通れることを確認する。`test_different_inlink_after_passage_does_not_pass_in_the_same_timestep` は、過去確定群の通過直後の別 inlink の通常群と、通常群で 1 台通過した直後の別 inlink の後続が、同じ時刻には通らないことを確認する。

`test_ordinary_signal_node_does_not_update_order_control_clearance_history` は、`order_control_type="none"` の通常合流が order-control clearance 履歴を更新しないことを確認する。全赤時間を UXsim が自動で足すことは確認しない。明示した信号設定が、既存の信号判定のまま残ることを確認する。

`test_generic_baseline_fork_uses_ordinary_merge_without_rank_ledger` は、`apply_copied_tvt_confirmed_ranks is False` の汎用 baseline fork が、`time_value` Node でも TVT 順位台帳を要求せず、通常合流で前進することを確認する。Node 別順位台帳が無いことは正常である。

`test_tvt_rank_applying_baseline_fork_applies_copied_confirmed_ranks` は、`apply_copied_tvt_confirmed_ranks is True` の TVT 順位適用 baseline fork が、コピー済み確定順位を物理適用することを確認する。過去確定群を通常 baseline 群より先に試す。

`test_tvt_rank_applying_baseline_fork_missing_node_ledger_is_runtime_error` は、到着候補がある TVT 順位適用 baseline fork で必要な Node 別順位台帳が欠けていれば `RuntimeError` であることを確認する。通常合流へ黙って戻さない。

`test_empty_incoming_vehicles_do_not_require_rank_ledger` は、到着列が 0 件なら、実 World と TVT 順位適用 baseline fork が Node 別順位台帳を要求せず正常 return することを確認する。汎用 baseline fork の mode `False` も維持する。交通状態、順位台帳、collector 記録は変えない。`Node.transfer` 経由では `_finish_node_transfer` が 1 回だけ動く。

`test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` は、この 34 件へ入れない。置くファイルは `tests_order_control_tvt_baseline_driver_registration.py` である。確認するのは、元台帳に T-1 以前の確定順位があること、TVT 用 baseline API を呼ぶこと、fork 側はその確定順位を使うこと、時刻 T の未確定 Visit は元台帳へ登録されること、fork 側には T の新規未確定 Visit が入らないこと、fork 側台帳と元台帳が別 mapping object であること、各 Node の rank state も別 object であること、元台帳の後続変更が fork へ伝播しないこと、fork 側の変更も元台帳へ伝播しないことである。

## 50. TESTS登録

`tests_order_control_tvt_mp_driver.py` と同じ方式にする。`test_` で始まる関数を定義順に `TESTS` tuple へ集める。件数は §49 の 34 件である。最後は `test_registry_matches_defined_functions` であり、定義と `TESTS` の一致を確認する。`__main__` では `TESTS` を順に実行する。collector、baseline driver、登録前複製の独立性は、この `TESTS` へ入れない。

## 51. 関係回帰

関係回帰として、既存ファイルへ次の mode 契約を追加する。この契約は、専用テスト 34 件へ含めない。

- `tests_order_control_baseline_collector.py` で、`apply_copied_tvt_confirmed_ranks` の既定値が `False` であることを確認する。
- 同じ collector テストで、constructor へ `bool` 以外を渡せば `ValueError` であることを確認する。暗黙変換しない。
- `tests_order_control_baseline_driver.py` で、`run_snapshot_fixed_baseline_fork()` が `_prepare_baseline_fork()` へ `False` を明示的に渡すことを確認する。
- `tests_order_control_tvt_baseline_driver_registration.py` で、`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` が `_prepare_baseline_fork()` へ `True` を明示的に渡すことを確認する。

`_prepare_baseline_fork` が `bool` 以外を `ValueError` にすることも、baseline driver 側の関係回帰で確認する。専用テスト 34 件へは含めない。

`tests_order_control_tvt_baseline_driver_registration.py` の `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` も、専用テスト 34 件へ含めない。登録前複製の独立性を、このファイルで確認する。

実装後に次を実行する。

- `tests_order_control_tvt_mp_physical_transfer.py`
- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_evaluation_end.py`
- FCFS と BATCH の既存 `Node.transfer` テスト
- 既存関数 `transfer_fcfs_no_clearance` の回帰。既存名は `no_clearance` を含むが、名称だけから `order_control_clearance_timesteps=0` と同じ意味だと推測しない。本節の clearance 設定値0とは区別する。関数名と実装は今回変更せず、その意味も今回再定義しない。比較・回帰確認用として維持する。

§47 の 2 テストは、更新後のソース契約で成功させる。それ以外の既存アサーションは、失敗したら本番を合わせて黙って期待値を変えない。失敗内容を報告して止まる。

TVT 物理通過の作業中実装では、`tests_order_control_baseline_driver.py`、`tests_order_control_tvt_baseline_fork_alignment.py`、`tests_order_control_tvt_mp_evaluation_end.py` の一部が、`RuntimeError: Node junction: TVT rank ledger is missing.` で失敗した。既存テストの期待値は変更していない。汎用 fork と空の到着列については、未保存の明示 mode と空 snapshot の正常 return で、baseline driver と evaluation end は成功している。fork alignment の残りは、呼出し側 mapping が実 World 属性と別 object のとき、登録前複製が fork へ接続されていないことが原因である。対処は、本節の登録前 `copy.deepcopy` である。失敗を隠すための期待値変更ではない。接続の実装後に、fork alignment と baseline driver registration を再実行する。

## 52. 正式サンプル回帰

`demos_and_examples/example_00en_simple.py` を実行する。評価終了時刻は未設定のままである。completed trips、average speed、旅行時間、delay、走行距離が、保存済みの従来結果と一致することを確認する。このサンプルの信号設定を、全赤時間の自動追加へ変更しない。研究評価で信号交差点を使うときは、青と次の青の間の全赤時間を信号設定として明示する。

## 53. py_compile

次を `py_compile` する。

- `uxsim/uxsim.py`
- `uxsim/order_control_tvt_mp_physical_transfer.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_driver.py`
- `tests_order_control_tvt_mp_physical_transfer.py`
- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`
- §47 で期待を更新した 2 つの既存テスト

登録前複製を足したあとも、上の `order_control_baseline_driver.py` と `tests_order_control_tvt_baseline_driver_registration.py` を `py_compile` する。物理通過 module へ `copy` を足すことは、この契約の実装ではない。

## 54. git diff --check

実装後に `git diff --check` を実行する。空白エラーは残さない。

## 55. 実装順序

物理通過、明示 mode、空の到着列の正常 return は、未保存のまま残っている。次の登録前複製は、その差分を消さずに足す。

1. `Node.transfer` の通常合流を、`_transfer_one_vehicle_between_links`、`_transfer_normal_merge`、`_finish_node_transfer` へ移す。この時点では `time_value` 分岐を足さない。通常 Node の結果が変わらないことを確認する。
2. `time_value` 分岐と `transfer_tvt_mp_passage_attempts` を足す。
3. collector へ `apply_copied_tvt_confirmed_ranks=False` を追加する。`_prepare_baseline_fork` には既定値のない同じ引数を追加する。汎用 API は `False`、TVT 順位台帳登録付き API は `True` を明示的に渡す。
4. `transfer_tvt_mp_passage_attempts` は、順位台帳を読む前に §13 の 3 分類を行う。到着列が 0 件なら、その後の台帳要求の前に正常 return する。
5. 新規専用テスト 34 件を足す。mode の関係回帰は、§51 の既存テストファイルへ別に足す。
6. §47 の 2 テストだけを、新しいソース契約へ更新する。既存 baseline 回帰の期待値は、失敗を隠すために変えない。
7. `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` へ、§43 の登録前 `copy.deepcopy` と fork への明示接続を足す。
8. `tests_order_control_tvt_baseline_driver_registration.py` へ独立性テストを足す。専用テスト 34 件には入れない。
9. fork alignment と baseline driver registration を再実行し、その後 §51 から §54 を実行する。

## 56. 独立確認手順

実装報告だけで完了にしない。確認する人は、次を自分で見る。

- `Node.transfer` の分岐順が §6 と一致する。
- FCFS と BATCH の関数本体の diff が空である。
- 物理通過 module が formal route を通過先に使っていない。
- 通過済み集合の属性を追加していない。
- `apply_copied_tvt_confirmed_ranks is True` の fork だけが、confirmed を確定群として試している。
- `apply_copied_tvt_confirmed_ranks is False` の fork は、順位台帳を読まず、通常合流で前進している。
- `_finish_node_transfer` が `Node.transfer` の正常経路で 1 回だけ呼ばれる。
- 専用テスト 34 件、§51 の関係回帰、正式サンプル、`py_compile`、`git diff --check` の結果。
- TVT 用 API が、未確定登録より前に `copy.deepcopy` し、その複製だけを fork World へ接続していること。
- 時刻 T の未確定 Visit が元台帳だけにあり、fork 側の mapping と各 Node の rank state が元と別 object であること。
- 正常な TVT 通過候補の `route_next_link is None` が、一時スキップではなく `RuntimeError` であること。
- clearance 設定値0は次の timestep、clearance 設定値1は次の次の timestep で、別 inlink が通過できること。
- TVT 順位適用 baseline fork の通常 baseline 群が、通常合流の選択順のまま order-control clearance を適用していること。
- 汎用 baseline fork は order-control clearance を適用せず、Node 別順位台帳を要求しないこと。

## 57. 採用しない方向

設計判断節の「採用しない方向」を維持する。加えて、次も採用しない。

- clearance 終了を戻り値の bool で `Node.transfer` へ返してから、呼出し側が通常群を分岐する。終了判断は `transfer_tvt_mp_passage_attempts` の内部に置く。
- 1 台移動 helper の中で clearance 履歴を更新する。通常 Node まで履歴が変わる。
- `incoming_vehicles` を許可集合だけへ差し替える。
- FCFS と BATCH の移動を、今回の 1 台移動 helper へ移す。
- 局所仮想計算の走査を、実 World の `Node.transfer` から呼ぶ。
- actual passage の field を、この実装で先に作る。
- 通常 baseline 群を、order-control clearance を無視して通す。
- 通常 baseline 群の通過後に、order-control clearance 履歴を更新しない。
- `order_control_type="none"` だから、安全のための clearance も不要だと扱う。
- 通常の信号交差点の全赤時間を、UXsim が自動で追加すると仮定する。
- clearance 設定値0を、同一 timestep 内の別 inlink 通過を許す「clearanceなし」と解釈する。
- clearance 設定値1を、直後の次 timestep で通過可能と解釈する。
- 通常の信号交差点の全赤時間と、order-control clearance 設定値を、同じ内部機構として扱う。
- clearance 設定値0を、本当の意味で待機時間がない方式として扱う。
- clearance 設定値0で、同一 timestep 内の別 inlink 通過を許す。
- clearance 設定値1で、T+1 の別 inlink 通過を許す。
- 既存の `no_clearance` という関数名だけから、`order_control_clearance_timesteps=0` と同じ意味だと推測する。
- `route_next_link is None` を、次時刻に自然解消する一時的な容量待ちとして扱う。
- `route_next_link is None` の Vehicle を永久にスキップし続ける。
- formal route を `route_next_link` の代替として強制する。
- collector が存在する baseline fork を、すべて TVT 順位適用 fork とみなす。
- Node 別順位台帳が無いことを理由に、fork 種別を推測する。
- TVT 順位適用 fork の台帳欠如を、通常合流への暗黙 fallback で隠す。
- 汎用 baseline fork へ T-1 以前の TVT 順位を強制する。
- 既存 baseline 回帰の期待値を、失敗を隠すために変更する。
- 引数 mapping を fork World へそのまま代入して共有する。
- fork 側と元側で同じ `OrderControlTvtNodeRankState` object を共有する。
- 時刻 T の新規未確定 Visit を fork 側台帳へ混ぜる。
- 引数 mapping が実 World 属性と同一 object であることを必須にする。
- 実 World 属性と別 mapping を渡せる既存 baseline API 契約を削除する。
- 時刻 T の未確定登録のあとで台帳を複製する。

## 58. 未確定事項

現時点では残っていない。

これは制度変更ではない。既存の汎用 baseline API と、TVT 順位台帳登録付き baseline API を、安全に共存させるための技術的識別である。

関数名、module 名、引数、戻り値、終了処理の位置、例外型、テスト名は本節で確定した。通常 baseline 群へ order-control clearance を適用する訂正は、既存の局所仮想計算との整合であり、新しい利用者判断ではない。clearance 設定値0と clearance 設定値1の時系列は、既存の strict greater-than を文書化する訂正であり、新しい利用者判断ではない。正常な TVT 通過候補で `route_next_link is None` を `RuntimeError` にする訂正は、正常系では `route_next_link` が存在するという確認に基づく防御であり、新しい利用者判断ではない。`apply_copied_tvt_confirmed_ranks` による fork 種別の識別も、新しい利用者判断ではない。呼出し側の順位台帳を登録前に独立複製して fork へ接続することも、新しい利用者判断ではない。制度判断は、入力にした設計判断節から変更していない。利用者判断は残っていない。

## 59. 完了条件

実装が完了したと言えるのは、次が全部真のときである。

- §6 の分岐で、対象 Node だけが TVT 物理通過を使う。
- 実 World は最新の確定順位だけを使い、未確定を通常群へ落とさない。Node 別順位台帳の欠如は `RuntimeError` である。
- TVT 順位適用 baseline fork は、登録前の独立複製にある過去確定群を先に試し、clearance で終了しなければ開始時の通常群だけを、order-control clearance 付きで通常合流する。到着候補があり、必要な Node 別順位台帳が欠けていれば `RuntimeError` である。
- 汎用 baseline fork は、TVT 順位台帳を要求せず、従来の通常合流で前進する。
- 2 種類の baseline fork は `apply_copied_tvt_confirmed_ranks` で区別し、Node 別順位台帳の有無から推測しない。
- 一時スキップした過去確定 Vehicle が通常群に入らない。
- 実進路は `route_next_link` であり、formal route は強制されない。
- 正常な TVT 通過候補で `route_next_link is None` なら `RuntimeError` であり、一時スキップでも formal route による補完でもない。
- `test_route_next_link_none_is_runtime_error_for_tvt_candidate` が、実 World、過去確定群、通常 baseline 群の 3 case で成功する。
- 通過済み集合と確定時刻 field が無い。
- collector は通過 1 回につき prepare と apply が 1 回である。
- observer は `Node.transfer` の外の既存 1 回のままである。
- 通常 Node、FCFS、BATCH、正式サンプルの結果が現行と一致する。
- TVT 順位適用 baseline fork の通常 baseline 群が、通常合流の選択順のまま order-control clearance を適用し、未充足でその時刻の通常群を終え、通過成功後に clearance 履歴を更新する。
- `order_control_type="none"` の通常合流は、order-control clearance 履歴を更新しない。
- clearance 設定値0では、別 inlink は直前通過と同じ timestep に通れず、次の timestep で通れる。
- clearance 設定値1では、別 inlink は次の timestep に通れず、次の次の timestep で通れる。間の 1 timestep を空ける。
- この off-by-one を、`test_clearance_zero_allows_different_inlink_only_from_next_timestep` と `test_clearance_one_requires_one_full_empty_timestep` で固定する。
- §48 の専用テスト 34 件と §51 の関係回帰が成功する。関係回帰には、collector の既定値と型検査、2 つの公開 API が渡す mode、`test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` を含める。これらは 34 件へ含めない。
- TVT 用 API が、登録前複製を fork へ接続し、時刻 T の未確定登録を元台帳だけへ適用し、fork と元台帳の object を共有しない。
- actual passage と actual outcome は未実装のままである。

## 60. 次の再開地点

1. 今回の文書修正を Terminal で限定確認する。
2. Python とテストの作業開始前からの未保存差分が、今回の文書作業で変化していないことを確認する。
3. `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()` で、対象 Node 検査のあと、登録前に `copy.deepcopy` し、fork World へ接続する。
4. 時刻 T の未確定登録は、元の呼出し側 mapping だけへ適用する。
5. `tests_order_control_tvt_baseline_driver_registration.py` へ `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` を追加する。専用テスト 34 件には含めない。
6. fork alignment と baseline driver registration を再実行する。既存期待値は、失敗を隠すために変えない。
7. 専用テスト 34 件、FCFS、BATCH、正式サンプルを再実行する。
8. 実装結果を第4巻と進捗第3巻へ記録する。
9. 差分と回帰結果を独立確認してから commit する。

上記の再開地点は履歴として残す。実装、独立確認、回帰結果は、同じ第4巻の「TVT-MP確定順位の物理通過接続 実装・独立確認・検証結果」を参照する。

# TVT-MP確定順位の物理通過接続 実装・独立確認・検証結果

記録日: 2026-09-29

本節は、直前の「TVT-MP確定順位の物理通過接続 完全実装前仕様」を実装し、Terminal で独立確認し、回帰を実行した結果である。設計判断節と完全実装前仕様節は、実装前の記録として残す。削除も短縮もしない。

最新の保存済み・push 済みコミットは `cc0cafa` である。HEAD と `origin/feature/intersection-order-control` は一致している。本節が記録する本番、テスト、仕様補足は、まだ Git 保存していない。`diagnostics/order_control.zip` は未追跡のままである。

完全実装前仕様どおり実装した。実装中に判明した仕様不足は、明示 mode、空の incoming snapshot、登録前凍結コピー、テスト fixture の直接配置で解消した。既存の期待値や assert は、失敗を回避するために変更していない。実装後の未解決失敗はない。仕様衝突はない。actual passage と actual outcome は未実装である。利用者判断が必要な事項は残っていない。

## 1. 実装概要

`time_value` かつ `order_control_eligible is True` の Node で、確定順位を物理通過の試行順へ接続した。`assigned_rank` は通過保証ではなく、通過を試す機会の順位である。

実装中に、次の不足が判明した。

- 汎用 baseline fork と TVT 順位適用 baseline fork を、collector の有無だけでは識別できなかった。明示 mode `apply_copied_tvt_confirmed_ranks` で解決した。
- 空の incoming snapshot でも Node 別順位台帳を要求していた。到着候補が無いときは台帳を要求せず、正常 return するようにした。
- TVT 用 baseline API を単独で呼ぶ経路では、呼出し側の順位台帳が fork World へ接続されなかった。登録前に `copy.deepcopy` した独立複製を、fork World へ明示接続した。
- テスト準備が、順位台帳の無い time_value 実 World の `junction_a` を実際に通過させていた。本番の `RuntimeError` は正しく、本番コードは緩めなかった。fixture だけを、整合した直接配置へ修正した。

## 2. 変更・新規作成ファイル

変更した本番ファイル:

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_driver.py`

新規の本番 module:

- `uxsim/order_control_tvt_mp_physical_transfer.py`

変更したテスト:

- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_mp_evaluation_end.py`

新規の専用テスト:

- `tests_order_control_tvt_mp_physical_transfer.py`

公開関数は `transfer_tvt_mp_passage_attempts(node)` である。TVT module は、`Node.transfer` の time_value 分岐の中で局所 import する。`uxsim.py` のファイル先頭では import しない。

## 3. Node.transferの分岐

`Node.transfer` の正式な順序は次である。

1. eligible かつ fcfs なら、`transfer_fcfs_clearance()` を呼び、return する。
2. eligible かつ batch なら、`transfer_batch()` を呼び、return する。
3. eligible が True かつ time_value なら、局所 import のあと `transfer_tvt_mp_passage_attempts(self)` を呼び、`_finish_node_transfer()` を呼び、return する。
4. その他は、`_transfer_normal_merge()` を呼び、`_finish_node_transfer()` を呼ぶ。

FCFS と BATCH は、既存の早期 return を維持した。FCFS と BATCH の関数本体は変更していない。

終了処理は、正常経路で 1 回だけである。TVT 処理が例外を出した場合は、終了処理へ到達しない。

## 4. Node private helper

`uxsim/uxsim.py` へ、次を追加した。

- `Node._transfer_one_vehicle_between_links`
- `Node._order_control_clearance_blocks_passage`
- `Node._transfer_normal_merge`
- `Node._finish_node_transfer`

1 台の物理移動、clearance 判定、通常合流、到着列の終了処理を分けた。候補順位、経路選択、observer、actual passage、actual outcome は、これらの helper へ混ぜていない。

## 5. 1台物理移動

`Node._transfer_one_vehicle_between_links` が担当するもの:

- baseline collector の prepare
- 累積台数
- `traveltime_actual`
- `link_arrival_time`
- inlink 流出容量
- outlink 流入容量
- Node 流量容量
- inlink からの削除
- outlink への追加
- `Vehicle.link`
- `begin_order_control_visit_on_link_entry`
- `x`
- leader
- follower
- lane
- `move_remain`
- `v`
- 移動後の inlink 先頭の trip 終了待ち
- `incoming_vehicles` からの削除
- baseline collector の apply

担当しないもの:

- 候補順位
- `assigned_rank`
- clearance 判定
- clearance 履歴更新
- `merge_priority`
- 経路選択
- formal route
- observer
- actual passage
- actual outcome

通常合流と TVT 確定群が、この helper を共有する。FCFS と BATCH は共有しない。

## 6. 通常合流

正式 signature:

```text
Node._transfer_normal_merge(
    self,
    allowed_vehicles=None,
    enforce_order_control_clearance=False,
)
```

確認済みの内容:

- `allowed_vehicles=None` は、現在の `incoming_vehicles` 全体である。
- tuple 指定時は、許可 Vehicle だけを候補にする。
- outlink 候補も、許可 Vehicle だけから作る。
- outlink の初出順を維持する。
- `number_of_lanes` 分を試す。
- 非 hard deterministic のときは `W.rng.shuffle` する。
- signal 条件を維持する。
- `merge_priority` を維持する。
- priority 合計が 0 のときは一様化する。
- hard deterministic のときは、既存の選択を維持する。
- live な入口空間と容量を使う。
- clearance 未充足なら、helper 全体を正常 return する。
- 通過成功後だけ、clearance 履歴を更新する。
- 終了処理は行わない。終了処理は `Node.transfer` が呼ぶ。

## 7. order-control clearance

共通 helper は `Node._order_control_clearance_blocks_passage(vehicle, inlink)` である。

契約:

- clearance 履歴の片側だけが None なら `RuntimeError` である。
- `last_order_control_inlink` が None なら、待機は不要である。
- 同じ inlink なら、待機は不要である。
- 別 inlink では strict greater-than である。

条件:

```text
W.T - last_order_control_entry_timestep
> order_control_clearance_timesteps
```

設定値 0:

- 同一 timestep 内の別 inlink 通過は不可である。
- 最短で次の timestep に通過できる。

設定値 1:

- 次の timestep では不可である。
- 最短で次の次の timestep に通過できる。
- 間の 1 timestep を確実に空ける。

TVT 確定群と、TVT 順位適用 fork の通常 baseline 群は、通過成功後に clearance 履歴を更新する。

汎用 baseline fork と、`order_control_type="none"` の通常合流では、order-control clearance 履歴を更新しない。

通常の信号交差点では、信号設定として明示した全赤時間が、安全上の clearance を担う。UXsim の自動付与には依存しない。

## 8. 実World

識別:

- collector は None である。
- 最新の確定順位を使う。
- 到着候補が 1 台以上あれば、Node 別順位台帳を要求する。
- 未確定は、通常群へ fallback しない。未確定のまま通過候補になる状態は `RuntimeError` である。
- 台帳の欠如を、通常合流へ暗黙に戻して隠さない。

## 9. TVT順位適用baseline fork

識別:

- collector は None ではない。
- `apply_copied_tvt_confirmed_ranks` は True である。

使用する順位は、登録前凍結コピーにある T-1 以前の確定順位である。過去確定群を先に試す。clearance で終了していなければ、その後に通常 baseline 群を処理する。通常 baseline 群にも order-control clearance を適用する。

到着候補が 1 台以上あり、必要な Node 別順位台帳が欠けていれば `RuntimeError` である。通常合流への暗黙 fallback はしない。

## 10. 汎用baseline fork

識別:

- collector は None ではない。
- `apply_copied_tvt_confirmed_ranks` は False である。

順位台帳を読まない。Node 別順位台帳を要求しない。従来の通常合流で前進する。order-control clearance は適用しない。order-control clearance 履歴も更新しない。

fork 種別は、collector の有無や Node 別順位台帳の有無から推測しない。非 bool の mode は `RuntimeError` である。

## 11. 空のincoming snapshot

3 分類のあと、generic fork の早期 return のあとで、incoming を snapshot する。長さが 0 なら、実 World でも TVT 順位適用 fork でも、順位台帳を要求せず正常 return する。

到着候補が 1 台以上あれば、実 World と TVT 順位適用 fork は Node 別台帳を要求する。空の到着列は、到着候補があるときの台帳欠如を許す理由にしない。

## 12. 順位台帳

`OrderControlTvtNodeRankState` は、Node 名、VisitKey、確定順、`assigned_rank`、formal route 名、未確定 VisitKey を持つ。live な Vehicle、Node、Link、World への参照は持たない。

実 World は、その時刻の driver 完了後の最新台帳を使う。TVT 順位適用 fork は、登録前に凍結した T-1 以前の確定順位を使う。時刻 T の新規未確定 Visit は fork の台帳へ入れない。

確定群は `assigned_rank` 順に一度ずつ試す。順位台帳、支払、補償、成立時履歴は、物理通過の中で変更しない。

## 13. 登録前凍結コピー

TVT 順位適用 baseline API の正式な処理順:

1. mode を True にして fork を作る。
2. snapshot 登録計画を作る。
3. 呼出し側の順位台帳を、登録前に検査する。
4. `copy.deepcopy(dict(rank_states_by_node_name))` で独立複製する。
5. 複製を fork World の `order_control_tvt_rank_states_by_node_name` へ接続する。
6. 元台帳だけへ、時刻 T の未確定 Visit を登録する。
7. collector へ snapshot 計画を登録する。
8. baseline forward する。

確認済み:

- fork 側 mapping は、元 mapping と別 object である。
- 各 Node の rank state も、別 object である。
- T-1 以前の confirmed 順位と formal route を複製する。
- 時刻 T の新規未確定 Visit は fork へ入らない。
- 元側の後続変更は fork へ伝播しない。
- fork 側の変更は元側へ伝播しない。
- 正常な driver 経路と、baseline API 単独経路を、同じ契約にした。
- 引数 mapping を fork へそのまま代入して共有しない。
- 時刻 T の未確定登録のあとで複製しない。

この不足は、fork alignment の回帰で判明した。代表例外は `RuntimeError: Node junction: TVT rank ledger is missing.` である。原因は、実 World 属性とは別の mapping を受け取れる API が、その mapping を登録前に fork へ複製して接続していなかったことである。既存テストの期待値は変更していない。

検査 helper は `_validate_rank_states_for_frozen_fork_copy` である。読取り専用である。mapping でないこと、対象 Node の欠如、型不一致、key と `node_name` の不一致は、登録 module と同じ `ValueError` である。不正な台帳は、`deepcopy` の前に拒否する。

既存の 2 つの公開 API の signature は変更していない。汎用 API は mode False を明示し、台帳を複製しない。TVT 用 API だけが mode True と、この凍結コピーを行う。

## 14. baseline collector mode

正式 constructor:

```text
OrderControlBaselineCollector(
    apply_copied_tvt_confirmed_ranks=False,
)
```

- 既定値は False である。
- bool だけを許容する。
- 非 bool は `ValueError` である。
- 通常の外部読取り可能属性として保存する。property や setter にはしない。
- 既存の引数なし constructor との後方互換を維持する。

`_prepare_baseline_fork` の `apply_copied_tvt_confirmed_ranks` は、既定値のない必須 keyword である。非 bool は `ValueError` である。汎用 baseline API は False を明示する。TVT 順位台帳登録付き API は True を明示する。

## 15. 候補snapshot

候補は、その時点の `incoming_vehicles` だけである。確定群を試す前に、通常 baseline 群を固定 snapshot として保持する。その後の incoming の変化で、通常群の対象を増やさない。

通過済みの Visit や、まだ到着していない Visit は再試行しない。通過済み VisitKey 集合は作らない。

## 16. assigned_rank

確定群は `assigned_rank` 順に一度ずつ試す。`assigned_rank` は通過保証ではない。正常な物理制約で通れなければ、順位も台帳も消さず、その時刻の後続を試す。次の timestep で再評価する。

baseline の選択順を、確定群の試行順には使わない。通常 baseline 群の選択順は、既存の通常合流のままである。

## 17. 実進路

実進路は `Vehicle.route_next_link` である。物理通過は、この live な次リンクを使う。台帳上の経路名で進路を書き換えない。

## 18. formal route

formal route は強制しない。`route_next_link` の代替にも使わない。順位、支払、補償の再計算もしない。

正常な TVT 通過候補で `route_next_link is None` なら `RuntimeError` である。一時スキップではない。次時刻まで待って自然解消する状態としても扱わない。目的地到着、trip abort、局所仮想計算の下流境界とは契約を分ける。

## 19. 一時スキップ

次は一時スキップである。順位も台帳も消さず、その時刻の後続を試す。

- 物理先頭ではない。
- 容量が足りない。
- 入口空間が足りない。

一時スキップした過去確定 Vehicle は、同じ時刻の通常 baseline 群へ入れない。

## 20. clearance終了

clearance 未充足だけ、その時刻の後続処理を終了する。TVT 確定群で clearance 未充足なら、通常 baseline 群も処理しない。通常 baseline 群の中で clearance 未充足なら、その時刻の通常群処理を終える。

物理制約による一時スキップと、clearance による時刻終了を分けた。重大な不整合は `RuntimeError` であり、一時スキップへ落とさない。

## 21. 通常baseline群

TVT 順位適用 fork では、過去確定群のあと、開始時に固定した通常 baseline 群を通常合流する。選択順は既存の通常合流のままである。order-control clearance を適用する。未充足なら、その時刻の通常群を終える。通過成功後に clearance 履歴を更新する。

過去確定群で先に通過した分の容量と入口空間を、通常群は live に見る。

汎用 baseline fork の通常合流は、この通常 baseline 群ではない。汎用 fork は台帳を読まず、order-control clearance も適用しない。

## 22. incoming_vehicles終了処理

`Node._finish_node_transfer` が、到着列の終了処理を担当する。`Node.transfer` の正常経路で 1 回だけ呼ぶ。

1 台移動 helper は、通過した Vehicle を `incoming_vehicles` から削除する。終了処理そのものは helper の中で行わない。TVT 処理が例外を出した場合は、終了処理へ到達しない。

`incoming_vehicles` を許可集合だけへ差し替えない。

## 23. collector

通過 1 回につき、prepare と apply を 1 回行う。prepare は移動の前、apply は移動の後である。1 台移動 helper がこの対を担当する。

通過しなかった一時スキップでは、prepare と apply を行わない。

## 24. downstream boundary observer

物理通過 module と `Node.transfer` の TVT 分岐は、downstream boundary observer を直接呼ばない。observer は `Node.transfer` の外にある既存の 1 回のままである。`capture_before_transfer` と `commit_after_transfer` の既存位置を、今回の helper へ移していない。

## 25. actual passage・actual outcome

actual passage と actual outcome は実装していない。実績価値、満足度、welfare、buyer 回数、seller 回数も、この接続では実装していない。field も先に作っていない。

## 26. 重大不整合

次は一時スキップではなく、`RuntimeError` である。

- 到着候補がある実 World で、Node 別順位台帳が無い。
- 到着候補がある TVT 順位適用 fork で、Node 別順位台帳が無い。
- 実 World の到着候補が未確定のままである。
- 正常な TVT 通過候補で `route_next_link is None` である。
- clearance 履歴の片側だけが None である。
- mode が bool ではない。

代表例外は `RuntimeError: Node junction: TVT rank ledger is missing.` と、`RuntimeError: Node junction_a: TVT rank ledger is missing.` である。前者は fork へ台帳が接続されていないときの回帰で出た。後者は、テスト準備が未準備の time_value 実 World を通過させたときに出た。どちらも本番の停止が正しい。

汎用 baseline fork は、台帳が無くてもこの例外にしない。順位台帳を読まず、通常合流する。

## 27. 例外時の状態

TVT 処理が例外を出した場合、`_finish_node_transfer` へ到達しない。例外を捕捉して通常合流へ戻さない。警告や別例外へ変換しない。

順位台帳、支払、補償、成立時履歴は、例外の前にも変更しない。登録前凍結コピーの検査に失敗した場合は、`deepcopy` も未確定登録も行わない。

fixture 修正後も、alignment 失敗時に実 World を変えないこと、未確定登録を残すこと、front registration を残すこと、apply や exec を呼ばない失敗境界は、既存 assert のままである。

## 28. テストfixture修正

次の 2 ファイルで、`vehicle_b` を `junction_a` へ実際に通過させず、`in_b` 上の整合した未到着状態を直接作るようにした。

- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_baseline_driver_registration.py`

追加 helper:

```text
_place_vehicle_on_inlink_with_new_order_control_visit
```

契約:

- 旧 Link の `vehicles` から削除する。
- leader と follower の相互参照を解除する。
- `in_b` へ追加する。
- `route_next_link` を `out_b` へ設定する。
- `begin_order_control_visit_on_link_entry()` で、`junction_b` 向け Visit を生成する。
- `junction_a` と `junction_b` の `incoming_vehicles` から除外する。
- `vehicle_b` は `junction_b` へ未到着である。
- current Visit は `junction_b` と `in_b` を指す。
- Visit を手書きしない。
- Visit ID を巻き戻さない。

`vehicle_a` を `in_a` へ進める間だけ、`vehicle_b` を `x=0` へ退避した。`x=180` のまま実 World を進めると、`junction_b` の到着候補になり、台帳の無い実 World が正しく停止するためである。その後、既存 helper で `x=180` へ戻した。current Visit object と Visit ID が変化しないことを assert した。

`vehicle_a` は、`in_a` の終端へ到着済みで、current Visit は `junction_a`、`junction_a.incoming_vehicles` へ登録済みである。

既存テストの assert、期待値、失敗境界は、削除も緩和もしていない。alignment の Node 順、collector の export 回数、未登録 VisitKey の検出、後続 Node を処理しないこと、partial result を返さないことは、そのままである。

## 29. 専用テスト34件

専用テストは `tests_order_control_tvt_mp_physical_transfer.py` の 34 件である。

主な追加契約:

- 時刻 T の最新確定順位
- T-1 以前の fork 確定順位
- 汎用 baseline fork の通常合流
- 過去確定群と通常 baseline 群
- 一時スキップ
- clearance 終了
- clearance 設定値 0 と 1
- 通常 baseline 群の clearance
- `route_next_link`
- formal route の非強制
- `route_next_link is None` の `RuntimeError`
- collector の prepare と apply
- observer の非呼出し
- 空の incoming snapshot では台帳不要
- FCFS と BATCH の早期 return
- 通常 Node 回帰
- `TESTS` 登録一致

直接実行は `34 tests passed` である。pytest は 34 件成功である。空の到着列の 1 件と、登録一致の 1 件を含む。mode の関係テストと、登録前凍結コピーの独立性テストは、この 34 件に含めない。

## 30. mode関係テスト

baseline collector:

- 既定値 False
- 明示 True と False
- 非 bool を `ValueError`

baseline driver:

- 汎用 API が False を明示する。
- `_prepare_baseline_fork` の非 bool を `ValueError` にする。
- 汎用 fork の collector mode が False である。

TVT baseline registration:

- TVT 用 API が True を明示する。
- collector mode が True である。
- 不正な順位台帳を、`deepcopy` の前に拒否する。
- 登録前凍結コピーは独立である。
- 時刻 T の新規未確定 Visit を fork へ混ぜない。
- fork 前進で、T-1 以前の確定順位を実際に使用する。

独立性テストは `test_tvt_rank_applying_fork_uses_independent_pre_registration_rank_snapshot` である。不正台帳を複製前に拒否するテストは `test_invalid_rank_states_raise_before_frozen_copy` である。どちらも `tests_order_control_tvt_baseline_driver_registration.py` にあり、専用テスト 34 件には含めない。

## 31. 中核回帰253件

次の 7 ファイルをまとめて実行した。

- `tests_order_control_tvt_mp_physical_transfer.py`
- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_driver.py`
- `tests_order_control_tvt_baseline_driver_registration.py`
- `tests_order_control_tvt_baseline_fork_alignment.py`
- `tests_order_control_tvt_mp_driver.py`
- `tests_order_control_tvt_mp_evaluation_end.py`

結果は `253 passed in 19.69s` である。

内訳:

- 物理通過専用: 34
- baseline collector: 35
- baseline driver: 71
- TVT baseline registration: 35
- fork alignment: 25
- TVT-MP driver: 31
- evaluation end: 22

合計 253 件である。未解決の失敗はない。

## 32. FCFS回帰

FCFS 関係は 73 件成功である。FCFS の関数本体は変更していない。`Node.transfer` では、eligible かつ fcfs の早期 return を維持している。

## 33. BATCH回帰

BATCH の残り単体は 293 件成功である。BATCH の関数本体は変更していない。`Node.transfer` では、eligible かつ batch の早期 return を維持している。

## 34. 正式サンプル

正式サンプルは、保存済みの数値と一致した。

- completed trips: 735 / 810
- average speed: 11.7 m/s
- total travel time: 119475.0 s
- average travel time: 162.6 s
- average delay: 62.6 s
- delay ratio: 0.385
- total distance traveled: 1632250.0 m

## 35. py_compile

変更・新規作成した本番とテストの 11 ファイルについて、`py_compile` は成功した。対象は §2 の 4 本番ファイルと 7 テストファイルである。

## 36. git diff --check

`git diff --check` は成功した。空白の誤りは出ていない。この確認は読取り専用である。commit や stage は、本節の記録時点では行っていない。

## 37. 独立確認結果

Terminal で、次の本番コードを直接確認した。

- `Node._transfer_one_vehicle_between_links`
- `Node._order_control_clearance_blocks_passage`
- `Node._transfer_normal_merge`
- `Node._finish_node_transfer`
- `Node.transfer`
- `transfer_tvt_mp_passage_attempts`
- `OrderControlBaselineCollector` の mode
- `_prepare_baseline_fork`
- TVT 用 baseline API の登録前凍結コピー

確認結果:

- 完全実装前仕様と一致した。
- FCFS と BATCH の本体に、意図しない変更はなかった。
- downstream boundary observer を直接呼ばない。
- actual passage と actual outcome を実装していない。
- 通常合流の信号判定、`merge_priority`、乱数順、hard deterministic を維持した。
- 重大不整合と、正常な一時スキップを分離した。
- 利用者判断が必要な事項はなかった。

## 38. 仕様との差

残る仕様との差はない。仕様衝突もない。

実装中に判明し、完全実装前仕様へ戻したうえで実装した事項は、次である。

- 汎用 fork と TVT 順位適用 fork の識別不足。明示 mode で解決した。
- 空の incoming snapshot に対する不要な台帳検査。到着候補が無いときは正常 return するようにした。
- baseline API 単独経路で、順位台帳が fork へ接続されない不足。登録前凍結コピーを明示接続した。
- テスト準備が、未準備の time_value 実 World を通過させる問題。本番は緩めず、fixture だけを直接配置へ修正した。

これらは新しい制度判断ではない。既存期待値を、失敗を隠すために変更してもいない。

## 39. 未実装範囲

この接続の次の段階として、未実装のままであるもの:

- actual passage
- actual outcome
- 実績評価、満足評価、welfare
- Vehicle 単位の buyer 回数、seller 回数、比率、価値の合算
- 非参加 Vehicle の外部効果集計

完全実装前仕様の非実装範囲も、この接続では実装していない。signal 統合、複数車線への一般化、`taxi`、`specified_route`、trip 終了 Vehicle の TVT 参加、対象外 Node の順位台帳削除、確定時刻 field、通過済み VisitKey 集合、formal route の強制、FCFS と BATCH の移動処理の共通化、局所仮想計算の拘束順位走査の変更は、未実装のままである。

## 40. 利用者判断が必要な事項

現時点では残っていない。

明示 mode、空の到着列、登録前凍結コピー、fixture の直接配置は、制度変更ではない。既存の汎用 baseline API と TVT 用 baseline API を共存させ、呼出し側台帳を fork と共有せず、未準備の time_value 実 World をテスト準備で通過させないための技術的修正である。

## 41. 完了条件

完全実装前仕様の完了条件は、今回の実装と回帰で満たした。

- 対象 Node だけが TVT 物理通過を使う。
- 実 World は最新の確定順位を使い、未確定を通常群へ落とさない。
- TVT 順位適用 fork は、登録前複製の過去確定群を先に試し、その後の通常群に order-control clearance を適用する。
- 汎用 fork は台帳を要求せず、従来の通常合流で前進する。
- 2 種類の fork は `apply_copied_tvt_confirmed_ranks` で区別する。
- 空の incoming snapshot は台帳を要求しない。到着候補があれば要求する。
- 実進路は `route_next_link` であり、formal route は強制しない。
- `route_next_link is None` は `RuntimeError` である。
- collector は通過 1 回につき prepare と apply が 1 回である。
- observer は `Node.transfer` の外のままである。
- 専用テスト 34 件、中核回帰 253 件、FCFS 73 件、BATCH 293 件、正式サンプルが成功した。
- actual passage と actual outcome は未実装のままである。

## 42. 次の再開地点

1. 第4巻と進捗第3巻の実装結果記録を Terminal で分割確認する。
2. 本番・テスト・文書の最終差分を確認する。
3. 関係回帰結果と変更ファイルを最終確認する。
4. 文書 2 ファイルを含む全実装対象を stage する。
5. `diagnostics/order_control.zip` は stage しない。
6. `git diff --cached --check` と `git diff --cached --stat` を確認する。
7. commit 名に document は必須ではない。今回は実装コミットである。
8. commit と push を分離する。
9. 保存後、actual passage・actual outcome の設計へ進む。

# TVT-MP単一decision timestep診断・通常ケースと境界ケースの比較（2026-09-30）

本節は、2026-09-30 に完成した独立診断の記録である。本番仕様の変更ではない。局所仮想計算の追加継続方式（方式 A・B・C と呼ばれる候補）の採否は、本節では決めない。

この節は診断完了時点の記録である。追加継続方式は当時未確定だった。方式 A・B・C という呼び方は、当時の未確定な検討名であり、追加継続設計の正式名称としては採用しない。第4巻の別節にある評価期間の方式A・方式Bとは別問題である。後続設計で、trade_scope 内の buyer・seller・nonparticipating 全員の candidate passage を、同じ candidate local loop で観測する方式が第一実装の採用方針となった。最新仕様は、本巻末尾の「TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）」を参照する。

過去の第4巻各節は、その時点の正式記録として残す。TVT-MP 単一 decision timestep の実交通診断については、本節を診断結果の参照先とする。終了条件と予測・実績の最新仕様は、上記の完全実装前仕様である。

## A. 診断ファイル

- 診断ファイル: `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py`
- 本番コード、既存テスト、既存設計文書を変更せずに作成した独立診断である。
- 2026-09-30 時点では Git 未追跡ファイルである。
- `diagnostics/order_control.zip` は既存の未追跡ファイルであり、本診断作業では触れていない。
- 診断スクリプトの `py_compile` は成功した。
- Stage 1〜3 の全 assert は成功した。

## B. Stage 1

Stage 1 は generic baseline fork の実交通確認である。

通常ケースの構成:

- snapshot `T=10`
- baseline horizon `=25`
- 1 つの time_value Node
- 4 本の approach inlink
- 1 本の outlink
- Vehicle A、B、C、D の 4 台
- current visit は通常走行によって自然生成する
- snapshot では 4 台とも not-yet-arrived
- baseline arrival:
  - A=11
  - B=12
  - C=13
  - D=14
- 初期の単純 baseline passage は A=12、B=13、C=14、D=15 だった。
- その後、P−1 候補集合に A〜D を全て含める診断条件として、診断用 outlink gate を設けた。
- 通常ケースで使用する baseline passage:
  - A=15
  - B=16
  - C=17
  - D=18
- `registered_visit_count=4`
- real World は baseline fork で変更されない。

性能の注意:

- generic baseline fork 自体は、利用者 Terminal では約 0.01 秒台だった。
- 利用者環境では `finalize_scenario` が約 18 秒かかったが、これは World 準備の環境依存時間であり、baseline fork 時間でも TVT-MP driver 時間でもない。
- Cursor 側環境では `finalize_scenario` は約 0.01 秒台だった。
- 性能比較では `finalize_scenario` を driver 時間へ含めない。

outlink gate:

- 到着順、candidate、rank、economic result を手動作成したものではない。
- junction 下流を一時的に塞ぎ、baseline passage を物理的に遅らせた診断用交通条件である。
- A〜D 全員が RoE passage `P` の P−1 候補集合へ入る状態を作る目的である。
- gate Vehicle は real World に置かれ、baseline fork および Stage 2 driver 内部のコピーにも存在する。
- release timestep は 15 である。
- 通常ケースで candidate local calculation が不必要に長期化していないことを、`final_offset` と `simulated_timestep_count` から確認した。

## C. Stage 2 通常ケース

Stage 2 は、同じ real World から本物の `run_tvt_mp_driver` を 1 回実行する。

設定:

- snapshot `T=10`
- baseline horizon `=25`
- max candidate Visit 数 `=4`
- evaluation end `=None`
- Node 数 `=1`
- candidate visits `=A、B、C、D`
- RoE `=A`
- A、B、D は参加、C は不参加

concrete candidates:

- `("B",)`
- `("D",)`
- `("B","D")`

3 候補すべて FIFO True。

role:

- `("B",)`: buyer B、seller A、nonparticipating なし
- `("D",)`: buyer D、sellers A・B、nonparticipating C
- `("B","D")`: buyers B・D、seller A、nonparticipating C

通常ケースの local result:

- `("B",)`: resolved=True、`final_offset=3`、`simulated_timestep_count=3`
- `("D",)`: resolved=True、`final_offset=5`、`simulated_timestep_count=5`
- `("B","D")`: resolved=True、`final_offset=5`、`simulated_timestep_count=5`

通常ケースでは、nonparticipating C が offset 4、virtual timestep 14 に binding 通過し、最後の required buyer D が offset 5、virtual timestep 15 に通過した。

したがって、通常ケースだけを見れば C passage は現行停止前に観測できるが、これは一般保証ではない。

economic:

- 3 候補すべて economically feasible
- selected `=("B","D")`
- payment `=CALCULATED`
- final rank `=SELECTED_CANDIDATE_RANKS`
- validation 成功
- atomic apply 成功

## D. 境界ケース Stage 3

Stage 3 は独立 World で構築した。

目的:

- nonparticipating C が binding 未通過のまま
- required buyer・seller の passage が全て揃い
- local calculation が resolved し
- economic evaluation から atomic apply まで進む

ことを実交通状態で実証する。

ネットワーク:

- 1 time_value Node
- 4 approach inlink
- 3 outlink（D→`out_d`、A・C→`out_c`、B→`out_b`）
- 全 link 単車線

到着:

- A=11、B=12、C=13、D=14

baseline passage（flow hold release timestep=16 の条件下）:

- A=16、B=16、C=17、D=16

diagnostic traffic conditions:

- Stage 3 専用 flow hold release timestep `=16`
- approach inlink `capacity_out=0.2`
- approach inlink `capacity_in=10000.0`
- snapshot 時点の `capacity_out_remain=0`
- `out_c` の jam density `=0.05`（inlink capacity 待機中に `move_remain` が蓄積し、同一 scan で C が誤通過しないための診断用 link 条件）
- Node flow は candidate local で十分開放
- clearance 待ちは使用しない（junction clearance を診断上満たす設定）

`capacity_out=0.2` の因果:

- candidate local の virtual time 更新で、各 offset ごとに `capacity_out_remain` が 0.2 ずつ補充される（`remain < DELTAN` のとき `+ capacity_out * DELTAT`）。
- offset 2〜4 では残量が 1 未満なので、到着済み Vehicle は `INLINK_OUTFLOW_CAPACITY_UNAVAILABLE` で一時 skip される。
- offset 5 では残量が 1 となり、D、A、C、B を同じ binding scan で試せる。
- このため 4 台を同一 scan へ揃えた。

candidate `("D",)` の complete binding sequence: D、A、C、B。

offset 5 / virtual timestep 15:

1. D が `out_d` へ通過
2. A が `out_c` へ通過
3. C は A が同一 scan で `out_c` へ入ったため、`OUTLINK_ENTRY_SPACE_UNAVAILABLE` で一時 skip
4. B が `out_b` へ通過
5. D、A、B の required passage を記録
6. required complete=True
7. resolved=True
8. calculation finished=True
9. C は同一 scan で再評価されず、binding passage 未観測のまま終了

C について:

- 全 timestep の binding passage 出現回数 `=0`
- required passage 対象外
- `newly_recorded_required_passage_visit_keys` へ一度も入らない
- 最終 skip reason `=OUTLINK_ENTRY_SPACE_UNAVAILABLE`

candidate `("D",)` の結果:

- resolved=True、stop_reason=RESOLVED、`final_offset=5`、`simulated_timestep_count=5`
- required candidate passage: D=15、A=15、B=15

economic（candidate `("D",)`）:

- D baseline=16、candidate=15 → expected saving=1 timestep
- declared VOT=100 → `G_b=100`
- seller A・B は candidate passage が baseline より遅くない（A・B は baseline=16、candidate=15）
- seller compensation `R=0`（待ち増加が 0 のため。A の申告 VOT=0 でも、今回の条件では `expected_waiting_increase_timesteps=0` なので `R_s=0` となる）
- total `G=100`、total `R=0`、surplus=100、economically feasible=True

Stage 3 では 3 候補すべて feasible。selected `=("B","D")`、surplus=101。

後段:

- payment=CALCULATED
- final rank=SELECTED_CANDIDATE_RANKS
- validation 成功
- atomic apply 成功

この結果の意味:

- 本番コードの不具合を示すものではない。
- 現行仕様どおり、buyer・seller の required passage が揃えば正常終了する。
- trade_scope 内 nonparticipating の candidate passage は成功条件ではない。
- nonparticipating が未通過のままでも、取引成立から atomic apply まで進めることを実交通状態で確認した（境界ケースを再現した）。
- この境界ケースは、方式 A・B・C による追加計算の必要性と負荷を検討するための基礎となる。

## E. 保存済み処理量の比較

診断 §38「Stage 2 versus Stage 3 workload comparison」は、保存済み `DriverPipelineTrace` から集計した。

Stage 2 と Stage 3 で同じ Node 件数・候補件数:

- target Node 数=1
- candidate Visit 数=4
- concrete candidate 数=3
- general trade rank 候補数=3
- FIFO inspection 候補数=3
- FIFO True 候補数=3
- local virtual 候補数=3
- resolved=3、unresolved=0
- economic 候補数=3、feasible 候補数=3
- selected `=("B","D")`
- expected candidate local World copy 数=3

World copy 数:

- FIFO True 候補ごとに candidate local World を 1 つ作る契約からの期待値である。
- 直接 timing counter で測った値ではない。
- 表記: `expected from one local World per FIFO-True candidate; not directly timed`

候補別（`buyers_sorted` で対応）:

- `("B",)`: Stage 2 simulated=3、timestep results=4、skip=13 / Stage 3 simulated=5、timestep results=6、skip=21
- `("D",)`: Stage 2 simulated=5、timestep results=6、binding transfer 成功=4、skip=14 / Stage 3 simulated=5、timestep results=6、binding transfer 成功=3、skip=21
- `("B","D")`: Stage 2 simulated=5、timestep results=6、skip=14 / Stage 3 simulated=6、timestep results=7、skip=21

合計:

Stage 2:

- total `simulated_timestep_count=13`
- total `timestep_result_count=16`
- binding transfer 成功=10
- temporary skip=41（理由は `NOT_ARRIVED_AT_TARGET_NODE` のみ）
- total horizon step ratio=0.1733

Stage 3:

- total `simulated_timestep_count=16`
- total `timestep_result_count=19`
- binding transfer 成功=10
- temporary skip=63（`NOT_ARRIVED=42`、`INLINK_OUTFLOW_CAPACITY_UNAVAILABLE=18`、`OUTLINK_ENTRY_SPACE_UNAVAILABLE=3`）
- total horizon step ratio=0.2133

重要な result 契約（保存済み result から確認）:

- `timestep_results` 数 `= final_offset + 1`
- `simulated_timestep_count = final_offset`
- 両者は同じではない。offset 0 も `timestep_results` に含まれることが差の原因である。

## F. 壁時計

利用者 Terminal で 5 回測定した `run_tvt_mp_driver` 時間（`world_prepare` 内の `finalize_scenario` は含めない）:

Stage 2:

- 0.0333、0.0325、0.0327、0.0323、0.0325 秒
- 平均 0.03266 秒、中央値 0.0325 秒、範囲 0.0323〜0.0333 秒

Stage 3:

- 0.0699、0.0532、0.0591、0.0597、0.0516 秒
- 平均 0.05870 秒、中央値 0.0591 秒、範囲 0.0516〜0.0699 秒

平均差: 0.02604 秒。Stage 3 / Stage 2 の平均比は約 1.80 である。

別の独立実行（利用者 Terminal）では Stage 2=0.0340 秒、Stage 3=0.0511 秒、比率は約 1.50 である。

診断スクリプトの 1 回実行（Cursor 環境）では、Stage 2 driver≈0.0507 秒、Stage 3 driver≈0.0462 秒となり、Stage 3 がやや短かった。これは利用者 Terminal の 5 回測定と混同しない。

整理:

- Stage 2 時間は比較的安定する。
- Stage 3 時間は変動が大きい。
- Stage 3 は保存済み処理件数（simulated step、skip 等）が多い。
- ただし driver 時間は処理件数へ単調比例しない。
- Stage 2 と Stage 3 は交通状態と outlink 構成が異なる。
- 時間差を C 未通過だけへ帰属できない。
- 保存済み result には stage 別内部時間と World.copy 単体時間がない。
- 現時点で比較できるのは whole-driver 時間と保存済み処理件数だけである。
- 方式 A・B・C の追加負荷はまだ測定していない。

## G. 今後の検討事項（未確定）

局所仮想計算の追加継続方式を検討する際の未確定事項:

1. nonparticipating 未通過時に、追加計算をどこまで継続するか
2. 方式 A・B・C の正確な定義
3. 各方式で得る値
4. 方式ごとの追加 virtual timestep 数
5. 追加 binding scan 数
6. 追加 World copy の要否
7. driver 全体時間への追加負荷
8. 方式間で比較条件をそろえる方法
9. stage 別 timing または World.copy 単体 timing を取得する診断方法
10. 本番コードへの instrumentation が必要か、診断側だけで測れるか
11. 通常ケースで追加継続が不要な候補を早期終了する扱い
12. horizon まで C が通過しない場合の未観測表現

方式 A・B・C の推奨や採否は、本節では行わない。

上記 §G は、2026-09-30 の診断完了時点で未確定だった検討リストである。削除しない。当時の制約では、nonparticipating 未通過でも buyer・seller 完了で正常終了することまでが確認済みであり、追加継続の中身はまだ決まっていなかった。

後続検討で比較し、第一実装では不採用とした方式は次の二つである。いずれも本診断節の本文には採用方針としては書かれていない。診断後の設計比較で検討した案である。

- selected candidate 決定後に、decision timestep T から新しい local World を copy し、選択候補だけを再計算する方式。
- 各 candidate の buyer・seller 完了時点の live local World と mutable state を selection 完了まで保持し、選択候補だけ後から再開する方式。

不採用の理由と、同じ local loop を trade_scope 全 Visit の観測まで続ける採用方針は、本巻末尾の完全実装前仕様を参照する。

# TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）

本節は完全実装前仕様である。Python と専用テストは未着手である。実装済みではない。

この論点の最新参照先は本節である。診断結果の過去記録は、同じ第4巻の「TVT-MP単一decision timestep診断・通常ケースと境界ケースの比較（2026-09-30）」である。buyer・seller の事後評価と成立時 record の分離は、詳細設計第3巻「13. 成立時recordとactual outcomeの分離」を維持する。本節は第3巻の buyer・seller 事後評価を削除も簡略化もしない。

進捗第3巻の対応節は「trade_scope全Visit観測の完全実装前仕様（2026-09-30）」である。

## 1. 現行契約と、本節が変える終了だけ

現行の candidate local virtual calculation は、buyer・seller の required candidate passage が全て記録されると、同じ virtual timestep の終了時に resolved かつ finished になる。

終了判定は次である。

- `resolved_after_timestep_end` は、buyer・seller の required passage 完了である。
- `calculation_finished_after_timestep_end` は、その完了、または最後の許容 offset への到達である。

`required_passage_records` は buyer・seller だけである。economic evaluation はこれを読み、buyer・seller 以外の role が入ると不整合として扱う。したがって nonparticipating をこの record へ入れない。

`resolved=True` の意味は変えない。buyer・seller の economic required passage が揃ったことである。nonparticipating 未観測だけを理由に `resolved=False` にしない。

`finished` の意味は変える。traffic observation 対象の全員を観測したとき、または既存 horizon の末尾に達したときだけ `finished=True` とする。buyer・seller が先に揃っても、trade_scope 内 nonparticipating が未観測なら finished にしない。

## 2. 第一実装で不採用とした比較案

診断節の方式 A・B・C は、当時未定義の検討名である。正式名称にはしない。評価期間の方式A・方式Bとも混同しない。

診断後に比較し、第一実装では不採用とした方式は次である。当時の制約下での検討案であり、記録上の誤りとして消さない。

再計算方式。selected candidate 決定後に、decision timestep T から新しい local World を copy し、選択候補だけを再計算する。

- decision timestep T から、元の buyer・seller 完了地点まで重複計算が必要になる。
- 実装は比較的単純だが、不要な再計算時間が生じる。
- nonparticipating が元の停止地点の直後に通過するとき、純粋な追加観測に対して再計算区間の割合が大きくなる。
- 例として、元の buyer・seller 完了 offset が 5 で、nonparticipating が offset 6 で通過する場合、純粋な追加観測は 1 offset でも、再計算方式では offset 0 からやり直す。

live state 保持方式。各 candidate の buyer・seller 完了時点の live local World と mutable state を selection 完了まで保持し、選択候補だけ後から再開する。

- 重複計算は避けられる。
- FIFO True candidate 数に応じて、複数の大規模 World を selection 完了まで同時保持する。
- 52 Node、10,000 Vehicle 等へ拡大すると、ピーク RAM が候補数に応じて増え、RAM 上限を超えるリスクがある。
- RAM 超過は計算時間の増加と違い、シミュレーション自体を完了できなくする。
- state の所有、selection 後の再開、不採用 candidate の破棄、例外時の後始末が複雑になる。
- final result へ live World や mutable state を残さない現行方針より、実装責務が増える。

採用方式。各 FIFO True candidate について、最初の candidate local calculation を必要なところまで同じ local World と同じ各種 state のまま続ける。

- decision timestep T からの再計算をしない。
- 追加 World copy を作らない。
- selection 完了待ちの live state 保持をしない。
- buyer・seller・nonparticipating の candidate passage を同じ local World 上で観測する。
- 同じ candidate local loop で完結する。

将来、この継続方式でも計算時間が重大なボトルネックになった場合は、live state 保持等の性能最適化を改めて検討できる。第一実装では採用しない。

## 3. economic required と traffic observation

economic required passage は buyer と seller だけである。既存の `required_passage_records` を使う。economic evaluation は引き続きこの record だけを読む。nonparticipating は入れない。

candidate traffic observation は、trade_scope 内の buyer、seller、nonparticipating である。partition 4 は観測対象に含めない。終了判定はこの集合を使う。保存は economic required とは別の frozen record 列である。

nonparticipating が 0 件なら、buyer・seller 完了が traffic observation 完了でもある。現行と同じ時点で終わる。

nonparticipating が buyer・seller より先に通過済みなら、最後の buyer・seller が通過した時点で全体完了になる。物理通過では一時 skip により後順位が先に通過し得る。nonparticipating が必ず先に通過する保証はない。trade_scope の最終 baseline 順位は trailing buyer であり、成立後の post-trade 順位では末尾側に seller が置かれる。nonparticipating は baseline local rank を維持し、割当順位上 trade_scope の末尾にはならない。

## 4. 終了条件

### 4.1 offset と virtual timestep

`baseline_timestep_T` は candidate local calculation の decision timestep T である。

`offset` は T から何 timestep 進んだかを示す 0 始まりの整数である。

コード上の正式関係は次である。

`virtual_timestep = baseline_timestep_T + offset`

Stage 3 診断の例（`T=10`、`configured_horizon_steps=25`）:

- offset 5 → virtual timestep 15
- offset 6 → virtual timestep 16
- 最後の許容 offset は 24 → 最後の virtual timestep は 34
- offset 24 の次となる offset 25 は処理しない。one-timestep API は許容 offset の範囲外で終了する。

### 4.2 終了の優先順位

優先順位は次である。

1. trade_scope 内の traffic observation 対象全員の candidate passage を観測する。
2. `configured_horizon_steps` の最後の許容 offset へ到達する。許容 offset は 0 から `configured_horizon_steps - 1` である。buyer・seller 完了後に新しい horizon は足さない。decision timestep T から数えた既存 horizon を共有する。
3. 重大不整合は status ではなく例外にする。

horizon 到達時を分ける。

buyer・seller が完了し、nonparticipating の一部または全部が未観測のとき。`resolved=True` のまま economic evaluation へ進める。traffic observation は部分完了または未完了である。正常結果である。nonparticipating 未観測だけを理由に candidate を unresolved にしない。

buyer・seller が未完了のとき。現行どおり unresolved であり、economic 成立計算へ進めない。

別々に保存する。

- `economic_required_passages_complete_offset`
- `economic_required_passages_complete_virtual_timestep`
- `all_trade_scope_passages_complete_offset`
- `all_trade_scope_passages_complete_virtual_timestep`

trade_scope 全員が揃わないまま horizon へ到達した場合、後者二つは `None` である。buyer・seller 完了と全員完了が同じ virtual timestep なら、両方へ同じ offset と virtual timestep を入れる。

既存契約は維持する。`timestep_results` 数は `final_offset + 1` である。`simulated_timestep_count` は `final_offset` である。offset 0 も `timestep_results` に含むため、両者は一致しない。

### 4.3 resolved、finished、stop_reason

現行 economic evaluation は、candidate local result について次の対応を要求する。本節でもこの一対一を維持する。

- `resolved=True` ↔ `stop_reason=RESOLVED`
- `resolved=False` ↔ `stop_reason=HORIZON_EXHAUSTED_UNRESOLVED`

`RESOLVED` を traffic observation 全員完了専用の意味へ変更しない。第一実装では新しい stop reason を追加しない。nonparticipating 未観測を `unresolved_reasons` へ入れない。nonparticipating 未観測は traffic observation record の `UNOBSERVED_AT_HORIZON` と関連 field で表す。

`finished` は、traffic observation 対象全員の観測完了、または最後の許容 offset 到達のいずれかで `True` である。

**状態1** economic required 完了、traffic observation 全員完了:

- `resolved=True`
- `stop_reason=RESOLVED`
- `unresolved_reasons=()`
- `finished=True`
- `all_trade_scope_passages_complete_offset` は int
- `all_trade_scope_passages_complete_virtual_timestep` は int

**状態2** economic required 完了、nonparticipating の一部または全部が未観測のまま horizon 到達:

- `resolved=True`
- `stop_reason=RESOLVED`
- `unresolved_reasons=()`
- `finished=True`
- `all_trade_scope_passages_complete_offset=None`
- `all_trade_scope_passages_complete_virtual_timestep=None`
- nonparticipating 未観測は traffic observation record の `UNOBSERVED_AT_HORIZON` で表す

**状態3** economic required 未完了のまま horizon 到達:

- `resolved=False`
- `stop_reason=HORIZON_EXHAUSTED_UNRESOLVED`
- `unresolved_reasons` には現行どおり buyer・seller 未通過理由を記録する
- `finished=True`

## 5. 通過処理

拘束順位列は既存の `visits_in_binding_order` である。Node 連続順位を反映した列であり、candidate 内の局所順位だけではない。buyer・seller・nonparticipating を交通計算上は同列に試す。

一時 skip は変更しない。`NOT_ARRIVED_AT_TARGET_NODE`、`NOT_INLINK_PHYSICAL_HEAD`、`INLINK_OUTFLOW_CAPACITY_UNAVAILABLE`、`OUTLINK_INFLOW_CAPACITY_UNAVAILABLE`、`NODE_FLOW_CAPACITY_UNAVAILABLE`、`OUTLINK_ENTRY_SPACE_UNAVAILABLE` である。skip した Visit は列から削除しない。同じ virtual timestep では後続を試し、次の virtual timestep では列の先頭から再評価する。

clearance 未充足だけ、その virtual timestep の対象 Node binding scan を終える。`CLEARANCE_NOT_SATISFIED` と `stopped_binding_visit_key` は scan stop context として残す。一時 skip enum へ混ぜない。

binding、unbound FCFS、required passage 記録、Vehicle advance、downstream boundary、capacity 更新、clearance の既存順は維持する。

buyer・seller の required passage record と、trade_scope 内全 Visit の traffic observation record は、同じ binding transfer result と同じ virtual timestep から作る。buyer・seller について、両 record の `candidate_passage_timestep` は必ず一致しなければならない。同じ Visit の candidate passage を二度記録しようとした場合は重大不整合として例外にする。Vehicle advance 後の位置から passage timestep を推測し直さない。binding Visit は unbound FCFS 候補から除外される既存契約を維持する。

final result へ live World、candidate local state、mutable transfer state は入れない。必要な情報は名前と数値の frozen record である。

## 6. 予測 traffic observation

概念名は `OrderControlTvtMpCandidateTrafficObservationRecord` である。buyer・seller・nonparticipating を同じ型で保存し、`trade_role` で区別する。candidate local result へこの record 列を追加する。

識別 field は、`visit_key`、`vehicle_name`、`vehicle_id`、`node_name`、`trade_role`、`binding_rank`、trade_scope 内順位、`inlink_name`、`route_next_link_name` である。

価値 field は、`true_vot_per_second`、`baseline_passage_timestep`、`candidate_passage_timestep`、`passage_observation_status`、`observed_offset`、`observed_virtual_timestep`、`predicted_time_difference_timesteps`、`predicted_time_difference_seconds`、`predicted_signed_time_value_change` である。

未観測と原因の field は、`last_checked_offset`、`last_checked_virtual_timestep`、`last_temporary_skip_reason`、`last_temporary_skip_offset`、`latest_clearance_stop_context`、`horizon_exhausted`、`observation_complete` である。

観測 status は `OBSERVED` と `UNOBSERVED_AT_HORIZON` である。同じ candidate local calculation の中なので、元計算と追加計算では分けない。

観測できたときの時間差は次である。

`predicted_time_difference_timesteps = baseline_passage_timestep - candidate_passage_timestep`

正は candidate で短縮、負は遅延、0 は同時刻である。

`predicted_time_difference_seconds = predicted_time_difference_timesteps × DELTAT`

nonparticipating の予測上の符号付き価値は次である。

`predicted_signed_time_value_change = predicted_time_difference_seconds × true_vot_per_second`

正は予測上の便益、負は予測上の損失、0 は予測上の変化なしである。`DELTAT` は秒、VOT は秒あたりである。buyer の `G_b` も秒と申告 VOT の積なので、時間単位は同じである。使う VOT が違う。当事者の economic evaluation は申告 VOT のままである。共通 record に true VOT を保存しても、申告 VOT の計算は置き換えない。

nonparticipating は支払・補償の対象ではない。`total_buyer_value_G`、`total_required_compensation_R`、surplus、`economically_feasible`、`infeasibility_reasons`、candidate selection、buyer payment、seller compensation には入れない。予測上の外部効果として別記録する。

未観測のときは、`candidate_passage_timestep`、時間差、秒、符号付き価値を `None` にする。status は `UNOBSERVED_AT_HORIZON` である。horizon 末尾時刻も 0 も代入しない。失敗扱いしない。

最後の一時 skip 理由は、その Visit が binding scan で最後に一時 skip された理由である。以前の offset の理由しか無いときは、その理由と offset を残す。最終 timestep で clearance により対象 Visit まで scan が届かなかったときは、一時 skip 理由を書き換えず、clearance の scan stop context を別 field に残す。両方残り得る。

真の VOT が 0 かどうかは、既存方針を維持する。今後採用する論文・統計に基づく分布が 0 を取り得るなら許容し、取り得ないなら許容しない。一律に常に有効とは書かない。

traffic observation record の `baseline_passage_timestep` は、可能な場合は正式な baseline 情報から取得する。符号付き時間差と価値を計算するには、baseline passage と candidate passage の両方が int である必要がある。baseline passage が利用できない場合、candidate passage を観測できても、次は `None` とする。

- `predicted_time_difference_timesteps`
- `predicted_time_difference_seconds`
- `predicted_signed_time_value_change`

baseline 不足を 0 や horizon 末尾で補完しない。baseline 不足を nonparticipating の通過失敗と混同しない。baseline 情報不足 status または理由 field の正式名称は、次の完全実装前仕様詳細化で確定する。buyer・seller の economic required については、現行 economic evaluation の baseline passage 検査を変更しない。

traffic observation 用の `true_vot_per_second` は、decision timestep T の candidate local World を構築した時点の local Vehicle から取得し、観測 record 用 state へ凍結する。candidate passage 観測後や result 作成時に、live real World の `Vehicle.vot_true` を読み直さない。現行コードでは atomic apply 時に実 World の `Vehicle.vot_true` を取得し、`OrderControlTvtMpTradeEstablishmentLogRecord.true_vot_per_second` へ保存している。selected trade の buyer・seller については、成立時 record へ凍結された `true_vot_per_second` を actual outcome で使用する。nonparticipating についても、decision 時点に凍結した true VOT を actual 追跡 registry と actual passage observation へ引き継ぐ。actual outcome 評価時にも、最新の live VOT を読み直さない。buyer・seller の economic evaluation が申告 VOT を使う既存仕様は変更しない。

## 7. actual outcome

actual passage と actual outcome は未実装である。成立時 record は後から書き換えない。actual 用 field を成立時 record へ `None` で予約しない。actual 関連の frozen record は、成立時 record とは別に `order_exchange_log` へ追加する。これは第3巻の既存方針である。通過前は成立時 record だけが `order_exchange_log` に存在する。

「共通 actual outcome 基盤」とは、共通の取引識別と Visit 識別、actual passage 観測基盤を共有する意味である。全 role の全 field を 1 つの巨大な optional 型へ押し込む意味ではない。共通 identity・passage 観測部分と、role 別または取引全体評価部分を分離できる。第3巻の buyer・seller 仕様を削除も簡略化もしない。

次の三層を区別する。型名と field 名の正式確定は、後続の actual outcome 詳細設計で行う。

### 7.1 Visit 単位 actual passage observation

役割: 実 World で 1 つの Visit が対象 Node を通過した事実を記録する。または評価終了で未観測と確定した事実を記録する。

含む候補 field: 取引識別 3 項目（`tvt_decision_timestep`、`node_name`、`buyers_sorted`）、`visit_key`、`vehicle_name`、`trade_role`、baseline passage、predicted candidate passage、actual passage、formal route、actual route、decision 時点で凍結した true VOT、actual passage observation status、時間差、nonparticipating の符号付き外部効果、passage prediction error、signed value prediction error。

この record は観測時、または評価終了で未観測が確定した時点で一度だけ作り、後から書き換えない。`order_exchange_log` に追加する frozen record の status は、追加時点で次のどちらかである。

- `ACTUAL_PASSAGE_OBSERVED`
- `ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END`

`WAITING_FOR_ACTUAL_PASSAGE` を frozen record として `order_exchange_log` へ追加しない。通過待ちは World 側の mutable registry で VisitKey 単位に管理する内部 waiting 状態である。registry の正式型、所有場所、重複拒否 API は actual passage 詳細設計で確定する。

記録の正本は、実 World で対象 Visit が対象 Node を通過した直後である。`Node.transfer` の TVT 通過成功の後である。observer は記録だけを行い、実 World の交通は変えない。baseline collector の prepare と apply を actual passage observation の正本にはしない。

追跡対象は selected candidate だけである。識別は Vehicle 名だけではなく VisitKey を使う。同じ Vehicle が同じ Node を再訪するためである。

### 7.2 buyer・seller の取引全体 ex-post evaluation result

役割: 同じ取引の buyer・seller の actual passage が全て揃った後に計算する。buyer・seller だけを対象とする。nonparticipating の actual passage 完了を待たない。

含む内容: 事後評価上の成立・不成立、buyer 全体の実績節約価値、seller 全体の実績要求補償、実績ベース参考支払、実績ベース参考補償、第3巻で確定済みの取引全体評価。Vehicle 単独の actual passage 観測時点では、参考金額、事後成立判定、満足分類などは未完成である。

### 7.3 Vehicle 別 role 評価または外部効果 record

役割: buyer・seller の realized gain、満足分類、役割別集計。nonparticipating の実績外部効果。個別 Visit 単位の研究分析。

buyer・seller に必要な申告 VOT、正式支払、正式補償、参考金額、実績利得は、第3巻の既存 actual outcome 仕様に合わせてこの層または関連層へ追加する。本節はそれを削らない。

`actual_time_difference_timesteps = baseline_passage_timestep - actual_passage_timestep`

`actual_time_difference_seconds = actual_time_difference_timesteps × DELTAT`

nonparticipating の実績上の符号付き価値は次である。

`actual_signed_time_value_change = actual_time_difference_seconds × true_vot_per_second`

正は実績上の時間短縮、負は実績上の遅延、0 は変化なしである。未観測なら actual passage、時間差、秒、符号付き価値、予測誤差は `None` である。

評価終了まで actual passage が無ければ、status を `ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END` にして凍結する。その後 record は書き換えない。実 World を評価終了後へ進めない。この評価終了は candidate horizon の終了ではない。

実通過の順序が予測順位と違っても、実測時刻をそのまま記録する。nonparticipating の actual value は支払・補償へ入れない。

予測誤差は次である。

`candidate_passage_prediction_error_timesteps = actual_passage_timestep - predicted_candidate_passage_timestep`

`signed_value_prediction_error = actual_signed_time_value_change - predicted_signed_time_value_change`

【2026-10-02 最新仕様による注記】

- 上記のfield名と式は、過去のCopilotが利用者の明示確認なしに導入したものである。
- 特にcandidate_passage_prediction_error_timestepsは、共通の通過時刻残差をactual minus candidateの向きで保存する案だったが、利用者合意済みの確定仕様ではなかった。
- prediction errorという名称は、引き算の向きと正負の意味がfield名から分からないため、新規実装では使用しない。
- 最新仕様では、方向をfield名で明示した次の共通値を保存する。

```text
candidate_minus_actual_passage_timesteps
= candidate_passage_timestep - actual_passage_timestep

candidate_minus_actual_passage_seconds
= candidate_minus_actual_passage_timesteps × DELTAT

candidate_minus_actual_time_value
= candidate_minus_actual_passage_seconds × true_vot_per_second
```

- 旧candidate_passage_prediction_error_timestepsは、新規実装へ引き継がない。
- 旧signed_value_prediction_errorが表そうとしていた値は、最新仕様ではcandidate_minus_actual_time_valueとして方向を明示して保存する。
- role別指標は、この共通値から後続評価層で導出する。
- 最新の正式参照先は、第4巻末尾
  「TVT-MP actual passage基盤 実装項目1の確定設計・実装・検証結果（2026-10-02）」
  §5および§6である。

未観測なら `None` である。正の価値誤差は、実績が予測より短縮側である。

## 8. buyer・seller の事後評価との分離

第3巻どおり、同じ取引の buyer・seller の actual passage が全て揃った時点で、buyer・seller の事後評価を始める。nonparticipating の actual passage 完了は待たない。

nonparticipating が未観測でも、buyer・seller の事後評価、実績ベース参考金額、正式支払、正式補償は保留も変更もしない。参考金額は buyer・seller だけである。nonparticipating の actual value は、事後評価上の成立・不成立にも、参考支払、参考補償、正式支払、正式補償にも入れない。正式支払と正式補償は成立時点で確定済みであり、actual passage では変えない。

nonparticipating の実績は、通過した時点で外部効果として別に記録する。評価終了まで通過しなければ、その Visit だけ未観測とする。buyer・seller の事後評価結果は、それによって変えない。

## 9. 経済処理・順位・適用

変えないものは、`total_buyer_value_G`、`total_required_compensation_R`、surplus、`economically_feasible`、`infeasibility_reasons`、selected candidate、buyer payment、seller compensation、final rank の決定、final consistency validation、atomic apply の成立条件である。

buyer・seller 未観測は現行どおり economic unresolved である。nonparticipating だけ未観測なら unresolved にしない。

外部効果は別集計できる。candidate ごとの予測外部効果、selected candidate の正式な予測外部効果、selected candidate の実績外部効果、予測対実績の誤差である。候補選択には使わない。全 FIFO True candidate の local result に予測 record を残すことと矛盾しない。

## 10. Stage 2 と Stage 3

Stage 2 の通常ケースでは、新終了条件による追加 timestep は発生しない。原因は、nonparticipating が buyer・seller 完了前に既に通過しているか、nonparticipating がいないことである。

`("B",)` は nonparticipating が 0 件である。buyer・seller 完了も traffic observation 完了も offset 3 である。`final_offset` は変わらない。

`("D",)` では C が offset 4 で通過し、buyer・seller 完了は offset 5 である。traffic observation 完了も offset 5 である。`final_offset` は変わらない。

`("B","D")` も C が offset 4 で通過し、buyer・seller 完了と traffic observation 完了は offset 5 である。`final_offset` は変わらない。

Stage 3 の境界ケースは、追加終了条件の根拠である。現行仕様では C 未通過のまま buyer・seller 完了で正常終了した。これは不具合ではない。

`("D",)` では buyer・seller 完了が offset 5 であり、その時点の C は未通過である。新仕様では finished にしない。offset 6 以降も同じ local World で続ける。終了は C の通過、または offset 24 である。horizon は 25 なので許容 offset は 0 から 24 である。C の candidate passage は未実行のため未確定である。horizon 末尾まで未通過なら `UNOBSERVED_AT_HORIZON` である。

`("B","D")` は selected candidate であり、C は trade_scope 内 nonparticipating である。同じ終了条件を適用する。economic、selection、payment、final rank、validation、atomic apply の意味は変えない。反証レビュー時点では、C が nonparticipating であること以外、buyer・seller 完了 offset と offset 5 時点の C 状態は未確認である。`("D",)` と同じ数値を推測で書かない。

Stage 3 の静的見通し（candidate `("D",)`、反証レビューと Terminal 独立確認）:

- offset 5 で D、A、B は binding 通過済み、C は未通過である。
- C の最後の skip は `OUTLINK_ENTRY_SPACE_UNAVAILABLE` である。
- offset 5 後の Vehicle advance により、`out_c` 上の A が入口閾値より先へ進む見込みがある。
- C の inlink `capacity_out_remain` は通過可能量を保持する。D、A、B は既通過集合に入る。C は `in_np` の物理先頭で route は `out_c` である。
- 静的条件では offset 6 で C が通過できる可能性が高い。ただし正式な candidate passage timestep は未実行のため未確定である。

診断を拡張するときの assert 候補は次である。nonparticipating が未通過かつ horizon 未到達なら `finished=False` である。buyer・seller 完了後も local loop が続く。C の通過時または horizon 末尾で `finished=True` である。economic required の完了時刻と、traffic observation の完了時刻を保存する。C は candidate passage または `UNOBSERVED_AT_HORIZON` である。予測符号付き価値は数値または `None` である。既存の economic、selection、payment、final rank、validation、atomic apply は不変である。`timestep_results` 数は `final_offset + 1`、`simulated_timestep_count` は `final_offset` である。

### 10.1 Stage 3 診断拡張の制約（反証レビュー）

現行本番 module は offset 5 で `_finished=True` と `_final_result` を設定する。現行 one-timestep API は finished state を拒否する。finished flag の強制解除、mock、patch、手動 result では新終了条件の正式検証にならない。本番終了条件を変更しないまま、現行 one-timestep API で offset 6 へ進むことはできない。

binding、virtual time、advance、boundary を診断側で個別に呼べば、C が次 scan で物理通過可能かだけは確認できる。ただし、それは新しい finished・resolved・result 契約の検証にはならない。新終了条件の正式診断は、本番終了条件を変更した実装と同時に行う必要がある。Stage 3 の offset 6 以降の診断拡張を、本番変更なしで先行できる作業として扱わない。

## 11. 未実装と再開

未実装は、本節の終了条件変更、traffic observation record、actual passage の捕捉、actual outcome 各層、nonparticipating の外部効果集計、World 側 actual passage 待ち registry である。診断スクリプトもまだ新終了条件を assert していない。本番実装はまだ行わない。

反証レビュー（2026-09-30 完了）では BLOCKER は無かった。IMPORTANT は次の 3 件であり、本節 §4.3、§5、§6、§7、§10.1 に反映済みである。

1. `resolved` と `stop_reason` の現行一対一を維持し、nonparticipating 未観測は traffic observation 側で表す。
2. true VOT は decision 時点の candidate local World 作成時に凍結し、live 読み直しをしない。
3. actual passage observation と取引全体 ex-post evaluation を分離し、waiting は World 側 registry で管理する。

再開時は本節と、進捗第3巻「trade_scope全Visit観測の完全実装前仕様（2026-09-30）」を最初に確認する。過去の再開項目として「本仕様に対する反証レビューと、Stage 3 の offset 6 以降を見る診断拡張」は履歴に残す。反証レビューにより、診断拡張単独は本番終了条件実装前には正式検証にならないと判明した。次作業は、完全実装前仕様の残る型・state 不変条件を詰め、本番終了条件実装と診断拡張を同一実装段階で行うための計画作成である。本番実装はまだ行わない。

**本節は実装前仕様の正式記録である。** 2026-10-01 に完了した candidate predicted traffic observation（trade_scope 全 Visit 観測）の実装・検証の最新参照先は、本巻末尾の「TVT-MP trade_scope全Visit観測 実装・検証結果（2026-10-01）」である。本節 §10・§10.1・§11 の「本番実装はまだ行わない」「offset 6 正式診断は未実装」等は、当時の制約下の記録として削除しない。

---

# TVT-MP trade_scope全Visit観測 実装・検証結果（2026-10-01）

本節は、2026-10-01 時点で push 済みの実装と検証の正式記録である。**trade_scope 全 Visit の candidate passage 観測（予測時間・予測符号付き価値・temporary skip・clearance 文脈・終了条件・frozen final result）について、本節が最新参照先である。** 設計意図・actual outcome 層・研究上の未確定契約は、直前の「TVT-MP trade_scope全Visitのcandidate passage観測とnonparticipating予測・実績時間価値 完全実装前仕様（2026-09-30）」を過去の正式記録として残す。削除も短縮もしない。

進捗第3巻の対応節は「TVT-MP trade_scope全Visit観測 実装完了要約（2026-10-01）」と、末尾「最新の再開地点（2026-10-01）」である。

## 保存済み実装コミット（push 済み・最新 `37c1ea6`）

| コミット | 内容 |
|----------|------|
| `c0b4484` | TVT-MP trade-scope traffic observation 型と初期化 |
| `93fbdc9` | candidate passage 時刻・価値観測の record 提案 |
| `f9f0f4e` | required passage と trade-scope 観測の joint state 記録、完了時刻追跡 |
| `b0ba281` | trade-scope Visit の最終 temporary-skip 理由と clearance scan-stop context |
| `37c1ea6` | trade-scope 観測完了・final result record・Stage 3 offset 6 診断 assert |

主な本番変更ファイル: `uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`。診断（本節の検証の一部）: `diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py`（コミット `37c1ea6` に含む）。

## 1. 実装対象（今回の範囲）

各 FIFO True candidate について、**trade_scope 内**の buyer・seller・nonparticipating 全 Visit に対し、次を candidate local virtual loop 上で記録し、final result に frozen 保存する。

- candidate passage 時刻（binding transfer 成功時）
- baseline passage との差（予測時間差）
- decision 時点で凍結した true VOT による予測符号付き時間価値
- temporary skip の最終理由と最終 offset
- clearance による scan-stop context（clearance 停止対象のみ）
- economic required（buyer・seller required passage）完了 offset / virtual timestep
- trade_scope 全 Visit 観測完了 offset / virtual timestep
- horizon 末尾まで未観測の確定（`UNOBSERVED_AT_HORIZON`）

**今回未実装（§14）:** 実 World の actual passage、World 側 passage-wait registry、actual observation record、buyer・seller 取引全体 ex-post evaluation、Vehicle 別 role 評価、nonparticipating の actual 外部効果、評価終了時の actual 未観測確定、実験出力・集計。

## 2. 観測初期化

- 対象 Visit は `trade_scope_of_this_candidate_visits` のみ。binding partition 1・2・4（trade_scope 外）は **含めない**。
- `true_vot_per_second` は candidate local World 作成時点の local `Vehicle` から **凍結** する。result 生成時や後段で live 読み直ししない。
- `baseline_passage_timestep` は正式 baseline collector 由来の値を用いる。
- 現行コード契約どおり **true VOT は 0 以上を許容** する（負値は拒否する既存契約は維持）。
- 研究上の「true VOT=0 を常に許すか」最終契約は VOT 分布に依存し、**未確定のまま**（完全実装前仕様 §4.3 と同趣旨）。

## 3. passage 記録（binding transfer と同期）

- **required passage record** は buyer・seller のみ。
- **traffic observation record** は buyer・seller・nonparticipating。
- いずれも **同一 binding transfer scan 結果・同一 virtual timestep** から記録する。
- buyer と seller の両 traffic observation で `candidate_passage_timestep` は **一致必須**。state 更新前に両方の反映可能性を検査し、required だけ、または traffic observation だけの **片側反映を防止** する。
- binding による物理 transfer は **rollback しない**（既存 binding 契約）。

## 4. 予測値（candidate local・観測済み Visit）

```text
predicted_time_difference_timesteps
  = baseline_passage_timestep - candidate_passage_timestep

predicted_time_difference_seconds
  = predicted_time_difference_timesteps × DELTAT

predicted_signed_time_value_change
  = predicted_time_difference_seconds × true_vot_per_second（decision 時点凍結）
```

- 正: 時間短縮・便益。負: 遅延・損失。0: 変化なし。
- 丸め、tolerance、`Decimal` は **不使用**。
- **economic evaluation の申告 VOT 計算（`G`・`R`・surplus・feasibility）は変更していない。** 予測符号付き価値は traffic observation 側の研究用 field である。

## 5. temporary skip と clearance

- temporary skip 時: `last_checked_offset` / `last_checked_virtual_timestep`、**最終** `last_temporary_skip_reason` / `last_temporary_skip_offset` を更新。
- clearance 理由は temporary skip 履歴に **混ぜない**。
- clearance で scan が止まった対象 Visit にのみ `latest_clearance_stop_context` を保存。
- clearance 停止位置より **後方の未走査 Visit** は last checked を更新しない。
- 観測済み Visit への再 skip・再 clearance は **重大不整合**（テストで拒否）。
- final frozen record では、過去に記録した最終 skip と clearance context を **保持** する。

## 6. 終了条件（本番実装済み）

```text
resolved_after_timestep_end
  ⇔ buyer・seller の required passage が全件完了

calculation_finished_after_timestep_end
  ⇔ trade_scope 全 Visit の candidate passage が全件観測済み
  または offset == configured_horizon_steps - 1
```

- buyer・seller 完了だけでは `calculation_finished_after_timestep_end` を **True にしない**。
- nonparticipating が未通過なら **同じ local loop・同じ local World** を継続する。horizon は **延長しない**。
- `resolved` と `stop_reason` の既存一対一を維持: `resolved=True` → `RESOLVED`、`resolved=False` → `HORIZON_EXHAUSTED_UNRESOLVED`。
- nonparticipating の horizon 未観測だけでは `unresolved_reasons` に **入れない**（economic unresolved とは分離）。

**Stage 3 で起きたことの原因（要約）:** buyer・seller（D・A・B）は approach inlink の有限 `capacity_out` リフィル後、offset 5（vt 15）で binding transfer 完了し economic required が閉じる。nonparticipating C は同じ offset では `out_c` の **OUTLINK_ENTRY_SPACE_UNAVAILABLE**（`out_c` 上の先行車と jam 密度設計）で未通過のため `resolved=True` でも **finished=False**。offset 6（vt 16）で C が binding 通過し、trade_scope 観測が閉じて finished になる。

## 7. timestep result 追加 field（必須・既定値なし）

`OrderControlTvtMpCandidateVirtualTimestepResult` に追加し、**必須 field** として構築する（省略・既定値なし）。

- `traffic_observation_complete_after_node_passage`
- `economic_required_first_completed_at_this_timestep`
- `traffic_observation_first_completed_at_this_timestep`

## 8. final result 追加 field（必須・既定値なし）

`OrderControlTvtMpCandidateLocalVirtualCalculationResult` に追加し、**必須 field** として構築する。

- `traffic_observation_records`
- `economic_required_passages_complete_offset`
- `economic_required_passages_complete_virtual_timestep`
- `all_trade_scope_passages_complete_offset`
- `all_trade_scope_passages_complete_virtual_timestep`

## 9. final traffic observation 状態

**観測済み:**

- `passage_observation_status = OBSERVED`
- `horizon_exhausted = False`
- `observation_complete = True`
- candidate passage・observed offset/virtual timestep・時間差・符号付き価値を記録

**horizon 未観測:**

- `passage_observation_status = UNOBSERVED_AT_HORIZON`
- `horizon_exhausted = True`
- `observation_complete = False`
- candidate passage、observed 時刻、時間差、価値は **`None`**（horizon 末尾時刻や 0 を **代入しない**）
- last checked、最終 skip、clearance context は **保持**

## 10. Stage 2 診断結果（通常ケース・原因付き）

診断 World では、nonparticipating C が buyer・seller required 完了 **前** に binding 通過する（Stage 2 専用レイアウト・容量条件）。したがって **新終了条件でも追加 offset は発生しない**。

| candidate | final_offset | 原因要約 |
|-----------|--------------|----------|
| `("B",)` | 3 | nonparticipating 0 件。required 完了と traffic observation 完了が同時。 |
| `("D",)` | 5 | C が offset 4 前後で通過済み。offset 5 で required と trade_scope 観測が同時完了。 |
| `("B","D")` | 5 | 同上。C 先行通過のため offset 5 で finished。 |

economic evaluation、selection、payment、compensation、final rank、validation、atomic apply の意味は **維持**（§12）。

## 11. Stage 3 診断結果（境界ケース・実測固定）

旧仕様では buyer・seller 完了（offset 5）で local 計算が終了していた。新仕様では **offset 5 で resolved・economic required 完了、offset 6 で trade_scope 完了と finished**。

### 11.1 candidate `("D",)`

| 項目 | 値 | 原因・備考 |
|------|-----|------------|
| buyer・seller required 完了 | offset 5 / vt 15 | D・A・B が同一 scan で binding transfer |
| `resolved_after_timestep_end` | offset 5 で True | economic required 完了 |
| `calculation_finished_after_timestep_end` | offset 5 で **False** | C 未通過 |
| C 最終 temporary skip | `OUTLINK_ENTRY_SPACE_UNAVAILABLE` @ offset 5 | `out_c` 入口空間不足 |
| C binding 通過 | offset 6 / vt 16 | 同一 local World 継続後の通過 |
| `final_offset` / `final_virtual_timestep` | 6 / 16 | trade_scope 観測完了で停止 |
| `simulated_timestep_count` | 6 | 既存契約 `== final_offset` |
| economic required 完了 | offset 5 / vt 15 | timestamps field |
| trade_scope 全 Visit 完了 | offset 6 / vt 16 | timestamps field |
| C baseline / candidate passage | 17 / 16 | 予測短縮 1 timestep |
| C `predicted_signed_time_value_change` | 6.0 | `DELTAT=1`、凍結 true VOT=6.0 |
| C in `required_passage_records` | **含めない** | nonparticipating |

### 11.2 candidate `("B","D")`（selected・実測固定）

| 項目 | 値 | 原因・備考 |
|------|-----|------------|
| `final_offset` / `final_virtual_timestep` | 6 / 16 | C 観測完了まで継続 |
| `simulated_timestep_count` | 6 | |
| economic required 完了 | offset 6 / vt 16 | A の required が offset 6 で記録 |
| trade_scope 全 Visit 完了 | offset 6 / vt 16 | |
| C 通過 | offset 5 / vt 15 | binding transfer で観測（`("D",)` より早い） |
| C traffic | `OBSERVED`, candidate passage 15 | baseline 17 → 予測短縮 2 timestep、符号付き価値 12.0 |
| C in `required_passage_records` | **含めない** | |
| selected candidate | `("B","D")` | 変更なし |

反証レビュー時点の「`("B","D")` の offset 5 時点 C 状態未確認」は、本実装・診断 assert により **解消** した。過去の未確認記述は完全実装前仕様 §10 に **履歴として残る**。

## 12. downstream 不変（検証で確認）

次は **変更していない**。

- `total_buyer_value_G`
- `total_required_compensation_R`
- surplus
- feasibility（`economically_feasible`・`infeasibility_reasons`）
- candidate selection（Stage 3 selected は `("B","D")` のまま）
- payment
- compensation
- final rank
- final consistency validation
- atomic apply

## 13. 検証結果（保存済み・再現手順）

### 13.1 関連テスト（8 ファイル・334 passed）

コミット列 `c0b4484`〜`37c1ea6` に直接触れたテスト 6 ファイルと、同一 TVT-MP パイプライン回帰 2 ファイルをまとめて実行し、**334 passed**（保存済み検証結果）。

1. `tests_order_control_tvt_mp_candidate_local_virtual_calculation.py`
2. `tests_order_control_tvt_mp_local_virtual_calculation_set.py`
3. `tests_order_control_tvt_mp_candidate_selection.py`
4. `tests_order_control_tvt_mp_economic_evaluation.py`
5. `tests_order_control_tvt_mp_payment_and_compensation.py`
6. `tests_order_control_tvt_mp_final_rank.py`
7. `tests_order_control_tvt_mp_driver.py`
8. `tests_order_control_tvt_mp_atomic_apply.py`

### 13.2 診断

- `python diagnostics/order_control/tvt_mp_single_decision_baseline_diagnostic.py` → **exit 0**
- Stage 2・Stage 3 含む全段 → **exit 0**
- **Stage 3 counterexample asserts: PASS**（offset 6 継続・C traffic observation・`("B","D")` 実測を明示 assert）

### 13.3 既存回帰

- FCFS・BATCH関係: **366 passed**（保存済み検証結果）
- UXsim 正式サンプル（保存済み数値と一致）:
  - completed trips **735 / 810**
  - average speed **11.7 m/s**
  - total travel time **119475.0 s**
  - average travel time **162.6 s**
  - average delay **62.6 s**
  - delay ratio **0.385**
  - total distance traveled **1632250.0 m**

### 13.4 静的検査

- 変更本番・テストの `py_compile`: **成功**（保存済み）
- `git diff --check`: **成功**（保存済み）

## 14. 未実装範囲（今回の実装と混同しない）

次は **今回未実装** である（完全実装前仕様 §7・§8 と同層。本節の candidate predicted 観測とは別）。

- 実 World の **actual passage** 捕捉
- World 側 **passage-wait registry**
- **actual passage observation record**（frozen `order_exchange_log`）
- buyer・seller の **取引全体 ex-post evaluation**
- **Vehicle 別 role 評価**
- nonparticipating の **actual 外部効果**
- 評価終了時の **actual 未観測確定**
- 実験出力と集計

## 15. 再開時の読み順

1. **本節**（実装・検証の最新）
2. 完全実装前仕様（2026-09-30）（設計・actual 層・研究契約）
3. 進捗第3巻末尾「最新の再開地点（2026-10-01）」

actual passage 基盤の **詳細実装前設計** を確認してから、実 World 側実装に進む。診断のみで offset 6 を先走り検証する必要は、本実装完了により **過去の再開項目** となった（履歴は残す）。

# TVT-MP actual passage基盤 実装項目1の確定設計・実装・検証結果（2026-10-02）

**本節が、actual passage 基盤実装項目1完了後の正式参照先である。** 過去節（§14「未実装範囲」に actual passage 基盤未実装の記述、§15 再開時の読み順、進捗第3巻「未実装（actual 系）」「actual passage 基盤へ直ちに本番実装へ進まない」等）は **当時の記録として削除・改変しない**。最新状態は **本節** で上書き参照する。

## 1. 現在地

- candidate predicted traffic observation はコミット `e12a24c` まで実装・検証・文書化され、**push 済み**である。
- actual passage 基盤の **実装項目1** はコミット `4dc4862` で実装され、リモートブランチへ **push 済み**である。
- ローカル HEAD と `origin/feature/intersection-order-control` は **`4dc4862` で一致**している。
- 既存未追跡ファイル `diagnostics/order_control.zip` だけが残り、**stage・変更・削除していない**。

## 2. actual系工程管理基準

現時点の actual 系工程管理基準は、**8 つの実装項目**と **2 つの仕上げ項目**である。

今回完了したのは **実装項目1**:

- actual 用 enum
- frozen actual passage observation record
- mutable Visit wait entry
- mutable transaction wait state
- mutable wait registry
- World 上の空 registry 初期化
- 専用テスト

上記 10 項目（actual 系全体の 8 つの実装項目と 2 つの仕上げ項目）は、現在確認済みの基準計画である。重大な未確認依存、重大な不整合、設計矛盾が後から判明する可能性まで含めて、**追加工程なしでの完了を絶対保証するものではない**。

actual 系全体の残りは、現時点で **実装項目 7 つ**、**仕上げ項目 2 つ**である。

## 3. 実装した型

**新規ファイル:**

`uxsim/order_control_tvt_mp_actual_passage.py`

**実装型:**

- `OrderControlTvtMpActualPassageRole`
- `OrderControlTvtMpActualPassageObservationStatus`
- `OrderControlTvtMpActualPassageWaitStatus`
- `OrderControlTvtMpActualPassageObservationRecord`
- `OrderControlTvtMpActualPassageWaitEntry`
- `OrderControlTvtMpActualPassageTradeWait`
- `OrderControlTvtMpActualPassageWaitRegistry`

**役割:**

- `OrderControlTvtMpActualPassageObservationRecord` は **frozen**
- `OrderControlTvtMpActualPassageWaitEntry`、`OrderControlTvtMpActualPassageTradeWait`、`OrderControlTvtMpActualPassageWaitRegistry` は **mutable**
- live な World、Vehicle、Node、Link は **保持しない**
- VisitKey は `OrderControlTvtVisitKey` を使用
- 取引識別の正本は `tvt_decision_timestep`、`node_name`、`buyers_sorted`
- entry 照合 key は `(node_name, visit_key)`
- transaction key は `(tvt_decision_timestep, node_name, buyers_sorted)`

**循環 import 回避（実装メモ）:** `OrderControlTvtMpCandidatePassageObservationStatus` は `uxsim.py` 先頭 import と TVT-MP 依存鎖の循環を避けるため、`order_control_tvt_mp_actual_passage.py` では `TYPE_CHECKING` 内 import と `from __future__ import annotations` を用いる。型注釈は維持し、モジュールロード時に candidate 側を引き込まない。

## 4. status

**actual passage observation status**（frozen observation record 用。`WAITING` は含めない）:

- `ACTUAL_PASSAGE_OBSERVED`
- `ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END`

**mutable wait status**（World 側 registry のみ）:

- `WAITING_FOR_ACTUAL_PASSAGE`
- `ACTUAL_PASSAGE_OBSERVED`
- `ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END`

`WAITING_FOR_ACTUAL_PASSAGE` を frozen `order_exchange_log` record として追加しない。待機中状態は **World 側 mutable registry だけ**で管理する。

## 5. 共通passage差分の確定設計

buyer、seller、nonparticipating の role に依存しない通過時刻の共通基盤として、**3 組の値**を明示保存する。

### baselineとcandidate

```
baseline_minus_candidate_passage_timesteps
  = baseline_passage_timestep - candidate_passage_timestep

baseline_minus_candidate_passage_seconds
  = baseline_minus_candidate_passage_timesteps × DELTAT

baseline_minus_candidate_time_value
  = baseline_minus_candidate_passage_seconds × true_vot_per_second
```

### baselineとactual

```
baseline_minus_actual_passage_timesteps
  = baseline_passage_timestep - actual_passage_timestep

baseline_minus_actual_passage_seconds
  = baseline_minus_actual_passage_timesteps × DELTAT

baseline_minus_actual_time_value
  = baseline_minus_actual_passage_seconds × true_vot_per_second
```

### candidateとactual

```
candidate_minus_actual_passage_timesteps
  = candidate_passage_timestep - actual_passage_timestep

candidate_minus_actual_passage_seconds
  = candidate_minus_actual_passage_timesteps × DELTAT

candidate_minus_actual_time_value
  = candidate_minus_actual_passage_seconds × true_vot_per_second
```

- **3 組をすべて明示保存**する。数学的には一部を他の値から導出できるが、後から瞬間的に理解しやすくし、**引き算の向きを field 名だけで確認**できるようにするため、明示保存を採用した。
- 曖昧な prediction error 名称は使用しない。field 名で引き算の向きを明示する。
- time value は **decision 時点で確定した `true_vot_per_second`** による研究・観測用の値である。
- **支払、補償、実績ベース参考支払、実績ベース参考補償、事後成立判定**には、成立時 record に保存した **`declared_vot_per_second`** を使用する。共通 true VOT time value を経済評価へ流用しない。

**§5 補足（旧式との関係）**

- 第3巻のbuyer旧式「予想時間節約 minus 実績時間節約」と、第4巻の旧candidate_passage_prediction_error_timestepsは、利用者が明示確定した式ではない。
- これらを新規実装の参照元にしない。
- sellerの旧式は数値上、最新のpredicted_based_actual_delay_timestepsと一致するが、最新実装では方向明示型の共通fieldとrole別名称を使用する。
- 2026-10-02節§5・§6を、この問題に関する最新仕様の正本とする。

## 6. role別指標への導出

role 別指標は共通 passage 差分から導出する。これらは後続の **Vehicle 別 role 評価 record** で扱い、今回の actual passage observation record へ **重複保存しない**。

### buyer

```
predicted_time_saving_timesteps
  = baseline_minus_candidate_passage_timesteps

actual_time_saving_timesteps
  = baseline_minus_actual_passage_timesteps

predicted_based_actual_saving_timesteps
  = candidate_minus_actual_passage_timesteps

predicted_saving_time_value
  = baseline_minus_candidate_time_value

actual_saving_time_value
  = baseline_minus_actual_time_value

predicted_based_actual_saving_time_value
  = candidate_minus_actual_time_value
```

正の `predicted_based_actual_saving` は、実際の通過が candidate 予測より早く、予測以上の時間節約が得られたことを表す。

### seller

```
predicted_delay_timesteps
  = -baseline_minus_candidate_passage_timesteps

actual_delay_timesteps
  = -baseline_minus_actual_passage_timesteps

predicted_based_actual_delay_timesteps
  = -candidate_minus_actual_passage_timesteps

predicted_delay_time_value
  = -baseline_minus_candidate_time_value

actual_delay_time_value
  = -baseline_minus_actual_time_value

predicted_based_actual_delay_time_value
  = -candidate_minus_actual_time_value
```

正の `predicted_based_actual_delay` は、実績遅延が candidate 予測より大きかったことを表す。

seller が baseline より早く通過した場合も **seller のまま**であり、buyer へ変更しない。時間評価では **負の遅延を保持**する。補償計算では後続仕様どおり非負遅延を使用するが、**今回の実装項目1では計算しない**。

### nonparticipating

```
predicted_signed_time_difference_timesteps
  = baseline_minus_candidate_passage_timesteps

actual_signed_time_difference_timesteps
  = baseline_minus_actual_passage_timesteps

predicted_based_actual_signed_difference_timesteps
  = candidate_minus_actual_passage_timesteps

predicted_signed_time_value
  = baseline_minus_candidate_time_value

actual_signed_time_value
  = baseline_minus_actual_time_value

predicted_based_actual_signed_time_value
  = candidate_minus_actual_time_value
```

nonparticipating は外部効果として評価し、buyer または seller へ役割変更しない。支払、補償、参考金額、事後成立判定へ **含めない**。

## 7. ObservationRecordとWaitEntryの責務

### ObservationRecord に保存するもの

- 取引識別（`tvt_decision_timestep`、`node_name`、`buyers_sorted`）
- Visit 識別（`visit_key`、`vehicle_name`）
- `role`
- `observation_status`
- `baseline_passage_timestep`、`candidate_passage_timestep`
- `actual_passage_timestep`、`actual_route_next_link_name`
- `predicted_observation_status`（candidate 側）、`predicted_route_next_link_name`
- `true_vot_per_second`
- **3 組 9 field** の共通 passage 差分:
  - `baseline_minus_candidate_passage_timesteps` / `_passage_seconds` / `_time_value`
  - `baseline_minus_actual_passage_timesteps` / `_passage_seconds` / `_time_value`
  - `candidate_minus_actual_passage_timesteps` / `_passage_seconds` / `_time_value`

**未観測 record**（`ACTUAL_PASSAGE_UNOBSERVED_AT_EVALUATION_END`）では:

- `baseline_minus_candidate` の 3 値は既知なので **保持できる**
- `baseline_minus_actual` の 3 値は **None**
- `candidate_minus_actual` の 3 値は **None**
- `actual_passage_timestep` と `actual_route_next_link_name` は **None**

実装項目1では record 生成時の **計算 helper は未実装**。型として値を保持できることのみを専用テストで確認した。

### WaitEntry に保存するもの（actual passage 前に確定しているもののみ）

- `baseline_passage_timestep`、`candidate_passage_timestep`
- `baseline_minus_candidate_passage_timesteps` / `_passage_seconds` / `_time_value`
- `true_vot_per_second`
- `predicted_observation_status`、`predicted_route_next_link_name`
- mutable `wait_status`
- 後続で actual observation record を関連付ける `actual_passage_observation_record`（初期は `None` 可）

`baseline_minus_actual_*` と `candidate_minus_actual_*` は、actual passage 前の WaitEntry へ **先に保存しない**。後続 observer が actual passage を観測した時点で ObservationRecord へ保存する。

## 8. World初期化

`uxsim/uxsim.py` の `World.__init__` に次の属性を追加した。

```
order_control_tvt_mp_actual_passage_wait_registry
```

各 World 生成時に、新しい空の `OrderControlTvtMpActualPassageWaitRegistry` を生成する。World 間で registry および内部 dict（`entries_by_node_name_and_visit_key`、`trades_by_transaction_key`）を **共有しない**。

交通処理、atomic apply、Node.transfer、evaluation end、`Vehicle.order_exchange_log` には **まだ接続していない**。

## 9. 実装範囲外（実装項目1）

今回 **未実装**:

- atomic apply 成功時の registry 登録
- registration proposal
- TVT 物理通過後の actual passage observer
- `Vehicle.order_exchange_log` への actual observation record 追加
- 評価終了時の未観測確定
- buyer・seller 完了通知
- ex-post evaluation
- Vehicle 別 role 評価
- nonparticipating actual 外部効果の計算
- 実験出力と集計

交通動作と既存 log 内容は **変わっていない**。

## 10. 検証結果（保存済み）

**専用テスト:** `tests_order_control_tvt_mp_actual_passage.py` — **15 passed**

観測内容の例（専用テスト fixture）:

- observed record: `baseline_passage_timestep=10`, `candidate_passage_timestep=8`, `actual_passage_timestep=7`, DELTAT 相当 60, `true_vot_per_second=0.5` → 9 field 整合（例: `baseline_minus_candidate_passage_timesteps=2`, `baseline_minus_actual_passage_timesteps=3`, `candidate_minus_actual_passage_timesteps=1` 等）
- frozen 確認用 fixture は同一 baseline/candidate/DELTAT/VOT で `actual_passage_timestep=1` と整合した 6 値（9/540/270.0 と 7/420/210.0）を使用
- 未観測 record: baseline_minus_candidate 3 値保持、actual 依存 6 値は None

**TVT-MP 関連 9 テストファイル: 349 passed**

- candidate predicted 側の既存 8 ファイル **334 件**
- actual passage 専用 **15 件**

**candidate local calculation と atomic apply の限定回帰: 116 passed**

**FCFS・BATCH: 366 passed**（約 5 分 23 秒、保存済み）

**py_compile:** 成功（`order_control_tvt_mp_actual_passage.py`、`uxsim.py`、専用テスト）

**git diff --check:** 成功

**UXsim 正式サンプル**は実装項目1では **再実行していない**。重要実装段階の完了時に再実行する。

## 11. 保存済みコミット

```
4dc4862
implement TVT-MP actual passage observation types, wait registry, and World initialization
```

リモートブランチへ push 済み。HEAD と `origin/feature/intersection-order-control` は一致している。

## 12. 次の作業

**次は実装項目2: atomic apply 成功後の registry 一括登録**（依存順を崩さない）。

必要内容:

- selected candidate の buyer・seller・nonparticipating **全件**を登録
- registration proposal を先に **全件作成**
- 登録前に **全不変条件を検査**
- atomic apply 成功 commit の末尾で **一括反映**
- apply 失敗時は registry へ **何も残さない**
- buyer・seller と nonparticipating の **true VOT 正本を区別**
- selected candidate の traffic observation から **predicted 情報を引き継ぐ**

実装項目2へ進む前に、**読取り専用**で確認する対象:

- atomic apply の proposal、validation、commit 境界
- 成立時 log record
- selected candidate traffic observation
- buyer・seller の true VOT 正本
- nonparticipating の true VOT 正本
- apply 失敗時の非反映契約

実装項目2の範囲を **atomic apply 登録だけ**に限定する。Node.transfer、evaluation end、buyer・seller 完了通知、ex-post evaluation、Vehicle 別 role 評価、実験出力へ **接続しない**。

# TVT-MP actual passage基盤 実装項目2 完全実装前設計（2026-10-02）

**本節が、actual passage 基盤実装項目2の完全実装前設計の正式参照先である。** 実装項目1完了節（同日、直前）は当時の確定設計・実装・検証結果として残す。本節はコード実装前の仕様であり、実装結果の記録ではない。

## 1. 目的と範囲

実装項目2の目的は、atomic apply で成立した selected candidate について、buyer、seller、nonparticipating の actual passage 待機情報を World 側 registry へ登録することである。

**今回実装するもの:**

- selected candidate の trade_scope 内 buyer、seller、nonparticipating 全件の registration proposal
- 全 proposal の事前検査
- 成功 commit 末尾での registry 一括反映
- apply 失敗時の registry 非反映
- buyer、seller、nonparticipating で異なる true VOT 正本の使用
- candidate traffic observation から predicted 情報を引き継ぐ
- `buyers_sorted` の正式型への訂正
- 専用テストと atomic apply 回帰

**今回実装しないもの:**

- Node.transfer
- actual passage observer
- actual passage observation record の生成
- `Vehicle.order_exchange_log` への actual record 追加
- evaluation end
- 未観測確定
- buyer・seller 完了通知
- ex-post evaluation
- Vehicle 別 role 評価
- nonparticipating actual 外部効果の計算
- 実験出力と集計

## 2. 独立確認済みのatomic apply構造

現在の atomic apply は、全 Node・全 Vehicle の prepare を完了してから commit する。

**現在の commit 順:**

1. rank state
2. `Vehicle.payment_paid`
3. `Vehicle.payment_received`
4. `Vehicle.order_exchange_log`

registry 登録も同じ prepare・commit 契約へ追加する。

- prepare 中に live registry を書き換えない
- 全 Node 分の proposal と既存 registry の重複を commit 開始前に検査する
- registry 用の完成済み replacement dict を prepare する
- 既存 4 種類の commit 完了後、return 直前に registry の 2 つの dict を一括代入する
- commit 中に検索、照合、再検査、再計算を行わない
- selected Node が 0 件なら registry dict を不要に置き換えない

公開関数 `apply_tvt_mp_validated_result` の引数は 3 つのままである。registry は引数に増やさず、`real_W.order_control_tvt_mp_actual_passage_wait_registry` を使う。

## 3. selected candidateからの情報経路

正式な参照経路:

```text
selected_candidate_economic_result
→ candidate_local_virtual_calculation_result
→ traffic_observation_records
```

`traffic_observation_records` は、`trade_scope_of_this_candidate_visits` の順序で 1 件ずつ作られ、final result でも同じ public order で保存される。

**登録対象:**

- buyer
- seller
- nonparticipating

**登録対象外:**

- partition 1
- partition 2
- partition 4
- trade_scope 外 Visit
- fallback
- `NO_VISITS_TO_CONFIRM`

登録対象は final rank 列の全体ではない。fallback と `NO_VISITS_TO_CONFIRM` は registration proposal を返さない。

## 4. buyers_sortedの正式型訂正

actual passage 型の現在の次の型は誤りである。

```text
tuple[str, ...]
```

正式型:

```text
tuple[OrderControlTvtVisitKey, ...]
```

**訂正対象:**

- `OrderControlTvtMpActualPassageObservationRecord.buyers_sorted`
- `OrderControlTvtMpActualPassageWaitEntry.buyers_sorted`
- `OrderControlTvtMpActualPassageTradeWait.buyers_sorted`
- `OrderControlTvtMpActualPassageWaitRegistry` の transaction key

正式な transaction key:

```text
tuple[
    int,
    str,
    tuple[OrderControlTvtVisitKey, ...],
]
```

**原因:**

atomic apply の成立時 record、concrete buyer candidate、trade rank では、`buyers_sorted` は buyer 名ではなく buyer VisitKey の tuple である。同じ Vehicle が同じ Node を再訪できるため、Vehicle 名だけへ縮退させない。

この訂正は新しい成果工程ではなく、実装項目1で判明した型不整合の限定修正として、実装項目2と同時に行う。実装項目1の専用テスト `tests_order_control_tvt_mp_actual_passage.py` は、文字列 tuple でこれらの field を作っているため、VisitKey tuple へ合わせる。

## 5. prepare用内部型

atomic apply 内へ、必要最小限の非公開 prepare 型を追加する。

**推奨概念:** `_PreparedActualPassageNodeRegistration`

保持するもの:

- 1 selected Node 分の `WaitEntry` tuple
- `TradeWait` 1 件

全 Node 分の検査後、registry commit 用として次の概念を用意する。

**推奨概念:** `_PreparedActualPassageRegistryCommit`

保持するもの:

- 対象 registry
- 全 proposal 反映済みの updated entry mapping
- 全 proposal 反映済みの updated transaction mapping

live registry object は prepare 中に変更しない。registry へ method は追加しない。

## 6. buyer・sellerの成立時recordとの対応

buyer・seller については、prepared Vehicle update が保持する成立時 record と traffic observation record を VisitKey で一対一照合する。

成立時 record を作るときに検査した同じ true VOT を registry entry でも使用する。

**手順:**

- `_prepare_one_money_record` で実 World `Vehicle.vot_true` を一度だけ読み、検査する
- 検査済み `true_vot_per_second` で成立時 record を作る
- 同じ成立時 record object を prepared Vehicle update へ保持する
- registry proposal は、その成立時 record の `true_vot_per_second` を使用する
- registry proposal 作成時に live `Vehicle.vot_true` を再読取しない

**照合項目:**

- `visit_key`
- `vehicle_name`
- `node_name`
- `buyers_sorted`
- role
- `baseline_passage_timestep`
- `candidate_passage_timestep`

buyer observation には BUYER 成立時 record がちょうど 1 件必要である。seller observation には SELLER 成立時 record がちょうど 1 件必要である。対応しない buyer・seller 成立時 record を残さない。

## 7. nonparticipatingの情報源

nonparticipating には money record と成立時 record がない。

nonparticipating の `WaitEntry` は candidate traffic observation record から作る。

**true VOT 正本:**

```text
traffic_observation_record.true_vot_per_second
```

nonparticipating について実 World `Vehicle.vot_true` を読まない。既存 atomic apply fixture では、money 対象外 Vehicle の `vot_true` が `None` になり得る。そこを読むと、凍結済み true VOT がある nonparticipating を誤って拒否する。

nonparticipating に buyer または seller の成立時 record が対応する場合は不整合として拒否する。

## 8. WaitEntryへ引き継ぐ情報

各 traffic observation record から次を登録する。

**identity:**

- `tvt_decision_timestep`
- `node_name`
- `buyers_sorted`
- `visit_key`
- `vehicle_name`
- role

**初期状態:**

- `wait_status = WAITING_FOR_ACTUAL_PASSAGE`
- `actual_passage_observation_record = None`

**predicted 情報:**

- `baseline_passage_timestep`
- `candidate_passage_timestep`
- `predicted_observation_status`
- `predicted_route_next_link_name`（traffic observation の `route_next_link_name`。成立時 record の formal route ではない）

**baseline_minus_candidate の 3 値:**

```text
baseline_minus_candidate_passage_timesteps
= traffic observation の predicted_time_difference_timesteps

baseline_minus_candidate_passage_seconds
= traffic observation の predicted_time_difference_seconds

baseline_minus_candidate_time_value
= traffic observation の predicted_signed_time_value_change
```

atomic apply では再計算しない。`DELTAT` を読み直さない。candidate 側の `predicted_time_difference_timesteps` は、観測確定時に `baseline_passage_timestep - candidate_passage_timestep` として既に保存されている。

`baseline_minus_actual_*` と `candidate_minus_actual_*` は、actual passage 前の `WaitEntry` へ保存しない。`OrderControlTvtMpActualPassageObservationRecord` は登録時に作らない。

role 変換は明示的な if/elif で行う。

- `LocalBindingTradeRole.BUYER` → `ActualPassageRole.BUYER`
- `LocalBindingTradeRole.SELLER` → `ActualPassageRole.SELLER`
- `LocalBindingTradeRole.NONPARTICIPATING` → `ActualPassageRole.NONPARTICIPATING`

## 9. candidate observation status

`OBSERVED` と `UNOBSERVED_AT_HORIZON` の両方を actual passage 待機 registry へ登録する。

**OBSERVED:**

- baseline passage は Python int
- candidate passage は Python int
- predicted timestep 差は baseline minus candidate と一致
- predicted seconds と time value は数値
- actual passage の待機を開始する

**UNOBSERVED_AT_HORIZON:**

- `candidate_passage_timestep` は `None`
- `predicted_time_difference_timesteps` は `None`
- `predicted_time_difference_seconds` は `None`
- `predicted_signed_time_value_change` は `None`
- `WaitEntry` の `baseline_minus_candidate` 3 値も `None`
- baseline passage と predicted route は保持
- actual passage の待機は開始する
- `wait_status` は `WAITING_FOR_ACTUAL_PASSAGE`

`passage_observation_status` が `None` なら、final traffic observation ではないため拒否する。horizon 末尾時刻などで `None` を補完しない。`passage_observation_status` が `None` のときは role を問わず拒否する。

**role 別 status 制約（補足）:**

- selected candidate として atomic apply へ到達する buyer・seller は、economic required passage が完了済みであるため、candidate traffic observation status は **`OBSERVED` 必須**である。
- buyer または seller が `UNOBSERVED_AT_HORIZON` なら、selected candidate の成立条件と矛盾するため、prepare で `RuntimeError` として拒否する。
- nonparticipating は `OBSERVED` または `UNOBSERVED_AT_HORIZON` のどちらでも登録する。
- 冒頭の「`OBSERVED` と `UNOBSERVED_AT_HORIZON` の両方を actual passage 待機 registry へ登録する」とは、**全 role が両 status を取り得る**という意味ではない。registry 全体として、**buyer・seller の `OBSERVED`** と、**nonparticipating の `OBSERVED` または `UNOBSERVED_AT_HORIZON`** を扱うという意味である。

## 10. TradeWait

traffic observation records の順序を維持して次を作る。

- `all_visit_keys`
- `buyer_visit_keys`
- `seller_visit_keys`
- `nonparticipating_visit_keys`

`TradeWait` には次を保存する。

- `tvt_decision_timestep`
- `node_name`
- `buyers_sorted`
- 上記 4 つの VisitKey tuple
- `buyer_seller_actual_passage_completion_notified = False`

nonparticipating は buyer・seller 完了条件へ含めない。今回、完了判定と通知処理は実装しない。

## 11. 事前不変条件

prepare で一度だけ検査する。

- `traffic_observation_records` が tuple
- `trade_scope_of_this_candidate_visits` が tuple
- 件数、順序、VisitKey が一致
- Vehicle 名が VisitKey 先頭要素と一致
- VisitKey 重複なし
- role は buyer、seller、nonparticipating のみ
- binding visit と observation の role が一致
- candidate observation status が `OBSERVED` または `UNOBSERVED_AT_HORIZON`
- buyer・seller 成立時 record との一対一対応
- buyer・seller の baseline passage と candidate passage が一致
- nonparticipating に成立時 record がない
- `OBSERVED` の status と値の組合せが整合
- `UNOBSERVED_AT_HORIZON` の status と `None` 値の組合せが整合

**role 別 status 制約（補足）:**

- buyer・seller の traffic observation は `passage_observation_status` が **`OBSERVED` であること**（selected candidate の economic required passage 完了と整合）
- buyer または seller が `UNOBSERVED_AT_HORIZON` のときは prepare で `RuntimeError`
- nonparticipating は `OBSERVED` または `UNOBSERVED_AT_HORIZON` を許容
- `passage_observation_status` が `None` のときは role を問わず拒否

登録時に保証したこれらの不変条件を、毎 timestep で再検査しない。

## 12. 全Node分の重複検査

全 Node の既存 prepare と registration proposal 作成が完了した後、commit 開始前に検査する。

**entry key:**

```text
(node_name, visit_key)
```

**transaction key:**

```text
(tvt_decision_timestep, node_name, buyers_sorted)
```

**拒否条件:**

- 今回 proposal 内で entry key が重複
- 今回 proposal 内で transaction key が重複
- 既存 registry に entry key が存在
- 既存 registry に transaction key が存在

拒否時は次のすべてを変更しない。

- rank state
- `payment_paid`
- `payment_received`
- `order_exchange_log`
- registry の entry mapping
- registry の transaction mapping
- registry 内部 dict object

## 13. replacement mapping

commit 前に既存 registry mapping をコピーする。

```text
updated_entries
= dict(registry.entries_by_node_name_and_visit_key)

updated_trades
= dict(registry.trades_by_transaction_key)
```

検査済み proposal をコピー側へ反映する。

live registry へ逐次追加しない。全 proposal 反映済みの完成した replacement mapping を prepare 結果として保持する。

## 14. commit

既存 commit 順を維持する。

1. rank state
2. `payment_paid`
3. `payment_received`
4. `order_exchange_log`
5. actual passage wait registry の 2 つの replacement mapping

registry commit は return 直前に行う。

commit 中には検索、照合、検査、再計算を行わず、完成済み dict を代入するだけとする。

selected Node が 0 件なら、空の replacement で既存 dict を置き換えない。registry の 2 つの dict object はそのまま残す。

## 15. テスト方針

`tests_order_control_tvt_mp_final_rank.py` は変更しない。`_local_result` の `traffic_observation_records=()` も維持する。

`tests_order_control_tvt_mp_atomic_apply.py` 内だけで、selected local result へ traffic observation records を差し込む。既存の `dataclasses.replace` で、selected の local result の `traffic_observation_records` だけを差し替える。呼び元は、selected を実際に apply する共通経路である。fallback と no-visit には足さない。

default fixture の trade scope にどの Vehicle がどの role で入るかは、今回の調査対象外である `tests_order_control_tvt_mp_final_consistency_validation.py` の構築に依存する。テストは Vehicle 名を固定せず、差し込んだ observation の role で検証する。

**必要な主要確認:**

- buyer、seller、nonparticipating 全件登録
- entry key と transaction key
- `TradeWait` の role 別 VisitKey tuple
- 全 entry の初期 wait status
- actual observation record が `None`
- buyer・seller は成立時 record の検査済み true VOT
- nonparticipating は candidate observation の凍結 true VOT
- nonparticipating の live `Vehicle.vot_true` を読まない
- `baseline_minus_candidate` 3 値の引継ぎ
- `OBSERVED` と `UNOBSERVED_AT_HORIZON`（registry 全体として buyer・seller は `OBSERVED`、nonparticipating は両方のいずれか。§9 補足）
- buyer・seller の `OBSERVED` 登録
- buyer・seller の `UNOBSERVED_AT_HORIZON` 拒否
- nonparticipating の `OBSERVED` 登録
- nonparticipating の `UNOBSERVED_AT_HORIZON` 登録
- fallback と `NO_VISITS_TO_CONFIRM` では非登録
- proposal 内重複拒否
- 既存 registry との重複拒否
- prepare 失敗時の rank、money、log、registry 不変
- registry 失敗時の内部 dict object 不変
- 複数 Node 途中失敗時の先行 Node 非登録
- traffic observation と trade_scope の不一致拒否
- status と値の組合せ不整合拒否
- `buyers_sorted` 型訂正後の専用テスト

## 16. 変更予定ファイル

**変更予定:**

- `uxsim/order_control_tvt_mp_actual_passage.py`
- `uxsim/order_control_tvt_mp_atomic_apply.py`
- `tests_order_control_tvt_mp_actual_passage.py`
- `tests_order_control_tvt_mp_atomic_apply.py`

**変更しない:**

- `uxsim/uxsim.py`
- candidate local calculation
- economic evaluation
- final rank
- final consistency validation
- `tests_order_control_tvt_mp_final_rank.py`
- diagnostics

## 17. 独立確認結果

Cursor 調査だけで確定せず、Terminal で次を直接確認したことを記録する。

- atomic apply の prepare と commit 境界
- commit 順
- 成立時 record の field
- buyer・seller true VOT の取得位置
- selected から traffic observation への参照経路
- traffic observation が trade scope 順で作られること
- final result が同じ public order を保存すること
- `OBSERVED` と `UNOBSERVED_AT_HORIZON` の finalize 契約
- `buyers_sorted` の正式型
- current actual passage 型の `buyers_sorted` 型不整合

独立確認の結果、**BLOCKER はなく、利用者判断事項も残っていない。** 実装項目2を上記設計で一意に実装できる。

# TVT-MP actual passage基盤 実装項目2 実装・検証結果（2026-10-02）

## 1. 実装結果

実装項目2
「atomic apply成功後のregistry一括登録」
を完全実装前設計に基づいて実装した。

変更ファイル:

- uxsim/order_control_tvt_mp_actual_passage.py
- uxsim/order_control_tvt_mp_atomic_apply.py
- tests_order_control_tvt_mp_actual_passage.py
- tests_order_control_tvt_mp_atomic_apply.py

コード差分全体:

- 4 files changed
- 1375 insertions
- 65 deletions

## 2. buyers_sorted型訂正

actual passage型のbuyers_sortedを、誤っていた

tuple[str, ...]

から、正式な次の型へ訂正した。

tuple[OrderControlTvtVisitKey, ...]

訂正対象:

- OrderControlTvtMpActualPassageObservationRecord
- OrderControlTvtMpActualPassageWaitEntry
- OrderControlTvtMpActualPassageTradeWait
- registryのtransaction key
- actual passage専用テストfixture

正式なtransaction key:

(tvt_decision_timestep, node_name, buyers_sorted)

buyers_sortedはbuyer Vehicle名のtupleではなく、buyer VisitKeyのtupleである。

## 3. prepare用内部型

atomic applyへ次の非公開prepare型を追加した。

- _PreparedActualPassageProposal
- _PreparedActualPassageRegistryReplacement

_PreparedActualPassageProposalは、1 selected Node分のWaitEntry tupleとTradeWaitを保持する。

_PreparedActualPassageRegistryReplacementは、次を保持する。

- 対象registry
- 全proposal反映済みentry replacement dict
- 全proposal反映済みtransaction replacement dict

prepare中はlive registryを変更しない。

## 4. 成立時recordの直接受渡し

_PreparedVehicleUpdateへ次を追加した。

establishment_record:
OrderControlTvtMpTradeEstablishmentLogRecord

_prepare_one_money_recordが作成した同じestablishment_record objectを、次の両方へ使用する。

- updated_order_exchange_logへappend
- _PreparedVehicleUpdate.establishment_recordへ保存

registry proposalはvehicle_update.establishment_recordを直接参照する。

更新後logの末尾から成立時recordを逆探索しない。
buyer・sellerのlive Vehicle.vot_trueをregistry proposal作成時に再読取しない。

専用テストで、次を確認した。

- prepared updateが保持するestablishment_record
- updated_order_exchange_log末尾のrecord
- commit後のVehicle.order_exchange_log内record

これらが同じobjectである。

## 5. selected Nodeのregistration proposal

selected candidateの次の経路からtraffic observationを取得する。

selected candidate economic result
→ candidate local virtual calculation result
→ traffic_observation_records

traffic observationの順序を維持して、buyer、seller、nonparticipating全件のWaitEntryとTradeWaitをprepareする。

fallbackとNO_VISITS_TO_CONFIRMではproposalを作らない。

## 6. role別true VOT正本

buyer・seller:

- 成立時recordに保存したtrue_vot_per_second
- _prepare_one_money_recordで検査済みの値
- registry proposal時にlive Vehicle.vot_trueを再読取しない

nonparticipating:

- candidate traffic observationに凍結されたtrue_vot_per_second
- live Vehicle.vot_trueを読まない

## 7. role別status制約

buyer・seller:

- OBSERVED必須
- UNOBSERVED_AT_HORIZONはRuntimeError
- NoneもRuntimeError

nonparticipating:

- OBSERVEDを許容
- UNOBSERVED_AT_HORIZONを許容
- NoneはRuntimeError

UNOBSERVED_AT_HORIZONのnonparticipatingも、actual passage待機registryへ登録する。

## 8. candidate保存値の引継ぎ

WaitEntryのbaseline_minus_candidate 3値は、candidate traffic observationの既存fieldから名前を変えてコピーする。

baseline_minus_candidate_passage_timesteps
=
predicted_time_difference_timesteps

baseline_minus_candidate_passage_seconds
=
predicted_time_difference_seconds

baseline_minus_candidate_time_value
=
predicted_signed_time_value_change

atomic applyでDELTATを読み直したり、secondsとtime valueを再計算したりしない。

## 9. 追加した不変条件

prepareで次を検査する。

- traffic_observation_recordsとtrade_scopeがtuple
- 件数、順序、VisitKey、roleが一致
- VisitKey重複なし
- vehicle_nameとVisitKey先頭要素が一致
- roleはbuyer、seller、nonparticipatingのみ
- buyer・seller成立時recordとの一対一対応
- baseline passageとcandidate passageの一致
- nonparticipatingに成立時recordがない
- role別status制約
- OBSERVEDではbaseline passageとcandidate passageがPython int
- OBSERVEDではpredicted_time_difference_timestepsが次の正式式と完全一致

predicted_time_difference_timesteps
=
baseline_passage_timestep - candidate_passage_timestep

- UNOBSERVED_AT_HORIZONではcandidate passageとpredicted 3値がNone

seconds値とtime valueの式はatomic applyで再計算しない。
DELTATを再読取しない。

## 10. 全Node一括検査とreplacement

全Node分の既存prepareとregistration proposal作成後、commit開始前に次を検査する。

- proposal内entry key重複
- proposal内transaction key重複
- 既存registryとのentry key重複
- 既存registryとのtransaction key重複

entry key:

(node_name, visit_key)

transaction key:

(tvt_decision_timestep, node_name, buyers_sorted)

既存registryの2つのdictをコピーし、全proposal反映済みreplacement dictを完成させる。

live registryへ逐次追加しない。

## 11. commit順

既存commit順を維持した。

1. rank state
2. payment_paid
3. payment_received
4. order_exchange_log
5. actual passage wait registryのreplacement dict

registry反映はreturn直前である。

commit中には検索、照合、検査、再計算を行わない。

selected Nodeが0件なら、registryの既存dict objectを置き換えない。

## 12. 失敗時のatomic性

prepareまたはregistry検査に失敗した場合、次をすべて変更しない。

- rank state
- payment_paid
- payment_received
- order_exchange_log
- registry entry mapping
- registry transaction mapping
- registry内部dict object

複数Nodeの途中で失敗しても、先行Node分だけをregistryへ登録しない。

## 13. テストと独立確認

Cursorの報告だけで確定せず、Terminalで次を独立確認した。

- prepare用内部型
- 全Node proposal集約
- replacement dict作成位置
- registry commit位置
- 成立時recordの直接受渡し
- live true VOTを再読取していないこと
- role別status制約
- baseline passageのPython int検査
- baseline minus candidateの完全一致検査
- 失敗時のruntime snapshot不変
- registry内容とdict object不変

検証結果:

- actual passage専用テストとatomic applyテスト:
  67 passed
- TVT-MP既存関連8ファイル:
  354 passed
- 上記合計:
  421 passed
- FCFS・BATCH:
  366 passed
  実行時間約5分27秒
- py_compile:
  成功
- git diff --check:
  成功

UXsim正式サンプルは、実装項目2では再実行していない。
重要実装段階または最終仕上げ項目で再実行する。

## 14. 範囲外

今回接続していないもの:

- Node.transfer
- actual passage observer
- actual observation record生成
- actual recordのVehicle.order_exchange_log追加
- evaluation end
- 未観測確定
- buyer・seller完了通知
- ex-post evaluation
- Vehicle別role評価
- nonparticipating actual外部効果計算
- 実験出力と集計

交通動作は変更していない。
既存成立時logの意味も変更していない。

## 15. 次の作業

次はactual系の実装項目3へ進む。

実装項目3の正式内容は、現在の工程計画と依存関係を再確認してから開始する。

コード実装前に、詳細設計第4巻と進捗第3巻の双方へ完全実装前設計を記録する。
