import httpx
import respx

from scrape_check.checks import robots
from scrape_check.fetch import make_client


@respx.mock
def test_parses_allow_disallow_and_sitemaps():
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(
            200,
            text=(
                "User-agent: *\n"
                "Disallow: /private/\n"
                "Crawl-delay: 5\n"
                "Sitemap: https://example.com/sitemap.xml\n"
            ),
        )
    )
    with make_client() as client:
        info = robots.check(client, "https://example.com/private/page")
        assert info.fetched is True
        assert info.allowed is False
        assert info.crawl_delay == 5.0
        assert "https://example.com/sitemap.xml" in info.sitemaps

        info2 = robots.check(client, "https://example.com/public/page")
        assert info2.allowed is True


@respx.mock
def test_missing_robots_means_allowed():
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    with make_client() as client:
        info = robots.check(client, "https://example.com/anything")
        assert info.fetched is True
        assert info.allowed is True
        assert info.status == 404


def test_invalid_url_returns_error():
    with make_client() as client:
        info = robots.check(client, "not-a-url")
        assert info.fetched is False
        assert info.error == "invalid URL"
