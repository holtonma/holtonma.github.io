from pathlib import Path

import pytest

from crosspost.convert import analyze, escape_dollars, rewrite, table_to_list

REPO = Path(__file__).resolve().parents[3]
POSTS = REPO / "content" / "posts"

# Table blocks counted by hand (outside fenced code) on 2026-11-27.
EXPECTED_TABLES = {
    "claude-sub-agents.md": 3,
    "Devin_Kimi_K3_and_the_RL_Flywheel.md": 1,
    "professional-home-infrastructure.md": 1,
    "self-hosting-rails-cloudflare-tunnels.md": 2,
    "suggest-watch-rag-llm.md": 1,
}


def body_of(name: str) -> str:
    raw = (POSTS / name).read_text()
    return raw.split("\n---\n", 1)[1]


@pytest.mark.parametrize("name", sorted(p.name for p in POSTS.glob("*.md")))
def test_table_counts_match_hand_count(name):
    assert len(analyze(body_of(name)).tables) == EXPECTED_TABLES.get(name, 0)


def test_tables_inside_fenced_code_are_ignored():
    body = "Intro\n\n```\n| a | b |\n| - | - |\n| 1 | 2 |\n```\n"
    assert analyze(body).tables == []


def test_list_keeps_every_header():
    body = "| A | B | C | D |\n|---|---|---|---|\n| 1 | 2 | 3 | 4 |\n| 5 | | 7 | 8 |\n"
    (table,) = analyze(body).tables
    out = table_to_list(table)
    assert out.splitlines() == [
        "- **A:** 1 · **B:** 2 · **C:** 3 · **D:** 4",
        "- **A:** 5 · **B:** — · **C:** 7 · **D:** 8",
    ]


def test_blank_header_gets_column_number():
    body = "|  | B |\n|---|---|\n| x | y |\n"
    (table,) = analyze(body).tables
    assert table_to_list(table) == "- **Column 1:** x · **B:** y"


def test_shortcode_blocks():
    a = analyze('See [this]({{< ref "other.md" >}}).\n', line_offset=10)
    assert any("line 11: Hugo shortcode" in p for p in a.problems)


def test_raw_html_blocks():
    a = analyze('<img src="/images/x.png">\n')
    assert any("raw HTML block" in p for p in a.problems)


def test_image_with_text_in_paragraph_blocks():
    a = analyze("Look ![x](/images/x.png) here.\n")
    assert any("shares its paragraph" in p for p in a.problems)


def test_image_with_italic_caption_becomes_figure():
    a = analyze("![Alt text](/images/x.png)\n*The caption*\n")
    assert a.problems == []
    (fig,) = a.figures
    assert (fig.alt, fig.caption) == ("Alt text", "The caption")


def test_dollars_escaped_outside_code_only():
    assert escape_dollars("cost $0.32 and `echo $HOME`") == "cost \\$0.32 and `echo $HOME`"


def test_rewrite_turns_caption_into_image_title_and_adds_source_link(tmp_path):
    body = '![A "quoted" alt](/images/x.png)\n*Cap with "quotes"*\n\nPrice $5.\n'
    a = analyze(body)
    md = rewrite(body, a, REPO, [], {}, {}, "https://example.com/p/")
    assert '"Cap with \\"quotes\\""' in md
    assert "Price \\$5." in md
    assert md.rstrip().endswith("*Originally published at [https://example.com/p/](https://example.com/p/).*")
