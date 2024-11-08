# core/event_system.py
from typing import Dict, Set, Callable, Any
from queue import Queue
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    """Event data structure"""
    type: str
    data: Any
    source: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class EventSystem:
    """
    Event system for inter-module communication
    Handles event publishing and subscription
    """
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._event_queue: Queue = Queue()
        self._running = False
        self._thread = None
        self.logger = logging.getLogger("EventSystem")
        
        # Track event statistics
        self._event_counts: Dict[str, int] = {}
        self._last_event_time: Dict[str, datetime] = {}

    def start(self):
        """Start the event processing thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_events, daemon=True)
        self._thread.start()
        self.logger.info("Event system started")

    def stop(self):
        """Stop the event processing thread"""
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        self.logger.info("Event system stopped")

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """
        Subscribe to an event type
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(callback)
        self.logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """
        Unsubscribe from an event type
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].discard(callback)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
        self.logger.debug(f"Unsubscribed from event: {event_type}")

    def publish(self, event: Event):
        """
        Publish an event to all subscribers
        Args:
            event: Event to publish
        """
        self._event_queue.put(event)
        
        # Update statistics
        self._event_counts[event.type] = self._event_counts.get(event.type, 0) + 1
        self._last_event_time[event.type] = event.timestamp

    def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                if not self._event_queue.empty():
                    event = self._event_queue.get()
                    self._dispatch_event(event)
                else:
                    time.sleep(0.001)  # Small sleep to prevent CPU spinning
            except Exception as e:
                self.logger.error(f"Error processing event: {str(e)}")

    def _dispatch_event(self, event: Event):
        """
        Dispatch event to all subscribers
        Args:
            event: Event to dispatch
        """
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event callback: {str(e)}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get event system statistics"""
        return {
            "event_counts": self._event_counts.copy(),
            "last_event_times": self._last_event_time.copy(),
            "subscriber_counts": {
                event_type: len(subscribers)
                for event_type, subscribers in self._subscribers.items()
            },
            "queue_size": self._event_queue.qsize()
        }

    def clear_statistics(self):
        """Clear event statistics"""
        self._event_counts.clear()
        self._last_event_time.clear()

# Common event types
class EventTypes:
    """Common event types used in the system"""
    # Market Data Events
    PRICE_UPDATE = "PRICE_UPDATE"
    ORDER_BOOK_UPDATE = "ORDER_BOOK_UPDATE"
    TRADE_UPDATE = "TRADE_UPDATE"
    
    # Trading Events
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_UPDATE = "POSITION_UPDATE"
    
    # System Events
    MODULE_INITIALIZED = "MODULE_INITIALIZED"
    MODULE_ERROR = "MODULE_ERROR"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    STATE_CHANGED = "STATE_CHANGED"
    
    
    # Analysis Events
    INDICATOR_UPDATE = "INDICATOR_UPDATE"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    
    # GUI Events
    GUI_UPDATE = "GUI_UPDATE"
    USER_ACTION = "USER_ACTION"

    CONNECTION_STATUS = "CONNECTION_STATUS"

    BALANCE_UPDATE = "BALANCE_UPDATE"

# Global event system instance
event_system = EventSystem()