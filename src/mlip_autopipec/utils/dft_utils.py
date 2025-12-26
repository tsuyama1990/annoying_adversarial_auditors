import re
import subprocess
from pathlib import Path
from typing import Tuple

import numpy as np
from ase.atoms import Atoms

from mlip_autopipec.data.models import DFTResult

# Conversion factors
RY_TO_EV = 13.605693122994
RY_AU_TO_EV_A = RY_TO_EV / 0.529177210903
RY_BOHR3_TO_EV_A3 = RY_TO_EV / (0.529177210903**3)


def generate_qe_input(
    atoms: Atoms,
    pseudo_dir: str | Path,
    ecutwfc: int,
    kpts: Tuple[int, int, int],
    pseudopotentials: dict[str, str] | None = None,
) -> str:
    """
    Generates a Quantum Espresso input file content string for a given ASE Atoms object.

    Args:
        atoms: The atomic structure.
        pseudo_dir: Path to the directory containing pseudopotential files.
        ecutwfc: The plane-wave energy cutoff.
        kpts: The k-point mesh dimensions.
        pseudopotentials: A dictionary mapping atomic symbols to pseudopotential filenames.
                          If None, it assumes a simple convention (e.g., 'Si' -> 'Si.UPF').

    Returns:
        A string containing the formatted Quantum Espresso input.
    """
    if pseudopotentials is None:
        symbols = sorted(list(set(atoms.get_chemical_symbols())))
        pseudopotentials = {s: f"{s}.UPF" for s in symbols}

    atom_types = sorted(pseudopotentials.keys())
    atom_type_map = {symbol: i + 1 for i, symbol in enumerate(atom_types)}

    input_lines = []
    input_lines.append(
        """
&CONTROL
    calculation = 'scf'
    restart_mode = 'from_scratch'
    prefix = 'mlip'
    outdir = './out'
    wfcdir = './wfc'
    pseudo_dir = '{}'
    verbosity = 'high'
/
""".format(
            pseudo_dir
        )
    )

    input_lines.append(
        """
&SYSTEM
    ibrav = 0
    nat = {}
    ntyp = {}
    ecutwfc = {}
/
""".format(
            len(atoms), len(atom_types), ecutwfc
        )
    )

    input_lines.append(
        """
&ELECTRONS
    mixing_beta = 0.7
    conv_thr = 1.0e-10
/
"""
    )

    input_lines.append("ATOMIC_SPECIES")
    for symbol in atom_types:
        # A placeholder for atomic mass, QE doesn't use it for SCF.
        atomic_mass = 28.0855
        pseudo_file = pseudopotentials[symbol]
        input_lines.append(f" {symbol}  {atomic_mass:.4f}  {pseudo_file}")

    input_lines.append("\nCELL_PARAMETERS (angstrom)")
    for vector in atoms.get_cell():
        input_lines.append(f" {vector[0]:14.9f} {vector[1]:14.9f} {vector[2]:14.9f}")

    input_lines.append("\nATOMIC_POSITIONS (angstrom)")
    for atom in atoms:
        pos = atom.position
        input_lines.append(
            f" {atom.symbol}  {pos[0]:14.9f} {pos[1]:14.9f} {pos[2]:14.9f}"
        )

    input_lines.append("\nK_POINTS (automatic)")
    input_lines.append(f" {kpts[0]} {kpts[1]} {kpts[2]} 0 0 0")

    return "\n".join(input_lines)


def parse_qe_output(output: str) -> DFTResult:
    """
    Parses the standard output of a Quantum Espresso run to extract results.

    Args:
        output: The stdout string captured from the `pw.x` execution.

    Returns:
        A DFTResult object containing the parsed data. If the run failed,
        `was_successful` is False and `error_message` is populated.
    """
    if "convergence NOT achieved" in output or "ERROR" in output:
        return DFTResult(
            total_energy_ev=0,
            forces=[],
            stress=[],
            was_successful=False,
            error_message=output[-500:],  # Capture the tail of the output for context
        )

    try:
        # Extract total energy
        energy_match = re.search(r"!\s+total energy\s+=\s+(-?\d+\.\d+)\s+Ry", output)
        total_energy_ry = float(energy_match.group(1))

        # Extract forces
        forces_section = re.search(
            r"Forces acting on atoms \(cartesian axes, Ry/au\):\s*\n([\s\S]+?)(?=total stress)",
            output,
        )
        forces_lines = forces_section.group(1).strip().split("\n")
        forces = []
        for line in forces_lines:
            parts = line.split()
            forces.append([float(parts[3]), float(parts[5]), float(parts[7])])

        # Extract stress
        stress_section = re.search(r"total stress\s+\(Ry/bohr\*\*3\).*?\n([\s\S]+)", output)
        stress_lines = stress_section.group(1).strip().split("\n")
        stress = []
        for line in stress_lines:
            # Filter out empty lines that might result from splitting
            if not line.strip():
                continue
            stress.append([float(p) for p in line.split()[:3]])

        return DFTResult(
            total_energy_ev=total_energy_ry * RY_TO_EV,
            forces=(np.array(forces) * RY_AU_TO_EV_A).tolist(),
            stress=(np.array(stress) * RY_BOHR3_TO_EV_A3).tolist(),
            was_successful=True,
        )
    except (AttributeError, IndexError, ValueError) as e:
        return DFTResult(
            total_energy_ev=0,
            forces=[],
            stress=[],
            was_successful=False,
            error_message=f"Parsing failed with error: {e}\nOutput tail:\n{output[-1000:]}",
        )


def run_qe(qe_command: str, input_file: str | Path) -> Tuple[bool, str, str]:
    """
    Executes a Quantum Espresso calculation as a subprocess.

    Args:
        qe_command: The command to run QE (e.g., "pw.x", "mpirun -np 4 pw.x").
        input_file: The path to the QE input file.

    Returns:
        A tuple containing: (success_flag, stdout, stderr).
    """
    command = f"{qe_command} -in {input_file}"
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, cwd=Path.cwd()
    )
    success = result.returncode == 0
    return success, result.stdout, result.stderr
