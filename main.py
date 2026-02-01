import logging
import os
import sys
from config import OUTPUT_DIR, STATE_FILE, OPENAI_API_KEY
from state_manager import StateManager
from vector_store_manager import VectorStoreManager
from scraper import Scraper
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Main execution entry point.
    
    Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
    """
    exit_code = 0
    try:
        logging.info("=" * 60)
        logging.info("Starting OptiBot scraper job")
        logging.info("=" * 60)
        
        state_manager = StateManager()
        vector_manager = VectorStoreManager(OPENAI_API_KEY)
        scraper = Scraper(OUTPUT_DIR)
        
        # Initialize Vector Store
        vs_id = vector_manager.get_or_create_vector_store(state_manager)
        
        articles = scraper.fetch_articles(limit=None)
        
        stats = {"added": 0, "updated": 0, "skipped": 0, "deleted": 0}
        
        # get newly fetch articles ids (empty set if no articles)
        newly_fetched_ids = {str(article.get("id")) for article in articles} if articles else set()
        
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
                        exit_code = 1
                # remove local file if exists
                state_manager.remove_article_state(article_id)
                stats["deleted"] += 1
                logging.info(f"Removed article {article_id} from state.")
        
        # Process articles with enhanced delta detection
        for article in articles:
            article_id = article.get('id')
            filepath, content, content_hash, last_modified = scraper.process_article(article)
            
            if not filepath:
                continue
            
            # Enhanced change detection: check both hash and last_modified
            current_state = state_manager.get_article_state(article_id)
            last_hash = current_state.get("hash")
            stored_last_modified = current_state.get("last_modified")
            
            # Fast path: if last_modified matches and hash matches, skip
            if stored_last_modified and last_modified:
                if stored_last_modified == last_modified and last_hash == content_hash and os.path.exists(filepath):
                    logging.info(f"Skipping {article_id} (No changes - hash and last_modified match)")
                    stats["skipped"] += 1
                    continue
            
            # Fallback: if hash matches and file exists, skip (backward compatibility)
            if last_hash == content_hash and os.path.exists(filepath):
                logging.info(f"Skipping {article_id} (No changes - hash matches)")
                stats["skipped"] += 1
                continue

            # Save file locally
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                logging.error(f"Error saving file {filepath}: {e}")
                exit_code = 1
                continue
            
            action = "Updated" if last_hash else "Added"
            logging.info(f"{action} local file: {filepath}")
            
            # Upload to OpenAI
            if vs_id:
                file_id = vector_manager.upload_file(filepath)
                if file_id:
                    try:
                        vector_manager.add_file_to_vector_store(vs_id, file_id)
                        state_manager.update_article_state(article_id, content_hash, file_id, last_modified)
                        if action == "Updated":
                            stats["updated"] += 1
                        else: 
                            stats["added"] += 1
                    except Exception as e:
                        logging.error(f"Error adding file to vector store: {e}")
                        exit_code = 1
                else:
                    logging.warning(f"Failed to upload file {filepath} to OpenAI")
                    exit_code = 1
            else:
                # Update state even if no OpenAI (local only mode)
                state_manager.update_article_state(article_id, content_hash, None, last_modified)
                if action == "Updated":
                    stats["updated"] += 1
                else:
                    stats["added"] += 1

        # Save state with error handling
        try:
            state_manager.save_state()
        except Exception as e:
            logging.error(f"Error saving state: {e}")
            exit_code = 1
        
        # Log vector store statistics
        # if vs_id:
        #     vector_manager.log_vector_store_stats(vs_id)
        
        logging.info("=" * 60)
        logging.info(f"Job Complete. Stats: {stats}")
        logging.info("=" * 60)
        
        return exit_code
        
    except Exception as e:
        logging.error(f"Fatal error in main: {e}", exc_info=True)
        return 1


def main_test():
    """Main execution entry point.
    
    Orchestrates the scraping, processing, state management, and OpenAI upload workflow.
    """
    bucket_name = os.getenv("BUCKET_NAME")
    bucket_secret_access_key = os.getenv("BUCKET_SECRET_ACCESS_KEY")
    state_key = "state.json"

    s3_client = boto3.client(
        's3',
        region_name='fra1',
        endpoint_url='https://fra1.digitaloceanspaces.com',
        aws_access_key_id=os.getenv("BUCKET_ACCESS_KEY_ID"),
        aws_secret_access_key=bucket_secret_access_key
    )

    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=state_key
        )
        content = response['Body'].read().decode('utf-8')
        if not content.strip():
            return {"articles": {}, "vector_store_id": None}
        print(content)
        return json.loads(content)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logging.info("No existing state in Spaces, starting fresh.")
            return {"articles": {}, "vector_store_id": None}
        logging.error(f"Error loading state from Spaces: {e}")
        return {"articles": {}, "vector_store_id": None}
    except Exception as e:
        logging.warning(f"Error loading state from Spaces: {e}. Starting fresh.")
        return {"articles": {}, "vector_store_id": None}

def clear_everything():
    state_manager = StateManager()
    vector_manager = VectorStoreManager(OPENAI_API_KEY)
    scraper = Scraper(OUTPUT_DIR)

    vector_manager.clear_all_files_from_vector_store('vs_697b2d0fe55c8191838044152526f53a')
    vector_manager.clear_file_from_storage()
    state_manager.remove_all_article_states()
    scraper.clear_output_directory()
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
