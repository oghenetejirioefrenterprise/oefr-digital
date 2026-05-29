# Licensed Insurance Agent Registry - Harvest

**Opportunity**: High-scoring (9/10) B2B dataset - insurance agent licenses from all 50 states + DC

**Target**: ~1.2M insurance agent licenses nationwide  
**Current**: 952,724 Texas records harvested (Phase 1 complete)

## Files

- `harvest_phase1_texas.py` - Texas Socrata API harvester
- `raw_texas.csv` - 952K Texas agent licenses (212 MB)
- `harvest_phase1_texas.json` - Harvest metadata
- `STATE_SOURCES.md` - State-by-state source catalog
- `PROGRESS.md` - Detailed progress report and roadmap

## Quick Start

```bash
# Run Texas harvest (already complete)
python3 harvest_phase1_texas.py

# Check results
head raw_texas.csv
cat harvest_phase1_texas.json
```

## Next Steps

See `PROGRESS.md` for Phase 2 roadmap (multi-state expansion).
