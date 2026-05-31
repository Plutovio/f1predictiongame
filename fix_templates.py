import glob
import ast

for filepath in glob.glob('templates/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content_stripped = content.strip()
    if content_stripped.startswith('"') and content_stripped.endswith('"'):
        try:
            # Parse the python string literal to unescape \n and \"
            unwrapped = ast.literal_eval(content_stripped)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(unwrapped)
            print(f"Fixed {filepath}")
        except Exception as e:
            print(f"Failed to fix {filepath}: {e}")
