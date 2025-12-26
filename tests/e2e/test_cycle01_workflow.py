import os
import subprocess
from pathlib import Path

import pytest
from ase.build import bulk
from ase.io import write

from mlip_autopipec.main_cycle01 import main

# A minimal config file for testing purposes
TEST_CONFIG_YAML = """
database:
  path: "test.db"

labelling:
  qe_command: "mock_pw.x"
  pseudo_dir: "pseudos/"
  ecutwfc: 60
  kpts: [4, 4, 4]

training:
  model_type: "mace"
  learning_rate: 0.01
  num_epochs: 2
  r_cut: 5.0
  delta_learn: false
  baseline_potential: "lj"
"""

# A mock pw.x script that produces predictable output
MOCK_PWX_SCRIPT = f"""#!/bin/bash
echo '!    total energy              =     -150.00000000 Ry'
echo 'Forces acting on atoms (cartesian axes, Ry/au):'
echo '     atom    1   fx=   0.00000000   fy=   0.00000000   fz=   0.00000000'
echo 'total stress  (Ry/bohr**3)                       (kbar)'
echo '  1.0   0.0   0.0'
echo '  0.0   1.0   0.0'
echo '  0.0   0.0   1.0'
exit 0
"""

@pytest.fixture(scope="module")
def setup_test_environment(tmpdir_factory):
    """
    Creates a temporary directory with all necessary files for an E2E run.
    This includes a mock QE executable, a structure file, and a config file.
    """
    tmpdir = tmpdir_factory.mktemp("e2e_test")

    # Create config file
    config_path = tmpdir.join("test_config.yaml")
    config_path.write(TEST_CONFIG_YAML)

    # Create structure file with two identical structures to satisfy MACE's
    # train/validation split requirement.
    atoms = bulk('Si', 'diamond', a=5.43)
    structure_path = tmpdir.join("si_bulk.xyz")
    write(str(structure_path), [atoms, atoms])

    # Create mock executable
    mock_pwx_path = tmpdir.join("mock_pw.x")
    mock_pwx_path.write(MOCK_PWX_SCRIPT)
    os.chmod(str(mock_pwx_path), 0o755)

    # Update the config to point to our mock executable
    # and add it to the system PATH
    original_path = os.environ['PATH']
    os.environ['PATH'] = f"{tmpdir}:{original_path}"

    yield str(config_path), str(structure_path)

    # Teardown
    os.environ['PATH'] = original_path

def test_cycle01_e2e_workflow(setup_test_environment, capsys):
    """
    Tests the full end-to-end workflow for Cycle 01 by invoking the CLI.
    """
    config_path, structure_path = setup_test_environment

    # We use subprocess to call our CLI to simulate a user running it.
    # This is more robust than calling the main function directly.
    command = [
        "python", "-m", "mlip_autopipec.main_cycle01",
        "--config", config_path,
        "--structure", structure_path
    ]

    # We change the working directory to the directory of the config file to
    # ensure that the database and model files are created there.
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(config_path),
        env={**os.environ, "PYTHONPATH": f"{os.getcwd()}/src"}
    )

    # Check that the process ran successfully
    assert process.returncode == 0, f"CLI process failed with stderr: {process.stderr}"

    # Check that the expected output was printed
    stdout = process.stdout
    assert "Labelling complete." in stdout
    assert "Workflow complete." in stdout
    assert "trained_model.pt" in stdout

    # Check that the output files were created
    config_dir = Path(os.path.dirname(config_path))
    assert (config_dir / "test.db").exists()
    assert (config_dir / "models" / "trained_model.pt").exists()
