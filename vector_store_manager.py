import logging
import time
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

    def add_file_to_vector_store(self, vector_store_id, file_id, wait_for_completion=True, max_wait_seconds=60):
        """Links an uploaded file to a Vector Store and waits for processing to log status.

        Args:
            vector_store_id (str): The ID of the Vector Store.
            file_id (str): The ID of the uploaded file.
            wait_for_completion (bool): Whether to wait for embedding to complete.
            max_wait_seconds (int): Maximum seconds to wait for completion.

        Returns:
            dict: File information including chunk count if available, None on error.
        """
        if not self.client or not vector_store_id or not file_id: return None
        
        try:
            # Link file to Vector Store
            vs_file = self.client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            
            # Wait for processing to complete if requested
            if wait_for_completion and vs_file.status != "completed":
                start_time = time.time()
                while vs_file.status not in ("completed", "failed", "cancelled"):
                    if time.time() - start_time > max_wait_seconds:
                        logging.warning(f"Timeout waiting for file {file_id} to complete embedding")
                        break
                    time.sleep(2)  # Poll every 2 seconds
                    try:
                        vs_file = self.client.vector_stores.files.retrieve(
                            vector_store_id=vector_store_id,
                            file_id=file_id
                        )
                    except Exception as e:
                        logging.warning(f"Error checking file status: {e}")
                        break
            
            # Log file and chunk information
            file_info = {
                "file_id": file_id,
                "status": vs_file.status
            }
            
            # Try to get chunk count from the file object
            chunk_count = None
            if hasattr(vs_file, "chunk_counts"):
                if isinstance(vs_file.chunk_counts, dict):
                    chunk_count = vs_file.chunk_counts.get("total")
                elif hasattr(vs_file.chunk_counts, "total"):
                    chunk_count = vs_file.chunk_counts.total
            
            file_info["chunk_count"] = chunk_count
            
            if vs_file.status == "completed":
                chunk_info = ""
                if chunk_count is not None:
                    chunk_info = f" with {chunk_count} chunk(s)"
                logging.info(f"Successfully linked and embedded file {file_id} in Vector Store {vector_store_id}{chunk_info}. Status: {vs_file.status}")
            else:
                error_msg = ""
                if hasattr(vs_file, 'last_error') and vs_file.last_error:
                    error_msg = f". Error: {vs_file.last_error}"
                logging.warning(f"File {file_id} added to Vector Store {vector_store_id} but status is: {vs_file.status}{error_msg}")
            
            return file_info

        except Exception as e:
            logging.error(f"Failed to link file {file_id}: {e}")
            return None
    
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
    
    def get_vector_store_stats(self, vector_store_id):
        """Retrieves statistics about files and chunks in the vector store.

        Args:
            vector_store_id (str): The ID of the Vector Store.

        Returns:
            dict: Statistics with 'file_count' and 'total_chunks' (if available), None on error.
        """
        if not self.client or not vector_store_id:
            return None
        
        try:
            # Get vector store information
            vs = self.client.vector_stores.retrieve(vector_store_id=vector_store_id)
            
            # List all files in the vector store
            files = self.client.vector_stores.files.list(vector_store_id=vector_store_id)
            file_count = len(files.data) if hasattr(files, 'data') else 0
            
            # Try to get chunk counts from vector store metadata
            total_chunks = None
            if hasattr(vs, 'file_counts') and vs.file_counts:
                # OpenAI API may provide chunk counts in file_counts
                if isinstance(vs.file_counts, dict):
                    total_chunks = vs.file_counts.get('total_chunks')
                elif hasattr(vs.file_counts, 'total_chunks'):
                    total_chunks = vs.file_counts.total_chunks
            
            # If not available from vector store, try to sum from individual files
            if total_chunks is None and file_count > 0:
                try:
                    chunk_sum = 0
                    files_with_chunks = 0
                    for file in files.data:
                        # Only check completed files
                        if hasattr(file, 'status') and file.status != 'completed':
                            continue
                        # Retrieve file details to get chunk count
                        try:
                            file_detail = self.client.vector_stores.files.retrieve(
                                vector_store_id=vector_store_id,
                                file_id=file.id
                            )
                            chunk_count = None
                            if hasattr(file_detail, 'chunk_counts'):
                                if isinstance(file_detail.chunk_counts, dict):
                                    chunk_count = file_detail.chunk_counts.get('total')
                                elif hasattr(file_detail.chunk_counts, 'total'):
                                    chunk_count = file_detail.chunk_counts.total
                            
                            if chunk_count:
                                chunk_sum += chunk_count
                                files_with_chunks += 1
                        except Exception:
                            # Skip files we can't retrieve details for
                            continue
                    
                    if chunk_sum > 0:
                        total_chunks = chunk_sum
                        if files_with_chunks < file_count:
                            logging.debug(f"Retrieved chunk counts for {files_with_chunks} of {file_count} files")
                except Exception as e:
                    logging.debug(f"Could not retrieve chunk counts from individual files: {e}")
            
            stats = {
                "file_count": file_count,
                "total_chunks": total_chunks
            }
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get vector store statistics: {e}")
            return None
    
    def log_vector_store_stats(self, vector_store_id):
        """Logs statistics about the vector store (file count and chunk count).

        Args:
            vector_store_id (str): The ID of the Vector Store.
        """
        if not vector_store_id:
            logging.info("Vector Store stats: No vector store ID available")
            return
        
        stats = self.get_vector_store_stats(vector_store_id)
        if stats:
            file_count = stats.get("file_count", 0)
            total_chunks = stats.get("total_chunks")
            
            if total_chunks is not None:
                logging.info(f"Vector Store {vector_store_id} contains {file_count} file(s) with {total_chunks} total chunk(s) embedded")
            else:
                logging.info(f"Vector Store {vector_store_id} contains {file_count} file(s) (chunk count unavailable)")
        else:
            logging.warning(f"Could not retrieve statistics for Vector Store {vector_store_id}")