# Cycle 03: Efficient Exploration - Specification Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 03
**Title:** Efficient Phase Space Exploration and Intelligent Sampling

## 1. Summary

This document provides the detailed technical specification for the third development cycle of the MLIP-AutoPipe project. With the core engine (Cycle 01) and automation framework (Cycle 02) now in place, Cycle 03 introduces a significant leap in the system's intelligence and data efficiency. The central objective of this cycle is to implement the **Explorer & Sampler (Module B)**, a sophisticated component designed to replace the relatively simple static structure generation of Module A with a dynamic, wide-ranging, and low-cost exploration of the material's potential energy surface. This cycle is critical for elevating the quality and generalizability of the final MLIP by ensuring the training data is not just diverse, but is sourced from the most physically relevant and informative regions of the conformational space.

The core strategy of Module B is to leverage pre-trained, large-scale universal potentials, often referred to as "foundation models" (e.g., MACE-MP, M3GNet). These models, while not as accurate as system-specific DFT calculations, provide a remarkably good approximation of atomic interactions at a fraction of the computational cost—often thousands of times faster. By using one of these models as a surrogate calculator, Module B can run extensive, high-temperature molecular dynamics (MD) simulations, generating trajectories that span millions of atomic configurations. This allows the system to cheaply explore a vast landscape of structures, including near-equilibrium vibrations, defect formations, amorphous states, and even transition pathways, which would be prohibitively expensive to simulate directly with DFT.

However, generating a massive trajectory is only half the battle. The second key innovation in this cycle is the implementation of an intelligent sampling algorithm, **DIRECT (Dimensionality Reduction, Clustering, and Stratified Sampling)**. Simply selecting random frames from the MD trajectory would be inefficient, as most frames are highly correlated and represent mundane thermal vibrations. Instead, the DIRECT algorithm processes the entire trajectory, calculates a unique fingerprint (descriptor) for the local atomic environment of each atom, and then uses dimensionality reduction and clustering techniques to identify all the unique conformational "themes" present in the simulation. By then sampling structures from each of these distinct clusters, the system ensures that the final dataset passed to the expensive DFT Labelling Engine is small, diverse, maximally informative, and free of statistical bias. As this module processes enormous amounts of data, performance is a key concern; therefore, critical parts of the descriptor calculation and analysis will be heavily optimized using tools like Numba to ensure the entire exploration phase remains fast and efficient.

## 2. System Architecture

The introduction of Module B, the Explorer & Sampler, significantly enhances the sophistication of the data generation phase of the pipeline. It is architecturally situated between the initial seeding (Module A) and the expensive labelling (Module C). The workflow is no longer a simple generation-then-labelling process; it now includes a crucial, intermediate exploration and filtration step.

The updated data flow proceeds as follows:
1.  **Initial Seeding (Module A):** The process starts as before, with Module A generating a small set of diverse, static initial structures (e.g., SQS cells).
2.  **Exploration (Module B - Part 1):** These initial structures are now used as starting points for high-temperature molecular dynamics simulations run by Module B. Module B employs a fast, pre-trained universal potential (Foundation Model) as its force calculator. This step generates one or more long trajectory files, containing potentially millions of atomic configurations. This is a computationally intensive step, and the architecture must support offloading these calculations to a GPU if available.
3.  **Sampling (Module B - Part 2):** The generated trajectory data is then processed by the DIRECT sampling algorithm within Module B. This involves descriptor calculation, dimensionality reduction, and clustering. The output is a new, much smaller, but highly diverse list of `ase.Atoms` objects, representing the most informative structures found during the exploration.
4.  **Labelling (Module C):** This curated list of structures from Module B is then passed to the DFT Labelling Engine (Module C) for the expensive, high-fidelity calculations.

This new architecture makes the data generation process much more powerful. Instead of relying on a handful of educated guesses from Module A, the system now performs a comprehensive search for interesting physics, ensuring that the valuable DFT resources are spent only on configurations that are genuinely novel and informative.

**Architectural Placement:**

```mermaid
graph TD
    A[Start: Full Config] --> B{Workflow Orchestrator};
    B --1. Invoke--> C[Module A: Structure Generator];
    C --2. Generate Initial Seeds--> D[List of ase.Atoms (Small)];
    B --3. Pass Seeds to--> E[Module B: Explorer & Sampler];

    subgraph "Module B: Internal Flow"
        E --a. Run Surrogate MD--> F[MD Trajectory (Large)];
        F --b. Process Trajectory--> G[DIRECT Sampler];
        G --c. Select Structures--> H[List of ase.Atoms (Curated)];
    end

    B --4. Receive Curated List from E--> I[Module C: Labelling Engine];
    I --5. Label Structures--> J[Data Store: ASE DB];
    B --6. Invoke--> K[Module D: Training Engine];

    subgraph "New in Cycle 03"
        E; F; G; H;
    end

    style E fill:#9cf,stroke:#333,stroke-width:2px
```

The `WorkflowOrchestrator` must be updated to manage this new multi-step data generation process. The configuration file (`exec_config_dump.yaml`) will be expanded to include parameters for Module B, such as the choice of surrogate model, the MD simulation temperature and duration, and the target number of structures to sample. Performance is a key architectural concern, so the integration of the surrogate model must be implemented in a way that allows for transparent GPU acceleration via frameworks like PyTorch.

## 3. Design Architecture

The design for Cycle 03 centers on the new `ExplorerSampler` class and the high-performance utility functions it requires.

**File and Class Structure:**

```
mlip_autopipec/
├── orchestrator_cycle03.py    # Updated orchestrator
├── modules/
│   ├── a_structure_generator.py # (from Cycle 02)
│   ├── b_explorer_sampler.py    # New module for this cycle
│   ├── c_labelling_engine.py      # (from Cycle 01)
│   └── d_training_engine.py      # (from Cycle 01)
├── utils/
│   └── descriptor_utils.py      # Numba-optimized descriptor calculations
└── models/
    └── surrogate_mace.pt        # Example pre-trained model file
```

**Class and API Definitions:**

1.  **`modules/b_explorer_sampler.py`**: This file will house the main `ExplorerSampler` class.
    ```python
    from typing import List
    from ase import Atoms
    from ase.md.langevin import Langevin
    from ase.io import read, write
    from ..utils import descriptor_utils

    class ExplorerSampler:
        def __init__(self, config: FullConfig):
            self._config = config
            self._surrogate_calc = self._load_surrogate_model()

        def execute(self, initial_structures: List[Atoms]) -> List[Atoms]:
            """Runs surrogate MD and then performs DIRECT sampling."""
            trajectory = self._run_surrogate_md(initial_structures)
            sampled_structures = self._perform_direct_sampling(trajectory)
            return sampled_structures

        def _load_surrogate_model(self):
            # Logic to load a pre-trained MACE model and wrap it
            # in an ASE Calculator object. Must handle CPU/GPU device placement.

        def _run_surrogate_md(self, structures: List[Atoms]) -> Trajectory:
            # For each starting structure, run a high-T MD simulation
            # using the surrogate calculator and ASE's dynamics modules.
            # Concatenate results into a single trajectory.

        def _perform_direct_sampling(self, trajectory: Trajectory) -> List[Atoms]:
            # 1. Calculate descriptors for all frames (call descriptor_utils)
            # 2. Use scikit-learn for PCA and KMeans clustering
            # 3. Implement stratified sampling to select frames
            # 4. Return the selected structures
    ```

2.  **`utils/descriptor_utils.py`**: This new module will contain the performance-critical code, optimized with Numba. The primary function will calculate a simplified local environment descriptor for speed.
    ```python
    import numpy as np
    from numba import jit, prange

    @jit(nopython=True, parallel=True)
    def fast_rdf_calculator(positions: np.ndarray, cell: np.ndarray, r_cut: float, n_bins: int):
        """
        A Numba-optimized function to calculate a simplified Radial Distribution
        Function descriptor for a single frame.
        This is an example; a more complex descriptor like SOAP could also be implemented.
        """
        # ... highly optimized, parallelized loops over atoms ...
        return rdf_descriptor
    ```

3.  **`orchestrator_cycle03.py`**: The orchestrator's logic is updated to insert Module B into the workflow.
    ```python
    # Simplified example
    def run_cycle03_workflow(config_path: str):
        # ... load config etc. ...
        generator = StructureGenerator(full_config)
        initial_seeds = generator.execute()

        # New step for Cycle 03
        explorer = ExplorerSampler(full_config)
        curated_structures = explorer.execute(initial_seeds)

        # Continue with existing flow, but use the new curated list
        labeller = LabellingEngine(...)
        db_ids = []
        for structure in curated_structures:
            db_id = labeller.execute(structure)
            db_ids.append(db_id)

        trainer = TrainingEngine(...)
        trainer.execute(ids=db_ids)
        print("Cycle 03 workflow complete.")
    ```
This design encapsulates the complexity of the exploration and sampling within the `ExplorerSampler` class. It makes a clear distinction between the high-level orchestration of the MD run and the low-level, high-performance calculation of descriptors, which is delegated to a separate, specialized utility module. This separation is key for maintainability and testing.

## 4. Implementation Approach

The implementation of Cycle 03 will be staged to manage complexity, focusing on integrating the external model first, then building the sampling logic, and finally optimizing for performance.

**Step 1: Surrogate Model Integration**
1.  **Model Selection and Loading:** We will select a suitable pre-trained foundation model (e.g., MACE-MP from the official repository). We will implement the `_load_surrogate_model` method in `ExplorerSampler`. This will involve using the `mace.load_model` function and writing a simple wrapper to make it compatible with the ASE `Calculator` API. The code must include logic to check for an available GPU and move the model to the `cuda` device if possible.
2.  **MD Simulation:** We will implement the `_run_surrogate_md` method. This will use standard ASE libraries like `ase.md.langevin.Langevin` to run the dynamics. We will configure the simulation parameters (temperature, timestep, duration) from the `FullConfig` object. The output will be a standard ASE trajectory file (`.traj`).

**Step 2: DIRECT Sampling Implementation**
1.  **Descriptor Calculation (Initial Version):** We will first implement the descriptor calculation using an existing high-level library like `dscribe`. This will allow us to get the logic of the sampling pipeline working correctly without premature optimization. We will compute SOAP descriptors for every atom in every frame of the trajectory.
2.  **Dimensionality Reduction and Clustering:** We will use `scikit-learn` to implement the next steps. We will use `sklearn.decomposition.PCA` to reduce the high-dimensional descriptor space and then `sklearn.cluster.KMeans` to group the configurations into clusters.
3.  **Stratified Sampling:** We will write the logic to sample from the identified clusters. This involves iterating through each cluster, selecting one or more representative members (e.g., the one closest to the cluster centroid), and adding them to our final list of curated structures.

**Step 3: Performance Optimization with Numba**
1.  **Identify Bottleneck:** We will profile the DIRECT sampling implementation and confirm that the descriptor calculation is the primary bottleneck, as expected.
2.  **Write Numba Kernel:** We will create the `utils/descriptor_utils.py` module. Inside, we will write a custom, Numba-optimized function (using `@jit`) to calculate a simplified descriptor, such as a radial distribution function, or a simplified SOAP-like descriptor. The key is to use NumPy arrays and explicit loops that Numba can effectively compile and parallelize.
3.  **Replace and Benchmark:** We will replace the call to the high-level library in `ExplorerSampler` with a call to our new, fast utility function. We will then create a benchmark test to measure the performance difference and assert that a significant speedup (e.g., an order of magnitude) has been achieved.

**Step 4: Integration and Testing**
1.  **Update Orchestrator:** The main workflow orchestrator will be updated as described in the Design Architecture section to include the new `ExplorerSampler` module.
2.  **Configuration Update:** The `HeuristicEngine` from Cycle 02 will be updated to add the new `exploration` section to the `FullConfig` it generates.
3.  **End-to-End Testing:** New integration tests will be developed to run the full workflow, verifying that the number of structures passed to the `LabellingEngine` matches the number requested from the sampler, and that these structures are indeed different from the initial seeds.

## 5. Test Strategy

Testing for Cycle 03 is crucial to validate both the physical correctness of the exploration and the performance of the implementation. The strategy includes unit tests for the algorithm's logic, integration tests for the new workflow, and specific performance benchmarks.

**Unit Testing:**

*   **`ExplorerSampler`:**
    *   **Model Loading:** A test will check that the `_load_surrogate_model` method correctly loads a model file and returns a valid ASE `Calculator` object. It will also test the device placement logic by mocking the `torch.cuda.is_available` function.
    *   **Sampling Logic:** We will test the `_perform_direct_sampling` method on a pre-generated, static trajectory file. This allows us to test the clustering and sampling logic without the overhead of an MD run. We will assert that the number of returned structures matches the requested number and that they are drawn from different parts of the trajectory.
    *   **MD Runner Mocking:** We will test the main `execute` method by mocking the `_run_surrogate_md` call to simply return a path to a static trajectory file. This allows us to test the overall orchestration of the class without a real MD run.

*   **`descriptor_utils`:**
    *   **Numerical Correctness:** The Numba-optimized descriptor function will be tested for correctness. We will run it on a simple, known atomic configuration (e.g., a 4-atom square) and assert that the output descriptor vector matches a pre-calculated, known-good result.
    *   **Comparison Test:** We will compare the output of our Numba function against a pure, unoptimized Python implementation for the same input, asserting that the results are numerically identical within a small tolerance.

**Integration Testing:**

*   **Test 1: Short End-to-End Exploration Run:**
    *   **Objective:** Verify that the new Module B integrates correctly into the main workflow.
    *   **Setup:** Use a simple `input.yaml` for a system like bulk Aluminum. Configure the exploration to be very short (e.g., 20 MD steps) and to sample 5 structures.
    *   **Execution:** Run the full Cycle 03 workflow.
    *   **Verification:** The test will assert that the workflow completes without errors. It will then query the database and verify that exactly 5 new structures were added and sent for labelling. It will also check that these structures are geometrically different from each other.

**Performance Testing:**

*   **Test 1: Descriptor Calculation Benchmark:**
    *   **Objective:** Quantify and verify the performance gain from using Numba.
    *   **Setup:** Create a test script that takes a medium-sized trajectory file (e.g., 1000 frames) as input.
    *   **Execution:** The script will first calculate descriptors for the entire trajectory using a slow, pure-Python/library-based method and record the time. It will then do the same using the Numba-optimized `fast_rdf_calculator` function.
    *   **Verification:** The test will assert that the execution time of the Numba version is at least 10 times faster than the pure Python version. This test is critical to ensure that the performance-critical requirement of this cycle has been met.
