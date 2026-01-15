try:
    from src.tests.mocks.mock_position import MockPosition
except ImportError:
    from tests.mocks.mock_position import MockPosition

class MockPositionBuilder:
    def build(self, signal, bar):
        return MockPosition(
            direction=signal.direction,
            source=signal.source,
            is_hedge=signal.metadata.get("is_hedge", False),
            price=signal.price or bar[3],
        )
