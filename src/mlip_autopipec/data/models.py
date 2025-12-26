from pydantic import BaseModel
from typing import List, Optional

class DFTResult(BaseModel):
    """
    A Pydantic model to represent the results of a DFT calculation.
    """
    total_energy_ev: float
    forces: List[List[float]]
    stress: List[List[float]]
    was_successful: bool
    error_message: Optional[str] = None

class TrainingConfig(BaseModel):
    """
    A Pydantic model for configuring the MLIP training process.
    """
    model_type: str
    learning_rate: float
    num_epochs: int
    r_cut: float
    delta_learn: bool
    baseline_potential: str
