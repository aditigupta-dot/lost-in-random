from qiskit import QuantumCircuit
from qiskit_aer import Aer
from qiskit import transpile

def check_answer(ans):
    qc = QuantumCircuit(1,1)

    if ans == "superposition":
        qc.h(0)

    qc.measure(0,0)

    simulator = Aer.get_backend('aer_simulator')
    compiled = transpile(qc, simulator)

    result = simulator.run(compiled, shots=1).result()
    counts = result.get_counts()

    return "1" in counts