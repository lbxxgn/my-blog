# UX Enhancements Deployment Checklist

## Pre-Deployment

- [ ] Run database migrations
  ```bash
  python backend/migrations/migrate_drafts.py
  python backend/migrations/migrate_image_optimization.py
  ```

- [ ] Generate asset manifest
  ```bash
  python -c "from backend.app import app; app.app_context().push(); app.asset_manager.regenerate()"
  ```

- [ ] Test all features locally
- [ ] Backup database
- [ ] Review configuration settings

## Post-Deployment

- [ ] Verify database tables created
- [ ] Check manifest.json exists
- [ ] Test keyboard shortcuts
- [ ] Test draft sync on mobile
- [ ] Upload test image and verify optimization
- [ ] Check browser console for errors
- [ ] Monitor logs for first hour

## Rollback Plan

If issues occur:
1. Disable feature flags in config (add to config.py):
   ```python
   FEATURE_DRAFT_SYNC = False
   FEATURE_IMAGE_OPTIMIZATION = False
   ```
2. Restart application
3. If database issues: run rollback migrations:
   ```bash
   python backend/migrations/rollback_drafts.py
   python backend/migrations/rollback_image_optimization.py
   ```
4. Restore database from backup if needed

## Feature Verification

### Keyboard Shortcuts (Task 1)
- [ ] Ctrl+K focuses search
- [ ] Ctrl+N navigates to new post
- [ ] Ctrl+/ shows help modal
- [ ] Ctrl+B/I in editor work
- [ ] ESC closes modals

### Breadcrumb Navigation (Task 2)
- [ ] Breadcrumb shows on post pages
- [ ] Links navigate correctly
- [ ] Mobile truncation works

### Asset Versioning (Task 3)
- [ ] CSS/JS have hash in filenames
- [ ] Edit triggers new hash
- [ ] Manifest regeneration works

### Draft Sync (Tasks 5-6)
- [ ] 30s auto-save works
- [ ] Multi-device conflict detection
- [ ] Draft recovery dialog appears
- [ ] Conflict resolution works

### Image Optimization (Tasks 7-8)
- [ ] Upload returns immediately
- [ ] Optimization completes in background
- [ ] Responsive images work
- [ ] Badge shows compression
