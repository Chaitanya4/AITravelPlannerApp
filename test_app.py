import sys
import unittest
from unittest.mock import MagicMock, patch

# Headless mock injection for modules not present in the runtime sandbox
sys.modules['streamlit'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

import json

# Import functions to test from app.py
from app import (
    sanitize_text,
    clean_destination_name,
    validate_days_count,
    generate_itinerary_json,
    generate_chat_response,
    LOCAL_EXPERTS
)

class TestNomadCompassCore(unittest.TestCase):

    def test_sanitize_text_basic(self):
        """Test standard string trimming and basic outputs."""
        self.assertEqual(sanitize_text("   Tokyo adventure  "), "Tokyo adventure")
        self.assertEqual(sanitize_text(123), "")
        self.assertEqual(sanitize_text(None), "")

    def test_sanitize_text_xss_mitigation(self):
        """Test that HTML and script tags are successfully stripped from user inputs."""
        dirty_input = "Temple visit <script>alert('XSS')</script> & relax"
        expected = "Temple visit alert('XSS') & relax"
        self.assertEqual(sanitize_text(dirty_input), expected)

    def test_sanitize_text_cropping(self):
        """Test that strings exceeding specified maximum limits are cropped properly."""
        long_string = "A" * 500
        cropped = sanitize_text(long_string, max_length=150)
        self.assertEqual(len(cropped), 150)
        self.assertEqual(cropped, "A" * 150)

    def test_clean_destination_name_safe(self):
        """Test that destination characters are restricted to alphanumeric and simple safe marks."""
        self.assertEqual(clean_destination_name("Kyoto, Japan"), "Kyoto, Japan")
        self.assertEqual(clean_destination_name("San Francisco-Oakland"), "San Francisco-Oakland")
        self.assertEqual(clean_destination_name("Osaka; DROP TABLE Users;"), "Osaka DROP TABLE Users")
        self.assertEqual(clean_destination_name(""), "")

    def test_validate_days_count(self):
        """Test clamping bounds for vacation durations (limits of [1, 10] days)."""
        self.assertEqual(validate_days_count(5), 5)
        self.assertEqual(validate_days_count(15), 10) # Clamps down to 10
        self.assertEqual(validate_days_count(0), 1)   # Clamps up to 1
        self.assertEqual(validate_days_count(-3), 1)  # Clamps up to 1
        self.assertEqual(validate_days_count("not-a-number"), 3) # Fallback default
        self.assertEqual(validate_days_count(None), 3)

    @patch("google.genai.Client")
    def test_generate_itinerary_json_success(self, mock_client_class):
        """Test successful vacation planning generation with structured mocked response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        
        mock_itinerary = {
            "destination": "Kyoto",
            "overview": "A historical tour of majestic temples and gardens.",
            "expertTips": ["Buy a day pass", "Arrive early at Fushimi Inari"],
            "days": [
                {
                    "dayNumber": 1,
                    "title": "Historical Shrines",
                    "activities": [
                        {
                            "time": "09:00 AM",
                            "title": "Fushimi Inari",
                            "description": "Walk through thousands of red Torii gates.",
                            "category": "cultural",
                            "locationName": "Fushimi Inari Taisha",
                            "expertTip": "Beat the crowds by arriving before 8am."
                        }
                    ]
                }
            ]
        }
        
        mock_response.text = json.dumps(mock_itinerary)
        mock_client.models.generate_content.return_value = mock_response

        # Execute
        result = generate_itinerary_json(
            client=mock_client,
            destination="Kyoto",
            days_count=3,
            interests="Ancient shrines, walking",
            traveler_type="Solo Explorer"
        )

        # Assertions
        self.assertEqual(result["destination"], "Kyoto")
        self.assertEqual(len(result["days"]), 1)
        self.assertEqual(result["days"][0]["title"], "Historical Shrines")
        mock_client.models.generate_content.assert_called_once()

    def test_generate_itinerary_errors(self):
        """Test that errors are thrown for invalid clients or destinations."""
        # Uninitialized client error
        with self.assertRaises(ValueError):
            generate_itinerary_json(client=None, destination="Osaka", days_count=3, interests="", traveler_type="")

        # Missing destination error
        mock_client = MagicMock()
        with self.assertRaises(ValueError):
            generate_itinerary_json(client=mock_client, destination="", days_count=3, interests="", traveler_type="")

    @patch("google.genai.Client")
    def test_generate_chat_response_success(self, mock_client_class):
        """Test expert chat answer generation with conversation logs forwarding."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Kyoto is famous for Matcha! You should visit Uji."
        mock_client.models.generate_content.return_value = mock_response

        history = [
            {"role": "user", "content": "Hi Chef Mei!"},
            {"role": "model", "content": "Hello traveler!"}
        ]

        reply = generate_chat_response(
            client=mock_client,
            destination="Kyoto",
            expert_instruction=LOCAL_EXPERTS["foodie"]["system_instruction"],
            user_message="Tell me about tea culinary options",
            history=history
        )

        self.assertEqual(reply, "Kyoto is famous for Matcha! You should visit Uji.")
        mock_client.models.generate_content.assert_called_once()

    def test_generate_chat_errors(self):
        """Test expert chat validation logic when values are missing or invalid."""
        # Client not loaded
        with self.assertRaises(ValueError):
            generate_chat_response(client=None, destination="Tokyo", expert_instruction="", user_message="Hi", history=[])

        # Destination empty
        mock_client = MagicMock()
        with self.assertRaises(ValueError):
            generate_chat_response(client=mock_client, destination="", expert_instruction="", user_message="Hi", history=[])

        # Empty prompt message
        reply = generate_chat_response(client=mock_client, destination="Tokyo", expert_instruction="", user_message="", history=[])
        self.assertEqual(reply, "I didn't receive a message. Please type something so I can help!")

if __name__ == "__main__":
    unittest.main()
