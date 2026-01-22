# Simple Personal Blog System

A minimal, clean personal blog system built with Flask and SQLite. Perfect for personal daily notes and musings.

## Features

- ✅ Clean, minimalist design optimized for reading
- ✅ Markdown support for writing posts
- ✅ Image upload functionality
- ✅ Responsive design (PC and mobile)
- ✅ Authentication-protected admin interface
- ✅ Draft and published states
- ✅ Easy deployment with single command

## Tech Stack

- **Backend**: Python Flask 3.x
- **Database**: SQLite
- **Frontend**: Jinja2 templates, plain CSS/JS
- **Markdown**: markdown2 library

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

First run will prompt you to create an admin user.

### 3. Access the Blog

- Blog: http://localhost:5000
- Admin: http://localhost:5000/admin
- Login: http://localhost:5000/login

## Directory Structure

```
simple-blog/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css      # Stylesheets
│   ├── js/
│   │   └── editor.js      # Editor JavaScript
│   └── uploads/           # Uploaded images
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Homepage
│   ├── post.html          # Single post view
│   ├── login.html         # Login page
│   └── admin/
│       ├── dashboard.html # Admin dashboard
│       └── editor.html    # Post editor
└── posts.db               # SQLite database (auto-created)
```

## Usage

### Creating a Post

1. Login at `/login`
2. Go to `/admin` and click "新建文章"
3. Enter title and content in Markdown
4. Upload images using the "上传图片" button
5. Check "立即发布" to publish, or leave unchecked for draft
6. Click "保存"

### Editing a Post

1. Go to `/admin`
2. Click "编辑" next to the post
3. Make changes and save

### Markdown Syntax

```markdown
# Heading 1
## Heading 2

**Bold text**
*Italic text*

`inline code`

[Link text](url)

![Image description](/static/uploads/image.jpg)
```

## Deployment

### Local Development

```bash
python app.py
```

Runs on http://0.0.0.0:5000

### Production Deployment

For production deployment:

1. Set a secure SECRET_KEY environment variable
2. Consider using a production WSGI server (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. Use a reverse proxy (nginx) for SSL termination

## Configuration

Edit `config.py` to customize:

- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: SQLite database path
- `UPLOAD_FOLDER`: Image upload directory
- `MAX_CONTENT_LENGTH`: Max upload size (default: 5MB)
- `ALLOWED_EXTENSIONS`: Allowed image types

## Backup

To backup your blog:

1. Copy `posts.db` file
2. Copy `static/uploads/` directory

```bash
tar czf blog-backup-$(date +%Y%m%d).tar.gz posts.db static/uploads/
```

## License

MIT

## Author

Created with love for personal blogging.
