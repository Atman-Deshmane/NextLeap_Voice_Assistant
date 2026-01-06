"""
GitHub Sync Service for Cloud Deployment Persistence

This module handles syncing store.json to GitHub for data persistence
on ephemeral cloud platforms like Render.
"""

import os
import threading
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Configuration from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "")  # e.g., "github.com/user/repo.git"

# Global repo reference
_repo = None


def setup_git():
    """
    Initialize the local git repository and configure authentication.
    Should be called once at app startup.
    """
    global _repo
    
    if not GITHUB_TOKEN or not GITHUB_REPO_URL:
        logger.warning("⚠️ Git sync disabled: GITHUB_TOKEN or GITHUB_REPO_URL not set")
        return False
    
    try:
        import git
        
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Initialize repo object
        _repo = git.Repo(project_root)
        
        # Configure git user for commits
        with _repo.config_writer() as config:
            config.set_value("user", "name", "AdvisorBot")
            config.set_value("user", "email", "bot@nextleap.app")
        
        # Update remote URL with token for authentication
        # Format: https://{TOKEN}@github.com/user/repo.git
        repo_url_no_https = GITHUB_REPO_URL.replace("https://", "").replace("http://", "")
        authenticated_url = f"https://{GITHUB_TOKEN}@{repo_url_no_https}"
        
        # Update or create origin remote
        try:
            origin = _repo.remote("origin")
            origin.set_url(authenticated_url)
        except Exception:
            _repo.create_remote("origin", authenticated_url)
        
        logger.info("✅ Git sync initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Git setup failed: {e}")
        return False


def pull_latest():
    """
    Pull the latest store.json from GitHub to restore state.
    Should be called at app startup after setup_git().
    """
    global _repo
    
    if not _repo:
        logger.warning("⚠️ Git sync not initialized, skipping pull")
        return False
    
    try:
        origin = _repo.remote("origin")
        
        # Fetch and pull from main/master branch
        try:
            origin.pull("main")
            logger.info("✅ Pulled latest from main branch")
        except Exception:
            try:
                origin.pull("master")
                logger.info("✅ Pulled latest from master branch")
            except Exception as e:
                logger.warning(f"⚠️ Pull failed (may be first run): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Git pull failed: {e}")
        return False


def push_updates():
    """
    Push store.json changes to GitHub in a background thread.
    Non-blocking to prevent slowing down the booking process.
    """
    def _push_task():
        global _repo
        
        if not _repo:
            logger.warning("⚠️ Git sync not initialized, skipping push")
            return
        
        try:
            # Path to store.json
            store_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "store.json"
            )
            
            # Check if store.json exists
            if not os.path.exists(store_path):
                logger.warning("⚠️ store.json not found, skipping push")
                return
            
            # Add store.json to index (force=True to bypass .gitignore)
            _repo.index.add(["store.json"], force=True)
            
            # Check if there are changes to commit
            if _repo.is_dirty() or len(_repo.index.diff("HEAD")) > 0:
                # Create commit with timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"💾 Auto-save: {timestamp}"
                
                _repo.index.commit(commit_message)
                logger.info(f"✅ Committed: {commit_message}")
                
                # Push to origin
                origin = _repo.remote("origin")
                try:
                    origin.push("main")
                    logger.info("✅ Pushed to main branch")
                except Exception:
                    try:
                        origin.push("master")
                        logger.info("✅ Pushed to master branch")
                    except Exception as e:
                        logger.error(f"❌ Push failed: {e}")
            else:
                logger.debug("No changes to push")
                
        except Exception as e:
            logger.error(f"❌ Git push failed: {e}")
    
    # Run in background thread to avoid blocking
    thread = threading.Thread(target=_push_task, daemon=True)
    thread.start()
