src = open('test_reports.py', encoding='utf-8').read()
if 'schema' not in src:
    src = src.replace('def main()', 'import schema\n\n\ndef main()', 1)
    # add validate call just before the final print
    src = src.replace(
        'print(f"test_reports OK")',
        'errs = schema.validate(json.load(open(os.path.join(D, "eval_report.json"), encoding="utf-8")),\n                       schema.SCHEMAS["eval_report.json"])\n    assert not errs, errs\n    print(f"test_reports OK")'
    )
    open('test_reports.py', 'w', encoding='utf-8').write(src)
    print('T20 integrated')

src2 = open('mypy.ini', encoding='utf-8').read()
if 'spear_fable.py' not in src2:
    src2 = src2.replace('files = intuition.py', 'files = intuition.py, spear_fable.py')
    open('mypy.ini', 'w', encoding='utf-8').write(src2)
    print('mypy.ini updated')
