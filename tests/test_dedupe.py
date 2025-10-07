"""
Tests for deduplication functionality.

This module tests the deduplication logic including:
- Instagram post ID checking
- Perceptual hash comparison
- Duplicate detection and marking
- Statistics and reporting
"""

import pytest
from unittest.mock import Mock, patch

from app.dedupe import Deduplicator, check_download_duplicate, check_transform_duplicate
from app.models import Download, Transform, InstagramTarget, StatusEnum


class TestDeduplicator:
    """Test cases for Deduplicator class."""
    
    @pytest.fixture
    def deduplicator(self):
        """Create a Deduplicator instance for testing."""
        return Deduplicator()
    
    @pytest.fixture
    def mock_download(self):
        """Create a mock download for testing."""
        target = InstagramTarget(username="test_user", is_active=True)
        download = Download(
            target=target,
            ig_post_id="test_post_123",
            ig_shortcode="test_post_123",
            source_url="https://instagram.com/p/test_post_123",
            local_path="test_video.mp4",
            permission_proof_path="test_proof.txt",
            file_size=1024,
            duration_seconds=30,
            caption="Test caption"
        )
        return download
    
    @pytest.fixture
    def mock_transform(self, mock_download):
        """Create a mock transform for testing."""
        transform = Transform(
            download_id=1,
            input_path="input.mp4",
            output_path="output.mp4",
            thumbnail_path="thumb.jpg",
            phash="a1b2c3d4e5f6",
            status=StatusEnum.COMPLETED
        )
        transform.download = mock_download
        return transform
    
    def test_deduplicator_initialization(self, deduplicator):
        """Test deduplicator initialization."""
        assert deduplicator.settings is not None
        assert deduplicator.phash_threshold == 10
        assert isinstance(deduplicator.phash_threshold, int)
    
    def test_compare_phashes_similar(self, deduplicator):
        """Test pHash comparison for similar hashes."""
        # Create two similar hashes (small Hamming distance)
        phash1 = "a1b2c3d4e5f6"
        phash2 = "a1b2c3d4e5f7"  # Only 1 bit different
        
        # Mock the imagehash comparison
        with patch('app.dedupe.imagehash') as mock_imagehash:
            mock_hash1 = Mock()
            mock_hash2 = Mock()
            mock_hash1.__sub__ = Mock(return_value=1)  # Hamming distance of 1
            
            mock_imagehash.hex_to_hash.side_effect = [mock_hash1, mock_hash2]
            
            result = deduplicator._compare_phashes(phash1, phash2)
            assert result is True
    
    def test_compare_phashes_different(self, deduplicator):
        """Test pHash comparison for different hashes."""
        phash1 = "a1b2c3d4e5f6"
        phash2 = "f6e5d4c3b2a1"  # Completely different
        
        with patch('app.dedupe.imagehash') as mock_imagehash:
            mock_hash1 = Mock()
            mock_hash2 = Mock()
            mock_hash1.__sub__ = Mock(return_value=50)  # Large Hamming distance
            
            mock_imagehash.hex_to_hash.side_effect = [mock_hash1, mock_hash2]
            
            result = deduplicator._compare_phashes(phash1, phash2)
            assert result is False
    
    def test_phash_distance_calculation(self, deduplicator):
        """Test pHash distance calculation."""
        phash1 = "a1b2c3d4e5f6"
        phash2 = "a1b2c3d4e5f7"
        
        with patch('app.dedupe.imagehash') as mock_imagehash:
            mock_hash1 = Mock()
            mock_hash2 = Mock()
            mock_hash1.__sub__ = Mock(return_value=5)
            
            mock_imagehash.hex_to_hash.side_effect = [mock_hash1, mock_hash2]
            
            distance = deduplicator._phash_distance(phash1, phash2)
            assert distance == 5
    
    def test_phash_distance_error_handling(self, deduplicator):
        """Test pHash distance calculation error handling."""
        phash1 = "invalid_hash"
        phash2 = "another_invalid_hash"
        
        with patch('app.dedupe.imagehash') as mock_imagehash:
            mock_imagehash.hex_to_hash.side_effect = Exception("Invalid hash")
            
            distance = deduplicator._phash_distance(phash1, phash2)
            assert distance == 999  # Error value
    
    def test_check_duplicate_transform_no_existing(self, deduplicator, mock_transform):
        """Test duplicate check when no existing transforms exist."""
        with patch('app.dedupe.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = []
            
            is_duplicate, reason = deduplicator.check_duplicate_transform(mock_transform)
            
            assert is_duplicate is False
            assert reason is None
    
    def test_check_duplicate_transform_similar_found(self, deduplicator, mock_transform):
        """Test duplicate check when similar transform is found."""
        # Create a mock existing transform
        existing_transform = Mock()
        existing_transform.id = 2
        existing_transform.phash = "a1b2c3d4e5f7"
        
        with patch('app.dedupe.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = [existing_transform]
            
            # Mock the pHash comparison to return True
            with patch.object(deduplicator, '_compare_phashes', return_value=True):
                with patch.object(deduplicator, '_phash_distance', return_value=5):
                    is_duplicate, reason = deduplicator.check_duplicate_transform(mock_transform)
                    
                    assert is_duplicate is True
                    assert "transform 2" in reason
                    assert "pHash distance: 5" in reason
    
    def test_mark_duplicate_transform(self, deduplicator, mock_transform):
        """Test marking a transform as duplicate."""
        with patch('app.dedupe.get_db_session') as mock_session:
            mock_db_transform = Mock()
            mock_session.return_value.__enter__.return_value.query.return_value.filter_by.return_value.first.return_value = mock_db_transform
            
            deduplicator.mark_duplicate_transform(mock_transform, "Test reason")
            
            assert mock_db_transform.status == StatusEnum.DUPLICATE
            assert mock_db_transform.error_message == "Test reason"
    
    def test_get_duplicate_stats(self, deduplicator):
        """Test getting deduplication statistics."""
        with patch('app.dedupe.get_db_session') as mock_session:
            # Mock database queries
            mock_session.return_value.__enter__.return_value.query.return_value.count.side_effect = [10, 8, 2]
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = []
            
            stats = deduplicator.get_duplicate_stats()
            
            assert isinstance(stats, dict)
            assert "total_downloads" in stats
            assert "total_transforms" in stats
            assert "duplicate_transforms" in stats
            assert "phash_threshold" in stats
            assert "similar_pairs_found" in stats
            assert "average_similarity_distance" in stats
    
    def test_get_unique_transforms_for_upload(self, deduplicator):
        """Test getting unique transforms ready for upload."""
        # Create mock transforms
        transform1 = Mock()
        transform1.phash = "hash1"
        transform2 = Mock()
        transform2.phash = "hash2"
        
        with patch('app.dedupe.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = [transform1, transform2]
            
            with patch.object(deduplicator, '_compare_phashes', return_value=False):
                unique_transforms = deduplicator.get_unique_transforms_for_upload()
                
                assert len(unique_transforms) == 2
                assert transform1 in unique_transforms
                assert transform2 in unique_transforms


class TestDedupeUtilities:
    """Test utility functions for deduplication."""
    
    def test_check_download_duplicate_function(self):
        """Test the check_download_duplicate utility function."""
        # This would require database setup, so just test the function exists
        assert callable(check_download_duplicate)
    
    def test_check_transform_duplicate_function(self):
        """Test the check_transform_duplicate utility function."""
        # This would require database setup, so just test the function exists
        assert callable(check_transform_duplicate)


class TestDedupeIntegration:
    """Integration tests for deduplication."""
    
    def test_process_transforms_for_duplicates(self, db_session):
        """Test processing all transforms for duplicates."""
        from app.models import Transform, Download, InstagramTarget
        from datetime import datetime
        
        # Create test data
        target = InstagramTarget(username="test_user", is_active=True)
        download = Download(
            target=target,
            ig_post_id="test_post",
            ig_shortcode="test_post",
            source_url="https://instagram.com/p/test_post",
            local_path="test_video.mp4",
            permission_proof_path="test_proof.txt",
            file_size=1024,
            duration_seconds=30,
            caption="Test caption",
            status="COMPLETED"
        )
        
        transform = Transform(
            download_id=download.id,
            input_path="test_video.mp4",
            output_path="test_output.mp4",
            thumbnail_path="test_thumb.jpg",
            phash="test_phash_123",
            status="COMPLETED"
        )
        
        db_session.add(target)
        db_session.add(download)
        db_session.add(transform)
        db_session.commit()
        
        deduplicator = Deduplicator()
        
        with patch.object(deduplicator, 'check_duplicate_transform') as mock_check:
            mock_check.return_value = (True, "Test duplicate")
            
            with patch.object(deduplicator, 'mark_duplicate_transform') as mock_mark:
                duplicates = deduplicator.process_transforms_for_duplicates()
                
                # Should call check and mark for each transform
                assert mock_check.called
                assert mock_mark.called


if __name__ == "__main__":
    pytest.main([__file__])
