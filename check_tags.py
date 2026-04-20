
import re

def check_balance(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    stack = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        line_num = i + 1
        # Match tags
        found_tags = re.findall(r'{%\s*(.*?)\s*%}', line)
        for t in found_tags:
            parts = t.split()
            if not parts: continue
            cmd = parts[0]
            
            print(f"L{line_num}: Found {cmd} | Stack: {[s[0] for s in stack]}")
            
            if cmd in ['if', 'for', 'block', 'with']:
                stack.append((cmd, line_num))
            elif cmd == 'endif':
                if stack and stack[-1][0] == 'if':
                    stack.pop()
                else:
                    print(f"!!! Error: unexpected endif at line {line_num}")
            elif cmd == 'endfor':
                if stack and stack[-1][0] == 'for':
                    stack.pop()
                else:
                    print(f"!!! Error: unexpected endfor at line {line_num}")
            elif cmd == 'endblock':
                if stack and stack[-1][0] == 'block':
                    stack.pop()
                else:
                    print(f"!!! Error: unexpected endblock at line {line_num}")

    print("Final Stack:", stack)

if __name__ == "__main__":
    check_balance('d:/project/templates/access_control/home.html')
