# Cycle 03: Efficient Exploration - User Acceptance Test (UAT) Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 03
**Title:** UAT for Efficient Phase Space Exploration and Intelligent Sampling

## 1. Test Scenarios

This document outlines the User Acceptance Tests (UAT) for the functionality developed in Cycle 03. The focus of this cycle is the introduction of the **Explorer & Sampler (Module B)**, which uses a fast surrogate potential to explore the material's phase space and intelligently select training candidates. These tests are designed to verify from a user's perspective that this new exploration phase is working correctly, improving the diversity of the dataset, and that its performance is acceptable.

| Scenario ID | Test Scenario Description                                                                                             | Priority |
| :---------- | :---------------------------------------------------------------------------------------------------------------------- | :------- |
| UAT-C03-01  | **Successful Workflow with Exploration:** Verify that the full pipeline, now including Module B, runs end-to-end without errors. | High     |
| UAT-C03-02  | **Verification of Sampled Structures:** Confirm that the structures selected by the DIRECT sampler are diverse and sourced from the MD trajectory. | High     |
| UAT-C03-03  | **GPU Acceleration:** Verify that the system automatically utilizes an available GPU for the surrogate MD simulation to accelerate the process. | Medium   |
| UAT-C03-04  | **Controllable Sampling Parameters:** Ensure that the user can control the number of sampled structures via the configuration file. | High     |

### Scenario Details

**UAT-C03-01: Successful Workflow with Exploration**
This is the main "happy path" test for the new, more complex workflow. The user will take a working `input.yaml` from Cycle 02 and add a new section to enable the exploration phase. For example:
```yaml
# ... elements and composition ...
exploration:
  enabled: true
  md_steps: 1000
  sample_count: 10
```
The user will then execute the main workflow. The primary acceptance criterion is that the entire pipeline completes successfully and produces a trained MLIP model. This test validates the high-level integration of Module B with the existing modules and confirms that the data flows correctly from the new exploration stage to the labelling and training stages.

**UAT-C03-02: Verification of Sampled Structures**
This test is designed to confirm that the sampler is not just a placeholder but is actively selecting meaningful structures from a dynamic simulation. After running the workflow from UAT-C03-01, the user will inspect the intermediate data. The acceptance criteria are:
1. The user will visualize the short MD trajectory file produced by the surrogate model and observe that the atoms are in motion, indicating a real simulation took place.
2. The user will then visualize the final structures that were stored in the `mlip.db` database. They should be able to see that these structures are varied and are "snapshots" from the trajectory, clearly different from the initial static crystal structure that started the simulation. For example, they should show thermal displacements and slightly distorted cell shapes. This confirms the core value proposition of Module B.

**UAT-C03-03: GPU Acceleration**
This test verifies a key performance feature. The user will need to run the workflow on a machine equipped with a compatible NVIDIA GPU and the required CUDA libraries. The user will monitor the GPU's utilization during the run using a tool like `nvidia-smi`. The acceptance criterion is that during the "Exploration Phase" of the workflow, the `nvidia-smi` command shows significant GPU utilization (e.g., > 10%) and memory usage by the Python process. This confirms that the system correctly detects and leverages the available GPU to speed up the most computationally intensive part of this cycle. If no GPU is present, the test is considered passed if the workflow still completes successfully on the CPU.

**UAT-C03-04: Controllable Sampling Parameters**
This test ensures that the user has effective control over the new module's behavior. The user will perform two consecutive runs. In the first run, they will set `sample_count: 5` in the exploration section of their `input.yaml`. In the second run, they will change this to `sample_count: 15`. The acceptance criterion is that after each run, a query to the `mlip.db` database shows that the number of newly added structures is exactly 5 and 15, respectively. This test validates that the configuration is being correctly parsed and acted upon by the `ExplorerSampler`.

## 2. Behavior Definitions

The following behavior definitions are written in Gherkin style to provide a clear, unambiguous description of the expected system behavior for the key test scenarios.

---

**Scenario: UAT-C03-01 - Successful Workflow with Exploration**

**GIVEN** I have a minimal configuration file `input_with_explore.yaml` that enables the exploration phase.
**WHEN** I execute the command `python -m mlip_autopipec.main_cycle03 --config input_with_explore.yaml`.
**THEN** the script should run to completion without raising any errors.
**AND** the script's output should log the start and end of the "Exploration Phase".
**AND** a trained model file must be created successfully.

---

**Scenario: UAT-C03-02 - Verification of Sampled Structures**

**GIVEN** I have successfully run the workflow from scenario UAT-C03-01.
**AND** an intermediate trajectory file `surrogate_md.traj` has been created.
**WHEN** I inspect the final structures stored in the `mlip.db` database.
**THEN** the potential energy of the first stored structure must be different from the potential energy of the last stored structure.
**AND** the atomic positions of the stored structures must be visibly different from the initial, perfect crystal structure.

---

**Scenario: UAT-C03-03 - GPU Acceleration**

**GIVEN** I am running the workflow on a machine with a supported NVIDIA GPU.
**AND** I am monitoring the GPU status with the `nvidia-smi` command.
**WHEN** the workflow's log indicates it is in the "Exploration Phase" running surrogate MD.
**THEN** the output of `nvidia-smi` should show a running process associated with the Python script.
**AND** that process should show non-zero GPU and Memory utilization.

---

**Scenario: UAT-C03-04 - Controllable Sampling Parameters**

**GIVEN** I have a configuration file `input.yaml` with `exploration.sample_count` set to `8`.
**WHEN** I run the full workflow.
**THEN** the number of new structures added to the `mlip.db` database for this run must be exactly `8`.
**GIVEN** I then change the `exploration.sample_count` in `input.yaml` to `12`.
**WHEN** I run the full workflow again.
**THEN** the number of new structures added to the `mlip.db` database for this second run must be exactly `12`.

---
