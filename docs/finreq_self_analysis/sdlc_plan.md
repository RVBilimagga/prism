# SDLC recommendation

| Model | Fit |
|---|---|
| Agile–DevSecOps hybrid | 64.2% |
| Agile–V-Model hybrid | 63.7% |
| DevSecOps | 63.2% |
| V-Model | 55.8% |
| Spiral | 52.6% |
| Waterfall | 52.1% |
| Agile | 44.2% |

## Chosen model: Agile–DevSecOps hybrid

- In favour: Security risk is high (1.00)
- In favour: Regulatory criticality is high (1.00)
- In favour: Expected frequency of change is high (0.80)
- Against: Requirement stability is high (0.80)
- Against: Need for continuous delivery is low (0.30)

## Decision factors

| Factor | Value | Source |
|---|---|---|
| Requirement stability | 0.80 | derived from requirements |
| Regulatory criticality | 1.00 | derived from requirements |
| Security risk | 1.00 | derived from requirements |
| Project complexity and size | 0.60 | project profile |
| Legacy-system dependence | 0.10 | derived from requirements |
| Expected frequency of change | 0.80 | project profile |
| Need for continuous delivery | 0.30 | project profile |
| Stakeholder availability | 0.90 | project profile |
| Need for formal verification | 0.60 | project profile |
| Consequence of failure | 0.30 | project profile |
| Budget and schedule pressure | 0.80 | project profile |
| Technical uncertainty | 0.80 | project profile |
| Testing and documentation needs | 0.90 | project profile |

## Workflow

### 1. Planning

- Activities: Agree scope, budget and schedule; Baseline the risk register
- Roles: Project manager, Business analyst
- Deliverables: Project plan, Risk register
- Exit gate: Project manager and compliance officer sign off scope

### 2. Sprint (repeats each iteration)

- Activities: Backlog refinement; Build and test the increment; Review and retrospective
- Roles: Product owner, Delivery team
- Deliverables: Working increment, Updated backlog
- Exit gate: Definition of done met; changed requirements re-approved

### 3. Secure delivery pipeline (repeats each iteration)

- Activities: Automated build and tests; SAST and dependency scanning; Policy-as-code compliance checks
- Roles: DevSecOps engineer
- Deliverables: Pipeline run evidence
- Exit gate: All automated gates green

### 4. Deployment

- Activities: Compliance approval; Release with rollback plan
- Roles: Release manager, Compliance officer
- Deliverables: Release notes, Compliance approval record
- Exit gate: Compliance approval recorded before production

### 5. Operations

- Activities: Monitoring; Audit logging; Incident response
- Roles: Operations
- Deliverables: Monitoring reports, Audit logs
- Exit gate: Periodic audit review

## Sign-off

- Project manager: pending
- Architect: pending
- Security lead: pending
- Compliance officer: pending

Status: awaiting sign-off.
