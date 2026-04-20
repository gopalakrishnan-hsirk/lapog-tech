
import re

file_path = r'd:\face\templates\access_control\home.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Find all tags in the line
    tags = re.findall(r'{%\s*(\w+).*?%}', line)
    for tag in tags:
        if tag in ['if', 'for', 'block']:
            stack.append((tag, line_num))
        elif tag == 'else' or tag == 'elif':
            # else doesn't change stack depth but we could check if top is 'if'
            pass
        elif tag == 'endif':
            if not stack or stack[-1][0] != 'if':
                print(f"Error: endif on line {line_num} does not match {stack[-1] if stack else 'nothing'}")
            else:
                stack.pop()
        elif tag == 'endfor':
            if not stack or stack[-1][0] != 'for':
                print(f"Error: endfor on line {line_num} does not match {stack[-1] if stack else 'nothing'}")
            else:
                stack.pop()
        elif tag == 'endblock':
            if not stack or stack[-1][0] != 'block':
                print(f"Error: endblock on line {line_num} does not match {stack[-1] if stack else 'nothing'}")
            else:
                block_info = stack.pop()
                if any(t[0] == 'if' or t[0] == 'for' for t in stack):
                    # This is actually allowed if the block is inside an if, 
                    # but usually it means we missed an endif inside the block.
                    pass

print(f"Final stack: {stack}")
