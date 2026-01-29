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
            logging.warning(f"State file {self.filepath} is corrupted. Resetting state.")
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

    def update_article_state(self, article_id, file_hash, openai_file_id=None):
        """Updates the state for an article.
        
        Args:
            article_id (int|str): The unique identifier of the article.
            file_hash (str): The MD5 hash of the article content.
            openai_file_id (str, optional): The ID of the file uploaded to OpenAI.
        """
        self.state["articles"][str(article_id)] = {
            "hash": file_hash,
            "openai_file_id": openai_file_id,
            "updated_at": "now" # In real app use datetime
        }
    
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
