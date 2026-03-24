import os
import requests  # type: ignore
from datetime import datetime

# Config from GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_favorited_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    # Grab rows where 'Favorite' is True AND 'On GitHub' is False
    query = {
        "filter": {
            "and": [
                {
                    "property": "Favorite",
                    "checkbox": {"equals": True}
                },
                {
                    "property": "On GitHub",
                    "checkbox": {"equals": False}
                }
            ]
        }
    }
    res = requests.post(url, headers=headers, json=query)
    return res.json().get("results", [])

def update_notion_page(page_id):
    # Check the "On GitHub" box instead of touching "Favorite"
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"properties": {"On GitHub": {"checkbox": True}}}
    requests.patch(url, headers=headers, json=data)

def extract_text(property_data, default=""):
    """Safely extract text from Notion's nested JSON."""
    if not property_data:
        return default
    
    prop_type = property_data.get("type")
    
    if prop_type == "title":
        text_list = property_data.get("title", [])
        return "".join([t.get("plain_text", "") for t in text_list]) if text_list else default
        
    elif prop_type == "rich_text":
        text_list = property_data.get("rich_text", [])
        return "".join([t.get("plain_text", "") for t in text_list]) if text_list else default
        
    elif prop_type == "url":
        return property_data.get("url") or default
        
    elif prop_type == "select":
        select_data = property_data.get("select")
        return select_data.get("name") if select_data else default
    
    return default

def sync():
    pages = get_favorited_pages()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    for page in pages:
        props = page["properties"]
        
        # Extract properties
        folder_path = extract_text(props.get("Topic for GitHub"), default="")
        title = extract_text(props.get("Paper Title"), default="Untitled Paper")
        doi = extract_text(props.get("DOI"), default="No DOI provided")
        citation = extract_text(props.get("Full Citation"), default="No citation provided")
        summary = extract_text(props.get("Summary"), default="No summary provided.")
        
        # Skip if there's no folder path selected in Notion
        if not folder_path:
            print(f"⚠️ No Topic assigned in Notion. Skipping {title}.")
            continue
            
        # Target directory uses the Notion dropdown string directly
        target_dir = f"topics/{folder_path}"
        os.makedirs(target_dir, exist_ok=True)
        readme_path = f"{target_dir}/README.md"
        
        # Format the Markdown entry
        new_entry = f"""## {today_date}
### {title}
#### DOI: <{doi}>
**Citation:** {citation}

**Summary:** {summary}

---

"""
        # Prepend to the existing README
        existing_content = ""
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
                
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_entry + existing_content)
            
        print(f"✅ Synced: {title} -> {target_dir}")
        
        # Check the "On GitHub" box so it doesn't duplicate next time
        update_notion_page(page["id"])

if __name__ == "__main__":
    sync()