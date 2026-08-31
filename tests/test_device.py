"""The wire boundary: nothing leaves without passing the allowlist, the
firmware gate and the bounds. No port is opened — the connection's write is
replaced by a recorder, so a leak shows up as bytes in a list."""
import unittest

import wolfmix_device as device
import wolfmix_protocol as protocol


class Recorder(device.WolfmixConnection):
    """A connection that records instead of writing. `__enter__` is never
    called, so no file descriptor exists at any point."""

    def __init__(self, firmware="2.0.18", allow=False):
        super().__init__("/dev/null", timeout=0.1, allow_untested_firmware=allow)
        self.firmware = firmware
        self.written = []

    def write_all(self, data):
        self.written.append(data)


class Allowlist(unittest.TestCase):
    """One send function, one list (AGENTS.md: no executable-firmware
    operations, ever). An event outside it cannot be framed at all."""

    def test_an_event_outside_the_list_is_refused_by_name(self):
        with self.assertRaises(protocol.WolfmixError) as caught:
            protocol.build_frame(1, protocol.DMX_PACKET, b"")
        self.assertIn("not allowlisted", str(caught.exception))

    def test_nothing_reaches_the_wire_on_refusal(self):
        link = Recorder()
        with self.assertRaises(protocol.WolfmixError):
            link.send(protocol.DMX_PACKET)
        self.assertEqual(link.written, [])

    def test_mutating_events_are_a_subset_of_the_allowlist(self):
        self.assertLessEqual(protocol.MUTATING_EVENTS,
                             protocol.ALLOWED_OUTGOING_EVENTS)

    def test_an_allowlisted_event_goes_through(self):
        link = Recorder()
        link.send(protocol.GET_SETTINGS)
        self.assertEqual(len(link.written), 1)


class FirmwareGate(unittest.TestCase):
    """Reads unconditional, mutations refused on a version nobody measured."""

    def test_a_mutation_is_refused_and_names_both_versions(self):
        link = Recorder(firmware="9.9.9")
        with self.assertRaises(protocol.WolfmixError) as caught:
            link.send(protocol.SET_MODE, b"\x00")
        message = str(caught.exception)
        self.assertIn("9.9.9", message)
        self.assertIn(protocol.TESTED_FIRMWARE[0], message)
        self.assertEqual(link.written, [], "an event reached the wire anyway")

    def test_a_read_is_untouched_by_the_gate(self):
        link = Recorder(firmware="9.9.9")
        link.send(protocol.GET_PROJECT_LIST)
        self.assertEqual(len(link.written), 1)

    def test_the_flag_lets_the_mutation_through(self):
        link = Recorder(firmware="9.9.9", allow=True)
        link.send(protocol.SET_MODE, b"\x00")
        self.assertEqual(len(link.written), 1)

    def test_a_tested_firmware_needs_no_flag(self):
        link = Recorder(firmware=protocol.TESTED_FIRMWARE[0])
        link.send(protocol.SET_MODE, b"\x00")
        self.assertEqual(len(link.written), 1)


class RawMode(unittest.TestCase):
    """A measured mode by name; a raw index only behind --experimental."""

    def test_a_named_mode_resolves(self):
        self.assertEqual(protocol.resolve_mode("home"), 0)
        self.assertEqual(protocol.resolve_mode("Static Color"), 7)
        self.assertEqual(protocol.resolve_mode("static-color"), 7)

    def test_a_raw_index_needs_the_flag(self):
        with self.assertRaises(protocol.WolfmixError) as caught:
            protocol.resolve_mode("28")
        self.assertIn("--experimental", str(caught.exception))

    def test_an_acting_mode_is_not_reachable_by_name(self):
        for index in protocol.ACTING_MODES:
            self.assertNotIn(index, protocol.NAMED_MODES.values())
            with self.assertRaises(protocol.WolfmixError):
                protocol.resolve_mode(str(index))

    def test_the_flag_opens_the_raw_index(self):
        self.assertEqual(protocol.resolve_mode("26", experimental=True), 26)
        self.assertEqual(protocol.resolve_mode("0x10", experimental=True), 16)

    def test_an_index_out_of_a_byte_is_refused_even_with_the_flag(self):
        for value in ("-1", "256"):
            with self.assertRaises(protocol.WolfmixError):
                protocol.resolve_mode(value, experimental=True)

    def test_a_nonsense_name_is_refused_with_the_flag_too(self):
        with self.assertRaises(protocol.WolfmixError) as caught:
            protocol.resolve_mode("wolfish", experimental=True)
        self.assertIn("not an index", str(caught.exception))


class PresetBounds(unittest.TestCase):
    """The panel's own range, and a raw byte — not a protobuf pair."""

    def test_the_panel_range_is_sent_as_one_raw_byte(self):
        self.assertEqual(protocol.preset_payload(0), b"\x00")
        self.assertEqual(protocol.preset_payload(protocol.PRESET_ID_MAX),
                         bytes([protocol.PRESET_ID_MAX]))

    def test_above_the_range_is_refused_as_unprobed(self):
        for value in (protocol.PRESET_ID_MAX + 1, 255):
            with self.assertRaises(protocol.WolfmixError) as caught:
                protocol.preset_payload(value)
            self.assertIn("unprobed", str(caught.exception))

    def test_a_negative_id_is_refused(self):
        with self.assertRaises(protocol.WolfmixError):
            protocol.preset_payload(-1)


if __name__ == "__main__":
    unittest.main()
