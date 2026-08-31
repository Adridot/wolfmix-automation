# The SSL2 fixture-profile format

An `.ssl2` file is one XML document under one stream cipher. It describes a
fixture: its brand and name, a physical block, and one or more DMX modes, each
a list of typed channels, each channel a list of presets over DMX ranges.

`tools/ssl2.py` reads them, writes them, and generates new ones.
[`LEGAL.md`](../LEGAL.md) says why reading this format is in scope here and the
four conditions that keep it there. **No file from the vendor's library — nor
any XML decrypted from one — belongs in this repository**, and `.gitignore`
refuses both.

```bash
python3 tools/ssl2.py dump fixture.ssl2 | xmllint --format -   # look
python3 tools/ssl2.py gen my-par.json my-par.ssl2              # build
python3 tools/ssl2.py verify                                   # prove the codec
SSL2_LIBRARY=/Applications/EasyViewConnect/ScanLibrary python3 tools/ssl2.py verify
python3 tools/ssl2.py enums                                    # rebuild the tables
python3 tools/ssl2.py diff mine.ssl2 theirs.ssl2               # bisect a rejection
```

The counts below are the Easy View 3 library's, 25 610 profiles. A second
library disagrees with it in ways that matter, and the next section is that
story — read it before trusting any figure here as a fact about the *format*.
`verify` re-derives the codec claims on demand; `enums` re-derives the tables.

## The cipher, and its one trap

AraCrypt: three LFSRs, key `DasCryptKey`, one keystream byte per plaintext
byte. The algorithm was published years ago by third parties (OFL issue #99,
HakanL's gist, the MIT `ssl2-tools` package); nothing was recovered here.

| | |
|---|---|
| **The trap** | It is **not** a plain XOR. When `plain ^ keystream` comes out **0**, the cipher emits the *keystream byte* instead. |
| **What that costs** | A NUL in the plaintext does not survive a round trip. XML has none, so decrypt/encrypt is exact — on XML, and only on XML. |
| **What it buys** | Encrypt and decrypt are the same operation, so there is one function. |
| **Speed** | The LFSRs never read the data, so the keystream is a pure function of the key: generate it once, XOR after that. Doing it per byte instead is what makes a Python sweep of the library take twenty minutes rather than ninety seconds. |

A second trap, upstream of the format: the corpus is full of **mojibake**.
`µ` — the marker on a fine (LSB) channel — is stored double-encoded, and reads
back as `Âµ`. The codec carries bytes through untouched rather than repairing
them, because repairing them would break the round trip. The generator emits
clean UTF-8.

## Structure

Thirteen elements, one nesting, no text content anywhere:

| Element | Parent | n | What it carries |
|---|---|---:|---|
| `DLMFILE` | — | 25 610 | `VERSION="3" TYPE="SSLLIBRARY"` |
| `SSLLIBRARY` | `DLMFILE` | 25 610 | name, `SSLLCUID`, `SSLLCOWNERUID` |
| `SSLPROPERTIES` | `SSLLIBRARY` | 25 610 | 34 always-present physical attributes |
| `SSLMODES` | `SSLLIBRARY` | 25 610 | `SSLNBMODE` |
| `SSLMODE` | `SSLMODES` | 58 463 | mode name, index, `SSLNBCHANNEL` |
| `SSLCHANNEL` | `SSLMODE`, `SSLGCHANNELS` | 1 066 103 | type, name, MSB/LSB, indexes |
| `SSLPRESETS` | `SSLCHANNEL` | 1 066 694 | `SSLNBPRESET`, a range UID when non-empty |
| `SSLPRESET` | `SSLPRESETS` | 2 402 621 | type, name, icon, DMX range, 20+ optional |
| `SSLBEAMS` | `SSLPROPERTIES`, `SSLCHANNEL` | 474 871 | `SSLNBBEAM` |
| `SSLBEAM` | `SSLBEAMS` | 1 256 446 | a beam's position |
| `SSLGCHANNELS` | `SSLLIBRARY` | 9 848 | a second channel list, matrices |
| `SSLCHANNELDMXRANGES` | `SSLCHANNEL` | 412 | `SSLCHANNELNBRANGE` |
| `SSLCHANNELDMXRANGE` | `SSLCHANNELDMXRANGES` | 1 003 | one sub-range |

### What varies between libraries, and what does not

This is the correction that cost the most here, so it goes before the tables.

Two Nicolaudie libraries sit on this machine, and they do not agree:

| | Easy View 3 | EasyViewConnect |
|---|---:|---:|
| profiles | 25 610 | 17 210 |
| `VERSION="3"`, byte-exact round trip | **25 610** | **7 764** of 7 924 |
| `VERSION="2"` (`TYPE="SSLLIBRARY2008"`, no prolog at all) | 0 | 9 286 |
| unreadable with `DasCryptKey` | 0 | 160 |

The Easy View 3 library is a **normalised export**: one prolog, ` />` on every
empty element, and not one byte between two tags in 25 610 files. Read that as
a property of the *format* — which is exactly what the first version of this
tool did — and the parser refuses a third of the older library. The one shipped
with EasyViewConnect indents with newlines (5 668 files), writes `/>` with no
space before it, has three files whose prolog carries no `encoding`, and one
with a UTF-8 BOM.

So the codec **records** all of it and re-emits it verbatim: the prolog, the
gap before every tag, the gap before every `</`, and the space before each
`>` / `/>`. Same rule as everywhere else in this tree — unknown bytes pass
through untouched. What every library does agree on is narrower than it looked:

| | |
|---|---|
| Content | no text, no comment, no CDATA — only whitespace between tags |
| Attributes | always `NAME="value"`, double-quoted, one space apart |
| Names | uppercase `[A-Z0-9]+`, elements and attributes alike |
| Empty elements | `<X …/>` or `<X …></X>`, both occur — the codec records which |

The generator emits the normalised form: one space before `/>`, no indentation.

**The 160 unreadable ones.** 157 of them share the same first eight *ciphertext*
bytes, so they are one family with one header, and `DasCryptKey` is not their
key; one is zero bytes long. Nothing here tries to find that key — that is the
first of the four conditions in [`LEGAL.md`](../LEGAL.md), and it is not
negotiable for a nicer number in a table.

### Counters and indexes

| Attribute | Rule |
|---|---|
| `SSLNBMODE`, `SSLNBCHANNEL`, `SSLNBPRESET` | the number of children, exactly |
| `SSLMODEINDEX` | 0…n−1 |
| UID suffix (`…-0`, `…-1`) | the element's index among its siblings |
| `SSLCHANNELTYPEINDEX` | how many channels of the **same type** came before — not the channel's position. Present on mode channels (945 234), absent on `SSLGCHANNELS` channels (120 869) |
| `SSLPRESETRANGEUID` | present exactly when `SSLNBPRESET > 0` (456 260 of 456 266) |
| `SSLPRESETDEFAULTPRESET="1"` | exactly one preset per channel |
| `SSLCHANNEL16BITSINDEX` | the paired channel's index, or `-1`; the pair carries `SSLCHANNELMSB="1"` / `SSLCHANNELLSB="1"` |

## Channel types (`SSLCHANNELTYPE`)

Every number the library uses, with the evidence. `n` is how many channels
carry it; **Agreement** is the share that agree on the name once the obvious
variants are folded together (case, spacing, a `1.` prefix, the `Âµ` marker).
A row marked **uncertain** is a candidate, not a reading — see `INCERTAINS_CANAL`
in [`tools/ssl2.py`](../tools/ssl2.py) for what the candidates are. Numbers
38–42, 49 and 51 do not occur at all.

Looking for "Gobo Wheel"? It is **8** — 16 068 channels, 23 % of them called
exactly that and another 55 % called a variant of it.

| Code | Name | n | Agreement | |
|---:|---|---:|---:|---|
| 0 | Generic | 158410 | 5 % |  |
| 1 | Pan | 37992 | 82 % |  |
| 2 | Tilt | 44094 | 82 % |  |
| 3 | Barrel Roll | 164 | 28 % | **uncertain** |
| 4 | Barrel Pan | 225 | 17 % | **uncertain** |
| 5 | Color Wheel | 18957 | 41 % |  |
| 6 | Color Wheel Rotation | 189 | 34 % |  |
| 7 | Dimmer | 78378 | 69 % |  |
| 8 | Gobo Wheel | 16068 | 23 % |  |
| 9 | Gobo Rotation | 7697 | 65 % |  |
| 10 | Gobo Index | 351 | 31 % |  |
| 11 | Gobo Shake | 448 | 66 % |  |
| 12 | Gobo Wheel Rotation | 304 | 41 % |  |
| 13 | Iris | 2408 | 94 % |  |
| 14 | Zoom | 14246 | 89 % |  |
| 15 | Shutter / Strobe | 55666 | 45 % |  |
| 16 | Focus | 9328 | 98 % |  |
| 17 | Frost | 5188 | 85 % |  |
| 18 | Speed | 43923 | 25 % |  |
| 19 | Prism | 9390 | 66 % |  |
| 20 | Prism Rotation | 6714 | 62 % |  |
| 21 | Prism Index | 71 | 31 % |  |
| 22 | Lamp | 2271 | 69 % |  |
| 23 | Color Temperature | 8575 | 26 % |  |
| 24 | Smoke | 1780 | 19 % | **uncertain** |
| 25 | Red | 132006 | 68 % |  |
| 26 | Green | 132003 | 67 % |  |
| 27 | Blue | 132003 | 68 % |  |
| 28 | Cyan | 2972 | 99 % |  |
| 29 | Magenta | 2970 | 99 % |  |
| 30 | Yellow | 2969 | 99 % |  |
| 31 | White | 70545 | 70 % |  |
| 32 | Gobo Bounce | 12 | 33 % | **uncertain** |
| 33 | Framing Rotation | 448 | 20 % |  |
| 34 | Framing Blade Rotation | 248 | 6 % |  |
| 35 | Framing Blade | 2408 | 5 % |  |
| 36 | Animation Wheel | 523 | 70 % |  |
| 37 | Macro | 25850 | 9 % |  |
| 43 | Warm White | 6191 | 65 % |  |
| 44 | Cold White | 4080 | 64 % |  |
| 45 | Amber | 16108 | 76 % |  |
| 46 | Uv | 7329 | 82 % |  |
| 47 | Lime | 1810 | 33 % | **uncertain** |
| 48 | Lime | 2386 | 94 % |  |
| 50 | Cyan | 63 | 71 % | **uncertain** |
| 52 | Pink | 11 | 27 % | **uncertain** |
| 53 | Mint | 331 | 100 % |  |

A generic channel (0) is called anything at all, which is why its agreement is
5 % and its reading is still solid. The public table in `ssl2-tools` covers 16
of these numbers and agrees with every one, except 37, which it reads
"Auto Programs".

## Preset types (`SSLPRESETTYPE`)

Same columns. Where the names split, the **parent channel type** settles it:
preset 3 sits under channel 5 (Color Wheel) 96 % of the time, which is what
makes it the colour wheel's rotation and not some other wheel's.

| Code | Name | n | Agreement | |
|---:|---|---:|---:|---|
| 0 | No Function | 1139945 | 9 % |  |
| 1 | Color | 309103 | 7 % |  |
| 2 | Color Combination 2 | 63545 | 3 % |  |
| 3 | Color Wheel Rotation | 20609 | 37 % |  |
| 4 | Dimmer | 73992 | 82 % |  |
| 5 | Dimmer Simple | 593 | 19 % | **uncertain** |
| 6 | Dimmer Pulse | 21808 | 24 % |  |
| 7 | Gobo | 279288 | 4 % |  |
| 8 | Gobo Rotation | 14449 | 33 % |  |
| 9 | Rotation Index | 6249 | 56 % |  |
| 10 | Gobo Shake | 4129 | 24 % |  |
| 11 | Gobo Wheel Rotation | 24342 | 45 % |  |
| 12 | Iris | 2277 | 34 % |  |
| 13 | Iris Open/Closed | 965 | 13 % | **uncertain** |
| 14 | Iris Pulse | 4314 | 19 % |  |
| 15 | Zoom | 13638 | 62 % |  |
| 16 | Zoom In/Out | 1780 | 8 % | **uncertain** |
| 17 | Lamp On | 3402 | 89 % |  |
| 18 | Lamp Off | 3274 | 94 % |  |
| 19 | Shutter Open | 73838 | 52 % |  |
| 20 | Shutter Closed | 22863 | 48 % |  |
| 21 | Strobe | 83629 | 59 % |  |
| 22 | Pulse Strobe | 17473 | 13 % |  |
| 23 | Blackout While Moving | 5310 | 73 % |  |
| 24 | Focus | 7866 | 57 % |  |
| 25 | Focus Simple | 274 | 8 % | **uncertain** |
| 26 | Frost | 5593 | 63 % |  |
| 27 | Frost Simple | 932 | 12 % |  |
| 28 | Speed | 45355 | 89 % |  |
| 29 | Speed Tracking | 595 | 34 % |  |
| 30 | Speed Simple | 1780 | 11 % | **uncertain** |
| 31 | Prism | 25837 | 33 % |  |
| 32 | Prism Rotation | 15545 | 39 % |  |
| 33 | Prism Rotation Index | 7421 | 58 % |  |
| 34 | Color Temperature | 9387 | 12 % |  |
| 35 | Color Temperature Step | 1827 | 12 % |  |
| 36 | Barrel Roll Rotation | 473 | 18 % |  |
| 37 | Smoke | 2652 | 13 % |  |
| 38 | Smoke Simple | 163 | 10 % |  |
| 39 | Frost Pulse | 1186 | 20 % |  |
| 40 | Rotation Off | 22266 | 95 % |  |
| 41 | Reset | 9411 | 27 % |  |
| 42 | Strobe Off | 29456 | 95 % |  |
| 43 | Color Combination 3 | 10436 | 15 % |  |
| 44 | Color Combination 4 | 3630 | 36 % |  |
| 45 | Color Wheel Index | 1414 | 62 % |  |
| 46 | Animation Wheel Rotation | 1026 | 12 % |  |
| 47 | Blackout While Gobo Wheel Changing | 995 | 82 % |  |
| 48 | Blackout While Color Wheel Changing | 1044 | 85 % |  |
| 49 | Blackout While Wheel Changing | 1451 | 62 % |  |
| 51 | Framing Rotation | 413 | 19 % |  |
| 52 | Framing Rotation Index | 156 | 29 % |  |
| 53 | Framing Blade 1 | 523 | 38 % |  |
| 54 | Framing Blade 2 | 499 | 39 % |  |
| 55 | Framing Blade 3 | 499 | 39 % |  |
| 56 | Framing Blade 4 | 499 | 39 % |  |
| 57 | Framing Blade 1 Rotation | 105 | 11 % | **uncertain** |
| 58 | Framing Blade 2 Rotation | 78 | 15 % | **uncertain** |
| 59 | Framing Blade 4 Rotation | 86 | 14 % | **uncertain** |
| 60 | Framing Blade 3 Rotation | 85 | 14 % | **uncertain** |
| 61 | Gobo Bounce | 387 | 75 % |  |
| 62 | Barrel Pan | 112 | 51 % |  |
| 100 | Fan Speed | 349 | 62 % |  |

## 16-bit channels

A coarse/fine pair is two `SSLCHANNEL`s of the same type, each carrying the
other's **index within the mode** in `SSLCHANNEL16BITSINDEX`, one flagged
`SSLCHANNELMSB="1"` and the other `SSLCHANNELLSB="1"`. All 62 400 pairs in the
library are symmetric; 47 of them straddle two channel *types*, which is the
only thing about them that is not uniform.

| | Measured over 25 610 profiles |
|---|---|
| Wired both ways | 124 772 / 124 772 half-channels point back at their partner |
| Same channel type | 124 753 / 124 772 |
| Fine after coarse in the mode | 62 360 / 62 400 |
| **Adjacent** | 115 743 / 124 772 — the other 7 % read `Pan Tilt µPan µTilt` |
| `SSLCHANNELTYPEINDEX` | the pair counts **once**: the fine half repeats its coarse half's index. That rule holds on 56 551 of the library's 58 463 modes, against 41 609 for counting every channel — which is what the generator used to do, and what a mode with no 16-bit channel cannot tell apart |

**The name, and the trap in it.** The fine half is marked with `µ`, stored
double-encoded: the file's UTF-8 text is `Âµ`, itself the UTF-8 of the UTF-8 of
`µ`. Writing a clean `µ` would produce a name unlike any of the library's, so
`tools/ssl2.py` builds the marker by doing to `µ` exactly what the vendor's
tooling did — `"µ".encode("utf-8").decode("latin-1")` — and the four bytes
`C3 82 C2 B5` land in the file. Where it goes is a plurality, not a rule:

| Form | n | |
|---|---:|---:|
| `Pan (Âµ)` | 28 113 | 45 % — what the generator writes |
| `ÂµPan` | 15 379 | 25 % |
| `( Âµ ) Pan` | 10 550 | 17 % |
| `microPan` | 4 368 | 7 % |
| `ï¿½Pan` and `ï¿½ Pan` | 3 590 | 6 % — the same marker, mojibake a second way |
| `Pan Fine`, `Pan 16 bit`, … | 400 | < 1 %, across 90 more forms |

## `SSLGCHANNELS` and `SSLCHANNELLINKED`

`SSLGCHANNELS` is a third child of `SSLLIBRARY`, after `SSLMODES`: a channel
list belonging to the profile rather than to a mode. A mode's channel points
into it with `SSLCHANNELLINKED`, whose value is one of its
`SSLCHANNELUID`s — 9 848 profiles carry the element, and not one link in any
of them points outside it. 63 more profiles carry links and **no**
`SSLGCHANNELS` at all, so the reference can dangle.

The identity worth having is the count:

> the number of `SSLCHANNEL` under `SSLGCHANNELS` equals the number of distinct
> `SSLCHANNELLINKED` over all modes.

**9 084 of 9 848 profiles (92.2 %).** The 764 that diverge all diverge the same
way — 2 077 entries no mode points at, and never a link with no entry:

| The 2 077 orphans | |
|---|---|
| 8-bit | 2 077 / 2 077 — not one is the fine half of a pair |
| Carry presets | 1 512 |
| Unique by (type, name) in their profile | 1 883 — `Color Wheel`, `Background Red`, `Index Colors` |

That reads as an editor that keeps a channel's global entry after the channel
has been removed from every mode: the list is a superset of what is used, never
a subset. It is the one thing the generator deliberately does not reproduce.

**The 16-bit pair collapses into one 8-bit entry**, which is measured and not
assumed: all 120 869 `SSLGCHANNELS` channels carry `MSB="0" LSB="0"` and
`SSLCHANNEL16BITSINDEX="-1"`, none carries `SSLCHANNELTYPEINDEX`, and the fine
half of a pair never links anywhere else than its coarse half — 26 947 pairs
share one entry, 35 453 leave the fine half unlinked, **none** point at two.
An entry is otherwise a copy of the mode channel, presets and preset UIDs
included; only `SSLPRESETTARGET` differs, and the next section says why.

Which mode channels are "the same channel" is the vendor editor's own
bookkeeping and cannot be read off a file. The generator uses `(type, name)`,
and says so — that is its convention, not a reading of the format.

## `SSLPRESETTARGET`

The index, **within the mode**, of the channel holding the physical object the
preset acts on; `-1` when there is none. 40 of the 63 preset types write `-1`
on 100 % of their presets — Shutter Open, Strobe, Iris, Colour, Dimmer, Reset.
The rest point, and what they point at is a channel type:

| Preset | → channel | points | that type | |
|---|---|---:|---:|---|
| 3 Color Wheel Rotation | 5 Color Wheel | 99 % | 94 % | |
| 8, 9, 10, 11, 61 (gobo rotation, index, shake, wheel rotation, bounce) | 8 Gobo Wheel | 95-99 % | 90-97 % | |
| 32, 33 Prism Rotation / Rotation Index | 19 Prism | 97 / 84 % | 89 / 95 % | |
| 45 Color Wheel Index | 5 Color Wheel | 90 % | 95 % | |
| 51 Framing Rotation | 33 Framing Rotation | 93 % | 92 % | |
| 53-56 Framing Blade 1-4 | 35 Framing Blade | 90-94 % | 100 % | |
| 57-60 Framing Blade Rotation | 34 Framing Blade Rotation | 65-71 % | 92-100 % | |
| 29 Speed Tracking | 1 Pan | 99 % | 84 % | |
| 7 Gobo | — | **1 %** | 96 % | left out: it barely points |
| 28 Speed | — | 98 % | **39 %** | left out: Pan 39 %, generic 24 %, macro 21 % |
| 30 Speed Simple | — | 94 % | **58 %** | left out, same reason |
| 52 Framing Rotation Index | — | 87 % | **72 %** | left out, same reason |

A type is claimed only when a majority of its presets point (≥ 50 %) *and* the
channel type they point at is settled (≥ 80 % of the pointing ones). Preset 28
is the instructive exclusion: what a speed governs is a property of the
fixture, not of the preset type, so `-1` and an explicit `target` are the
honest answers and a guess is not.

*Which* channel of that type, when a fixture has two gobo wheels: the preset's
own channel if it is already of the target type, otherwise the channel of that
type with the **same `SSLCHANNELTYPEINDEX`** as the channel carrying the preset
— the second gobo-rotation channel drives the second wheel — falling back to
the first channel of that type. That rule reproduces the library's own value on
**1 930 409 of 1 981 368 presets (97.43 %)**; `ssl2.py enums` prints the
residue per type, and preset 28 alone accounts for 34 362 of the 50 959 misses.
Picking the first channel instead of the same-rank one scores 97.31 %, and gets
Prism Rotation wrong ten points more often.

**The `SSLGCHANNELS` copy always carries `-1`** — 421 260 of 421 260 — even
where the mode's copy carries an index. A mode-relative channel index means
nothing in a list that belongs to no mode.

## The five optional preset attributes

`SSLPRESETLEVELMIN`/`LEVELMAX`, `SSLPRESETPARAMMIN`/`PARAMMAX` and
`SSLPRESETCOLOR`. Whether one is written at all is a property of the **preset
type**, and the distribution says so without a threshold having to be argued
over: across the 315 (type, attribute) cells, every one is either ≤ 21 %
present or ≥ 94 % present. Nothing lands in the 73-point gap.

| | |
|---|---|
| `LEVELMIN` / `LEVELMAX` | **not** the preset's DMX range. 0 and 255 on 21 679 of 21 679 gobo presets, whatever range each covers — a level scale in its own units. Present on 1 410 935 presets |
| `PARAMMIN` / `PARAMMAX` | the physical parameter's range, in the parameter's own unit: 0-100 for a percentage, 0-250 for a strobe, 0-720 for a rotation index in degrees, 0-16 for a zoom, 1-22 for a colour temperature. The *magnitude* is settled by the preset type; the *orientation* is not — `0,100` and `100,0` split 67/33 on Speed, which is the direction of the effect and belongs in the description |
| `SSLPRESETCOLOR` | **0xBBGGRR**, not 0xRRGGBB. The library's `Red` presets carry 255 and its `Blue` ones 16 711 680; `Yellow` is 65 535 and `Cyan` 16 776 960. A description should say `"#rrggbb"` and let the tool do the swap |

`DEFAUTS_PRESET` in [`tools/ssl2.py`](../tools/ssl2.py) is the per-type default
the generator writes when the description is silent, and `ssl2.py enums`
re-derives all four tables from a library and refuses a disagreement — it
reports **0 divergences** over the 25 610 profiles here. The share the dominant
value wins by is printed rather than enforced, because it is what says which
cells are firm: `LEVELMIN`/`LEVELMAX` at 98-100 %, `PARAMMIN`/`PARAMMAX`
between 40 % and 100 %, and `SSLPRESETCOLOR` on preset 1 (Color) at 44 % —
a colour preset's colour is its content, and the default white is a fallback,
not a reading.

## Writing a fixture

A description is JSON. The smallest useful one is three lines of channels:

```json
{
  "name": "Acme Par 18",
  "brand": "Acme",
  "modes": [
    {"name": "3ch", "channels": [
      {"type": "Red"}, {"type": "Green"}, {"type": "Blue"}
    ]}
  ]
}
```

```bash
python3 tools/ssl2.py gen acme-par-18.json
```

Everything else is filled in: UIDs, counters, indexes, and the physical block,
copied from the shape of the library's own `_GENERIC/RGB.ssl2`. A generated
profile differs from that template in its **identity only** — five UIDs, the
creator field and the RDM name — and in nothing structural.

| Key | Where | Meaning |
|---|---|---|
| `name`, `brand` | top level | required |
| `properties` | top level | values passed straight into `SSLPROPERTIES` (beam angle, size, icon, 3D object…), overriding the defaults; an unknown name is refused |
| `modes[]` | top level | at least one; `name` optional |
| `channels[]` | mode | `type` required — a name from the table above, or its number |
| `name`, `icon` | channel | default to the type's name and to empty — and for a fine channel, to the coarse one's name plus the `µ` marker |
| `fine` | channel | `true` pairs this channel as the fine half of the nearest earlier unpaired channel of the same type; an integer names the coarse channel's index outright, for the 7 % of layouts that read `Pan Tilt µPan µTilt` |
| `presets[]` | channel | optional |
| `gchannels` | top level | `true` emits `SSLGCHANNELS` and links every mode channel to it; one entry per distinct `(type, name)`, a 16-bit pair counting once |
| `type` | preset | required, from the preset table |
| `dmx` | preset | `[start, end]`, default `[0, 255]`; overlapping ranges are refused |
| `default` | preset | the DMX value it opens on; defaults to `start` |
| `defaut` | preset | `true` on the one preset the channel starts on; defaults to the first |
| `name`, `icon` | preset | default to the type's name and to `NoIcon` |
| `color` | preset | `"#rrggbb"`, or the integer the file carries (**0xBBGGRR**); `null` drops the attribute. Defaults to the preset type's |
| `level`, `param` | preset | `[min, max]`, either half `null` to drop it, the pair `null` to drop both. Default to the preset type's — `level` is *not* the DMX range |
| `target` | preset | the index of the mode channel the preset acts on, or `null` for none. Defaults to the rule in [`SSLPRESETTARGET`](#sslpresettarget) |

A fuller one — dimmer, shutter with three states, colour wheel with presets:

```json
{
  "name": "Test Par RGB",
  "brand": "wolfmix-automation",
  "modes": [
    {"name": "7ch", "channels": [
      {"type": "Dimmer"},
      {"type": "Shutter / Strobe", "name": "Shutter", "presets": [
        {"type": "Shutter Closed", "name": "Closed", "dmx": [0, 7]},
        {"type": "Shutter Open", "name": "Open", "dmx": [8, 15], "defaut": true},
        {"type": "Strobe", "name": "Slow to fast", "dmx": [16, 255], "default": 128}
      ]},
      {"type": "Color Wheel", "name": "Color", "presets": [
        {"type": "Color", "name": "White", "dmx": [0, 9]},
        {"type": "Color", "name": "Red", "dmx": [10, 19]},
        {"type": "Color", "name": "Blue", "dmx": [20, 29]},
        {"type": "Color Wheel Rotation", "name": "Clockwise", "dmx": [30, 255]}
      ]},
      {"type": "Red"}, {"type": "Green"}, {"type": "Blue"}, {"type": "White"}
    ]}
  ]
}
```

And the parts this section used to say could not be described — a 16-bit pair
whose halves are not adjacent, a global channel list, a colour, a strobe's
range in Hz:

```json
{
  "name": "Test Moving 16bit",
  "brand": "wolfmix-automation",
  "gchannels": true,
  "modes": [
    {"name": "6ch", "channels": [
      {"type": "Pan"},
      {"type": "Tilt"},
      {"type": "Pan", "fine": true},
      {"type": "Tilt", "fine": true},
      {"type": "Color Wheel", "name": "Color", "presets": [
        {"type": "Color", "name": "White", "dmx": [0, 9], "color": "#ffffff"},
        {"type": "Color", "name": "Red", "dmx": [10, 19], "color": "#ff0000"},
        {"type": "Color Wheel Rotation", "name": "Spin", "dmx": [20, 255]}
      ]},
      {"type": "Shutter / Strobe", "name": "Shutter", "presets": [
        {"type": "Shutter Open", "name": "Open", "dmx": [0, 15], "defaut": true},
        {"type": "Strobe", "name": "1 to 25 Hz", "dmx": [16, 255], "param": [1, 25]}
      ]}
    ]}
  ]
}
```

The four channels come out `Pan`, `Tilt`, `Pan (Âµ)`, `Tilt (Âµ)`, each pair
carrying the other half's index; `SSLGCHANNELS` gets four entries, not six,
because a pair counts once; `Spin` gets `SSLPRESETTARGET="4"`, the colour
wheel's own index, without the description saying so.

Drop the result into `ScanLibrary/<Brand>/` and the software picks it up.

## Limits

| | |
|---|---|
| `VERSION="2"` | refused, **as a version we do not decode, not as a broken file** — 9 286 of them sit in the EasyViewConnect library. They decrypt cleanly with the same key, carry `TYPE="SSLLIBRARY2008"` and have no `<?xml` prolog at all. `verify` counts them apart, and `charge_xml` raises `VersionNonPriseEnCharge`. Calling them corrupt would be a lie about someone else's file. |
| A wrong key | refused, and told apart from the above: the marker is `<DLMFILE` in the decrypted head, not the prolog — the prolog cannot carry it, since V2 has none. |
| `SSLBEAMS` | read and round-tripped, **not generated**. Multi-beam bars and matrices survive a read/write cycle; they cannot be described yet. Of the five limits this section used to list, it is the one still standing as written. |
| 16-bit pairs, `SSLGCHANNELS`, `SSLPRESETTARGET` and the five preset attributes | **generated and accepted; the wiring itself is still unread.** A profile carrying all four loads, patches and reports its 10 channels in Easy View (below), so nothing in them is refused. What no test here has seen is the *effect*: whether the software pairs the fine channel, in which order it holds the channels, and what it prints for the `µ` marker. Easy View 3 shows none of the three, and settling them needs a W1 driving it over the 3D Link. |
| `SSLPRESETPRISMTYPE`, `SSLPRESETSHOWDIMMER` | observed, not understood. The generator writes the library's majority value and offers no option: an unmeasured knob is worse than no knob. `SSLPRESETTARGET` used to sit on this line and no longer does — see its own section. |
| The `SSLGCHANNELS` orphans | 764 profiles carry global entries no mode points at, and the generator does not reproduce that. The reading — an editor keeping a removed channel's entry — is `hypothesized`: it explains every case seen, and nothing here has watched the editor do it. |
| `SSLCREATOR` | left empty. It holds an email address in the library, and a generated profile is not theirs to sign. |

## The software test

The round trip proves the codec, not acceptance. A file the software refuses
is worth nothing, so the writer is only trustworthy once Easy View has loaded
one.

**Prediction, published before the test** (method:
[`docs/methodology.md`](methodology.md)):

1. The profile is accepted and appears under its brand with its name, its
   channels in order and its presets listed — **0.7**.
2. If it is refused, the cause is `SSLLCOWNERUID`: every profile in the library
   carries the vendor's one cloud-account UUID, and a generated one carries its
   own. Prediction: it is **ignored** — an unknown owner means "not from the
   cloud", not "invalid" — **0.85**.
3. A restart, or an explicit library rescan, is needed before a new file shows
   up — **0.5**.

**Outcome: accepted** (Easy View, 2026-08-31, this machine). Both generated
profiles imported, appear in the room, and patch — the fixture panel reads
`Mode 1 (7 Channels)` for the seven-channel description above, and 7000 K,
which is our `SSLLAMPTEMP`. Prediction 1 holds. Prediction 2 holds with it:
`SSLLCOWNERUID` was a UUID we invented and the profile loaded anyway, so an
owner outside the vendor's cloud account is ignored rather than refused.
Prediction 3 was not tested — the app was started after the files were in
place, so nothing says whether a running instance would have needed a rescan.

The writer is **software-confirmed** for what that test covers: the file is
read, the fixture exists, the channel count is ours. It does **not** yet cover
the channel *order* or the presets as displayed — nothing has looked at that
list. Do not stretch the claim past the measurement.

Two defaults are worth overriding, both inherited from the generic panel and
both visible in that panel:

| `properties` key | Default | Why you may want another |
|---|---|---|
| `SSLLAMPLUX`, `SSLLAMPPOWER` | `0` | the panel then reports 1 lm, and the fixture throws almost no light in the 3D view. The library's usual value is `-1` (unspecified) |
| `SSLBEAMOPENING` | `1` | a 1° beam — right for a flat panel, wrong for anything with a lens |

### The second test: 16 bits, `SSLGCHANNELS`, and the channel order

The first test proved the file is read and the channel *count* is ours. It
looked at neither the order of the channels nor the presets, and neither
existed at the time. This one is scoped at exactly what the first did not
cover.

Description: a ten-channel moving head, `Pan Tilt µPan µTilt` — a **non-adjacent**
16-bit layout, so the pairing cannot be read off adjacency — then Gobo Wheel,
Gobo Rotation, Color Wheel, Shutter, Dimmer, Zoom, in that order and not in a
canonical one. `gchannels: true`, colours given as `#rrggbb`, one strobe with
an explicit `param` range.

**Prediction, published before the test:**

1. The profile is accepted, and the fixture panel reads **10 channels** —
   **0.85**. The first test earns most of that; what is new is that nothing in
   the five new attributes, the targets or `SSLGCHANNELS` trips a validator.
2. The channels appear **in the description's order**, Dimmer ninth — **0.85**.
   Nothing has ever looked at this, on any generated profile.
3. Easy View shows Pan and Tilt as **one 16-bit parameter each**, not as four
   independent channels — **0.7**. This is the claim the whole first item of
   the task rests on, and the pair is deliberately non-adjacent so that a
   passing result is about `SSLCHANNEL16BITSINDEX` and not about position.
4. The fine channel's name displays as `Pan (Âµ)`, **not** `Pan (µ)` — **0.6**.
   The file's UTF-8 text really is `Âµ`; a conformant reader shows the mojibake,
   and every one of the library's own 62 400 fine channels would show it too.
   If Easy View shows a clean `µ`, it repairs the double encoding on the way in,
   and that is worth knowing before anyone "fixes" the marker.
5. `SSLGCHANNELS` changes nothing visible — it is a redundant copy of what the
   modes already carry — **0.6**.

**Outcome: one confirmed, three unmeasurable in this application, one
consistent** (Easy View 3, 2026-09-01, this machine).

**1 holds.** The profile appears under `wolfmix-automation`, the Mode dropdown
reads `Mode 1 (10 Channels)`, and it patches — `Patched On`, `Universe 1`,
`Address 1`. The Fixture panel reads 7000 K and a 14° beam, which are our
`SSLLAMPTEMP` and our `SSLBEAMOPENING`. So a profile carrying two 16-bit pairs,
an `SSLGCHANNELS` list, eight `SSLCHANNELLINKED` references, non-`-1`
`SSLPRESETTARGET`s and all five optional preset attributes is **read and
patched without complaint**. That is the claim the writer needed and did not
have.

**2, 3 and 4 cannot be measured in Easy View 3, and this is a property of the
application, not a failed test.** It has no per-fixture channel list — checked
in the Fixture panel, the `View` menu (which offers only Builder View, Live
View, DMX Levels, Full screen, Always on top), the `DMX Levels` grid, which is
512 unnamed values, and Preferences, which has no DMX or network section. It
has no DMX input to drive either: `Controller: None`, no Art-Net, and it holds
no socket on the 3D-Link port. Its saved project is a ZIP whose every entry —
`project.ev` and the wheel images — is password-encrypted, and opening that is
the one thing [`LEGAL.md`](../LEGAL.md) rules out, so the channel order, the
pairing and the `µ` rendering were **not** read off it. The route that can
settle all three is not documented in this tree yet: WTOOLS drives Easy View 3
over its 3D Link, so import the profile *there*, patch it, push channel 9 and
watch the panel light, push channel 3 and watch a 1/256 step. It needs a W1
connected, which is why it did not happen here.

**5 is consistent, not confirmed.** Nothing visible changed, which is what was
predicted — and "nothing visible" is not a measurement.

Two things worth recording next to the result:

- **A running instance does not see a new file.** With Easy View already open,
  the profile dropped into `ScanLibrary/` was absent from Add Fixture; the
  refresh button in that dialog rescanned and it appeared, with no restart.
  That measures prediction 3 of the first test, which had been left untested.
- **Adding the fixture crashed Easy View once**, and it is not the profile's
  doing: the report is `EXC_BAD_ACCESS` in
  `QAccessible::updateAccessibility` under `ObjectsWidget::expandParent`,
  *after* `AddFixtureObjectCommand::redo()` and `CEvent::objectAdded()` had
  both returned — Qt's accessibility bridge, which is live because the session
  was driving the app through the accessibility API. It did not reproduce on
  the same profile in a fresh project.


## Not the Wolfmix

Loading a profile into Easy View is not the same as having a Wolfmix drive the
fixture. WTOOLS does not read `ScanLibrary/` at all: its fixture library is
`wmProfiles.wmx` in its own application-support directory — a sidecar whose
payload is undecoded here, no key for it being public ([`LEGAL.md`](../LEGAL.md)).
A profile
generated here reaches a W1 the way any other does — through WTOOLS's own
import — and nothing in `tools/ssl2.py` shortens that path.
