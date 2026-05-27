import os
import glob

components_dir = 'web/src/components'
jsx_files = glob.glob(os.path.join(components_dir, '*.jsx'))

replacements = {
    'text-white': 'text-slate-900 dark:text-white',
    'text-on-surface-variant': 'text-slate-600 dark:text-on-surface-variant',
    'border-white/5': 'border-black/5 dark:border-white/5',
    'border-white/10': 'border-black/10 dark:border-white/10',
    'border-white/20': 'border-black/20 dark:border-white/20',
    'bg-white/5': 'bg-black/5 dark:bg-white/5',
    'bg-white/10': 'bg-black/10 dark:bg-white/10',
    'bg-black/20': 'bg-slate-200 dark:bg-black/20',
    'bg-black/30': 'bg-slate-300 dark:bg-black/30',
    'bg-surface/60': 'bg-white/60 dark:bg-surface/60',
    'bg-surface-container-high': 'bg-slate-200 dark:bg-surface-container-high',
    'hover:bg-white/5': 'hover:bg-black/5 dark:hover:bg-white/5',
    'hover:bg-white/10': 'hover:bg-black/10 dark:hover:bg-white/10',
    'hover:text-on-surface': 'hover:text-slate-900 dark:hover:text-on-surface'
}

for file_path in jsx_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        # Prevent double replacement if script is run twice
        if new not in new_content:
            new_content = new_content.replace(old, new)
            
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
