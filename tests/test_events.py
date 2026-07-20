from aiforge.events.bus import Event, EventBus, EventType


def test_subscribe_and_emit():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.CUSTOM, lambda e: received.append(e))
    bus.emit(EventType.CUSTOM, {"x": 1})
    assert len(received) == 1
    assert received[0].data["x"] == 1


def test_wildcard_and_unsubscribe():
    bus = EventBus()
    seen = []
    unsub = bus.subscribe("*", lambda e: seen.append(e.type))
    bus.emit(EventType.TOOL_START)
    unsub()
    bus.emit(EventType.TOOL_END)
    assert seen == [EventType.TOOL_START]


def test_history_filtering():
    bus = EventBus()
    bus.emit(EventType.AGENT_START)
    bus.emit(EventType.TOOL_START)
    bus.emit(EventType.AGENT_END)
    assert len(bus.history()) == 3
    assert len(bus.history(EventType.AGENT_START)) == 1


def test_handler_error_isolated():
    bus = EventBus()
    calls = []

    def boom(_):
        raise ValueError("nope")

    bus.subscribe(EventType.CUSTOM, boom)
    bus.subscribe(EventType.CUSTOM, lambda e: calls.append(1))
    bus.emit(EventType.CUSTOM)  # must not raise
    assert calls == [1]
