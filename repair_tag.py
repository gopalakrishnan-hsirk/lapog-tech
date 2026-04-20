
import re

filename = 'd:/project/templates/access_control/home.html'
with open(filename, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find the split tag across lines
# It has a newline and some spaces/indentation
pattern = r'\{% else %\}-{%[ \t\r\n]+endif %\}'
replacement = r'{% else %}-{% endif %}'

new_content = re.sub(pattern, replacement, content)

if new_content == content:
    print("Could not find the pattern to replace.")
    # Try a broader pattern
    pattern2 = r'\{% else %\}-{%[ \t\r\n]+( *|[\t]*)endif %\}'
    new_content = re.sub(pattern2, replacement, content)

if new_content != content:
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully joined the tag.")
else:
    print("Failed to repair. Pattern might be different.")
