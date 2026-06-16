"""Quantum layer implementation using PennyLane."""

import torch
import torch.nn as nn
import pennylane as qml


class QuantumLayer(nn.Module):
    """Quantum layer implementation using PennyLane."""

    def __init__(self, n_qubits, n_layers, device_name="lightning.qubit"):
        super().__init__()
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.device_name = device_name

        dev = qml.device(device_name, wires=n_qubits)

        @qml.qnode(dev, interface="torch")
        def circuit(inputs, weights):
            for i in range(n_qubits):
                qml.RY(inputs[i], wires=i)

            for j in range(n_layers):
                for i in range(n_qubits):
                    qml.CNOT(wires=[i, (i + 1) % n_qubits])
                for i in range(n_qubits):
                    qml.RY(weights[j, i], wires=i)

            return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

        weight_shapes = {"weights": (n_layers, n_qubits)}
        self.qlayer = qml.qnn.TorchLayer(circuit, weight_shapes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the quantum layer."""
        if x.dim() == 1:
            x = x.unsqueeze(0)

        outputs = [self.qlayer(sample) for sample in x]
        return torch.stack(outputs)

    def get_circuit_info(self) -> dict:
        """Return metadata for the quantum circuit."""
        return {
            "n_qubits": self.n_qubits,
            "n_layers": self.n_layers,
            "device": self.device_name,
            "total_parameters": self.n_layers * self.n_qubits,
        }
