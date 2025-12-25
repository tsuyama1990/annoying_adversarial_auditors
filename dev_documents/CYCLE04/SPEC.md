# Cycle 04: The Active Learning Loop - Specification Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 04
**Title:** Closing the Loop: On-the-Fly Simulation and Autonomous Retraining

## 1. Summary

This document provides the detailed technical specification for the fourth and most transformative development cycle of the MLIP-AutoPipe project. Cycles 01-03 established a powerful, automated pipeline for generating a high-quality initial MLIP. Cycle 04 brings the project to its ultimate goal by "closing the loop," transforming the linear pipeline into a dynamic, self-improving, autonomous system. This will be achieved by implementing the **Simulation Engine (Module E)** and embedding it within a global **Active Learning Loop**, managed by the central `WorkflowOrchestrator`. The system will now be capable of using its own trained MLIP to run a full-scale molecular dynamics (MD) or kinetic Monte Carlo (kMC) simulation. Crucially, while the simulation runs, the system will actively monitor its own performance, detecting moments of high uncertainty where the model is forced to extrapolate into unknown territory. When such an event is detected, the system will automatically pause, capture the novel atomic configuration, acquire the correct DFT label for it, and retrain the MLIP to incorporate the new knowledge.

The core of this cycle is the implementation of the **On-the-Fly (OTF) Inference Loop**. This is the mechanism that gives the system its autonomy. The Simulation Engine (Module E) will not just run a simulation but will do so under constant self-scrutiny. It will use the MLIP to predict not only forces but also an estimate of the model's own uncertainty. This "uncertainty metric" is the key signal. When it exceeds a user-defined threshold, it acts as a trigger, indicating that the simulation has encountered a configuration that was not well-represented in the initial training data. This is precisely the moment when new, valuable information can be gathered. The orchestrator will manage this entire feedback process: pausing the simulation (run via an external engine like LAMMPS), extracting the structure, dispatching it to the Labelling Engine (Module C), adding the new data to the training set, invoking the Training Engine (Module D) to create an improved potential, and finally, resuming the simulation with the new, more knowledgeable MLIP.

This cycle represents the culmination of all previous efforts and delivers on the project's central promise: removing the human expert from the loop. The system will no longer be just a tool for generating a static potential; it will become a dynamic agent for scientific discovery, capable of autonomously exploring complex energy landscapes and iteratively improving its understanding of the material's physics. A key technical detail is the method of structure extraction; to ensure the DFT calculations are physically meaningful, high-uncertainty configurations will be extracted as small, periodic cells ("periodic embeddings") rather than simple atomic clusters, thereby avoiding spurious surface effects. The successful completion of this cycle will result in a system that can generate MLIPs that are not only accurate for known configurations but are robust and reliable even when exploring rare events and complex, long-timescale phenomena.

## 2. System Architecture

The introduction of the Active Learning Loop in Cycle 04 fundamentally changes the system's architecture from a linear, sequential pipeline to a cyclical, state-driven one. The `WorkflowOrchestrator` evolves from a simple script into a state machine that manages the entire autonomous learning process. Module E, the Simulation Engine, is added as the primary "workhorse" that uses the MLIP, while also serving as the sensor that detects uncertainty.

The new cyclical workflow is as follows:
1.  **Initial Training:** The workflow begins by executing the full pipeline from Cycles 01-03, resulting in a high-quality initial MLIP, which we can call `MLIP_v0`.
2.  **Start Simulation (Module E):** The `Orchestrator` initiates a long-running MD or kMC simulation in Module E (interfacing with LAMMPS), using `MLIP_v0` as the force calculator.
3.  **On-the-Fly Monitoring (Module E):** As the LAMMPS simulation proceeds, the `Orchestrator` periodically (or via a callback mechanism) queries the state of the simulation. For each new configuration, it uses the MLIP to calculate both the forces and an uncertainty score.
4.  **Uncertainty Trigger:** The uncertainty score is compared against a threshold defined in the configuration. If it is below the threshold, the simulation continues. If it is exceeded:
    a.  The `Orchestrator` pauses the LAMMPS simulation.
    b.  It extracts the high-uncertainty atomic configuration.
5.  **Re-Labelling (Module C):** The orchestrator sends this single, highly informative structure back to the DFT Labelling Engine.
6.  **Re-Training (Module D):** Once the new DFT label is stored in the database, the `Orchestrator` invokes the Training Engine. The training set now includes all previous data plus the new point. The result is an improved potential, `MLIP_v1`.
7.  **Resume Simulation:** The `Orchestrator` replaces `MLIP_v0` with `MLIP_v1` in the Simulation Engine and resumes the LAMMPS simulation from where it was paused.
8.  **Loop:** This process (steps 3-7) is repeated, creating `MLIP_v2`, `MLIP_v3`, and so on, for a user-defined number of "generations" or until no more uncertainties are detected.

**Architectural Placement:**

```mermaid
graph TD
    subgraph "Initial Phase (Cycles 1-3)"
        A[Start] --> B(Generate Initial MLIP v0)
    end

    B --> C{Workflow Orchestrator};

    subgraph "Active Learning Loop"
        C --1. Start/Resume Sim w/ MLIP vN--> D[Module E: Simulation Engine (LAMMPS)];
        D --2. Run & Monitor--> C;
        C --3. Uncertainty > Threshold?--> E{Decision};
        E --No--> D;
        E --Yes--> F[Pause Sim & Extract Structure];
        F --4. Send Structure--> G[Module C: Labelling Engine];
        G --5. Get New Label--> H[Data Store: ASE DB];
        H --6. Add to Dataset--> I[Module D: Training Engine];
        I --7. Train--> J[New MLIP vN+1];
        J --8. Update Model--> C;
    end

    style C fill:#f9f,stroke:#333,stroke-width:2px
```

This cyclical architecture requires robust state management within the `Orchestrator`. It must keep track of the current generation, the path to the latest MLIP, and the state of the external LAMMPS simulation. Communication with LAMMPS will likely be file-based, where the `Orchestrator` writes a "pause" file that LAMMPS is scripted to check for periodically.

## 3. Design Architecture

The design for Cycle 04 is centered around the new `SimulationEngine` class and the significantly more complex `WorkflowOrchestrator`.

**File and Class Structure:**

```
mlip_autopipec/
├── orchestrator_cycle04.py    # New state-machine orchestrator
├── modules/
│   ├── ...                      # Modules A, B, C, D
│   └── e_simulation_engine.py   # New module for this cycle
├── utils/
│   └── lammps_utils.py          # Helpers for running/controlling LAMMPS
└── ...
```

**Class and API Definitions:**

1.  **`modules/e_simulation_engine.py`**: This file will contain the `SimulationEngine` class, a Python interface to the external LAMMPS process.
    ```python
    import subprocess

    class SimulationEngine:
        def __init__(self, config: FullConfig):
            self._config = config
            self._process: subprocess.Popen | None = None

        def start(self, structure: Atoms, mlip_path: str):
            """Generates LAMMPS input files and starts the simulation
            as a background subprocess."""
            # Use lammps_utils to create data file and input script
            # self._process = subprocess.Popen(["lmp", "-in", "in.lammps"])

        def pause(self):
            """Pauses the running LAMMPS simulation (e.g., by creating a stop file)."""

        def resume(self, mlip_path: str):
            """Resumes the simulation, potentially with a new MLIP."""

        def get_current_structure(self) -> Atoms:
            """Reads the latest structure from the LAMMPS trajectory output."""
    ```

2.  **`utils/lammps_utils.py`**: Helper functions for interacting with LAMMPS.
    ```python
    def write_lammps_data(structure: Atoms, file_path: str):
        # ... ASE's built-in writers or custom logic ...

    def write_lammps_input(mlip_path: str, ...):
        # ... logic to generate the text for 'in.lammps', including
        # the 'pair_style mace' and commands to periodically check
        # for a 'stop' file.
    ```

3.  **`modules/d_training_engine.py` (Modification)**: The `TrainingEngine` and the underlying MLIP model must be modified to provide uncertainty estimates.
    ```python
    # Inside the MACE/NequIP wrapper
    def predict(self, atoms: Atoms) -> (Forces, float):
        # ... existing prediction logic ...
        # Add logic for uncertainty, e.g., committee disagreement
        uncertainty = model.get_uncertainty(atoms)
        return forces, uncertainty
    ```

4.  **`orchestrator_cycle04.py`**: The new orchestrator with the main loop.
    ```python
    class WorkflowOrchestrator:
        def __init__(self, config):
            self._config = config
            # ... instantiate all modules ...

        def execute(self):
            # 1. Run initial data generation and training (Cycles 2-3)
            #    to get the initial MLIP.
            initial_mlip_path = self._run_initial_phase()

            # 2. Start the main active learning loop.
            self._run_active_learning_loop(initial_mlip_path)

        def _run_active_learning_loop(self, mlip_path):
            current_mlip = mlip_path
            self.sim_engine.start(initial_structure, current_mlip)

            for gen in range(self._config.active_learning.max_generations):
                while simulation_is_running:
                    # Monitor loop
                    time.sleep(self._config.active_learning.monitor_interval)
                    current_structure = self.sim_engine.get_current_structure()
                    _, uncertainty = self.trainer.predict(current_structure)

                    if uncertainty > self._config.active_learning.threshold:
                        self.sim_engine.pause()
                        # Extract structure (using periodic embedding)
                        new_label_id = self.labeller.execute(extracted_structure)
                        current_mlip = self.trainer.execute(
                            ids=self.db.get_all_ids()
                        )
                        self.sim_engine.resume(current_mlip)
                        break # Exit monitor loop to start next generation
    ```
This design clearly encapsulates the interaction with the external simulator within the `SimulationEngine`. The `Orchestrator` is the "brain," managing the overall state and the decision logic of the loop, making it the most complex component of the system.

## 4. Implementation Approach

The implementation of Cycle 04 will be methodical, starting with basic control of the external simulator and progressively building the full autonomous loop.

**Step 1: Basic LAMMPS Integration**
1.  **LAMMPS Utilities:** First, implement the helper functions in `lammps_utils.py`. This includes a robust function to write an ASE Atoms object to a LAMMPS data file and a function to generate a basic `in.lammps` script that uses a generic MLIP (like MACE).
2.  **`SimulationEngine` Scaffolding:** Implement the `start` method in the `SimulationEngine`. The goal is to successfully launch a LAMMPS simulation as a background process from Python. This step is complete when a test can start a simulation and verify that a LAMMPS process is running.

**Step 2: Implementing Uncertainty Quantification**
1.  **Model Adaptation:** The core MLIP model wrapper will be modified to provide an uncertainty metric. A practical approach is to use a "deep ensemble" or committee. The `TrainingEngine` will be modified to train not one, but a small number (e.g., 3-5) of MLIPs with different random initializations.
2.  **Uncertainty Calculation:** The `predict` method will now run inference with all models in the committee. The uncertainty will be calculated as the standard deviation of the force predictions among the committee members. A high standard deviation means the models disagree, indicating high uncertainty.

**Step 3: Building the Monitoring and Control Loop**
1.  **Pause/Resume Mechanism:** The most challenging part of the LAMMPS interaction is implementing a reliable pause/resume mechanism. A simple and robust approach is file-based signaling. The `in.lammps` script will be modified to include a loop that periodically checks for the existence of a file (e.g., `PAUSE_SIM`). If the file exists, LAMMPS will stop. The `SimulationEngine.pause()` method will simply create this file. The `resume()` method will delete the file and restart the LAMMPS process from the last saved state.
2.  **Monitoring Logic:** Implement the monitoring loop within the `Orchestrator` as designed above. It will periodically get the latest structure from the running simulation's output trajectory, call the model's `predict` method to get the uncertainty, and check it against the threshold.

**Step 4: Implementing the Full Active Learning Loop**
1.  **Periodic Embedding:** Implement the structure extraction logic. This function will take the full simulation cell and the index of the atom with the highest uncertainty. It will then carve out a smaller, fully periodic cell centered on this atom, ensuring that the local environment is perfectly preserved for the subsequent DFT calculation.
2.  **Orchestrator State Machine:** Assemble all the pieces into the final `_run_active_learning_loop` method in the `Orchestrator`. This involves managing the state transitions: `running` -> `paused` -> `labelling` -> `training` -> `running`. The logic must correctly handle passing the new MLIP path to the `resume` method and updating the training dataset for the next iteration.

**Step 5: Testing**
Given the complexity, testing will be critical. The "mock loop" integration test, where the expensive DFT and training steps are replaced by fast dummy functions, will be the most important test to build. This will allow for rapid testing of the orchestrator's complex logic (state transitions, pause/resume signals, etc.) without the hours-long wait times of the real components. A final, short end-to-end test will be run to validate the entire system.

## 5. Test Strategy

Testing Cycle 04 requires a focus on the complex interactions and state management of the new active learning loop.

**Unit Testing:**

*   **`SimulationEngine`:**
    *   **Input Generation:** Test the `lammps_utils` functions to ensure they generate syntactically correct LAMMPS input and data files for a variety of `ase.Atoms` objects.
    *   **Process Control Mocking:** The `start`, `pause`, and `resume` methods will be tested by mocking the `subprocess.Popen` and file system calls (`os.path.exists`, `os.remove`). We will assert that `pause()` creates the signal file and `resume()` removes it, and that the correct command is used to start the process.

*   **Uncertainty Calculation:**
    *   Test the uncertainty logic with a mock model committee. We will create a dummy committee where models return pre-defined, different force values and assert that the calculated standard deviation (the uncertainty) is correct.

*   **`Orchestrator`:**
    *   Test the periodic embedding extraction function with a known large cell and assert that the extracted smaller cell is correct.

**Integration Testing:**

*   **Test 1: Mock Active Learning Loop:**
    *   **Objective:** This is the most critical test. It must verify the orchestrator's entire state machine logic without the expensive components.
    *   **Setup:**
        *   Replace `LabellingEngine.execute` with a dummy function that returns immediately.
        *   Replace `TrainingEngine.execute` with a dummy that returns a new fake model path.
        *   Replace `SimulationEngine` with a mock that simulates a process, writes dummy trajectory files, and responds to the pause/resume signals.
        *   The mock `SimulationEngine`'s associated uncertainty model will be programmed to return a high uncertainty value after a specific number of steps (e.g., 5).
    *   **Execution:** Run the `_run_active_learning_loop` with `max_generations` set to 2.
    *   **Verification:** Assert that the loop runs exactly twice. Assert that the `pause` and `resume` methods on the mock `SimulationEngine` were called twice. Assert that the (mocked) `LabellingEngine` and `TrainingEngine` were also called twice. This validates the entire control flow.

**End-to-End (E2E) Testing:**

*   **Test 1: Short Full-System Run:**
    *   **Objective:** Verify that all real components work together for a short run.
    *   **Setup:** Use a simple system (e.g., bulk Al). Configure the active learning with `max_generations: 1` and a low uncertainty threshold to ensure it triggers quickly. The initial exploration phase should also be minimal.
    *   **Execution:** Run the full `main_cycle04` workflow.
    *   **Verification:** The workflow must complete without crashing. The logs must be inspected to confirm that one full cycle of the loop (simulation -> uncertainty detection -> pause -> labelling -> training -> resume) was actually executed with the real components. The final test is to check that a new, second MLIP file was created.
