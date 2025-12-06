import wikipedia
from langchain_core.tools import tool
import requests
from typing import Optional

@tool
def search_wikipedia_images(query: str) -> str:
    """
    Search Wikipedia for a page related to the query and return a list of image URLs found on that page.
    Useful for finding historical photographs or context images.
    """
    print(f"  🖼️ Tool Call: Searching Wikipedia images for '{query}'...")
    try:
        # Search for pages
        search_results = wikipedia.search(query)
        if not search_results:
            return "No Wikipedia pages found."
            
        # Get the first result's page
        page_title = search_results[0]
        try:
            page = wikipedia.page(page_title, auto_suggest=False)
        except wikipedia.DisambiguationError as e:
            # If disambiguation, try the first option
            page = wikipedia.page(e.options[0], auto_suggest=False)
        except wikipedia.PageError:
            return f"Page '{page_title}' not found."
            
        images = page.images
        
        # Filter images (avoid SVGs, small icons, etc if possible, but for now just return list)
        valid_images = [img for img in images if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # Limit to top 5
        return f"Found images on page '{page.title}':\n" + "\n".join(valid_images[:5])
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

