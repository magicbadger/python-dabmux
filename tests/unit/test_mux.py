"""
Unit tests for DAB Multiplexer.

These tests verify that the multiplexer correctly combines inputs
and generates ETI frames.
"""
import pytest
import tempfile
import os
from dabmux.mux import DabMultiplexer
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    DabLabel, SubchannelType, TransmissionMode
)
from dabmux.input.file import RawFileInput
from dabmux.output.file import FileOutput


class TestDabMultiplexer:
    """Test DabMultiplexer class."""

    def test_create_multiplexer(self) -> None:
        """Test creating a multiplexer."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test Ensemble")

        mux = DabMultiplexer(ensemble)
        assert mux.ensemble == ensemble
        assert len(mux.inputs) == 0
        assert len(mux.outputs) == 0
        assert mux.frame_count == 0

    def test_add_output(self) -> None:
        """Test adding output to multiplexer."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path)
            mux.add_output(output)

            assert len(mux.outputs) == 1
            assert mux.outputs[0] == output

            output.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_add_input(self) -> None:
        """Test adding input to multiplexer."""
        ensemble = DabEnsemble()

        # Add a subchannel to the ensemble
        subchannel = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ensemble.subchannels.append(subchannel)

        mux = DabMultiplexer(ensemble)

        # Create a test input file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Test audio data' * 100)
            temp_path = f.name

        try:
            input_source = RawFileInput()
            input_source.open(temp_path)

            mux.add_input("audio1", input_source)
            assert len(mux.inputs) == 1
            assert "audio1" in mux.inputs

            input_source.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_add_input_nonexistent_subchannel(self) -> None:
        """Test adding input for nonexistent subchannel raises error."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Test data')
            temp_path = f.name

        try:
            input_source = RawFileInput()
            input_source.open(temp_path)

            with pytest.raises(ValueError, match="not found"):
                mux.add_input("nonexistent", input_source)

            input_source.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_add_duplicate_input(self) -> None:
        """Test adding duplicate input raises error."""
        ensemble = DabEnsemble()
        subchannel = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ensemble.subchannels.append(subchannel)

        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Test data')
            temp_path = f.name

        try:
            input1 = RawFileInput()
            input1.open(temp_path)
            mux.add_input("audio1", input1)

            input2 = RawFileInput()
            input2.open(temp_path)

            with pytest.raises(ValueError, match="already exists"):
                mux.add_input("audio1", input2)

            input1.close()
            input2.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_generate_empty_frame(self) -> None:
        """Test generating an empty frame."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.transmission_mode = TransmissionMode.TM_I

        mux = DabMultiplexer(ensemble)

        frame = mux.generate_frame()
        assert frame.fc.mid == 1  # Mode I
        assert frame.fc.nst == 0  # No subchannels
        assert mux.frame_count == 1

    def test_generate_frame_with_subchannels(self) -> None:
        """Test generating frame with subchannels."""
        ensemble = DabEnsemble()
        ensemble.transmission_mode = TransmissionMode.TM_I

        # Add subchannels
        sub1 = DabSubchannel(uid="audio1", id=1, start_address=0, bitrate=128)
        sub2 = DabSubchannel(uid="audio2", id=2, start_address=100, bitrate=128)
        ensemble.subchannels.extend([sub1, sub2])

        mux = DabMultiplexer(ensemble)

        frame = mux.generate_frame()
        assert frame.fc.nst == 2  # Two subchannels
        assert len(frame.stc_headers) == 2

        # Check STC headers
        assert frame.stc_headers[0].scid == 1
        assert frame.stc_headers[1].scid == 2

    def test_write_frame(self) -> None:
        """Test writing a frame to output."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path)
            mux.add_output(output)

            frame = mux.generate_frame()
            mux.write_frame(frame)

            # Verify frame was written
            assert output.frame_count == 1

            output.close()

            # Verify file exists and has data
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_run_once(self) -> None:
        """Test running multiplexer once."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path)
            mux.add_output(output)

            result = mux.run_once()
            assert result is True
            assert mux.frame_count == 1
            assert output.frame_count == 1

            output.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_run_limited_frames(self) -> None:
        """Test running multiplexer for a limited number of frames."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path)
            mux.add_output(output)

            # Generate 10 frames
            mux.run(num_frames=10)

            assert mux.frame_count == 10
            assert output.frame_count == 10

            output.close()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_frame_count_wraps(self) -> None:
        """Test that frame count wraps at 256."""
        ensemble = DabEnsemble()
        mux = DabMultiplexer(ensemble)
        mux.frame_count = 255

        frame = mux.generate_frame()
        assert frame.fc.fct == 255

        frame = mux.generate_frame()
        assert frame.fc.fct == 0  # Wrapped

    def test_cleanup(self) -> None:
        """Test cleaning up multiplexer resources."""
        ensemble = DabEnsemble()
        subchannel = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ensemble.subchannels.append(subchannel)

        mux = DabMultiplexer(ensemble)

        # Create test input file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Test data' * 100)
            input_path = f.name

        # Create test output file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            output_path = f.name

        try:
            # Add input
            input_source = RawFileInput()
            input_source.open(input_path)
            mux.add_input("audio1", input_source)

            # Add output
            output = FileOutput()
            output.open(output_path)
            mux.add_output(output)

            # Both should be open
            assert input_source.is_open
            assert output.is_open

            # Cleanup
            mux.cleanup()

            # Both should be closed
            assert not input_source.is_open
            assert not output.is_open

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestMultiplexerIntegration:
    """Integration tests for multiplexer."""

    def test_complete_workflow(self) -> None:
        """Test complete multiplexer workflow."""
        # Create ensemble
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.ecc = 0xE1
        ensemble.label = DabLabel(text="Integration Test")
        ensemble.transmission_mode = TransmissionMode.TM_I

        # Add service
        service = DabService(uid="radio1", id=0x1234)
        service.label = DabLabel(text="Test Radio")
        ensemble.services.append(service)

        # Add subchannel
        subchannel = DabSubchannel(
            uid="audio1",
            id=1,
            type=SubchannelType.DABPlusAudio,
            start_address=0,
            bitrate=128
        )
        ensemble.subchannels.append(subchannel)

        # Add component
        component = DabComponent(uid="comp1")
        component.service_id = service.id
        component.subchannel_id = subchannel.id
        ensemble.components.append(component)

        # Create multiplexer
        mux = DabMultiplexer(ensemble)

        # Create test input file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x00' * 1000)
            input_path = f.name

        # Create output file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            output_path = f.name

        try:
            # Add input
            input_source = RawFileInput()
            input_source.open(input_path)
            mux.add_input("audio1", input_source)

            # Add output
            output = FileOutput()
            output.open(output_path + "?type=streamed")
            mux.add_output(output)

            # Generate some frames
            mux.run(num_frames=5)

            # Verify
            assert mux.frame_count == 5
            assert output.frame_count == 5

            # Cleanup
            mux.cleanup()

            # Verify output file exists
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
