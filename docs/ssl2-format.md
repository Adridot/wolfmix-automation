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
| `name`, `icon` | channel | default to the type's name and to empty |
| `presets[]` | channel | optional |
| `type` | preset | required, from the preset table |
| `dmx` | preset | `[start, end]`, default `[0, 255]`; overlapping ranges are refused |
| `default` | preset | the DMX value it opens on; defaults to `start` |
| `defaut` | preset | `true` on the one preset the channel starts on; defaults to the first |
| `name`, `icon` | preset | default to the type's name and to `NoIcon` |

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

Drop the result into `ScanLibrary/<Brand>/` and the software picks it up.

## Limits

| | |
|---|---|
| `VERSION="2"` | refused, **as a version we do not decode, not as a broken file** — 9 286 of them sit in the EasyViewConnect library. They decrypt cleanly with the same key, carry `TYPE="SSLLIBRARY2008"` and have no `<?xml` prolog at all. `verify` counts them apart, and `charge_xml` raises `VersionNonPriseEnCharge`. Calling them corrupt would be a lie about someone else's file. |
| A wrong key | refused, and told apart from the above: the marker is `<DLMFILE` in the decrypted head, not the prolog — the prolog cannot carry it, since V2 has none. |
| `SSLBEAMS`, `SSLGCHANNELS` | read and round-tripped, **not generated**. Multi-beam bars and matrices survive a read/write cycle; they cannot be described yet. |
| 16-bit channels | same: read, not generated. A fine channel needs `SSLCHANNELMSB`/`LSB` and `SSLCHANNEL16BITSINDEX` wired both ways, and that has not been measured against the software. |
| `SSLPRESETTARGET`, `SSLPRESETPRISMTYPE`, `SSLPRESETSHOWDIMMER` | observed, not understood. The generator writes the library's majority value and offers no option: an unmeasured knob is worse than no knob. |
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

## Not the Wolfmix

Loading a profile into Easy View is not the same as having a Wolfmix drive the
fixture. WTOOLS does not read `ScanLibrary/` at all: its fixture library is
`wmProfiles.wmx` in its own application-support directory, one of the opaque
sidecars this repository does not touch ([`LEGAL.md`](../LEGAL.md)). A profile
generated here reaches a W1 the way any other does — through WTOOLS's own
import — and nothing in `tools/ssl2.py` shortens that path.
