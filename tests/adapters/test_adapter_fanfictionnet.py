from unittest.mock import patch

import pytest

from fanficfare.adapters.adapter_fanfictionnet import FanFictionNetSiteAdapter
from fanficfare.configurable import Configuration
from fanficfare.exceptions import FailedToDownload

NOT_FOUND = """<html><body><span class='gui_warning'>FanFiction.Net Message Type 1<hr size=1 noshade>
Chapter not found. Please check to see you are not using an outdated url.</span></body></html>"""

STORY = """<html><head>
<link rel="canonical" href="//www.fanfiction.net/s/123/1/Test-Story">
</head><body>
<div id=content_wrapper_inner>
<div id=pre_story_links><a class=xcontrast_txt href="/book/">Books</a> <a class=xcontrast_txt href="/book/Test/">Test Fandom</a></div>
<div id=profile_top>
<b class='xcontrast_txt'>Test Story</b>
By:<a class='xcontrast_txt' href='/u/456/Author'>Author</a>
<div style='margin-top:2px' class='xcontrast_txt'>A summary.</div>
<span class='xgray xcontrast_txt'><a href='https://www.fictionratings.com/' target='rating'>Fiction  T</a> - English - Adventure - Harry P. - Chapters: 2 - Words: 1,000 - Reviews: 3 - Favs: 4 - Follows: 5 - Updated: <span data-xutime='1700000000'>Nov 14</span> - Published: <span data-xutime='1600000000'>Sep 13</span> - id: 123 </span>
</div>
<select id=chap_select name=chapter><option value=1 selected>1. One</option><option value=2>2. Two</option></select>
<div role='main' class='storytextp' id='storytextp'><div class='storytext xcontrast_txt nocopy' id='storytext'><p>Chapter text.</p></div></div>
</div></body></html>"""

ADAPTER_PATH = 'fanficfare.adapters.adapter_fanfictionnet.FanFictionNetSiteAdapter'


def make_adapter(url='https://www.fanfiction.net/s/123/1/Test-Story'):
    config = Configuration(["www.fanfiction.net"], "EPUB", lightweight=True)
    return FanFictionNetSiteAdapter(config, url)


def responder(pages):
    def get_request(url, usecache=True):
        return pages.get(url, NOT_FOUND)
    return get_request


def test_url_variants_chapter_one_include_story_url():
    adapter = make_adapter()
    assert adapter._chapter_url_variants('https://www.fanfiction.net/s/123/1/Test-Story') == [
        'https://www.fanfiction.net/s/123/1/Test-Story',
        'https://www.fanfiction.net/s/123/1/',
        'https://www.fanfiction.net/s/123/1',
        'https://www.fanfiction.net/s/123/',
        'https://www.fanfiction.net/s/123',
    ]


def test_url_variants_later_chapter():
    adapter = make_adapter()
    assert adapter._chapter_url_variants('https://www.fanfiction.net/s/123/5/') == [
        'https://www.fanfiction.net/s/123/5/',
        'https://www.fanfiction.net/s/123/5',
    ]


def test_chapter_text_falls_back_to_bare_story_url():
    adapter = make_adapter()
    pages = {'https://www.fanfiction.net/s/123/': STORY}
    with patch(ADAPTER_PATH + '.get_request', side_effect=responder(pages)) as get_request:
        text = adapter.getChapterText('https://www.fanfiction.net/s/123/1/Test-Story')
    assert 'Chapter text.' in text
    assert get_request.call_count == 4


def test_chapter_text_no_fallback_when_found():
    adapter = make_adapter()
    pages = {'https://www.fanfiction.net/s/123/2/Test-Story': STORY}
    with patch(ADAPTER_PATH + '.get_request', side_effect=responder(pages)) as get_request:
        adapter.getChapterText('https://www.fanfiction.net/s/123/2/Test-Story')
    assert get_request.call_count == 1


def test_metadata_falls_back_to_story_url():
    adapter = make_adapter()
    pages = {'https://www.fanfiction.net/s/123': STORY}
    with patch(ADAPTER_PATH + '.get_request', side_effect=responder(pages)), \
         patch(ADAPTER_PATH + '.setCoverImage'):
        adapter.doExtractChapterUrlsAndMetadata()
    assert adapter.story.getMetadata('title') == 'Test Story'
    assert adapter.story.getMetadata('author') == 'Author'
    assert adapter.num_chapters() == 2


def test_metadata_still_fails_when_all_variants_not_found():
    adapter = make_adapter()
    with patch(ADAPTER_PATH + '.get_request', side_effect=responder({})) as get_request:
        with pytest.raises(FailedToDownload):
            adapter.doExtractChapterUrlsAndMetadata()
    assert get_request.call_count == 5
