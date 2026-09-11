import json


def _hex(addr):
    if isinstance(addr, (bytes, bytearray)):
        from genlayer.py.types import Address
        return Address(bytes(addr)).as_hex
    return str(addr)


def test_submit_resolve_read_happy_path(direct_vm, direct_deploy, direct_alice):
    """Happy path: submit claim, resolve with AI consensus, read verdict + reasoning."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    evidence = "NASA confirms: Earth orbits the Sun. Source: https://nasa.gov/earth"
    
    # 1. SUBMIT
    contract.submit_claim(
        "claim-1",
        "The Earth orbits the Sun",
        evidence,
        "Science",
        _hex(direct_alice)
    )

    claim = json.loads(contract.get_claim("claim-1"))
    assert claim["exists"] is True
    assert claim["text"] == "The Earth orbits the Sun"
    assert claim["evidence_url"] == evidence
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


def test_reject_verdict(direct_vm, direct_deploy, direct_alice):
    """Verify REJECTED path."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    evidence = "Flat Earth Society claims: Earth is flat. Source: https://flatearth.org"
    contract.submit_claim("claim-2", "The Earth is flat", evidence, "Science", _hex(direct_alice))

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
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    evidence = "Insufficient data to determine."
    contract.submit_claim("claim-3", "Life exists on Mars", evidence, "Science", _hex(direct_alice))

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "INCONCLUSIVE",
        "confidence": 25,
        "reasoning": "Insufficient evidence to confirm or deny life on Mars."
    }))
    verdict = contract.resolve_claim("claim-3")

    claim = json.loads(contract.get_claim("claim-3"))
    assert verdict == "INCONCLUSIVE"
    assert claim["verdict"] == "INCONCLUSIVE"


def test_reject_double_resolve(direct_vm, direct_deploy, direct_alice):
    """Verify resolving an already-resolved claim fails."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    contract.submit_claim("claim-5", "Test", "Evidence", "General", _hex(direct_alice))

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "VERIFIED",
        "confidence": 80,
        "reasoning": "Looks good"
    }))
    contract.resolve_claim("claim-5")

    # Second resolve should fail
    try:
        contract.resolve_claim("claim-5")
        assert False, "Should have reverted"
    except Exception as e:
        assert "already resolved" in str(e.message)


def test_submit_duplicate_claim_throws(direct_vm, direct_deploy, direct_alice):
    """Verify duplicate claim submission fails."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    contract.submit_claim("claim-6", "First", "Evidence", "General", _hex(direct_alice))

    try:
        contract.submit_claim("claim-6", "Second", "Evidence", "General", _hex(direct_alice))
        assert False, "Should have reverted"
    except Exception as e:
        assert "already exists" in str(e.message)


def test_get_claim_not_found(direct_vm, direct_deploy, direct_alice):
    """Verify get_claim returns exists=False for unknown claim."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    claim = json.loads(contract.get_claim("nonexistent"))
    assert claim["exists"] is False


def test_get_claims_count(direct_vm, direct_deploy, direct_alice):
    """Verify get_claims_count returns correct count."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    contract.submit_claim("claim-7", "Claim 7", "Evidence", "Tech", _hex(direct_alice))
    contract.submit_claim("claim-8", "Claim 8", "Evidence", "Tech", _hex(direct_alice))

    assert contract.get_claims_count() == "2"


def test_appeal_flow(direct_vm, direct_deploy, direct_alice):
    """Verify appeal flow works."""
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/evidence_claim_escrow.py")

    contract.submit_claim("claim-9", "Test claim", "Evidence", "General", _hex(direct_alice))

    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "REJECTED",
        "confidence": 80,
        "reasoning": "Rejected"
    }))
    contract.resolve_claim("claim-9")

    # Appeal
    contract.appeal_verdict("claim-9")

    appeal = json.loads(contract.get_appeal("appeal-claim-9-1"))
    assert appeal["exists"] is True
    assert appeal["original_verdict"] == "REJECTED"

    # Finalize appeal
    direct_vm.mock_llm(r".*", json.dumps({
        "verdict": "VERIFIED",
        "confidence": 90,
        "reasoning": "On second look, verified"
    }))
    contract.finalize_appeal("appeal-claim-9-1")

    claim = json.loads(contract.get_claim("claim-9"))
    assert claim["verdict"] == "VERIFIED"
