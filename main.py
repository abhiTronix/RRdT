import rrtstar
from randomPolicySampler import RandomPolicySampler
from likelihoodPolicySampler import LikelihoodPolicySampler

# if python says run, then we should run
if __name__ == '__main__':
    epsilon = 7.0
    # epsilon = 7.0 * 10
    max_number_nodes = 2000
    radius = 15
    prob_block_size = 15

    # sampler = RandomPolicySampler()
    sampler = LikelihoodPolicySampler(prob_block_size=prob_block_size)

    CHECK_ENTIRE_PATH = False

    rrt = rrtstar.RRT(sampler=sampler, goalBias=True, check_entire_path=CHECK_ENTIRE_PATH, image='map.png', epsilon=epsilon, max_number_nodes=max_number_nodes, radius=radius)
    rrt.run()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
