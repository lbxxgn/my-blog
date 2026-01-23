# Simple Personal Blog System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal personal blog system with Markdown support, image upload, and authentication for single-user deployment.

**Architecture:** Flask application with SQLite database, server-side Jinja2 templates, session-based authentication, and file-based image storage. Focus on simplicity and YAGNI principles.

**Tech Stack:** Python 3.x, Flask 3.x, SQLite, markdown2, Werkzeug password hashing, Jinja2 templates, vanilla CSS/JS

---

## Task 1: Project Setup and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.env.example`
- Create: `.gitignore`

**Context:** This is the foundation task. Sets up the project structure, dependencies, and configuration needed for all subsequent tasks.

**Steps:**
1. Create `requirements.txt` with Flask, markdown2, and Werkzeug
2. Create `config.py` with SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER configuration
3. Create `.env.example` for environment variable template
4. Create `.gitignore` to exclude Python cache, DB files, virtual env
5. Run `pip install -r requirements.txt` to install dependencies
6. Commit: "feat: set up project dependencies and configuration"

---

## Task 2: Database Models

**Files:**
- Create: `models.py`

**Context:** Core data layer. All other tasks depend on this for database operations. Implements SQLite models for posts and users with full CRUD operations.

**Implementation Requirements:**
- `init_db()`: Create posts and users tables
- `create_post(title, content, is_published)`: Insert new post
- `update_post(post_id, title, content, is_published)`: Update existing post
- `delete_post(post_id)`: Delete post
- `get_all_posts(include_drafts=False)`: Retrieve posts
- `get_post_by_id(post_id)`: Get single post
- `create_user(username, password_hash)`: Create user
- `get_user_by_username(username)`: Retrieve user for auth

**Database Schema:**
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    is_published BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
```

**Commit:** "feat: implement database models"

---

## Task 3: Basic Flask Application with Authentication

**Files:**
- Create: `app.py`
- Create: `templates/base.html`

**Context:** Core application logic. Implements all routes, authentication, and request handling. Depends on models.py.

**Implementation Requirements:**

**Routes:**
- `GET /`: Homepage listing published posts
- `GET /post/<id>`: View single post with Markdown rendering
- `GET /login`, `POST /login`: Login page and authentication
- `GET /logout`: Logout and clear session
- `GET /admin`: Admin dashboard (login required)
- `GET /admin/new`, `POST /admin/new`: Create new post (login required)
- `GET /admin/edit/<id>`, `POST /admin/edit/<id>`: Edit post (login required)
- `POST /admin/delete/<id>`: Delete post (login required)
- `POST /admin/upload`: Upload image (login required)

**Authentication:**
- Session-based using Flask sessions
- `@login_required` decorator for admin routes
- Werkzeug password hashing
- `create_admin_user()` function to prompt for admin creation on first run

**Markdown:**
- Use markdown2 library for rendering
- Enable extras: fenced-code-blocks, tables

**Image Upload:**
- Validate file types: png, jpg, jpeg, gif, webp
- Max size: 5MB
- Generate unique filename with timestamp
- Save to `static/uploads/`
- Return JSON with URL

**Commit:** "feat: create Flask application with authentication and routes"

---

## Task 4: Base Template and Navigation

**Files:**
- Create: `templates/base.html`

**Context:** Foundation template that all other templates extend. Provides consistent layout, navigation, and flash message display.

**Implementation Requirements:**
- HTML5 structure with viewport meta tag for responsive design
- Block definitions: title, content
- Navigation header with:
  - Blog title linking to home
  - Links: Home, Admin (if logged in), Login/Logout
- Flash message display with success/error categories
- Footer with copyright
- Link to `static/css/style.css`

**Note:** Already created in Task 3, update if needed.

---

## Task 5: Public-Facing Templates

**Files:**
- Create: `templates/index.html`
- Create: `templates/post.html`

**Context:** User-facing templates for reading blog posts. Must extend base.html.

**index.html Requirements:**
- List all published posts in reverse chronological order
- Each post shows: title (linked), date, excerpt (first 200 chars)
- "Read more" link to full post
- Empty state message if no posts

**post.html Requirements:**
- Display full post with rendered Markdown
- Show creation date, updated date (if different)
- "Back to home" link
- Max-width 680px for optimal reading

**Commit:** "feat: add public-facing templates for homepage and post view"

---

## Task 6: Admin Templates

**Files:**
- Create: `templates/login.html`
- Create: `templates/admin/dashboard.html`
- Create: `templates/admin/editor.html`

**Context:** Admin interface for managing posts. All require authentication.

**login.html Requirements:**
- Simple login form with username and password fields
- POST to `/login`
- Clean, centered layout

**dashboard.html Requirements:**
- Table listing all posts (published and drafts)
- Columns: title, status (published/draft badge), created_at, actions
- Actions: Edit link, Delete button with confirmation
- "New Post" button at top
- Empty state if no posts

**editor.html Requirements:**
- Form with title input
- Toolbar with Markdown shortcuts: Bold, Italic, Heading, Link, Code, Image Upload
- Split view: textarea on left, live preview on right
- Image upload button that inserts Markdown syntax
- "Publish now" checkbox
- Save and Cancel buttons
- Load existing post data when editing

**Commit:** "feat: add admin templates for dashboard and editor"

---

## Task 7: CSS Styling

**Files:**
- Create: `static/css/style.css`

**Context:** Provides clean, minimalist, responsive styling for the entire application.

**Design Requirements:**
- **Typography**: System fonts, 16px base, 1.6 line-height
- **Color Scheme**: White background, dark gray text (#333), blue accent (#2563eb)
- **Layout**:
  - Container max-width 1200px, centered
  - Post cards with hover effects
  - Single post max-width 680px for reading
- **Components**:
  - Header: Sticky top, nav links
  - Buttons: Primary (blue), secondary (gray), danger (red), upload (green)
  - Forms: Clean inputs with borders
  - Tables: Full width for admin dashboard
  - Alerts: Success (green), error (red) with icons
  - Badges: Published (green), Draft (yellow)
- **Editor**: Split pane (50/50 on desktop, stacked on mobile)
- **Responsive**: Mobile breakpoints at 768px
- **YAGNI**: No animations, no dark mode (keep it simple)

**Commit:** "feat: add comprehensive CSS styling"

---

## Task 8: JavaScript for Editor

**Files:**
- Create: `static/js/editor.js`

**Context:** Provides live Markdown preview and image upload functionality for the editor.

**Implementation Requirements:**

**Live Preview:**
- Listen to textarea input events
- Simple Markdown parser (headers, bold, italic, code, links, images, line breaks)
- Update preview div in real-time
- Convert Markdown to HTML

**Insert Markdown Helpers:**
- `insertMarkdown(before, after)` function
- Insert at cursor position
- Support selected text wrapping

**Image Upload:**
- Listen to file input change
- POST to `/admin/upload` with FormData
- On success: Insert `![图片描述](url)` at cursor
- On error: Show alert message
- Reset file input after upload

**Commit:** "feat: add JavaScript for editor with live preview and image upload"

---

## Task 9: README Documentation

**Files:**
- Create: `README.md`

**Context:** Comprehensive documentation for setup, usage, and deployment.

**Requirements:**
- Project description and features
- Tech stack overview
- Quick start guide
- Directory structure
- Usage instructions (create, edit posts)
- Markdown syntax reference
- Deployment guide (local and production)
- Configuration options
- Backup instructions
- License

**Commit:** "docs: add comprehensive README with setup and usage instructions"

---

## Task 10: Final Testing and Verification

**Context:** Ensure the complete application works end-to-end.

**Steps:**
1. Start application with `python app.py`
2. Create admin user when prompted
3. Test login flow
4. Create a test post with Markdown content
5. Upload an image
6. Publish the post
7. View the post on homepage
8. Test edit functionality
9. Test mobile responsiveness (browser dev tools)
10. Verify all links work
11. Stop server

**Final Commit:** If any issues found, fix and commit. If all good, ensure all previous commits are clean.

---

## Summary

After completing all 10 tasks, you'll have a fully functional personal blog system with:
- ✅ Python Flask backend with SQLite database
- ✅ User authentication with session management
- ✅ Markdown editor with live preview
- ✅ Image upload functionality
- ✅ Responsive design for PC and mobile
- ✅ Clean, minimalist UI
- ✅ Draft and published post states
- ✅ Comprehensive documentation

Ready to deploy with single command: `python app.py`
