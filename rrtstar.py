#!/usr/bin/env python

# rrtstar.py
# This program generates a
# asymptotically optimal rapidly exploring random tree (RRT*) in a rectangular region.

import sys
import random
import math
import pygame
from pygame.locals import *
from math import sqrt, cos, sin, atan2
from checkCollision import *
import numpy as np

# constants
XDIM = 640
YDIM = 480
EPSILON = 7.0
NUMNODES = 2000
RADIUS = 15
fpsClock = pygame.time.Clock()

INFINITE = sys.maxsize

ALPHA_CK = 255,0,255

GOAL_RADIUS = 10

SCALING = 3

GOAL_BIAS = 0.05

img = None
c_min = None
x_center = None
angle = None
c_max = INFINITE


############################################################

def collides(p):    #check if point is white (which means free space)
    global pygame, img
    # make sure x and y is within image boundary
    x = int(p[0])
    y = int(p[1])
    if x < 0 or x >= img.get_width() or y < 0 or y >= img.get_height():
        # print(x, y)
        return True
    color = img.get_at((x, y))
    white = 255, 255, 255
    # print(color)
    if color == pygame.Color(*white):
        return False
    return True


def dist(p1, p2):
    return np.linalg.norm(p1 - p2)
    # return sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def step_from_to(p1, p2):
    if dist(p1, p2) < EPSILON:
        return np.array(p2)
    else:
        theta = atan2(p2[1] - p1[1], p2[0] - p1[0])
        pos = p1[0] + EPSILON * cos(theta), p1[1] + EPSILON * sin(theta)
        return np.array(pos)


def chooseParent(nn, newnode, nodes):
    global img
    for p in nodes:
        if checkIntersect(p, newnode, img) and dist(p.pos, newnode.pos) < RADIUS and p.cost + dist(p.pos, newnode.pos) < nn.cost + dist(nn.pos, newnode.pos):
            nn = p
    newnode.cost = nn.cost + dist(nn.pos, newnode.pos)
    newnode.parent = nn
    return newnode, nn


def reWire(nodes, newnode, pygame, screen):
    global img
    white = 255, 240, 200
    black = 20, 20, 40
    for i in range(len(nodes)):
        p = nodes[i]
        if checkIntersect(p, newnode, img) and p != newnode.parent and dist(p.pos, newnode.pos) < RADIUS and newnode.cost + dist(p.pos, newnode.pos) < p.cost:
            pygame.draw.line(screen, white, p.pos, p.parent.pos)
            p.parent = newnode
            p.cost = newnode.cost + dist(p.pos, newnode.pos)
            nodes[i] = p
            pygame.draw.line(screen, black, p.pos, newnode.pos)
    return nodes

# to force drawSolutionPath only draw once for every new solution
solution_path_c_max = INFINITE

def drawSolutionPath(start, goal, nodes, pygame, screen):
    global solution_path_c_max, c_max

    # redraw new path
    green = 0,150,0
    screen.fill(ALPHA_CK)

    nn = nodes[0]
    for p in nodes:
        if dist(p.pos, goal.pos) < dist(nn.pos, goal.pos):
            nn = p
    while nn != start:
        pygame.draw.line(screen, green, nn.pos, nn.parent.pos, 5)
        nn = nn.parent



def get_random_path(c_max):
    if c_max != INFINITE: #max size represent infinite (not found solution yet)
        global c_min, x_center, angle
        # already have a valid solution, optimise in ellipse region
        r1 = c_max / 2
        r2 = math.sqrt(abs(c_max**2 - c_min**2))

        x = np.random.uniform(-1, 1)
        y = np.random.uniform(-1, 1)

        x2 =  x * r1 * math.cos(angle) + y * r2 * math.sin(angle)
        y2 = -x * r1 * math.sin(angle) + y * r2 * math.cos(angle)

        ##################################
        ##################################
        ##################################
        pos =  x2 + x_center[0] , y2 + x_center[1]
        return np.array(pos)

    # Random path
    while True:
        p = random.random()*XDIM, random.random()*YDIM
        if not collides(p):
            return np.array(p)

class Node:
    pos = None  # index 0 is x, index 1 is y
    cost = 0
    parent = None

    def __init__(self, pos):
        self.pos = pos

def main():
    global pygame, img

    # initialize and prepare screen
    pygame.init()
    img = pygame.image.load('map.png')
    XDIM = img.get_width()
    YDIM = img.get_height()

    pygame.display.set_caption('RRTstar')
    white = 255, 255, 255
    black = 20, 20, 40
    red = 255, 0, 0
    blue = 0, 0, 255
    # screen.fill(white)

    ################################################################################
    # text
    pygame.font.init()
    myfont = pygame.font.SysFont('Arial', 20 * SCALING)
    ################################################################################
    # main window
    window = pygame.display.set_mode([XDIM * SCALING, YDIM * SCALING])
    ################################################################################
    # background aka the room
    background = pygame.Surface( [XDIM, YDIM] )
    background.blit(img,(0,0))
    # resize background to match windows
    background = pygame.transform.scale(background, (XDIM * SCALING, YDIM * SCALING))
    ################################################################################
    # path of RRT*
    path_layers = pygame.Surface( [XDIM, YDIM] )
    path_layers.fill(ALPHA_CK)
    path_layers.set_colorkey(ALPHA_CK)
    # rescale to make it bigger
    path_layers_rescale = pygame.Surface( [XDIM * SCALING, YDIM * SCALING] )
    path_layers_rescale.fill(ALPHA_CK)
    path_layers_rescale.set_colorkey(ALPHA_CK)
    ################################################################################
    # layers to store the solution path
    solution_path_screen = pygame.Surface( [XDIM, YDIM] )
    solution_path_screen.fill(ALPHA_CK)
    solution_path_screen.set_colorkey(ALPHA_CK)
    # rescale to make it bigger
    solution_path_screen_rescale = pygame.Surface( [XDIM * SCALING, YDIM * SCALING] )
    solution_path_screen_rescale.fill(ALPHA_CK)
    solution_path_screen_rescale.set_colorkey(ALPHA_CK)
    ################################################################################

    startPt = None
    goalPt = None

    num_nodes = 0

    def update():
        pygame.transform.scale(path_layers, (XDIM * SCALING, YDIM * SCALING), path_layers_rescale)
        pygame.transform.scale(solution_path_screen, (XDIM * SCALING, YDIM * SCALING), solution_path_screen_rescale)

        window.blit(background,(0,0))
        window.blit(path_layers_rescale,(0,0))
        window.blit(solution_path_screen_rescale,(0,0))

        if startPt is not None:
            pygame.draw.circle(path_layers, red, startPt.pos, GOAL_RADIUS)
        if goalPt is not None:
            pygame.draw.circle(path_layers, blue, goalPt.pos, GOAL_RADIUS)

        _cost = 'INF' if c_max == INFINITE else round(c_max, 2)
        text = 'Cost_min:  {}   |   Nodes:  {}'.format(_cost, num_nodes)
        window.blit(myfont.render(text, False, (0, 0, 0)), (20,YDIM * SCALING * 0.9))

        pygame.display.update()

    nodes = []
    ##################################################
    # Get starting and ending point
    print('Select Starting Point and then Goal Point')
    fpsClock.tick(10)
    while startPt is None or goalPt is None:
        for e in pygame.event.get():
            if e.type == MOUSEBUTTONDOWN:
                mousePos = (int(e.pos[0] / SCALING), int(e.pos[1] / SCALING))
                if startPt is None:
                    if collides(mousePos) == False:
                        print(('starting point set: ' + str(mousePos)))
                        startPt = Node(np.array(mousePos))
                        nodes.append(startPt)
                elif goalPt is None:
                    if collides(mousePos) == False:
                        print(('goal point set: ' + str(mousePos)))
                        goalPt = Node(np.array(mousePos))
                elif e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                    sys.exit("Leaving.")
        update()
    ##################################################
    # calculate information regarding shortest path
    global c_min, x_center, angle
    c_min = dist(startPt.pos, goalPt.pos)
    x_center = (startPt.pos[0]+goalPt.pos[0])/2 , (startPt.pos[1]+goalPt.pos[1])/2
    dy = goalPt.pos[1] - startPt.pos[1]
    dx = goalPt.pos[0] - startPt.pos[0]
    angle = math.atan2(-dy, dx)

    ##################################################

    fpsClock.tick(10000)
    global c_max

    for i in range(NUMNODES):
        # probabiilty to bias toward goal (while not reaching goal yet)
        if c_max == INFINITE and random.random() < GOAL_BIAS:
            rand = Node(np.array(goalPt.pos))
        else:
            rand = Node(get_random_path(c_max))
        nn = nodes[0]
        for p in nodes:
            if dist(p.pos, rand.pos) < dist(nn.pos, rand.pos):
                nn = p
        interpolatedNode = step_from_to(nn.pos, rand.pos)

        newnode = Node(interpolatedNode)
        if checkIntersect(nn, rand, img):

            [newnode, nn] = chooseParent(nn, newnode, nodes)
            # newnode.parent = nn

            nodes.append(newnode)
            pygame.draw.line(path_layers, black, nn.pos, newnode.pos)
            nodes = reWire(nodes, newnode, pygame, path_layers)
            pygame.display.update()

            if dist(newnode.pos, goalPt.pos) < GOAL_RADIUS:
                # print('Reached goal!')

                if newnode.cost < c_max:
                    c_max = newnode.cost
                    drawSolutionPath(startPt, goalPt, nodes, pygame, solution_path_screen)

            for e in pygame.event.get():
                if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                    sys.exit("Leaving.")
        num_nodes = i
        update()
    update() # update one last time
    # wait for exit
    while True:
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                sys.exit("Leaving.")


# if python says run, then we should run
if __name__ == '__main__':
    main()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
