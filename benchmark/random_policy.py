from typing import Any, Dict, List, Type, Optional, Union

import argparse
import os
import pprint
import torch
import numpy as np

from datetime import datetime
from torch.utils.tensorboard import SummaryWriter
from tianshou.data import Collector, ReplayBuffer
from tianshou.policy import BasePolicy
from tianshou.trainer import onpolicy_trainer
from tianshou.utils import TensorboardLogger
from tianshou.data import Batch
from tianshou.utils import RunningMeanStd


class RandomPolicy(BasePolicy):
    """Implementation of random policy. This policy assign user tasks to service
    providers at random.

    :param dist_fn: distribution class for computing the action.
    :type dist_fn: Type[torch.distributions.Distribution]
    :param float discount_factor: in [0, 1]. Default to 0.99.
    :param bool action_scaling: whether to map actions from range [-1, 1] to range
        [action_spaces.low, action_spaces.high]. Default to True.
    :param str action_bound_method: method to bound action to range [-1, 1], can be
        either "clip" (for simply clipping the action), "tanh" (for applying tanh
        squashing) for now, or empty string for no bounding. Default to "clip".
    :param Optional[gym.Space] action_space: env's action space, mandatory if you want
        to use option "action_scaling" or "action_bound_method". Default to None.
    :param lr_scheduler: a learning rate scheduler that adjusts the learning rate in
        optimizer in each policy.update(). Default to None (no lr_scheduler).
    """

    def __init__(
            self,
            dist_fn: Type[torch.distributions.Distribution],
            discount_factor: float = 0.99,
            reward_normalization: bool = False,
            action_scaling: bool = True,
            action_bound_method: str = "clip",
            **kwargs: Any
    ) -> None:
        super().__init__(
            action_scaling=action_scaling,
            action_bound_method=action_bound_method,
            **kwargs)
        self.dist_fn = dist_fn
        assert 0.0 <= discount_factor <= 1.0, "discount factor should be in [0, 1]"
        self._gamma = discount_factor
        self._rew_norm = reward_normalization
        self.ret_rms = RunningMeanStd()
        self._eps = 1e-8

    def process_fn(
            self,
            batch: Batch,
            buffer: ReplayBuffer,
            indices: np.ndarray
    ) -> Batch:
        r"""Compute the discounted returns for each transition.

        .. math::
            G_t = \sum_{i=t}^T \gamma^{i-t}r_i

        where :math:`T` is the terminal time step, :math:`\gamma` is the
        discount factor, :math:`\gamma \in [0, 1]`.
        """
        v_s_ = np.full(indices.shape, self.ret_rms.mean)
        unnormalized_returns, _ = self.compute_episodic_return(
            batch, buffer, indices, v_s_=v_s_, gamma=self._gamma, gae_lambda=1.0
        )
        if self._rew_norm:
            batch.returns = (unnormalized_returns - self.ret_rms.mean) / \
                            np.sqrt(self.ret_rms.var + self._eps)
            self.ret_rms.update(unnormalized_returns)
        else:
            batch.returns = unnormalized_returns
        return batch

    def forward(
            self,
            batch: Batch,
            state: Optional[Union[dict, Batch, np.ndarray]] = None,
            **kwargs: Any
    ) -> Batch:
        """Compute action at random."""

        logits, hidden = torch.rand((batch.obs.shape[0], NUM_SERVICE_PROVIDERS)), None

        # convert to probability distribution
        if isinstance(logits, tuple):
            dist = self.dist_fn(*logits)
        else:
            dist = self.dist_fn(logits)

        # use deterministic policy
        if self.action_type == "discrete":
            act = logits.argmax(-1)
        elif self.action_type == "continuous":
            act = logits[0]

        return Batch(logits=logits, act=act, state=hidden, dist=dist)

    def learn(
            self,
            batch: Batch,
            batch_size: int,
            repeat: int,
            **kwargs: Any
    ) -> Dict[str, List[float]]:
        return {"loss": [0.]}


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reward-threshold', type=float, default=None)
    parser.add_argument('--gamma', type=float, default=0.95)
    parser.add_argument('--epoch', type=int, default=500)
    parser.add_argument('--step-per-epoch', type=int, default=100)
    parser.add_argument('--episode-per-collect', type=int, default=1)
    parser.add_argument('--repeat-per-collect', type=int, default=1)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--training-num', type=int, default=20)
    parser.add_argument('--test-num', type=int, default=10)
    parser.add_argument('--logdir', type=str, default='log')
    parser.add_argument('--render', type=float, default=0.01)
    parser.add_argument('--rew-norm', type=int, default=0)
    parser.add_argument(
        '--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_known_args()[0]
    return args


def main(args=get_args()):
    env, train_envs, test_envs = make_aigc_env(args.training_num, args.test_num)

    args.state_shape = env.observation_space.shape or env.observation_space.n
    args.action_shape = env.action_space.shape or env.action_space.n

    # random policy
    policy = RandomPolicy(
        torch.distributions.Categorical,
        args.gamma,
        reward_normalization=args.rew_norm,
        action_space=env.action_space,
        action_scaling=False,
        action_bound_method="",
    )

    # collector
    train_collector = Collector(policy, train_envs)
    test_collector = Collector(policy, test_envs)

    # log
    time_now = datetime.now().strftime('%b%d-%H%M%S')
    root = path.dirname(path.dirname(path.abspath(__file__)))
    log_path = os.path.join(root, args.logdir, 'aigcaas', 'random', time_now)
    writer = SummaryWriter(log_path)
    logger = TensorboardLogger(writer)

    # trainer
    result = onpolicy_trainer(
        policy,
        train_collector,
        test_collector,
        args.epoch,
        args.step_per_epoch,
        args.repeat_per_collect,
        args.test_num,
        args.batch_size,
        episode_per_collect=args.episode_per_collect,
        logger=logger,
    )

    # Watch the performance
    if __name__ == '__main__':
        pprint.pprint(result)
        env, _, _ = make_aigc_env()
        policy.eval()
        collector = Collector(policy, env)
        result = collector.collect(n_episode=1, render=args.render)
        rews, lens = result["rews"], result["lens"]
        print(f"Final reward: {rews.mean()}, length: {lens.mean()}")


if __name__ == '__main__':
    if __package__ is None:
        import sys
        from os import path

        sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
        from env import make_aigc_env
        from config import *
    else:
        from ..env import make_aigc_env
        from ..config import *

    main(get_args())