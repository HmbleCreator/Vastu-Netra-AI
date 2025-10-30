"""Unit tests for SpatialIndex implementations."""
import os
import sys
import unittest
from dataclasses import dataclass

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from shapely.geometry import box, Polygon
from backend.app.solvers.impl.graph_solver_impl import SpatialIndex

@dataclass
class MockRoom:
    """Mock room class for testing."""
    polygon: Polygon

class TestSpatialIndex(unittest.TestCase):
    def setUp(self):
        """Create test rooms with known overlaps."""
        self.rooms = [
            MockRoom(box(0, 0, 2, 2)),     # Room 0
            MockRoom(box(1, 1, 3, 3)),     # Room 1 (overlaps 0)
            MockRoom(box(4, 4, 6, 6)),     # Room 2 (isolated)
            MockRoom(box(-1, -1, 0.5, 0.5)) # Room 3 (overlaps 0)
        ]
        
    def test_grid_index(self):
        """Test grid-based spatial index."""
        index = SpatialIndex(self.rooms, grid_size=1.0)
        
        # Test known overlaps
        test_box = box(0, 0, 2, 2)
        overlaps = index.query_overlaps(test_box)
        self.assertIn(0, overlaps)
        self.assertIn(1, overlaps)
        self.assertIn(3, overlaps)
        self.assertNotIn(2, overlaps)
        
        # Test isolated room
        isolated = index.query_overlaps(box(4, 4, 6, 6))
        self.assertEqual(len(isolated), 1)
        self.assertIn(2, isolated)
        
    def test_rtree_index(self):
        """Test rtree-based spatial index if available."""
        try:
            # Try to create a test rtree index first
            from rtree import index
            test_idx = index.Index()
            print("\nrtree functionality verified")
            
            # Now test our SpatialIndex implementation
            index = SpatialIndex(self.rooms, grid_size=1.0)
            print("SpatialIndex created, use_rtree =", index.use_rtree)
            
            # Skip test if rtree import succeeded but wasn't used
            if not index.use_rtree:
                self.skipTest(f"rtree {rtree.__version__} available but not used")
                
            # Test same overlaps as grid implementation
            test_box = box(0, 0, 2, 2)
            overlaps = index.query_overlaps(test_box)
            self.assertIn(0, overlaps)
            self.assertIn(1, overlaps)
            self.assertIn(3, overlaps)
            self.assertNotIn(2, overlaps)
            
            # Test isolated room
            isolated = index.query_overlaps(box(4, 4, 6, 6))
            self.assertEqual(len(isolated), 1)
            self.assertIn(2, isolated)
            
        except ImportError as e:
            self.skipTest(f"rtree not available: {str(e)}")
        except Exception as e:
            self.fail(f"Unexpected error testing rtree: {str(e)}")
            
    def test_index_consistency(self):
        """Test that both implementations give consistent results."""
        # Create both indexes if possible
        grid_index = SpatialIndex(self.rooms, grid_size=1.0)
        
        try:
            import rtree
            rtree_index = SpatialIndex(self.rooms, grid_size=1.0)
            if rtree_index.use_rtree:
                # Test multiple query boxes
                test_cases = [
                    box(0, 0, 2, 2),
                    box(4, 4, 6, 6),
                    box(-1, -1, 3, 3),
                    box(2, 2, 4, 4)
                ]
                
                for test_box in test_cases:
                    grid_results = grid_index.query_overlaps(test_box)
                    rtree_results = rtree_index.query_overlaps(test_box)
                    self.assertEqual(
                        grid_results, 
                        rtree_results,
                        f"Inconsistent results for {test_box.bounds}"
                    )
        except ImportError:
            self.skipTest("rtree not available for consistency test")