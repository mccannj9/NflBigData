#! /usr/bin/env python3

import os
import sys
import itertools

import numpy as np
import pandas as pd

from matplotlib import pyplot as plt
from scipy.stats import multivariate_normal as mvn

from utils.math import sigmoid

play = int(sys.argv[1])

# adapt for windows
try:
    homedir = os.environ['HOME']
except KeyError:
    homedir = os.path.join(
        os.environ['HOMEDRIVE'], os.environ['HOMEPATH']
    )

datapath = os.path.join(
    homedir, 'dev/NflBigData/data/kaggle/train.csv'
)

data = pd.read_csv(datapath, low_memory=False)
print(data.head())

play_data = data[play*22: (play+1)*22]

rusher = np.argmax(
    np.array(play_data['NflId'] == play_data['NflIdRusher'])
)

color_ids = ['red'] * 11 + ['blue'] * 11
color_ids[rusher] = 'green'
color_ids[11] = 'black'

# show player position in first play in scatter plot with colors
plt.scatter(play_data['X'], play_data['Y'], color=color_ids)

# TODO (1) Plot vectors with orientation and direction of movement
#      (2) Scale direction of movement vectors by speed and accel
#      (3) Calculate rusher space between all defenders
#      (4) Calculate player influence using basic bivariate normal

# need to convert to radians
degs_dir = play_data['Dir']
rads_dir = degs_dir * (np.pi/180)

degs_ort = play_data['Orientation']
rads_ort = degs_ort * (np.pi/180)

# getting x, y components on the unit circle
# will scale by speed at some point
x_dirs = np.array(np.sin(rads_dir)).reshape(-1, 1)
y_dirs = np.array(np.cos(rads_dir)).reshape(-1, 1)
dir_vecs = np.concatenate([x_dirs, y_dirs], axis=1)

x_orts = np.array(np.sin(rads_ort)).reshape(-1, 1)
y_orts = np.array(np.cos(rads_ort)).reshape(-1, 1)
ort_vecs = np.concatenate([x_orts, y_orts], axis=1)

# getting the origin of the vectors to plot, i.e. player positions
x_pos = np.array(play_data['X']).reshape(-1,1)
y_pos = np.array(play_data['Y']).reshape(-1,1)
pos = np.concatenate([x_pos, y_pos], axis=1)

# plot the vectors ...
plt.quiver(
    pos[:, 0], pos[:, 1],
    dir_vecs[:, 0], dir_vecs[:, 1],
    color=color_ids, scale=50
)

plt.quiver(
    pos[:, 0], pos[:, 1],
    ort_vecs[:, 0], ort_vecs[:, 1],
    color=color_ids, scale=25
)

plt.show()

# TODO -- Project: Calculating player influence
# (1, done) Generate mesh grid, which will be image pixels
# (2, done) Calculate influence for each player and point on the image
# Note: should be 11 images for defense, 10 for offense, still deciding for ball carrier
# (3) Add images together for defense and offense separately
# (4) Take difference between summed images for defense and offense, sigmoid it for a single image

# Computation of influence area
# Find factor of Cov = R * S * S * R^-1

# adjust angle for standard unit circle
theta = -(rads_dir[11] - (np.pi/2))

# rotation matrix for above angle
R = np.array(
    [
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta), np.cos(theta)]
    ]
)

# compute eigenvalues using projection of speed onto unit eigenvectors
Sx = play_data.iloc[11].S * np.cos(theta)
Sy = play_data.iloc[11].S * np.sin(theta)
S = np.array([[Sx, 0], [0, Sy]])

Sigma = R @ S @ S @ np.linalg.inv(R)

player_x_pos = int(round(play_data.iloc[11].X))
player_y_pos = int(round(play_data.iloc[11].Y))

mvn_for_player = mvn(mean=[player_x_pos, player_y_pos], cov=Sigma)
image_wd, image_ht = 120, 57

# need to account for difference in coordinates between numpy and nfl data
player_influence_image = np.zeros((image_ht, image_wd))

for i, (a, b) in enumerate(
    itertools.product(range(image_ht), range(image_wd))
):
    a = image_ht - a - 1
    player_influence_image[a, b] = mvn_for_player.pdf([b, a])

a, b = zip(*list(
    itertools.product(range(image_ht), range(image_wd))
))

player_influence_image_test = np.zeros((image_ht, image_wd))
player_influence_image_test[a, b] = mvn_for_player.pdf(list(zip(b, a)))

fig, ax = plt.subplots(2)
ax[0].imshow(player_influence_image, origin='lower')
ax[1].imshow(player_influence_image_test, origin='lower')

fig.savefig("./data/player_influence_image.png", dpi=300)

image_wd, image_ht = 120, 57
player_influence_images = np.zeros((len(play_data), image_ht, image_wd))
for x in range(len(play_data)):
    # adjust angle for standard unit circle
    theta = -(rads_dir[x] - (np.pi/2))

    # rotation matrix for above angle
    R = np.array(
        [
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)]
        ]
    )

    # compute eigenvalues using projection of speed onto unit eigenvectors
    Sx = play_data.iloc[x].S * np.cos(theta) * play_data.iloc[x].A
    Sy = play_data.iloc[x].S * np.sin(theta) * play_data.iloc[x].A
    S = np.array([[Sx, 0], [0, Sy]])

    Sigma = R @ S @ S @ np.linalg.inv(R)

    player_x_pos = int(round(play_data.iloc[x].X))
    player_y_pos = int(round(play_data.iloc[x].Y))

    mvn_for_player = mvn(mean=[player_x_pos, player_y_pos], cov=Sigma)
    for i, (a, b) in enumerate(
        itertools.product(range(image_ht), range(image_wd))
    ):
        a = image_ht - a - 1
        player_influence_images[x, a, b] = mvn_for_player.pdf([b, a])

    player_influence_images[x] = sigmoid(player_influence_images[x])
    # player_influence_images[x] /= player_influence_images[x].max()

team_1 = player_influence_images[:11, :, :].sum(axis=0)
team_2 = player_influence_images[11:, :, :].sum(axis=0)

prob_of_ctrl = sigmoid(team_1 - team_2)

fig, ax = plt.subplots(3)
ax[0].imshow(prob_of_ctrl, origin='lower')
ax[1].imshow(team_1, origin='lower')
ax[2].imshow(team_2, origin='lower')

fig.savefig("./data/sigmoid_player_influences.png", dpi=300)
