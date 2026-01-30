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
    
    articles = scraper.fetch_articles(limit=None)
    
    stats = {"added": 0, "updated": 0, "skipped": 0, "deleted": 0}
    
    # get newly fetch articles ids
    newly_fetched_ids = {str(article.get("id")) for article in articles}
    
    # get ids from state.json
    stored_ids = set(state_manager.get_all_article_ids())
    
    ids_to_delete = stored_ids - newly_fetched_ids
    
    if ids_to_delete:
        logging.info(f"Deleting {len(ids_to_delete)} articles no longer present in source.")
        for article_id in ids_to_delete:
            # get openai_file_id
            article_state = state_manager.get_article_state(article_id)
            openai_file_id = article_state.get("openai_file_id")
            if vs_id and openai_file_id:
                try:
                    vector_manager.remove_file_from_vector_store(vs_id, openai_file_id)
                    vector_manager.remove_file_from_openai(openai_file_id)
                    logging.info(f"Removed file {openai_file_id} from Vector Store and OpenAI.")
                except Exception as e:
                    logging.error(f"Error removing file {openai_file_id}: {e}")
            # remove local file if exists
            state_manager.remove_article_state(article_id)
            stats["deleted"] += 1
            logging.info(f"Removed article {article_id} from state.")            
    
    
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
    scraper = Scraper(OUTPUT_DIR)
    articles = scraper.fetch_articles(limit=None)
    print(f"Fetched {len(articles)} articles.")

if __name__ == "__main__":
    main()
