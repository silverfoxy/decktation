"""Publish JUnit failures on the Actions run page and as error annotations."""

import html
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def annotation(message):
    message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::error::{message}')


def summarize(reports):
    lines = ['## Test results', '', '| Suite | Passed | Failed | Skipped |',
             '| --- | ---: | ---: | ---: |']
    details = []
    for label, filename in reports:
        try:
            root = ET.parse(filename).getroot()
        except (OSError, ET.ParseError) as error:
            message = f'{label}: test report unavailable; check the suite or setup step ({error}).'
            annotation(message)
            lines.append(f'| {html.escape(label)} | Report unavailable | — | — |')
            continue
        cases = list(root.iter('testcase'))
        failed = skipped = 0
        for case in cases:
            problems = list(case.findall('failure')) + list(case.findall('error'))
            if problems:
                failed += 1
                name = ' / '.join(filter(None, [case.get('classname'), case.get('name')]))
                error = '\n'.join(p.text or p.get('message', '') for p in problems)
                annotation(f'{label}: {name}\n{error[:3000]}')
                details.append(f'<details><summary>{html.escape(label + ": " + name)}</summary>\n\n'
                               f'<pre>{html.escape(error[:12000])}</pre>\n\n</details>')
            elif case.find('skipped') is not None:
                skipped += 1
        lines.append(f'| {html.escape(label)} | {len(cases) - failed - skipped} | {failed} | {skipped} |')
    lines += ['', *details, '', 'Download the test evidence artifacts for full reports, browser traces, screenshots and backend logs.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    summary = summarize(arg.split('=', 1) for arg in sys.argv[1:])
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as output:
            output.write(summary)
    else:
        print(summary)
