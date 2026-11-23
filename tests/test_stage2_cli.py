"""Интеграционные сценарии со стандартным вводом как в PyCharm."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, user_input=''):
    return subprocess.run([sys.executable, str(ROOT / 'main.py'), *args],
                          input=user_input, text=True, capture_output=True, cwd=ROOT,
                          timeout=12, check=False)


def test_menu_and_quit():
    result = run(user_input='0\n')
    assert result.returncode == 0
    assert 'Выбрать логику' in result.stdout
    assert 'Завершение работы' in result.stdout


def test_classical_one_is_true_not_half():
    result = run(user_input='3\np\n1\n0\n')
    assert result.returncode == 0
    assert 'Значение истинности: 1' in result.stdout
    assert 'Значение истинности: 1/2' not in result.stdout


def test_k3_l3_same_valuation_different_results():
    script = '1\n2\n3\np -> p\n1/2\n1\n3\n3\np -> p\n0.5\n0\n'
    r = run(user_input=script)
    assert r.returncode == 0
    assert 'Выбрана логика: Клини K3' in r.stdout
    assert 'Выбрана логика: Лукасевича L3' in r.stdout
    assert 'Значение истинности: 1/2' in r.stdout
    assert 'Значение истинности: 1' in r.stdout
    assert 'Traceback' not in r.stderr


def test_invalid_classical_half_then_valid_recovery():
    r = run(user_input='3\np\n1/2\n1\n0\n')
    assert r.returncode == 0
    assert 'ОШИБКА ОЦЕНКИ' in r.stdout
    assert 'Значение истинности: 1' in r.stdout


def test_truth_table_k3_all_rows():
    r = run(user_input='1\n2\n4\np -> p\n0\n')
    assert r.returncode == 0
    assert 'Строк в таблице: 3' in r.stdout
    assert '1/2 | 1/2' in r.stdout
    assert 'Таблица завершена: 3 из 3 строк.' in r.stdout


def test_properties_distinguish_not_false():
    r = run(user_input='1\n3\n5\np & !p\n0\n')
    assert r.returncode == 0
    assert 'Выполнимость: НЕТ' in r.stdout
    assert 'Тождественная ложность: НЕТ' in r.stdout
    assert 'Контрпример общезначимости:' in r.stdout


def test_comparison_half_marks_classical_unavailable():
    r = run(user_input='6\np -> p\nда\n½\n0\n')
    assert r.returncode == 0
    assert 'неприменимо' in r.stdout
    assert 'несопоставимы' in r.stdout
    assert 'Количество различающихся оценок K3/L3: 1' in r.stdout
    assert 'Traceback' not in r.stderr


def test_comparison_with_no_valuation():
    r = run(user_input='6\np | q\nнет\n0\n')
    assert r.returncode == 0
    assert 'Значения одной оценки: не сравнивались' in r.stdout


def test_bad_formula_recovery_and_back():
    r = run(user_input='5\np ->\n4\n:back\n3\np\n:back\n0\n')
    assert r.returncode == 0
    assert 'ОШИБКА СИНТАКСИСА' in r.stdout
    assert 'Завершение работы' in r.stdout
    assert 'Traceback' not in r.stderr


def test_table_limit_blocks_before_output():
    names = ' | '.join('p' + str(i) for i in range(12))
    r = run(user_input=f'1\n2\n4\n{names}\n0\n')
    assert r.returncode == 0
    assert 'Полный анализ не проводился' in r.stdout
    assert 'Таблица завершена:' not in r.stdout


def test_table_long_output_needs_confirmation():
    r = run(user_input='1\n2\n4\np | q | r | s | t\nнет\n0\n')
    assert r.returncode == 0
    assert 'Строк в таблице: 243' in r.stdout
    assert 'Вывод таблицы отменён' in r.stdout
    assert 'Таблица завершена:' not in r.stdout


def test_nonexistent_menu_number_is_rejected_as_formula_without_crash():
    r = run(user_input='99\n0\n')
    assert r.returncode == 0
    assert 'ОШИБКА СИНТАКСИСА' in r.stdout
    assert 'Traceback' not in r.stderr


def test_cli_analyze_flag():
    r = run('--analyze', 'p -> p', '--logic', 'l3')
    assert r.returncode == 0
    assert 'Общезначимость: ДА' in r.stdout
    r2 = run('--analyze', 'p ->', '--logic', 'k3')
    assert r2.returncode == 2
    assert 'ОШИБКА' in r2.stdout


def test_eof_in_submenu_exits_gracefully():
    for script in ('1\n', '3\np\n', '5\n', '6\np\n'):
        r = run(user_input=script)
        assert r.returncode == 0
        assert 'Завершение работы' in r.stdout
        assert 'Traceback' not in r.stderr
