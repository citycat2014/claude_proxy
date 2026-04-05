"""
Background worker for asynchronous database writes.

Uses a queue to buffer API interactions and write them in batches,
reducing database I/O overhead and improving proxy performance.
"""

import queue
import threading
import logging
import time
from datetime import datetime
from typing import Optional, List, Any

from storage.database import Database
from storage.models import Session, Request, ToolCall

logger = logging.getLogger(__name__)


class DatabaseWriteWorker:
    """
    Background worker that batches database writes.

    Interactions are queued and written in batches to reduce I/O overhead.
    """

    def __init__(self, db: Database, batch_size: int = 10, batch_interval: float = 0.1):
        """
        Initialize the write worker.

        Args:
            db: Database instance for writes
            batch_size: Number of items to batch before writing
            batch_interval: Maximum time to wait before flushing batch (seconds)
        """
        self.db = db
        self.batch_size = batch_size
        self.batch_interval = batch_interval

        # Queue for buffering interactions
        self.queue: queue.Queue = queue.Queue(maxsize=1000)

        # Worker thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Batch buffer
        self._batch: List[Any] = []
        self._last_flush = time.time()

        # Stats
        self.items_queued = 0
        self.items_written = 0
        self.batches_written = 0

    def start(self):
        """Start the background worker thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Write worker already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="DBWriteWorker")
        self._thread.start()
        logger.info(f"Write worker started (batch_size={self.batch_size}, interval={self.batch_interval}s)")

    def stop(self, timeout: float = 5.0):
        """
        Stop the worker and flush pending items.

        Args:
            timeout: Maximum time to wait for thread to finish
        """
        if self._thread is None:
            return

        logger.info(f"Stopping write worker... pending items: {self.queue.qsize()} + batch: {len(self._batch)}")

        # Flush any remaining items
        self._flush_batch()

        # Signal stop
        self._stop_event.set()

        # Wait for thread to finish
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            logger.warning("Write worker thread did not terminate cleanly")

        self._thread = None
        logger.info(f"Write worker stopped. Total written: {self.items_written}")

    def enqueue(self, item: Any):
        """
        Add an item to the write queue.

        Args:
            item: Item to write (tuple of session, request, tool_calls)
        """
        try:
            self.queue.put_nowait(item)
            self.items_queued += 1
        except queue.Full:
            # Queue full - write synchronously as fallback
            logger.warning("Write queue full, writing synchronously")
            self._write_item(item)

    def _run(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                # Try to get item with timeout
                try:
                    item = self.queue.get(timeout=0.05)
                    self._batch.append(item)

                    # Flush if batch is full
                    if len(self._batch) >= self.batch_size:
                        self._flush_batch()

                except queue.Empty:
                    # No items - check if we should flush due to interval
                    if self._batch and (time.time() - self._last_flush) > self.batch_interval:
                        self._flush_batch()

            except Exception as e:
                logger.error(f"Error in write worker: {e}")

        # Final flush on exit
        self._flush_batch()

    def _flush_batch(self):
        """Flush the current batch to database."""
        if not self._batch:
            return

        try:
            start = time.time()

            # Write all items in batch
            for item in self._batch:
                self._write_item(item)
                self.items_written += 1

            elapsed_ms = int((time.time() - self._last_flush) * 1000)
            logger.debug(f"Flushed batch of {len(self._batch)} items in {elapsed_ms}ms")

            self.batches_written += 1
            self._batch.clear()
            self._last_flush = time.time()

        except Exception as e:
            logger.error(f"Error flushing batch: {e}")
            # Items remain in batch for retry on next flush

    def _write_item(self, item: tuple):
        """
        Write a single item to database.

        Args:
            item: Tuple of (session, request, tool_calls) or (request, tool_calls)
        """
        try:
            request_data = None
            if len(item) == 3:
                # Full item with session
                session, request, tool_calls = item
                if session:
                    self.db.upsert_session(session)
                self.db.save_request(request)
                for tool_call in tool_calls:
                    self.db.save_tool_call(tool_call)
                request_data = request
            else:
                # Just request and tool calls
                request, tool_calls = item
                self.db.save_request(request)
                for tool_call in tool_calls:
                    self.db.save_tool_call(tool_call)
                request_data = request

            # Broadcast WebSocket event if callback is set
            if self.on_write_callback and request_data:
                self.on_write_callback(request_data)

        except Exception as e:
            logger.error(f"Error writing item: {e}")
            raise  # Re-raise so batch retry doesn't keep failing

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "queue_size": self.queue.qsize(),
            "batch_size": len(self._batch),
            "items_queued": self.items_queued,
            "items_written": self.items_written,
            "batches_written": self.batches_written,
            "pending": self.queue.qsize() + len(self._batch),
        }


# Global worker instance
_worker: Optional[DatabaseWriteWorker] = None


def init_worker(db: Database, batch_size: int = 10, batch_interval: float = 0.1):
    """Initialize the global write worker."""
    global _worker
    _worker = DatabaseWriteWorker(db, batch_size, batch_interval)
    _worker.start()
    return _worker


def get_worker() -> Optional[DatabaseWriteWorker]:
    """Get the global write worker."""
    return _worker


def enqueue_write(item: tuple):
    """Enqueue an item for writing."""
    if _worker:
        _worker.enqueue(item)
    else:
        logger.warning("Write worker not initialized, writing synchronously")
        # Fallback to synchronous write - unpack and write directly
        db = Database()
        if len(item) == 3:
            session, request, tool_calls = item
            if session:
                db.upsert_session(session)
            db.save_request(request)
            for tool_call in tool_calls:
                db.save_tool_call(tool_call)
        else:
            request, tool_calls = item
            db.save_request(request)
            for tool_call in tool_calls:
                db.save_tool_call(tool_call)


def shutdown_worker(timeout: float = 5.0):
    """Shutdown the global write worker."""
    if _worker:
        _worker.stop(timeout=timeout)
