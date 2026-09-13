import json
import uuid
import os
from pathlib import Path
from datetime import datetime, timedelta
import threading


class SessionManager:
    """
    Handles unique AI-agent sessions and persistent JSON session state.

    Features:
    - Creates unique sessions
    - Stores session state in JSON files
    - 24-hour rolling session expiry
    - Thread-safe saving
    - Windows-safe session file replacement
    """

    def __init__(self, sessions_dir="sessions", ttl_hours=24):
        self.sessions_dir = Path(sessions_dir)

        # Create sessions folder if it does not exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.ttl_hours = ttl_hours

        # Prevent simultaneous session writes
        self.lock = threading.Lock()

    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------

    def _now(self):
        """Return the current timezone-aware datetime."""
        return datetime.now().astimezone()

    # ---------------------------------------------------------
    # SESSION FILE
    # ---------------------------------------------------------

    def _session_path(self, session_id):
        """Return the JSON file path for a session."""
        return self.sessions_dir / f"{session_id}.json"

    # ---------------------------------------------------------
    # CREATE SESSION
    # ---------------------------------------------------------

    def create_session(self, initial_state=None):
        """Create a new unique AI-agent session."""

        session_id = uuid.uuid4().hex

        now = self._now()
        expires_at = now + timedelta(hours=self.ttl_hours)

        default_state = {
            "history": [],
            "summary": "",
            "scratchpad": {},
            "last_tool_result": None,
            "plan_step": 0,
            "preferences": {},
            "query_count": 0
        }

        session = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "state": initial_state if initial_state is not None else default_state
        }

        self.save_session(
            session_id,
            session["state"]
        )

        return session

    # ---------------------------------------------------------
    # LOAD SESSION
    # ---------------------------------------------------------

    def load_session(self, session_id):
        """Load an existing session if it has not expired."""

        path = self._session_path(session_id)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as file:
                session = json.load(file)

            # Validate required session information
            expires_at = datetime.fromisoformat(
                session["expires_at"]
            )

            # Check session expiration
            if self._now() >= expires_at:
                self.delete_session(session_id)
                return None

            return session

        except (
            json.JSONDecodeError,
            KeyError,
            ValueError,
            OSError
        ):
            return None

    # ---------------------------------------------------------
    # SAVE SESSION
    # ---------------------------------------------------------

    def save_session(self, session_id, state):
        """
        Save session state safely.

        Uses a temporary file first and then replaces
        the real session file.

        Includes Windows-specific handling for
        temporary file locking.
        """

        path = self._session_path(session_id)

        existing = None

        # Load existing session metadata
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as file:
                    existing = json.load(file)

            except (
                json.JSONDecodeError,
                OSError
            ):
                existing = None

        now = self._now()

        # Preserve original creation time
        if existing:
            created_at = existing.get(
                "created_at",
                now.isoformat()
            )
        else:
            created_at = now.isoformat()

        session = {
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": now.isoformat(),
            "expires_at": (
                now + timedelta(hours=self.ttl_hours)
            ).isoformat(),
            "state": state
        }

        # Temporary file
        temp_path = path.with_suffix(".tmp")

        # -----------------------------------------------------
        # THREAD-SAFE SAVE
        # -----------------------------------------------------

        with self.lock:

            try:
                # Write complete session to temporary file
                with open(
                    temp_path,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        session,
                        file,
                        indent=2,
                        ensure_ascii=False
                    )

                # -------------------------------------------------
                # NORMAL REPLACEMENT
                # -------------------------------------------------

                try:
                    os.replace(
                        temp_path,
                        path
                    )

                except PermissionError:

                    # -------------------------------------------------
                    # WINDOWS FALLBACK
                    # -------------------------------------------------
                    #
                    # Windows can temporarily lock a JSON file
                    # during rapid Streamlit reruns.
                    #

                    try:

                        if path.exists():
                            path.unlink()

                        os.replace(
                            temp_path,
                            path
                        )

                    except PermissionError as e:

                        print(
                            f"⚠️ Session file is temporarily locked: {e}"
                        )

                        # Clean up temporary file
                        try:
                            if temp_path.exists():
                                temp_path.unlink()
                        except Exception:
                            pass

            except OSError as e:

                print(
                    f"⚠️ Session save failed: {e}"
                )

                # Clean up temporary file
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except Exception:
                    pass

    # ---------------------------------------------------------
    # DELETE SESSION
    # ---------------------------------------------------------

    def delete_session(self, session_id):
        """Delete a session file."""

        path = self._session_path(session_id)

        try:

            if path.exists():
                path.unlink()

        except OSError as e:

            print(
                f"⚠️ Could not delete session {session_id}: {e}"
            )

    # ---------------------------------------------------------
    # CHECK SESSION
    # ---------------------------------------------------------

    def session_exists(self, session_id):
        """Return True if the session exists and is not expired."""

        return self.load_session(session_id) is not None


# -------------------------------------------------------------
# SIMPLE TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    print("Testing SessionManager...")

    manager = SessionManager()

    # Create session
    session = manager.create_session()

    session_id = session["session_id"]

    print(f"✅ Session created: {session_id}")

    # Load session
    loaded = manager.load_session(session_id)

    if loaded:
        print("✅ Session loaded successfully")
    else:
        print("❌ Session loading failed")

    # Update session
    state = loaded["state"]

    state["query_count"] = 1
    state["history"].append({
        "role": "user",
        "content": "What is a headache?"
    })

    manager.save_session(
        session_id,
        state
    )

    print("✅ Session updated successfully")

    # Load again
    updated = manager.load_session(session_id)

    if updated:
        print(
            f"✅ Query count: "
            f"{updated['state']['query_count']}"
        )
    else:
        print("❌ Updated session could not be loaded")

    print("✅ SessionManager test completed")