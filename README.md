# Intelligence: Decentralized Evidence-Based Claim Escrow

**Tagline** — A reusable, on-chain escrow primitive that stores raw evidence, lets a trusted validator resolve claims, and guarantees GEN payout integrity.

## Why it matters

Builders of prediction markets, staking-task platforms, or any service that requires verifiable dispute resolution need a generic claim-handling core. Intelligence provides that core without tying you to a specific front-end.

## Consensus Design

- **GenVM** — contract compilation and deployment validated by GenLayer
- **Optimistic Democracy** — only the designated validator can resolve claims
- **Equivalence Principle** — evidence stored as keccak256(rawEvidence); the hash is publicly verifiable and matches the on-chain copy

## Architecture

```
User → submit_claim(claim_id, text, evidence_url, category) → claim stored
Validator → resolve_claim(claim_id) → AI consensus → verdict + reasoning stored
Anyone → get_claim(claim_id) → full claim with verdict
Anyone → get_evidence(claim_id) → evidence hash + verification
```

## State Design

| Field | Type | Purpose |
|-------|------|---------|
| id | str | Unique claim identifier |
| text | str | Claim text |
| evidence_url | str | URL of evidence |
| category | str | Claim category |
| poster | str | Submitter address |
| claimant | str | Claimant address (receives payout) |
| amount | u256 | Escrowed GEN |
| timestamp | u256 | Submission time |
| resolved | bool | Resolution status |
| verdict | str | VERIFIED/REJECTED/INCONCLUSIVE |
| confidence | u256 | 0-100 score |
| reasoning | str | AI evidence assessment |
| resolved_at | u256 | Resolution time |
| appeal_count | u256 | Number of appeals |

## Safety Notes

- No external calls before state update (re-entrancy safe)
- Only validator can resolve claims
- Validator can be replaced via `set_validator`
- Evidence hash verification via `get_evidence`

## API

| Function | Params | Returns | Notes |
|----------|--------|---------|-------|
| submit_claim | claim_id, text, evidence_url, category, claimant | None | Payable. Stores claim + escrow |
| resolve_claim | claim_id | verdict | Only validator. AI consensus. |
| appeal_verdict | claim_id | str | Payable. 1 GEN bond. |
| finalize_appeal | appeal_id | verdict | Only validator. |
| get_claim | claim_id | JSON | Full claim with verdict |
| get_appeal | appeal_id | JSON | Full appeal state |
| get_claims_count | None | str | Total claims |
| now | None | str | Current timestamp |

## Deploy & Test

```bash
# Install dependencies
pip install genlayer

# Deploy to Studio (fast testing)
genlayer deploy --contract contracts/Intelligence.py --rpc https://studio.genlayer.com/api

# Deploy to Bradbury (real testnet)
genlayer deploy --contract contracts/Intelligence.py

# Run tests
python -m pytest tests/test_intelligence.py -v
```

## License
MIT
