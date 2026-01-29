import logging
import os
from config import OUTPUT_DIR, STATE_FILE, OPENAI_API_KEY
from state_manager import StateManager
from vector_store_manager import VectorStoreManager
from scraper import Scraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main execution entry point.
    
    Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
    """
    state_manager = StateManager(STATE_FILE)
    vector_manager = VectorStoreManager(OPENAI_API_KEY)
    scraper = Scraper(OUTPUT_DIR)
    
    # Initialize Vector Store
    vs_id = vector_manager.get_or_create_vector_store(state_manager)
    
    articles = scraper.fetch_articles(limit=5)
    
    stats = {"added": 0, "updated": 0, "skipped": 0}
    
    for article in articles:
        article_id = article.get('id')
        filepath, content, content_hash = scraper.process_article(article)
        
        if not filepath:
            continue
            
        # Check state
        current_state = state_manager.get_article_state(article_id)
        last_hash = current_state.get("hash")
        
        if last_hash == content_hash and os.path.exists(filepath):
            logging.info(f"Skipping {article_id} (No changes)")
            stats["skipped"] += 1
            continue

        # Save file locally
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        action = "Updated" if last_hash else "Added"
        logging.info(f"{action} local file: {filepath}")
        
        # Upload to OpenAI
        if vs_id:
            file_id = vector_manager.upload_file(filepath)
            if file_id:
                vector_manager.add_file_to_vector_store(vs_id, file_id)
                state_manager.update_article_state(article_id, content_hash, file_id)
                if action == "Updated":
                    stats["updated"] += 1
                else: 
                    stats["added"] += 1
        else:
            # Update state even if no OpenAI (local only mode)
             state_manager.update_article_state(article_id, content_hash, None)
             if action == "Updated":
                 stats["updated"] += 1
             else:
                 stats["added"] += 1

    state_manager.save_state()
    logging.info(f"Job Complete. Stats: {stats}")


def main_test():
    """Main execution entry point.
    
    Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
    """
    vector_manager = VectorStoreManager(OPENAI_API_KEY)
    vector_manager.clear_file_from_storage()
    vector_manager.clear_all_files_from_vector_store("vs_697b2d0fe55c8191838044152526f53a")

if __name__ == "__main__":
    main()
