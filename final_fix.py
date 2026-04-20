import re
import os

file_path = r'd:\face\templates\access_control\home.html'

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Read {len(content)} bytes from {file_path}")

# Regex to find {% ... %} tags that extend over multiple lines
# We capture the whole tag in group 1
pattern = re.compile(r'({%[^%]*?%})', re.DOTALL)

def fix_tag(match):
    tag = match.group(1)
    if '\n' in tag:
        # It's a split tag
        # Collapse whitespace to single space
        joined = re.sub(r'\s+', ' ', tag)
        # Ensure spaces around internal contents: "{%if" -> "{% if"
        joined = joined.replace('{%', '{% ').replace('%}', ' %}')
        # Cleanup double spaces
        joined = re.sub(r'\s+', ' ', joined).strip()
        # Specific fix for clean formatting
        joined = joined.replace('{% ', '{% ').replace(' %}', ' %}')
        print(f"Fixing split tag:\nORIGINAL: {tag!r}\nFIXED:    {joined!r}\n")
        return joined
    return tag

new_content = pattern.sub(fix_tag, content)

if new_content != content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully wrote fixed content to home.html")
else:
    print("No split tags found needing fix.")

# Verification
with open(file_path, 'r', encoding='utf-8') as f:
    check_content = f.read()
    
# Check for any remaining tags with newlines
remaining_splits = re.findall(r'{%[^%]*?\n[^%]*?%}', check_content, re.DOTALL)
if remaining_splits:
    print(f"WARNING: Found {len(remaining_splits)} remaining split tags!")
    for i, tag in enumerate(remaining_splits):
        print(f"  Split {i+1}: {tag!r}")
else:
    print("VERIFICATION PASS: No split tags remaining.")
