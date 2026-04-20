
import os
import re

templates_dir = r'd:\face\templates\access_control'

def join_tags(match):
    tag_content = match.group(0)
    # Remove newlines and multiple spaces within the tag
    joined = re.sub(r'\s+', ' ', tag_content)
    # Normalize spacing
    joined = joined.replace('{%', '{% ').replace('%}', ' %}')
    joined = re.sub(r'{\s+%', '{%', joined)
    joined = re.sub(r'%\s+}', '%}', joined)
    joined = joined.replace('{% ', '{% ').replace(' %}', ' %}')
    # Final cleanup of any potential double spaces created
    joined = re.sub(r'\s+', ' ', joined)
    return joined

for filename in os.listdir(templates_dir):
    if filename.endswith('.html'):
        file_path = os.path.join(templates_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all {% ... %} blocks (including across newlines)
        fixed_content = re.sub(r'{%.*?%}', join_tags, content, flags=re.DOTALL)
        
        # Also fix multi-line {{ ... }} tags just in case
        def join_var_tags(match):
            tag_content = match.group(0)
            joined = re.sub(r'\s+', ' ', tag_content)
            joined = joined.replace('{{', '{{ ').replace('}}', ' }}')
            joined = re.sub(r'{\s+{', '{{', joined)
            joined = re.sub(r'}\s+}', '}}', joined)
            joined = joined.replace('{{ ', '{{ ').replace(' }}', ' }}')
            joined = re.sub(r'\s+', ' ', joined)
            return joined
            
        fixed_content = re.sub(r'{{.*?}}', join_var_tags, fixed_content, flags=re.DOTALL)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"Repaired: {filename}")

print("Successfully repaired all templates.")
