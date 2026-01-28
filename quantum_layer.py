import torch
import torch.nn as nn
import pennylane as qml

class QuantumLayer(nn.Module):
    """
    Quantum layer implementation using PennyLane.
    
    This layer implements a variational quantum circuit (VQC) that can be
    integrated into classical neural networks for hybrid quantum-classical computing.
    
    Args:
        n_qubits (int): Number of qubits in the quantum circuit.
        n_layers (int): Number of layers in the quantum circuit.
        device_name (str): Quantum device to use (default: "lightning.qubit" for Metal).
    """

    def init(self, nqubits, nlayers, device_name="lightning.qubit"):
        super().init()
        self.nqubits = nqubits
        self.nlayers = nlayers
        self.devicename = devicename

        # Use Metal-compatible device if on macOS with MPS/Metal
        # "lightning.qubit" is optimized for CPU/GPU (Metal via Torch MPS)
        dev = qml.device(devicename, wires=nqubits)

        # Define quantum circuit
        @qml.qnode(dev, interface="torch")
        def circuit(inputs, weights):
            # Encode classical inputs into quantum states
            for i in range(n_qubits):
                qml.RY(inputs[i], wires=i)

            # Apply variational layers
            for j in range(n_layers):
                # Entangle qubits using CNOT gates in ring pattern
                for i in range(n_qubits):
                    qml.CNOT(wires=[i, (i + 1) % n_qubits])

                # Apply rotation gates
                for i in range(n_qubits):
                    qml.RY(weights[j, i], wires=i)

            # Measure all qubits in Z basis
            return [qml.expval(qml.PauliZ(i)) for i in range(n_qubits)]

        # Define weight shapes for the quantum circuit
        weightshapes = {"weights": (nlayers, n_qubits)}

        # Create TorchLayer for integration with PyTorch
        self.qlayer = qml.qnn.TorchLayer(circuit, weightshapes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the quantum layer.

        Args:
            x (torch.Tensor): Input tensor of shape (batchsize, nqubits) or (n_qubits,)

        Returns:
            torch.Tensor: Output tensor of shape (batchsize, nqubits)
        """
        # Ensure x is 2D (batchsize, nqubits)
        if x.dim() == 1:
            x = x.unsqueeze(0)

        # Compute output through the quantum layer
        outputs = [self.q_layer(sample) for sample in x]
        return torch.stack(outputs)

    def getcircuitinfo(self) -> dict:
        """
        Get information about the quantum circuit.

        Returns:
            dict: Circuit information including number of qubits and layers.
        """
        return {
            "nqubits": self.nqubits,
            "nlayers": self.nlayers,
            "device": self.device_name,
            "totalparameters": self.nlayers * self.n_qubits,
        }