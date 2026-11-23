import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, input_text=None):
    return subprocess.run([sys.executable, str(ROOT / "main.py"), *args],
                          input=input_text, text=True, capture_output=True, cwd=ROOT,
                          timeout=10, check=False)


def test_cli_formula_mode():
    result = run("--formula", "p -> q -> r")
    assert result.returncode == 0
    assert "ПРИНЯТО" in result.stdout
    assert "((p → q) → r)" in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_malformed_formula_mode_has_nonzero_exit():
    result = run("--formula", "p ->")
    assert result.returncode == 2
    assert "ОШИБКА СИНТАКСИСА" in result.stdout
    assert "Traceback" not in result.stderr


def test_interactive_mode_recovers_after_error():
    result = run(input_text="p ->\np -> q -> (q -> q)\n:exit\n")
    assert result.returncode == 0
    assert "ОШИБКА СИНТАКСИСА" in result.stdout
    assert "ПРИНЯТО" in result.stdout
    assert "((p → q) → (q → q))" in result.stdout
    assert "Завершение работы" in result.stdout


def test_exit_is_a_variable_not_a_command():
    result = run(input_text="exit\n:help\n:exit\n")
    assert result.returncode == 0
    assert "Переменные: exit" in result.stdout
    assert "Приоритеты" in result.stdout


def test_eof_exit():
    result = run(input_text="")
    assert result.returncode == 0
    assert "Завершение работы" in result.stdout
