# Quality Agent — Technical scoring 0–10

The **Quality** step validates the rendered video and produces a **0–10 technical score** before creative `video_review`.

## Dimensions

| Dimension | Checks |
|-----------|--------|
| integrity | Render exists, readable, minimum size |
| resolution | 1080×1920 |
| codec | H.264 / avc1 |
| framerate | ~60fps (partial credit ≥30fps) |
| audio | Narration ref + audio stream in file |
| duration | 15–60s ideal (partial credit outside) |
| subtitles | Segments or subtitle files |
| subtitle_sync | SRT cue timing vs segment list (when both present) |
| bitrate | Minimum `QUALITY_MIN_BITRATE_BPS` from ffprobe |
| real_clips / narration | When `QUALITY_REQUIRE_REAL_MEDIA=true` in production |

Overall **quality_score** = rounded average of dimension scores (0–10).

## Pass / fail

```env
QUALITY_MIN_SCORE=6
QUALITY_REQUIRE_REAL_MEDIA=
QUALITY_MIN_BITRATE_BPS=1000000
```

Unified publish gate: `contentos_shared.audiovisual_qa.evaluate_publish_gate()` — used by `auto_retry` and `publisher`.

- `quality_passed=true` when score ≥ min, no critical failures (missing render/audio), and no blocking errors
- On fail → workflow retries **`editor`** (unchanged)
- Artifact: `quality_report.json` in pipeline assets

## Payload (downstream)

```json
{
  "quality_score": 9,
  "quality_passed": true,
  "quality_min_score": 6,
  "quality_dimensions": {
    "integrity": 10,
    "resolution": 10,
    "codec": 10,
    "framerate": 10,
    "audio": 10,
    "duration": 10,
    "subtitles": 10
  },
  "quality_errors": [],
  "quality_suggestions": []
}
```

`video_review` consumes `quality_score` for the **technical** dimension and combined heuristic score.

## Related

- Creative score: `VIDEO_REVIEW_MIN_SCORE` (default 8) — [FLOW.md](./FLOW.md)
- Retry loop: quality → editor; video_review → script/hook (B8)
