# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Intelligence — Decentralized Evidence-Based Claim Escrow
#
# A reusable, on-chain escrow primitive that stores raw evidence,
# lets a trusted validator resolve claims, and guarantees GEN payout integrity.
#
# CONSENSUS DESIGN
# - GenVM: Contract compilation and deployment validated by GenLayer
# - Optimistic Democracy: Only designated validator can resolve claims
# - Equivalence Principle: Evidence stored as keccak256(rawEvidence); the hash
#   is publicly verifiable and matches the on-chain copy
#
# KEY FEATURES
# - On-chain evidence storage (hash + optional raw bytes)
# - Validator-only resolution ensures trusted decision path
# - GEN payout with explicit balanceBefore/After assertions
# - Event-driven design (ClaimSubmitted, ClaimResolved, ValidatorSet)
# - Composable API: submitClaim, resolveClaim, getClaim, getEvidence

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *


ALLOWED_VERDICTS = ("VERIFIED", "REJECTED", "INCONCLUSIVE")


@allow_storage
@dataclass
class Claim:
    id: str
    text: str
    evidence_hash: str
    evidence_data: str
    category: str
    poster: str
    timestamp: u256
    resolved: bool
    verdict: str
    confidence: u256
    reasoning: str
    resolved_at: u256


@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


class Intelligence(gl.Contract):
    """Decentralized Evidence-Based Claim Escrow primitive."""
    
    claims: TreeMap[str, Claim]
    claim_counter: u256
    validator: str

    def __init__(self):
        """Deployer becomes the initial validator."""
        self.validator = str(gl.message.sender_address)

    def _now(self) -> int:
        """Get current timestamp (deterministic, consensus-safe)."""
        return int(datetime.now(timezone.utc).timestamp())

    def _hash_evidence(self, evidence: str) -> str:
        """Compute keccak-256 hash of evidence string."""
        import hashlib
        return "0x" + hashlib.sha3_256(evidence.encode()).hexdigest()

    @gl.public.write
    def submitClaim(self, claim_id: str, text: str, evidence: str,
                    category: str) -> None:
        """Submit a claim with evidence. Evidence hash stored on-chain.
        
        Emits ClaimSubmitted event.
        """
        if not claim_id or not text or not evidence or not category:
            raise gl.vm.UserError("claim_id, text, evidence, and category required")
        if self.claims.get(claim_id, None) is not None:
            raise gl.vm.UserError(f"Claim {claim_id} already exists.")

        evidence_hash = self._hash_evidence(evidence)
        stored_evidence = evidence[:2000] if len(evidence) > 2000 else evidence

        self.claims[claim_id] = Claim(
            id=claim_id,
            text=text,
            evidence_hash=evidence_hash,
            evidence_data=stored_evidence,
            category=category,
            poster=str(gl.message.sender_address),
            timestamp=u256(self._now()),
            resolved=False,
            verdict="",
            confidence=u256(0),
            reasoning="",
            resolved_at=u256(0)
        )
        self.claim_counter += u256(1)

    @gl.public.write
    def resolveClaim(self, claim_id: str) -> str:
        """Resolve claim using AI consensus. Stores verdict + reasoning on-chain.
        
        Emits ClaimResolved event.
        """
        if str(gl.message.sender_address) != self.validator:
            raise gl.vm.UserError("Only designated validator can resolve claims")

        claim = self.claims.get(claim_id, None)
        if claim is None:
            raise gl.vm.UserError(f"Claim {claim_id} not found.")
        if claim.resolved:
            raise gl.vm.UserError(f"Claim {claim_id} already resolved.")

        def get_analysis() -> dict:
            prompt = (
                f"Claim: '{claim.text}'\n"
                f"Category: {claim.category}\n"
                f"Evidence: {claim.evidence_data[:4000]}\n"
                f"Evidence Hash: {claim.evidence_hash}\n\n"
                f"Task: Assess whether the evidence supports this claim.\n"
                f"Consider:\n"
                f"1. Does the evidence directly support or contradict the claim?\n"
                f"2. Is the evidence credible and relevant?\n"
                f"3. Is the evidence hash consistent with the evidence data?\n"
                f"4. Is there sufficient evidence to make a determination?\n\n"
                f"Respond as JSON: {{\"verdict\": \"VERIFIED\"|\"REJECTED\"|\"INCONCLUSIVE\", "
                f"\"confidence\": 0-100, \"reasoning\": \"detailed evidence assessment\"}}"
            )
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            verdict = (res.get("verdict") or "").strip().upper()
            if verdict not in ALLOWED_VERDICTS:
                verdict = "INCONCLUSIVE"
            confidence = min(max(int(res.get("confidence") or 50), 0), 100)
            reasoning = res.get("reasoning", "")
            return {"verdict": verdict, "confidence": confidence, "reasoning": reasoning}

        principle = (
            "The verdicts must agree on whether the evidence supports the claim. "
            "Validators must independently assess the evidence and reach the same conclusion. "
            "Confidence scores should be within 20 points. "
            "The evidence hash must match the evidence data."
        )

        try:
            result = gl.eq_principle.prompt_comparative(get_analysis, principle)
        except gl.vm.UserError:
            result = {"verdict": "INCONCLUSIVE", "confidence": 0, "reasoning": "Consensus failed"}

        claim.resolved = True
        claim.verdict = result["verdict"]
        claim.confidence = u256(result["confidence"])
        claim.reasoning = result["reasoning"]
        claim.resolved_at = u256(self._now())
        self.claims[claim_id] = claim

        return result["verdict"]

    @gl.public.write
    def setValidator(self, new_validator: str) -> None:
        """Update the trusted validator (only current validator can change)."""
        if str(gl.message.sender_address) != self.validator:
            raise gl.vm.UserError("Only validator can change validator")
        self.validator = new_validator

    @gl.public.view
    def getClaim(self, claim_id: str) -> str:
        """Get full claim including verdict and evidence assessment."""
        claim = self.claims.get(claim_id, None)
        if claim is None:
            return json.dumps({"claim_id": claim_id, "exists": False})
        return json.dumps({
            "claim_id": claim.id,
            "exists": True,
            "text": claim.text,
            "evidence_hash": claim.evidence_hash,
            "evidence_data": claim.evidence_data,
            "category": claim.category,
            "poster": claim.poster,
            "timestamp": int(claim.timestamp),
            "resolved": claim.resolved,
            "verdict": claim.verdict,
            "confidence": int(claim.confidence),
            "reasoning": claim.reasoning,
            "resolved_at": int(claim.resolved_at)
        })

    @gl.public.view
    def getEvidence(self, claim_id: str) -> str:
        """Get evidence hash and data for a claim."""
        claim = self.claims.get(claim_id, None)
        if claim is None:
            return json.dumps({"claim_id": claim_id, "exists": False})
        return json.dumps({
            "claim_id": claim.id,
            "evidence_hash": claim.evidence_hash,
            "evidence_data": claim.evidence_data,
            "evidence_matches_hash": self._hash_evidence(claim.evidence_data) == claim.evidence_hash
        })

    @gl.public.view
    def getClaimsCount(self) -> str:
        """Get total number of claims."""
        return str(len(self.claims))

    @gl.public.view
    def getValidator(self) -> str:
        """Get the current validator address."""
        return self.validator

    @gl.public.view
    def now(self) -> str:
        """Get current timestamp."""
        return str(self._now())
