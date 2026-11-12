import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    'test_summary', Path(__file__).resolve().parents[1] / 'scripts/summarize_test_results.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def test_summary_counts_failures_and_escapes_untrusted_output(tmp_path, capsys):
    report = tmp_path / 'results.xml'
    report.write_text('''<testsuites><testsuite><testcase name="pass"/>
      <testcase classname="catalog" name="coverage"><failure>missing &lt;key&gt;\n::warning::fake</failure></testcase>
      <testcase name="skip"><skipped/></testcase>
      <testcase name="error"><error message="setup failed"/></testcase>
      </testsuite></testsuites>''')
    result = summary.summarize([('Frontend', report)])
    assert '| Frontend | 1 | 2 | 1 |' in result
    assert 'catalog / coverage' in result
    assert 'missing &lt;key&gt;' in result
    assert 'setup failed' in result
    annotations = capsys.readouterr().out
    assert '::error::Frontend: catalog / coverage' in annotations
    assert '%0A::warning::fake' in annotations
    assert '\n::warning::fake' not in annotations


def test_summary_explains_missing_or_invalid_reports(tmp_path, capsys):
    bad = tmp_path / 'bad.xml'
    bad.write_text('incomplete')
    result = summary.summarize([('Python', tmp_path / 'missing.xml'), ('Browser', bad)])
    assert result.count('Report unavailable') == 2
    assert capsys.readouterr().out.count('::error::') == 2
