# Repo-Mining Factory Spec: turning task-oriented repos into edge-typed primitives

Last updated: 2026-07-03

Audience: Claude Code, Codex, and agents building the source-adapter factory.

Status: specification + a hand-seeded first tranche. The application-domain
primitives that popular task repos encode (media/YouTube, image processing,
object detection, API integration, enrichment) are seeded in
`scripts/seeds/universal_families_media_vision_seed.py` and compose on the edge
graph today. This doc specifies the FACTORY that ingests real repositories into
the same edge-typed primitive shape at scale.

Honesty note: this workspace has restricted outbound network (scoped to the one
session repo), so live external-repo scraping does not run here. The seeded
families reference the real libraries (yt-dlp, FFmpeg, Pillow, OpenCV,
Ultralytics YOLO, Whisper, requests) as `source_ref_families` and stay
`candidate=true / serves_truth=false` - they become source-backed only when a
live miner attaches actual source refs and proof receipts.

## Why repos are a high-yield factory

A task-oriented repo already encodes a typed capability graph: function
signatures are typed edges (`def f(x: VideoFile) -> AudioFile`), CLI commands
have typed args/outputs, README examples show the ordering. The factory's job
is to extract those contracts as compact edge cards - NOT to copy the code -
so the route compiler can order them.

```text
repo -> capability graph -> edge-typed primitive candidates -> normalize ports
     -> compose -> benchmark -> proof -> promote
```

## What to extract (per repo)

```text
public functions / methods    -> py.fn primitive candidates (signature = edges)
CLI entry points              -> cli.command primitives (argv -> stdout/exit)
class methods / pipelines     -> primitive groups (hidden member route)
README / examples commands    -> observed route candidates + co-occurrence
tests / fixtures              -> proof asset candidates
OpenAPI / MCP / proto specs   -> contract-typed primitives (edges pre-typed)
requirements / imports        -> effect + dependency signals
LICENSE                       -> license gate (promotion blocker until reviewed)
```

## The miner pipeline (network-enabled runs)

```text
1. discover:   search repos by task keyword (youtube download, object detection,
               playlist, enrichment, image resize, ocr, api pagination, ...)
2. gate:       LICENSE + secret scan + generated/vendored exclusion (promotion
               blockers recorded, never bypassed)
3. parse:      Tree-sitter / AST -> symbols, signatures, CLI, specs (deterministic)
4. edge-type:  map each signature's params/return to the SHARED port vocabulary
               (VideoFile, AudioFile, ImageFile, DetectionSet, RecordPageStream,
               EnrichedRecordSet, ...) so mined primitives compose with existing
               ones - reuse primitives/edges.py canonical types + synonyms
5. card:       emit reusable_primitive_family / implemented_code_primitive cards
               (compact edge + blackbox + effects + proof obligations + source_refs)
6. dedupe:     kind::input_edge::output_edge::code_sha256
7. stage:      candidate rows, candidate=true / serves_truth=false
8. verify:     import smoke test + fixture behavior test -> receipts (only then
               does an implemented-code primitive become source-backed, L4->)
```

The load-bearing step is (4) edge-typing to the shared vocabulary. A mined
`download(url) -> path` is worthless for composition unless its ports are typed
`MediaUrl -> VideoFile`. That is what lets the compiler order a mined primitive
after `enumerate_playlist` and before `extract_audio` without reading its code.

## Shared port vocabulary (extend, do not fork)

The media/vision/api/enrichment ports already in use - reuse them so mined
primitives chain with the seeded ones:

```text
media:   MediaUrl, PlaylistUrl, MediaUrlSet, VideoFile, VideoFileSet, AudioFile,
         FrameSequence, TranscriptText, SubtitleTrack, Thumbnail, MediaMetadata
image:   ImageFile, ImageBatch
vision:  DetectionSet, BoundingBoxSet, ClassificationSet, ImageEmbedding,
         OcrTextBlockSet, TrackSet
api:     ApiResponse, RecordPage, RecordPageStream, NormalizedRecordSet, AccessToken
enrich:  EnrichedRecordSet
config:  DownloadPolicy, TranscodePolicy, DetectPolicy, ResizeSpec, ModelSpec,
         FetchPolicy, AuthSpec, EnrichPolicy, PaginationSpec, SchemaSpec
receipt: DownloadReceipt, TranscodeReceipt, DetectionReceipt, EnrichmentReceipt,
         FetchReceipt, OcrReceipt
```

## Proof it works today (seeded tranche, recompute from run manifest)

The seeded families already compile into the exact task pipelines these repos
solve, purely from edges, zero model calls:

```text
MediaUrl   -> download_video -> extract_audio -> transcribe_audio -> TranscriptText  (3 steps, all exact)
PlaylistUrl-> enumerate_playlist -> download_set -> VideoFileSet                       (2 steps, fan-out)
ImageFile  -> detect_objects -> nms_filter -> crop_regions -> ImageBatch              (3 steps, multi-input join)
FetchPolicy-> paginated_fetch -> flatten_pages -> company_profile -> EnrichedRecordSet (3 steps)
```

See `benchmarks/route_compiler_runs/<id>/compiled_routes.jsonl`.

## Candidate source repos / libraries by task (mining targets)

```text
youtube/media:     yt-dlp, ffmpeg-python, moviepy, pytube
transcription:     openai-whisper, faster-whisper, whisperX
image processing:  Pillow, opencv-python, scikit-image, imageio
object detection:  ultralytics (YOLO), detectron2, mmdetection, supervision
ocr:               tesseract/pytesseract, paddleocr, easyocr
embeddings:        open_clip, sentence-transformers, timm
api integration:   requests, httpx, tenacity, authlib
enrichment:        geopy, phonenumbers, email-validator, dnspython
```

## Next build slices

1. Implement the deterministic AST miner (`scripts/mine_repo_primitives.py`)
   with the license/secret gate and the edge-typing step, runnable in a
   network-enabled environment; output candidate cards into a new lane pack.
2. Import-smoke + fixture verification harness so mined implemented-code
   primitives earn receipts (L4 -> L7).
3. Feed mined edges through `primitives/route_compiler.py` and log the compose
   rate lift per repo - the metric that says a repo was worth mining.
4. A private/tenant variant that mines internal repos into tenant-scoped
   primitives (never storing raw code; only edges + source-ref hashes), per the
   operating manual's private-repo factory.
