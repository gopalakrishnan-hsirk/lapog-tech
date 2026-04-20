
import re

file_path = r'd:\face\templates\access_control\home.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Normalize tags: Join any tag that spans multiple lines
# This matches {% ... %} including newlines
def normalize_tag(match):
    tag = match.group(0)
    # Replace all whitespace sequences (including newlines) with a single space
    # but keep a space after {% and before %}
    inner = tag[2:-2].strip()
    return f"{{% {re.sub(r'\\s+', ' ', inner)} %}}"

fixed_content = re.sub(r'{%.*?%}', normalize_tag, content, flags=re.DOTALL)

# 2. Check balance
if_count = len(re.findall(r'{% if ', fixed_content))
endif_count = len(re.findall(r'{% endif %}', fixed_content))
for_count = len(re.findall(r'{% for ', fixed_content))
endfor_count = len(re.findall(r'{% endfor %}', fixed_content))
block_count = len(re.findall(r'{% block ', fixed_content))
endblock_count = len(re.findall(r'{% endblock %}', fixed_content))

print(f"Stats: IF={if_count}, ENDIF={endif_count}")
print(f"Stats: FOR={for_count}, ENDFOR={endfor_count}")
print(f"Stats: BLOCK={block_count}, ENDBLOCK={endblock_count}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

if if_count != endif_count:
    print("WARNING: Unbalanced IF tags!")
if for_count != endfor_count:
    print("WARNING: Unbalanced FOR tags!")
if block_count != endblock_count:
    print("WARNING: Unbalanced BLOCK tags!")

print("Successfully processed home.html")
