# BuildingShop folding platform trolley: 16:9 Amazon demo video

**Render (no voiceover):** `out/buildingshop_folding_trolley_amazon_16x9.mp4`. 1920×1080, 30 fps, 35.0 s, −14.5 LUFS. No captions and no border.

**Sources:**
- Supplier demo clip (`raw/ref_a.mp4`, Sagar confirmed it's ours to use), upscaled to 1080p. At 13 s another brand's crate shows at the edge, so that shot is cropped past it.
- 4 Runway images (`plates/`): load, folded, shop and home. Each was generated with a frame of the real trolley as a reference.
- The ESPO video was **not** used: it carries their logo, watermark and contact details.

**Amazon rules:** no URL, price or phone number. The trolley is on screen from frame 1. The only claims are the ones Sagar confirmed (up to 500 kg, folding handle) plus what the footage shows (flat platform, wheels).

## Edit (what plays)
| Time | Shot | Graphics | Sound |
|---|---|---|---|
| 0.0–3.4 | Real clip: foot flips the handle up, it locks | BUILDINGSHOP / Folding Platform Trolley | click on lock |
| 3.4–8.4 | Real clip: hero, slow push-in | Callouts with leader lines: folding steel handle, wide flat platform, smooth-rolling wheels | pops |
| 8.4–12.8 | Runway: loaded with cement bags in a warehouse | 0→500 KG load gauge | impact when it lands |
| 12.8–17.8 | Real clip: pushed across the floor | floor arrow, "Rolls smoothly, less effort" | wheel roll |
| 17.8–20.3 | Real clip reversed: handle folds down | "Handle folds flat" | click |
| 20.3–23.6 | Runway: folded flat against the storeroom wall | "Stores flat in any corner" | |
| 23.6–26.8 | Runway: shop / godown with cartons | "Shops & godowns", "Warehouses" | |
| 26.8–30.0 | Runway: home shifting by the lift | "Home & office shifting" | |
| 30.0–35.0 | Real clip: pushed toward camera | End card: title + up to 500 kg / folding handle / easy to push & store | fade |

Music is an original synthesised bright corporate bed (112 BPM). There are whooshes on the cuts.

## Optional voiceover (one voice, background only, no captions)
Settings: Eleven Multilingual v2, Speed 1.0, Stability 45%, Similarity 75%, Style 30%, Speaker Boost on.

**Voice: NARRATOR.** Warm, confident Indian male or female, product-explainer tone (not dramatic).
Save as `narrator.mp3` (the `<break>` lengths are set so each line lands on its shot):
```
मिलिए BuildingShop के folding platform trolley से। <break time="1.2s" /> मज़बूत steel handle… चौड़ा flat platform… और आराम से चलने वाले wheels। <break time="1.0s" /> पाँच सौ किलो तक का load, आसानी से। <break time="1.5s" /> भारी सामान? बस हल्का सा धक्का… और काम हो गया। <break time="1.3s" /> काम ख़त्म हुआ तो handle मोड़ो… और trolley को किसी भी कोने में रख दो। <break time="1.2s" /> दुकान हो, godown हो, या घर की shifting… हर जगह काम आए। <break time="1.0s" /> BuildingShop folding platform trolley… काम आसान, मेहनत कम।
```
To make the voiceover version, run `python3 demo16x9.py --vo vo/narrator.mp3`. The music ducks under the voice automatically. If any line runs long, I'll retime that shot to it.
