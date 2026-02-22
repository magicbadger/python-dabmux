"""
Unit tests for ZMQ parameter management (Phase 2).
"""
import pytest
from dabmux.mux import DabMultiplexer
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    DabLabel, DynamicLabel
)


class TestZmqParameterManagement:
    """Tests for ZMQ service parameter management."""

    def create_test_ensemble(self):
        """Create test ensemble with services and components."""
        ensemble = DabEnsemble()
        ensemble.id = 0xCE15
        ensemble.ecc = 0xE1
        ensemble.label = DabLabel(text="Test Ensemble")

        # Service
        service = DabService(uid='radio1')
        service.id = 0x5001
        service.label = DabLabel(text="Test Radio", short_text="Radio")
        service.pty = 10  # Pop music
        service.language = 9  # English
        ensemble.services.append(service)

        # Subchannel
        subchannel = DabSubchannel(uid='audio_ch')
        subchannel.id = 0
        subchannel.bitrate = 48
        ensemble.subchannels.append(subchannel)

        # Component
        component = DabComponent(uid='audio_comp')
        component.service_id = service.id
        component.subchannel_id = subchannel.id
        component.label = DabLabel(text="Main Programme")
        component.dynamic_label = DynamicLabel(text="Now Playing")
        ensemble.components.append(component)

        return ensemble

    def test_set_service_pty(self):
        """Test setting service PTY."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # Set PTY
        result = mux._zmq_set_service_pty({
            "service_uid": "radio1",
            "pty": 1  # News
        })

        assert result["success"] is True
        assert result["old_pty"] == 10
        assert result["new_pty"] == 1
        assert ensemble.services[0].pty == 1

    def test_set_service_pty_invalid_range(self):
        """Test setting PTY with invalid value."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # PTY must be 0-31
        with pytest.raises(ValueError, match="PTY must be between 0 and 31"):
            mux._zmq_set_service_pty({
                "service_uid": "radio1",
                "pty": 99
            })

    def test_set_service_pty_not_found(self):
        """Test setting PTY for non-existent service."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        with pytest.raises(ValueError, match="Service not found"):
            mux._zmq_set_service_pty({
                "service_uid": "invalid",
                "pty": 1
            })

    def test_set_service_language(self):
        """Test setting service language."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # Set language
        result = mux._zmq_set_service_language({
            "service_uid": "radio1",
            "language": 15  # German
        })

        assert result["success"] is True
        assert result["old_language"] == 9
        assert result["new_language"] == 15
        assert ensemble.services[0].language == 15

    def test_set_service_language_invalid_range(self):
        """Test setting language with invalid value."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        with pytest.raises(ValueError, match="Language must be between 0 and 127"):
            mux._zmq_set_service_language({
                "service_uid": "radio1",
                "language": 200
            })

    def test_set_service_label(self):
        """Test setting service label."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # Set label
        result = mux._zmq_set_service_label({
            "service_uid": "radio1",
            "text": "New Radio Name",
            "short_text": "NewRadio"
        })

        assert result["success"] is True
        assert result["old_label"] == "Test Radio"
        assert result["new_label"] == "New Radio Name"
        assert result["old_short"] == "Radio"
        assert result["new_short"] == "NewRadio"
        assert ensemble.services[0].label.text == "New Radio Name"
        assert ensemble.services[0].label.short_text == "NewRadio"

    def test_set_service_label_auto_short(self):
        """Test setting label with auto-generated short label."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # Set label without short text
        result = mux._zmq_set_service_label({
            "service_uid": "radio1",
            "text": "Example Radio"
        })

        assert result["success"] is True
        assert ensemble.services[0].label.text == "Example Radio"
        assert ensemble.services[0].label.short_text == "Example "  # First 8 chars

    def test_set_service_label_too_long(self):
        """Test setting label with text too long."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        with pytest.raises(ValueError, match="Label text must be 16 characters or less"):
            mux._zmq_set_service_label({
                "service_uid": "radio1",
                "text": "This is way too long for a label"
            })

    def test_set_service_label_short_too_long(self):
        """Test setting label with short text too long."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        with pytest.raises(ValueError, match="Short label must be 8 characters or less"):
            mux._zmq_set_service_label({
                "service_uid": "radio1",
                "text": "Test Radio",
                "short_text": "VeryLongShort"
            })

    def test_get_all_services(self):
        """Test getting all services."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        result = mux._zmq_get_all_services({})

        assert "services" in result
        assert len(result["services"]) == 1

        service = result["services"][0]
        assert service["uid"] == "radio1"
        assert service["id"] == 0x5001
        assert service["label"] == "Test Radio"
        assert service["short_label"] == "Radio"
        assert service["pty"] == 10
        assert service["language"] == 9

    def test_get_all_components(self):
        """Test getting all components."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        result = mux._zmq_get_all_components({})

        assert "components" in result
        assert len(result["components"]) == 1

        component = result["components"][0]
        assert component["uid"] == "audio_comp"
        assert component["service_id"] == 0x5001
        assert component["subchannel_id"] == 0
        assert component["label"] == "Main Programme"
        assert component["is_packet_mode"] is False

        # Check dynamic label
        assert "dynamic_label" in component
        assert component["dynamic_label"]["text"] == "Now Playing"
        assert component["dynamic_label"]["charset"] == 2  # UTF-8
        assert component["dynamic_label"]["toggle"] is False

    def test_get_all_components_with_carousel(self):
        """Test getting components with carousel info."""
        ensemble = self.create_test_ensemble()
        ensemble.components[0].carousel_enabled = True
        ensemble.components[0].carousel_directory = "/carousel"

        mux = DabMultiplexer(ensemble)

        result = mux._zmq_get_all_components({})

        component = result["components"][0]
        assert "carousel" in component
        assert component["carousel"]["enabled"] is True
        assert component["carousel"]["directory"] == "/carousel"

    def test_get_all_subchannels(self):
        """Test getting all subchannels."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        result = mux._zmq_get_all_subchannels({})

        assert "subchannels" in result
        assert len(result["subchannels"]) == 1

        subchannel = result["subchannels"][0]
        assert subchannel["uid"] == "audio_ch"
        assert subchannel["id"] == 0
        assert subchannel["type"] == "audio"  # SubchannelType.DABAudio
        assert subchannel["bitrate"] == 48
        assert "protection" in subchannel

    def test_get_all_services_multiple(self):
        """Test getting multiple services."""
        ensemble = self.create_test_ensemble()

        # Add second service
        service2 = DabService(uid='radio2')
        service2.id = 0x5002
        service2.label = DabLabel(text="Radio 2")
        service2.pty = 1  # News
        service2.language = 9
        ensemble.services.append(service2)

        mux = DabMultiplexer(ensemble)

        result = mux._zmq_get_all_services({})

        assert len(result["services"]) == 2
        assert result["services"][0]["uid"] == "radio1"
        assert result["services"][1]["uid"] == "radio2"
        assert result["services"][1]["pty"] == 1

    def test_parameter_changes_persist(self):
        """Test that parameter changes persist across calls."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        # Change PTY
        mux._zmq_set_service_pty({"service_uid": "radio1", "pty": 5})

        # Change language
        mux._zmq_set_service_language({"service_uid": "radio1", "language": 15})

        # Change label
        mux._zmq_set_service_label({
            "service_uid": "radio1",
            "text": "Updated Radio"
        })

        # Verify all changes persisted
        service = ensemble.services[0]
        assert service.pty == 5
        assert service.language == 15
        assert service.label.text == "Updated Radio"

        # Verify via get_all_services
        result = mux._zmq_get_all_services({})
        svc_info = result["services"][0]
        assert svc_info["pty"] == 5
        assert svc_info["language"] == 15
        assert svc_info["label"] == "Updated Radio"
