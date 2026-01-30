import logging
from openai import OpenAI

from state_manager import StateManager
class VectorStoreManager:
    """Handles interactions with OpenAI's Vector Store API."""

    def __init__(self, api_key):
        """Initializes the VectorStoreManager.

        Args:
            api_key (str): The OpenAI API key.
        """
        self.client = OpenAI(api_key=api_key) if api_key else None
        if not self.client:
            logging.warning("OpenAI API Key not found. OpenAI integration disabled.")

    def get_or_create_vector_store(self, state_manager: StateManager, name="OptiBot Knowledge Base"):
        """Retrieves an existing Vector Store or creates a new one if not found.

        Args:
            state_manager (StateManager): The state manager to retrieve/save the stored ID.
            name (str): The name for the new Vector Store if creation is needed.

        Returns:
            str: The Vector Store ID.
        """
        if not self.client: return None
        
        vs_id = state_manager.get_vector_store_id()
        if vs_id:
            try:
                # Validate it exists
                self.client.vector_stores.retrieve(
                    vector_store_id=vs_id)
                logging.info(f"Using existing Vector Store: {vs_id}")
                return vs_id
            except Exception:
                logging.warning(f"Saved Vector Store {vs_id} not found/accessible. Creating new one.")
        
        try:
            vs = self.client.vector_stores.create(
                name = name,
                expires_after={
                    "anchor":"last_active_at",
                    "days": 20
                }
            )
            vs_id = vs.id
            state_manager.set_vector_store_id(vs_id)
            logging.info(f"Created new Vector Store: {vs_id}")
            return vs_id
        except Exception as e:
            logging.error(f"Failed to create Vector Store: {e}")
            return None

    def upload_file(self, filepath):
        """Uploads a file to OpenAI for 'assistants' purpose.
        
        Args:
            filepath (str): The path to the local file to upload.

        Returns:
            str: The OpenAI File ID if successful, else None.
        """
        if not self.client: return "mock_file_id"
        
        try:
            with open(filepath, "rb") as file_stream:
                file_obj = self.client.files.create(
                    file=file_stream,
                    purpose="assistants"
                )
            logging.info(f"Uploaded file {filepath} to OpenAI: {file_obj.id}")
            return file_obj.id
        except Exception as e:
            logging.error(f"Failed to upload {filepath}: {e}")
            return None

    def add_file_to_vector_store(self, vector_store_id, file_id):
        """Links an uploaded file to a Vector Store and waits for processing to log status.

        Args:
            vector_store_id (str): The ID of the Vector Store.
            file_id (str): The ID of the uploaded file.
        """
        if not self.client or not vector_store_id or not file_id: return
        
        try:
            # Link file to Vector Store
            vs_file  = self.client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            if vs_file.status == "completed":
                logging.info(f"Successfully linked and embedded file {file_id} in Vector Store {vector_store_id}. Status: {vs_file.status}")
            else:
                 logging.warning(f"File {file_id} added to Vector Store {vector_store_id} but status is: {vs_file.status}. Error: {vs_file.last_error}")

        except Exception as e:
            logging.error(f"Failed to link file {file_id}: {e}")
    
    def clear_all_files_from_vector_store(self, vector_store_id):
        """Deletes all files from the specified Vector Store.

        Args:
            vector_store_id (str): The ID of the Vector Store.
        """
        if not self.client or not vector_store_id: return
        
        try:
            files = self.client.vector_stores.files.list(
                vector_store_id=vector_store_id
            )
            for file in files.data:
                self.client.vector_stores.files.delete(
                    vector_store_id=vector_store_id,
                    file_id=file.id
                )
                logging.info(f"Deleted file {file.id} from Vector Store {vector_store_id}.")
        except Exception as e:
            logging.error(f"Failed to clear files from Vector Store {vector_store_id}: {e}")
    def remove_file_from_openai(self, file_id):
        """Deletes a file from OpenAI storage.

        Args:
            file_id (str): The ID of the file to delete.
        """
        if not self.client or not file_id: return
        
        try:
            self.client.files.delete(
                file_id=file_id
            )
            logging.info(f"Deleted file {file_id} from OpenAI storage.")
        except Exception as e:
            logging.error(f"Failed to delete file {file_id} from OpenAI storage: {e}")
    def remove_file_from_vector_store(self, vector_store_id, file_id):
        """Deletes a file from the specified Vector Store.

        Args:
            vector_store_id (str): The ID of the Vector Store.
            file_id (str): The ID of the file to delete.
        """
        if not self.client or not vector_store_id or not file_id: return
        
        try:
            self.client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            logging.info(f"Deleted file {file_id} from Vector Store {vector_store_id}.")
        except Exception as e:
            logging.error(f"Failed to delete file {file_id} from Vector Store {vector_store_id}: {e}")
    def clear_file_from_storage(self):
        """Deletes all files from OpenAI storage.

        Args:
            file_id (str): The ID of the file to delete.
        """
        if not self.client : return
        
        # get all files and delete
        try:
            files = self.client.files.list()
            for file in files.data:
                self.client.files.delete(
                    file_id=file.id
                )
                logging.info(f"Deleted file {file.id} from OpenAI storage.")
        except Exception as e:
            logging.error(f"Failed to clear files from OpenAI storage: {e}")