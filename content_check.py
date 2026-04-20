
import re

file_path = r'd:\face\templates\access_control\home.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_content = False
stack = []

for i, line in enumerate(lines):
    line_num = i + 1
    # Find all tags
    tags = re.findall(r'{%\s*(\w+).*?%}', line)
    for tag in tags:
        if tag == 'block':
            if 'content' in line:
                in_content = True
        elif tag == 'endblock':
            if in_content:
                print(f"INFO: End of content block at line {line_num}")
                print(f"REMAINING STACK: {stack}")
                in_content = False
        
        if in_content:
            if tag in ['if', 'for']:
                stack.append((tag, line_num))
            elif tag == 'endif':
                if not stack or stack[-1][0] != 'if':
                    print(f"ERROR: endif at {line_num} but stack is {stack}")
                else:
                    stack.pop()
            elif tag == 'endfor':
                if not stack or stack[-1][0] != 'for':
                    print(f"ERROR: endfor at {line_num} but stack is {stack}")
                else:
                    stack.pop()
            elif tag == 'else':
                if not stack or stack[-1][0] != 'if':
                    print(f"ERROR: else at {line_num} but stack is {stack}")
            elif tag == 'elif':
                if not stack or stack[-1][0] != 'if':
                    print(f"ERROR: elif at {line_num} but stack is {stack}")
            elif tag == 'empty':
                if not stack or stack[-1][0] != 'for':
                    print(f"ERROR: empty at {line_num} but stack is {stack}")
