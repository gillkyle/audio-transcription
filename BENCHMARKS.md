# Benchmarks

**Model:** `mlx-community/whisper-large-v3-turbo`
**Hardware:** Apple Silicon (local)
**Date:** 2026-02-15

## Model Load Time

~10s one-time cost per batch run.

## Per-File Timings (warm cache)

| File | Size | Audio | Processing | Speed |
|------|------|-------|------------|-------|
| Jan 01 journal | 1.9 MB | 5.8 min | 10.0s | 34.8x realtime |
| Jan 02 journal | 3.9 MB | 12.3 min | 18.5s | 39.7x realtime |
| Jan 03 journal | 2.6 MB | 8.1 min | 13.3s | 36.4x realtime |
| **Total** | **8.4 MB** | **26.1 min** | **41.8s** | **37.5x realtime** |

## Key Rate

- **~1.6 seconds of processing per minute of audio**
- RTF: 0.027 (processes 37.5x faster than realtime)

## Extrapolated Estimates

| Batch | Audio | Est. Processing Time |
|-------|-------|---------------------|
| 10 files like these | ~1 hr | ~2.3 min |
| 50 files like these | ~7 hrs | ~12 min |
| 100 files like these | ~15 hrs | ~23 min |
| 1 hour of audio | 1 hr | ~1.6 min |
| 10 hours | 10 hrs | ~16 min |
| 100 hours | 100 hrs | ~2.7 hrs |
| 500 hours | 500 hrs | ~13 hrs |
| 1,000 hours | 1,000 hrs | ~27 hrs |

## Notes

- Longer files process slightly faster due to better amortization of per-file overhead.
- Estimates assume single-worker sequential processing.
