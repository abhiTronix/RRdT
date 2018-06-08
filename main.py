import rrtstar
from randomPolicySampler import RandomPolicySampler
from likelihoodPolicySampler import LikelihoodPolicySampler
from particleFilterSampler import ParticleFilterSampler
from nearbyPolicySampler import NearbyPolicySampler
from mouseSampler import MouseSampler

# if python says run, then we should run
if __name__ == '__main__':
    epsilon = 10.0
    max_number_nodes = 3000
    goal_radius = 15
    prob_block_size = 5
    SCALING = 4
    IGNORE_STEP_SIZE = True

    sampler = NearbyPolicySampler(prob_block_size=prob_block_size)
    sampler = LikelihoodPolicySampler(prob_block_size=prob_block_size)
    sampler = RandomPolicySampler()
    sampler = ParticleFilterSampler()
    sampler = MouseSampler()

    rrt = rrtstar.RRT(
        showSampledPoint=True,
        scaling=SCALING,
        sampler=sampler,
        goalBias=False,
        image='map.png',
        epsilon=epsilon,
        max_number_nodes=max_number_nodes,
        radius=goal_radius,
        ignore_step_size=IGNORE_STEP_SIZE,
        always_refresh=False
        )
    rrt.run()
