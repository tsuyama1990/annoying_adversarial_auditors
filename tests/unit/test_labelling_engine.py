import pytest
from unittest.mock import MagicMock, patch

from ase.build import bulk
import numpy as np

from mlip_autopipec.utils import dft_utils
from mlip_autopipec.modules.c_labelling_engine import LabellingEngine
from mlip_autopipec.data.models import DFTResult

# Sample QE output for a successful run (simplified)
SUCCESSFUL_QE_OUTPUT = """
!    total energy              =     -150.00000000 Ry
Forces acting on atoms (cartesian axes, Ry/au):
     atom    1   fx=   0.00000000   fy=   0.00000000   fz=   0.00000000
     atom    2   fx=   0.00000000   fy=   0.00000000   fz=   0.00000000
total stress  (Ry/bohr**3)                       (kbar)
  1.000000   0.000000   0.000000        147.04      0.00      0.00
  0.000000   1.000000   0.000000          0.00    147.04      0.00
  0.000000   0.000000   1.000000          0.00      0.00    147.04
"""

# Sample QE output for a failed run
FAILED_QE_OUTPUT = """
     Maximum number of scf cycles reached.
     convergence NOT achieved
"""

@pytest.fixture
def silicon_atoms():
    """Provides a standard 2-atom silicon cell."""
    return bulk('Si', 'diamond', a=5.43)

def test_generate_qe_input(silicon_atoms):
    """Tests that the generated QE input string is correct."""
    input_str = dft_utils.generate_qe_input(
        atoms=silicon_atoms,
        pseudo_dir='/path/to/pseudos',
        ecutwfc=60,
        kpts=(4, 4, 4)
    )
    assert '&CONTROL' in input_str
    assert "calculation = 'scf'" in input_str
    assert '&SYSTEM' in input_str
    assert 'ibrav = 0' in input_str
    assert 'nat = 2' in input_str
    assert 'ntyp = 1' in input_str
    assert 'ecutwfc = 60' in input_str
    assert 'ATOMIC_SPECIES' in input_str
    assert 'Si  28.0855  Si.UPF' in input_str
    assert 'CELL_PARAMETERS (angstrom)' in input_str
    assert 'ATOMIC_POSITIONS (angstrom)' in input_str
    assert 'K_POINTS (automatic)' in input_str
    assert '4 4 4 0 0 0' in input_str

def test_parse_successful_qe_output():
    """Tests parsing of a successful QE run output."""
    ry_to_ev = 13.605693122994
    ry_au_to_ev_a = 13.605693122994 / 0.529177210903
    ry_bohr3_to_ev_a3 = 13.605693122994 / (0.529177210903 ** 3)

    result = dft_utils.parse_qe_output(SUCCESSFUL_QE_OUTPUT)

    assert result.was_successful
    assert result.error_message is None
    assert result.total_energy_ev == pytest.approx(-150.0 * ry_to_ev)
    assert np.allclose(result.forces, np.zeros((2, 3)))
    expected_stress = np.diag([1.0, 1.0, 1.0]) * ry_bohr3_to_ev_a3
    assert np.allclose(result.stress, expected_stress)


def test_parse_failed_qe_output():
    """Tests parsing of a failed (non-converged) QE run output."""
    result = dft_utils.parse_qe_output(FAILED_QE_OUTPUT)
    assert not result.was_successful
    assert "convergence NOT achieved" in result.error_message

@patch('subprocess.run')
@patch('mlip_autopipec.utils.dft_utils.generate_qe_input')
@patch('mlip_autopipec.utils.dft_utils.parse_qe_output')
def test_labelling_engine_execute_success(
    mock_parse, mock_generate, mock_run, silicon_atoms
):
    """Tests the LabellingEngine's main execute method on a successful run."""
    mock_db = MagicMock()
    mock_db.write.return_value = 1

    # Mock the return values from helpers
    mock_generate.return_value = "dummy_input_content"
    mock_run.return_value = MagicMock(
        returncode=0, stdout=SUCCESSFUL_QE_OUTPUT, stderr=""
    )
    mock_parse.return_value = DFTResult(
        total_energy_ev=-2040.0,
        forces=[[0,0,0], [0,0,0]],
        stress=[[1,0,0],[0,1,0],[0,0,1]],
        was_successful=True
    )

    engine = LabellingEngine(qe_command="mpirun -np 4 pw.x", db=mock_db)
    db_id = engine.execute(silicon_atoms, pseudo_dir='.')

    mock_generate.assert_called_once()
    mock_run.assert_called_once()
    # Check that the executable and input file are in the command, but don't
    # assert on the full absolute path to make the test more robust.
    command_str = mock_run.call_args[0][0]
    assert 'pw.x' in command_str
    assert 'QE_input.in' in command_str
    mock_parse.assert_called_once_with(SUCCESSFUL_QE_OUTPUT)
    mock_db.write.assert_called_once()
    assert db_id == 1
