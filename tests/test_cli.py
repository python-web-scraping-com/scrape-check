import json

import httpx
import respx
from click.testing import CliRunner

from scrape_check.cli import main

_SSR_BODY = (
    "<!doctype html><html><head><title>Plain HTML Page Title Here</title></head><body>"
    + "<p>Real article content that is server rendered.</p>" * 20
    + "</body></html>"
)


def _mock_clean(host: str):
    respx.get(f"https://{host}/robots.txt").mock(return_value=httpx.Response(404))
    respx.get(f"https://{host}/").mock(return_value=httpx.Response(200, html=_SSR_BODY))


@respx.mock
def test_single_url_exit_zero_for_clean_site():
    _mock_clean("example.com")
    result = CliRunner().invoke(main, ["https://example.com/"])
    assert result.exit_code == 0
    assert "Recommendation" in result.output


@respx.mock
def test_single_url_json_output():
    _mock_clean("example.com")
    result = CliRunner().invoke(main, ["https://example.com/", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["target"] == "https://example.com/"
    assert payload["recommendation"]["strategy"] == "requests"


def test_no_url_and_no_batch_is_usage_error():
    result = CliRunner().invoke(main, [])
    assert result.exit_code != 0
    assert "Provide a URL" in result.output


@respx.mock
def test_user_agent_flag_is_forwarded():
    route = respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, html=_SSR_BODY)
    )
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))

    result = CliRunner().invoke(main, ["https://example.com/", "-u", "MyBot/1.0", "--json"])
    assert result.exit_code == 0
    assert route.calls.last.request.headers["user-agent"] == "MyBot/1.0"


@respx.mock
def test_batch_file_json_array():
    _mock_clean("a.com")
    _mock_clean("b.com")

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("urls.txt", "w") as fh:
            fh.write("https://a.com/\n# comment\n\nhttps://b.com/\n")
        result = runner.invoke(main, ["--batch", "urls.txt", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert {p["target"] for p in payload} == {"https://a.com/", "https://b.com/"}


@respx.mock
def test_batch_from_stdin_dash():
    _mock_clean("a.com")
    _mock_clean("b.com")

    result = CliRunner().invoke(main, ["-", "--json"], input="https://a.com/\nhttps://b.com/\n")
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 2


@respx.mock
def test_batch_exit_code_is_worst():
    _mock_clean("a.com")
    # b.com is client-rendered -> headless -> exit 1
    respx.get("https://b.com/robots.txt").mock(return_value=httpx.Response(404))
    csr_body = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Single Page Application Shell With A Realistic Length Title</title>"
        "</head><body><div id='root'></div>"
        "<script src='/static/react.bundle.js'></script>"
        "<script src='/static/app.bundle.js'></script></body></html>"
    )
    respx.get("https://b.com/").mock(return_value=httpx.Response(200, html=csr_body))

    result = CliRunner().invoke(main, ["--batch", "-", "--json"], input="https://a.com/\nhttps://b.com/\n")
    assert result.exit_code == 1


def test_batch_empty_input_is_usage_error():
    result = CliRunner().invoke(main, ["--batch", "-"], input="\n# only comments\n")
    assert result.exit_code != 0
    assert "no URLs found" in result.output


@respx.mock
def test_batch_summary_table_rendered():
    _mock_clean("a.com")
    result = CliRunner().invoke(main, ["--batch", "-"], input="https://a.com/\n")
    assert result.exit_code == 0
    assert "batch summary" in result.output
