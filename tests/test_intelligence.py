import json


def _hex(addr):
    if isinstance(addr, (bytes, bytearray)):
        from genlayer.py.types import Address
        return Address(bytes(addr)).as_hex
    return str(addr)


def test_submit_resolve_read_end_to_end(direct_vm, direct_deploy, direct_alice):
    """Reproducible test: submit claim with evidence, resolve, read verdict + assessment."""
    direct_vm.sender = direct_alice  # Set sender BEFORE deploy so alice is validator
    contract = direct_deploy("contracts/intelligence.py")

    evidence = "NASA confirms: Earth orbits the Sun. Source: https://nasa.gov/earth"
    
    # 1. SUBMIT
    contract.submit_claim(
        "claim-1",
        "The Earth orbits the Sun",
        evidence,
        "Science"
    )

    claim = json.loads(contract.get_claim("claim-1"))
    assert claim["exists"] is True
    assert claim["text"] == "The Earth orbits the Sun"
    assert claim["evidence_hash"] is not None
    assert len(claim["evidence_hash"]) == 66  # 0x + 64 hex chars
    assert claim["resolved"] is False

    # 2. RESOLVE
    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "VERIFIED",
        "confidence": 95,
        "reasoning": "Evidence directly supports the claim: NASA confirms heliocentric model."
    }))
    verdict = contract.resolve_claim("claim-1")
    assert verdict in ("VERIFIED", "REJECTED", "INCONCLUSIVE")

    # 3. READ
    claim = json.loads(contract.get_claim("claim-1"))
    assert claim["resolved"] is True
    assert claim["verdict"] in ("VERIFIED", "REJECTED", "INCONCLUSIVE")
    assert 0 <= claim["confidence"] <= 100
    assert isinstance(claim["reasoning"], str) and len(claim["reasoning"]) > 0

    # 4. EVIDENCE
    evidence_data = json.loads(contract.get_evidence("claim-1"))
    assert evidence_data["evidence_hash"] == claim["evidence_hash"]
    assert evidence_data["evidence_data"] == evidence[:2000]


def test_reject_verdict(direct_vm, direct_deploy, direct_alice):
    """Verify REJECTED path."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    evidence = "Flat Earth Society claims: Earth is flat. Source: https://flatearth.org"
    contract.submit_claim("claim-2", "The Earth is flat", evidence, "Science")

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "REJECTED",
        "confidence": 98,
        "reasoning": "Overwhelming scientific evidence contradicts flat Earth claim."
    }))
    verdict = contract.resolve_claim("claim-2")

    claim = json.loads(contract.get_claim("claim-2"))
    assert verdict == "REJECTED"
    assert claim["verdict"] == "REJECTED"


def test_inconclusive_verdict(direct_vm, direct_deploy, direct_alice):
    """Verify INCONCLUSIVE path."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    evidence = "Insufficient data to determine."
    contract.submit_claim("claim-3", "Life exists on Mars", evidence, "Science")

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "INCONCLUSIVE",
        "confidence": 25,
        "reasoning": "Insufficient evidence to confirm or deny life on Mars."
    }))
    verdict = contract.resolve_claim("claim-3")

    claim = json.loads(contract.get_claim("claim-3"))
    assert verdict == "INCONCLUSIVE"
    assert claim["verdict"] == "INCONCLUSIVE"


def test_submit_duplicate_claim_throws(direct_vm, direct_deploy, direct_alice):
    """Verify duplicate claim submission fails."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    contract.submit_claim("claim-5", "First", "Evidence", "General")

    try:
        contract.submit_claim("claim-5", "Second", "Evidence", "General")
        assert False, "Should have reverted"
    except Exception as e:
        assert "already exists" in str(e.message)


def test_resolve_already_resolved_throws(direct_vm, direct_deploy, direct_alice):
    """Verify resolving an already-resolved claim fails."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    contract.submit_claim("claim-6", "Test", "Evidence", "General")

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "VERIFIED",
        "confidence": 80,
        "reasoning": "Looks good"
    }))
    contract.resolve_claim("claim-6")

    try:
        contract.resolve_claim("claim-6")
        assert False, "Should have reverted"
    except Exception as e:
        assert "already resolved" in str(e.message)


def test_get_claim_not_found(direct_vm, direct_deploy, direct_alice):
    """Verify get_claim returns exists=False for unknown claim."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    claim = json.loads(contract.get_claim("nonexistent"))
    assert claim["exists"] is False


def test_get_evidence_not_found(direct_vm, direct_deploy, direct_alice):
    """Verify get_evidence returns exists=False for unknown claim."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    data = json.loads(contract.get_evidence("nonexistent"))
    assert data["exists"] is False


def test_get_claims_count(direct_vm, direct_deploy, direct_alice):
    """Verify get_claims_count returns correct count."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    contract.submit_claim("claim-7", "Claim 7", "Evidence", "General")
    contract.submit_claim("claim-8", "Claim 8", "Evidence", "Tech")

    assert contract.get_claims_count() == "2"


def test_evidence_hash_matches(direct_vm, direct_deploy, direct_alice):
    """Verify evidence hash is computed correctly and matches on retrieval."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/intelligence.py")

    evidence = "This is test evidence for hash verification."
    contract.submit_claim("claim-9", "Test claim", evidence, "General")

    data = json.loads(contract.get_evidence("claim-9"))
    assert data["evidence_matches_hash"] is True
