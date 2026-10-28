# Video source and narration

`script-v4.json` is the multilingual source of the 168-second review cut. Its English master has Portuguese (Brazil), Spanish and Mandarin alternate narration and closed captions. The footage shows an actual native IRIS workflow with a recorded agent proposal and synthetic effects, distinct from the frozen live-model evaluation. The new demonstration case was approved once by an authenticated test reviewer; Rafael is not the approver shown.

Narration is synthetic, not Rafael’s voice. It was rendered locally with Kokoro-82M and Kokoro-82M-v1.1-zh (Apache-2.0), using kokoro-onnx (MIT). Model weights, environments, credentials and the vendor IRIS image are excluded from this repository and the source package. Attribution and license texts accompany this script. Original editorial graphics and a quiet synthetic transition bed accompany genuine continuous browser recordings.

Generate the production script and planning captions:

```sh
python3 -I docs/video/video_cc.py docs/video/script-v4.json /tmp/pbp-video-planning
```

The generator distributes planning cues uniformly over each scene. Final delivery captions instead follow actual synthesized segment spans, with phrase timing reviewed against the export. They are provided beside the videos. The four languages still receive final linguistic and pronunciation review; no certified native-speaker review is claimed.

Organizer instructions require an English README and a video or description. Four-language narration is an accessibility choice; no multilingual-video bonus or specific formal approval is claimed. Publishing the contest entry still requires Rafael’s explicit approval.
