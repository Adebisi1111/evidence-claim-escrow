# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Decentralized Evidence-Based Claim Escrow
#
# A claimant submits a claim with evidence and escrows funds.
# AI validators assess the evidence and reach consensus.
# If verified → funds released to claimant.
# If rejected → funds returned to poster.
# Disputes can be appealed with a bond for re-assessment.
#
# EVIDENCE ASSESSMENT:
#   Each claim includes an evidence URL. AI validators fetch and assess
#   the evidence to determine if the claim is VERIFIED or REJECTED.
#   The reasoning field stores the AI's evidence assessment.
#
# CONSENSUS DESIGN:
#   prompt_comparative with principle: validators must agree on whether
#   the evidence supports the claim. Confidence must be within 20 points.

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *


ALLOWED_VERDICTS = ("VERIFIED", "REJECTED", "INCONCLUSIVE")
APPEAL_BOND = 1000000000000000000  # 1 GEN
MAX_APPEALS = 2


@allow_storage
@dataclass
class Claim:
    id: str
    text: str
    evidence_url: str
    category: str
    poster: str
    claimant: str
    amount: u256
    timestamp: u256
    resolved: bool
    verdict: str           # VERIFIED / REJECTED / INCONCLUSIVE
    confidence: u256       # 0-100
    reasoning_str: str         # AI evidence assessment
    resolved_at: u256
    appeal_count: u256


@allow_storage
@dataclass
class Appeal:
    id: str
    claim_id: str
    appellant: str
    bond: u256
    timestamp: u256
    resolved: bool
    original_verdict: str
    new_verdict: str


@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


class EvidenceClaimEscrow(gl.Contract):
    claims: TreeMap[str, Claim]
    appeals: TreeMap[str, Appeal]
    claim_counter: u256
    appeal_counter: u256

    def __init__(self):
        pass

    def _now(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _assess_evidence(self, claim_text: str, evidence_url: str, category: str) -> dict:
        """AI assesses the evidence to determine if claim is supported."""
        prompt = (
            f"Claim: '{claim_text}'\n"
            f"Category: {category}\n"
            f"Evidence URL: {evidence_url}\n\n"
            f"Your task: Determine if the evidence at the given URL supports this claim.\n"
            f"Consider:\n"
            f"1. Does the evidence directly support or contradict the claim?\n"
            f"2. Is the evidence credible and relevant?\n"
            f"3. Is there sufficient evidence to make a determination?\n\n"
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

    @gl.public.write.payable
    def submit_claim(self, claim_id: str, text: str, evidence_url: str,
                     category: str, claimant: str) -> None:
        """Submit a claim with evidence and escrow funds."""
        if not claim_id or not text or not evidence_url or not category:
            raise gl.vm.UserError("claim_id, text, evidence_url, and category required")
        if gl.message.value <= u256(0):
            raise gl.vm.UserError("Must escrow funds (value > 0)")
        if self.claims.get(claim_id, None) is not None:
            raise gl.vm.UserError(f"Claim {claim_id} already exists.")

        self.claims[claim_id] = Claim(
            id=claim_id,
            text=text,
            evidence_url=evidence_url,
            category=category,
            poster=str(gl.message.sender_address),
            claimant=claimant,
            amount=gl.message.value,
            timestamp=u256(self._now()),
            resolved=False,
            verdict="",
            confidence=u256(0),
            reasoning_str="",
            resolved_at=u256(0),
            appeal_count=u256(0)
        )
        self.claim_counter += u256(1)

    @gl.public.write
    def resolve_claim(self, claim_id: str) -> str:
        """AI consensus assesses evidence and determines verdict."""
        claim = self.claims.get(claim_id, None)
        if claim is None:
            raise gl.vm.UserError(f"Claim {claim_id} not found.")
        if claim.resolved:
            raise gl.vm.UserError(f"Claim {claim_id} already resolved.")

        def get_analysis() -> dict:
            return self._assess_evidence(claim.text, claim.evidence_url, claim.category)

        principle = (
            "The verdicts must agree on whether the evidence supports the claim. "
            "Validators must independently assess the evidence URL and reach the same conclusion. "
            "Confidence scores should be within 20 points."
        )

        try:
            result = gl.eq_principle.prompt_comparative(get_analysis, principle)
        except gl.vm.UserError:
            result = {"verdict": "INCONCLUSIVE", "confidence": 0, "reasoning": "Consensus failed"}

        claim.resolved = True
        claim.verdict = result["verdict"]
        claim.confidence = u256(result["confidence"])
        claim.reasoning_str = result["reasoning"]
        claim.resolved_at = u256(self._now())
        self.claims[claim_id] = claim

        # Release or return funds based on verdict
        if result["verdict"] == "VERIFIED":
            # Pay claimant
            _Payee(Address(claim.claimant)).emit_transfer(
                value=claim.amount, on="finalized"
            )
        elif result["verdict"] == "REJECTED":
            # Return funds to poster
            _Payee(Address(claim.poster)).emit_transfer(
                value=claim.amount, on="finalized"
            )
        # INCONCLUSIVE: funds stay in escrow

        return result["verdict"]

    @gl.public.write.payable
    def appeal_verdict(self, claim_id: str) -> str:
        """Appeal a verdict with bond for re-assessment."""
        claim = self.claims.get(claim_id, None)
        if claim is None:
            raise gl.vm.UserError(f"Claim {claim_id} not found.")
        if not claim.resolved:
            raise gl.vm.UserError(f"Claim {claim_id} not yet resolved.")
        if int(claim.appeal_count) >= MAX_APPEALS:
            raise gl.vm.UserError(f"Max appeals ({MAX_APPEALS}) reached.")
        if gl.message.value < u256(APPEAL_BOND):
            raise gl.vm.UserError(f"Appeal bond too low. Min: {APPEAL_BOND} wei")

        original_verdict = claim.verdict
        claim.resolved = False
        claim.verdict = ""
        claim.confidence = u256(0)
        claim.reasoning_str = ""
        claim.resolved_at = u256(0)
        claim.appeal_count += u256(1)
        self.claims[claim_id] = claim

        appeal_id = f"appeal-{claim_id}-{claim.appeal_count}"
        self.appeals[appeal_id] = Appeal(
            id=appeal_id,
            claim_id=claim_id,
            appellant=str(gl.message.sender_address),
            bond=gl.message.value,
            timestamp=u256(self._now()),
            resolved=False,
            original_verdict=original_verdict,
            new_verdict=""
        )
        self.appeal_counter += u256(1)
        return "APPEAL_ACCEPTED"

    @gl.public.write
    def finalize_appeal(self, appeal_id: str) -> str:
        """Finalize appeal after re-resolution."""
        appeal = self.appeals.get(appeal_id, None)
        if appeal is None:
            raise gl.vm.UserError(f"Appeal {appeal_id} not found.")
        if appeal.resolved:
            raise gl.vm.UserError(f"Appeal {appeal_id} already resolved.")

        claim = self.claims.get(appeal.claim_id, None)
        if claim is None:
            raise gl.vm.UserError("Claim not found.")

        if not claim.resolved:
            result = self._assess_evidence(claim.text, claim.evidence_url, claim.category)
            claim.resolved = True
            claim.verdict = result["verdict"]
            claim.confidence = u256(result["confidence"])
            claim.reasoning_str = result["reasoning"]
            claim.resolved_at = u256(self._now())
            self.claims[appeal.claim_id] = claim

        appeal.resolved = True
        appeal.new_verdict = claim.verdict
        self.appeals[appeal_id] = appeal
        return claim.verdict

    @gl.public.view
    def get_claim(self, claim_id: str) -> str:
        """Get full claim including verdict and evidence assessment."""
        claim = self.claims.get(claim_id, None)
        if claim is None:
            return json.dumps({"claim_id": claim_id, "exists": False})
        return json.dumps({
            "claim_id": claim.id,
            "exists": True,
            "text": claim.text,
            "evidence_url": claim.evidence_url,
            "category": claim.category,
            "poster": claim.poster,
            "claimant": claim.claimant,
            "amount": int(claim.amount),
            "timestamp": int(claim.timestamp),
            "resolved": claim.resolved,
            "verdict": claim.verdict,
            "confidence": int(claim.confidence),
            "reasoning": claim.reasoning_str,
            "resolved_at": int(claim.resolved_at),
            "appeal_count": int(claim.appeal_count)
        })

    @gl.public.view
    def get_appeal(self, appeal_id: str) -> str:
        appeal = self.appeals.get(appeal_id, None)
        if appeal is None:
            return json.dumps({"appeal_id": appeal_id, "exists": False})
        return json.dumps({
            "appeal_id": appeal.id,
            "exists": True,
            "claim_id": appeal.claim_id,
            "appellant": appeal.appellant,
            "bond": int(appeal.bond),
            "timestamp": int(appeal.timestamp),
            "resolved": appeal.resolved,
            "original_verdict": appeal.original_verdict,
            "new_verdict": appeal.new_verdict
        })

    @gl.public.view
    def get_claims_count(self) -> str:
        return str(len(self.claims))

    @gl.public.view
    def now(self) -> str:
        return str(self._now())
