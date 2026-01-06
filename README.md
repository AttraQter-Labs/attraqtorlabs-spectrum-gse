# Spectrum GSE — Canonical v1.0.0

Spectrum GSE is a deterministic validation and analysis engine for quantum circuits.  
Version 1.0.0 is behaviorally frozen: no learning, no optimization, no topology mutation.

## Positioning
- Deterministic stabilizer: bounded angle scaling only on rotation gates.
- Non-learning and non-adaptive by design.
- Intended for post-analysis, validation, and verification workflows across academic and enterprise settings.

## Capabilities
- Accepts QASM2 strings or `qiskit.QuantumCircuit` objects.
- Produces a stabilized circuit with deterministic, identity-derived scaling.
- Optional Aer-based simulation helper for quick histogram checks.

## Installation
```bash
pip install -r requirements.txt
```

## Minimal Usage
```python
from spectrum_gse import SpectrumGSE

engine = SpectrumGSE(identity="example-user")
stabilized = engine.stabilize(qasm_or_circuit)
```

CLI entry point:
```bash
python -m spectrum_gse.engine --identity example-user < circuit.qasm
```

## Invariants
- Behavior is reproducible for the same identity and input circuit.
- No learning loops, optimizers, or adaptive control paths exist.
- Circuit topology is preserved; only rotation angles are deterministically scaled.

## Versioning
- Canonical release: **1.0.0**
- Branding: **Spectrum GSE** only.

## Scope
Spectrum GSE is delivered for deterministic validation and analysis. It is not a training system, optimizer, or controller. Use cases include regression validation, reproducibility checks, and post-run analysis. This repository is the frozen Spectrum GSE v1.0.0 baseline.
