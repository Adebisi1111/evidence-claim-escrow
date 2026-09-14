import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock

# Mock genlayer before importing contract
import sys
sys.modules['genlayer'] = MagicMock()

# Import after mock
from contracts.intelligence_escrow import IntelligenceClaimEscrow


class TestIntelligenceClaimEscrow:
    """Test suite for Intelligence Evidence-Based Claim Escrow v2."""

    def setup_method(self):
        """Setup test fixtures."""
        self.contract = IntelligenceClaimEscrow()
        self.contract.next_escrow_id = 0
        self.contract.escrows = {}

    def test_create_escrow_locks_funds(self):
        """Test creating an escrow with sufficient funds."""
        with patch('contracts.intelligence_escrow.gl') as mock_gl:
            mock_gl.message.value = 1000000000000000000
            mock_gl.message.sender_address = MagicMock()
            mock_gl.message.sender_address.__str__ = lambda self: "0xDepositor"
            mock_gl.vm.run_nondet.return_value = json.dumps({
                "verdict": "SUPPORTED",
                "quality_score": 85,
                "confidence_score": 90
            })
            
            escrow_id = self.contract.createClaimEscrow(
                claim="The sky is blue",
                claimant="0xClaimant"
            )
        
        assert escrow_id == 0
        assert self.contract.escrows[0]["status"] == "RESOLVED"
        assert self.contract.escrows[0]["quality_score"] == 85
        assert self.contract.escrows[0]["confidence_score"] == 90
        assert self.contract.escrows[0]["verdict"] == "SUPPORTED"

    def test_create_escrow_without_funds_rejected(self):
        """Test that creating an escrow without funds is rejected."""
        with patch('contracts.intelligence_escrow.gl') as mock_gl:
            mock_gl.message.value = 0
            
            with pytest.raises(Exception, match="Escrow must be funded with GEN"):
                self.contract.createClaimEscrow(
                    claim="Test claim",
                    claimant="0xClaimant"
                )

    def test_refuted_verdict_returns_funds(self):
        """Test that a REFUTED verdict returns funds to depositor."""
        with patch('contracts.intelligence_escrow.gl') as mock_gl:
            mock_gl.message.value = 1000000000000000000
            mock_gl.message.sender_address = MagicMock()
            mock_gl.message.sender_address.__str__ = lambda self: "0xDepositor"
            mock_gl.vm.run_nondet.return_value = json.dumps({
                "verdict": "REFUTED",
                "quality_score": 20,
                "confidence_score": 75
            })
            
            escrow_id = self.contract.createClaimEscrow(
                claim="False claim",
                claimant="0xClaimant"
            )
        
        assert self.contract.escrows[escrow_id]["status"] == "REFUTED"
        assert self.contract.escrows[escrow_id]["verdict"] == "REFUTED"

    def test_verify_consensus_payload_matching(self):
        """Test that matching payloads pass consensus."""
        proposed = json.dumps({
            "verdict": "SUPPORTED",
            "quality_score": 85,
            "confidence_score": 90
        })
        validator = json.dumps({
            "verdict": "SUPPORTED",
            "quality_score": 85,
            "confidence_score": 90
        })
        
        assert self.contract._verify_consensus_payload(proposed, validator) is True

    def test_verify_consensus_payload_mismatched_verdict(self):
        """Test that mismatched verdicts fail consensus."""
        proposed = json.dumps({
            "verdict": "SUPPORTED",
            "quality_score": 85,
            "confidence_score": 90
        })
        validator = json.dumps({
            "verdict": "REFUTED",
            "quality_score": 85,
            "confidence_score": 90
        })
        
        assert self.contract._verify_consensus_payload(proposed, validator) is False

    def test_verify_consensus_payload_mismatched_scores(self):
        """Test that mismatched scores fail consensus."""
        proposed = json.dumps({
            "verdict": "SUPPORTED",
            "quality_score": 85,
            "confidence_score": 90
        })
        validator = json.dumps({
            "verdict": "SUPPORTED",
            "quality_score": 70,
            "confidence_score": 90
        })
        
        assert self.contract._verify_consensus_payload(proposed, validator) is False

    def test_verify_consensus_payload_invalid_json(self):
        """Test that invalid JSON fails consensus."""
        assert self.contract._verify_consensus_payload("invalid", "json") is False

    def test_get_escrow(self):
        """Test retrieving escrow details."""
        self.contract.escrows[0] = {
            "claim": "Test",
            "depositor": "0xDepositor",
            "claimant": "0xClaimant",
            "amount": 1000000000000000000,
            "status": "RESOLVED",
            "quality_score": 85,
            "confidence_score": 90,
            "verdict": "SUPPORTED"
        }
        
        result = self.contract.get_escrow(0)
        data = json.loads(result)
        
        assert data["exists"] is True
        assert data["status"] == "RESOLVED"
        assert data["quality_score"] == 85
        assert data["verdict"] == "SUPPORTED"

    def test_get_escrow_not_found(self):
        """Test retrieving non-existent escrow."""
        result = self.contract.get_escrow(999)
        data = json.loads(result)
        assert data["exists"] is False

    def test_get_escrows_count(self):
        """Test escrow count."""
        self.contract.escrows[0] = {"claim": "Test 1"}
        self.contract.escrows[1] = {"claim": "Test 2"}
        
        count = self.contract.get_escrows_count()
        assert count == "2"

    def test_multiple_escrows_increment_id(self):
        """Test that escrow IDs increment correctly."""
        with patch('contracts.intelligence_escrow.gl') as mock_gl:
            mock_gl.message.value = 1000000000000000000
            mock_gl.message.sender_address = MagicMock()
            mock_gl.message.sender_address.__str__ = lambda self: "0xDepositor"
            mock_gl.vm.run_nondet.return_value = json.dumps({
                "verdict": "SUPPORTED",
                "quality_score": 85,
                "confidence_score": 90
            })
            
            id1 = self.contract.createClaimEscrow("Claim 1", "0xClaimant1")
            id2 = self.contract.createClaimEscrow("Claim 2", "0xClaimant2")
        
        assert id1 == 0
        assert id2 == 1
        assert len(self.contract.escrows) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
