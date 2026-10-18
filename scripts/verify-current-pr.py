#!/usr/bin/env python3
"""Verify a PR build against GitHub's live PR state without executing it."""
import argparse
import json
import os
import re
import sys
from urllib.request import Request, urlopen
import zipfile


def current_pr(repository, number, sha, head_repository):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid base repository')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', head_repository):
        raise ValueError('Invalid head repository')
    if number <= 0 or not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Invalid PR identity')
    request = Request(f'https://api.github.com/repos/{repository}/pulls/{number}',
                      headers={'Accept': 'application/vnd.github+json',
                               'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}',
                               'User-Agent': 'decktation-pr-publisher'})
    with urlopen(request, timeout=30) as response:
        pr = json.load(response)
    return (pr.get('state') == 'open' and pr.get('head', {}).get('sha') == sha and
            (pr.get('head', {}).get('repo') or {}).get('full_name') == head_repository)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--head-repository', required=True)
    parser.add_argument('--number', type=int)
    parser.add_argument('--artifact')
    parser.add_argument('--output')
    args = parser.parse_args()
    number = args.number
    if args.artifact:
        with zipfile.ZipFile(args.artifact) as archive:
            manifest = archive.getinfo('decktation/plugin.json')
            if manifest.file_size > 32768:
                raise ValueError('Plugin manifest exceeds limit')
            plugin = json.loads(archive.read(manifest))
        match = re.fullmatch(r'\d+\.\d+\.\d+-dev\.pr-([1-9]\d*)\.([0-9a-f]{7})', plugin['version'])
        if not match or match.group(2) != args.sha[:7]:
            raise ValueError('Artifact does not identify its PR and commit')
        number = int(match.group(1))
    if number is None or not current_pr(args.repository, number, args.sha, args.head_repository):
        raise ValueError('PR closed, moved, or not associated with this build')
    if args.output:
        with open(args.output, 'a', encoding='utf-8') as destination:
            destination.write(f'number={number}\nhead_repository={args.head_repository}\n')
    else:
        print(number)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
