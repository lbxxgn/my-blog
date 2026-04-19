# Reading Experience Enhancement Design

Date: 2026-04-19

## Context

The blog's article reading page works but lacks polish for long-form reading. Two pain points identified: no immersive reading mode (too many distractions), and the dark mode is too harsh (pure black backgrounds, high contrast). Both PC and mobile users need these improvements.

## Feature 1: Immersive Reading Mode

### Trigger
- Book-page icon button in post header area (PC: next to theme toggle, mobile: in top bar)
- Keyboard shortcut `R` to toggle
- State persisted to `localStorage` per post URL

### Behavior on Enter
- **Hide**: header nav, footer, share buttons, comments section, tags, sidebar
- **Layout**: article full-width centered, `max-width` narrows to 680px, more side padding
- **Typography**: line-height increases to 1.9, paragraph spacing slightly larger
- **Background**: pure white (light) or warm dark (dark), grain texture overlay disabled
- **UI overlay**: semi-transparent exit button (top-right, PC) or thin exit bar (mobile), reading progress bar stays visible
- PC: subtle decorative side lines in light gray

### Behavior on Exit
- Press `R` again, click exit button, or `Esc`
- Mobile: tap thin top bar to exit

### Files Modified
- `templates/post.html` — add reader mode toggle button
- `static/css/enhancements.css` — `.reader-mode` body class with overrides
- `static/js/enhancements.js` — toggle logic, localStorage, keyboard handler

### CSS Approach
Single class `reader-mode` on `<body>`. All overrides scoped to `body.reader-mode`:
```
body.reader-mode header { display: none }
body.reader-mode .share-buttons { display: none }
body.reader-mode .comments-section { display: none }
body.reader-mode .post-tags { display: none }
body.reader-mode .post-navigation { display: none }
body.reader-mode .post-content { max-width: 680px; line-height: 1.9 }
body.reader-mode::after { display: none } /* hide grain */
```

## Feature 2: Dark Mode Color Optimization

### Current Problems
- Background `#1a1a1a` is pure black — too harsh
- Text `#d4d4d4` contrast too high against black
- Code blocks barely distinguishable from content area
- Overall tone is cold/uncomfortable for extended reading

### New Dark Palette
| Element | Current | New | Reason |
|---------|---------|-----|--------|
| Background | `#1a1a1a` | `#191b22` | Warm blue-gray, less harsh |
| Card/code bg | `#252525` | `#1e2028` | Subtle distinction from background |
| Text | `#d4d4d4` | `#c8ccd4` | Softer, less contrast |
| Heading | `#e8e8e8` | `#dce0e8` | Consistent with text softening |
| Border | `#404040` | `#2a2d38` | More subtle |
| Secondary text | `#b8b8b8` | `#8b919d` | Clearer hierarchy |

### System Preference Detection
On first visit (no `localStorage` theme set), check `prefers-color-scheme: dark` media query and auto-apply dark theme. Once user manually toggles, their choice takes priority.

### Files Modified
- `static/css/enhancements.css` — update `.dark-theme` CSS variable overrides

## Verification
- PC: open any post, press `R` — all chrome disappears, article centered with generous spacing. Press `R` again to restore.
- Mobile: tap reader icon — same behavior, thin exit bar at top.
- Dark mode: toggle to dark, compare text/background warmth. Code blocks should be distinguishable but not jarring.
- First visit in system dark mode: should auto-apply dark theme.
- Reader mode + dark mode combined: should work together seamlessly.
