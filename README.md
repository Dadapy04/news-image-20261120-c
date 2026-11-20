# THE WORLD IN ONE IMAGE — 20 November 2026

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/Dadapy04/news-image-20261120-c/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/Dadapy04/news-image-20261120-c/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

## Concept

A front page compresses a day into a hierarchy, and this renderer makes that
hierarchy literal. The top of the sheet carries the heaviest news of Friday,
20 November 2026: a night of Russian drone and missile strikes on Ukraine, at
least eight dead, and missiles that briefly crossed into Polish airspace and
sent Polish and allied aircraft into the sky. Below it, a proportional band
turns editorial weight into geometry — each story's share of the day becomes
its share of the printed rule, so the summit, the ceasefire talks, the Senate
vote and the European wage marches are readable as proportions before a single
word is read. The remaining stories run as a numbered list, and a wire strip
closes the sheet with three one-liners.

Everything is rendered from scratch. There is no imaging library, no font
file, no network call and no clock. The canvas is a plain RGB byte buffer, the
typeface is a 5x7 bitmap table written into the source, and the encoder builds
IHDR, IDAT and IEND chunks by hand with `zlib` and `struct`. The same fixture
always produces the same pixels, so the artefact can be checked as well as
looked at.

## Run it

```
python3 main.py            # writes out/2026-11-20.png
python3 main.py --check    # renders twice, asserts identical bytes
python3 main.py --stats    # story count, total weight, rendered height
```

Standard library only. Python 3.8 or newer is enough.

## Layout

```
main.py            the renderer: canvas, bitmap font, wrapping, PNG encoder, CLI
news.json          the fixture: edition, issue, dateline, 5 stories, 3 wire items
out/2026-11-20.png the rendered broadsheet (1600 px wide, height cropped to ink)
README.md          this file
LICENSE            MIT
.makefun/owner.json  bounty wallet metadata
```

## License

MIT. Copyright 2026 Dadapy04. See [LICENSE](LICENSE).
