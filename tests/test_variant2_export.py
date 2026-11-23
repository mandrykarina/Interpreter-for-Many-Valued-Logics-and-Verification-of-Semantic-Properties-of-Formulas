"""Проверка файлов для отчёта и интерактивных сценариев третьего этапа."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from logic import LogicSystem
from variants.export import export_variant2

ROOT = Path(__file__).resolve().parents[1]


def run(*args, user_input=''):
    return subprocess.run([sys.executable, str(ROOT / 'main.py'), *args],
                          input=user_input, text=True, capture_output=True, cwd=ROOT,
                          timeout=18, check=False)


def test_generate_all_20_report_files(tmp_path):
    files = export_variant2(tmp_path)
    assert len(files) == 20
    assert len(list(tmp_path.glob('F*_truth_table.csv'))) == 15
    assert all(path.is_file() and path.stat().st_size > 0 for path in files)
    data = json.loads((tmp_path / 'variant2_results.json').read_text(encoding='utf-8'))
    assert len(data['formulae']) == 5
    assert len(data['relations']) == 4
    assert data['relations']['R2']['logics']['l3']['counterexample']['conclusion_value'] == '1/2'
    assert data['relations']['R3']['logics']['k3']['counterexample']['conclusion_value'] == '1/2'
    assert data['relations']['R4']['logics']['classical']['counterexample']['conclusion_value'] == '0'
    assert data['formulae']['F4']['logics']['k3']['identically_false'] is False
    assert data['formulae']['F4']['logics']['k3']['satisfiable'] is False
    for name in ('F1', 'F2', 'F3', 'F4', 'F5'):
        for system in LogicSystem:
            with (tmp_path / f'{name}_{system.value}_truth_table.csv').open(
                    encoding='utf-8-sig', newline='') as file:
                rows = list(csv.reader(file, delimiter=';'))
            assert len(rows) == len(system.values) ** (len(rows[0]) - 1) + 1
            assert all(len(row) == len(rows[0]) for row in rows)
            assert all(value in ('0', '1/2', '1') for row in rows[1:] for value in row)
    report = (tmp_path / 'variant2_report_results.md').read_text(encoding='utf-8')
    assert '# Лабораторная №2' in report and '### R4' in report
    assert 'p=1, q=0, r=1, s=1, t=1' in report


def test_cli_entails_valid_with_premises():
    result = run('--logic', 'k3', '--premise', 'p', '--premise', 'p -> q', '--entails', 'q')
    assert result.returncode == 0, result.stderr
    assert 'СЛЕДУЕТ' in result.stdout
    assert 'Совместных моделей посылок' in result.stdout


def test_cli_entails_empty_premises():
    r = run('--logic', 'k3', '--entails', 'p -> p')
    assert r.returncode == 0
    assert 'НЕ СЛЕДУЕТ' in r.stdout
    assert '(пустой набор)' in r.stdout
    assert '1/2' in r.stdout


def test_cli_entails_vacuous():
    r = run('--premise', 'p & !p', '--entails', 'q')
    assert r.returncode == 0
    assert 'вакуумно' in r.stdout
    assert 'СЛЕДУЕТ' in r.stdout


def test_cli_entails_invalid_syntax():
    r = run('--premise', 'p ->', '--entails', 'q')
    assert r.returncode == 2
    assert 'ОШИБКА' in r.stdout
    assert 'Traceback' not in r.stderr


def test_cli_premise_without_entails_is_usage_error():
    r = run('--premise', 'p')
    assert r.returncode == 2
    assert '--premise требует --entails' in r.stderr


def test_cli_variant_summary_reference():
    r = run('--variant2')
    assert r.returncode == 0
    assert 'R2' in r.stdout and 'НЕ СЛЕДУЕТ' in r.stdout
    assert 'F5' in r.stdout and 'общезначима=ДА' in r.stdout


def test_cli_export(tmp_path):
    r = run('--export-results', str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert '20 файлов' in r.stdout
    assert (tmp_path / 'F5_l3_truth_table.csv').exists()


def test_interactive_manual_entailment_0_premises():
    r = run(user_input='8\n\np -> p\n0\n')
    assert r.returncode == 0, r.stderr
    assert '(пустой набор)' in r.stdout
    assert 'СЛЕДУЕТ' in r.stdout
    assert 'Завершение работы' in r.stdout


def test_interactive_manual_invalid_premise_and_conclusion_recovery():
    r = run(user_input='8\np ->\np\n\nq ->\nq\n0\n')
    assert r.returncode == 0, r.stderr
    assert r.stdout.count('ОШИБКА СИНТАКСИСА') == 2
    assert 'НЕ СЛЕДУЕТ' in r.stdout
    assert 'Traceback' not in r.stderr


def test_interactive_manual_back_cancel():
    r = run(user_input='8\n:back\n8\n\n:back\n0\n')
    assert r.returncode == 0 and 'Завершение работы' in r.stdout


def test_interactive_variant_formula_and_truth_table():
    r = run(user_input='1\n3\n9\n1\nF4\nда\n0\n0\n')
    assert r.returncode == 0, r.stderr
    assert 'Тождественная ложность: НЕТ' in r.stdout
    assert '1/2 | 1/2' in r.stdout
    assert 'F4' in r.stdout


def test_interactive_variant_relation():
    r = run(user_input='1\n3\n9\n2\nR2\n0\n0\n')
    assert r.returncode == 0, r.stderr
    assert 'НЕ СЛЕДУЕТ' in r.stdout
    assert 'A5 = 1' in r.stdout
    assert 'Заключение = 1/2' in r.stdout


def test_interactive_variant_unknown_selection_recovers():
    r = run(user_input='9\n1\nF99\n2\nR99\n0\n0\n')
    assert r.returncode == 0
    assert 'Неизвестная формула' in r.stdout
    assert 'Неизвестное отношение' in r.stdout


def test_interactive_return_from_variant_to_original_menu():
    r = run(user_input='9\n0\n2\np -> q -> r\n0\n')
    assert r.returncode == 0
    assert 'ПРИНЯТО' in r.stdout
    assert '((p → q) → r)' in r.stdout
