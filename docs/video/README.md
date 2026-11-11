# Current Proof Desk media, v5.0.0

[Watch v5](https://www.youtube.com/watch?v=GTaQR-LZLKk) · [English MP4](https://github.com/rafaorlando3/proof-before-pay/releases/download/media-v5.0.0/Proof-Before-Pay-v5-en.mp4) · [Brazilian Portuguese MP4](https://github.com/rafaorlando3/proof-before-pay/releases/download/media-v5.0.0/Proof-Before-Pay-v5-pt-BR.mp4)

This **171-second** cut shows the actual hosted Proof Desk on 11 November 2026: the 11-example snapshot, three starting routes, a retained 84 BRL synthetic refund, a closed mismatch with no effect, labelled constructed inputs, retained LIVE 1566, the local checklist and an emulated mobile view. It makes no new product model call, embedding, transaction, review, payment or case. It is not footage of the v7 evaluation.

The desktop capture is 1440×810. S03 uses a native narrow 504×934 view after a blurred desktop take was rejected. The emulated mobile take is 390×844. Their original aspect is preserved in the 1920×1080/30fps export; no invented UI, pan, zoom or time stretching was added. Cuts join separate real takes. The final card is editorial, not product UI. Earlier failed captures remain private and are excluded.

`script-v5.json` contains the approved narration and four caption texts. [media-v5.0.0.json](media-v5.0.0.json) pins the two exact MP4 hashes, screenshot sources and review scope. [cc-v5/](cc-v5/) contains four SRT tracks aligned for each of the two narration versions; each MP4 also embeds all four tracks. Use the `en-audio_*.srt` files for the YouTube English master. Languages: EN, PT-BR, ES and Simplified Chinese. Only English and Brazilian Portuguese have new narration in this cut; the earlier four-voice release remains historical.

Narration uses local Kokoro synthetic voices `af_heart` (EN) and `pf_dora` (PT-BR), not Rafael's voice. Kokoro models are Apache-2.0; kokoro-onnx is MIT. Existing license and attribution files below accompany the source. Weights, environments, credentials, vendor images and private evaluation inputs are excluded. There is no music track. Caption translations are machine-assisted and not certified.

Validation covers ffprobe, complete video/audio decoding, both local Whisper-base transcription comparisons, actual export/source frame inspection and subtitle checks. Decoded AAC matched its final narration WAV with correlation above 0.9999. The ASR PT output misrecognizes some brand and technical terms; it is not a verbatim or pronunciation certificate. Its trailing music token was checked against four seconds of digital silence and rejected. No human-ear or naturalness certification is claimed.

Codex inspected actual frames and checks. Claude reviewed supplied actual frames through official CLI image input plus text/metadata. Argon independently reviewed script, ASR, metadata and exact hashes; it did not directly view images. Neither peer claimed full video playback or audio listening. Hash review does not establish watching or hearing. The final media files and these factual scope limits were approved before publication.

## Historical 4.2.1 source and narration

The section below describes the earlier cut and its original publication gate. Rafael separately authorized the current media refresh and publication without a new generic approval. Historical sources and organizer delivery are preserved.

### Earlier source and narration

`script-v4.json` is the multilingual source of the 168-second review cut. Its English master has Portuguese (Brazil), Spanish and Mandarin alternate narration and closed captions. The footage shows an actual native IRIS workflow with a recorded agent proposal and synthetic effects, distinct from the frozen live-model evaluation. The new demonstration case was approved once by an authenticated test reviewer; Rafael is not the approver shown.

Narration is synthetic, not Rafael’s voice. It was rendered locally with Kokoro-82M and Kokoro-82M-v1.1-zh (Apache-2.0), using kokoro-onnx (MIT). Model weights, environments, credentials and the vendor IRIS image are excluded from this repository and the source package. Attribution and license texts accompany this script. Original editorial graphics and a quiet synthetic transition bed accompany genuine continuous browser recordings.

Generate the production script and planning captions:

```sh
python3 -I docs/video/video_cc.py docs/video/script-v4.json /tmp/pbp-video-planning
```

The generator distributes planning cues uniformly over each scene. Final delivery captions instead follow actual synthesized segment spans, with phrase timing reviewed against the export. They are provided beside the videos. The four languages still receive final linguistic and pronunciation review; no certified native-speaker review is claimed.

Organizer instructions require an English README and a video or description. Four-language narration is an accessibility choice; no multilingual-video bonus or specific formal approval is claimed. Publishing the contest entry still requires Rafael’s explicit approval.
