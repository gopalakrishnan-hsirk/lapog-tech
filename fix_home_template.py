
import re

file_path = r'd:\face\templates\access_control\home.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix split {% endif %} and similar
# Look for {% followed by everything until %} even across newlines
# Then replace them with normalized versions (no internal newlines)

def fix_tag(match):
    tag = match.group(0)
    # Remove newlines and extra spaces inside the tag
    normalized = re.sub(r'\s+', ' ', tag)
    return normalized

# This regex matches {% ... %} including newlines
# [^%]* matches characters until %, but we need to be careful with %}
# Using a non-greedy .*? with re.DOTALL is safer
fixed_content = re.sub(r'{%.*?%}', fix_tag, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Successfully fixed split tags in home.html")
