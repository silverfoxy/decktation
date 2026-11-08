#!/usr/bin/env python3
"""Announce a published stable release using its tagged changelog notes."""
import argparse
import base64
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

MARKER = re.compile(r'<!-- decktation-discord-message:(\d+) -->')


class AnnouncementError(Exception):
    pass


def github(method, path, data=None):
    request = Request('https://api.github.com/' + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      method=method, headers={
                          'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                          'Accept': 'application/vnd.github+json',
                          'Content-Type': 'application/json',
                          'User-Agent': 'Decktation-release-announcements',
                      })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def release_notes(changelog, tag):
    version = re.escape(tag.removeprefix('v'))
    match = re.search(r'^## \[' + version + r'\][^\n]*\n(.*?)(?=^## \[|\Z)',
                      changelog, re.M | re.S)
    if not match:
        raise AnnouncementError('No changelog section found for the release tag.')
    return re.sub(r'^\[[^\]]+\]:[^\n]*$', '', match[1], flags=re.M).strip()


def payload(tag, notes, release_url, download_url):
    # Discord allows a 4096-character embed description. Count UTF-16 units too,
    # since an emoji may occupy two units on the receiving side.
    suffix = '\n\n[Read all release notes](https://decktation.com/changelog/' + tag[1:] + '/)'
    notes = notes.encode('utf-16-le')[:(4096 - len(suffix)) * 2].decode('utf-16-le', errors='ignore')
    return {
        'username': 'Decktation releases',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': 'Decktation ' + tag + ' is available', 'url': release_url,
            'description': notes.rstrip() + suffix, 'color': 0x246BFD,
            'fields': [
                {'name': 'Install or update', 'value': '[Download Decktation.zip](' + download_url + ')'},
                {'name': 'Learn the features', 'value': '[Animated walkthrough](https://decktation.com/walkthrough/)'},
            ],
        }],
    }


def send(webhook, message):
    url = urlsplit(webhook)
    if (url.scheme != 'https' or url.netloc not in {'discord.com', 'discordapp.com'}
            or not re.fullmatch(r'/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_.-]+', url.path)):
        raise AnnouncementError('The configured Discord webhook URL is invalid.')
    query = dict(parse_qsl(url.query))
    query['wait'] = 'true'
    target = urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ''))
    request = Request(target, data=json.dumps(message).encode(), method='POST', headers={
        'Content-Type': 'application/json', 'User-Agent': 'Decktation-release-announcements',
    })
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    message_id = str(result.get('id', ''))
    if not message_id.isdigit():
        raise AnnouncementError('Discord did not confirm a saved message.')
    return message_id


def announce(repo, tag, previous_id=''):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise AnnouncementError('Invalid repository name.')
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise AnnouncementError('Only stable vX.Y.Z releases can be announced.')
    release = github('GET', f'repos/{repo}/releases/tags/{tag}')
    if release.get('draft') or release.get('prerelease'):
        raise AnnouncementError('Draft and prerelease announcements are disabled.')
    asset = next((asset for asset in release.get('assets', [])
                  if asset.get('name') == 'Decktation.zip' and asset.get('state') == 'uploaded'
                  and asset.get('size', 0) > 0), None)
    if not asset:
        raise AnnouncementError('The installable release archive is not available yet.')
    body = release.get('body') or ''
    existing = MARKER.search(body)
    message_id = existing[1] if existing else previous_id
    if message_id and not message_id.isdigit():
        raise AnnouncementError('Invalid previous Discord message identifier.')
    if not message_id:
        webhook = os.environ.get('DISCORD_RELEASE_WEBHOOK_URL', '')
        if not webhook:
            print('::warning::DISCORD_RELEASE_WEBHOOK_URL is not configured; announcement skipped.')
            return None
        content = github('GET', f'repos/{repo}/contents/CHANGELOG.md?ref={tag}')
        notes = release_notes(base64.b64decode(content['content']).decode(), tag)
        message = payload(tag, notes, release['html_url'], asset['browser_download_url'])
        message_id = send(webhook, message)
        print('Discord confirmed release announcement message ' + message_id + '.')
    else:
        print('Release already announced; no duplicate message sent.')
    if not existing:
        github('PATCH', f'repos/{repo}/releases/{release["id"]}', {
            'body': body.rstrip() + '\n\n<!-- decktation-discord-message:' + message_id + ' -->',
        })
    return message_id


def capture(repo, tag):
    """Preserve a prior message ID before the release uploader replaces its body."""
    try:
        release = github('GET', f'repos/{repo}/releases/tags/{tag}')
    except HTTPError as error:
        if error.code == 404:
            return ''
        raise
    match = MARKER.search(release.get('body') or '')
    return match[1] if match else ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['announce', 'capture'], nargs='?', default='announce')
    args = parser.parse_args()
    repo = os.environ['GITHUB_REPOSITORY']
    tag = os.environ['RELEASE_TAG']
    try:
        if args.action == 'capture':
            message_id = capture(repo, tag)
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('message_id=' + message_id + '\n')
        else:
            announce(repo, tag, os.environ.get('PREVIOUS_DISCORD_MESSAGE_ID', ''))
    except HTTPError as error:
        # Never print an exception URL or response body: webhook URLs are secrets.
        print(f'::error::Release announcement request failed (HTTP {error.code}).', file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError, ValueError, KeyError, AnnouncementError):
        print('::error::Release announcement failed. Check the webhook secret, release assets, and changelog.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
