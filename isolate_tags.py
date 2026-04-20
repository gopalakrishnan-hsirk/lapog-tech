
import re

file_path = r'd:\face\templates\access_control\home.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize tags and ensure each tag is on its own line
# First, remove any existing newlines inside tags
def clean_tag(match):
    tag = match.group(0)
    inner = tag[2:-2].strip()
    return f"{{% {re.sub(r'\\s+', ' ', inner)} %}}"

content = re.sub(r'{%.*?%}', clean_tag, content, flags=re.DOTALL)

# Now, ensure every tag has a newline before and after it
# We do this by replacing {% with \n{% and %} with %}\n
# Then we clean up multiple newlines
content = re.sub(r'{%', r'\n{%', content)
content = re.sub(r'%}', r'%}\n', content)

# Clean up multiple newlines and spaces
content = re.sub(r'\n\s*\n', '\n', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully forced tags to new lines in home.html")
