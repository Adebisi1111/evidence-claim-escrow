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
User → submitClaim(claim_id, text, evidence, category) → claim stored
Validator → resolveClaim(claim_id) → AI consensus → verdict + reasoning stored
Anyone → getClaim(claim_id) → full claim with verdict
Anyone → getEvidence(claim_id) → evidence hash + verification
```

## State Design

| Field | Type | Purpose |
|-------|------|---------|
| id | str | Unique claim identifier |
| text | str | Claim text |
| evidence_hash | str | keccak256 hash of evidence |
| evidence_data | str | Truncated evidence (2000 chars max) |
| category | str | Claim category |
| poster | str | Submitter address |
| timestamp | u256 | Submission time |
| resolved | bool | Resolution status |
| verdict | str | VERIFIED/REJECTED/INCONCLUSIVE |
| confidence | u256 | 0-100 score |
| reasoning | str | AI evidence assessment |
| resolved_at | u256 | Resolution time |

## Safety Notes

- No external calls before state update (re-entrancy safe)
- Only validator can resolve claims
- Validator can be replaced via `setValidator`
- Evidence hash verification via `getEvidence`

## API

| Function | Params | Returns | Notes |
|----------|--------|---------|-------|
| submitClaim | claim_id, text, evidence, category | None | Stores claim + evidence hash |
| resolveClaim | claim_id | verdict | Only validator. AI consensus. |
| setValidator | new_validator | None | Only current validator |
| getClaim | claim_id | JSON | Full claim with verdict |
| getEvidence | claim_id | JSON | Evidence hash + verification |
| getClaimsCount | None | str | Total claims |
| getValidator | None | str | Current validator |

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
