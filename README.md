# Universal AI Governance (UAIG) Gateway

**Enterprise-Grade SMT Formal Verification Proxy for Large Language Model Systems**  
*Compliant with FDA CSA Draft Guidance (2022), GAMP 5 Second Edition, and 21 CFR Part 11*

---

## 1. Executive Summary
The **Universal AI Governance (UAIG) Gateway** is an authoritative neuro-symbolic execution proxy designed for deployment in regulated enterprise environments (Life Sciences, MedTech, Financial Infrastructure). The system eliminates non-deterministic model parameter hallucination by executing automated First-Order Predicate Logic assertions via an embedded SMT theorem prover (**Microsoft Z3**) prior to downstream API or tool invocation.

Live Governance Console & Demonstration: [https://ai-governance-engine.github.io](https://ai-governance-engine.github.io)

---

## 2. Architecture Specification (IEEE 1471 / ISO 42010)

```
+-----------------------------------------------------------------------------+
|                            ENTERPRISE CLIENT APPLICATION                    |
+-----------------------------------------------------------------------------+
                                       |
                                       | 1. Dispatches Unverified Tool Request
                                       v
+-----------------------------------------------------------------------------+
|               UAIG GATEWAY (REVERSE PROXY / INGESTION LAYER)                |
|  - OpenAPI 3.1 Contract Validation (Pydantic V2 AST Parser)                 |
|  - Context Resolution (Clearance, Role, Transaction Quota, Session Hash)    |
+-----------------------------------------------------------------------------+
                                       |
                                       | 2. Maps Payload to Formal Invariants
                                       v
+-----------------------------------------------------------------------------+
|                   Z3 SMT FORMAL VERIFICATION SUBSYSTEM                      |
|  - Translation Engine: JSON AST -> First-Order Predicate Logic              |
|  - Logic Solver: Microsoft Z3 SMT Theorem Prover (Linear/Nonlinear Arith.)  |
|  - Decision Engine: Solvability Check (SAT / UNSAT / UNKNOWN)               |
|  - UNSAT Core Extraction: Isolate Minimal Violating Clause Set              |
+-----------------------------------------------------------------------------+
          |                                                       |
          | SAT (Proven Invariant Compliance)                     | UNSAT (Policy Violated)
          v                                                       v
+------------------------------------+  +-------------------------------------+
|        DOWNSTREAM DISPATCH         |  |      BLOCK & REMEDIATION ENGINE     |
| - Forward payload to target API    |  | - Suppress downstream execution     |
| - Return 200 OK + Proof Attestation|  | - Return 422 Unprocessable Entity   |
+------------------------------------+  | - Return Formal Refutation Proof    |
                   |                    +-------------------------------------+
                   |                                       |
                   +-------------------+-------------------+
                                       |
                                       | 3. Emit Deterministic Event Record
                                       v
+-----------------------------------------------------------------------------+
|                TAMPER-EVIDENT AUDIT SUBSYSTEM (21 CFR PART 11)              |
|  - WAL-Mode Relational Persistence (SQLite Engine)                          |
|  - Cryptographic Hash Chain: Record_N = SHA256(Record_N-1 || Payload || Res)|
|  - Immutable Timestamping, Session Identity, and Digital Signature Proof   |
+-----------------------------------------------------------------------------+
```

---

## 3. Formal Invariant Specifications

| Policy ID | Category | Formal Mathematical Specification | Failure Diagnostic |
| :--- | :--- | :--- | :--- |
| **POL-SEC-001** | Clearance Boundary | `req_clearance <= user_clearance` | Required security clearance exceeds authenticated user clearance. |
| **POL-FIN-001** | Financial Boundary | `transaction_amount >= 0.0 AND transaction_amount <= max_transaction` | Proposed transaction amount violates enterprise budget envelope. |
| **POL-REG-001** | PHI / HIPAA Boundary | `is_phi_data IMPLIES user_is_clinical` | Protected Health Information requested by non-clinical principal. |

---

## 4. Controlled Regulatory Documentation

All specifications follow GAMP 5 Category 5 software qualification standards:

- **[IEEE 1471 Architectural Blueprint](docs/IEEE-1471-ARCHITECTURE-BLUEPRINT.md)**: Formal architectural description per ISO/IEC/IEEE 42010.
- **[User Requirement Specification (URS)](docs/URS-UAIG-001.md)**: 10 formal user requirements (`URS-001` through `URS-010`).
- **[Functional Requirement Specification (FRS)](docs/FRS-UAIG-001.md)**: Functional allocation and SMT solver parameters.
- **[CSA Validation Summary Report](docs/CSA-VALIDATION-SUMMARY-REPORT.md)**: Automated qualification execution report sealed with cryptographic SHA-256 digital digest.

---

## 5. Verification and Qualification Execution

### Execute Unit & Formal Invariant Tests
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### Execute Automated CSA Qualification Protocol
```bash
python tests/test_csa_qualification.py
python scripts/generate_rtm_csa_report.py
```

### Launch Proxy Gateway (FastAPI / ASGI)
```bash
uvicorn uaig_core.gateway:app --host 0.0.0.0 --port 8000
```
API Documentation available at `http://localhost:8000/docs` (OpenAPI 3.1).

---

## 6. Regulatory Attestation
The UAIG Gateway has been qualified with 100% test pass rate across 10 qualification test vectors. All verification decisions commit append-only, cryptographically linked electronic records conforming to FDA 21 CFR Part 11 Section 11.10.
