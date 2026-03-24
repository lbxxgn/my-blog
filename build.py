#!/usr/bin/env python3
import os
import sys
from cssmin import cssmin
from jsmin import jsmin
import shutil
import argparse

SKIP_DIRS = {'uploads', '__pycache__', 'node_modules'}
SKIP_FILES = {'.DS_Store'}


def main():
    parser = argparse.ArgumentParser(description='Build optimized static assets')
    parser.add_argument('--minify', action='store_true', help='Minify CSS/JS files')
    parser.add_argument('--merge', action='store_true', help='Merge CSS/JS files')
    args = parser.parse_args()

    # Create build directory
    build_dir = os.path.join(os.path.dirname(__file__), 'static_build')
    os.makedirs(build_dir, exist_ok=True)

    # Copy all static files first
    for root, dirs, files in os.walk('static'):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file in SKIP_FILES:
                continue
            src_path = os.path.join(root, file)
            dest_path = os.path.join(build_dir, src_path[7:])  # Remove 'static/' prefix
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            if args.minify:
                # Minify CSS files
                if file.endswith('.css'):
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    minified = cssmin(content)
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(minified)
                    print(f'Minified CSS: {src_path} → {dest_path}')

                # Minify JS files
                elif file.endswith('.js'):
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    minified = jsmin(content)
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(minified)
                    print(f'Minified JS: {src_path} → {dest_path}')

                # Copy other files as-is
                else:
                    shutil.copy2(src_path, dest_path)
                    print(f'Copied: {src_path} → {dest_path}')
            else:
                shutil.copy2(src_path, dest_path)
                print(f'Copied: {src_path} → {dest_path}')

    # Create merged bundles if requested
    if args.merge:
        print("\nCreating merged CSS bundle...")
        css_files = [
            'static/css/style.css',
            'static/css/mobile-weibo.css',
            'static/css/pc-feed.css',
            'static/css/lightbox.css',
            'static/css/share.css',
            'static/css/draft-dialog.css',
            'static/css/easymde.css',
            'static/css/quill.css'
        ]

        merged_css = ''
        for css_file in css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    merged_css += f"\n/* --- {css_file} --- */\n"
                    merged_css += f.read()

        if args.minify:
            merged_css = cssmin(merged_css)

        merged_css_path = os.path.join(build_dir, 'css/bundle.css')
        os.makedirs(os.path.dirname(merged_css_path), exist_ok=True)
        with open(merged_css_path, 'w', encoding='utf-8') as f:
            f.write(merged_css)
        print(f'Created merged CSS bundle: {merged_css_path}')

        print("\nCreating merged JS bundle...")
        js_files = [
            'static/js/main.js',
            'static/js/lazyload.js',
            'static/js/loading.js',
            'static/js/infinite-scroll.js',
            'static/js/mobile-layout.js',
            'static/js/mobile-editor.js',
            'static/js/lightbox.js',
            'static/js/code-copy.js',
            'static/js/share.js',
            'static/js/shortcuts.js',
            'static/js/theme.js',
            'static/js/draft-sync.js',
            'static/js/editor-workbench.js',
            'static/js/pagination.js',
            'static/js/passkeys.js'
        ]

        merged_js = ''
        for js_file in js_files:
            if os.path.exists(js_file):
                with open(js_file, 'r', encoding='utf-8') as f:
                    merged_js += f"\n/* --- {js_file} --- */\n"
                    merged_js += f.read()

        if args.minify:
            merged_js = jsmin(merged_js)

        merged_js_path = os.path.join(build_dir, 'js/bundle.js')
        os.makedirs(os.path.dirname(merged_js_path), exist_ok=True)
        with open(merged_js_path, 'w', encoding='utf-8') as f:
            f.write(merged_js)
        print(f'Created merged JS bundle: {merged_js_path}')

    print(f"\nBuild completed! Output directory: {build_dir}")
    if args.minify:
        print("Files were minified for production use")
    if args.merge:
        print("Files were merged into bundles for fewer HTTP requests")

if __name__ == '__main__':
    main()
