"""
Script to remove all Django template comments from HTML templates.

This removes all {# ... #} comments that might be visible in the UI.
"""

import os
import re
from pathlib import Path

def remove_comments_from_file(file_path):
    """Remove Django template comments from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove single-line comments {# ... #}
        content = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
        
        # Remove multi-line comments that might span lines
        content = re.sub(r'\{#[\s\S]*?#\}', '', content)
        
        # Clean up extra blank lines (more than 2 consecutive)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Remove comments from all template files."""
    templates_dir = Path('templates')
    
    if not templates_dir.exists():
        print("Templates directory not found!")
        return
    
    # Get all HTML template files
    template_files = list(templates_dir.rglob('*.html'))
    
    print(f"Found {len(template_files)} template files")
    print("Removing comments...\n")
    
    modified_count = 0
    for template_file in template_files:
        if remove_comments_from_file(template_file):
            print(f"Cleaned: {template_file}")
            modified_count += 1
    
    print(f"\nDone! Modified {modified_count} files.")

if __name__ == '__main__':
    main()

