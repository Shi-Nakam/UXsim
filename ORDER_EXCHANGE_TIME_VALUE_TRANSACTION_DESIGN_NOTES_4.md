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
