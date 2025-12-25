# Cycle 04: The Active Learning Loop - User Acceptance Test (UAT) Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 04
**Title:** UAT for On-the-Fly Simulation and Autonomous Retraining

## 1. Test Scenarios

This document outlines the User Acceptance Tests (UAT) for the functionality developed in Cycle 04. This cycle introduces the complete, autonomous **Active Learning Loop**, the core feature of the MLIP-AutoPipe system. These tests are designed to verify, from a user's perspective, that the system can successfully use its own potential to run simulations, detect model uncertainty, and automatically trigger a retraining cycle to improve itself. The focus is on the correctness of the control loop, the tangible output of the process, and the user's ability to control its behavior.

| Scenario ID | Test Scenario Description                                                                                             | Priority |
| :---------- | :---------------------------------------------------------------------------------------------------------------------- | :------- |
| UAT-C04-01  | **Successful Single-Generation Active Learning Run:** Verify that the system can complete one full cycle of the active learning loop. | High     |
| UAT-C04-02  | **Verification of Model Retraining:** Confirm that the active learning cycle produces a new, updated MLIP model file.         | High     |
| UAT-C04-03  | **Controllable Number of Generations:** Ensure the user can specify the maximum number of retraining cycles.                   | Medium   |
| UAT-C04-04  | **Graceful Finish with No Uncertainty:** Verify the system completes a simulation without retraining if the uncertainty threshold is never met. | High     |

### Scenario Details

**UAT-C04-01: Successful Single-Generation Active Learning Run**
This is the most critical "happy path" test for the entire project's concept. The user will configure the workflow to run for a single active learning generation (`max_generations: 1`) and set a reasonably low uncertainty threshold to ensure it triggers. The user then launches the full workflow. The acceptance criterion is that the system runs to completion without errors. The user must be able to see from the console output or log files clear evidence of the loop's execution: the start of the simulation, a message indicating high uncertainty was detected, the pausing of the simulation, the triggering of DFT labelling and retraining, and the final resumption and completion of the simulation.

**UAT-C04-02: Verification of Model Retraining**
This test provides tangible proof that the retraining process is not just being logged, but is actually happening. After a successful run of UAT-C04-01, the user will inspect the project's model directory. The acceptance criterion is the existence of at least two MLIP model files: the initial model (e.g., `MLIP_v0.pt`) and the updated model created after the first retraining cycle (e.g., `MLIP_v1.pt`). The user must verify that these two files are not identical, for example by checking their file sizes or computing their file hashes (`md5sum`). A difference between the files proves that the Training Engine was run with new data and a new model was saved.

**UAT-C04-03: Controllable Number of Generations**
This test verifies that the user can control the duration and depth of the active learning process. The user will modify the configuration to run for two generations (`max_generations: 2`) and set a low uncertainty threshold. The acceptance criteria are:
1. The system must complete the workflow successfully.
2. The logs must show evidence of the active learning loop being completed twice.
3. The ASE database must contain exactly two new atomic configurations that were added "on-the-fly" during the simulation.
This test confirms that the orchestrator's main control loop is correctly managing the state and iteration count.

**UAT-C04-04: Graceful Finish with No Uncertainty**
This test verifies the system's behavior in the case where the initial model is already very good and never encounters situations of high uncertainty. The user will configure the active learning loop but set the `uncertainty_threshold` to an extremely high, physically unreachable value (e.g., `1000.0`). The acceptance criteria are:
1. The LAMMPS simulation should start and run to its full, pre-defined number of steps without being interrupted.
2. The system should finish gracefully with a success message.
3. The logs must not contain any messages about uncertainty being triggered or retraining being initiated.
4. No new model files should be created beyond the initial one.
This test ensures the system does not get stuck or behave incorrectly when its self-improvement mechanism is not needed.

## 2. Behavior Definitions

The following behavior definitions are written in Gherkin style to provide a clear, unambiguous description of the expected system behavior for the key test scenarios.

---

**Scenario: UAT-C04-01 - Successful Single-Generation Active Learning Run**

**GIVEN** I have a configuration file `active_learning.yaml` with `active_learning.enabled: true` and `active_learning.max_generations: 1`.
**AND** the `uncertainty_threshold` is set to a low value.
**WHEN** I execute the main workflow command.
**THEN** the script should run to completion without raising any errors.
**AND** the application log must contain messages in the following order: "Starting initial simulation", "Uncertainty threshold exceeded", "Pausing simulation", "Starting DFT labelling for new structure", "Starting retraining", "Resuming simulation".

---

**Scenario: UAT-C04-02 - Verification of Model Retraining**

**GIVEN** I have successfully run the workflow from scenario UAT-C04-01.
**AND** an initial model file named `MLIP_v0.pt` was created.
**WHEN** I check the contents of the model directory.
**THEN** a new model file named `MLIP_v1.pt` must also exist.
**AND** the file hash of `MLIP_v0.pt` must not be identical to the file hash of `MLIP_v1.pt`.

---

**Scenario: UAT-C04-03 - Controllable Number of Generations**

**GIVEN** I have a configuration file with `active_learning.max_generations` set to `2`.
**AND** the `uncertainty_threshold` is set to a low value.
**WHEN** I run the full workflow.
**THEN** the application log must show that the retraining process was initiated exactly two times.
**AND** when I query the `mlip.db` database, the number of entries with a comment like "Added from OTF generation" must be exactly `2`.

---

**Scenario: UAT-C04-04 - Graceful Finish with No Uncertainty**

**GIVEN** I have a configuration file with `active_learning.enabled: true`.
**AND** the `active_learning.uncertainty_threshold` is set to `1000.0`.
**WHEN** I execute the main workflow command.
**THEN** the script should run to completion without raising any errors.
**AND** the application log must show that the main simulation completed its full number of steps.
**AND** the log must not contain any messages like "Uncertainty threshold exceeded" or "Starting retraining".
**AND** only the initial `MLIP_v0.pt` model file should exist in the model directory.

---
