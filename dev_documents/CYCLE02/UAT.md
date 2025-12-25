# Cycle 02: Automation Kickstart - User Acceptance Test (UAT) Document

**Version:** 1.0.0
**Status:** Final
**Cycle:** 02
**Title:** UAT for Initial Structure and Configuration Automation

## 1. Test Scenarios

This document outlines the User Acceptance Tests (UAT) for the functionality developed in Cycle 02. This cycle's primary goal is to remove the need for manual user intervention in providing atomic structures and detailed configurations. The user now interacts with the system via a single, high-level `input.yaml` file. These tests are designed from the perspective of a user to verify that this new, simplified workflow is functional, intelligent, and robust. The user will test the system's ability to correctly interpret their scientific intent, automatically generate appropriate inputs for the backend, and handle incorrect or unsupported requests gracefully.

| Scenario ID | Test Scenario Description                                                                                             | Priority |
| :---------- | :---------------------------------------------------------------------------------------------------------------------- | :------- |
| UAT-C02-01  | **Successful Alloy Workflow from Minimal Input:** Verify a full run for an alloy system starting from a minimal `input.yaml`.       | High     |
| UAT-C02-02  | **Successful Molecule Workflow from Minimal Input:** Verify a full run for a molecular system starting from a minimal `input.yaml`. | High     |
| UAT-C02-03  | **Verification of Generated `exec_config_dump.yaml`:** Confirm that the Heuristic Engine produces a complete and sensible configuration file. | High     |
| UAT-C02-04  | **Verification of Generated Structures:** Check that Module A produces a diverse and valid set of initial atomic structures in the database. | Medium   |
| UAT-C02-05  | **Handling of Invalid Composition:** Ensure the system gives a clear error message for a composition with unsupported elements.     | High     |

### Scenario Details

**UAT-C02-01: Successful Alloy Workflow from Minimal Input**
This is the primary "happy path" test for a common use case. The user will create a very simple `input.yaml` file containing only the elements and composition for a binary alloy, for example, `elements: [Cu, Au]` and `composition: CuAu`. They will then execute the main workflow. The acceptance criterion is that the entire pipeline runs to completion without any errors and produces a final trained MLIP model file. This test validates that the Heuristic Engine correctly identifies the system as an 'alloy', triggers the SQS algorithm in Module A, and that the generated structures are successfully processed by the core engine from Cycle 01.

**UAT-C02-02: Successful Molecule Workflow from Minimal Input**
This test is similar to the first but validates a different path through the system's logic. The user will create a minimal `input.yaml` for a simple molecule, for example, `elements: [H, O]` and `composition: H2O`. They will run the main workflow. The acceptance criterion is, again, the successful creation of a trained MLIP model file without any errors. This test confirms that the Heuristic Engine correctly identifies the system as a 'molecule' and triggers the Normal Mode Sampling (NMS) algorithm, demonstrating the system's ability to handle different material types correctly.

**UAT-C02-03: Verification of Generated `exec_config_dump.yaml`**
This test focuses on the output of the Heuristic Engine. After running the workflow from UAT-C02-01, the user will inspect the `exec_config_dump.yaml` file that was created. The acceptance criteria are:
1. The file must be valid YAML.
2. The `system.structure_type` field must be correctly set to `'alloy'`.
3. The `dft_compute` section must be fully populated with specific, sensible values for `ecutwfc`, `ecutrho`, and `pseudopotentials`. The user should see that the cutoff energy is a reasonable number (e.g., > 40 Ry) and not zero or null.
This test verifies that the core automation logic is working as intended and is making reasonable, expert-level decisions.

**UAT-C02-04: Verification of Generated Structures**
This test verifies the output of the Structure Generator (Module A). After running the workflow from UAT-C02-01, the user will inspect the `mlip.db` database. The acceptance criteria are:
1. The database should contain multiple new entries (e.g., more than 5).
2. The user should be able to extract these structures (e.g., by visualizing them or checking their properties) and see that they are not all identical. They should observe variations in atomic positions and cell shape, indicating that the generation process is creating a diverse dataset.
This test confirms that Module A is not just running, but is producing a useful and varied set of inputs for the training process.

**UAT-C02-05: Handling of Invalid Composition**
This test checks the system's input validation and robustness. The user will create an `input.yaml` containing a fictional element, e.g., `elements: [Fe, Zz]`. They will then execute the workflow. The acceptance criterion is that the system exits gracefully with a clear, user-friendly error message, such as "Error: The element 'Zz' is not supported or has no corresponding pseudopotential in the SSSP library." The system must not crash or produce a long, cryptic traceback. This test validates the error-handling capabilities of the Heuristic Engine.

## 2. Behavior Definitions

The following behavior definitions are written in Gherkin style to provide a clear, unambiguous description of the expected system behavior for the key test scenarios.

---

**Scenario: UAT-C02-01 - Successful Alloy Workflow from Minimal Input**

**GIVEN** I have a minimal configuration file named `cuau_input.yaml` with the content:
```yaml
elements: [Cu, Au]
composition: CuAu
```
**WHEN** I execute the command `python -m mlip_autopipec.main_cycle02 --config cuau_input.yaml`.
**THEN** the script should run to completion without raising any errors.
**AND** the script's output should contain a success message, for example, "Cycle 02 workflow complete."
**AND** a trained model file must exist.

---

**Scenario: UAT-C02-02 - Successful Molecule Workflow from Minimal Input**

**GIVEN** I have a minimal configuration file named `h2o_input.yaml` with the content:
```yaml
elements: [H, O]
composition: H2O
```
**WHEN** I execute the command `python -m mlip_autopipec.main_cycle02 --config h2o_input.yaml`.
**THEN** the script should run to completion without raising any errors.
**AND** the script's output should contain a success message, for example, "Cycle 02 workflow complete."
**AND** a trained model file must exist.

---

**Scenario: UAT-C02-03 - Verification of Generated `exec_config_dump.yaml`**

**GIVEN** I have successfully run the workflow from scenario UAT-C02-01.
**WHEN** I open and inspect the generated `exec_config_dump.yaml` file.
**THEN** the file must be syntactically valid YAML.
**AND** the value of the key `system.structure_type` must be the string `"alloy"`.
**AND** the value of the key `dft_compute.ecutwfc` must be a floating-point number greater than 30.0.
**AND** the value of the key `dft_compute.pseudopotentials` must be a non-empty string.

---

**Scenario: UAT-C02-04 - Verification of Generated Structures**

**GIVEN** I have successfully run the workflow from scenario UAT-C02-01.
**WHEN** I query the `mlip.db` database for the number of new structures created in the latest run.
**THEN** the number of structures must be greater than 1.
**AND** when I extract the atomic positions of the first two structures, their coordinates must not be identical.

---

**Scenario: UAT-C02-05 - Handling of Invalid Composition**

**GIVEN** I have a minimal configuration file named `invalid_input.yaml` with the content:
```yaml
elements: [Fe, Zz]
composition: FeZz
```
**WHEN** I execute the command `python -m mlip_autopipec.main_cycle02 --config invalid_input.yaml`.
**THEN** the script should exit gracefully and not produce a Python traceback.
**AND** the script's output on the console should contain a clear error message like "Error: Element 'Zz' is not supported."

---
