import numpy as np
import torch

SEED = 0
np.random.seed(0)
torch.manual_seed(0)

# For service provider
NUM_SERVICE_PROVIDERS = 20  # number of service providers
# TOTAL_T_RANGE = np.arange(300, 500, step=20)
# TOTAL_T_RANGE = np.arange(350, 510, step=10)
TOTAL_T_RANGE = np.arange(500, 1000, step=100)
# providers
NUM_CPUS = 32  # number of logical cpu cores available
NUM_GPUS = 8  # number of graphic cards available
CPU_MEM = 128 * 2 ** 30  # total cpu memory available
GPU_MEM = 24 * 2 ** 30  # gpu memory for each graphic card
# Reward function for an inpainted image. The value is related to t_T in the diffusion algorithm.
# AX_RANGE = np.arange(0, 100, step=10)
# AY_RANGE = np.arange(0., 0.5, step=0.05)
# BX_RANGE = np.arange(200, 260, step=10)
# BY_RANGE = np.arange(0.5, 1., step=0.05)
AX_RANGE = np.arange(0, 100, step=10)
AY_RANGE = np.arange(0., 0.5, step=0.05)
BX_RANGE = np.arange(150, 250, step=10)
BY_RANGE = np.arange(0.5, 1., step=0.05)
# REWARD = lambda ax, ay, bx, by, t: \
#     (by - ay) / (bx - ax) * (t - ax) + ay if ax <= t <= bx else \
#     (ay if t < ax else by)
REWARD = lambda ax, ay, bx, by, t: \
    (by - ay) / (bx - ax) * (t - ax) if ax <= t <= bx else \
    (0 if t < ax else by - ay)

# For user
NUM_USERS = 1000  # number of users to serve
LOCATION_RANGE = [(0, 0), (100, 100)]  # [(x_min, y_min), (x_max, y_max)]

# For task generator
LAMBDA = 0.001  # λ for Poisson distribution
TOTAL_TIME = 1000000  # time duration of an episode
T_RANGE = np.arange(100, 260, step=10)  # range of t_T for diffusion algorithm

# For task
NUM_TASK_TYPES = 5  # number of task types available
IMG_CHW = (3, 218, 178)  # (n_channel, height, width)
IMG_BUFFER = 8 * 2 ** 10  # 8KBytes per image, JPEG format, for storage and transmission
GPU_MEM_OCCUPY = 4000 * 2 ** 20  # 7468MB GPU memory occupation per image and per run
GPU_UTILITY = 1.  # GPU-Util of 100%, full load
CPU_MEM_OCCUPY = 2000 * 2 ** 20  # 4980MB CPU memory occupation per image and per run
CPU_UTILITY = 0.1  # CPU-Util of 10%
CRASH_PENALTY_COEF = 1.
# Runtime for each image. The value is proportional to t_T in the diffusion algorithm.
RUNTIME = lambda t: (0.001 * t ** 2 + 2.5 * t - 14) * 60
