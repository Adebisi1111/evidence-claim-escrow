# Intelligence: Decentralized Evidence-Based Claim Escrow

**Tagline** — A reusable, on-chain escrow primitive where AI validators fetch and assess evidence via consensus, then update participant reputation based on the verdict.

## Why it matters

Builders of prediction markets, staking-task platforms, or any service that requires verifiable dispute resolution need a generic claim-handling core. Intelligence provides that core without tying you to a specific front-end.

## Consensus Design

- **GenVM** — contract compilation and deployment validated by GenLayer
- **Single-Flow Verification** — evidence is fetched and assessed in ONE non-deterministic call
- **Validator Binding** — validators re-run the full fetch+assessment and compare every field (verdict + confidence)
- **Reputation Tracking** — every verified/rejected claim updates participant stats on-chain

## Architecture

```
User → submit_claim(claim_id, text, evidence_url, category) → funds escrowed
       ↓
resolve_claim(claim_id) → fetch evidence + assess via consensus
       ↓
       ├─ VERIFIED → funds released to claimant + reputation updated
       ├─ REJECTED → funds returned to poster + reputation updated
       └─ INCONCLUSIVE → funds stay in escrow

appeal_verdict(claim_id) → pay bond → reset claim for re-assessment
       ↓
finalize_appeal(appeal_id) → re-run consensus → update reputation
```

## State Design

| Field | Type | Purpose |
|-------|------|---------|
| id | str | Unique claim identifier |
| text | str | Claim text |
| evidence_url | str | URL of evidence (fetched in nondet flow) |
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

## Participant Reputation

| Field | Purpose |
|-------|---------|
| verified_claims | Count of VERIFIED verdicts |
| rejected_claims | Count of REJECTED verdicts |
| total_escrowed | Total GEN escrowed across all claims |

## Key Safeguards

- **Single nondeterministic flow** — evidence fetched and assessed in ONE call (no nested nondet)
- **Full field binding** — validators compare verdict AND confidence (±20 tolerance)
- **Reputation state effect** — every resolution updates participant stats on-chain
- **Appeal lifecycle** — bond required, resets claim, re-runs full consensus
