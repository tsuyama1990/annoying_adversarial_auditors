# Cycle 01: Core Engine - Specification Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 01
**Title:** Core Engine: Automated Labelling and Delta Learning Training

## 1. Summary

This document provides the detailed technical specification for the first development cycle of the MLIP-AutoPipe project. Cycle 01 is arguably the most critical phase, as it lays the foundational bedrock upon which the entire autonomous system will be built. The primary objective of this cycle is to develop the "Core Engine," which consists of two tightly integrated components: the automated DFT **Labelling Engine (Module C)** and the physics-aware **Training Engine (Module D)**. The successful completion of this cycle will yield a system capable of performing the most fundamental task in any MLIP workflow: taking a given atomic structure, calculating its properties (energy, forces, stress) using a first-principles method, and then using that data to train a machine learning model. While this initial version will lack the sophisticated automation and active learning loops of the final product, it will serve as the essential proof-of-concept, demonstrating the viability of the core software architecture and the integration of the key external simulation packages, Quantum Espresso and a modern MLIP framework.

The scope of this cycle is deliberately focused and pragmatic. For the Labelling Engine, the goal is to create a robust and reliable Python wrapper for the Quantum Espresso `pw.x` executable. This is more than a simple command-line call; the engine must be capable of taking a standardized atomic structure representation (an `ase.Atoms` object) and automatically generating a syntactically correct and physically sensible QE input file. This involves programmatically setting crucial parameters like cell dimensions, atomic positions, pseudopotentials, and initial convergence settings. After executing the calculation, the engine must then parse the often-verbose QE output to precisely extract the required labels—total energy, atomic forces, and virial stress—and store them in a structured, accessible format within our central ASE database. Error handling is also a key consideration; the engine must be able to detect and report common DFT calculation failures, such as non-convergence of the self-consistent field (SCF) loop.

The second part of the core, the Training Engine, will focus on implementing a state-of-the-art MLIP training pipeline. A key requirement from the system architecture is the use of **Delta Learning**. This is a crucial design choice for ensuring the physical realism of our potentials. Instead of learning the total energy and forces directly, the MLIP will be trained to predict the *difference* between the true DFT values and the values calculated from a simpler, analytical baseline potential (e.g., a combination of Lennard-Jones and ZBL potentials). This approach embeds fundamental physical constraints directly into the model, ensuring, for instance, that atoms repel strongly at very short distances, a behavior that is often difficult for ML models to learn from sparse data alone. This cycle will therefore involve integrating a framework like MACE or NequIP and building the data pipeline that feeds it not just the DFT labels, but the calculated residuals required for the Delta Learning process. The final output of this cycle will be a command-line tool that, while manually operated, successfully demonstrates the end-to-end process of labelling and training for a single atomic configuration, validating our core technological choices and architectural design.

## 2. System Architecture

In the context of Cycle 01, we are implementing the foundational data processing pipeline of the overall MLIP-AutoPipe system. While the grander orchestration and feedback loops are deferred to later cycles, the architectural principles of modularity and data-centric design are paramount from the very beginning. The system at this stage can be visualized as a linear data flow, starting with a user-provided atomic structure and ending with a trained MLIP. This workflow is the nascent form of the final system's active learning loop. The central data repository, the ASE Database, is established in this cycle and serves as the connective tissue between the two core modules. Every piece of data—the input structure, the DFT parameters, the calculated labels, and the final model's metadata—is recorded in this database, fulfilling our core requirement for provenance and reproducibility from day one.

The two primary modules, the Labelling Engine (Module C) and the Training Engine (Module D), are designed as distinct, loosely-coupled services that communicate via the central database. This separation is a critical architectural choice. It means that the Labelling Engine's sole responsibility is to accurately perform and record DFT calculations, without any knowledge of what the data will be used for. Similarly, the Training Engine's responsibility is to train a model from a given dataset, without concern for how that data was generated. This decoupling allows for future flexibility; for example, the Quantum Espresso-based Labelling Engine could be swapped for a VASP- or CP2K-based one with zero required changes to the Training Engine.

**Module C: Labelling Engine (Automated DFT)**
Architecturally, Module C acts as an abstraction layer over the external Quantum Espresso code. It exposes a clean Python API—`label(atoms: ase.Atoms) -> DFTResult`—to the rest of the system. Internally, this module will be composed of three sub-components:
1.  **Input Writer:** A component responsible for translating the in-memory `ase.Atoms` object into a valid QE input file string. It will fetch appropriate pseudopotential names and cutoff energies from a configuration file or a library like SSSP.
2.  **Process Runner:** A robust sub-component for executing the external `pw.x` process. It will handle command-line execution (including MPI commands like `mpirun`), capture `stdout` and `stderr`, and manage timeouts and error conditions.
3.  **Output Parser:** A component that uses regular expressions or a dedicated parsing library to scan the QE output file for the specific lines containing the final total energy, atomic forces, and stress tensor. It will be designed to be resilient to minor variations in output formatting.

**Module D: Training Engine (Delta Learning)**
Module D is the machine learning core of the system. Its architecture is designed to be a configurable pipeline that takes labelled data from the database and produces a trained model file.
1.  **Data Loader:** This component queries the ASE database to fetch a set of labelled structures. Crucially, for each structure, it also computes the energy and forces from the chosen baseline potential (e.g., ZBL). It then calculates the *delta* (residual) that the ML model needs to learn.
2.  **Model Integrator:** This will be a wrapper around the chosen MLIP framework (e.g., MACE). It will be responsible for instantiating the model with the correct hyperparameters (number of layers, cutoff radius, etc.) defined in the system's configuration.
3.  **Training Loop:** This component implements the actual training process. It splits the data into training and validation sets, feeds batches of data to the model, calculates the loss function (on the delta values), and uses an optimizer (like Adam) to update the model's weights. It will also handle validation checks and save the model with the best performance.

The interaction between these components is mediated by the `WorkflowOrchestrator`, which, in this cycle, will be a simple script. It will first call Module C to label an initial structure, and once the result is stored in the database, it will then call Module D to train a model on that single data point. This simple, linear orchestration validates the fundamental module interaction and data flow, paving the way for the complex, cyclical orchestrations of later cycles. The use of a central, persistent database from the outset is the key architectural feature that ensures traceability and enables this modular, decoupled design to function effectively.

## 3. Design Architecture

The software design for Cycle 01 focuses on creating a clean, maintainable, and testable Python codebase. We will use object-oriented principles to encapsulate the logic for each module and Pydantic for strict data modelling, ensuring that data passed between components is always valid.

**File and Class Structure:**

```
mlip_autopipec/
├── main_cycle01.py        # CLI entry point for this cycle's functionality
├── orchestrator_cycle01.py # Simple orchestrator for the linear workflow
├── modules/
│   ├── c_labelling_engine.py
│   └── d_training_engine.py
├── data/
│   ├── models.py
│   └── database.py
├── utils/
│   ├── dft_utils.py
│   └── baseline_potentials.py
└── configs/
    └── cycle01_config.yaml # Configuration for QE path, MLIP params, etc.
```

**Class and API Definitions:**

1.  **`data.models.py`**: This file will define the core data structures using Pydantic, ensuring type safety and clear contracts between components.
    ```python
    from pydantic import BaseModel
    from typing import List

    class DFTResult(BaseModel):
        total_energy_ev: float
        forces: List[List[float]]
        stress: List[List[float]]
        was_successful: bool
        error_message: str | None = None

    class TrainingConfig(BaseModel):
        model_type: str
        learning_rate: float
        num_epochs: int
        r_cut: float
        delta_learn: bool
        baseline_potential: str
    ```

2.  **`modules.c_labelling_engine.LabellingEngine`**: The main class for handling DFT calculations.
    ```python
    from ase.atoms import Atoms
    from .data.models import DFTResult
    from .data.database import AseDB

    class LabellingEngine:
        def __init__(self, qe_command: str, db: AseDB):
            self._qe_command = qe_command
            self._db = db

        def execute(self, atoms: Atoms) -> int:
            """Generates input, runs QE, parses output, and saves to DB.
            Returns the database ID of the new entry."""
            # ... internal logic using dft_utils ...
            result: DFTResult = self._parse_output(...)
            db_id = self._db.write(atoms, result)
            return db_id
    ```

3.  **`modules.d_training_engine.TrainingEngine`**: The class responsible for the MLIP training workflow.
    ```python
    from .data.database import AseDB
    from .data.models import TrainingConfig

    class TrainingEngine:
        def __init__(self, config: TrainingConfig, db: AseDB):
            self._config = config
            self._db = db

        def execute(self, ids: list[int]) -> str:
            """Loads data for given IDs from DB, prepares it for Delta Learning,
            trains the model, and returns the path to the saved model file."""
            data = self._load_and_prepare_data(ids)
            # ... logic to integrate with MACE/NequIP ...
            # ... training loop ...
            model_path = self._save_model(...)
            return model_path

        def _load_and_prepare_data(self, ids: list[int]):
            """Queries DB, computes baseline values, and calculates residuals."""
            # ... internal logic using baseline_potentials.py ...
    ```

4.  **`orchestrator_cycle01.py`**: A simple script to wire the components together for the initial demonstration.
    ```python
    # Simplified example
    from ase.io import read
    from .modules.c_labelling_engine import LabellingEngine
    from .modules.d_training_engine import TrainingEngine
    # ... other imports ...

    def run_cycle01_workflow():
        config = load_config('configs/cycle01_config.yaml')
        db = AseDB('mlip.db')
        labeller = LabellingEngine(config.qe_command, db)
        trainer = TrainingEngine(config.training, db)

        initial_structure = read('initial.xyz')
        db_id = labeller.execute(initial_structure)
        trained_model_path = trainer.execute(ids=[db_id])
        print(f"Workflow complete. Model saved to: {trained_model_path}")
    ```
This design establishes a clear separation of concerns. The `LabellingEngine` and `TrainingEngine` are self-contained units that can be tested independently. The use of Pydantic models for configuration and results enforces a rigid, error-resistant structure. The orchestrator is kept deliberately simple in this cycle, serving only to prove that the two core modules can be connected and can function sequentially.

## 4. Implementation Approach

The implementation of Cycle 01 will be broken down into a series of logical, sequential steps, ensuring that each part is built and tested before the next is added. The approach prioritizes establishing the external dependencies and interfaces first, followed by the internal logic.

**Step 1: Project Scaffolding and Dependency Management**
The very first step is to create the directory structure outlined in the Design Architecture. We will initialize a `pyproject.toml` file to manage the project's metadata and dependencies. The initial set of dependencies will be installed using `uv`:
*   `ase`: For handling atomic structures and the database.
*   `pydantic`: For data modelling.
*   `pyyaml`: For parsing the configuration file.
*   `mace-torch` or `nequip`: The chosen MLIP framework.
*   `pytest` and `pytest-mock`: For the testing framework.
This step ensures a reproducible development environment is established from the outset.

**Step 2: Implementing the Labelling Engine (Module C)**
This module will be built in three distinct parts:
1.  **Input Generation:** We will start by writing the `dft_utils.generate_qe_input` function. This function will take an `ase.Atoms` object and a set of parameters (cutoffs, k-points) and produce a string containing the QE input file content. This will be unit-tested extensively with various structures (e.g., cubic, triclinic cells) to ensure correctness. We will use SSSP pseudopotential and cutoff recommendations, which will be stored in a configuration file.
2.  **Process Execution:** Next, we will implement the logic to run the `pw.x` executable using Python's `subprocess` module. This will be wrapped in a helper function that handles capturing standard output and standard error, and detects non-zero exit codes. Care will be taken to construct the command line properly, allowing for `mpirun` prefixes for parallel execution as specified in the configuration.
3.  **Output Parsing:** The most fragile part of this module is parsing the QE output. We will create a `dft_utils.parse_qe_output` function that takes the captured stdout string as input. It will use carefully crafted regular expressions to find and extract the final energy (`! total energy`), the forces (`Forces acting on atoms`), and the stress tensor (`total stress`). This function will be tested against a collection of pre-saved, real QE output files, including those from successful runs and failed (non-converged) runs, to ensure its robustness.
4.  **Class Integration:** Finally, these functions will be integrated into the `LabellingEngine` class, which will orchestrate the call sequence: generate input -> run process -> parse output -> store in the `AseDB`.

**Step 3: Implementing the Training Engine (Module D)**
This module's implementation will also be staged.
1.  **Baseline Potential Calculation:** We will first implement the `utils.baseline_potentials` module. This will contain functions that take an `ase.Atoms` object and return the energy and forces calculated from a simple potential like Lennard-Jones or ZBL. This will be a pure Python/NumPy implementation, heavily unit-tested for correctness.
2.  **Data Loading and Preparation:** The `_load_and_prepare_data` method of the `TrainingEngine` will be implemented. This method will fetch data from the `AseDB`, call the baseline potential functions, and compute the `delta` values (e.g., `force_delta = dft_force - baseline_force`). The output will be a list of data objects ready for the MLIP framework.
3.  **MLIP Framework Integration:** This is the core integration task. We will write a wrapper around the chosen framework (e.g., MACE). This wrapper will handle the boilerplate code for:
    *   Initializing the MACE model architecture.
    *   Converting our prepared data into the `torch_geometric` or `ase.Atoms` list format expected by MACE.
    *   Setting up the PyTorch optimizer and loss function.
    *   Running the training loop for the specified number of epochs.
    *   Saving the final trained model to a file.

**Step 4: Wiring and Final Testing**
Once both modules are implemented and unit-tested, we will write the simple `orchestrator_cycle01.py` script. This script will instantiate the engines and run them in sequence on a simple test case, like a single silicon atom in a box or a water molecule. An end-to-end integration test will be created from this script, which will run a real, albeit very fast, QE calculation and a short MLIP training run (e.g., for 5 epochs). The successful execution of this test will signify the completion of Cycle 01.

## 5. Test Strategy

The testing strategy for Cycle 01 is foundational, focusing on ensuring the correctness of individual components (unit tests) and verifying their ability to work together (integration tests). The goal is to build a high level of confidence in the core data processing pipeline before adding further complexity. We will use the `pytest` framework for all tests.

**Unit Testing:**

The focus of unit testing is to test each class and function in isolation, using `pytest-mock` to replace external dependencies like file I/O or actual subprocess calls.

*   **`LabellingEngine` (Module C):**
    *   **Input Writer Tests:** A suite of tests will verify the `generate_qe_input` function. We will provide it with different `ase.Atoms` objects (varying cell sizes, symmetries, number of atoms) and assert that the generated input string is syntactically correct and contains the right values. We will also test edge cases like empty structures or unsupported atom types.
    *   **Output Parser Tests:** We will create a directory of static test data containing saved QE output files. This will include outputs from a standard successful run, a run that failed to converge, a run with magnetic moments, and a run with stress calculations. The `parse_qe_output` function will be tested against each of these files to ensure it extracts the correct data, or correctly identifies the failure mode.
    *   **Process Runner Mocking:** When testing the `LabellingEngine.execute` method, we will mock the `subprocess.run` call. This allows us to test the engine's logic (e.g., that it calls the correct command and handles the mocked return code) without actually needing Quantum Espresso to be installed or run, making the unit tests fast and portable.

*   **`TrainingEngine` (Module D):**
    *   **Baseline Potential Tests:** The `baseline_potentials` functions will be tested against known analytical values. For a two-atom system at a specific distance, we will assert that the calculated LJ/ZBL potential energy and force match hand-calculated or reference values to a high precision.
    *   **Data Preparation Tests:** We will test the `_load_and_prepare_data` method by providing it with a mock database interface. We will verify that it correctly retrieves the DFT data, calls the baseline potential calculator, and computes the delta values accurately.
    *   **Trainer Mocking:** The integration with the MLIP framework will be tested by mocking the framework itself. We will test that our `TrainingEngine` correctly instantiates the model (e.g., `mace.MACE(...)` is called with the right parameters) and that it calls the training method with the correctly prepared data. This verifies our wrapper logic without the need for a time-consuming GPU-based training run in the unit test suite.

**Integration Testing:**

Integration tests are designed to ensure that the separately developed modules function correctly when connected. These tests are slower and have more dependencies (requiring a real QE executable and a working MLIP installation).

*   **Test 1: Successful Labelling Workflow:**
    *   **Objective:** Verify the full process from `ase.Atoms` object to a successful entry in the ASE database.
    *   **Setup:** Requires a lightweight test case (e.g., a single H atom in a box) and a configured path to the `pw.x` executable. The test will start with an empty database.
    *   **Execution:** The test will call `LabellingEngine.execute` with the H atom structure.
    *   **Verification:** The test will assert that the `execute` method completes without errors. It will then query the database to ensure that a new entry was created and that the stored energy and forces are of the correct type and are physically reasonable (e.g., forces are close to zero for a symmetric configuration).

*   **Test 2: Full End-to-End Run (Labelling + Training):**
    *   **Objective:** Verify the entire Cycle 01 workflow from a structure file to a saved MLIP model file.
    *   **Setup:** Builds on Test 1.
    *   **Execution:** The test will first call the `LabellingEngine` to create a database entry. It will then instantiate the `TrainingEngine` and call its `execute` method, pointing it to the newly created database ID. The training will be configured for a minimal number of epochs (e.g., 2-3) to ensure the test runs quickly.
    *   **Verification:** The test will assert that the `TrainingEngine.execute` method returns a valid file path and that a model file actually exists at that path. This confirms that the data flowed correctly from the labeller to the database, and from the database to the trainer, and that the training process completed without crashing. This is the ultimate "smoke test" for Cycle 01.
