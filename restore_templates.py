import json
import os
import ast

log_path = r'C:\Users\dell\.gemini\antigravity\brain\d51fb0d0-1ae7-4e2f-8856-3731adc08b6b\.system_generated\logs\transcript.jsonl'
restored = 0

with open(log_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            if data.get('tool_calls'):
                for tc in data['tool_calls']:
                    if tc.get('name') == 'write_to_file':
                        args = tc.get('args', {})
                        
                        target_str = args.get('TargetFile')
                        code_str = args.get('CodeContent')
                        
                        if target_str and code_str:
                            try:
                                # target_str is a string that might be wrapped in quotes
                                if target_str.startswith('"') and target_str.endswith('"'):
                                    target = ast.literal_eval(target_str)
                                else:
                                    target = target_str
                                
                                if code_str.startswith('"') and code_str.endswith('"'):
                                    # handle literal newlines properly
                                    code = ast.literal_eval(code_str.replace('\n', '\\n'))
                                else:
                                    code = code_str
                                
                                if target.endswith('.html'):
                                    os.makedirs(os.path.dirname(target), exist_ok=True)
                                    
                                    # Remove the usage comments that cause recursion
                                    code = code.replace('<!-- Usage: {% include', '{# Usage: {% include').replace('%} -->', '%} #}')
                                    
                                    with open(target, 'w', encoding='utf-8') as tf:
                                        tf.write(code)
                                    restored += 1
                                    print(f"Restored {target}")
                            except Exception as parse_e:
                                print(f"Error parsing args on line {line_idx}: {parse_e}")
                                print("TargetStr:", repr(target_str)[:100])
        except Exception as e:
            print(f"Outer Error on line {line_idx}: {e}")

print('Restored HTML files:', restored)
