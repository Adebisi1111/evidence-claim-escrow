# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Intelligence Evidence-Based Claim Escrow v2
#
# A reusable, on-chain escrow primitive where AI validators independently research
# claims via web-tethered consensus, then route funds based on verified verdicts.

import json
from genlayer import *


class IntelligenceClaimEscrow(gl.Contract):
    next_escrow_id: u256
    escrows: TreeMap[u256, dict]

    def __init__(self):
        self.next_escrow_id = u256(0)
        self.escrows = TreeMap[u256, dict]()

    def _verify_consensus_payload(self, proposed_output: str, validator_output: str) -> bool:
        """
        Consensus Guard Rail: Independently binds every variable affecting state metrics 
        to ensure nodes reach absolute consensus before execution.
        """
        try:
            prop = json.loads(proposed_output)
            val = json.loads(validator_output)
            
            # Explicitly bind categorical outcomes and metrics
            if prop["verdict"] != val["verdict"]:
                return False
            if prop["quality_score"] != val["quality_score"]:
                return False
            if prop["confidence_score"] != val["confidence_score"]:
                return False
                
            return True
        except (KeyError, TypeError, json.JSONDecodeError):
            return False

    def _process_adjudication_lifecycle(self, escrow_id: u256, checked_json: str):
        """Substantive financial state routing based on verified results."""
        data = json.loads(checked_json)
        record = self.escrows[escrow_id]
        
        record["quality_score"] = data["quality_score"]
        record["confidence_score"] = data["confidence_score"]
        record["verdict"] = data["verdict"]
        
        if data["verdict"] == "SUPPORTED":
            record["status"] = "RESOLVED"
            # Substantive Action: Claim is valid; release escrow funds to claimant
            _Recipient(Address(record["claimant"])).emit_transfer(value=u256(record["amount"]))
        else:
            record["status"] = "REFUTED"
            # Substantive Action: Claim is refuted; return funds to depositor
            _Recipient(Address(record["depositor"])).emit_transfer(value=u256(record["amount"]))
        
        self.escrows[escrow_id] = record

    @gl.public.write.payable
    def createClaimEscrow(self, claim: str, claimant: str) -> u256:
        """Locks funds into escrow and triggers a single, web-tethered research verification flow."""
        if gl.message.value <= u256(0):
            raise gl.vm.UserError("Escrow must be funded with GEN")
        
        escrow_id = self.next_escrow_id
        self.next_escrow_id += u256(1)
        
        self.escrows[escrow_id] = {
            "claim": claim,
            "depositor": str(gl.message.sender_address),
            "claimant": claimant,
            "amount": int(gl.message.value),
            "status": "RESEARCHING",
            "quality_score": 0,
            "confidence_score": 0,
            "verdict": ""
        }
        
        # Single prompt directing the node to independently research the live web
        research_prompt = (
            f"You are an authoritative, objective fact-checking validator.\n"
            f"Do NOT rely on user-provided text. You must use your web-browsing capability to\n"
            f"independently research the following claim: '{claim}'.\n\n"
            f"Find reliable web sources and output EXACTLY a valid JSON object matching this structure:\n"
            f'{{"verdict": "SUPPORTED" or "REFUTED", "quality_score": <int 1-100>, "confidence_score": <int 1-100>}}'
        )
        
        # Exactly one non-deterministic execution point
        adjudication_result = gl.vm.run_nondet(
            prompt=research_prompt,
            validator=self._verify_consensus_payload
        )
        
        self._process_adjudication_lifecycle(escrow_id, adjudication_result)
        
        return escrow_id

    @gl.public.view
    def get_escrow(self, escrow_id: u256) -> str:
        """Get full escrow details."""
        record = self.escrows.get(escrow_id, None)
        if record is None:
            return json.dumps({"escrow_id": int(escrow_id), "exists": False})
        return json.dumps({
            "escrow_id": int(escrow_id),
            "exists": True,
            "claim": record["claim"],
            "depositor": record["depositor"],
            "claimant": record["claimant"],
            "amount": record["amount"],
            "status": record["status"],
            "quality_score": record["quality_score"],
            "confidence_score": record["confidence_score"],
            "verdict": record["verdict"]
        })

    @gl.public.view
    def get_escrows_count(self) -> str:
        return str(len(self.escrows))
