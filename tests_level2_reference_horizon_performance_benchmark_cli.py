# CLI and helper tests for level2_reference_horizon_performance_benchmark.py
#
# Run from the repository root:
#   python tests_level2_reference_horizon_performance_benchmark_cli.py

from __future__ import annotations

import ast
import importlib.util
import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent
_BENCH_PATH = (
    _REPO_ROOT
    / "diagnostics"
    / "order_control"
    / "level2_reference_horizon_performance_benchmark.py"
)


def _load_benchmark_module():
    spec = importlib.util.spec_from_file_location("level2_ref_bench_cli", _BENCH_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_BENCH = _load_benchmark_module()


def _fake_benchmark_result(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "level2_ref_horizon_quick_raw_timing.csv"
    semantic_path = directory / "level2_ref_horizon_quick_semantic_summary.csv"
    timing_path = directory / "level2_ref_horizon_quick_timing_summary.csv"
    for path in (raw_path, semantic_path, timing_path):
        path.write_text("csv\n", encoding="utf-8")
    return {
        "raw_path": raw_path,
        "semantic_path": semantic_path,
        "timing_path": timing_path,
    }


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = _BENCH.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def test_ast_parse():
    with open(_BENCH_PATH, encoding="utf-8") as handle:
        ast.parse(handle.read(), filename=str(_BENCH_PATH))


def test_quick_and_full_together_exit_2():
    code, _, stderr = _run_main(["--quick", "--full"])
    assert code == 2
    assert "cannot be used together" in stderr


def test_invalid_horizons_exit_2():
    code, _, stderr = _run_main(["--quick", "--horizons", "0,abc"])
    assert code == 2
    assert "invalid --horizons" in stderr


def test_empty_horizons_exit_2():
    code, _, stderr = _run_main(["--quick", "--horizons", ","])
    assert code == 2
    assert "invalid --horizons" in stderr or "must not be empty" in stderr


def test_negative_horizon_exit_2():
    code, _, stderr = _run_main(["--quick", "--horizons", "0,-1"])
    assert code == 2
    assert "must be >= 0" in stderr


def test_repeats_zero_exit_2():
    code, _, stderr = _run_main(["--quick", "--repeats", "0"])
    assert code == 2
    assert "--repeats must be >= 1" in stderr


def test_negative_reference_horizon_exit_2():
    code, _, stderr = _run_main(["--quick", "--reference-horizon", "-1"])
    assert code == 2
    assert "--reference-horizon must be >= 0" in stderr


def test_copy_benchmark_csv_same_file_no_error():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "same.csv"
        path.write_text("payload", encoding="utf-8")
        _BENCH._copy_benchmark_csv(path, path)
        assert path.read_text(encoding="utf-8") == "payload"


def test_copy_benchmark_csv_same_file_via_resolve():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "data.csv"
        source.write_text("payload", encoding="utf-8")
        destination = Path(str(source))
        _BENCH._copy_benchmark_csv(source, destination)


def test_copy_benchmark_csv_copies_to_different_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.csv"
        destination = root / "nested" / "dest.csv"
        source.write_text("payload", encoding="utf-8")
        _BENCH._copy_benchmark_csv(source, destination)
        assert destination.read_text(encoding="utf-8") == "payload"


def test_copy_benchmark_csv_creates_parent_directory():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.csv"
        destination = root / "a" / "b" / "dest.csv"
        source.write_text("payload", encoding="utf-8")
        assert not destination.parent.exists()
        _BENCH._copy_benchmark_csv(source, destination)
        assert destination.parent.is_dir()
        assert destination.is_file()


def test_main_prints_output_directory_with_explicit_output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "explicit"
        fake_result = _fake_benchmark_result(output_dir)
        with mock.patch.object(_BENCH, "_run_benchmark", return_value=fake_result):
            code, stdout, _ = _run_main(
                [
                    "--quick",
                    "--repeats",
                    "1",
                    "--horizons",
                    "0",
                    "--output-dir",
                    str(output_dir),
                ]
            )
        assert code == 0
        assert stdout.splitlines()[-1] == f"Benchmark output directory: {output_dir}"


def test_main_prints_output_directory_with_default_temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "generated"
        fake_result = _fake_benchmark_result(output_dir)
        with mock.patch.object(_BENCH, "_run_benchmark", return_value=fake_result):
            code, stdout, _ = _run_main(
                ["--quick", "--repeats", "1", "--horizons", "0"]
            )
        assert code == 0
        lines = [
            line
            for line in stdout.splitlines()
            if line.startswith("Benchmark output directory: ")
        ]
        assert len(lines) == 1
        reported = Path(lines[0].split(": ", 1)[1])
        assert reported.is_dir()


def test_main_copies_custom_csv_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        output_dir = root / "default"
        custom_raw = root / "custom" / "raw.csv"
        custom_semantic = root / "custom" / "semantic.csv"
        custom_timing = root / "custom" / "timing.csv"
        fake_result = _fake_benchmark_result(output_dir)
        with mock.patch.object(_BENCH, "_run_benchmark", return_value=fake_result):
            code, _, _ = _run_main(
                [
                    "--quick",
                    "--repeats",
                    "1",
                    "--horizons",
                    "0",
                    "--output-dir",
                    str(output_dir),
                    "--raw-csv",
                    str(custom_raw),
                    "--semantic-csv",
                    str(custom_semantic),
                    "--timing-summary-csv",
                    str(custom_timing),
                ]
            )
        assert code == 0
        assert custom_raw.read_text(encoding="utf-8") == "csv\n"
        assert custom_semantic.read_text(encoding="utf-8") == "csv\n"
        assert custom_timing.read_text(encoding="utf-8") == "csv\n"


def test_main_raw_csv_same_path_as_source_no_error():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "default"
        fake_result = _fake_benchmark_result(output_dir)
        same_raw = fake_result["raw_path"]
        with mock.patch.object(_BENCH, "_run_benchmark", return_value=fake_result):
            code, _, _ = _run_main(
                [
                    "--quick",
                    "--repeats",
                    "1",
                    "--horizons",
                    "0",
                    "--output-dir",
                    str(output_dir),
                    "--raw-csv",
                    str(same_raw),
                ]
            )
        assert code == 0
        assert same_raw.read_text(encoding="utf-8") == "csv\n"


def main() -> None:
    tests = [
        test_ast_parse,
        test_quick_and_full_together_exit_2,
        test_invalid_horizons_exit_2,
        test_empty_horizons_exit_2,
        test_negative_horizon_exit_2,
        test_repeats_zero_exit_2,
        test_negative_reference_horizon_exit_2,
        test_copy_benchmark_csv_same_file_no_error,
        test_copy_benchmark_csv_same_file_via_resolve,
        test_copy_benchmark_csv_copies_to_different_path,
        test_copy_benchmark_csv_creates_parent_directory,
        test_main_prints_output_directory_with_explicit_output_dir,
        test_main_prints_output_directory_with_default_temp_dir,
        test_main_copies_custom_csv_paths,
        test_main_raw_csv_same_path_as_source_no_error,
    ]
    for test in tests:
        test()
    print(f"All {len(tests)} benchmark CLI tests passed.")


if __name__ == "__main__":
    main()
