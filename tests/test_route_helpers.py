"""Unit tests for route helper functions (DRY payload extraction)."""
import unittest

from routes import _project_payload


class TestProjectPayload(unittest.TestCase):
    """
    Tests for the shared _project_payload() helper used by the create/update
    project routes. Verifies field extraction and default fallbacks.
    """

    def test_none_returns_all_defaults(self):
        """None payload -> all fields fall back to defaults."""
        payload = _project_payload(None)
        self.assertEqual(payload['title'], '')
        self.assertEqual(payload['description'], '')
        self.assertEqual(payload['status'], 'ongoing')
        self.assertEqual(payload['budget'], 0)
        self.assertEqual(payload['location'], '')
        self.assertEqual(payload['image_url'], '')
        self.assertEqual(payload['start_date'], '')
        self.assertEqual(payload['end_date'], '')

    def test_empty_dict_same_as_none(self):
        """An empty dict behaves identically to None."""
        self.assertEqual(_project_payload({}), _project_payload(None))

    def test_extracts_provided_fields(self):
        """Provided fields are extracted verbatim."""
        data = {
            'title': 'Road Repair',
            'description': 'Fix potholes',
            'status': 'ongoing',
            'budget': 100000,
            'location': 'Barangay 1',
            'image_url': '/static/uploads/img.jpg',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        }
        payload = _project_payload(data)
        self.assertEqual(payload['title'], 'Road Repair')
        self.assertEqual(payload['description'], 'Fix potholes')
        self.assertEqual(payload['status'], 'ongoing')
        self.assertEqual(payload['budget'], 100000)
        self.assertEqual(payload['location'], 'Barangay 1')
        self.assertEqual(payload['image_url'], '/static/uploads/img.jpg')
        self.assertEqual(payload['start_date'], '2026-01-01')
        self.assertEqual(payload['end_date'], '2026-12-31')

    def test_missing_keys_fall_back_to_defaults(self):
        """Fields not present in the payload fall back to defaults."""
        payload = _project_payload({'title': 'Only Title'})
        self.assertEqual(payload['title'], 'Only Title')
        self.assertEqual(payload['description'], '')
        self.assertEqual(payload['status'], 'ongoing')
        self.assertEqual(payload['budget'], 0)

    def test_explicit_empty_values_are_kept(self):
        """Explicit empty/falsy values are preserved, not overwritten by defaults."""
        payload = _project_payload({
            'title': 'X',
            'status': '',
            'budget': 0,
            'start_date': '',
        })
        self.assertEqual(payload['status'], '')
        self.assertEqual(payload['budget'], 0)
        self.assertEqual(payload['start_date'], '')


if __name__ == '__main__':
    unittest.main()
