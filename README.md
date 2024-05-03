![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/adobe-bot/116f9fefb73f6fcf9ffe8ce34d72efd7/raw/covbadge.json)

# kernDump
Various scripts for analyzing, reading and writing kerning information. These
can be helpful for analyzing kerning (and the loss thereof) through various
stages of font production. Some of these tools have been presented at [ATypI Amsterdam 2013](https://atypi.org/presentation/yearning-for-kerning/).

---

### `convertKernedOTFtoKernedUFO.py`
Extracts kerning and groups from a compiled OTF and injects them into a new UFO file (which is created via `tx`).

__Dependencies:__ `getKerningPairsFromOTF.py` (same repo), [fontTools](https://github.com/fonttools/fonttools), `tx` (Part of the [Adobe FDK](https://github.com/adobe-type-tools/afdko))  
__Environment:__ command line
```zsh
python3 convertKernedOTFtoKernedUFO.py font.otf
```

---

### `dumpkerning.py`
Just van Rossum wrote this script. It imports all of the `getKerningPairsFromXXX` scripts (except VFB), and therefore can dump kerning from all kinds of formats (except VFB). Results in a `.kerndump` file at the location of the input file.

__Dependencies:__ `getKerningPairsFromFEA.py`, `getKerningPairsFromOTF.py`, `getKerningPairsFromUFO.py` (same repo)  
__Environment:__ command line
```zsh
python3 dumpkerning.py font.otf
python3 dumpkerning.py font.ufo
python3 dumpkerning.py kern.fea
```

---

### `getKerningPairsFromFEA.py`
Extract a list of all kerning pairs that would be created from a feature file.
Has the ability to use a GlyphOrderAndAliasDB file for translation of
“friendly” glyph names to final glyph names (for comparison with the output of
`getKerningPairsFromOTF.py`)

__Dependencies:__ None  
__Environment:__ command line

```zsh
python3 getKerningPairsFromFEA.py kern.fea
python3 getKerningPairsFromFEA.py -go <path to GlyphOrderAndAliasDB file> kern.fea

```

---

### `getKerningPairsFromOTF.py`
Extract a list of all (flat) GPOS kerning pairs in a font, and report the
absolute number of pairs.

__Dependencies:__ [fontTools](https://github.com/behdad/fonttools)  
__Environment:__ command line

```zsh
python3 getKerningPairsFromOTF.py font.otf
python3 getKerningPairsFromOTF.py font.ttf
```

---

### `getKerningPairsFromUFO.py`
Extract a list of all (flat) kerning pairs in a UFO file’s kern object, and
report the absolute number of pairs.

__Dependencies:__ [defcon](https://github.com/typesupply/defcon) or Robofont  
__Environment:__ command line or Robofont

```zsh
python3 getKerningPairsFromUFO.py font.ufo
```

---

### `getKerningPairsFromVFB.py`
Extract a list of all (flat) kerning pairs from a VFB’s kern object, and
report the absolute number of pairs. Run as a FontLab script.

__Dependencies:__ [FontLab 5](http://old.fontlab.com/font-editor/fontlab-studio/)  
__Environment:__ FontLab Studio 5

---

### `kernInfoWindow.py`
(Silly) visualization of absolute kerning distance.
Example of using the above `getKerningPairsFromUFO.py` from within Robofont.

__Dependencies:__ `getKerningPairsFromUFO.py` (above)  
__Environment:__ Robofont

<img src="kernInfoWindow.png" width="412" height="384" alt="Kern Info Window" />

---

### `kernMap.py`
Simple map to illustrate kerning topography.

By default, the output is an interactive html `canvas`, for exploration of the
kerning map. Use `pixel` or `svg` formats to obtain a fingerprint of the
kerning data.

__Environment:__ command line

<img src="kernmap_canvas.png" alt="KernMap canvas" />
<img src="kernmap_pixel.png" alt="KernMap pixel" />
