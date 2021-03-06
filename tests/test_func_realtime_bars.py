import asyncio

from ib_async.functionality.realtime_bars import RealtimeBarsMixin
from ib_async.protocol import Outgoing, Incoming
from .utils import FunctionalityTestHelper


class FixtureMatchingSymbolsMixin(RealtimeBarsMixin, FunctionalityTestHelper):
    pass


def test_subscribe():
    t = FixtureMatchingSymbolsMixin()
    instrument = t.test_instrument

    bars_received = []

    def bar_hander(bar):
        bars_received.append(bar)

    # adding a handler should trigger a subscription message
    instrument.on_bar += bar_hander
    t.assert_one_message_sent(Outgoing.REQ_REAL_TIME_BARS, 3, 43, 172604153, 'LLOY', 'STK', partial_match=True)

    # Test if bars actually arrives
    t.fake_incoming(Incoming.REAL_TIME_BARS, 2, 43, 1525245478, 4.0, 5.0, 6.0, 7.0, 10, 5.5, 1)
    assert len(bars_received) == 1

    # removing the last handler should trigger an unsubscribe
    instrument.on_bar -= bar_hander
    t.assert_one_message_sent(Outgoing.CANCEL_REAL_TIME_BARS, 3, 43)

    # Simulate a stray bar arriving
    t.fake_incoming(Incoming.REAL_TIME_BARS, 2, 43, 1525245478, 4.0, 5.0, 6.0, 7.0, 10, 5.5, 1)
    assert len(bars_received) == 1


def test_historical():
    t = FixtureMatchingSymbolsMixin()
    instrument = t.test_instrument
    fut = instrument.get_historic_bars('20171231  23:59:59', bar_size=60, duration=86400)

    t.assert_one_message_sent(Outgoing.REQ_HISTORICAL_DATA, '6', '43', '172604153', 'LLOY', 'STK', '', '0.0', '',
                              '', 'SMART', 'EBS', 'CHF', 'LLOY', 'LLOY', '1', '20171231  23:59:59', '1 min', '1 D',
                              '1', 'MIDPOINT', '2', '')
    assert not fut.done()

    t.fake_incoming(Incoming.HISTORICAL_DATA, 2, 43, "20171228  23:59:59", "20171231  23:59:59", 0)
    assert fut.done()
    assert fut.result() == []


def test_historical_cancel():
    t = FixtureMatchingSymbolsMixin()
    instrument = t.test_instrument
    fut = instrument.get_historic_bars('20171231  23:59:59', bar_size=60, duration=86400)

    t.assert_one_message_sent(Outgoing.REQ_HISTORICAL_DATA, 6, 43, 172604153, 'LLOY', 'STK', '', 0.0, '',
                              '', 'SMART', 'EBS', 'CHF', 'LLOY', 'LLOY', 1, '20171231  23:59:59', '1 min', '1 D',
                              1, 'MIDPOINT', '2', '')
    assert not fut.done()

    fut.cancel()

    # Cancellation is handled in the event loop. Need to give it a chance to run.
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(0))

    t.assert_one_message_sent(Outgoing.CANCEL_HISTORICAL_DATA, 1, 43)

    # Sumulate the cancellation crossing the result
    t.fake_incoming(Incoming.HISTORICAL_DATA, 2, 43, "20171228  23:59:59", "20171231  23:59:59", 0)
