import os
import requests
from datetime import datetime

# Config from GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 1. Map Notion Dropdown values to your folder paths
# The key is the exact text in your Notion "Topic for GitHub" column.
# The value is the folder path inside the "topics/" directory.
TOPIC_MAP = {
    "Information Theory": "foundations-intelligence/information-theory",
    "Stochastic Processes": "foundations-intelligence/stochastic-processes",
    "Optimization Theory": "foundations-intelligence/optimization-theory",
    "Causality": "foundations-intelligence/causality",
    "Embeddings": "representational-modeling/embeddings",
    "Geometric DL": "representational-modeling/geometric-dl",
    "Multimodal": "representational-modeling/multimodal",
    "Interpretability": "representational-modeling/interpretability",
    "Sequential Decision Making": "dynamics-evolution/decision-making",
    "Generative Design": "dynamics-evolution/generative-design",
    "Trajectory Inference": "dynamics-evolution/trajectory-inference",
    "Perturbation Prediction": "dynamics-evolution/perturbation",
    "Knowledge Synthesis": "applied-medicine/knowledge-synthesis",
    "Structural Omics": "applied-medicine/omics",
    "Automated Discovery": "applied-medicine/automated-discovery",
    "Robustness & Safety": "applied-medicine/safety"
}

def get_favorited_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    query = {
        "filter": {
            "property": "Favorite",
            "checkbox": {"equals": True}
        }
    }
    res = requests.post(url, headers=headers, json=query)
    return res.json().get("results", [])

def update_notion_page(page_id):
    # Uncheck the box so we don't sync it again
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"properties": {"Favorite": {"checkbox": False}}}
    requests.patch(url, headers=headers, json=data)

def extract_text(property_data, default=""):
    """Helper function to safely extract text from Notion's nested JSON."""
    if not property_data:
        return default
    
    prop_type = property_data.get("type")
    if prop_type == "title":
        return property_data["title"]["plain_text"] if property_data["title"] else default
    elif prop_type == "rich_text":
        return property_data["rich_text"]["plain_text"] if property_data["rich_text"] else default
    elif prop_type == "url":
        return property_data.get("url") or default
    elif prop_type == "select":
        return property_data["select"]["name"] if property_data.get("select") else default
    
    return default

def sync():
    pages = get_favorited_pages()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    for page in pages:
        props = page["properties"]
        
        # 2. Extract properties based on your exact Notion column names
        # Note: If your Notion columns are named differently, change the string keys below!
        topic_key = extract_text(props.get("Topic for GitHub"), default="Uncategorized")
        title = extract_text(props.get("Paper Title"), default="Untitled Paper")
        doi = extract_text(props.get("DOI"), default="No DOI provided")
        citation = extract_text(props.get("Full Citation"), default="No citation provided")
        summary = extract_text(props.get("Summary"), default="No summary provided.")
        
        # 3. Determine the target directory
        folder_path = TOPIC_MAP.get(topic_key)
        if not folder_path:
            print(f"⚠️ Topic '{topic_key}' not found in TOPIC_MAP. Skipping {title}.")
            continue
            
        target_dir = f"topics/{folder_path}"
        os.makedirs(target_dir, exist_ok=True)
        readme_path = f"{target_dir}/README.md"
        
        # 4. Format the Markdown entry
        new_entry = f"""## {today_date}
### {title}
#### DOI: <{doi}>
**Citation:** {citation}

**Summary:** {summary}

---

"""
        # 5. Prepend to the existing README (or create if it doesn't exist)
        existing_content = ""
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
                
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_entry + existing_content)
            
        print(f"✅ Synced: {title} -> {target_dir}")
        
        # 6. Uncheck the Notion Favorite box
        update_notion_page(page["id"])

if __name__ == "__main__":
    sync()