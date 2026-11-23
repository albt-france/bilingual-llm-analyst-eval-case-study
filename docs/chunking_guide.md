# Chunking a long text into logical blocks

A block is a part of the text that answers one question and can be read on its own. Good blocks make summaries,
fact checks and retrieval easier: each claim can be traced to one block.

## Rules

1. **Start from the author's structure.** The lead plus each top-level section is one block; sub-sections stay
   inside their parent unless the parent is longer than about 800 words.
2. **Drop non-content blocks**: See also, References, External links, Further reading (French: Voir aussi, Notes et
   références, Liens externes, Annexes).
3. **Give each block a title that says what it answers**, not only the section name ("How Eurostat came to exist"
   rather than "History").
4. **Every sentence belongs to exactly one block**; no overlap, no gap.
5. **Record the size** (words) so a reviewer sees an unbalanced split at once.
6. **Cite the revision** (Wikipedia `oldid`), since articles change.

## Worked example: "Eurostat" (English Wikipedia, revision 1356128040, CC BY-SA 4.0)

| # | Block (section) | Words | Title that says what it answers |
|---|---|---|---|
| 1 | Lead | 88 | What Eurostat is and what it does |
| 2 | Name | 140 | Where the name comes from |
| 3 | History | 1,336 | How the office developed (long: candidate for a split by period) |
| 4 | Operations | 655 | How it produces and harmonises statistics |
| 5 | Access to Eurostat statistics | 217 | How to get the data |
| 6 | Locations | 260 | Where it is based |

Left out: See also, References, External links. Sizes are computed by `src/build_series_tasks.py` (`sections()`).

**Typical slips** (simulated model): dropping the last content block (MISSED_BLOCK), splitting on every
sub-heading (too many tiny blocks), or merging the lead into the first section.

## Version française

Même méthode pour l'article « Institut national de la statistique et des études économiques » (révision 241378467) :
introduction + 15 sections de contenu, « Notes et références » et « Annexes » exclues. Les titres de blocs sont
rédigés en français (« Comment l'Insee est organisé » plutôt que « Organisation »).
