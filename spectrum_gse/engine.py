"""
Spectrum GSE deterministic stabilizer and analysis helpers.

Canonical v1.0.0 — behaviorally frozen, deterministic, and topology-safe.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    from qiskit import QuantumCircuit, QiskitError, transpile
    from qiskit_aer import AerSimulator
    from qiskit.qasm2 import loads as qasm2_loads

    QISKIT_AVAILABLE = True
except Exception:  # pragma: no cover
    QuantumCircuit = Any  # type: ignore
    AerSimulator = Any  # type: ignore
    transpile = None  # type: ignore
    qasm2_loads = None  # type: ignore
    QISKIT_AVAILABLE = False


SPECTRUM_GSE = "1.0.0"
MAX_PAYLOAD_BYTES = 1_000_000


def identity_vector(identity: str, dim: int = 100_200) -> np.ndarray:
    """
    Encode an identity string into a deterministic, normalized real vector.

    Default dimension keeps parity with earlier research baselines that used
    ~100k-length identity embeddings for stability sweeps.
    """
    if dim <= 0:
        raise ValueError("dim must be positive")

    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    base = np.frombuffer(digest, dtype=np.uint8).astype(np.float64) / 255.0

    reps = math.ceil(dim / base.size)
    tiled = np.tile(base, reps)[:dim]
    tiled -= tiled.mean()
    norm = np.linalg.norm(tiled)
    return tiled / norm if norm else np.zeros(dim, dtype=np.float64)


def _stability_projection(v: np.ndarray) -> np.ndarray:
    """
    Lightweight, deterministic mixing used to produce a bounded stabilizer vector.
    """
    v = v.astype(np.float64)
    mixed = np.tanh(0.12 * v)
    fft = np.fft.rfft(mixed)
    phases = np.exp(1j * np.linspace(0.0, 2.0 * math.pi, fft.size))
    blended = np.fft.irfft(fft * phases, n=v.size).real
    blended -= blended.mean()
    norm = np.linalg.norm(blended)
    return blended / norm if norm else blended


@dataclass(frozen=True)
class SpectrumGSEConfig:
    latent_dim: int = 100_200
    epsilon_angle: float = 0.01


class SpectrumGSE:
    """
    Deterministic Spectrum GSE stabilizer.

    - No learning or optimization.
    - No topology mutation; only bounded angle scaling on rotation gates.
    - Stable across runs for the same identity and input.
    """

    def __init__(self, identity: str, config: Optional[SpectrumGSEConfig] = None):
        self.identity = identity
        self.config = config or SpectrumGSEConfig()
        self._id_vec = identity_vector(identity, self.config.latent_dim)

    def _circuit_to_features(self, qc: "QuantumCircuit") -> np.ndarray:
        angles = []
        for inst_tuple in qc.data:
            inst = getattr(inst_tuple, "operation", inst_tuple[0])
            params = getattr(inst, "params", [])
            if params:
                try:
                    angles.append(float(params[0]))
                except (TypeError, ValueError):
                    # Non-numeric parameters are ignored to keep stabilization deterministic.
                    continue
        if not angles:
            counts: Dict[str, int] = {}
            for inst_tuple in qc.data:
                inst = getattr(inst_tuple, "operation", inst_tuple[0])
                name = inst.name
                counts[name] = counts.get(name, 0) + 1
            angles = list(counts.values()) or [0.0]

        v = np.array(angles, dtype=np.float64)
        v -= v.mean()
        std = v.std()
        if std > 0:
            v /= std

        if v.size < self.config.latent_dim:
            reps = math.ceil(self.config.latent_dim / v.size)
            v = np.tile(v, reps)[: self.config.latent_dim]
        elif v.size > self.config.latent_dim:
            v = v[: self.config.latent_dim]
        return v

    def _apply_vector(self, qc: "QuantumCircuit", stabilizer: np.ndarray) -> "QuantumCircuit":
        if not QISKIT_AVAILABLE:
            return qc

        eps = self.config.epsilon_angle
        out = qc.copy()
        real = stabilizer.real
        n = real.size
        idx = 0
        new_data = []

        for inst_tuple in out.data:
            inst = getattr(inst_tuple, "operation", inst_tuple[0])
            qargs = getattr(inst_tuple, "qubits", inst_tuple[1] if len(inst_tuple) > 1 else [])
            cargs = getattr(inst_tuple, "clbits", inst_tuple[2] if len(inst_tuple) > 2 else [])
            name = inst.name.lower()
            params = list(getattr(inst, "params", []))

            if name in {"rx", "ry", "rz"} and params:
                scale = 1.0 + eps * real[idx % n]
                try:
                    params[0] = float(params[0]) * scale
                except (TypeError, ValueError):
                    pass
                idx += 1

            try:
                new_inst = inst.__class__(*params)
            except (TypeError, ValueError):
                new_inst = inst

            new_data.append((new_inst, list(qargs), list(cargs)))

        out.data = new_data
        return out

    def stabilize(self, circuit_or_qasm: Any) -> Any:
        """
        Deterministically stabilize a circuit or QASM2 string.
        """
        if not QISKIT_AVAILABLE:
            return circuit_or_qasm

        if isinstance(circuit_or_qasm, str):
            try:
                qc = qasm2_loads(circuit_or_qasm) if qasm2_loads else None
            except (ValueError, QiskitError):
                return circuit_or_qasm
            if qc is None:
                return circuit_or_qasm
        elif isinstance(circuit_or_qasm, QuantumCircuit):
            qc = circuit_or_qasm
        else:
            return circuit_or_qasm

        features = self._circuit_to_features(qc)
        stabilizer_in = 0.7 * features + 0.3 * self._id_vec
        stabilizer_vec = _stability_projection(stabilizer_in)

        return self._apply_vector(qc, stabilizer_vec)

    def simulate(self, qc: "QuantumCircuit", shots: int = 1024) -> Dict[str, int]:
        if not QISKIT_AVAILABLE:
            raise RuntimeError("Qiskit + qiskit-aer required for simulation.")

        sim = AerSimulator()
        circ = qc.copy()
        circ.measure_all()
        compiled = transpile(circ, sim)
        result = sim.run(compiled, shots=shots).result()
        return result.get_counts(0)


class ValidatorEngine(SpectrumGSE):
    """
    Validation-oriented wrapper. Mirrors SpectrumGSE while providing a named validate entry point.
    """

    def validate(self, circuit_or_qasm: Any) -> Any:
        return self.stabilize(circuit_or_qasm)


class ExplorerEngine(SpectrumGSE):
    """
    Analysis wrapper that returns both the stabilized circuit and the intermediate vector.
    """

    def analyze(self, circuit_or_qasm: Any) -> Tuple[Any, Optional[np.ndarray]]:
        if not QISKIT_AVAILABLE:
            return circuit_or_qasm, None

        if isinstance(circuit_or_qasm, str):
            try:
                qc = qasm2_loads(circuit_or_qasm) if qasm2_loads else None
            except (ValueError, QiskitError):
                return circuit_or_qasm, None
            if qc is None:
                return circuit_or_qasm, None
        elif isinstance(circuit_or_qasm, QuantumCircuit):
            qc = circuit_or_qasm
        else:
            return circuit_or_qasm, None

        features = self._circuit_to_features(qc)
        stabilizer_in = 0.7 * features + 0.3 * self._id_vec
        stabilizer_vec = _stability_projection(stabilizer_in)
        return self._apply_vector(qc, stabilizer_vec), stabilizer_vec


def cli_main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Spectrum GSE deterministic stabilizer")
    parser.add_argument("--identity", required=True, help="Identity string used for stabilization")
    parser.add_argument(
        "--qasm",
        type=argparse.FileType("r"),
        help="Optional QASM2 file to stabilize. Falls back to stdin if omitted.",
    )
    args = parser.parse_args()

    payload = args.qasm.read() if args.qasm else sys.stdin.read()
    if payload and len(payload) > MAX_PAYLOAD_BYTES:
        parser.error("Input payload too large; limit is 1MB for deterministic validation.")

    engine = SpectrumGSE(args.identity)
    stabilized = engine.stabilize(payload) if payload else payload

    if QISKIT_AVAILABLE and isinstance(stabilized, QuantumCircuit):
        print(stabilized.qasm())
    else:
        print(stabilized)


if __name__ == "__main__":  # pragma: no cover
    cli_main()
