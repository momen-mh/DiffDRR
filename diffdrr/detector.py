# AUTOGENERATED! DO NOT EDIT! File to edit: ../notebooks/api/02_detector.ipynb.

# %% ../notebooks/api/02_detector.ipynb 3
from __future__ import annotations

import torch
from fastcore.basics import patch
from torch.nn.functional import normalize

# %% auto 0
__all__ = ['Detector']

# %% ../notebooks/api/02_detector.ipynb 5
class Detector:
    """Construct a 6 DoF X-ray detector system. This model is based on a C-Arm."""

    def __init__(
        self,
        height: int,  # Height of the X-ray detector
        width: int,  # Width of the X-ray detector
        delx: float,  # Pixel spacing in the X-direction
        dely: float,  # Pixel spacing in the Y-direction
        n_subsample: int | None = None,  # Number of target points to randomly sample
    ):
        self.height = height
        self.width = width
        self.delx = delx
        self.dely = dely
        self.n_subsample = n_subsample
        if self.n_subsample is not None:
            self.subsamples = []

# %% ../notebooks/api/02_detector.ipynb 6
@patch
def make_xrays(
    self: Detector,
    sdr: torch.Tensor,  # source-to-detector radius (half of the source-to-detector distance)
    rotations: torch.Tensor,  # Vector of C-arm rotations (theta, phi, gamma) for azimuthal, polar, and roll angles
    translations: torch.Tensor,  # Vector of C-arm translations (bx, by, bz)
):
    """Create source and target points for X-rays to trace through the volume."""

    # Get the detector plane normal vector
    assert len(rotations) == len(translations)
    source, center, basis = _get_basis(sdr, rotations)
    source += translations.unsqueeze(1)
    center += translations.unsqueeze(1)

    # Construct the detector plane with different offsets for even or odd heights
    h_off = 1.0 if self.height % 2 else 0.5
    w_off = 1.0 if self.width % 2 else 0.5
    t = (torch.arange(-self.height // 2, self.height // 2) + h_off) * self.delx
    s = (torch.arange(-self.width // 2, self.width // 2) + w_off) * self.dely

    coefs = torch.cartesian_prod(t, s).reshape(-1, 2).to(sdr)
    target = torch.einsum("bcd,nc->bnd", basis, coefs)
    target += center
    if self.n_subsample is not None:
        sample = torch.randperm(self.height * self.width)[: int(self.n_subsample)]
        target = target[:, sample, :]
        self.subsamples.append(sample.tolist())
    return source, target

# %% ../notebooks/api/02_detector.ipynb 7
def _get_basis(rho, rotations):
    # Get the rotation of 3D space
    R = rho.unsqueeze(-1) * Rxyz(rotations)

    # Get the detector center and X-ray source
    source = R[..., 0].unsqueeze(1)
    center = -source

    # Get the basis of the detector plane (before translation)
    R_ = normalize(R.clone(), dim=-1)
    u, v = R_[..., 1], R_[..., 2]
    basis = torch.stack([u, v], dim=1)

    return source, center, basis

# %% ../notebooks/api/02_detector.ipynb 8
# Define 3D rotation matrices
def Rxyz(rotations):
    theta, phi, gamma = rotations[:, 0], rotations[:, 1], rotations[:, 2]
    batch_size = len(rotations)
    device = rotations
    R_z = Rz(theta, batch_size, device)
    R_y = Ry(phi, batch_size, device)
    R_x = Rx(gamma, batch_size, device)
    return torch.einsum("bij,bjk,bkl->bil", R_z, R_y, R_x)


def Rx(gamma, batch_size, device):
    t0 = torch.zeros(batch_size, 1).to(device)
    t1 = torch.ones(batch_size, 1).to(device)
    return torch.stack(
        [
            t1,
            t0,
            t0,
            t0,
            torch.cos(gamma.unsqueeze(1)),
            -torch.sin(gamma.unsqueeze(1)),
            t0,
            torch.sin(gamma.unsqueeze(1)),
            torch.cos(gamma.unsqueeze(1)),
        ],
        dim=1,
    ).reshape(batch_size, 3, 3)


def Ry(phi, batch_size, device):
    t0 = torch.zeros(batch_size, 1).to(device)
    t1 = torch.ones(batch_size, 1).to(device)
    return torch.stack(
        [
            torch.cos(phi.unsqueeze(1)),
            t0,
            torch.sin(phi.unsqueeze(1)),
            t0,
            t1,
            t0,
            -torch.sin(phi.unsqueeze(1)),
            t0,
            torch.cos(phi.unsqueeze(1)),
        ],
        dim=1,
    ).reshape(batch_size, 3, 3)


def Rz(theta, batch_size, device):
    t0 = torch.zeros(batch_size, 1).to(device)
    t1 = torch.ones(batch_size, 1).to(device)
    return torch.stack(
        [
            torch.cos(theta.unsqueeze(1)),
            -torch.sin(theta.unsqueeze(1)),
            t0,
            torch.sin(theta.unsqueeze(1)),
            torch.cos(theta.unsqueeze(1)),
            t0,
            t0,
            t0,
            t1,
        ],
        dim=1,
    ).reshape(batch_size, 3, 3)
