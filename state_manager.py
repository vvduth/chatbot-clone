import datetime
import os
import json
import logging
class StateManager:
    """Manages the state of processed articles and the vector store ID."""

    def __init__(self, state_file):
        """Initializes the StateManager.
        
        Args:
            state_file (str): The path to the JSON file where state is stored.
        """
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self):
        """Loads the state from the JSON file. 
        
        Returns:
            dict: The loaded state or a default empty state if the file doesn't exist.
        """
        if not os.path.exists(self.state_file):
            return {"articles": {}, "vector_store_id": None}
        try:
            with open(self.state_file, 'r', encoding="utf-8") as f:
                content = f.read().strip()
                if not content: 
                    return {"articles": {}, "vector_store_id": None}
                return json.loads(content)
        except Exception:
            logging.warning(f"State file {self.state_file} is corrupted. Resetting state.")
            return {"articles": {}, "vector_store_id": None}

    def save_state(self):
        """Saves the current state to the JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_article_state(self, article_id):
        """Retrieves the state for a specific article.
        
        Args:
           article_id (int|str): The unique identifier of the article.
           
        Returns:
           dict: The state dictionary for the article (e.g. hash, openai_file_id).
        """
        return self.state["articles"].get(str(article_id), {})

    def update_article_state(self, article_id, file_hash, openai_file_id=None, last_modified=None):
        """Updates the state for an article.
        
        Args:
            article_id (int|str): The unique identifier of the article.
            file_hash (str): The MD5 hash of the article content.
            openai_file_id (str, optional): The ID of the file uploaded to OpenAI.
            last_modified (str, optional): ISO format timestamp from API (Last-Modified header).
        """
        self.state["articles"][str(article_id)] = {
            "hash": file_hash,
            "openai_file_id": openai_file_id,
            "last_modified": last_modified,
            "updated_at": datetime.datetime.now().isoformat()
        }
    
    def needs_update(self, article_id, content_hash, last_modified):
        """Checks if an article needs to be updated based on hash and last_modified timestamp.
        
        Args:
            article_id (int|str): The unique identifier of the article.
            content_hash (str): The MD5 hash of the current article content.
            last_modified (str): ISO format timestamp from API (Last-Modified header).
        
        Returns:
            bool: True if article needs update, False if it can be skipped.
        """
        current_state = self.get_article_state(article_id)
        
        # If no state exists, article is new
        if not current_state:
            return True
        
        stored_hash = current_state.get("hash")
        stored_last_modified = current_state.get("last_modified")
        
        # Fast path: if last_modified matches and hash matches, skip
        if stored_last_modified and last_modified:
            if stored_last_modified == last_modified and stored_hash == content_hash:
                return False
        
        # If hash matches but last_modified differs, still check hash (content might be same)
        if stored_hash == content_hash:
            return False
        
        # Otherwise, needs update
        return True
    
    def get_vector_store_id(self):
        """Gets the stored OpenAI Vector Store ID.

        Returns:
            str: The Vector Store ID, or None if not set.
        """
        return self.state.get("vector_store_id")

    def set_vector_store_id(self, vs_id):
        """Sets and saves the OpenAI Vector Store ID.

        Args:
            vs_id (str): The Vector Store ID to save.
        """
        self.state["vector_store_id"] = vs_id
    def get_all_article_ids(self):
        """Retrieves all stored article IDs.

        Returns:
            list: A list of all article IDs in the state.
        """
        return list(self.state["articles"].keys())
    def remove_all_article_states(self):
        """Removes all article states and saves to file."""
        self.state["articles"] = {}
        self.save_state()
        
        
    def remove_article_state(self, article_id):
        """Removes the state entry for a specific article.

        Args:
            article_id (int|str): The unique identifier of the article to remove.
        """
        if str(article_id) in self.state["articles"]:
            del self.state["articles"][str(article_id)]
